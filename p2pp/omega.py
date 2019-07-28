__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'


from p2pp.formatnumbers import hexify_short, hexify_float, hexify_long
import p2pp.variables as v
from p2pp.colornames import find_nearest_colour
from p2pp.logfile import log_warning
import p2pp.gui as gui

# ################################################################
# ######################### ALGORITHM PROCESSING ################
# ################################################################
def algorithm_create_process_string(heating, compression, cooling):
    return "{} {} {}".format(hexify_short(int(heating)),
                             hexify_short(int(compression)),
                             hexify_short(int(cooling))
                             )


def algorithm_process_material_configuration(splice_info):
    fields = splice_info.split("_")
    if fields[0] == "DEFAULT" and len(fields) == 4:
        v.default_splice_algorithm = algorithm_create_process_string(fields[1],
                                                                     fields[2],
                                                                     fields[3])

    if len(fields) == 5:
        key = "{}-{}".format(fields[0],
                             fields[1])
        v.splice_algorithm_dictionary[key] = algorithm_create_process_string(fields[2],
                                                                             fields[3],
                                                                             fields[4])


def algorithm_transition_used(from_input, to_input):
    if len(v.splice_used_tool) > 0:
        for idx in range(len(v.splice_used_tool) - 1):
            if v.splice_used_tool[idx] == from_input and v.splice_used_tool[idx + 1] == to_input:
                return True
    return False


def algorithm_create_table():
    splice_list = []
    for i in range(4):
        for j in range(4):

            if i == j:
                continue
            try:
                algo_key = "{}{}".format(v.used_filament_types.index(v.filament_type[i]) + 1,
                                         v.used_filament_types.index(v.filament_type[j]) + 1)
                if algo_key in splice_list:
                    continue
            except:
                continue

            if not algorithm_transition_used(i, j):
                continue

            splice_list.append(algo_key)

            try:
                algo = v.splice_algorithm_dictionary["{}-{}".format(v.filament_type[i], v.filament_type[j])]
            except KeyError:
                log_warning("WARNING: No Algorithm defined for transitioning" +
                            " {} to {}. Using Default".format(v.filament_type[i],
                                                              v.filament_type[j]))
                algo = v.default_splice_algorithm

            v.splice_algorithm_table.append("D{} {}".format(algo_key, algo))


