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

import struct


def hexify_short(num):
    # hexify_short: Converts a short integer into the specific notation used by Mosaic
    return "D" + '{0:04x}'.format(num)


def hexify_long(num):
    # hexify_long: Converts a 32-bit integer into the specific notation used by Mosaic
    return "D" + '{0:08x}'.format(num)


def hexify_float(f):
    # hexify_float: Converts a 32-bit floating point number into the specific notation used by Mosaic
    return "D" + (hex(struct.unpack('<I', struct.pack('<f', f))[0]))[2:]


def hours(sec):
    return int(sec / 3600)


def minutes(sec):
    return int((sec % 3600) / 60)


def seconds(sec):
    return int(sec % 60)


def comment_out(line):
    return "; -- P2PP removed" + line
