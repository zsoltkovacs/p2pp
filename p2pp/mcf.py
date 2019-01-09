__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '1.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import os
import p2pp.gui as gui
from p2pp.formatnumbers import hexify_short, hexify_long, hexify_float
from p2pp.colornames import findNearestColor
import p2pp.variables as v


# ################################################################
# ######################### COMPOSE WARNING BLOCK ################
# ################################################################
def log_warning(text):
    v.processWarnings.append(";" + text)


# ################################################################
# ######################### ALGORITHM PROCESSING ################
# ################################################################

def algorithm_createprocessstring(heating, compression, cooling):
    return "{} {} {}".format(hexify_short(int(heating)),
                             hexify_short(int(compression)),
                             hexify_short(int(cooling))
                             )


def algorithm_processmaterialconfiguration(splice_info):
    fields = splice_info.split("_")
    numfields = len(fields)

    if fields[0] == "DEFAULT" and numfields == 4:
        v.defaultSpliceAlgorithm = algorithm_createprocessstring(fields[1],
                                                                 fields[2],
                                                                 fields[3])

    if numfields == 5:
        key = "{}-{}".format(fields[0],
                             fields[1])
        v.spliceAlgorithmDictionary[key] = algorithm_createprocessstring(fields[2],
                                                                         fields[3],
                                                                         fields[4])


def algorithm_createtable():
    for i in range(4):
        for j in range(4):
            if i==j:
                continue
            if not v.paletteInputsUsed[i] or not v.paletteInputsUsed[j]:
                continue
            try:
                algo = v.spliceAlgorithmDictionary["{}-{}".format(v.filamentType[i], v.filamentType[j])]
            except KeyError:
                log_warning("WARNING: No Algorithm defined for transitioning {} to {}. Using Default".format(v.filamentType[i],
                                                                                                             v.filamentType[j]))
                algo = v.defaultSpliceAlgorithm

            v.spliceAlgorithmTable.append("D{}{} {}".format(i + 1,
                                                            j + 1,
                                                            algo
                                                            )
                                          )


# Generate the Omega - Header that drives the Palette to generate filament
def header_generateomegaheader(job_name, splice_offset):

    if v.printerProfileString == '':
        log_warning("Printerprofile identifier is missing, add \n;P2PP PRINTERPROFILE=<your printer profile ID> to the Printer Start GCode block\n")
    if len(v.spliceExtruderPosition) == 0:
        log_warning("This does not look lie a multi color file......\n")

    algorithm_createtable()

    header = []
    summary = []
    warnings = []
    header.append('O21 ' + hexify_short(20) + "\n")  # MSF2.0
    header.append('O22 D' + v.printerProfileString.strip("\n") + "\n")  # printerprofile used in Palette2
    header.append('O23 D0001' + "\n")              # unused
    header.append('O24 D0000' + "\n")              # unused

    header.append("O25 ")

    for i in range(4):
        if v.paletteInputsUsed[i]:
            if v.filamentType[i] == "":
                log_warning(
                    "Filament #{} is missing Material Type, make sure to add ;P2PP FT=[filament_type] to filament GCode".format(
                        i))
            if v.filemantDescription[i] == "Unnamed":
                log_warning(
                    "Filament #{} is missing job_name, make sure to add ;P2PP FN=[filament_preset] to filament GCode".format(
                        i))
            if v.filemantDescription[i] == "-":
                log_warning(
                    "Filament #{} is missing Color info, make sure to add ;P2PP FC=[extruder_colour] to filament GCode".format(
                        i))
                v.filemantDescription[i] = '000000'

            header.append("D{}{}{}_{} ".format(i + 1,
                                            v.filamentColorCode[i].strip("\n"),
                                            findNearestColor(v.filamentColorCode[i].strip("\n")),
                                            v.filemantDescription[i].strip("\n")
                                            ))
        else:
            header.append("D0 ")

    header.append("\n")

    header.append('O26 ' + hexify_short(len(v.spliceExtruderPosition)) + "\n")
    header.append('O27 ' + hexify_short(len(v.pingExtruderPosition)) + "\n")
    header.append('O28 ' + hexify_short(len(v.spliceAlgorithmTable)) + "\n")
    header.append('O29 ' + hexify_short(v.hotSwapCount) + "\n")

    for i in range(len(v.spliceExtruderPosition)):
        header.append("O30 D{:0>1d} {}\n".format(v.spliceUsedTool[i],
                                                 hexify_float(v.spliceExtruderPosition[i])
                                                 )
                      )

    for i in range(len(v.spliceAlgorithmTable)):
        header.append("O32 {}\n".format(v.spliceAlgorithmTable[i]))

    if len(v.spliceExtruderPosition) > 0:
        header.append("O1 D{} {}\n".format(job_name, hexify_float(v.spliceExtruderPosition[-1])))
    else:
        header.append("O1 D{} {}\n".format(job_name, hexify_float(v.totalMaterialExtruded + splice_offset)))

    header.append("M0\n")
    header.append("T0\n")

    summary.append(";------------------:\n")
    summary.append(";SPLICE INFORMATION:\n")
    summary.append(";------------------:\n")
    summary.append(";       Splice Offset = {:-8.2f}mm\n\n".format(splice_offset))

    for i in range(len(v.spliceExtruderPosition)):
        summary.append(";{:04}   Tool: {}  Location: {:-8.2f}mm   length {:-8.2f}mm \n".format(i + 1,
                                                                                               v.spliceUsedTool[i],
                                                                                               v.spliceExtruderPosition[i],
                                                                                               v.spliceLength[i],
                                                                                               )
                       )

    summary.append("\n")
    summary.append(";------------------:\n")
    summary.append(";PING  INFORMATION:\n")
    summary.append(";------------------:\n")

    for i in range(len(v.pingExtruderPosition)):
        summary.append(";Ping {:04} at {:-8.2f}mm\n".format(i + 1,
                                                            v.pingExtruderPosition[i]
                                                            )
                       )

    warnings.append("\n")
    warnings.append(";------------------:\n")
    warnings.append(";PROCESS WARNINGS:\n")
    warnings.append(";------------------:\n")

    if len(v.processWarnings) == 0:
        warnings.append(";None\n")
    else:
        for i in range(len(v.processWarnings)):
            warnings.append("{}\n".format(v.processWarnings[i]))
        gui.show_warnings(warnings)

    return {'header': header, 'summary': summary, 'warnings': warnings}


