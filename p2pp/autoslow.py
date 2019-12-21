__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import math

import p2pp.gcode as gcode
import p2pp.variables as v

points_at_risk = []


class coord():
    x = 0
    y = 0
    z = 0

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def distance(self, coordb):
        if self.x == None or self.y == None or self.z == None:
            return 0

        dx = self.x - coordb.x
        dy = self.y - coordb.y
        dz = self.z - coordb.z

        return math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    def assign(self, coordb):
        self.x = coordb.x
        self.y = coordb.y
        self.z = coordb.z


PRESTARTOFFSET = 20
SAFE_EXTRUSION = 40
EXTENDED_SPLICE_TIME = 40


def calculate_points_at_risk():
    for i in range(len(v.splice_offset)):
        printpoint = i - v.tubelength - PRESTARTOFFSET

        # anything pre-tubelength is during loading and not during printing process... no correction is needed
        if printpoint >= v.tubelength:
            points_at_risk.append(printpoint)


def auto_slowdown_process():
    keep_speed = 1000
    previous_coordinate = coord(None, None)
    extrusion = 0
    extrusionmultiplier = 1
    commandtime = 0

    _startindex = None
    _startextrusion = 0
    _starttime = 0

    idx = 0
    while idx < range(len(v.processed_gcode)):
        g = gcode.GCodeCommand(v.processed_gcode[i])

        # detect flow rate changes
        if g.Command == "M221":
            extrusionmultiplier = g.get_parameter("S", 100) / 100

        if g.Command == "G28":
            previous_coordinate.x = 0
            previous_coordinate.y = 0
            previous_coordinate.z = 0

        if g.is_movement_command():
            keep_speed = g.get_parameter("F", keep_speed * 60) / 60

            newpos = coord(g.get_parameter("X", previous_coordinate.x),
                           g.get_parameter("Y", previous_coordinate.y),
                           g.get_parameter("Z", previous_coordinate.z))

            movetime = previous_coordinate.distance(newpos)
            if movetime == 0 and g.has_E():
                commandtime += g.E / keep_speed
            else:
                commandtime += previous_coordinate.distance(newpos) / keep_speed

            extrusion += g.get_parameter("E") * extrusionmultiplier

            if len(points_at_risk):
                # check if we passed a points at risk
                if points_at_risk[0] - extrusion < 0:
                    # if there are two consecutive splices, and the first has not tripped the
                    # slowdown trap, we should assume we have enough in the buffer to reste the counters
                    # the inserted correction value should be commented out
                    if _startindex is not None:
                        v.processed_gcode[_startindex] = "; No Slowdown needed"

                    # insert a
                    v.processed_gcode.insert(idx + 1, "M220 XXX")
                    _startindex = idx + 1
                    _starttime = commandtime
                    _startextrusion = extrusion
                    # remove point at risk
                    points_at_risk.pop(0)

            if _startindex is not None:
                _extruded = extrusion - _startextrusion
                if _extruded > SAFE_EXTRUSION:
                    speedfactor = 100 * (commandtime - _starttime) / EXTENDED_SPLICE_TIME
                    splicetime = commandtime - _starttime
                    v.processed_gcode[idx + 1] = "M220 S{} ; Autoslowdown".format(int(speedfactor))

        idx += 1
