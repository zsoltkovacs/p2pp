__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3 '
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.gui as gui
import p2pp.variables as v


class GCodeCommand:
    Command = None
    is_movement_command = False
    is_toolchange = False
    Parameters = {}
    Class = 0
    Comment = None
    Layer = None
    X = None
    Y = None
    Z = None
    E = None

    def __init__(self, gcode_line):
        self.Command = None
        self.Parameters = {}
        self.Comment = None
        self.Layer = v.parsedlayer
        self.is_toolchange = False
        gcode_line = gcode_line.strip()
        pos = gcode_line.find(";")

        if pos != -1:
            self.Comment = gcode_line[pos + 1:]
            gcode_line = (gcode_line.split(';')[0]).strip()

        fields = gcode_line.split(' ')

        if len(fields[0]) > 0:

            self.Command = fields[0]
            self.is_toolchange = self.Command[0] == 'T'
            self.is_movement_command = self.Command in ['G0', 'G1', 'G2', 'G3', 'G5', 'G10', 'G11']

            fields = fields[1:]

            while len(fields) > 0:
                param = fields[0].strip()
                if len(param) > 0:
                    p = param[0]
                    val = param[1:]

                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass

                    self.Parameters[p] = val

                    if p == "X":
                        self.X = val
                    if p == "Y":
                        self.Y = val
                    if p == "Z":
                        self.Z = val
                    if p == "E":
                        self.E = val

                fields = fields[1:]

    def command_value(self):
        if self.Command:
            return self.Command[1:]
        else:
            return None

    def __str__(self):
        p = ""

        # use the same formatting as prusa to ease file compares (X, Y, Z, E, F)

        sorted_keys = "XYZE"
        if self.is_movement_command:
            for key in sorted_keys:
                if key in self.Parameters:
                    form = "{} {}"
                    value = self.Parameters[key]
                    if (value is None) or (value == ""):
                        gui.log_warning("GCode error detected, file might not print correctly")
                        value = ""

                    if type(value) in [int, float]:
                        if key in "XYZ":
                            form = "{}{:0.3f} "
                        if key == "E":
                            form = "{}{:0.5f} "

                    p = p + form.format(key, value)

        for key in self.Parameters:
            if not self.is_movement_command or key not in sorted_keys:
                value = self.Parameters[key]
                if value is None:
                    value = ""

                p = p + "{}{} ".format(key, value)

        c = self.Command
        if not c:
            c = ""

        if not self.Comment:
            co = ""
        else:
            co = ";" + self.Comment

        return ("{} {} {}".format(c, p, co)).strip() + "\n"

    def update_parameter(self, parameter, value):
        self.Parameters[parameter] = value
        if parameter == "X":
            self.X = value
        if parameter == "Y":
            self.Y = value
        if parameter == "Z":
            self.Z = value
        if parameter == "E":
            self.E = value

    def remove_parameter(self, parameter):
        if parameter in self.Parameters:
            if self.Comment:
                self.Comment = "[R_{}{}] ".format(parameter, self.Parameters[parameter]) + self.Comment
            else:
                self.Comment = "[R_{}{}] ".format(parameter, self.Parameters[parameter])
            self.Parameters.pop(parameter)

            if parameter == "X":
                self.X = None
            if parameter == "Y":
                self.Y = None
            if parameter == "Z":
                self.Z = None
            if parameter == "E":
                self.E = None

    def move_to_comment(self, text):
        if self.Command:
            self.Comment = "-- P2PP -- removed [{}] - {}".format(text, self)
        self.Command = None
        self.X = None
        self.Y = None
        self.Z = None
        self.E = None
        self.Parameters.clear()
        self.is_movement_command = False
        self.is_toolchange = False

    def get_comment(self):
        if not self.Comment:
            return ""
        else:
            return self.Comment

    def has_parameter(self, parametername):
        return parametername in self.Parameters

    def get_parameter(self, parm, defaultvalue=0):
        if self.has_parameter(parm):
            return self.Parameters[parm]
        return defaultvalue

    def issue_command(self, speed=-1):
        extrusion = 0
        if self.E:
            extrusion = self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
            if self.is_movement_command:
                v.total_material_extruded += extrusion
                v.material_extruded_per_color[ v.current_tool] += extrusion
                v.purge_count += extrusion

                if v.absolute_extruder and v.gcode_has_relative_e:
                    if v.absolute_counter == -9999 or v.absolute_counter > 3000:
                        v.processed_gcode.append("G92 E0.00  ; Extruder counter reset")
                        v.absolute_counter = 0

                    v.absolute_counter += self.E
                    self.update_parameter("E", v.absolute_counter)

        if v.absolute_extruder and v.gcode_has_relative_e:
            if self.Command == "M83":
                self.Command = "M82"
            if self.Command == "G92":
                v.absolute_counter = self.E

        s = str(self)
        if speed != -1:
            s = s.replace("%SPEED%", "{:0.0f}".format(speed))
        v.processed_gcode.append(s)
        v.processed_extrusion.append(extrusion)

    def add_comment(self, text):
        if self.Comment:
            self.Comment += text
        else:
            self.Comment = text

    def is_comment(self):
        return self.Command is None and not (self.Comment is None)

    def is_xy_positioning(self):
        return self.is_movement_command and self.X and self.Y and not self.E

    def is_retract_command(self):
        if self.E:
            return self.is_movement_command and self.E < 0
        else:
            return self.Command == "G10"

    def is_unretract_command(self):
        if self.E:
            return self.is_movement_command and self.E > 0 and self.X is None and self.Y is None and self.Z is None
        else:
            return self.Command == "G11"


def issue_code(s):
    GCodeCommand(s).issue_command()
