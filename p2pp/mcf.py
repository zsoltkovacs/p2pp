__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import os
import io
import p2pp.gui as gui
from p2pp.formatnumbers import hexify_float
import p2pp.parameters as parameters
import p2pp.sidewipe as sidewipe
import p2pp.variables as v
from p2pp.gcodeparser import gcode_remove_params, get_gcode_parameter, parse_slic3r_config
from p2pp.omega import header_generate_omega, algorithm_process_material_configuration
from p2pp.logfile import log_warning


# ################### GCODE PROCESSING ###########################
def gcode_process_toolchange(new_tool, location):
    # some commands are generated at the end to unload filament,
    # they appear as a reload of current filament - messing up things
    if new_tool == v.current_tool:
        return

    location += v.splice_offset

    if new_tool == -1:
        location += v.extra_runout_filament
    else:
        v.palette_inputs_used[new_tool] = True

    length = location - v.previous_toolchange_location

    if v.current_tool != -1:
        v.splice_extruder_position.append(location)
        v.splice_length.append(length)
        v.splice_used_tool.append(v.current_tool)

        if len(v.splice_extruder_position) == 1:
            if v.splice_length[0] < v.min_start_splice_length:
                log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(length,
                                                                                          v.min_start_splice_length))
        else:
            if v.splice_length[-1] < v.min_splice_length:
                log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".
                            format(v.min_splice_length, length, v.current_layer, v.current_tool))

    v.previous_toolchange_location = location
    v.current_tool = new_tool


def gcode_filter_toolchange_block(line):
    # --------------------------------------------------------------
    # Do not perform this part of the GCode for MMU filament unload
    # --------------------------------------------------------------
    discarded_moves = ["E-15.0000",
                       "G1 E10.5000",
                       "G1 E3.0000",
                       "G1 E1.5000"
                       ]

    if line.startswith("G1"):
        for gcode_filter in discarded_moves:
            if gcode_filter in line:         # remove specific MMU2 extruder moves
                return ";--- P2PP removed [M]"+line
        return gcode_remove_params(line, ["F"])

    if line.startswith("M907"):
        return ";--- P2PP removed [S]" + line   # remove motor power instructions

    if line.startswith("M220"):
        return ";--- P2PP removed [S]" + line   # remove feedrate instructions

    if line.startswith("G4 S0"):
        return ";--- P2PP removed [S}" + line   # remove dwelling instructions

    return line


def coordinate_on_bed(x, y):
    if v.bed_origin_x > x:
        return False
    if x >= v.bed_origin_x + v.bed_size_x:
        return False
    if v.bed_origin_y >= y:
        return False
    if y >= v.bed_origin_y + v.bed_size_y:
        return False
    return True


def moved_in_tower():
    return not coordinate_on_bed(v.currentPositionX, v.currentPositionY)


