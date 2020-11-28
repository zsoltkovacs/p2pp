__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import os
import time

import p2pp.gcode as gcode
import p2pp.gui as gui
import p2pp.p2_m4c as m4c
import p2pp.parameters as parameters
import p2pp.pings as pings
import p2pp.purgetower as purgetower
import p2pp.variables as v
from p2pp.gcodeparser import parse_slic3r_config
from p2pp.omega import header_generate_omega, algorithm_process_material_configuration
from p2pp.sidewipe import create_side_wipe, create_sidewipe_bb3d


# layer_regex = re.compile(";LAYER\s+(\d+)\s*")
# layerheight_regex = re.compile(";LAYERHEIGHT\s+(\d+(\.\d+)?)\s*")


def optimize_tower_skip(max_layers):
    skippable = v.skippable_layer.count(True)

    idx = 1
    while skippable > max_layers:
        if v.skippable_layer[idx]:
            v.skippable_layer[idx] = False
            skippable -= 1
        idx += 1

    if skippable > 0:
        gui.log_warning(
            "Tower delta in effect: {} Layers or {:.2f}mm".format(skippable, skippable * v.layer_height))
    else:
        gui.create_logitem("Tower Purge Delta could not be applied to this print")


def gcode_process_toolchange(new_tool):
    if new_tool == v.current_tool:
        return

    location = v.total_material_extruded + v.splice_offset

    if new_tool == -1:
        location += v.extra_runout_filament
        v.material_extruded_per_color[v.current_tool] += v.extra_runout_filament
        v.total_material_extruded += v.extra_runout_filament
    else:
        v.palette_inputs_used[new_tool] = True

    length = location - v.previous_toolchange_location

    if v.current_tool != -1:

        v.splice_extruder_position.append(location)
        v.splice_length.append(length)
        v.splice_used_tool.append(v.current_tool)

        if len(v.splice_extruder_position) == 1:
            min_length = v.min_start_splice_length
            gui_format = "Warning : Short first splice (<{}mm) Length:{:-3.2f} Layer {} Input {}"
        else:
            min_length = v.min_splice_length
            gui_format = "Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}"

        if v.splice_length[-1] < min_length:
            if v.autoaddsplice and (v.full_purge_reduction or v.side_wipe):
                v.autoadded_purge = v.min_start_splice_length - length
                v.side_wipe_length += v.autoadded_purge
                v.splice_extruder_position[-1] += v.autoadded_purge
                v.splice_length[-1] += v.autoadded_purge
            else:
                gui.log_warning(gui_format.format(length, min_length, v.last_parsed_layer, v.current_tool + 1))
                v.filament_short[new_tool] = max(v.filament_short[new_tool],
                                                 v.min_start_splice_length - v.splice_length[-1])

        v.previous_toolchange_location = v.splice_extruder_position[-1]

    v.previous_tool = v.current_tool
    v.current_tool = new_tool


def calculate_temp_wait_position():
    x_offset = 2 + 4 * v.extrusion_width
    y_offset = 2 + 8 * v.extrusion_width

    if abs(v.wipe_tower_info_minx - v.purge_keep_x) < abs(v.wipe_tower_info_maxx - v.purge_keep_x):
        pos_x = v.wipe_tower_info_minx + x_offset
    else:
        pos_x = v.wipe_tower_info_maxx - x_offset

    if abs(v.wipe_tower_info_miny - v.purge_keep_y) < abs(v.wipe_tower_info_maxy - v.purge_keep_y):
        pos_y = v.wipe_tower_info_miny + y_offset
    else:
        pos_y = v.wipe_tower_info_maxy - y_offset

    return [pos_x, pos_y]


def inrange(number, low, high):
    if number is None:
        return True
    return low <= number <= high


def y_on_bed(y):
    return inrange(y, v.bed_origin_y, v.bed_origin_y + v.bed_size_y)


def x_on_bed(x):
    return inrange(x, v.bed_origin_x, v.bed_origin_x + v.bed_size_x)


def coordinate_on_bed(x, y):
    return x_on_bed(x) and y_on_bed(y)


def x_coordinate_in_tower(x):
    return inrange(x, v.wipe_tower_info_minx, v.wipe_tower_info_maxx)


def y_coordinate_in_tower(y):
    return inrange(y, v.wipe_tower_info_miny, v.wipe_tower_info_maxy)


