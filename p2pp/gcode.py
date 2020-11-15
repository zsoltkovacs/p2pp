__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3 '
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v

X = 0
Y = 1
Z = 2
E = 3
F = 4
S = 5
OTHER = 6
COMMAND = 7
COMMENT = 8
MOVEMEMT = 9
EXTRUDE = 10
RETRACT = 11
UNRETRACT = 12
CLASS = 13


def create_command(gcode_line, is_comment=False):

    return_value = [None, None, None, None, None, None, "", None,  "", False, False, False, False, 0]

    if is_comment:
        return_value[COMMENT] = gcode_line[1:]
    else:
        pos = gcode_line.find(";")

        if pos != -1:
            return_value[COMMENT] = gcode_line[pos + 1:]
            gcode_line = gcode_line[:pos].strip()

        fields = gcode_line.split(' ')

        if len(fields[0]) > 0:

            return_value[COMMAND] = fields[0]
            return_value[MOVEMEMT] = return_value[COMMAND] in ['G0', 'G1']

            fields = fields[1:]
            while len(fields) > 0:
                param = fields[0].strip()
                if len(param) > 0:
                    idx = "XYZEFS".find(param[0])
                    if idx >= 0:
                        val = param[1:]
                        try:
                            if "." in val:
                                val = float(val)
                            else:
                                val = int(val)
                        except ValueError:
                            pass
                        return_value[idx] = val
                    else:
                        return_value[OTHER] = return_value[OTHER] + " " + param

                fields = fields[1:]

            if return_value[E]:
                return_value[RETRACT] = return_value[E] < 0
                return_value[UNRETRACT] = return_value[E] > 0 and not return_value[X] and not return_value[Y] and not return_value[Z]
                return_value[EXTRUDE] = return_value[E] > 0

    return return_value


def create_commandstring(gcode_tupple):
    if gcode_tupple[COMMAND]:
        p = gcode_tupple[COMMAND]
        if gcode_tupple[X]:
            p = p + " X{:0.3f}".format(gcode_tupple[X])
        if gcode_tupple[Y]:
            p = p + " Y{:0.3f}".format(gcode_tupple[Y])
        if gcode_tupple[Z]:
            p = p + " Z{:0.3f}".format(gcode_tupple[Z])
        if gcode_tupple[E]:
            p = p + " E{:0.5f}".format(gcode_tupple[E])
        if gcode_tupple[F]:
            p = p + " F{}".format(gcode_tupple[F])
        if gcode_tupple[S]:
            p = p + " S{}".format(gcode_tupple[S])
        if len(gcode_tupple[OTHER]) > 0:
            p = p + " "+gcode_tupple[OTHER]
        if gcode_tupple[COMMENT] != "":
            p = p + " ;" + gcode_tupple[COMMENT]
    else:
        if gcode_tupple[COMMENT] != "":
            p = ";" + gcode_tupple[COMMENT]
        else:
            p = ""
    return p


def remove_extrusion(gcode_tupple):
    gcode_tupple[E] = None
    gcode_tupple[RETRACT] = None
    gcode_tupple[UNRETRACT] = None
    gcode_tupple[EXTRUDE] = None


def move_to_comment(gcode_tupple, text):
    if gcode_tupple[COMMAND]:
        gcode_tupple[COMMENT] = "-- P2PP -- removed [{}] - {}".format(text, create_commandstring(gcode_tupple))
    else:
        gcode_tupple[COMMENT] = ""
    gcode_tupple[COMMAND] = None
    gcode_tupple[X] = None
    gcode_tupple[Y] = None
    gcode_tupple[Z] = None
    gcode_tupple[E] = None
    gcode_tupple[F] = None
    gcode_tupple[S] = None
    gcode_tupple[OTHER] = ""
    gcode_tupple[RETRACT] = None
    gcode_tupple[UNRETRACT] = None
    gcode_tupple[EXTRUDE] = None


def get_parameter(gcode_tupple, pv, defaultvalue=0):
    if gcode_tupple[pv]:
        return gcode_tupple[pv]
    return defaultvalue


def issue_command(gcode_tupple, speed=0):
    if gcode_tupple[E] and gcode_tupple[MOVEMEMT]:
        extrusion = gcode_tupple[E] * v.extrusion_multiplier * v.extrusion_multiplier_correction
        v.total_material_extruded += extrusion
        v.material_extruded_per_color[v.current_tool] += extrusion
        v.purge_count += extrusion

        if v.absolute_extruder and v.gcode_has_relative_e:
            if v.absolute_counter == -9999 or v.absolute_counter > 3000:
                v.processed_gcode.append("G92 E0.00  ; Extruder counter reset")
                v.absolute_counter = 0

            v.absolute_counter += gcode_tupple[E]
            gcode_tupple[E] = v.absolute_counter

    if v.absolute_extruder and v.gcode_has_relative_e:
        if gcode_tupple[COMMAND] == "M83":
            gcode_tupple[COMMAND] = "M82"
        if gcode_tupple[COMMAND] == "G92":
            v.absolute_counter = gcode_tupple[E]

    s = create_commandstring(gcode_tupple)
    if speed:
        s = s.replace("%SPEED%", "{:0.0f}".format(speed))
    v.processed_gcode.append(s)


def issue_code(code_string, is_comment = False):
    issue_command(create_command(code_string, is_comment))
