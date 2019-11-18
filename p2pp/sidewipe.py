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
        v.processed_gcode.append("M107                ; Turn FAN OFF\n")
    else:
        v.processed_gcode.append("M106 S{}           ; Set FAN Power\n".format(n))


def resetfanspeed():
    setfanspeed(v.saved_fanspeed)


def generate_blob(length, count):
    v.processed_gcode.append("\n;---- BIGBRAIN3D SIDEWIPE BLOB {} -- purge {:.3f}mm\n".format(count + 1, length))
    # v.processed_gcode.append("M907 X{} ; set motor power\n".format(int(v.purgemotorpower)))

    v.processed_gcode.append(
        "G1 X{:.3f} F3000   ; go near the edge of the print\n".format(v.bigbrain3d_x_position - 10))
    v.processed_gcode.append(
        "G1 X{:.3f} F1000   ; go to the actual wiping position\n".format(v.bigbrain3d_x_position))  # takes 2.5 seconds
    setfanspeed(0)
    if v.retraction < 0:
        purgetower.unretract(v.current_tool, 1200)
    if v.bigbrain3d_smartfan:
        v.processed_gcode.append("G1 E{:6.3f} F200     ; Purge FAN OFF \n".format(length / 4))
        setfanspeed(64)
        v.processed_gcode.append("G1 E{:6.3f} F200     ; Purge FAN 25% \n".format(length / 4))
        setfanspeed(128)
        v.processed_gcode.append("G1 E{:6.3f} F200     ; Purge FAN 50% \n".format(length / 4))
        setfanspeed(192)
        v.processed_gcode.append("G1 E{:6.3f} F200     ; Purge FAN 75% \n".format(length / 4))
    else:
        v.processed_gcode.append("G1 E{:6.3f} F200     ; UNRETRACT/PURGE/RETRACT \n".format(length))
    purgetower.retract(v.current_tool, 1200)
    setfanspeed(255)
    v.processed_gcode.append(
        "G4 S{0:.0f}              ; blob {0}s cooling time\n".format(v.bigbrain3d_blob_cooling_time))
    v.processed_gcode.append("G1 X{:.3f} F10800  ; activate flicker\n".format(v.bigbrain3d_x_position - 20))
    v.processed_gcode.append(
        "G4 S1               ; Mentally prep for second whack\n".format(v.bigbrain3d_x_position - 20))
    v.processed_gcode.append("G1 X{:.3f} F3000   ; approach for second whach\n".format(v.bigbrain3d_x_position - 10))
    v.processed_gcode.append("G1 X{:.3f} F1000   ; final position for whack and......\n".format(
        v.bigbrain3d_x_position))  # takes 2.5 seconds
    v.processed_gcode.append("G1 X{:.3f} F10800  ; WHACKAAAAA!!!!\n".format(v.bigbrain3d_x_position - 20))
def create_sidewipe_BigBrain3D():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

    # purge blobs should all be same size
    purgeleft = v.side_wipe_length % v.bigbrain3d_blob_size
    purgeblobs = int(v.side_wipe_length / v.bigbrain3d_blob_size)

    if purgeleft > 1:
        purgeblobs += 1
        correction = v.bigbrain3d_blob_size - purgeleft
    else:
        correction = -purgeleft

    v.processed_gcode.append(";-------------------------------\n")
    v.processed_gcode.append("; P2PP BB3DBLOBS: {:.0f} BLOBS\n".format(purgeblobs))
    v.processed_gcode.append(";-------------------------------\n")


    v.processed_gcode.append(
        "; Req={:.2f}mm  Act={:.2f}mm\n".format(v.side_wipe_length, v.side_wipe_length + correction))
    v.processed_gcode.append("; Purge difference {:.2f}mm\n".format(correction))
    v.processed_gcode.append(";-------------------------------\n")

    v.total_material_extruded += correction * v.extrusion_multiplier * v.extrusion_multiplier_correction
    v.material_extruded_per_color[
        v.current_tool] += correction * v.extrusion_multiplier * v.extrusion_multiplier_correction

    if v.retraction == 0:
        purgetower.retract(v.current_tool)

    if (v.current_position_z < 25):
        v.processed_gcode.append("\nG1 Z25.000 F8640    ; Increase Z to prevent collission with bed\n")

    v.processed_gcode.append("G1 X{:.3f} F10800  ; go near edge of bed\n".format(v.bigbrain3d_x_position - 30))
    v.processed_gcode.append("G4 S0               ; wait for the print buffer to clear\n")
    v.processed_gcode.append("M907 X{}           ; increase motor power\n".format(v.bigbrain3d_motorpower_high))
    for i in range(purgeblobs):
        generate_blob(v.bigbrain3d_blob_size, i)

    # NOT NEEDED
    # if (v.current_position_z < 25):
    #     v.processed_gcode.append("\nG1 Z{:.4f} F8640    ; Reset correct Z height to continue print\n".format(v.current_position_z))

    resetfanspeed()
    v.processed_gcode.append("\nM907 X{}           ; reset motor power\n".format(v.bigbrain3d_motorpower_normal))
    v.processed_gcode.append("\n;-------------------------------\n\n")

    v.side_wipe_length = 0




def create_side_wipe():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

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

    purgetower.unretract(v.current_tool)

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

    purgetower.retract(v.current_tool)
    v.processed_gcode.append(";---------------------------\n")

    v.side_wipe_length = 0