def coordinate_in_tower(x, y):
    return v.wipe_tower_info_minx <= x <= v.wipe_tower_info_maxx and v.wipe_tower_info_miny <= y <= v.wipe_tower_info_maxy


def entertower(layer_hght):
    purgeheight = layer_hght - v.cur_tower_z_delta
    if v.current_position_z != purgeheight:
        v.max_tower_delta = max(v.cur_tower_z_delta, v.max_tower_delta)
        gcode.issue_code(";------------------------------", True)
        gcode.issue_code(";  P2PP DELTA ENTER", True)
        gcode.issue_code(";  Current Z-Height = {:.2f}".format(v.current_position_z), True)
        gcode.issue_code(";  Tower height = {:.2f}".format(purgeheight), True)
        gcode.issue_code(";  Tower delta = {:.2f} ".format(v.current_position_z - purgeheight), True)
        gcode.issue_code(";------------------------------", True)

        if v.retraction >= 0:
            purgetower.retract(v.current_tool)
        gcode.issue_code("G1 X{} Y{} F8640".format(v.current_position_x, v.current_position_y))
        gcode.issue_code("G1 Z{:.2f} F10810".format(purgeheight))

        if purgeheight <= 0.21:
            gcode.issue_code("G1 F{}".format(min(1200, v.wipe_feedrate)))
        else:
            gcode.issue_code("G1 F{}".format(v.wipe_feedrate))


CLS_UNDEFINED = 0
CLS_NORMAL = 1
CLS_TOOL_START = 2
CLS_TOOL_UNLOAD = 4
CLS_TOOL_PURGE = 8
CLS_EMPTY = 16
CLS_BRIM = 32
CLS_BRIM_END = 64
CLS_ENDGRID = 128
CLS_COMMENT = 256
CLS_ENDPURGE = 512
CLS_TONORMAL = 1024
CLS_TOOLCOMMAND = 2048

hash_FIRST_LAYER_BRIM_START = hash("WIPE TOWER FIRST LAYER BRIM START")
hash_FIRST_LAYER_BRIM_END = hash("WIPE TOWER FIRST LAYER BRIM END")
hash_EMPTY_GRID_START = hash("EMPTY GRID START")
hash_EMPTY_GRID_END = hash("EMPTY GRID END")
hash_TOOLCHANGE_START = hash("TOOLCHANGE START")
hash_TOOLCHANGE_UNLOAD = hash("TOOLCHANGE UNLOAD")
hash_TOOLCHANGE_WIPE = hash("TOOLCHANGE WIPE")
hash_TOOLCHANGE_END = hash("TOOLCHANGE END")


def update_class(gcode_line):
    line_hash = hash(gcode_line)  # drop "; CP "

    if line_hash == hash_EMPTY_GRID_START:
        v.block_classification = CLS_EMPTY
        v.layer_emptygrid_counter += 1
        return

    if line_hash == hash_EMPTY_GRID_END:
        v.block_classification = CLS_ENDGRID
        return

    if line_hash == hash_TOOLCHANGE_START:
        v.block_classification = CLS_TOOL_START
        v.layer_toolchange_counter += 1
        return

    if line_hash == hash_TOOLCHANGE_UNLOAD:
        v.block_classification = CLS_TOOL_UNLOAD
        return

    if line_hash == hash_TOOLCHANGE_WIPE:
        v.block_classification = CLS_TOOL_PURGE
        return

    if line_hash == hash_TOOLCHANGE_END:
        if v.previous_block_classification == CLS_TOOL_UNLOAD:
            v.block_classification = CLS_NORMAL
        else:
            if v.previous_block_classification == CLS_TOOL_PURGE:
                v.block_classification = CLS_ENDPURGE
            else:
                v.block_classification = CLS_TONORMAL
        return

    if line_hash == hash_FIRST_LAYER_BRIM_START:
        v.block_classification = CLS_BRIM
        v.tower_measure = True
        return

    if line_hash == hash_FIRST_LAYER_BRIM_END:
        v.tower_measure = False
        v.wipe_tower_info_minx -= 2 * v.extrusion_width
        v.wipe_tower_info_maxx += 2 * v.extrusion_width
        v.wipe_tower_info_miny -= 4 * v.extrusion_width
        v.wipe_tower_info_maxy += 4 * v.extrusion_width
        v.wipe_tower_xsize = v.wipe_tower_info_maxx - v.wipe_tower_info_minx
        v.wipe_tower_ysize = v.wipe_tower_info_maxy - v.wipe_tower_info_miny
        v.block_classification = CLS_BRIM_END
        return


