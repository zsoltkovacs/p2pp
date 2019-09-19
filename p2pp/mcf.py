__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import os
import time

import p2pp.gcode as gcode
import p2pp.gui as gui
import p2pp.parameters as parameters
import p2pp.pings as pings
import p2pp.purgetower as purgetower
import p2pp.variables as v
from p2pp.gcodeparser import get_gcode_parameter, parse_slic3r_config
from p2pp.omega import header_generate_omega, algorithm_process_material_configuration
from p2pp.sidewipe import create_side_wipe


def optimize_tower_skip(skipmax, layersize):
    skipped = 0.0
    skipped_num = 0
    for idx in range(len(v.skippable_layer) - 1, 0, -1):
        if skipped >= skipmax:
            v.skippable_layer[idx] = False
        elif v.skippable_layer[idx]:
            skipped = skipped + layersize
            skipped_num += 1

    if skipped > 0:
        gui.log_warning("Warning: Purge Tower delta in effect: {} Layers or {:-6.2f}mm".format(skipped_num, skipped))
    else:
        gui.create_logitem("Tower Purge Delta could not be applied to this print")


def convert_to_absolute():
    absolute = 0.0

    for i in range(len(v.processed_gcode)):
        line = v.processed_gcode[i]

        if line.startswith("G1") or line.startswith("G0"):
            if "E" in line:
                fields = line.split()
                for j in range(1, len(fields)):
                    if fields[j][0] == "E":
                        to_e = float(fields[j][1:])
                        absolute += to_e
                        fields[j] = "E{:.5f}".format(absolute)
                line = " ".join(fields) + "\n"
                v.processed_gcode[i] = line
            continue

        if line.startswith("M83"):
            v.processed_gcode[i] = "M82\n"

        if line.startswith("G92 E"):
            absolute = get_gcode_parameter(line, "E")


# ################### GCODE PROCESSING ###########################
def gcode_process_toolchange(new_tool, location):
    # some commands are generated at the end to unload filament,
    # they appear as a reload of current filament - messing up things
    if new_tool == v.current_tool:
        return

    location += v.splice_offset

    if new_tool == -1:
        location += v.extra_runout_filament
        v.material_extruded_per_color[v.current_tool] += v.extra_runout_filament
        v.total_material_extruded += v.extra_runout_filament
    else:
        v.palette_inputs_used[new_tool] = True

    length = location - v.previous_toolchange_location

    if v.current_tool != -1:
        v.splice_extruder_position.append(location)
        v.splice_length.append(length)
        v.splice_used_tool.append(v.current_tool)

        if len(v.splice_extruder_position) == 1:
            if v.splice_length[0] < v.min_start_splice_length:
                gui.log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(length,
                                                                                              v.min_start_splice_length))

                filamentshortage = v.min_start_splice_length - v.splice_length[0]
                v.filament_short[new_tool] = max(v.filament_short[new_tool], filamentshortage)
        else:
            if v.splice_length[-1] < v.min_splice_length:
                gui.log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".
                                format(v.min_splice_length, length, v.current_layer, v.current_tool))
                filamentshortage = v.min_splice_length - v.splice_length[-1]
                v.filament_short[new_tool] = max(v.filament_short[new_tool], filamentshortage)

        v.previous_toolchange_location = location
    v.previous_tool = v.current_tool
    v.current_tool = new_tool


def inrange(number, low, high):
    if not number:
        return True
    if number < low or number > high:
        return False
    return True


def x_on_bed(x):
    return inrange(x, v.bed_origin_x, v.bed_origin_x + v.bed_size_x)


def coordinate_on_bed(x, y):
    return inrange(x, v.bed_origin_x, v.bed_origin_x + v.bed_size_x) and \
           inrange(y, v.bed_origin_y, v.bed_origin_y + v.bed_size_y)


def coordinate_in_tower(x, y):
    return inrange(x, v.wipe_tower_info['minx'], v.wipe_tower_info['maxx']) and \
           inrange(y, v.wipe_tower_info['miny'], v.wipe_tower_info['maxy'])

