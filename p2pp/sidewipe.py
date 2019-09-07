__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v
from p2pp.gcodeparser import get_gcode_parameter



def coordinate_in_tower(x, y):
    if x < v.wipe_tower_info['minx']:
        return False
    if x > v.wipe_tower_info['maxx']:
        return False
    if y < v.wipe_tower_info['miny']:
        return False
    if y > v.wipe_tower_info['maxy']:
        return False
    return True

def create_side_wipe():
    if not v.side_wipe:
        return

    v.processed_gcode.append(";P2PP SIDE WIPE CODE\n")
    v.processed_gcode.append(";-------------------\n")
    v.processed_gcode.append(";  Side wipe length: {}mm\n".format(v.side_wipe_length))

    if (v.max_wipe > 0) and (v.side_wipe_length > v.max_wipe):
        v.total_material_extruded = v.total_material_extruded - v.side_wipe_length + v.max_wipe
        v.side_wipe_length = v.max_wipe * v.extrusion_multiplier

    if v.side_wipe_length > 0:
        for line in v.before_sidewipe_gcode:
            v.processed_gcode.append(line + "\n")

        retract()
        v.processed_gcode.append("G1 F8640\n")
        v.processed_gcode.append("G0 {} Y{}\n".format(v.side_wipe_loc, v.sidewipe_miny))
        sweep_base_speed = v.wipe_feedrate * 20 * abs(v.sidewipe_maxy - v.sidewipe_miny) / 150
        sweep_length = 20
        feed_rate = -1

        moveto = v.sidewipe_maxy

        while v.side_wipe_length > 0:
            sweep = min(v.side_wipe_length, sweep_length)
            v.side_wipe_length -= sweep_length

            wipe_speed = int(sweep_base_speed / sweep)
            wipe_speed = min(wipe_speed, 5000)
            if feed_rate != wipe_speed:
                v.processed_gcode.append("G1 F{}\n".format(wipe_speed))
                feed_rate = wipe_speed

            v.processed_gcode.append("G1 {} Y{} E{}\n".format(v.side_wipe_loc, moveto, sweep * v.sidewipe_correction))

            if moveto == v.sidewipe_maxy:
                moveto = v.sidewipe_miny
            else:
                moveto = v.sidewipe_maxy

        v.processed_gcode.append(";-------------------\n")
        v.side_wipe_length = 0
        for line in v.after_sidewipe_gcode:
            v.processed_gcode.append(line + "\n")


def unretract():
    v.processed_gcode.append("G1 E{}\n".format(v.sidewipe_retract))
    v.total_material_extruded += v.sidewipe_retract * v.extrusion_multiplier * v.extrusion_multiplier_correction
    v.wipe_retracted = False

def retract():
    v.processed_gcode.append("G1 E{}\n".format(-v.sidewipe_retract))
    v.total_material_extruded -= v.sidewipe_retract * v.extrusion_multiplier * v.extrusion_multiplier_correction
    v.wipe_retracted = True


def retro_cleanup():
    # retrospective cleanup of generated code AFTER detecting a purge volume in print
    # if v.isReprap_Mode:
    #     look_for = "M572"
    # else:
    #     look_for = "M900"
    # if not v.side_wipe:
    #     return
    # idx = len(v.processed_gcode) - 1
    # while idx > -1 and not v.processed_gcode[idx].startswith(look_for):
    #     if v.processed_gcode[idx][0:1] == "G1":
    #         extruder_movement = get_gcode_parameter(v.processed_gcode[idx], "E")
    #         if extruder_movement != "":
    #             v.side_wipe_length += extruder_movement
    #     if not v.processed_gcode[idx].startswith("M73"):
    #         v.processed_gcode[idx] = ";--- P2PP removed [Retro Correction]" + v.processed_gcode[idx]
    #     idx -= 1

    pos = len(v.processed_gcode) - 1
    while pos > 0:
        if v.processed_gcode[pos].startswith("G1"):
            _x = get_gcode_parameter(v.processed_gcode[pos], "X")
            _y = get_gcode_parameter(v.processed_gcode[pos], "Y")

            if _x and _y:
                if coordinate_in_tower(_x,_y):
                    v.processed_gcode[pos] = ";--- P2PP removed [Tower Delta] - {}".format(v.processed_gcode[pos])
                    break
        pos = pos - 1


def sidewipe_toolchange_start():
    if v.side_wipe:
        v.side_wipe_length = 0
        v.wipe_start_extrusion = v.total_material_extruded
        retro_cleanup()


def collect_wipetower_info(line):
    if line.startswith("; CP WIPE TOWER FIRST LAYER BRIM START"):
        v.define_tower = True

    if line.startswith("; CP WIPE TOWER FIRST LAYER BRIM END"):
        v.define_tower = False
        v.wipe_tower_info['minx'] -= 2
        v.wipe_tower_info['miny'] -= 2
        v.wipe_tower_info['maxx'] += 2
        v.wipe_tower_info['maxy'] += 2
        v.processed_gcode.append("; TOWER COORDINATES ({:-8.2f},{:-8.2f}) to ({:-8.2f},{:-8.2f})\n".format(
            v.wipe_tower_info['minx'], v.wipe_tower_info['miny'], v.wipe_tower_info['maxx'], v.wipe_tower_info['maxy']
        ))

    if line.startswith("; CP WIPE TOWER FIRST LAYER BRIM START") or line.startswith("; CP EMPTY GRID START"):
        if not v.within_tool_change_block:
            retro_cleanup()
            v.side_wipe_skip = v.side_wipe

    if line.startswith("; CP WIPE TOWER FIRST LAYER BRIM END") or line.startswith("; CP EMPTY GRID END"):
        v.side_wipe_skip = False

    if line.startswith("G"):
        parm_x = get_gcode_parameter(line, "X")
        parm_y = get_gcode_parameter(line, "Y")

        if parm_x:
            if v.define_tower:
                v.wipe_tower_info['maxx'] = max(v.wipe_tower_info['maxx'], parm_x)
                v.wipe_tower_info['minx'] = min(v.wipe_tower_info['minx'], parm_x)
            if not v.side_wipe_skip:
                v.current_position_x = parm_x

        if parm_y:
            if v.define_tower:
                v.wipe_tower_info['maxy'] = max(v.wipe_tower_info['maxy'], parm_y)
                v.wipe_tower_info['miny'] = min(v.wipe_tower_info['miny'], parm_y)
            if not v.side_wipe_skip:
                v.current_position_y = parm_y
