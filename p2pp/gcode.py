__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3 '
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v

formats = ["{}{:0.3f} ", "{}{:0.3f} ", "{}{:0.3f} ", "{}{:0.5f} ", "{}{} ", "{}{} " ]

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


class GCodeCommand:

    Parms = []

    def __init__(self, gcode_line, is_comment=False):

        self.Parms = [None, None, None, None, None, None, "", None,  "", False, False, False, False, 0]

        if is_comment:
            self.Parms[COMMENT] = gcode_line[1:]
            return
        else:
            pos = gcode_line.find(";")

            if pos != -1:
                self.Parms[COMMENT] = gcode_line[pos + 1:]
                if pos == 1:
                    return
                gcode_line = gcode_line[:pos].strip()

        fields = gcode_line.split(' ')

        if len(fields[0]) > 0:

            self.Parms[COMMAND] = fields[0]
            self.Parms[MOVEMEMT] = self.Parms[COMMAND] in ['G0', 'G1']

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
                        self.Parms[idx] = val
                    else:
                        self.Parms[OTHER] = self.Parms[OTHER] + " " + param

                fields = fields[1:]

            if self.Parms[E]:
                self.Parms[RETRACT] = self.Parms[E] < 0
                self.Parms[UNRETRACT] = self.Parms[E] > 0 and not self.Parms[X] and not self.Parms[Y] and not self.Parms[Z]
                self.Parms[EXTRUDE] = self.Parms[E] > 0


    def command_value(self):
        if self.Parms[COMMAND]:
            return self.Parms[COMMAND][1:]
        else:
            return 0


    def __str__(self):
        p = ""
        if self.Parms[COMMAND]:
            p = self.Parms[COMMAND] + " "
            for idx in range(6):
                if self.Parms[idx]:
                    letter = "XYZEFS"[idx]
                    value = self.Parms[idx]
                    layout = formats[idx]
                    p = p + layout.format(letter, value)

        p = p + self.Parms[OTHER]

        if self.Parms[COMMENT] != "":
            p = p + ";" + self.Parms[COMMENT]

        return p

    def update_parameter(self, pv, value):
        try:
            self.Parms[pv] = value
        except IndexError:
            pass

    def remove_parameter(self, pv):
        self.update_parameter(pv, None)
        if pv == 3:
            self.Parms[RETRACT] = None
            self.Parms[UNRETRACT] = None
            self.Parms[EXTRUDE] = None

    def move_to_comment(self, text):
        if self.Parms[COMMAND]:
            self.Parms[COMMENT] = "-- P2PP -- removed [{}] - {}".format(text, self)
        self.Parms[COMMAND] = None
        self.Parms[COMMAND] = None
        self.Parms[X] = None
        self.Parms[Y] = None
        self.Parms[Z] = None
        self.Parms[E] = None
        self.Parms[F] = None
        self.Parms[S] = None
        self.Parms[OTHER] = ""
        self.Parms[RETRACT] = None
        self.Parms[UNRETRACT] = None
        self.Parms[EXTRUDE] = None

    def get_parameter(self, pv, defaultvalue=0):
        if self.Parms[pv]:
            return self.Parms[pv]
        return defaultvalue

    def issue_command(self, speed=0):
        if self.Parms[E] and self.Parms[MOVEMEMT]:
            extrusion = self.Parms[E] * v.extrusion_multiplier * v.extrusion_multiplier_correction
            v.total_material_extruded += extrusion
            v.material_extruded_per_color[v.current_tool] += extrusion
            v.purge_count += extrusion

            if v.absolute_extruder and v.gcode_has_relative_e:
                if v.absolute_counter == -9999 or v.absolute_counter > 3000:
                    v.processed_gcode.append("G92 E0.00  ; Extruder counter reset")
                    v.absolute_counter = 0

                v.absolute_counter += self.Parms[E]
                self.update_parameter(E, v.absolute_counter)

        if v.absolute_extruder and v.gcode_has_relative_e:
            if self.Parms[COMMAND] == "M83":
                self.Parms[COMMAND] = "M82"
            if self.Parms[COMMAND] == "G92":
                v.absolute_counter = self.Parms[E]

        s = str(self)
        if speed:
            s = s.replace("%SPEED%", "{:0.0f}".format(speed))
        v.processed_gcode.append(s)

    def add_comment(self, text):
        self.Parms[COMMENT] += text

def issue_code(s, is_comment = False):
    GCodeCommand(s, is_comment).issue_command()
