__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '3.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import os
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
    if new_tool == v.currentTool:
        return

    location += v.splice_offset

    if new_tool == -1:
        location += v.extraRunoutFilament
    else:
        v.paletteInputsUsed[new_tool] = True

    length = location - v.previousToolChangeLocation

    if v.currentTool != -1:
        v.spliceExtruderPosition.append(location)
        v.spliceLength.append(length)
        v.spliceUsedTool.append(v.currentTool)

        if len(v.spliceExtruderPosition) == 1:
            if v.spliceLength[0] < v.minimalStartSpliceLength:
                log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(length,
                                                                                          v.minimalStartSpliceLength))
        else:
            if v.spliceLength[-1] < v.minimalSpliceLength:
                log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".
                            format(v.minimalSpliceLength, length, v.currentLayer, v.currentTool))

    v.previousToolChangeLocation = location
    v.currentTool = new_tool


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
                return ";--- P2PP removed "+line
        return gcode_remove_params(line, ["F"])

    if line.startswith("M907"):
        return ";--- P2PP removed " + line   # remove motor power instructions

    if line.startswith("M220"):
        return ";--- P2PP removed " + line   # remove feedrate instructions

    if line.startswith("G4 S0"):
        return ";--- P2PP removed " + line   # remove dwelling instructions

    return line


def CoordinateOnBed(x,y):
    return (x >= v.bed_origin_x and x <= v.bed_origin_x+v.bed_size_x and y >= v.bed_origin_y and y <= v.bed_origin_y+v.bed_size_y)


def moved_in_tower():
    return not CoordinateOnBed(v.currentPositionX ,v.currentPositionY)


