__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v


def if_defined(x, y):
    if x:
        return x
    return y


def generate_purge_sequence():
    if not v.side_wipe_length > 0:
        return

    v.processed_gcode.append("; --------------------------------------------------\n")
    v.processed_gcode.append("; --- P2PP WIPE SEQUENCE START  FOR {:5.2f}mm\n".format(v.side_wipe_length))
    v.processed_gcode.append("; --------------------------------------------------\n")
    v.processed_gcode.append("G1 F{}\n".format(v.wipe_feedrate))
    v.processed_gcode.append("G1 X{} Y{}\n".format(v.purge_last_posx, v.purge_last_posy))
    v.processed_gcode.append("G1 Z{} F10800\n".format(v.purgelayer * v.layer_height))

    # generate wipe code
    while v.side_wipe_length > 0:

        tmp = v.purgetower[v.purge_current_index]
        tmp.issue_command()

        v.purge_last_posx = if_defined(tmp.X, v.purge_last_posx)
        v.purge_last_posy = if_defined(tmp.Y, v.purge_last_posy)
        v.side_wipe_length -= if_defined(tmp.E, 0)

        v.purge_current_index = (v.purge_current_index + 1) % len(v.purgetower)

        if v.purge_current_index == 0:
            v.purgelayer += 1
            if v.side_wipe_length > 0:
                v.processed_gcode.append("G1 Z{} F10800\n".format(v.purgelayer * v.layer_height))

    # return to print height
    v.processed_gcode.append("; -------------------------------------\n")
    v.processed_gcode.append("G1 Z{} F10800\n".format(v.current_position_z))
    v.processed_gcode.append("; --- P2PP WIPE SEQUENCE END DONE\n")
    v.processed_gcode.append("; -------------------------------------\n")

    # if we extruded more we need to account for that in the total count
    correction = -v.side_wipe_length * v.extrusion_multiplier * v.extrusion_multiplier_correction
    v.total_material_extruded += correction
    v.material_extruded_per_color[v.current_tool] += correction
    v.side_wipe_length = 0