def entertower():
    if v.cur_tower_z_delta > 0:
        v.max_tower_delta = max(v.cur_tower_z_delta, v.max_tower_delta)
        v.processed_gcode.append(";------------------------------\n")
        v.processed_gcode.append(";  P2PP DELTA >> TOWER {:.2f}mm\n".format(
            v.current_position_z - v.cur_tower_z_delta - v.retract_lift[v.current_tool]))
        v.processed_gcode.append("G1 E{}\n".format(v.retract_length[v.current_tool]))
        v.processed_gcode.append(
            "G1 Z{:.2f} F10810\n".format(v.current_position_z - v.cur_tower_z_delta - v.retract_lift[v.current_tool]))
        v.processed_gcode.append("G1 E{}\n".format(-v.retract_length[v.current_tool]))
        v.processed_gcode.append(";------------------------------\n")


CLS_UNDEFINED = 0
CLS_NORMAL = 1
CLS_TOOL_START = 2
CLS_TOOL_UNLOAD = 3
CLS_TOOL_PURGE = 4
CLS_EMPTY = 5
CLS_FIRST_EMPTY = 6
CLS_BRIM = 7
CLS_BRIM_END = 8
CLS_ENDGRID = 9
CLS_COMMENT = 10
CLS_ENDPURGE = 11
CLS_TONORMAL = 99

SPEC_HOPUP = 1
SPEC_HOPDOWN = 2
SPEC_INTOWER = 16
SPEC_RETRACTS = 4
SPEC_TOOLCHANGE = 8


def update_class(gcode_line):
    v.previous_block_classification = v.block_classification
    if gcode_line.startswith("; CP"):
        if "TOOLCHANGE START" in gcode_line:
            v.block_classification = CLS_TOOL_START

        if "TOOLCHANGE UNLOAD" in gcode_line:
            v.block_classification = CLS_TOOL_UNLOAD

        if "TOOLCHANGE WIPE" in gcode_line:
            v.block_classification = CLS_TOOL_PURGE

        if "TOOLCHANGE END" in gcode_line:
            if v.previous_block_classification == CLS_TOOL_UNLOAD:
                v.block_classification = CLS_NORMAL
            else:
                v.block_classification = CLS_TONORMAL

        if "WIPE TOWER FIRST LAYER BRIM START" in gcode_line:
            v.block_classification = CLS_BRIM

        if "WIPE TOWER FIRST LAYER BRIM END" in gcode_line:
            if v.full_purge_reduction or v.tower_delta:
                v.block_classification = CLS_BRIM_END
            else:
                v.block_classification = CLS_TONORMAL

        if "EMPTY GRID START" in gcode_line:
            v.block_classification = CLS_EMPTY


        if "EMPTY GRID END" in gcode_line:
            v.block_classification = CLS_ENDGRID

        if v.block_classification == CLS_TONORMAL and v.previous_block_classification == CLS_TOOL_PURGE:
            v.block_classification = CLS_ENDPURGE

        if v.block_classification == CLS_EMPTY and v.purge_first_empty:
            v.block_classification = CLS_FIRST_EMPTY
            v.purge_first_empty = False

    return v.block_classification == v.previous_block_classification


def flagset(value, mask):
    return (value & mask) == mask


def backpass(currentclass):
    idx = len(v.parsedgcode) - 2
    end_search = max(1, v.lasthopup)
    while idx > end_search:
        tmp = v.parsedgcode[idx]
        if tmp.fullcommand == "G1" and tmp.has_parameter("E") and tmp.has_parameter("F"):
            v.gcodeclass[idx] = currentclass
            tmp = v.parsedgcode[idx - 1]
            if tmp.fullcommand == "G1" and tmp.has_parameter("Z"):
                v.gcodeclass[idx - 1] = currentclass
                tmp = v.parsedgcode[idx - 2]
                idx = idx - 1
            if tmp.fullcommand == "G1" and tmp.has_parameter("X") and tmp.has_parameter("Y") and not tmp.has_parameter(
                    "E"):
                tmp.Comment = "Part of next block"
            else:
                idx = idx + 1
            while idx <= len(v.parsedgcode) - 2:
                v.gcodeclass[idx - 1] = currentclass
                idx = idx + 1
            break
        idx = idx - 1