def gcode_parseline(gcode_fullline):

    __tower_remove = False

    if not gcode_fullline[0] == ";":
        gcode_fullline = gcode_fullline.split(';')[0]

    gcode_fullline = gcode_fullline.rstrip('\n')

    if gcode_fullline == "":
        v.processedGCode.append("\n")
        return


    if gcode_fullline.startswith('T'):
        new_tool = int(gcode_fullline[1])
        gcode_process_toolchange(new_tool, v.totalMaterialExtruded)
        v.allowFilamentInformationUpdate = True
        v.processedGCode.append(';--- P2PP removed ' + gcode_fullline+"\n")
        return

    if v.side_wipe:
        sidewipe.collect_wipetower_info(gcode_fullline)

        if v.side_wipe_skip:
            v.processedGCode.append(";--- P2PP sremoved "+gcode_fullline+"\n")
            return

        if moved_in_tower() and v.side_wipe and not v.side_wipe_skip:
            if not gcode_fullline[0] == ";":
                v.processedGCode.append(";--- P2PP  - Purge Tower - " + gcode_fullline + "\n")
            gcode_fullline = gcode_remove_params(gcode_fullline, ["X", "Y"])
            __tower_remove = True

    # Processing of extrusion speed commands
    # ############################################
    if gcode_fullline.startswith("M220"):
        new_feedrate = get_gcode_parameter(gcode_fullline, "S")
        if new_feedrate != "":
            v.currentprintFeedrate = new_feedrate / 100

    # Processing of extrusion multiplier commands
    # ############################################
    if gcode_fullline.startswith("M221"):
        new_multiplier = get_gcode_parameter(gcode_fullline, "S")
        if new_multiplier != "":
            v.extrusionMultiplier = new_multiplier / 100

    # Processing of print head movements
    #############################################

    if gcode_fullline.startswith("G"):
        toX = get_gcode_parameter(gcode_fullline, "X")
        toY = get_gcode_parameter(gcode_fullline, "Y")
        prevx = v.currentPositionX
        prevy = v.currentPositionY
        if toX != "":
            v.currentPositionX = float(toX)
        if toY != "":
            v.currentPositionY = float(toY)
        if not CoordinateOnBed(v.currentPositionX, v.currentPositionY) and CoordinateOnBed(prevx, prevy):
            gcode_fullline = ";"+gcode_fullline

    if gcode_fullline.startswith("G1"):
            extruder_movement = get_gcode_parameter(gcode_fullline, "E")
            if extruder_movement != "":
                extruder_movement = extruder_movement * v.extrusionMultiplier
                if v.withinToolchangeBlock and v.side_wipe:
                        v.side_wipe_length += extruder_movement

                v.totalMaterialExtruded += extruder_movement

                if (v.totalMaterialExtruded - v.lastPingExtruderPosition) > v.pingIntervalLength and\
                        v.side_wipe_length == 0:
                    v.pingIntervalLength = v.pingIntervalLength * v.pingLengthMultiplier
                    v.pingIntervalLength = min(v.maxPingIntervalLength, v.pingIntervalLength)
                    v.lastPingExtruderPosition = v.totalMaterialExtruded
                    v.pingExtruderPosition.append(v.lastPingExtruderPosition)
                    v.processedGCode.append(";Palette 2 - PING\n")
                    v.processedGCode.append("G4 S0\n")
                    v.processedGCode.append("O31 {}\n".format(hexify_float(v.lastPingExtruderPosition)))

            if v.withinToolchangeBlock and v.side_wipe:
                if not __tower_remove:
                    v.processedGCode.append(';--- P2PP removed ' + gcode_fullline+"\n")
                return

            if not v.withinToolchangeBlock and v.wipeRetracted:
                sidewipe.unretract()

    # Other configuration information
    # this information should be defined in your Slic3r printer settings, startup GCode
    ###################################################################################
    if gcode_fullline.startswith(";P2PP"):
        parameters.check_config_parameters(gcode_fullline)
        v.side_wipe = not CoordinateOnBed(v.wipetower_posx, v.wipetower_posy)

        if gcode_fullline.startswith(";P2PP MATERIAL_"):
                algorithm_process_material_configuration(gcode_fullline[15:])

    if gcode_fullline.startswith("M900"):
        k_factor = get_gcode_parameter(gcode_fullline, "K")
        if int(k_factor) > 0:
            sidewipe.create_side_wipe()
            v.withinToolchangeBlock = False
            v.mmu_unload_remove = False

    if gcode_fullline.startswith(";P2PP ENDPURGETOWER"):
        sidewipe.create_side_wipe()
        v.withinToolchangeBlock = False
        v.mmu_unload_remove = False

    # Next section(s) clean up the GCode generated for the MMU
    # specially the rather violent unload/reload required for the MMU2
    # special processing for side wipes is required in this section
    #################################################################

    if "TOOLCHANGE START" in gcode_fullline:
        v.allowFilamentInformationUpdate = False
        v.withinToolchangeBlock = True
        sidewipe.sidewipe_toolchange_start()

    if ("TOOLCHANGE END" in gcode_fullline) and not v.side_wipe:
        v.withinToolchangeBlock = False
        v.mmu_unload_remove = False

    if "TOOLCHANGE UNLOAD" in gcode_fullline and not v.side_wipe:
        v.currentprintFeed = v.wipeFeedRate / 60.0
        v.mmu_unload_remove = True
        v.processedGCode.append(";P2PP Set wipe speed to {}mm/s\n".format(v.currentprintFeed))
        v.processedGCode.append("G1 F{}\n".format(v.wipeFeedRate))


    if "TOOLCHANGE WIPE" in gcode_fullline:
        v.mmu_unload_remove = False
        if CoordinateOnBed(v.currentPositionX, v.currentPositionY):
            v.processedGCode.append("G0 X{} Y{}\n".format(v.currentPositionX, v.currentPositionY))

        # Layer Information
    if gcode_fullline.startswith(";LAYER "):
        v.currentLayer = gcode_fullline[7:]

    if v.mmu_unload_remove :
            v.processedGCode.append(gcode_filter_toolchange_block(gcode_fullline)+"\n")
            return

    if v.withinToolchangeBlock:
        v.processedGCode.append(gcode_filter_toolchange_block(gcode_fullline) + "\n")
        return

    # Catch All
    v.processedGCode.append(gcode_fullline+"\n")


# Generate the file and glue it all together!
# #####################################################################
def generate(input_file, output_file, printer_profile, splice_offset, silent):
    v.printerProfileString = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0].replace(" ","_")
    _taskName = _taskName.replace(".mcf","")


    v.splice_offset = splice_offset

    try:
        opf = open(input_file, encoding='utf-8')
    except:
        try:
            opf = open(input_file)
        except:
            gui.user_error("Could'nt read input file\n'{}'".format(input_file))
            exit(1)

    v.inputGcode = opf.readlines()

    opf.close()

    parse_slic3r_config()

    v.side_wipe = not CoordinateOnBed(v.wipetower_posx, v.wipetower_posy)

    # Process the file
    # #################
    for line in v.inputGcode:
        gcode_parseline(line)

    gcode_process_toolchange(-1, v.totalMaterialExtruded)
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
    opf.writelines(v.processedGCode)
