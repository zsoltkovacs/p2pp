#!/usr/bin/pythonw
__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'


import platform
from os import listdir
import sys
from os.path import isfile, join, expanduser, dirname
try:
    # p ython version 2.x
    import Tkinter as tkinter
    import ttk
    import tkMessageBox
except ImportError:
    # python version 3.x
    import tkinter
    from tkinter import ttk
    from tkinter import messagebox as tkMessageBox

p2ppscript = ""
folder = ""

platformD = platform.system()
if platformD == 'Darwin':
    folder = expanduser('~/Library/Application Support/PrusaSlicer')
    p2ppscript = "{}/p2pp.command ".format(dirname(sys.argv[0]))
elif platformD == 'Windows':
    folder = "....."
    p2ppscript = "{}\\p2pp.bat".format(dirname(sys.argv[0]))

def get_files( mypath ):
    return [f for f in listdir(mypath) if isfile(join(mypath, f))]


def get_folders( mypath , mask=None):
    return [f for f in listdir(mypath) if (not isfile(join(mypath, f))) and mask and (mask in f)]


def copyfile(src, dst):
    pass


def center(win, width, height):
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)  # center horizontally in screen
    y = (win.winfo_screenheight() // 2) - (height // 2)  # center vertically in screen
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    win.minsize(int(width / 1.2), int(height / 1.2))
    win.maxsize(width * 4, height * 4)


def line(frame, txt, parameter, val, te , row):
    rowadd = 1
    v = None
    tkinter.Label(frame, text=txt, font=fixedfont, background="#409090").grid(row=row + rowadd, column=0, sticky="W")
    tkinter.Label(frame, text=parameter, font=fixedfontbold, background="#409090").grid(row=row + rowadd, column=1, sticky="W")

    if te == 0:  # input box
        v = tkinter.StringVar(frame, value=val)
        e = tkinter.Entry(frame, background="#40C0C0", textvariable=v, justify='right')
        e.grid(row=row + rowadd, column=2, sticky="W")
    elif te == 1:  # checkbox
        v = tkinter.BooleanVar(frame, value=val)
        e = tkinter.Checkbutton(frame, background="#409090", variable=v)
        e.grid(row=row + rowadd, column=2, sticky="W")
    elif te ==2:   #label
        e = tkinter.Label(frame, text=val, font=fixedfont, background="#409090")
        e.grid(row=row + rowadd, column=2, sticky="W")

    return v

def configitemadd( frame, item ):
    v = tkinter.BooleanVar(frame, value=False)
    e = tkinter.Checkbutton(frame, text=item, background="#909090", variable=v)
    e.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
    return v



var_printerID = "50325050494e464f".upper()
var_consolewait = True
var_saveunprocessed = True
var_checkversion = False
var_absoluteextruder = False
var_spliceoffset = 40
var_endoffilament = 150
var_pla_pla = "0_0_0"
var_default = "0_0_0"

mainwindow = tkinter.Tk()
mainwindow.title("Palette2 Post Processing - Configuration utility")
center(mainwindow, 1000, 800)
mainwindow['padx'] = 10
mainwindow['pady'] = 10
boldfontlarge = 'Courier 24 bold'
normalfont = 'Courier 16'
boldfont = 'Courier 16 bold'
fixedfont = 'Courier 14'
fixedfontbold = 'Courier 14 bold'
fixedsmallfont = 'Courier 8'

mainwindow.lift()
mainwindow.attributes('-topmost', True)
mainwindow.after_idle(mainwindow.attributes, '-topmost', False)
mainwindow.update()

configframe = tkinter.Frame(mainwindow, border=1, relief='sunken', background="#409090", padx=10, pady=10)
configframe.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

configframe.columnconfigure(0, pad=5, weight=3)
configframe.columnconfigure(1, pad=5, weight=1)
configframe.columnconfigure(2, pad=5, weight=1)

tkinter.Label(configframe, text='\nBasic P2PP Configuration\n', font=boldfont, foreground="blue", underline=1, background="#409090").grid(row=0, column=0, columnspan=3, sticky=tkinter.W+tkinter.E)

var_printerID = line(configframe,"Printer ID", "PRINTERID", var_printerID, 0, 0)
var_consolewait = line(configframe,"Wait on completion", "CONSOLEWAIT", var_consolewait, 1, 1)
var_saveunprocessed = line(configframe,"Backup Unprocessed File", "SAVEUNPROCESSED", var_saveunprocessed, 1, 2)
var_checkversion = line(configframe,"Check version on startup", "CHECKVERSION", var_checkversion, 1, 3)
var_absoluteextruder = line(configframe,"Convert to absolute extrusion", "ABSOLUTEEXTRUDER", var_absoluteextruder, 1, 4)
var_spliceoffset = line(configframe,"Extra Length on first splice", "SPLICEOFFSET", var_spliceoffset,  0, 5)
var_endoffilament = line(configframe,"Extra Length at end of the print (mm)", "EXTRAENDFILAMENT", var_endoffilament,  0, 6)

tkinter.Label(configframe, text='\nStandaard Material Configuration\n', font=boldfont, underline=1, foreground="blue",background="#409090").grid(row=8, column=0, columnspan=3, sticky=tkinter.W+tkinter.E)

line(configframe, "Default Splice (Heat/Compression/Cool)", "MATERIAL_DEFAULT", "MATERIAL_DEFAULT_0_0_0",  2, 9)
line(configframe, "PLA -> PLA (Heat/Compression/Cool)", "MATERIAL_PLA_PLA", "MATERIAL_PLA_PLA_0_0_0",  2, 10)
line(configframe, "PETG -> PETG (Heat/Compression/Cool)", "MATERIAL_PETG_PETG", "MATERIAL_PETG_PETG_0_0_0",  2, 11)

tkinter.Label(configframe, text='\nStandard Layer Configuration\n', font=boldfont, foreground="blue", underline=1, background="#409090").grid(row=12, column=0, columnspan=3, sticky=tkinter.W+tkinter.E)
line(configframe, "Constant Layer Configuration", "LAYER", "LAYER [layer_num]",  2, 13)
line(configframe, "Variable Layer Configuration", "LAYERHEIGHT", "LAYERHEIGHT [layer_z]",  2, 14)

tkinter.Label(configframe, text='\nP2PP Script Locationn\n', font=boldfont, foreground="blue", underline=1, background="#409090").grid(row=15, column=0, columnspan=3, sticky=tkinter.W+tkinter.E)

tkinter.Label(configframe, text="Post Processing Script", font=fixedfont, background="#409090").grid(row=16, column=0, sticky="W")
tkinter.Label(configframe, text=p2ppscript, font=fixedfont, background="#409090").grid(row=17, column=1, columnspan=2)

psconfigframe = tkinter.Frame(mainwindow, border=1, relief='sunken', background="#909090")
psconfigframe.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

tkinter.Label(psconfigframe, text='Prusa Slicer Configuration Info', font=boldfontlarge, background="#909090").pack(side=tkinter.TOP, expand=0)

printers = tkinter.Frame(psconfigframe, border=1, relief='sunken', background="#909090")
printers.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=1)


tkinter.Label(printers, text='Printer Configs', font=boldfont, background="#909090").pack(side=tkinter.TOP, expand=0)


prints = tkinter.Frame(psconfigframe, border=1, relief='sunken', background="#909090")
prints.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=1)


tkinter.Label(prints, text='Print Configs', font=boldfont, background="#909090").pack(side=tkinter.TOP, expand=0)

printerprofiles = get_files(folder + "/printer")
printprofiles = get_files(folder + "/print")

buttonframe = tkinter.Frame(mainwindow, border=1, relief='sunken', background="#909090")
buttonframe.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=0)


tkinter.Button(buttonframe, text="EXIT").pack(side=tkinter.BOTTOM, fill=tkinter.X, expand=1)
tkinter.Button(buttonframe, text ="Create Profile").pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=0)

for pf in printerprofiles:
    configitemadd(printers, pf)

for pr in printprofiles:
    configitemadd(prints, pr)




mainwindow.mainloop()