def add_point_to_tower(x, y):
    if x:
        v.wipe_tower_info_minx = min(v.wipe_tower_info_minx, x)
        v.wipe_tower_info_maxx = max(v.wipe_tower_info_maxx, x)
    if y:
        v.wipe_tower_info_miny = min(v.wipe_tower_info_miny, y)
        v.wipe_tower_info_maxy = max(v.wipe_tower_info_maxy, y)


def create_tower_gcode():
    purgetower.purge_create_layers(v.wipe_tower_info_minx, v.wipe_tower_info_miny, v.wipe_tower_xsize,
                                   v.wipe_tower_ysize)
    gui.create_logitem(
        " Purge Tower :X{:.2f} Y{:.2f}  W{:.2f} H{:.2f}".format(v.wipe_tower_info_minx, v.wipe_tower_info_miny,
                                                                v.wipe_tower_xsize, v.wipe_tower_ysize))
    gui.create_logitem(
        " Layer Length Solid={:.2f}mm   Sparse={:.2f}mm".format(purgetower.sequence_length_solid,
                                                                purgetower.sequence_length_empty))


def parse_gcode():
    v.layer_toolchange_counter = 0
    v.layer_emptygrid_counter = 0

    v.block_classification = CLS_NORMAL
    v.previous_block_classification = CLS_NORMAL
    total_line_count = len(v.input_gcode)

    flh = int(v.first_layer_height * 100)
    olh = int(v.layer_height * 100)
    use_layer_instead_of_layerheight = v.synced_support or not v.support_material

    backpass_line = -1
    jndex = 0
    v.side_wipe_towerdefined = False

    for index in range(total_line_count):

        v.previous_block_classification = v.block_classification

        line = v.input_gcode[jndex]
        jndex += 1

        if jndex == 100000:
            gui.progress_string(4 + 46 * index // total_line_count)
            v.input_gcode = v.input_gcode[jndex:]
            jndex = 0

        if line.startswith(';'):

            # try finding a P2PP configuration command
            # until config_end command is encountered

            is_comment = True

            if line.startswith('; CP'):  # code block assignment
                update_class(line[5:])

            elif line.startswith(';LAYER'):  # Layer instructions

                fields = line.split(' ')
                layer = None

                if use_layer_instead_of_layerheight and len(fields[0]) == 6:
                    try:
                        layer = int(fields[1])
                    except (ValueError, IndexError):
                        pass

                elif fields[0][6:] == 'HEIGHT':
                    try:
                        lv = int((float(fields[1]) + 0.001) * 100)
                        lv = lv - flh
                        if lv % olh == 0:
                            layer = int(lv / olh)
                    except (ValueError, IndexError):
                        pass

                if layer is not None:
                    v.last_parsed_layer = layer
                    v.layer_end.append(index)
                    if layer > 0:
                        v.skippable_layer.append((v.layer_emptygrid_counter > 0) and (v.layer_toolchange_counter == 0))
                        v.layer_toolchange_counter = 0
                        v.layer_emptygrid_counter = 0

            else:
                if not v.p2pp_configend or v.set_tool > 3 or v.p2pp_tool_unconfigged[v.set_tool]:
                    m = v.regex_p2pp.match(line)
                    if m:
                        if m.group(1).startswith("MATERIAL"):
                            algorithm_process_material_configuration(m.group(1)[9:])
                        else:
                            parameters.check_config_parameters(m.group(1), m.group(2))

        else:
            is_comment = False
            try:
                if line[0] == 'T':
                    v.block_classification = CLS_TOOL_PURGE
                    cur_tool = int(line[1])
                    if v.set_tool != -1 and v.set_tool < 4:
                        v.p2pp_tool_unconfigged[v.set_tool] = False
                    v.set_tool = cur_tool
                    v.m4c_toolchanges.append(cur_tool)
                    v.m4c_toolchange_source_positions.append(len(v.parsed_gcode))
            except (TypeError, IndexError):
                pass

        code = gcode.create_command(line, is_comment)
        code[gcode.CLASS] = v.block_classification

        v.parsed_gcode.append(code)

        if v.block_classification != v.previous_block_classification:

            if v.block_classification == CLS_BRIM_END:
                backpass_line = len(v.parsed_gcode)

            if v.block_classification == CLS_TOOL_START or \
                    v.block_classification == CLS_TOOL_UNLOAD or \
                    v.block_classification == CLS_EMPTY:
                if backpass_line > -1:
                    while backpass_line < len(v.parsed_gcode):
                        v.parsed_gcode[backpass_line][gcode.CLASS] = v.block_classification
                        backpass_line += 1
                    backpass_line = -1

        if v.tower_measure:
            add_point_to_tower(code[gcode.X], code[gcode.Y])

        if v.side_wipe_towerdefined and (code[gcode.MOVEMENT] & 3) == 3:
            if coordinate_in_tower(code[gcode.X], code[gcode.Y]):
                code[gcode.MOVEMENT] += 256
                backpass_line = len(v.parsed_gcode) - 1

        if v.block_classification in [CLS_ENDGRID, CLS_ENDPURGE]:
            if ((code[gcode.MOVEMENT] & 3) == 3) and not coordinate_in_tower(code[gcode.X], code[gcode.Y]):
                v.parsed_gcode[-1][gcode.CLASS] = CLS_NORMAL
                v.block_classification = CLS_NORMAL

        if v.block_classification == CLS_BRIM_END:
            v.block_classification = CLS_NORMAL
            v.side_wipe_towerdefined = True

    v.side_wipe_towerdefined = False


def gcode_parseline(g):
    current_block_class = g[gcode.CLASS]

    if current_block_class not in [CLS_TOOL_PURGE, CLS_TOOL_START, CLS_TOOL_UNLOAD] and v.current_temp != v.new_temp:
        gcode.issue_code(v.temp1_stored_command)
        v.temp1_stored_command = ""

    # filter off comments
    if g[gcode.COMMAND] is None:
        if v.needpurgetower and g[gcode.COMMENT].endswith("BRIM END"):
            v.needpurgetower = False
            create_tower_gcode()
            purgetower.purge_generate_brim()

        gcode.issue_command(g)
        return

    # procedd none- movement commends
    if g[gcode.MOVEMENT] == 0:

        if g[gcode.COMMAND].startswith('T'):
            gcode_process_toolchange(int(g[gcode.COMMAND][1:]))
            if not v.debug_leaveToolCommands:
                gcode.move_to_comment(g, "--P2PP-- Color Change")
            v.toolchange_processed = True
            gcode.issue_command(g)
            return
        else:
            if g[gcode.COMMAND].startswith('M'):
                if g[gcode.COMMAND] in ["M140", "M190", "M73", "M84", "M201", "M203", "G28", "G90", "M115", "G80",
                                        "G21", "M907", "M204"]:
                    gcode.issue_command(g)
                    return

                if g[gcode.COMMAND] in ["M104", "M109"]:
                    if not v.process_temp or current_block_class not in [CLS_TOOL_PURGE, CLS_TOOL_START,
                                                                         CLS_TOOL_UNLOAD]:
                        g[gcode.COMMENT] += " Unprocessed temp "
                        gcode.issue_command(g)
                        v.new_temp = gcode.get_parameter(g, gcode.S, v.current_temp)
                        v.current_temp = v.new_temp
                    else:
                        v.new_temp = gcode.get_parameter(g, gcode.S, v.current_temp)
                        if v.new_temp >= v.current_temp:
                            g[gcode.COMMAND] = "M109"
                            v.temp2_stored_command = gcode.create_commandstring(g)
                            gcode.move_to_comment(g,
                                                  "--P2PP-- delayed temp rise until after purge {}-->{}".format(v.current_temp,
                                                                                                       v.new_temp))
                            v.current_temp = v.new_temp
                        else:
                            v.temp1_stored_command = gcode.create_commandstring(g)
                            gcode.move_to_comment(g,
                                                  "--P2PP-- delayed temp drop until after purge {}-->{}".format(v.current_temp,
                                                                                                       v.new_temp))
                            gcode.issue_command(g)
                    return

                if g[gcode.COMMAND] == "M107":
                    gcode.issue_command(g)
                    v.saved_fanspeed = 0
                    return

                if g[gcode.COMMAND] == "M106":
                    gcode.issue_command(g)
                    v.saved_fanspeed = gcode.get_parameter(g, gcode.S, v.saved_fanspeed)
                    return

                # flow rate changes have an effect on the filament consumption.  The effect is taken into account for ping generation
                if g[gcode.COMMAND] == "M221":
                    v.extrusion_multiplier = float(gcode.get_parameter(g, gcode.S, v.extrusion_multiplier * 100)) / 100
                    gcode.issue_command(g)
                    return

                # feed rate changes in the code are removed as they may interfere with the Palette P2 settings
                if g[gcode.COMMAND] in ["M220"]:
                    gcode.move_to_comment(g, "--P2PP-- Feed Rate Adjustments are removed")
                    gcode.issue_command(g)
                    return

            if current_block_class == CLS_TOOL_UNLOAD:
                if g[gcode.COMMAND] in ["G4", "M900"]:
                    gcode.move_to_comment(g, "--P2PP-- tool unload")

            gcode.issue_command(g)
            return

    # ---- AS OF HERE ONLY MOVEMENT COMMANDS ----

    classupdate = current_block_class != v.previous_block_classification
    v.previous_block_classification = current_block_class

    if g[gcode.MOVEMENT] & 1:
        v.previous_purge_keep_x = v.purge_keep_x
        gcode_x_position = v.purge_keep_x = g[gcode.X]
    else:
        gcode_x_position = v.current_position_x

    if g[gcode.MOVEMENT] & 2:
        v.previous_purge_keep_y = v.purge_keep_y
        gcode_y_position = v.purge_keep_y = g[gcode.Y]
    else:
        gcode_y_position = v.current_position_y

    if g[gcode.MOVEMENT] & 4:
        v.keep_z = g[gcode.Z]

    # this goes for all situations: START and UNLOAD are not needed
    if current_block_class in [CLS_TOOL_START, CLS_TOOL_UNLOAD]:
        if g[gcode.MOVEMENT] & 3 == 3:
            v.purge_pos_x = g[gcode.X]
            v.purge_pos_y = g[gcode.Y]
        gcode.move_to_comment(g, "--P2PP-- tool unload")
        gcode.issue_command(g)
        return

    # --------------------- TOWER DELTA PROCESSING
    if v.tower_delta:

        if classupdate:

            if current_block_class == CLS_TOOL_PURGE:
                gcode.issue_command(g)
                entertower(v.last_parsed_layer * v.layer_height + v.first_layer_height)
                return

            if current_block_class == CLS_EMPTY and not v.towerskipped and v.current_layer_is_skippable:
                v.towerskipped = (g[gcode.MOVEMENT] & 256) == 256
                if not v.towerskipped:
                    entertower(v.last_parsed_layer * v.layer_height + v.first_layer_height)

            if v.previous_block_classification in [CLS_ENDPURGE, CLS_ENDGRID]:
                if v.towerskipped:
                    gcode.issue_code("G1 Z{:.2f} F10810    ".format(v.keep_z))
                    v.towerskipped = False

        if current_block_class == CLS_TONORMAL:
            gcode.move_to_comment(g, "--P2PP-- post block processing")
            gcode.issue_command(g)
            return

        if v.towerskipped:
            gcode.move_to_comment(g, "--P2PP-- tower skipped")
            gcode.issue_command(g)
            return

        if current_block_class == CLS_TOOL_PURGE:
            if g[gcode.F] > v.purgetopspeed:
                g[gcode.F] = v.purgetopspeed

    # --------------------- SIDE WIPE PROCESSING
    if v.side_wipe:

        if classupdate:

            if current_block_class == CLS_BRIM and v.bigbrain3d_purge_enabled:
                create_sidewipe_bb3d(v.bigbrain3d_prime * v.bigbrain3d_blob_size)

        if not v.towerskipped and (g[gcode.MOVEMENT] & 3) == 3:
            v.towerskipped = (g[gcode.MOVEMENT] & 256) == 256

        if v.towerskipped and current_block_class == CLS_NORMAL and (g[gcode.MOVEMENT] & 3) == 3:
            if coordinate_on_bed(g[gcode.X], g[gcode.Y]):

                v.towerskipped = False
                if v.toolchange_processed and v.side_wipe_length:
                    create_side_wipe()
                    v.toolchange_processed = False

        if not v.side_wipe_towerdefined:
            if (g[gcode.MOVEMENT] & 7) == 3 and coordinate_in_tower(g[gcode.X], g[gcode.Y]):
                v.towerskipped = True
                v.side_wipe_towerdefined = True

        if v.towerskipped:
            if current_block_class in [CLS_TOOL_PURGE, CLS_ENDPURGE]:
                if g[gcode.EXTRUDE]:
                    v.side_wipe_length += g[gcode.E]
            gcode.move_to_comment(g, "--P2PP-- side wipe skipped")
            gcode.issue_command(g)
            return

    # --------------------- FULL PURGE PROCESSING
    if v.full_purge_reduction:

        if classupdate:

            if v.previous_block_classification == CLS_ENDGRID:
                v.towerskipped = False

        if not v.towerskipped and current_block_class == CLS_EMPTY and v.current_layer_is_skippable:
            v.towerskipped = (g[gcode.MOVEMENT] & 256) == 256

        if v.towerskipped or current_block_class in [CLS_TONORMAL, CLS_BRIM, CLS_ENDGRID]:
            gcode.move_to_comment(g, "--P2PP-- full purge skipped")
            gcode.issue_command(g)
            return

        if current_block_class in [CLS_TOOL_PURGE, CLS_ENDPURGE, CLS_EMPTY]:
            if g[gcode.EXTRUDE]:
                v.side_wipe_length += g[gcode.E]
            gcode.move_to_comment(g, "--P2PP-- full purge skipped")
            gcode.issue_command(g)
            return

        if v.toolchange_processed and current_block_class == CLS_NORMAL:
            if v.side_wipe_length and (g[gcode.MOVEMENT] & 3) == 3 and not (g[gcode.MOVEMENT] & 256) == 256:
                purgetower.purge_generate_sequence()
                v.toolchange_processed = False
            else:
                gcode.move_to_comment(g, "--P2PP-- full purge skipped")
                gcode.issue_command(g)
                return

        if v.expect_retract and (g[gcode.MOVEMENT] & 3):
            v.expect_retract = False
            if v.retraction >= 0 and g[gcode.RETRACT]:
                purgetower.retract(v.current_tool)

        if v.retract_move and g[gcode.RETRACT]:
            g[gcode.X] = v.retract_x
            g[gcode.Y] = v.retract_y
            g[gcode.MOVEMENT] |= 3
            v.retract_move = False

            if v.retraction <= - v.retract_length[v.current_tool]:
                gcode.move_to_comment(g, "--P2PP-- Double Retract")
            else:
                v.retraction += g[gcode.E]

    # --------------------- NO TOWER PROCESSING
    if not v.pathprocessing:

        if classupdate:

            if current_block_class in [CLS_TOOL_PURGE, CLS_EMPTY]:
                if v.acc_ping_left <= 0:
                    pings.check_accessorymode_first()
                v.enterpurge = True

        if v.toolchange_processed:
            gcode.issue_code("G1 X{:.3f} Y{:.3f} F8640; P2PP tower realign\n".format(v.purge_pos_x, v.purge_pos_y))
            gcode.issue_code("G1 Z{} ;P2PP correct z-moves".format(v.keep_z))
            v.toolchange_processed = False


        if current_block_class == CLS_TOOL_PURGE:

            if g[gcode.EXTRUDE] and gcode_x_position != v.purge_keep_y and gcode_y_position != v.purge_keep_y \
                    and not coordinate_in_tower(gcode_x_position, gcode_y_position) \
                    and coordinate_in_tower(v.purge_keep_x, v.purge_keep_y):
                gcode.remove_extrusion(g)

            if g[gcode.F] is not None and g[gcode.F] > v.purgetopspeed and g[gcode.E]:
                g[gcode.F] = v.purgetopspeed
                g[gcode.COMMENT] += " prugespeed topped"

        if v.enterpurge:

            v.enterpurge = False

            _x = v.previous_purge_keep_x if g[gcode.X] is not None else v.purge_keep_x
            _y = v.previous_purge_keep_y if g[gcode.Y] is not None else v.purge_keep_y

            if not coordinate_in_tower(_x, _y):
                _x = v.purge_keep_x
                _y = v.purge_keep_y

            if v.retraction == 0:
                purgetower.retract(v.current_tool, 3000)

            if v.temp2_stored_command != "":
                wait_location = calculate_temp_wait_position()
                gcode.issue_code(
                    "G1 X{:.3f} Y{:.3f} F8640; temp wait position\n".format(wait_location[0], wait_location[0]))
                gcode.issue_code(v.temp2_stored_command)
                v.temp2_stored_command = ""
                gcode.issue_code(
                    "G1 X{:.3f} Y{:.3f} F8640; P2PP Inserted to realign\n".format(_x, _y))

            gcode.remove_extrusion(g)
            if g[gcode.X] == _x:
                g[gcode.X] = None

    # --------------------- GLOBAL PROCEDDING

    if g[gcode.UNRETRACT]:
        g[gcode.E] = min(-v.retraction, g[gcode.E])
        v.retraction += g[gcode.E]

    if g[gcode.RETRACT]:
        g[gcode.E] = +g[gcode.E]
        v.retraction += g[gcode.E]

    if (g[gcode.MOVEMENT] & 3) and g[gcode.EXTRUDE] and v.retraction < -0.01:
        purgetower.unretract(v.current_tool, -1, ";--- P2PP --- fixup retracts")

    gcode.issue_command(g)

    # --------------------- PING PROCESSING

    if v.accessory_mode:
        pings.check_accessorymode_second(g[gcode.E])
    else:
        if g[gcode.EXTRUDE] and v.side_wipe_length == 0:
            pings.check_connected_ping()

    v.previous_position_x = v.current_position_x
    v.previous_position_y = v.current_position_y


# Generate the file and glue it all together!

def generate(input_file, output_file, printer_profile, splice_offset):
    starttime = time.time()
    v.printer_profile_string = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0].replace(" ", "_")
    _taskName = _taskName.replace(".mcf", "")

    v.splice_offset = splice_offset

    try:
        # python 3.x
        # noinspection PyArgumentList
        opf = open(input_file, encoding='utf-8')
    except TypeError:
        try:
            # python 2.x
            opf = open(input_file)
        except IOError:
            if v.gui:
                gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
            else:
                print ("Could not read input file\n'{}".format(input_file))
            return
    except IOError:
        if v.gui:
            gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
        else:
            print ("Could not read input file\n'{}".format(input_file))
        return

    gui.setfilename(input_file)
    gui.set_printer_id(v.printer_profile_string)
    gui.create_logitem("Reading File " + input_file)
    gui.progress_string(1)
    v.input_gcode = opf.readlines()
    opf.close()

    if v.save_unprocessed:
        pre, ext = os.path.splitext(input_file)
        of = pre + "_unprocessed" + ext
        gui.create_logitem("Saving original (unprocessed) code to: " + of)
        opf = open(of, "w")
        opf.writelines(v.input_gcode)
        opf.close()

    v.input_gcode = [item.strip() for item in v.input_gcode]

    gui.create_logitem("Analyzing slicer parameters")
    gui.progress_string(2)
    parse_slic3r_config()

    gui.create_logitem("Pre-parsing GCode")
    gui.progress_string(4)
    parse_gcode()

    v.input_gcode = None

    if v.bed_size_x == -9999 or v.bed_size_y == -9999 or v.bed_origin_x == -9999 or v.bed_origin_y == -9999:
        gui.log_warning("Bedsize not correctly defined.  The generated file may NOT print correctly")
    else:
        gui.create_logitem("Bed origin ({:3.1f}mm, {:3.1f}mm)".format(v.bed_origin_x, v.bed_origin_y))
        gui.create_logitem("Bed zise   ({:3.1f}mm, {:3.1f}mm)".format(v.bed_size_x, v.bed_size_y))
        if v.bed_shape_rect and v.bed_shape_warning:
            gui.create_logitem("Manual bed size override, Prusa Bedshape parameters ignored.")

    gui.create_logitem("")

    if v.tower_delta or v.full_purge_reduction and v.variable_layer:
        gui.log_warning("Variable layers are not compatible with fullpruge/tower delta")

    if v.process_temp and v.side_wipe:
        gui.log_warning("TEMPERATURECONTROL and Side Wipe / BigBrain3D are not compatible")

    if v.palette_plus:
        if v.palette_plus_ppm == -9:
            gui.log_warning("P+ parameter P+PPM not set correctly in startup GCODE")
        if v.palette_plus_loading_offset == -9:
            gui.log_warning("P+ parameter P+LOADINGOFFSET not set correctly in startup GCODE")

    v.side_wipe = not coordinate_on_bed(v.wipetower_posx, v.wipetower_posy)
    v.tower_delta = v.max_tower_z_delta > 0

    gui.create_logitem("Creating tool usage information")
    m4c.calculate_loadscheme()

    if v.side_wipe:

        if v.skirts and v.ps_version >= "2.2":
            gui.log_warning("SIDEWIPE and SKIRTS are NOT compatible in PS2.2 or later")
            gui.log_warning("THIS FILE WILL NOT PRINT CORRECTLY")

        if v.wipe_remove_sparse_layers:
            gui.log_warning("SIDE WIPE mode not compatible with sparse wipe tower in PS")
            gui.log_warning("Use Tower Delta instead")
            gui.log_warning("THIS FILE WILL NOT PRINT CORRECTLY")

        gui.create_logitem("Side wipe activated", "blue")

        if v.full_purge_reduction:
            gui.log_warning("Full Purge Reduction is not compatible with Side Wipe, performing Side Wipe")
            v.full_purge_reduction = False

    if v.full_purge_reduction:
        v.side_wipe = False
        gui.create_logitem("Full Tower Reduction activated", "blue")
        if v.tower_delta:
            gui.log_warning("Full Purge Reduction is not compatible with Tower Delta, performing Full Purge Reduction")
            v.tower_delta = False

    v.pathprocessing = (v.tower_delta or v.full_purge_reduction or v.side_wipe)
    v.uses_prusa_tower = not (v.full_purge_reduction or v.side_wipe)

    if v.autoaddsplice and not v.full_purge_reduction and not v.side_wipe:
        gui.log_warning("AUTOADDPURGE only works with side wipe and fullpurgereduction at this moment")

    if (len(v.skippable_layer) == 0) and v.pathprocessing:
        gui.log_warning("LAYER configuration is missing.")
        gui.log_warning("Check the P2PP documentation for furhter info.")
    else:

        if v.tower_delta:
            v.skippable_layer[0] = False
            optimize_tower_skip(int(v.max_tower_z_delta / v.layer_height))

        gui.create_logitem("Generate processed GCode")

        total_line_count = len(v.parsed_gcode)
        v.retraction = 0
        v.last_parsed_layer = -1
        v.previous_block_classification = v.parsed_gcode[0][gcode.CLASS]
        idx = 0

        for process_line_count in range(total_line_count):

            try:
                if process_line_count >= v.layer_end[0]:
                    v.last_parsed_layer += 1
                    v.layer_end.pop(0)
                    v.current_layer_is_skippable = v.skippable_layer[v.last_parsed_layer]
                    if v.current_layer_is_skippable:
                        v.cur_tower_z_delta += v.layer_height
            except IndexError:
                pass

            gcode_parseline(v.parsed_gcode[idx])
            idx = idx + 1

            if idx > 100000:
                v.parsed_gcode = v.parsed_gcode[idx:]
                idx = 0

            if process_line_count % 10000 == 0:
                gui.progress_string(50 + 50 * process_line_count // total_line_count)

        v.parsed_gcode = None
        v.processtime = time.time() - starttime

        gcode_process_toolchange(-1)
        omega_result = header_generate_omega(_taskName)
        header = omega_result['header'] + omega_result['summary'] + omega_result['warnings']

        # write the output file
        ######################

        if not output_file:
            output_file = input_file
        gui.create_logitem("Generating GCODE file: " + output_file)
        opf = open(output_file, "w")
        if not v.accessory_mode:
            opf.writelines(header)
            opf.write("\n\n;--------- START PROCESSED GCODE ----------\n\n")
        if v.accessory_mode:
            opf.write("M0\n")
            opf.write("T0\n")

        if v.splice_offset == 0:
            gui.log_warning("SPLICE_OFFSET not defined")
        for line in v.processed_gcode:
            opf.write(line)
            opf.write("\n")
        opf.close()

        if v.accessory_mode:

            pre, ext = os.path.splitext(output_file)
            if v.palette_plus:
                maffile = pre + ".msf"
            else:
                maffile = pre + ".maf"
            gui.create_logitem("Generating PALETTE MAF/MSF file: " + maffile)

            maf = open(maffile, 'w')

            for h in header:
                h = h.strip('\r\n')
                # noinspection PyTypeChecker
                maf.write(unicode(h))
                maf.write('\r\n')
            maf.close()

        gui.print_summary(omega_result['summary'])

    gui.progress_string(100)
    if (len(v.process_warnings) > 0 and not v.ignore_warnings) or v.consolewait:
        gui.close_button_enable()
