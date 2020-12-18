__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import sys
import p2pp.colornames as colornames
import p2pp.variables as v
import version

CEND = '\33[0m'
CBOLD = '\33[1m'
CITALIC = '\33[3m'
CURL = '\33[4m'
CBLINK = '\33[5m'
CBLINK2 = '\33[6m'
CSELECTED = '\33[7m'

CBLACK = '\33[30m'
CRED = '\33[31m'
CGREEN = '\33[32m'
CYELLOW = '\33[33m'
CBLUE = '\33[34m'
CVIOLET = '\33[35m'
CBEIGE = '\33[36m'
CWHITE = '\33[37m'

CBLACKBG = '\33[40m'
CREDBG = '\33[41m'
CGREENBG = '\33[42m'
CYELLOWBG = '\33[43m'
CBLUEBG = '\33[44m'
CVIOLETBG = '\33[45m'
CBEIGEBG = '\33[46m'
CWHITEBG = '\33[47m'

CGREY  = '\33[90m'
CRED2 = '\33[91m'
CGREEN2 = '\33[92m'
CYELLOW2 = '\33[93m'
CBLUE2 = '\33[94m'
CVIOLET2 = '\33[95m'
CBEIGE2 = '\33[96m'
CWHITE2 = '\33[97m'


def print_summary(summary):
    create_logitem("")
    create_logitem("-" * 19, CBLUE)
    create_logitem("   Print Summary", CBLUE)
    create_logitem("-" * 19, CBLUE)
    create_emptyline()
    create_logitem("Number of splices:    {0:5}".format(len(v.splice_extruder_position)))
    create_logitem("Number of pings:      {0:5}".format(len(v.ping_extruder_position)))
    create_logitem("Total print length {:-8.2f}mm".format(v.total_material_extruded))
    create_emptyline()
    if v.full_purge_reduction or v.tower_delta:
        create_logitem("Tower Delta Range  {:.2f}mm -  {:.2f}mm".format(v.min_tower_delta, v.max_tower_delta))
    create_emptyline()

    if v.m4c_numberoffilaments <= 4:

        create_logitem("Inputs/Materials used:")

        for i in range(len(v.palette_inputs_used)):
            if v.palette_inputs_used[i]:
                create_colordefinition(0, i + 1, v.filament_type[i], v.filament_color_code[i],
                                       v.material_extruded_per_color[i])

    else:
        create_logitem("Materials used:")
        for i in range(v.m4c_numberoffilaments):
            create_colordefinition(1, i + 1, v.filament_type[0], v.filament_color_code[i], 0)

        create_emptyline()

        create_logitem("Required Toolchanges: {}".format(len(v.m4c_headerinfo)))



def create_logitem(text, color=CWHITE):
    text = text.strip()
    print("  " + color + text + CEND)



def create_colordefinition(reporttype, p2_input, filament_type, color_code, filamentused):
    name = "----"
    if reporttype == 0:
        name = "Input"
    if reporttype == 1:
        name = "Filament"

    if reporttype == 0:
        print("\t{} {} {:-8.2f}mm - {}  \t{:15} ".format(name, p2_input, filamentused, filament_type, colornames.find_nearest_colour(color_code)))
    if reporttype == 1:
        print("\t{}  - {}  \t{:15} ".format(name, p2_input, filament_type, colornames.find_nearest_colour(color_code)))


def create_emptyline():
    print("")


def close_button_enable():
    create_emptyline()

    if sys.version_info[0] == 3:
        print()
        input("Press enter to terminate....")
    else:
        raw_input("Press enter to terminate....")
    exit()


def log_warning(text):
    v.process_warnings.append(";" + text)
    print(CRED + text + CEND)


print(" -- P2PP === Palette 2 Post Processor for Prusa Slicer - Version {}".format(version.Version))

