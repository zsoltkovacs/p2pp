__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.purgetower as purgetower
import p2pp.variables as v


#
# to be implemented - Big Brain 3D purge mechanism support
#


def setfanspeed(n):
    if n == 0:
        v.processed_gcode.append("M107")
    else:
        v.processed_gcode.append("M106 S{}".format(n))


def resetfanspeed():
    setfanspeed(v.saved_fanspeed)


def generate_blob(n):
    v.processed_gcode.append(";---- BIGBRAIN3D SIDEWIPE BLOB -- purge {:.3f}mm\n".format(n))
    # v.processed_gcode.append("M907 X{} ; set motor power\n".format(int(v.purgemotorpower)))
    v.processed_gcode.append("G1 X200 F10800 ; go near the edge of the print\n")
    v.processed_gcode.append("G4 S0 ; wait for the print buffer to clear\n")
    v.processed_gcode.append("G1 X249.5 F3000 ; go near the edge of the print\n")
    v.processed_gcode.append(
        "G1 X{} F1000; go to the actual wiping position\n".format(v.bigbrain3d_x_position))  # takes 2.5 seconds
    setfanspeed(0)
    purgetower.unretract()
    v.processed_gcode.append("G1 E{:6.3f}".format(n))
    purgetower.retract()
    setfanspeed(255)
    v.processed_gcode.append("G4 S{:03} ; blob cooling time\n".forat(v.bigbrain3d_blob_cooling_time))
    v.processed_gcode.append("G1 X240 F10800 ; go near the edge of the print\n")


def create_sidewipe_BigBrain3D(purgesize):
    purgetower.retract(v.current_tool)

    while purgesize > 0:
        blob = min(v.bigbrain3d_blob_size, purgesize)
        if (purgesize - blob) < 10:
            blob += purgesize
            purgesize = 0
        generate_blob(blob)

    purgetower.unretract(v.current_tool)

    resetfanspeed()

    pass




def create_side_wipe():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

    v.after_side_wipe = True
    v.processed_gcode.append(";---------------------------\n")
    v.processed_gcode.append(";  P2PP SIDE WIPE: {:7.3f}mm\n".format(v.side_wipe_length))

    for line in v.before_sidewipe_gcode:
        v.processed_gcode.append(line + "\n")

    if v.retraction == 0:
        purgetower.retract(v.current_tool)

    v.processed_gcode.append("G1 F8640\n")
    v.processed_gcode.append("G0 {} Y{}\n".format(v.side_wipe_loc, v.sidewipe_miny))

    sweep_base_speed = v.wipe_feedrate * 20 * abs(v.sidewipe_maxy - v.sidewipe_miny) / 150
    sweep_length = 20

    yrange = [v.sidewipe_maxy, v.sidewipe_miny]
    rangeidx = 0
    moveto = yrange[rangeidx]

    purgetower.unretract()

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

    purgetower.retract()
    v.processed_gcode.append(";---------------------------\n")

    v.side_wipe_length = 0