def parse_gcode():
    cur_z = -999
    cur_tool = 0
    retract = 0.6
    layer = -1
    toolchange = 0
    emptygrid = 0

    v.block_classification = CLS_NORMAL
    v.previous_block_classification = CLS_NORMAL
    total_line_count = len(v.input_gcode)

    index = 0
    for line in v.input_gcode:
        gui.progress_string(4 + 46 * index // total_line_count)

        specifier = 0
        v.parsedgcode.append(gcode.GCodeCommand(line))
        classupdate = False


        if line.startswith(';'):

            ## P2PP SPECIFIC SETP COMMANDS
            ########################################################
            if line.startswith(";P2PP"):
                parameters.check_config_parameters(line)

            if line.startswith(";P2PP MATERIAL_"):
                algorithm_process_material_configuration(line[15:])

            ## LAYER DISCRIMINATION COMMANDS
            ########################################################

            if line.startswith(";LAYER"):
                layer = int(line[7:])
                if layer > 0:
                    v.skippable_layer.append((emptygrid > 0) and (toolchange == 0))
                toolchange = 0
                emptygrid = 0

            ## Update block class from comments information
            #########################################################
            classupdate = update_class(line)



        if classupdate:

            if v.block_classification == CLS_TOOL_START:
                toolchange += 1

            if v.block_classification == CLS_EMPTY:
                emptygrid += 1


        ## Z-HOPS detection
        ###################
        if v.parsedgcode[-1].has_parameter("Z"):

            to_z = v.parsedgcode[-1].get_parameter("Z", 0)
            delta = (to_z - cur_z)

            if abs(delta - retract) < 0.0001:
                specifier |= SPEC_HOPUP

                if v.block_classification == CLS_TONORMAL:
                    v.previous_block_classification = v.block_classification = CLS_NORMAL

            if abs(- delta - retract) < 0.0001:
                specifier |= SPEC_HOPDOWN

            cur_z = to_z

        ## retract detections
        #####################
        if v.parsedgcode[-1].is_movement_command() and v.parsedgcode[-1].has_parameter("E"):
            if v.parsedgcode[-1].get_parameter("E", 0) < 0:
                specifier |= SPEC_RETRACTS

        ## tool change detection
        ########################
        if v.parsedgcode[-1].Command == 'T':
            cur_tool = int(v.parsedgcode[-1].Command_value)
            retract = v.retract_lift[cur_tool]
            specifier |= SPEC_TOOLCHANGE

        ## Extend block backwards towards last hop up
        #############################################


        if v.block_classification in [CLS_TOOL_START, CLS_TOOL_UNLOAD, CLS_EMPTY,
                                      CLS_BRIM] and not v.full_purge_reduction:
            backpass(v.block_classification)


        if v.block_classification in [CLS_ENDGRID, CLS_ENDPURGE]:
            if v.parsedgcode[-1].fullcommand == "G1":
                if v.parsedgcode[-1].X and v.parsedgcode[-1].Y:
                    specifier |= SPEC_INTOWER

            if flagset(specifier, SPEC_RETRACTS):
                v.block_classification = CLS_NORMAL


        ## Put obtained values in global variables
        ##########################################
        v.gcodeclass.append(v.block_classification)
        v.layernumber.append(layer)
        v.linetool.append(cur_tool)
        v.parsecomment.append(specifier)
        v.classupdates.append(v.block_classification != v.previous_block_classification)
        v.previous_block_classification = v.block_classification
        index = index + 1

        if v.block_classification == CLS_BRIM_END:
            v.block_classification = CLS_NORMAL


def update_extrusion(length):
    v.total_material_extruded += length
    v.material_extruded_per_color[v.current_tool] += length

def gcode_parseline(index):

    g = v.parsedgcode[index]
    block_class = v.gcodeclass[index]
    previous_block_class = v.gcodeclass[max(0, index - 1)]
    classupdate = block_class != previous_block_class

    if g.Command == 'T':
        gcode_process_toolchange(int(g.Command_value), v.total_material_extruded)
        g.move_to_comment("Color Change")
        g.issue_command()
        return

    if g.fullcommand in ["M104", "M106", "M109", "M140", "M190", "M73", "M900", "M84"]:
        g.issue_command()
        return

    if g.fullcommand in ["M220"]:
        g.move_to_comment("Flow Rate Adjustments are removed")
        g.issue_command()
        return

    if g.fullcommand == "M221":
        v.extrusion_multiplier = float(g.get_parameter("S", v.extrusion_multiplier * 100)) / 100
        g.issue_command()
        return

    ## ALL SITUATIONS
    ##############################################
    if block_class in [CLS_TOOL_START, CLS_TOOL_UNLOAD]:
        if v.tower_delta:
            if g.is_movement_command():
                if g.fullcommand == "G4":
                    g.move_to_comment("tool unload")
                if not (g.has_parameter("Z")):
                    g.move_to_comment("tool unload")
                else:
                    g.remove_parameter("X")
                    g.remove_parameter("Y")
                    g.remove_parameter("F")
                    g.remove_parameter("E")
        else:
            g.move_to_comment("tool unload")
        g.issue_command()
        return

    if not v.side_wipe:
        if g.X:
            if v.wipe_tower_info['minx'] <= g.X <= v.wipe_tower_info['maxx']:
                v.keep_x = g.X
        if g.Y:
            if v.wipe_tower_info['miny'] <= g.Y <= v.wipe_tower_info['maxy']:
                v.keep_y = g.Y
    elif not x_on_bed(g.X):
        g.remove_parameter("X")

    ## SIDEWIPE / FULLPURGEREDUCTION / TOWER DELTA
    ###############################################
    if v.pathprocessing:

        if block_class == CLS_TONORMAL:

            if not g.is_comment():
                g.move_to_comment("post block processing")
            g.issue_command()
            return

        if flagset(v.parsecomment[index], SPEC_INTOWER):
            if coordinate_in_tower(g.X, g.Y):
                g.Comment = "removed parms X{:.3f} and Y{:.3f}".format(g.X, g.Y)
                g.remove_parameter("X")
                g.remove_parameter("Y")


        # sepcific for FULL_PURGE_REDUCTION
        if v.full_purge_reduction:

            # get information about the purge tower dimensions
            if block_class == CLS_BRIM and not (g.X and g.Y):
                if g.X:
                    purgetower.purge_width = min(purgetower.purge_width,
                                                 abs(g.X - v.previous_position_x))
                if g.Y:
                    purgetower.purge_height = min(purgetower.purge_height,
                                                  abs(g.Y - v.previous_position_y))

            if block_class == CLS_BRIM_END:
                # generate a purge tower alternative

                _x = v.wipe_tower_info['minx'] + 4 * v.extrusion_width
                _y = v.wipe_tower_info['miny'] + 4 * v.extrusion_width
                _w = v.wipe_tower_info['maxx'] - v.wipe_tower_info['minx'] - 8 * v.extrusion_width
                _h = v.wipe_tower_info['maxy'] - v.wipe_tower_info['miny'] - 8 * v.extrusion_width

                # purgetower.purge_create_layers(v.wipetower_posx, v.wipetower_posy,
                #                                purgetower.purge_width - 2 * v.extrusion_width,
                #                                purgetower.purge_height - 2 * v.extrusion_width)
                purgetower.purge_create_layers(_x, _y, _w, _h)
                # generate og items for the new purge tower
                gui.create_logitem(
                    " Purge Tower :Loc X{:.2f} Y{:.2f}  W{:.2f} H{:.2f}".format(_x, _y, _w, _h))
                gui.create_logitem(
                    " Layer Length Solid={:.2f}mm   Sparse={:.2f}mm".format(purgetower.sequence_length_solid,
                                                                            purgetower.sequence_length_empty))
                # issue the new purge tower
                for i in purgetower.brimlayer:
                    i.issue_command()
                # set the flag to update the post-session retraction move section
                v.retract_move = True
                v.retract_x = purgetower.last_brim_x
                v.retract_y = purgetower.last_brim_y
                # correct the amount of extrusion for the brim
                update_extrusion(
                    purgetower.sequence_length_brim * v.extrusion_multiplier * v.extrusion_multiplier_correction)

        # sepcific for SIDEWIPE
        if v.side_wipe:

            # side wipe does not need a brim
            if block_class == CLS_BRIM:
                if not g.is_comment():
                    g.move_to_comment("side wipe - removed")
                g.issue_command()
                return

        # entering the purge tower with a delta
        ########################################
        if v.tower_delta:

            if classupdate:

                if block_class == CLS_TOOL_PURGE:
                    g.issue_command()
                    v.processed_gcode.append("G1 X{} Y{}\n".format(v.keep_x, v.keep_y))
                    entertower()
                    return

        # going into an empty grid -- check if it should be consolidated
        ################################################################
        if classupdate and block_class in [CLS_FIRST_EMPTY, CLS_EMPTY]:
            if v.skippable_layer[v.layernumber[index]]:
                v.towerskipped = True
                if v.tower_delta:
                    v.cur_tower_z_delta += v.layer_height
                    v.processed_gcode.append(";-------------------------------------\n")
                    v.processed_gcode.append(";  GRID SKIP --TOWER DELTA {:6.2f}mm\n".format(v.cur_tower_z_delta))
                    v.processed_gcode.append(";-------------------------------------\n")

        # changing from EMPTY to NORMAL
        ###############################
        if (previous_block_class == CLS_ENDGRID) and (block_class == CLS_NORMAL):
            v.towerskipped = False

        if v.towerskipped:
            if not g.is_comment():
                g.move_to_comment("tower skipped")
            g.issue_command()
            return
    else:
        if classupdate and block_class in [CLS_TOOL_PURGE, CLS_EMPTY] and v.acc_ping_left <= 0:
            pings.check_accessorymode_first()

    if v.tower_delta:
        if g.E and block_class in [CLS_TOOL_UNLOAD, CLS_TOOL_PURGE]:
            if not inrange(g.X, v.wipe_tower_info['minx'], v.wipe_tower_info['maxx']):
                g.remove_parameter("E")
            if not inrange(g.Y, v.wipe_tower_info['miny'], v.wipe_tower_info['maxy']):
                g.remove_parameter("E")

    # process movement commands
    ###########################

    if not g.has_parameter("E"):
        g.E = 0

    if v.full_purge_reduction and block_class == CLS_NORMAL and classupdate:
        purgetower.purge_generate_sequence()

    if g.is_movement_command():

        if v.retract_move and g.E < 0:
            g.update_parameter("X", v.retract_x)
            g.update_parameter("Y", v.retract_y)
            v.retract_move = False

        v.current_position_x = g.get_parameter("X", v.current_position_x)
        v.current_position_y = g.get_parameter("Y", v.current_position_y)
        v.current_position_z = g.get_parameter("Z", v.current_position_z)

        if block_class == CLS_BRIM:
            v.wipe_tower_info['minx'] = min(v.wipe_tower_info['minx'], v.current_position_x - 1)
            v.wipe_tower_info['miny'] = min(v.wipe_tower_info['miny'], v.current_position_y - 1)
            v.wipe_tower_info['maxx'] = max(v.wipe_tower_info['maxx'], v.current_position_x + 1)
            v.wipe_tower_info['maxy'] = max(v.wipe_tower_info['maxy'], v.current_position_y + 1)

            if v.full_purge_reduction:
                g.move_to_comment("replaced by P2PP brim code")
                g.remove_parameter("E")
                g.E = 0

        update_extrusion(g.E * v.extrusion_multiplier * v.extrusion_multiplier_correction)

    if v.side_wipe or v.full_purge_reduction:
        if block_class in [CLS_TOOL_PURGE, CLS_ENDPURGE, CLS_EMPTY, CLS_FIRST_EMPTY]:
            v.side_wipe_length += g.E
            g.move_to_comment("side wipe/full purge")

    if v.side_wipe and block_class == CLS_NORMAL and classupdate:
        create_side_wipe()

    # g.Comment = " ; - {}".format(v.total_material_extruded)
    g.issue_command()

    ### PING PROCESSING
    ###################

    if v.accessory_mode:
        pings.check_accessorymode_second(g.E)

    if g.E > 0 and v.side_wipe_length == 0:
        pings.check_connected_ping()

    v.previous_position_x = v.current_position_x
    v.previous_position_y = v.current_position_y

# Generate the file and glue it all together!
# #####################################################################
def generate(input_file, output_file, printer_profile, splice_offset, silent):
    starttime = time.time()
    v.printer_profile_string = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0].replace(" ", "_")
    _taskName = _taskName.replace(".mcf", "")

    v.splice_offset = splice_offset

    try:
        # python 3.x
        opf = open(input_file, encoding='utf-8')
    except TypeError:
        try:
            # python 2.x
            opf = open(input_file)
        except IOError:
            if v.gui:
                gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
            else:
                print ("Could not read input file\n'{}".format(input_file))
            return
    except IOError:
        if v.gui:
            gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
        else:
            print ("Could not read input file\n'{}".format(input_file))
        return

    gui.setfilename(input_file)
    gui.set_printer_id(v.printer_profile_string)
    gui.create_logitem("Reading File " + input_file)
    gui.progress_string(1)

    v.input_gcode = opf.readlines()
    opf.close()

    v.input_gcode = [item.strip() for item in v.input_gcode]

    gui.create_logitem("Analyzing slicer parameters")
    gui.progress_string(2)
    parse_slic3r_config()

    gui.create_logitem("Pre-parsing GCode")
    gui.progress_string(4)
    parse_gcode()

    if v.palette_plus:
        if v.palette_plus_ppm == -9:
            gui.log_warning("P+ parameter P+PPM not set correctly in startup GCODE")
        if v.palette_plus_loading_offset == -9:
            gui.log_warning("P+ parameter P+LOADINGOFFSET not set correctly in startup GCODE")

    v.side_wipe = not coordinate_on_bed(v.wipetower_posx, v.wipetower_posy)
    v.tower_delta = v.max_tower_z_delta > 0

    if v.side_wipe:
        gui.create_logitem("Side wipe activated", "blue")
        if v.full_purge_reduction:
            gui.log_warning("Full Purge Reduction is not compatible with Side Wipe, performing Side Wipe")
            v.full_purge_reduction = False

    if v.full_purge_reduction:
        v.side_wipe = False
        gui.create_logitem("Full Tower Reduction activated", "blue")
        if v.tower_delta:
            gui.log_warning("Full Purge Reduction is not compatible with Tower Delta, performing Full Purge Reduction")
            v.tower_delta = False

    v.pathprocessing = (v.tower_delta or v.full_purge_reduction or v.side_wipe)

    optimize_tower_skip(v.max_tower_z_delta, v.layer_height)

    gui.create_logitem("Generate processed GCode")

    total_line_count = len(v.input_gcode)
    for process_line_count in range(total_line_count):
        gcode_parseline(process_line_count)
        gui.progress_string(50 + 50 * process_line_count // total_line_count)

    if abs(v.min_tower_delta) >= min(v.retract_lift) + v.layer_height:
        gui.log_warning("Increase retraction Z hop, {:2f}mm needed to print correctly".v.retract_lift[v.current_tool])
        if abs(v.min_tower_delta) > min(v.retract_lift) + v.layer_height:
            gui.log_warning("THIS FILE WILL NOT PRINT CORRECTLY")
    v.processtime = time.time() - starttime

    gcode_process_toolchange(-1, v.total_material_extruded)
    omega_result = header_generate_omega(_taskName)
    header = omega_result['header'] + omega_result['summary'] + omega_result['warnings']

    if v.absolute_extruder and v.gcode_has_relative_e:
        gui.create_logitem("Converting to absolute extrusion")
        convert_to_absolute()

    # write the output file
    ######################

    if not output_file:
        output_file = input_file
    gui.create_logitem("Generating GCODE file: " + output_file)
    opf = open(output_file, "w")
    if not v.accessory_mode:
        opf.writelines(header)
        opf.write("\n\n;--------- START PROCESSED GCODE ----------\n\n")
    if v.accessory_mode:
        opf.write("M0\n")
        opf.write("T0\n")

    if v.splice_offset == 0:
        gui.log_warning("SPLICE_OFFSET not defined")
    opf.writelines(v.processed_gcode)
    opf.close()

    if v.accessory_mode:

        pre, ext = os.path.splitext(output_file)
        if v.palette_plus:
            maffile = pre + ".msf"
        else:
            maffile = pre + ".maf"
        gui.create_logitem("Generating PALETTE MAF/MSF file: " + maffile)
        opf = open(maffile, "w")
        for i in range(len(header)):
            if not header[i].startswith(";"):
                opf.write(header[i])

    gui.print_summary(omega_result['summary'])

    gui.progress_string(100)
    if (len(v.process_warnings) > 0 and not silent) or v.consolewait:
        gui.close_button_enable()
