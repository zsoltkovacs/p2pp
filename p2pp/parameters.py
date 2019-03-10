__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '3.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import p2pp.variables as v
from p2pp.logfile import log_warning


def check_config_parameters(gcode_line):
    # BASIC SETUP  (material setup handled in mcf.py)

    if gcode_line.startswith(";P2PP PRINTERPROFILE=") and v.printerProfileString == '': # -p takes precedence over printer defined in file
        v.printerProfileString = gcode_line[21:]

    if gcode_line.startswith(";P2PP SPLICEOFFSET="):
        v.splice_offset = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP EXTRAENDFILAMENT="):
        v.extraRunoutFilament = float(gcode_line[23:])

    if gcode_line.startswith(";P2PP BEFORESIDEWIPEGCODE"):
        v.before_sidewipe_gcode.append(gcode_line[25:].strip())

    if gcode_line.startswith(";P2PP AFTERSIDEWIPEGCODE"):
        v.after_sidewipe_gcode.append(gcode_line[24:].strip())

    if gcode_line.startswith(";P2PP MINSTARTSPLICE="):
        v.minimalStartSpliceLength = float(gcode_line[21:])
        if v.minimalStartSpliceLength < 100:
            v.minimalStartSpliceLength = 100
            log_warning("Minimal first slice length adjusted to 100mm")

    if gcode_line.startswith(";P2PP BEDSIZEX="):
        v.bed_size_x = float(gcode_line[15:])
    if gcode_line.startswith(";P2PP BEDSIZEY="):
        v.bed_size_y = float(gcode_line[15:])
    if gcode_line.startswith(";P2PP BEDORIGINX="):
        v.bed_origin_x = float(gcode_line[17:])
    if gcode_line.startswith(";P2PP BEDORIGINY="):
        v.bed_origin_y = float(gcode_line[17:])

    if gcode_line.startswith(";P2PP MINSPLICE="):
        v.minimalSpliceLength = float(gcode_line[16:])
        if v.minimalSpliceLength < 70:
            v. minimalSpliceLength = 70
            log_warning("Minimal slice length adjusted to 70mm")

    # LINEAR PING
    if gcode_line.startswith(";P2PP LINEARPING"):
        v.pingLengthMultiplier = 1.0

    if gcode_line.startswith(";P2PP LINEARPINGLENGTH="):
        v.pingIntervalLength = float(gcode_line[23:])
        if (v.pingIntervalLength<350):
            v.pingIntervalLength = 300
            log_warning("Minimal Linear Ping distance is 300mm!  Your config statet: {}".format(gcode_line))

    # SIDE TRANSITIONING
    if gcode_line.startswith(";P2PP SIDEWIPELOC="):
        v.side_wipe_loc = gcode_line[18:].strip()

    if gcode_line.startswith(";P2PP WIPEFEEDRATE="):
        v.side_wipe_loc = gcode_line[19:].strip()

    if gcode_line.startswith(";P2PP SIDEWIPEMINY="):
        v.sideWipeMinY = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP SIDEWIPEMAXY="):
        v.sideWipeMaxY = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP SIDEWIPECORRECTION="):
        v.sidewipecorrection = float(gcode_line[26:])
        if v.sidewipecorrection < 0.9 or v.sidewipecorrection > 1.10:
            v.sidewipecorrection = 1.0
