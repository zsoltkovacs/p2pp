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
import p2pp.variables as vars




#################################################################
########################## COMPOSE WARNING BLOCK ################
#################################################################

def log_warning(text):
    vars.processWarnings.append(";"+text)


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
        vars.defaultSpliceAlgorithm = algorithm_createprocessstring(fields[1],
                                                               fields[2],
                                                               fields[3])

    if numfields == 5:
        key = "{}-{}".format(fields[0],
                             fields[1])
        vars.spliceAlgorithmDictionary[key] = algorithm_createprocessstring(fields[2],
                                                                       fields[3],
                                                                       fields[4])


def algorithm_createtable():
    for i in range(4):
        for j in range(4):
            if  not vars.paletteInputsUsed[i] or not vars.paletteInputsUsed[j]:
                continue
            try:
                algo =  vars.spliceAlgorithmDictionary["{}-{}".format(vars.filamentType[i],
                                                                      vars.filamentType[j])]
            except:
                log_warning("WARNING: No Algorithm defined for transitioning {} to {}. Using Default".format(vars.filamentType[i],
                                                                                                             vars.filamentType[j]))
                algo =  vars.defaultSpliceAlgorithm

            vars.spliceAlgorithmTable.append("D{}{} {}".format(i + 1,
                                                          j + 1,
                                                          algo
                                                          )
                                        )



# Generate the Omega - Header that drives the Palette to generate filament
def header_generateomegaheader(Name, splice_offset):

    if vars.printerProfileString == '':
        log_warning("Printerprofile identifier is missing, add \n;P2PP PRINTERPROFILE=<your printer profile ID> to the Printer Start GCode block\n")
    if len(vars.spliceExtruderPosition) == 0:
        log_warning("This does not look lie a multi color file......\n")

    algorithm_createtable()

    header = []
    summary = []
    warnings = []
    header.append('O21 ' + hexify_short(20) + "\n")  # MSF2.0
    header.append('O22 D' + vars.printerProfileString + "\n")  # printerprofile used in Palette2
    header.append('O23 D0001' + "\n")              # unused
    header.append('O24 D0000' + "\n")              # unused

    header.append("O25 ")

    for i in range(4):
        if vars.paletteInputsUsed[i]:
            if vars.filamentType[i] == "":
                log_warning(
                    "Filament #{} is missing Material Type, make sure to add ;P2PP FT=[filament_type] to filament GCode".format(
                        i))
            if vars.filemantDescription[i] == "Unnamed":
                log_warning(
                    "Filament #{} is missing Name, make sure to add ;P2PP FN=[filament_preset] to filament GCode".format(
                        i))
            if vars.filemantDescription[i] == "-":
                log_warning(
                    "Filament #{} is missing Color info, make sure to add ;P2PP FC=[extruder_colour] to filament GCode".format(
                        i))
                vars.filemantDescription[i] = '000000'

            header.append( "D{}{}{} ".format(i + 1,
                                    vars.filamentColorCode[i],
                                    vars.filemantDescription[i]
                                        ))
        else:
            header.append( "D0 " )

    header.append( "\n")

    header.append('O26 ' + hexify_short(len(vars.spliceExtruderPosition)) + "\n")
    header.append('O27 ' + hexify_short(len(vars.pingExtruderPosition)) + "\n")
    header.append('O28 ' + hexify_short(len(vars.spliceAlgorithmTable)) + "\n")
    header.append('O29 ' + hexify_short(vars.hotSwapCount) + "\n")

    for i in range(len(vars.spliceExtruderPosition)):
        header.append("O30 D{:0>1d} {}\n".format(vars.spliceUsedTool[i],
                                                 hexify_float(vars.spliceExtruderPosition[i])
                                                 )
                      )

    for i in range(len(vars.spliceAlgorithmTable)):
        header.append("O32 {}\n".format(vars.spliceAlgorithmTable[i]))

    if len(vars.spliceExtruderPosition) > 0:
        header.append("O1 D{} {}\n".format(Name, hexify_float(vars.spliceExtruderPosition[-1])))
    else:
        header.append("O1 D{} {}\n".format(Name, hexify_float(vars.totalMaterialExtruded + splice_offset)))

    header.append("M0\n")
    header.append("T0\n")

    summary.append(";------------------:\n")
    summary.append(";SPLICE INFORMATION:\n")
    summary.append(";------------------:\n")
    summary.append(";       Splice Offset = {:-8.2f}mm\n\n".format(splice_offset))

    for i in range(len(vars.spliceExtruderPosition)):
        summary.append(";{:04}   Tool: {}  Location: {:-8.2f}mm   length {:-8.2f}mm \n".format(i + 1,
                                                                                               vars.spliceUsedTool[i],
                                                                                               vars.spliceExtruderPosition[i],
                                                                                               vars.spliceLength[i],
                                                                                      )
                      )

    summary.append("\n")
    summary.append(";------------------:\n")
    summary.append(";PING  INFORMATION:\n")
    summary.append(";------------------:\n")

    for i in range(len(vars.pingExtruderPosition)):
        summary.append(";Ping {:04} at {:-8.2f}mm\n".format(i + 1,
                                                            vars.pingExtruderPosition[i]
                                                           )
                       )

    warnings.append("\n")
    warnings.append(";------------------:\n")
    warnings.append(";PROCESS WARNINGS:\n")
    warnings.append(";------------------:\n")

    if len(vars.processWarnings) == 0:
        warnings.append(";None\n")
    else:
        for i in range(len(vars.processWarnings)):
            warnings.append("{}\n".format(vars.processWarnings[i]))
        gui.showwarnings(warnings)


    return {'header': header, 'summary': summary, 'warnings': warnings}