def gcode_parseline(gcode_full_line):

    __tower_remove = False

    if not gcode_full_line[0] == ";":
        gcode_full_line = gcode_full_line.split(';')[0]

    gcode_full_line = gcode_full_line.rstrip('\n')

    if gcode_full_line == "":
        v.processed_gcode.append("\n")
        return

    if gcode_full_line.startswith('T'):
        new_tool = int(gcode_full_line[1])
        gcode_process_toolchange(new_tool, v.total_material_extruded)
        v.allow_filament_information_update = True
        v.processed_gcode.append(';--- P2PP removed [1]' + gcode_full_line + "\n")
        return

    if gcode_full_line[0:4] in ["M104", "M106", "M109", "M140", "M190"]:
        v.processed_gcode.append(gcode_full_line + "\n")
        return

    if v.side_wipe:
        sidewipe.collect_wipetower_info(gcode_full_line)

        if v.side_wipe_skip:
            v.processed_gcode.append(";--- P2PP removed [2]" + gcode_full_line + "\n")
            return

        if moved_in_tower() and v.side_wipe and not v.side_wipe_skip:
            if not gcode_full_line[0] == ";":
                v.processed_gcode.append(";--- P2PP  - Purge Tower - " + gcode_full_line + "\n")
            gcode_full_line = gcode_remove_params(gcode_full_line, ["X", "Y"])
            __tower_remove = True

    # Processing of extrusion speed commands
    # ############################################
    if gcode_full_line.startswith("M220"):
        new_feedrate = get_gcode_parameter(gcode_full_line, "S")
        if new_feedrate != "":
            v.current_print_feedrate = new_feedrate / 100

    # Processing of extrusion multiplier commands
    # ############################################
    if gcode_full_line.startswith("M221"):
        new_multiplier = get_gcode_parameter(gcode_full_line, "S")
        if new_multiplier != "":
            v.extrusion_multiplier = new_multiplier / 100

    # Processing of print head movements
    #############################################

    if v.empty_grid and (v.wipe_feedrate != 2000):
        gcode_full_line = gcode_remove_params(gcode_full_line, ["F"])

    if gcode_full_line.startswith("G") and not gcode_full_line.startswith("G28"):
        to_x = get_gcode_parameter(gcode_full_line, "X")
        to_y = get_gcode_parameter(gcode_full_line, "Y")
        prev_x = v.currentPositionX
        prev_y = v.currentPositionY
        if to_x != "":
            v.currentPositionX = float(to_x)
        if to_y != "":
            v.currentPositionY = float(to_y)
        if not coordinate_on_bed(v.currentPositionX, v.currentPositionY) and coordinate_on_bed(prev_x, prev_y):
            gcode_full_line = ";" + gcode_full_line

    if gcode_full_line.startswith("G1"):
            extruder_movement = get_gcode_parameter(gcode_full_line, "E")
            if extruder_movement != "":
                extruder_movement = extruder_movement * v.extrusion_multiplier
                if v.within_tool_change_block and v.side_wipe:
                        v.side_wipe_length += extruder_movement

                v.total_material_extruded += extruder_movement

                if (v.total_material_extruded - v.last_ping_extruder_position) > v.ping_interval and\
                        v.side_wipe_length == 0:
                    v.ping_interval = v.ping_interval * v.ping_length_multiplier
                    v.ping_interval = min(v.max_ping_interval, v.ping_interval)
                    v.last_ping_extruder_position = v.total_material_extruded
                    v.ping_extruder_position.append(v.last_ping_extruder_position)
                    v.processed_gcode.append(";Palette 2 - PING\n")
                    v.processed_gcode.append("G4 S0\n")
                    v.processed_gcode.append("O31 {}\n".format(hexify_float(v.last_ping_extruder_position)))

            if v.within_tool_change_block and v.side_wipe:
                if not __tower_remove:
                    v.processed_gcode.append(';--- P2PP removed [3]' + gcode_full_line + "\n")
                return

            if not v.within_tool_change_block and v.wipe_retracted:
                sidewipe.unretract()

    # Other configuration information
    # this information should be defined in your Slic3r printer settings, startup GCode
    ###################################################################################
    if gcode_full_line.startswith(";P2PP"):
        parameters.check_config_parameters(gcode_full_line)
        v.side_wipe = not coordinate_on_bed(v.wipetower_posx, v.wipetower_posy)

        if gcode_full_line.startswith(";P2PP MATERIAL_"):
                algorithm_process_material_configuration(gcode_full_line[15:])

    if gcode_full_line.startswith("M900"):
        k_factor = get_gcode_parameter(gcode_full_line, "K")
        if float(k_factor) > 0:
            sidewipe.create_side_wipe()
            v.within_tool_change_block = False
            v.mmu_unload_remove = False
        if v.reprap_compatible:
            v.processed_gcode.append(';--- P2PP removed [4]' + gcode_full_line + "\n")
            return

    if gcode_full_line.startswith(";P2PP ENDPURGETOWER"):
        sidewipe.create_side_wipe()
        v.within_tool_change_block = False
        v.mmu_unload_remove = False

    # Next section(s) clean up the GCode generated for the MMU
    # specially the rather violent unload/reload required for the MMU2
    # special processing for side wipes is required in this section
    #################################################################

    if "CP EMPTY GRID START" in gcode_full_line and v.current_layer > "0":
        v.empty_grid = True
        v.current_print_feed = v.wipe_feedrate / 60
        v.processed_gcode.append(";P2PP Set wipe speed to {}mm/s\n".format(v.current_print_feed))
        v.processed_gcode.append("G1 F{}\n".format(v.wipe_feedrate))

    if "CP EMPTY GRID END" in gcode_full_line:
        v.empty_grid = False

    if "TOOLCHANGE START" in gcode_full_line:
        v.allow_filament_information_update = False
        v.within_tool_change_block = True
        sidewipe.sidewipe_toolchange_start()

    if ("TOOLCHANGE END" in gcode_full_line) and not v.side_wipe:
        v.within_tool_change_block = False
        v.mmu_unload_remove = False

    if "TOOLCHANGE UNLOAD" in gcode_full_line and not v.side_wipe:
        v.current_print_feed = v.wipe_feedrate / 60
        v.mmu_unload_remove = True
        if v.current_layer != "0":
            v.processed_gcode.append(";P2PP Set wipe speed to {}mm/s\n".format(v.current_print_feed))
            v.processed_gcode.append("G1 F{}\n".format(v.wipe_feedrate))
        else:
            v.processed_gcode.append(";P2PP Set wipe speed to 33.3mm/s\n")
            v.processed_gcode.append("G1 F2000\n")

    if "TOOLCHANGE WIPE" in gcode_full_line:
        v.mmu_unload_remove = False
        if coordinate_on_bed(v.currentPositionX, v.currentPositionY):
            v.processed_gcode.append("G0 X{} Y{}\n".format(v.currentPositionX, v.currentPositionY))

        # Layer Information
    if gcode_full_line.startswith(";LAYER "):
        v.current_layer = gcode_full_line[7:]

    if v.mmu_unload_remove:
            v.processed_gcode.append(gcode_filter_toolchange_block(gcode_full_line) + "\n")
            return

    if v.within_tool_change_block:
        v.processed_gcode.append(gcode_filter_toolchange_block(gcode_full_line) + "\n")
        return

    # Catch All
    v.processed_gcode.append(gcode_full_line + "\n")


# Generate the file and glue it all together!
# #####################################################################
def generate(input_file, output_file, printer_profile, splice_offset, silent):
    v.printer_profile_string = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0].replace(" ", "_")
    _taskName = _taskName.replace(".mcf", "")

    v.splice_offset = splice_offset

    try:
        opf = open(input_file, encoding='utf-8')
    except:
        try:
            opf = open(input_file)
        except:
            gui.user_error("Could'nt read input file\n'{}'".format(input_file))
            return

    v.input_gcode = opf.readlines()

    opf.close()

    parse_slic3r_config()

    v.side_wipe = not coordinate_on_bed(v.wipetower_posx, v.wipetower_posy)

    # Process the file
    # #################
    for line in v.input_gcode:
        gcode_parseline(line)

    gcode_process_toolchange(-1, v.total_material_extruded)
    omega_result = header_generate_omega(_taskName)
    header = omega_result['header'] + omega_result['summary'] + omega_result['warnings']

    if not silent:
        print (''.join(omega_result['summary']))
        print (''.join(omega_result['warnings']))

    # write the output file
    ######################
    if not output_file:
        output_file = input_file
    opf = open(output_file, "w")
    opf.writelines(header)
    opf.writelines(v.processed_gcode)