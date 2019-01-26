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


import p2pp.variables as v

def gcode_removeparams(gcode, params):
    result = ""
    parts = gcode.split(" ")

    for subcommand in parts:
        if subcommand == "":
            continue
        if not subcommand[0] in params:
            result += subcommand+" "

    result.strip(" ")
    if len(result) < 4:
        return ";--- P2PP Removed "+gcode

    return result


def get_gcode_parameter(gcode, parameter):
    fields = gcode.split()
    for parm in fields:
        if parm[0] == parameter:
            return float(parm[1:])
    return ""


def parseSlic3rConfig():


    for idx in reversed(range(len(v.inputGcode))):
        gcodeline = v.inputGcode[idx].rstrip("\n")

        if gcodeline.startswith("; avoid_crossing_perimeters"):
            break

        if gcodeline.startswith("; extruder_colour"):

            parmstart = gcodeline.find("#")
            if parmstart != -1:
                gcodeline = gcodeline[parmstart+1:].replace(";","")
                filamentColor = gcodeline.split("#")

            if (len(filamentColor)==4):
                v.filamentColorCode = filamentColor
            continue


        if gcodeline.startswith("; filament_type"):
            parmstart = gcodeline.find("=")
            if parmstart != -1:
                filaments = gcodeline[parmstart+1:].strip(" ").split(";")
            if (len(filaments)==4):

                v.filamentType = filaments
                v.usedFilamentTypes = list(set(filaments))
            continue

        if gcodeline.startswith("; wiping_volumes_matrix"):
            parmstart = gcodeline.find("=")
            if parmstart != -1:
                wipinginfo = gcodeline[parmstart+1:].strip(" ").split(",")
                if len(wipinginfo) != 16:
                    continue
                for idx in range(len(wipinginfo)):
                    wipinginfo[idx] = int(wipinginfo[idx])

                v.maxWipe = max(wipinginfo)

            continue