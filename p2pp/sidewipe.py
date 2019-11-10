__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v


def create_side_wipe():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

    v.after_side_wipe = True
    v.processed_gcode.append(";---------------------------\n")
    v.processed_gcode.append(";  P2PP SIDE WIPE: {:7.3f}mm\n".format(v.side_wipe_length))

    for line in v.before_sidewipe_gcode:
        v.processed_gcode.append(line + "\n")

    if not v.user_firemware_retraction:
        v.processed_gcode.append("G1 E{}\n".format(-v.retract_length[v.current_tool]))
    else:
        v.processed_gcode.append("G10")

    v.processed_gcode.append("G1 F8640\n")
    v.processed_gcode.append("G0 {} Y{}\n".format(v.side_wipe_loc, v.sidewipe_miny))

    sweep_base_speed = v.wipe_feedrate * 20 * abs(v.sidewipe_maxy - v.sidewipe_miny) / 150
    sweep_length = 20

    yrange = [v.sidewipe_maxy, v.sidewipe_miny]
    rangeidx = 0
    moveto = yrange[rangeidx]

    while v.side_wipe_length > 0:
        sweep = min(v.side_wipe_length, sweep_length)
        v.side_wipe_length -= sweep_length
        wipe_speed = min(5000, int(sweep_base_speed / sweep))

        v.processed_gcode.append(
            "G1 {} Y{} E{:.5f} F{}\n".format(v.side_wipe_loc, moveto, sweep * v.sidewipe_correction, wipe_speed))

        rangeidx += 1
        moveto = yrange[rangeidx % 2]

    for line in v.after_sidewipe_gcode:
        v.processed_gcode.append(line + "\n")

    if not v.user_firemware_retraction:
        v.processed_gcode.append("G1 E{}\n".format(v.retract_length[v.current_tool]))
    else:
        v.processed_gcode.append("G11")

    v.processed_gcode.append(";---------------------------\n")

    v.side_wipe_length = 0
