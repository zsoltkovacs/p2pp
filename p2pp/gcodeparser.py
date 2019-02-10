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
from p2pp.logfile import log_warning


def gcode_remove_params(gcode, params):
    result = ''
    p = gcode.split(' ')
    for s in p:
        if s == '':
            continue
        if not s[0] in params:
            result += s + ' '

    result.strip(' ')
    if len(result) < 4:
        return ';--- P2PP Removed ' + gcode

    return result


def get_gcode_parameter(gcode, parameter):
    fields = gcode.split()
    for parm in fields:
        if parm[0] == parameter:
            return float(parm[1:])
    return ""


def parse_slic3r_config():
    for idx in reversed(range(len(v.inputGcode))):
        gcode_line = v.inputGcode[idx].rstrip("\n")

        if gcode_line.startswith("; avoid_crossing_perimeters"):
            break

        if gcode_line.startswith("; wipe_tower_x"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                v.wipetower_posx = float(gcode_line[parameter_start+1:].strip())

        if gcode_line.startswith("; wipe_tower_y"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                v.wipetower_posy = float(gcode_line[parameter_start+1:].strip())


        if gcode_line.startswith("; extruder_colour"):
            filament_colour = ''
            parameter_start = gcode_line.find("#")
            if parameter_start != -1:
                gcode_line = gcode_line[parameter_start+1:].replace(";", "")
                filament_colour = gcode_line.split("#")

            if len(filament_colour) == 4:
                v.filamentColorCode = filament_colour
            continue

        if gcode_line.startswith("; filament_type"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                filament_string = gcode_line[parameter_start+1:].strip(" ").split(";")
                if len(filament_string) == 4:
                    v.filamentType = filament_string
                    v.usedFilamentTypes = list(set(filament_string))
            continue

        if gcode_line.startswith(";"):
            pass

        if gcode_line.startswith("; wiping_volumes_matrix"):
            wiping_info = []
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                wiping_info = gcode_line[parameter_start+1:].strip(" ").split(",")
                if len(wiping_info) != 16:
                    continue
                for i in range(len(wiping_info)):
                    wiping_info[i] = int(wiping_info[i])
            v.maxWipe = max(wiping_info)
            continue

        if gcode_line.startswith("; retract_before_travel"):
            pass