#################### GCODE PROCESSING ###########################

def gcode_processtoolchange(newTool, Location, splice_offset):

    # some commands are generated at the end to unload filament, they appear as a reload of current filament - messing up things
    if newTool == vars.currentTool:
        return

    Location += splice_offset


    if newTool == -1:
        Location += vars.extraRunoutFilament
    else:
        vars.paletteInputsUsed[newTool] = True

    Length = Location - vars.previousToolChangeLocation

    if vars.currentTool != -1:
        vars.spliceExtruderPosition.append(Location)
        vars.spliceLength.append(Length)
        vars.spliceUsedTool.append(vars.currentTool)


        if len(vars.spliceExtruderPosition)==1:
            if vars.spliceLength[0] < vars.minimalStartSpliceLength:
                log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(Length, vars.minimalStartSpliceLength))
        else:
            if vars.spliceLength[-1] < vars.minimalSpliceLength:
                log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".format(vars.minimalSpliceLength, Length, vars.currentLayer, currentTool))

    vars.previousToolChangeLocation = Location
    vars.currentTool = newTool

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
        return ";P2PP Removed "+gcode

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
                return ";P2PP removed "+line
        return gcode_removespeedinfo(line)

    if gcode_command_4 == "M907":
        return ";P2PP removed " + line   # remove motor power instructions

    if gcode_command_4 == "M220":
        return ";P2PP removed " + line   # remove feedrate instructions

    if line.startswith("G4 S0"):
        return ";P2PP removed " + line   # remove dwelling instructions

    return line


def get_gcode_parameter(gcode, parameter):
    fields = gcode.split()
    for parm in fields:
        if parm[0] == parameter:
            return float(parm[1:])
    return ""