# ################### GCODE PROCESSING ###########################
def gcode_processtoolchange(new_tool, location, splice_offset):

    # some commands are generated at the end to unload filament, they appear as a reload of current filament - messing up things
    if new_tool == v.currentTool:
        return

    location += splice_offset

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
                log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(length, v.minimalStartSpliceLength))
        else:
            if v.spliceLength[-1] < v.minimalSpliceLength:
                log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".format(v.minimalSpliceLength, length, v.currentLayer, v.currentTool))

    v.previousToolChangeLocation = location
    v.currentTool = new_tool


# Gcode remove speed information from a G1 statement
def gcode_removespeedinfo(gcode):
    result = ""
    parts = gcode.split(" ")

    for subcommand in parts:
        if subcommand == "":
            continue
        if subcommand[0] != "F":
            result += subcommand+" "

    if len(result) < 4:
        return ";--- P2PP Removed "+gcode

    return result


def gcode_filtertoolchangeblock(line, gcode_command_2, gcode_command_4):
    # --------------------------------------------------------------
    # Do not perform this part of the GCode for MMU filament unload
    # --------------------------------------------------------------
    discarded_moves = ["E-15.0000",
                       "G1 E10.5000",
                       "G1 E3.0000",
                       "G1 E1.5000"
                       ]

    if gcode_command_2 == "G1":
        for gcode_filter in discarded_moves:
            if gcode_filter in line:         # remove specific MMU2 extruder moves
                return ";--- P2PP removed "+line
        return gcode_removespeedinfo(line)

    if gcode_command_4 == "M907":
        return ";P2PP removed " + line   # remove motor power instructions

    if gcode_command_4 == "M220":
        return ";--- P2PP removed " + line   # remove feedrate instructions

    if line.startswith("G4 S0"):
        return ";--- P2PP removed " + line   # remove dwelling instructions

    return line


def get_gcode_parameter(gcode, parameter):
    fields = gcode.split()
    for parm in fields:
        if parm[0] == parameter:
            return float(parm[1:])
    return ""



