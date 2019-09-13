__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

XAXIS = "X"
YAXIS = "Y"
ZAXIS = "Z"
SPEED = "F"
EXTRUDER = "E"
RELATIVE = True
ABSOLUTE = False

import p2pp.variables as v

class GCodeCommand:
    Command = None
    fullcommand = None
    Command_value = None
    Parameters = {}
    Comment = None
    X = None
    Y = None
    Z = None
    E = None

    def __init__(self, gcode_line):
        self.Command = None
        self.fullcommand = None
        self.Command_value = None
        self.Parameters = {}
        self.Comment = None
        gcode_line = gcode_line.strip()
        pos = gcode_line.find(";")

        if pos != -1:
            self.Comment = gcode_line[pos + 1:]
            gcode_line = (gcode_line.split(';')[0]).strip()

        fields = gcode_line.split(' ')

        if len(fields[0]) > 0:
            command = fields[0]
            self.Command = command[0]
            self.Command_value = command[1:]
            self.fullcommand = fields[0]
            fields = fields[1:]

            while len(fields) > 0:
                param = fields[0].strip()
                if len(param) > 0:
                    p = param[0]
                    v = param[1:]

                    try:
                        if "." in v:
                            v = float(v)
                        else:
                            v = int(v)
                    except ValueError:
                        pass

                    self.Parameters[p] = v

                fields = fields[1:]

        self.X = self.get_parameter("X", None)
        self.Y = self.get_parameter("Y", None)
        self.Z = self.get_parameter("Z", None)
        self.E = self.get_parameter("E", None)

    def __str__(self):
        p = ""
        for key in self.Parameters:
            p = p + "{}{} ".format(key, self.Parameters[key])

        c = self.fullcommand
        if not c:
            c = ""

        if not self.Comment:
            co = ""
        else:
            co = ";" + self.Comment

        return ("{} {} {}".format(c, p, co)).strip() + "\n"

    def update_parameter(self, parameter, value):
        self.Parameters[parameter] = value

    def remove_parameter(self, parameter):
        if parameter in self.Parameters:
            self.Parameters.pop(parameter)

    def move_to_comment(self, text):
        if self.Command:
            self.Comment = "-- P2PP -- removed [{}] - {}".format(text, self)

        self.Command = None
        self.Command_value = None
        self.fullcommand = None
        self.Parameters.clear()

    def has_parameter(self, parametername):
        return parametername in self.Parameters

    def get_parameter(self, parm , defaultvalue = 0 ):
        if self.has_parameter(parm):
            return self.Parameters[parm]
        return defaultvalue

    def issue_command(self):
        v.processed_gcode.append(str(self))

    def add_comment(self, text):
        if self.Comment:
            self.Comment += text
        else:
            self.Comment = text

    def is_comment(self):
        return self.Command == None and not (self.Comment == None)

    def is_movement_command(self):
        return self.Command == "G" and self.Command_value in ['0', '1', '2', '3', '5']