# G Code parsing routine
def gcode_parseline(splice_offset, gcodeFullLine):


    if not gcodeFullLine[0]==";":
        gcodeFullLine = gcodeFullLine.split(';')[0]

    gcodeFullLine = gcodeFullLine.rstrip('\n')

    if len(gcodeFullLine) < 2:
        return {'gcode': gcodeFullLine, 'splice_offset': splice_offset}


    gcodeCommand2 = gcodeFullLine[0:2]
    gcodeCommand4 = gcodeFullLine[0:4]


    # Processing of extrusion speed commands
    #############################################
    if gcodeCommand4 == "M220":
        newFeedrate = get_gcode_parameter(gcodeFullLine, "S")
        if (newFeedrate != ""):
            currentprintFeedrate = newFeedrate/100


    # Processing of extrusion multiplier commands
    #############################################
    if gcodeCommand4 == "M221":
        newMultiplier = get_gcode_parameter(gcodeFullLine , "S")
        if (newMultiplier != ""):
            extrusionMultiplier = newMultiplier/100

    # Processing of Extruder Movement commands
    # and generating ping at threshold intervals
    #############################################


    if gcodeCommand2 == "G1":

            extruderMovement = get_gcode_parameter(gcodeFullLine, "E")

            if extruderMovement != "":

                vars.actualExtrusionLength =  extruderMovement * vars.extrusionMultiplier
                vars.totalMaterialExtruded += vars.actualExtrusionLength

                if (vars.totalMaterialExtruded - vars.lastPingExtruderPosition) > vars.pingIntervalLength:
                    vars.pingIntervalLength = vars.pingIntervalLength * vars.pingLengthMultiplier

                    vars.pingIntervalLength = min(vars.maxPingIntervalLength, vars.pingIntervalLength)

                    vars.lastPingExtruderPosition = vars.totalMaterialExtruded
                    vars.pingExtruderPosition.append(vars.lastPingExtruderPosition)
                    vars.processedGCode.append(";Palette 2 - PING\n")
                    vars.processedGCode.append("G4 S0\n")
                    vars.processedGCode.append("O31 {}\n".format(hexify_float(vars.lastPingExtruderPosition)))
                    # processedGCode.append("M117 PING {:03} {:-8.2f}mm]\n".format(len(pingExtruderPosition), lastPingExtruderPosition))

    # Process Toolchanges. Build up the O30 table with Splice info
    ##############################################################
    if gcodeFullLine[0] == 'T':
        newTool = int(gcodeFullLine[1])
        gcode_processtoolchange(newTool, vars.totalMaterialExtruded, splice_offset)
        vars.allowFilamentInformationUpdate = True
        return {'gcode': ';P2PP removed ' + gcodeFullLine, 'splice_offset': splice_offset}

    # Build up the O32 table with Algo info
    #######################################
    if gcodeFullLine.startswith(";P2PP FT=") and vars.allowFilamentInformationUpdate:  # filament type information
        vars.filamentType[vars.currentTool] = gcodeFullLine[9:]

    if gcodeFullLine.startswith(";P2PP FN=") and vars.allowFilamentInformationUpdate:  # filament color information
        p2ppinfo = gcodeFullLine[9:].strip("\n-+!@#$%^&*(){}[];:\"\',.<>/?").replace(" ", "_")
        vars.filemantDescription[vars.currentTool] = p2ppinfo

    if gcodeFullLine.startswith(";P2PP FC=#") and vars.allowFilamentInformationUpdate:  # filament color information
        p2ppinfo = gcodeFullLine[10:]
        vars.filamentColorCode[vars.currentTool] = p2ppinfo

    # Other configuration information
    # this information should be defined in your Slic3r printer settings, startup GCode
    ###################################################################################
    if gcodeFullLine.startswith(";P2PP PRINTERPROFILE=") and vars.printerProfileString == '':   # -p takes precedence over printer defined in file
        vars.printerProfileString = gcodeFullLine[21:]

    if gcodeFullLine.startswith(";P2PP SPLICEOFFSET="):
        splice_offset = float(gcodeFullLine[19:])

    if gcodeFullLine.startswith(";P2PP MINSTARTSPLICE="):
        vars.minimalStartSpliceLength = float(gcodeFullLine[21:])
        if vars.minimalStartSpliceLength < 100:
            vars.minimalStartSpliceLength = 100

    if gcodeFullLine.startswith(";P2PP MINSPLICE="):
        vars.minimalSpliceLength = float(gcodeFullLine[16:])
        if vars.minimalSpliceLength < 40:
            vars. minimalSpliceLength = 40

    if gcodeFullLine.startswith(";P2PP MATERIAL_"):
        algorithm_processmaterialconfiguration(gcodeFullLine[15:])

    # Next section(s) clean up the GCode generated for the MMU
    # specially the rather violent unload/reload required for the MMU2
    ###################################################################
    if "TOOLCHANGE START" in gcodeFullLine:
        vars.allowFilamentInformationUpdate = False
        vars.withinToolchangeBlock = True
    if "TOOLCHANGE END" in gcodeFullLine:
        vars.withinToolchangeBlock = False
    if "TOOLCHANGE UNLOAD" in gcodeFullLine:
        vars.processedGCode.append(";P2PP Set Wipe Speed\n")
        vars.processedGCode.append("G1 F2000\n")
        vars.currentprintFeed = 2000.0/60.0

    # Layer Information
    if gcodeFullLine.startswith(";LAYER "):
        vars.currentLayer = gcodeFullLine[7:]
        return {'gcode': gcodeFullLine, 'splice_offset': splice_offset}

    if vars.withinToolchangeBlock:
        return {'gcode': gcode_filtertoolchangeblock(gcodeFullLine, gcodeCommand2, gcodeCommand4), 'splice_offset': splice_offset}

    # Catch All
    return {'gcode': gcodeFullLine, 'splice_offset': splice_offset}




def generate(input_file, output_file, printer_profile, splice_offset, silent):

    vars.printerProfileString = printer_profile

    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0]

    try:
        with open(input_file) as opf:
            gcode_file = opf.readlines()
    except:
        gui.usererror("Could not from file\n'{}'".format(input_file))
        exit(1)




    # Process the file
    ##################
    for line in gcode_file:
        # gcode_parseline now returns splice_offset from print file if it exists, keeping everything consistent.
        # splice_offset from gcode takes precedence over splice_offset from CLI.
        result = gcode_parseline(splice_offset, line)
        splice_offset = float(result['splice_offset'])
        vars.processedGCode.append(result['gcode']+"\n")
    gcode_processtoolchange(-1, vars.totalMaterialExtruded, splice_offset)
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
    opf.writelines(vars.processedGCode)
