__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '1.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import p2pp.variables as v
from p2pp.gcodeparser import   get_gcode_parameter



def create_side_wipe(  ):
    v.processedGCode.append(";P2PP SIDE WIPE CODE\n")
    v.processedGCode.append(";-------------------\n")
    v.processedGCode.append(";  Side wipe length: {}mm\n".format(v.side_wipe_length))

    if (v.maxWipe>0) and (v.side_wipe_length > v.maxWipe):
        v.totalMaterialExtruded = v.totalMaterialExtruded -v.side_wipe_length + v.maxWipe
        v.side_wipe_length = v.maxWipe

    if v.side_wipe_length>0:
        v.processedGCode.append("G1 E{}\n".format(-v.sidewiperetract))
        v.wipeRetracted = True
        v.processedGCode.append("G1 F8640\n")
        v.processedGCode.append("G0 {} Y{} F2500\n".format(v.side_wipe_loc, v.sideWipeMinY))
        sweepBaseSpeed = 25000 * abs(v.sideWipeMaxY - v.sideWipeMinY)/150
        sweeplen = 20 *abs(v.sideWipeMaxY - v.sideWipeMinY)/150
        feedRate =  -1

        moveto = v.sideWipeMaxY

        while v.side_wipe_length > 0:
            sweep =  min(v.side_wipe_length, sweeplen)
            v.side_wipe_length -=sweeplen

            wipespeed = int(sweepBaseSpeed/sweep)
            wipespeed = min( wipespeed, 5000)
            if feedRate != wipespeed:
                v.processedGCode.append("G1 F{}\n".format( wipespeed))
                feedRate = wipespeed

            v.processedGCode.append("G1 {} Y{} E{}\n".format(v.side_wipe_loc, moveto, sweep * v.sidewipecorrection))

            if moveto == v.sideWipeMaxY:
                moveto = v.sideWipeMinY
            else:
                moveto = v.sideWipeMaxY

        v.processedGCode.append(";-------------------\n")
        v.side_wipe_length = 0

def unretract():
    v.processedGCode.append("G1 E{}\n".format(v.sidewiperetract))
    v.wipeRetracted = False

# restrospective cleanup of generated code AFTER detectinf a purge volume in print

def retro_cleanup():


    if not v.side_wipe:
        return
    idx = len(v.processedGCode) - 1
    while idx > -1 and not v.processedGCode[idx].startswith("M900"):
        if v.processedGCode[idx][0:1] == "G1":
            extruder_movement = get_gcode_parameter(v.processedGCode[idx], "E")
            if extruder_movement != "":
                v.side_wipe_length += extruder_movement
        if not v.processedGCode[idx].startswith("M73"):
            v.processedGCode[idx] = ";--- P2PP removed " + v.processedGCode[idx]
        idx -= 1


def sidewipe_toolchangestart():
    if v.side_wipe:
        v.side_wipe_length = 0
        v.wipe_start_extrusion = v.totalMaterialExtruded
        retro_cleanup()

def collect_wiprtower_info(gcode_fullline):

    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM START"):
        v.defineTower = True

    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM END"):
        v.defineTower = False
        v.wipe_tower_info['minx']-=2
        v.wipe_tower_info['miny']-=2
        v.wipe_tower_info['maxx']+=2
        v.wipe_tower_info['maxy']+=2
        v.processedGCode.append("; TOWER COORDINATES ({:-8.2f},{:-8.2f}) to ({:-8.2f},{:-8.2f})\n".format(
            v.wipe_tower_info['minx'], v.wipe_tower_info['miny'], v.wipe_tower_info['maxx'], v.wipe_tower_info['maxy']
        ))

    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM START") or \
       gcode_fullline.startswith("; CP EMPTY GRID START"):

        if not v.withinToolchangeBlock:
            retro_cleanup()
            v.side_wipe_skip = v.side_wipe

    if gcode_fullline.startswith("; CP WIPE TOWER FIRST LAYER BRIM END") or \
       gcode_fullline.startswith("; CP EMPTY GRID END"):
       v.side_wipe_skip = False


    if gcode_fullline[0] == "G":

        parmX = get_gcode_parameter(gcode_fullline, "X")
        parmY = get_gcode_parameter(gcode_fullline, "Y")


        if parmX != "":
            if v.defineTower:
                v.wipe_tower_info['maxx'] = max (v.wipe_tower_info['maxx'],parmX)
                v.wipe_tower_info['minx'] = min(v.wipe_tower_info['minx'], parmX)
            if not v.side_wipe_skip:
                   v.currentPositionX = parmX

        if parmY != "":
            if v.defineTower:
                v.wipe_tower_info['maxy'] = max(v.wipe_tower_info['maxy'], parmY)
                v.wipe_tower_info['miny'] = min(v.wipe_tower_info['miny'], parmY)
            if not v.side_wipe_skip:
                v.currentPositionY = parmY






