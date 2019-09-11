__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'


import p2pp.gcodeparser as gp
import p2pp.variables as v

wipe_command = []
wipe_length  = []
wipe_posx    = []
wipe_posy    = []
wipe_index    = -1
wipe_height = 0
last_wipe_x  = -1
last_wipe_y  = -1

tower_start_x = None
tower_start_y = None

tower_xmin = -1
tower_xmax = -1
tower_ymin = -1
tower_y_max = -1

totalpurge = 0      #float - maximum amounf of purge per layer

purgperlayer = []
maxindex = 0


def analyze_purge_info():
    global tower_start_x, tower_start_y, _last_wipe_x, last_wipe_y, wipe_index, max_index
    global tower_xmin, tower_xmax, tower_ymin, tower_ymax
    global totalpurge
    # analyze purge information from the raw input file
    l = 0

    copycode = False
    while l < len(v.input_gcode):
        gcode = v.input_gcode[l].strip()
        l=l+1
        if gcode.startswith("; CP WIPE TOWER FIRST LAYER BRIM END"):
            copycode = True
            continue


        if gcode.startswith("; CP EMPTY GRID END"):
            break

        if copycode:
            to_x = gp.get_gcode_parameter(gcode, "X")
            to_y = gp.get_gcode_parameter(gcode, "Y")
            if not tower_start_x:
                tower_start_x = to_x
            if not tower_start_y:
                tower_start_y = to_y

            if gcode.startswith("G1"):
                pos = gcode.find("F")
                if pos != -1:
                    gcode = (gcode[0:pos-1]).strip()
                e_move = gp.get_gcode_parameter(gcode, "E")
                if not e_move:
                    e_move = 0
                totalpurge += e_move
                wipe_command.append(gcode)
                wipe_length.append(e_move)
                wipe_posx.append(to_x)
                wipe_posy.append(to_y)
        max_index = len(wipe_command)

        tower_xmin = min(wipe_posx)
        tower_xmax = max(wipe_posx)
        tower_ymin = min(wipe_posy)
        tower_ymax = max(wipe_posy)

def generatepurge( length , speed ):
    global tower_start_x, tower_start_y, last_wipe_x, last_wipe_y, wipe_index, wipe_height

    # go to wipe position
    if wipe_index == -1:
        last_wipe_x = tower_start_x
        last_wipe_y = tower_start_y
        wipe_index = 0
        wipe_height = v.layer_height

    v.processed_gcode.append("; --- P2PP WIPE SEQUENCE START  FOR {:5.2f}mm--\n".format(length))
    v.processed_gcode.append("G1 F{}\n".format(speed))
    v.processed_gcode.append("G1 X{} Y{}\n".format(last_wipe_x, last_wipe_y))
    v.processed_gcode.append("G1 Z{} F10800\n".format(wipe_height))

    # generate wipe code

    purged = 0
    while purged < length:
        v.processed_gcode.append(wipe_command[wipe_index]+"\n")
        if wipe_posx[wipe_index]:
            last_wipe_x = wipe_posx[wipe_index]
        if wipe_posy[wipe_index]:
            last_wipe_y = wipe_posy[wipe_index]
        purged += wipe_length[wipe_index]
        wipe_index += 1
        if wipe_index == max_index:
            wipe_height += v.layer_height
            v.processed_gcode.append("G1 Z{} F10800\n".format(wipe_height))
            wipe_index = 0


    # save wipe position

    # return to print height
    v.processed_gcode.append("G1 Z{} F10800\n".format(v.current_position_z))
    v.processed_gcode.append("; --- P2PP WIPE SEQUENCE END  DONE {:5.2f}mm--\n".format(purged))
    return purged

def generateemptyframe ():
    # generate empty frame on print
    #
    purged = 0
    v.processed_gcode.append("; --- P2PP EMPTY FRAME\n")
    v.processed_gcode.append("G1 F{}\n".format(speed))
    v.processed_gcode.append("G1 X{} Y{}\n".format(last_wipe_x, last_wipe_y))
    v.processed_gcode.append("G1 Z{} F10800\n".format(wipe_height))
    v.processed_gcode.append("; --- P2PP WIPE SEQUENCE END  DONE {:5.2f}mm--\n".format(purged))
    pass

