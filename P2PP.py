#!/usr/bin/pythonw
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

import p2pp.mcf as mcf
import argparse
import p2pp.variables as v
import version as ver
import p2pp.gui as gui
import sys
import os
from platform import system


arguments = argparse.ArgumentParser(description='Generates MCF/Omega30 headers from an multi-tool/multi-extruder'
                                                ' GCODE derived from Slic3r.')

arguments.add_argument('-i',
                       '--input-file',
                       required=True)
arguments.add_argument('-d',
                       '--output-file',
                       required=False)
arguments.add_argument('-o',
                       '--splice-offset',
                       type=float,
                       required=False,
                       default=40.00,
                       help='Offset position in the purge tower '
                            'where transition occurs. Similar to transition offset in Chroma.'
                            ' GCODE ;P2PP SPLICEOFFSET=xxx takes precedence over anything set here'
                       )
arguments.add_argument('-n',
                       '--nogui',
                       action='store_true',
                       required=False
                       )

arguments.add_argument('-p',
                       '--printer-profile',
                       required=False,
                       default='',
                       help='A unique ID linked to a printer configuration'
                            ' profile in the Palette 2 hardware.'
                       )
arguments.add_argument('-s',
                       '--silent',
                       default=False,
                       help='Omits Summary page after processing from being printed to STDOUT'
                       )

arguments.add_argument('-w',
                       '--wait',
                       required=False,
                       help='--w 1 Wait for the user to press enter after processing the file.'
                       )


def main(args):

    if not args['nogui']:
        v.gui = True
    else:
        v.gui = False

    v.filename = args['input_file']
    mcf.generate(v.filename,
                 args['output_file'],
                 args['printer_profile'],
                 args['splice_offset'],
                 args['silent']
                 )

    if args['wait'] == "1":
        raw_input("Press Enter to continue...")


if __name__ == "__main__":
    v.version = ver.Version

    if len(sys.argv)==1:
        platformD = system()
        if platformD == 'Darwin':
            gui.user_error("Script name to be entered in Slic3r/PrusaSlicer", "{}/p2pp.command".format(os.path.dirname(sys.argv[0])))
        elif platformD == 'Windows':
            gui.user_error("Script name to be entered in Slic3r/PrusaSlicer","{}/\\2pp.bat".format(os.path.dirname(sys.argv[0])))

    else:
        main(vars(arguments.parse_args()))
