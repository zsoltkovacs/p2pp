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



from p2pp.formatnumbers import hexify_short,  hexify_float
import p2pp.variables as v
from p2pp.colornames import findNearestColor
from p2pp.logfile import log_warning
import p2pp.gui as gui

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


def algorithm_transitionused(fromInput, toInput):
    if len(v.spliceUsedTool)>0 :

       for idx in range(len(v.spliceUsedTool)-1):
           if  v.spliceUsedTool[idx] == fromInput and v.spliceUsedTool[idx+1] == toInput:
               return True

    return False


def algorithm_createtable():

    spliceAlgoList = []
    for i in range(4):
        for j in range(4):

            if i==j:
                continue

            try:
                algoKey = "{}{}".format(v.usedFilamentTypes.index(v.filamentType[i])+1,v.usedFilamentTypes.index(v.filamentType[j])+1)
                if algoKey in spliceAlgoList:
                    continue
            except:
                continue

            if not algorithm_transitionused(i,j):
                continue

            spliceAlgoList.append(algoKey)

            try:
                algo = v.spliceAlgorithmDictionary["{}-{}".format(v.filamentType[i], v.filamentType[j])]
            except KeyError:
                log_warning("WARNING: No Algorithm defined for transitioning {} to {}. Using Default".format(v.filamentType[i],
                                                                                                             v.filamentType[j]))
                algo = v.defaultSpliceAlgorithm


            v.spliceAlgorithmTable.append("D{} {}".format(algoKey,algo))



############################################################################
# Generate the Omega - Header that drives the Palette to generate filament
############################################################################
def header_generateomegaheader(job_name):

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
            if v.filamentColorCode[i] == "-":
                log_warning(
                    "Filament #{} is missing Color info, make sure to add ;P2PP FC=[extruder_colour] to filament GCode".format(
                        i))
                v.filamentColorCode[i] = '000000'

            header.append("D{}{}{}_{} ".format(v.usedFilamentTypes.index(v.filamentType[i])+1,
                                            v.filamentColorCode[i].strip("\n"),
                                            findNearestColor(v.filamentColorCode[i].strip("\n")),
                                            v.filamentType[i].strip("\n")
                                            ))
        else:
            header.append("D0 ")

    header.append("\n")

    header.append('O26 ' + hexify_short(len(v.spliceExtruderPosition)) + "\n")
    header.append('O27 ' + hexify_short(len(v.pingExtruderPosition)) + "\n")
    if len(v.spliceAlgorithmTable) > 9:
        log_warning("ATTENTION: THIS FILE WILL NOT POTENTIALLY NOT WORK CORRECTY DUE TO A BUG IN PALETTE2 PLUGIN")
        header.append("O28 D{:0>4d}\n".format(len(v.spliceAlgorithmTable)))
    else:
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
        header.append("O1 D{} {}\n".format(job_name, hexify_float(v.totalMaterialExtruded + v.splice_offset)))

    header.append("M0\n")
    header.append("T0\n")

    summary.append(";------------------:\n")
    summary.append(";SPLICE INFORMATION:\n")
    summary.append(";------------------:\n")
    summary.append(";       Splice Offset = {:-8.2f}mm\n\n".format(v.splice_offset))

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
