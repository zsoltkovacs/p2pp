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


def floatparameter(s):
    pos = s.find("=")
    try:
        return float(s[pos+1:])
    except:
        return 0

def stringparameter(s):
    pos = s.find("=")
    try:
        return s[pos+1:].strip()
    except:
        return ""

def check_config_parameters(line):
    # BASIC SETUP  (material setup handled in mcf.py

    # -p takes precedence over printer defined in file
    if "PRINTERPROFILE" in line:
        tmp_string = stringparameter(line)
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
        return

    if "ACCESSORYMODE" in line:
        v.accessory_mode = True

    if "SPLICEOFFSET" in line:
        v.splice_offset = floatparameter(line)
        return

    if "PROFILETYPEOVERRIDE" in line:
        v.filament_type[v.current_tool] = stringparameter(line)
        v.used_filament_types.append(v.filament_type[v.current_tool])
        v.used_filament_types = list(dict.fromkeys(v.used_filament_types))
        return

    if "EXTRUSIONMULTIPLIERCORRECTION" in line:
        v.filament_type[v.current_tool] = floatparameter(line)
        return

    if "EXTRAENDFILAMENT" in line:
        v.extra_runout_filament = floatparameter(line)
        return

    if "BEFORESIDEWIPEGCODE" in line:
        v.before_sidewipe_gcode.append(stringparameter(line))
        return

    if "AFTERSIDEWIPEGCODE" in line:
        v.after_sidewipe_gcode.append(stringparameter(line))
        return

    if "MINSTARTSPLICE" in line:
        v.min_start_splice_length = floatparameter(line)
        if v.min_start_splice_length < 100:
            v.min_start_splice_length = 100
            log_warning("Minimal first slice length adjusted to 100mm")
        return

    if "BEDSIZEX" in line:
        v.bed_size_x = floatparameter(line)
        return
    if "BEDSIZEY" in line:
        v.bed_size_y = floatparameter(line)
        return
    if "BEDORIGINX" in line:
        v.bed_origin_x = floatparameter(line)
        return
    if "BEDORIGINY" in line:
        v.bed_origin_y = floatparameter(line)
        return

    if "MINSPLICE" in line:
        v.min_splice_length = floatparameter(line)
        if v.min_splice_length < 70:
            v. min_splice_length = 70
            log_warning("Minimal slice length adjusted to 70mm")
        return

    # LINEAR PING


    if "LINEARPINGLENGTH" in line:
        v.ping_interval = floatparameter(line)
        v.ping_length_multiplier = 1.0
        if v.ping_interval < 300:
            v.ping_interval = 300
            log_warning("Minimal Linear Ping distance is 300mm!  Your config stated: {}".format(line))
        return

    if "LINEARPING" in line:
        v.ping_length_multiplier = 1.0
        return


    # SIDE TRANSITIONING
    if "SIDEWIPELOC" in line:
        v.side_wipe_loc = stringparameter(line)
        return

    if "WIPEFEEDRATE" in line:
        v.wipe_feedrate = floatparameter(line)
        return

    if "SIDEWIPEMINY" in line:
        v.sidewipe_miny = floatparameter(line)
        return

    if "SIDEWIPEMAXY" in line:
        v.sidewipe_maxy = floatparameter(line)
        return

    if "SIDEWIPECORRECTION" in line:
        v.sidewipe_correction = floatparameter(line)
        if v.sidewipe_correction < 0.9 or v.sidewipe_correction > 1.10:
            v.sidewipe_correction = 1.0
        return

    if "PURGETOWERDELTA" in line:
        if abs(floatparameter(line)) != abs(float(0)):
            v.max_tower_z_delta = abs(floatparameter(line))
            log_warning("CAUTION --  TOWER DELTA ENABLED -- {:-2.2f}mm".format(v.max_tower_z_delta))
        return

    # REPRAP COMPATIBILITY
    if "REPRAPCOMPATIBLE" in line:
        v.reprap_compatible = True
        return


    # Program parameters
    if "NOGUI" in line:
        v.gui = False
        return

    if "CONSOLEWAIT" in line:
        v.consolewait = True