# G Code parsing routine
def gcode_parseline(splice_offset, gcode_fullline):

    if not gcode_fullline[0] == ";":
        gcode_fullline = gcode_fullline.split(';')[0]
        gcode_fullline = gcode_fullline.rstrip('\n')

    if len(gcode_fullline) < 2 or gcode_fullline.startswith("M73") or gcode_fullline.startswith("M900"):
        return {'gcode': gcode_fullline, 'splice_offset': splice_offset}

    gcode_command2 = gcode_fullline[0:2]
    gcode_command4 = gcode_fullline[0:4]


    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM START") or \
       gcode_fullline.startswith("; CP EMPTY GRID START"):
        if not v.withinToolchangeBlock:
            v.side_wipe_skip = v.side_wipe

    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM END") or \
       gcode_fullline.startswith("; CP EMPTY GRID END"):
       v.side_wipe_skip = False

    if v.side_wipe_skip == True:
        return {'gcode': ";--- P2PP removed "+gcode_fullline , 'splice_offset': splice_offset}

    # Processing of extrusion speed commands
    # ############################################
    if gcode_command4 == "M220":
        new_feedrate = get_gcode_parameter(gcode_fullline, "S")
        if new_feedrate != "":
            v.currentprintFeedrate = new_feedrate / 100

    # Processing of extrusion multiplier commands
    # ############################################
    if gcode_command4 == "M221":
        new_multiplier = get_gcode_parameter(gcode_fullline, "S")
        if new_multiplier != "":
            v.extrusionMultiplier = new_multiplier / 100

    # Processing of Extruder Movement commands
    # and generating ping at threshold intervals
    # ############################################
    if gcode_command2 == "G1":

            extruder_movement = get_gcode_parameter(gcode_fullline, "E")

            if extruder_movement != "":

                if v.withinToolchangeBlock:
                    if v.side_wipe:
                        v.side_wipe_length += extruder_movement * v.extrusionMultiplier

                actual_extrusion_length = extruder_movement * v.extrusionMultiplier
                v.totalMaterialExtruded += actual_extrusion_length

                if (v.totalMaterialExtruded - v.lastPingExtruderPosition) > v.pingIntervalLength:
                    v.pingIntervalLength = v.pingIntervalLength * v.pingLengthMultiplier

                    v.pingIntervalLength = min(v.maxPingIntervalLength, v.pingIntervalLength)

                    v.lastPingExtruderPosition = v.totalMaterialExtruded
                    v.pingExtruderPosition.append(v.lastPingExtruderPosition)
                    v.processedGCode.append(";Palette 2 - PING\n")
                    v.processedGCode.append("G4 S0\n")
                    v.processedGCode.append("O31 {}\n".format(hexify_float(v.lastPingExtruderPosition)))
                    # processedGCode.append("M117 PING {:03} {:-8.2f}mm]\n".format(len(pingExtruderPosition), lastPingExtruderPosition))

    # Process Toolchanges. Build up the O30 table with Splice info
    ##############################################################
    if gcode_fullline[0] == 'T':
        new_tool = int(gcode_fullline[1])
        gcode_processtoolchange(new_tool, v.totalMaterialExtruded, splice_offset)
        v.allowFilamentInformationUpdate = True
        return {'gcode': ';--- P2PP removed ' + gcode_fullline, 'splice_offset': splice_offset}

    # Build up the O32 table with Algo info
    #######################################
    if gcode_fullline.startswith(";P2PP FT=") and v.allowFilamentInformationUpdate:  # filament type information
        v.filamentType[v.currentTool] = gcode_fullline[9:].strip("\n")

    if gcode_fullline.startswith(";P2PP FN=") and v.allowFilamentInformationUpdate:  # filament color information
        p2ppinfo = gcode_fullline[9:].strip("\n-+!@#$%^&*(){}[];:\"\',.<>/?").replace(" ", "_")
        v.filemantDescription[v.currentTool] = p2ppinfo

    if gcode_fullline.startswith(";P2PP FC=#") and v.allowFilamentInformationUpdate:  # filament color information
        p2ppinfo = gcode_fullline[10:]
        v.filamentColorCode[v.currentTool] = p2ppinfo

    # Other configuration information
    # this information should be defined in your Slic3r printer settings, startup GCode
    ###################################################################################
    if gcode_fullline.startswith(";P2PP PRINTERPROFILE=") and v.printerProfileString == '':   # -p takes precedence over printer defined in file
        v.printerProfileString = gcode_fullline[21:]

    if gcode_fullline.startswith(";P2PP SPLICEOFFSET="):
        splice_offset = float(gcode_fullline[19:])

    if gcode_fullline.startswith(";P2PP SIDEWIPELOC="):
        v.side_wipe_loc = gcode_fullline[18:].strip("\n")
        v.side_wipe = True
        #log_warning("Using the experimental Side Transition featue")

    if gcode_fullline.startswith(";P2PP EXTRAENDFILAMENT="):
        v.extraRunoutFilament = float(gcode_fullline[23:])

    if gcode_fullline.startswith(";P2PP MINSTARTSPLICE="):
        v.minimalStartSpliceLength = float(gcode_fullline[21:])
        if v.minimalStartSpliceLength < 100:
            v.minimalStartSpliceLength = 100

    if gcode_fullline.startswith(";P2PP MINSPLICE="):
        v.minimalSpliceLength = float(gcode_fullline[16:])
        if v.minimalSpliceLength < 40:
            v. minimalSpliceLength = 40

    if gcode_fullline.startswith(";P2PP MATERIAL_"):
        algorithm_processmaterialconfiguration(gcode_fullline[15:])

    # Next section(s) clean up the GCode generated for the MMU
    # specially the rather violent unload/reload required for the MMU2
    # special processing for side wipes is required in this section
    #################################################################

    if "TOOLCHANGE START" in gcode_fullline:
        v.allowFilamentInformationUpdate = False
        v.withinToolchangeBlock = True
        if v.side_wipe:
            v.side_wipe_length = 0
            v.wipe_start_extrusion= v.totalMaterialExtruded

    if ("TOOLCHANGE END" in gcode_fullline) and not v.side_wipe:
        v.withinToolchangeBlock = False

    if ("PURGING FINISHED" in gcode_fullline) and  v.withinToolchangeBlock and v.side_wipe:
        if v.side_wipe_length>0:
            v.processedGCode.append(";P2PP Side Wipe\n")
            v.processedGCode.append("G1 {} Y25\n".format(v.side_wipe_loc))
            wipespeed = int(25000/(v.side_wipe_length))
            wipespeed = min( wipespeed, 2000)
            v.processedGCode.append("G1 {} Y175 E{} F{}\n".format(v.side_wipe_loc, v.side_wipe_length, wipespeed ))
            v.processedGCode.append("G1 X245 F200\n")
            v.processedGCode.append(";Side Wipe Check {} - {} = {} (purged {})\n".format(v.totalMaterialExtruded,v.wipe_start_extrusion, v.totalMaterialExtruded-v.wipe_start_extrusion, v.side_wipe_length))
            v.side_wipe_length = 0
        v.withinToolchangeBlock = False

    if "TOOLCHANGE UNLOAD" in gcode_fullline and not  v.side_wipe:
        v.processedGCode.append(";P2PP Set Wipe Speed\n")
        v.processedGCode.append("G1 F2000\n")
        v.currentprintFeed = 2000.0 / 60.0

    # Layer Information
    if gcode_fullline.startswith(";LAYER "):
        v.currentLayer = gcode_fullline[7:]
        return {'gcode': gcode_fullline, 'splice_offset': splice_offset}

    if v.withinToolchangeBlock:
        return {'gcode': gcode_filtertoolchangeblock(gcode_fullline, gcode_command2, gcode_command4), 'splice_offset': splice_offset}

    # Catch All
    return {'gcode': gcode_fullline, 'splice_offset': splice_offset}


# Generate the file and glue it all together!
# #####################################################################
def generate(input_file, output_file, printer_profile, splice_offset, silent):


    v.printerProfileString = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0]

    try:
        opf = open(input_file, encoding='utf-8')
    except:
        try:
            opf = open(input_file)
        except:
            gui.usererror("Could read input file\n'{}'".format(input_file))
            exit(1)


    gcode_file = opf.readlines()

    opf.close()

    # Process the file
    # #################
    for line in gcode_file:
        result = gcode_parseline(splice_offset, line)
        splice_offset = float(result['splice_offset'])
        v.processedGCode.append(result['gcode'] + "\n")


    gcode_processtoolchange(-1, v.totalMaterialExtruded, splice_offset)
    omega_result = header_generateomegaheader(_taskName, splice_offset)
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

