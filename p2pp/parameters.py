__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v
from p2pp.logfile import log_warning


def check_config_parameters(gcode_line):
    # BASIC SETUP  (material setup handled in mcf.py

    # -p takes precedence over printer defined in file
    if gcode_line.startswith(";P2PP PRINTERPROFILE="):
        tmp_string = gcode_line[21:].strip()
        if len(tmp_string) != 16:
            log_warning("Invalid Printer profile!  - Has invalid length (expect 16) - [{}]"
                        .format(tmp_string))
            tmp_string= ""
        if not all(char in set("0123456789ABCDEFabcdef") for char in tmp_string):
            log_warning("Invalid Printer profile!  - Invalid characters  (expect 0123456789abcdef) - [{}]"
                        .format(tmp_string))
            tmp_string = ""

        if len(tmp_string) == 16:
            v.printer_profile_string = tmp_string

    if gcode_line.startswith(";P2PP SPLICEOFFSET="):
        v.splice_offset = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP PROFILETYPEOVERRIDE="):
        v.filament_type[v.current_tool] = gcode_line[26:].strip()
        v.used_filament_types.append(gcode_line[26:].strip())
        v.used_filament_types = list(dict.fromkeys(v.used_filament_types))


    if gcode_line.startswith(";P2PP EXTRAENDFILAMENT="):
        v.extra_runout_filament = float(gcode_line[23:])

    if gcode_line.startswith(";P2PP BEFORESIDEWIPEGCODE"):
        v.before_sidewipe_gcode.append(gcode_line[25:].strip())

    if gcode_line.startswith(";P2PP AFTERSIDEWIPEGCODE"):
        v.after_sidewipe_gcode.append(gcode_line[24:].strip())

    if gcode_line.startswith(";P2PP MINSTARTSPLICE="):
        v.min_start_splice_length = float(gcode_line[21:])
        if v.min_start_splice_length < 100:
            v.min_start_splice_length = 100
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
        v.min_splice_length = float(gcode_line[16:])
        if v.min_splice_length < 70:
            v. min_splice_length = 70
            log_warning("Minimal slice length adjusted to 70mm")

    # LINEAR PING
    if gcode_line.startswith(";P2PP LINEARPING"):
        v.ping_length_multiplier = 1.0

    if gcode_line.startswith(";P2PP LINEARPINGLENGTH="):
        v.ping_interval = float(gcode_line[23:])
        if v.ping_interval < 350:
            v.ping_interval = 300
            log_warning("Minimal Linear Ping distance is 300mm!  Your config stated: {}".format(gcode_line))

    # SIDE TRANSITIONING
    if gcode_line.startswith(";P2PP SIDEWIPELOC="):
        v.side_wipe_loc = gcode_line[18:].strip()

    if gcode_line.startswith(";P2PP WIPEFEEDRATE="):
        v.wipe_feedrate = float(gcode_line[19:].strip())

    if gcode_line.startswith(";P2PP SIDEWIPEMINY="):
        v.sidewipe_miny = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP SIDEWIPEMAXY="):
        v.sidewipe_maxy = float(gcode_line[19:])

    if gcode_line.startswith(";P2PP SIDEWIPECORRECTION="):
        v.sidewipe_correction = float(gcode_line[26:])
        if v.sidewipe_correction < 0.9 or v.sidewipe_correction > 1.10:
            v.sidewipe_correction = 1.0

    if gcode_line.startswith(";P2PP PURGETOWERDELTA="):
        v.max_tower_z_delta = abs(float(gcode_line[22:]))
        log_warning("CAUTION --  TOWER DELTA ENABLED -- {:-2.2f}mm".format(v.max_tower_z_delta))

    # REPRAP COMPATIBILITY
    if gcode_line.startswith(";P2PP REPRAPCOMPATIBLE"):
        v.reprap_compatible = True
