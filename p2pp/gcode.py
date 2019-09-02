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



class GCodeCommand:
    Command = None
    Command_value = None
    Parameters = {}
    Comment = None

    def __init__(self, gcode_line):
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
            fields = fields[1:]

            while len(fields) > 0:
                param = fields[0].strip()
                if len(param) > 0:
                    p = param[0]
                    v = param[1:]

                    if v.isnumeric():
                        if "." in v:
                            v = float(v)
                        else:
                            v = int(v)
                    self.Parameters[p] = v

                fields = fields[1:]

    def __str__(self):
        p = ""
        for key in self.Parameters:
            p = p + "{}{} ".format(key, self.Parameters[key])
        c = self.Command
        if not c:
            c = ""

        cv = self.Command_value
        if not cv:
            cv = ""

        if not self.Comment:
            co = ""
        else:
            co = ";" + self.Comment

        return ("{}{} {} {}".format(c, cv, p, co)).strip()

    def update_parameter(self, parameter, value):
        self.Parameters[parameter] = value

    def remove_parameter(self, parameter):
        if parameter in self.Parameters:
            self.Parameters.pop(parameter)

    def move_to_comment(self, text):
        if self.Command:
            self.Comment = "-- P2PP -- removed [{}] : {}".format(text, self)

        self.Command = None
        self.Command_value = None
        self.Parameters.clear()

    def has_parameter(self, parametername):
        return parametername in self.Parameters

    def get_parameter(self, parm , defaultvalue = 0 ):
        if self.has_parameter(parm):
            return self.Parameters[parm]
        return defaultvalue

    def is_movement_command(self):
        return self.Command == "G" and self.Command_value in ['0', '1', '2', '3', '5']

    def get_updated_axis(self, axis, oldvalues):

        assert isinstance(axis, list)
        assert isinstance(oldvalues, list)
        assert len(axis) == len(oldvalues)

        rval = []
        for i in range(len(axis)):
            _axis = axis[i]
            _oldval = oldvalues[i]

            if self.Command=="G" and self.Command_value == "92":
                moverelative = [False] * len(axis)
                multiplier = [1] * len(axis)


            if self.is_movement_command() or (self.Command=="G" and self.Command_value == "92"):
                if _axis in self.Parameters:
                    if moverelative[i]:
                        rval.append(_oldval + self.Parameters[_axis] * multiplier[i])
                    else:
                        rval.append(self.Parameters[_axis] * multiplier[i])
                else:
                    rval.append(_oldval)

        return rval

