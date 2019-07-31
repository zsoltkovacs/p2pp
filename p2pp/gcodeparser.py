__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'


import p2pp.variables as v


def gcode_remove_params(gcode, params):
    removed = False
    result = ''
    rempar=''
    p = gcode.split(' ')
    for s in p:
        if s == '':
            continue
        if not s[0] in params:
            result += s + ' '
        else:
            rempar = rempar + s + ' '
            removed = True

    result.strip(' ')
    rempar.strip(' ')
    if len(result) < 4:
        return ';--- P2PP Removed [Removed Parameters] - ' + gcode

    if removed:
        return result +";--- P2PP Removed [Removed Parameters] - " + rempar
    else:
        return result




def get_gcode_parameter(gcode, parameter):
    fields = gcode.split()
    for parm in fields:
        if parm[0] == parameter:
            return float(parm[1:])
    return ""


def parse_slic3r_config():
    for idx in reversed(range(len(v.input_gcode))):
        gcode_line = v.input_gcode[idx].rstrip("\n")

        if gcode_line.startswith("; avoid_crossing_perimeters"):
            break

        if gcode_line.startswith("; wipe_tower_x"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                v.wipetower_posx = float(gcode_line[parameter_start + 1:].strip())

        if gcode_line.startswith("; layer_height"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                v.layer_height = float(gcode_line[parameter_start + 1:].strip())

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
                v.filament_color_code = filament_colour
            continue

        if gcode_line.startswith("; filament_type"):
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                filament_string = gcode_line[parameter_start+1:].strip(" ").split(";")
                if len(filament_string) == 4:
                    v.filament_type = filament_string
                    v.used_filament_types = list(set(filament_string))
            continue

        if gcode_line.startswith("; gcode_flavor"):
            if "reprap" in gcode_line:
                v.isReprap_Mode = True

        if "use_relative_e_distances" in gcode_line:
            parameter_start = gcode_line.find("=")
            if parameter_start != -1:
                gcode_line = gcode_line[parameter_start + 1:].replace(";", "")
                if "1" in gcode_line:
                    v.gcode_has_relative_e = True
                else:
                    v.gcode_has_relative_e = False



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
            v.max_wipe = max(wiping_info)
            continue

        if gcode_line.startswith("; retract_before_travel"):
            pass
