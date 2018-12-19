__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '1.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import struct


# hexify_short is used to turn a short integer into the specific notation used by Mosaic
def hexify_short(num):
    return "D" + '{0:04x}'.format(num)



# hexify_long is used to turn a 32-bit integer into the specific notation used by Mosaic
def hexify_long(num):
    return "D" + '{0:08x}'.format(num)



# hexify_float is used to turn a 32-but floating point number into the specific notation used by Mosaic
def hexify_float(f):
    return "D" + (hex(struct.unpack('<I', struct.pack('<f', f))[0]))[2:]