############################################################################
# Generate the Omega - Header that drives the Palette to generate filament
############################################################################
def header_generate_omega(job_name):
    if v.printer_profile_string == '':
        log_warning("The PRINTERPROFILE identifier is missing, Please add:\n" +
                    ";P2PP PRINTERPROFILE=<your printer profile ID>\n" +
                    "to your Printers Start GCODE.\n")

    if len(v.splice_extruder_position) == 0:
        log_warning("This does not look like a multi-colour file.\n")
        if v.gui:
            if gui.ask_yes_no('Not a Multi-Colour file?', "This doesn't look like a multi-colour file. Skip processing?"):
                exit(1)
        else:
            if yes_or_no("This does not look like a multi-colour file.. Skip P2PP Processing?\n"):
                exit(1)

    algorithm_create_table()

    header = []
    summary = []
    warnings = []

    header.append('O21 ' + hexify_short(20) + "\n")  # MSF2.0

    if v.printer_profile_string == '':
        v.printer_profile_string = v.default_printerprofile
        log_warning("No or Invalid Printer profile ID specified, using default P2PP printer profile ID {}"
                    .format(v.default_printerprofile))

    header.append('O22 D' + v.printer_profile_string.strip("\n") + "\n")  # PRINTERPROFILE used in Palette2
    header.append('O23 D0001' + "\n")              # unused
    header.append('O24 D0000' + "\n")              # unused

    header.append("O25 ")

    for i in range(4):
        if v.palette_inputs_used[i]:
            if v.filament_type[i] == "":
                log_warning(
                    "Filament #{} is missing Material Type, make sure to add" +
                    " ;P2PP FT=[filament_type] to filament GCode".format(i))
            if v.filament_color_code[i] == "-":
                log_warning(
                    "Filament #{} is missing Color info, make sure to add" +
                    ";P2PP FC=[extruder_colour] to filament GCode".format(i))
                v.filament_color_code[i] = '000000'

            header.append("D{}{}{}_{} ".format(v.used_filament_types.index(v.filament_type[i]) + 1,
                                               v.filament_color_code[i].strip("\n"),
                                               find_nearest_colour(v.filament_color_code[i].strip("\n")),
                                               v.filament_type[i].strip("\n")
                                               ))
        else:
            header.append("D0 ")

    header.append("\n")

    header.append('O26 ' + hexify_short(len(v.splice_extruder_position)) + "\n")
    header.append('O27 ' + hexify_short(len(v.ping_extruder_position)) + "\n")
    if len(v.splice_algorithm_table) > 9:
        log_warning("ATTENTION: THIS FILE WILL NOT POTENTIALLY NOT WORK CORRECTLY DUE TO A BUG IN PALETTE2 PLUGIN")
        header.append("O28 D{:0>4d}\n".format(len(v.splice_algorithm_table)))
    else:
        header.append('O28 ' + hexify_short(len(v.splice_algorithm_table)) + "\n")
    header.append('O29 ' + hexify_short(v.hotswap_count) + "\n")

    for i in range(len(v.splice_extruder_position)):
        header.append("O30 D{:0>1d} {}\n".format(v.splice_used_tool[i],
                                                 hexify_float(v.splice_extruder_position[i])
                                                 )
                      )

    for i in range(len(v.splice_algorithm_table)):
        header.append("O32 {}\n"
                      .format(v.splice_algorithm_table[i]))

    if len(v.splice_extruder_position) > 0:
        header.append("O1 D{} {}\n"
                      .format(job_name, hexify_long(int(v.splice_extruder_position[-1] + 0.5))))
    else:
        header.append("O1 D{} {}\n"
                      .format(job_name, hexify_long(int(v.total_material_extruded + v.splice_offset + 0.5))))

    if not v.accessory_mode:
        header.append("M0\n")
        header.append("T0\n")

    summary.append(";---------------------:\n")
    summary.append("; - SPLICE INFORMATION:\n")
    summary.append(";---------------------:\n")
    summary.append(";       Splice Offset = {:-8.2f}mm\n\n".format(v.splice_offset))

    for i in range(len(v.splice_extruder_position)):
        summary.append(";{:04}   Tool: {}  Location: {:-8.2f}mm   length {:-8.2f}mm \n"
                       .format(i + 1,
                               v.splice_used_tool[i],
                               v.splice_extruder_position[i],
                               v.splice_length[i],
                               )
                       )

    summary.append("\n")
    summary.append(";-------------------:\n")
    summary.append("; - PING INFORMATION:\n")
    summary.append(";-------------------:\n")

    for i in range(len(v.ping_extruder_position)):
        summary.append(";Ping {:04} at {:-8.2f}mm\n".format(i + 1,
                                                            v.ping_extruder_position[i]
                                                            )
                       )

    if v.side_wipe and v.side_wipe_loc == "":
        log_warning("Using sidewipe with undefined SIDEWIPELOC!!!")

    warnings.append("\n")
    warnings.append(";------------------------:\n")
    warnings.append("; - PROCESS INFO/WARNINGS:\n")
    warnings.append(";------------------------:\n")

    warnings.append(";Generated with P2PP version {}\n".format(v.version))
    warnings.append(";Processed file:. {}\n".format(v.filename))

    if len(v.process_warnings) == 0:
        warnings.append(";No warnings\n")
    else:
        for i in range(len(v.process_warnings)):
            warnings.append("{}\n".format(v.process_warnings[i]))

    return {'header': header, 'summary': summary, 'warnings': warnings}


def yes_or_no(question):
    answer = raw_input(question + "([Y]es/[N]o): ").lower().strip()
    print("")
    while not(answer == "y" or answer == "yes" or answer == "n" or answer == "no"):
        print("Input yes or no")
        answer = raw_input(question + "([Y]es/[N]o):").lower().strip()
        print("")
    if answer[0] == "y":
        return True
    else:
        return False
