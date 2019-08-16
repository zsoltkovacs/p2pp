__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

try:
    # p ython version 2.x
    import Tkinter as tkinter
    import tkMessageBox
except ImportError:
    # python version 3.x
    import tkinter
    from tkinter import messagebox as tkMessageBox

import os
import sys
from platform import system
import version
import variables as v


platformD = system()

last_pct = -1


def progress_string(pct):
    global last_pct
    if last_pct == pct:
        return
    if pct == 100:
        if len(v.process_warnings) == 0:
            progress.set("COMPLETED OK")
            progress_field.config(font=boldfont)
            progress_field.config(fg='#008000')
        else:
            progress.set("COMPLETED WITH WARNINGS")
            progress_field.config(font=boldfont)
            progress_field.config(fg='#800000')
    else:
        progress.set("{0:3}% [".format(pct) + "#" * (pct // 2) + "-" * (50-pct // 2) + "]")
    mainwindow.update()
    last_pct = pct


def create_logitem(text, color="black"):
    loglist.insert(tkinter.END, text)
    loglist.itemconfig(tkinter.END, foreground=color)
    mainwindow.update()


def close_window():
    mainwindow.destroy()

def update_button_pressed():
    v.upgradeprocess(version.latest_stable_version , v.update_file_list)


def close_button_enable():
    closebutton.config(state=tkinter.NORMAL)
    # WIP disable upgrade for now
    # if not (v.upgradeprocess == None):
    #     tkinter.Button(buttonframe, text='Upgrade to '+version.latest_stable_version, command=update_button_pressed).pack(side=tkinter.RIGHT)
    mainwindow.mainloop()


def center(win, width, height):
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)  # center horizontally in screen
    y = (win.winfo_screenheight() // 2) - (height // 2)  # center vertically in screen
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    win.minsize(width, height)
    win.maxsize(width, height)


def set_printer_id(text):
    printerid.set(text)
    mainwindow.update()


def setfilename(text):
    filename.set(text)
    mainwindow.update()


def user_error(header, body_text):
    tkMessageBox.showinfo(header, body_text)


def ask_yes_no(title, message):
    result = tkMessageBox.askquestion(title, message)
    return result


mainwindow = tkinter.Tk()
mainwindow.title("Palette2 Post Processing for PrusaSliceer")
center(mainwindow, 800, 600)

if platformD == 'Windows':
    logo_image = os.path.dirname(sys.argv[0]) + '\\favicon.ico'
    mainwindow.iconbitmap(logo_image)
    mainwindow.update()

mainwindow['padx'] = 10
mainwindow['pady'] = 10

normalfont = 'Helvetica 16'
boldfont = 'Helvetica 16 bold'
fixedfont = 'Courier 14'
fixedsmallfont = 'Courier 12'

# Top Information Frqme
infoframe = tkinter.Frame(mainwindow, border=3, relief='sunken', background="#808080")
infoframe.pack(side=tkinter.TOP, fill=tkinter.X)

# logo
logoimage = tkinter.PhotoImage(file=os.path.dirname(sys.argv[0]) + "/appicon.ppm")
logofield = tkinter.Label(infoframe, image=logoimage)
logofield.pack(side=tkinter.LEFT, fill=tkinter.Y)

infosubframe = tkinter.Frame(infoframe, background="#808080")
infosubframe.pack(side=tkinter.LEFT, fill=tkinter.X)
infosubframe["padx"] = 20

# file name display
tkinter.Label(infosubframe, text='Filename:', font=boldfont, background="#808080").grid(row=0, column=1, sticky="w")
filename = tkinter.StringVar()
setfilename("-----")
tkinter.Label(infosubframe, textvariable=filename, font=normalfont, background="#808080").grid(row=0, column=2,
                                                                                               sticky="w")

# printer ID display
printerid = tkinter.StringVar()
set_printer_id("-----")

tkinter.Label(infosubframe, text='Printer ID:', font=boldfont, background="#808080").grid(row=1, column=1, sticky="w")
tkinter.Label(infosubframe, textvariable=printerid, font=normalfont, background="#808080").grid(row=1, column=2,
                                                                                                sticky="w")


tkinter.Label(infosubframe, text="P2PP Version:", font=boldfont, background="#808080").grid(row=2, column=1,
                                                                                            sticky="w")
tkinter.Label(infosubframe, text=version.Version, font=normalfont, background="#808080").grid(row=2, column=2,
                                                                                              sticky="w")

# progress bar
progress = tkinter.StringVar()
progress.set(progress_string(0))
tkinter.Label(infosubframe, text='Progress:', font=boldfont, background="#808080").grid(row=3, column=1, sticky="w")
progress_field = tkinter.Label(infosubframe, textvariable=progress, font=fixedfont, background="#808080")
progress_field.grid(row=3, column=2, sticky="w")

# Log frame
logframe = tkinter.Frame(mainwindow, border=3, relief="sunken")
logframe.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

loglistscroll = tkinter.Scrollbar(logframe, orient=tkinter.VERTICAL)
loglistscroll.pack(side='right', fill=tkinter.Y)

loglist = tkinter.Listbox(logframe, yscrollcommand=loglistscroll.set, font=fixedsmallfont)
loglist.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=1)

loglistscroll.config(command=loglist.yview)

# Button frame
buttonframe = tkinter.Frame(mainwindow, border=1, relief="sunken")
buttonframe.pack(side=tkinter.BOTTOM, fill=tkinter.X)

closebutton = tkinter.Button(buttonframe, text="Exit", state=tkinter.DISABLED, command=close_window)
closebutton.pack(side=tkinter.LEFT)


mainwindow.rowconfigure(0, weight=1)
mainwindow.rowconfigure(1, weight=1000)
mainwindow.rowconfigure(2, weight=1)

mainwindow.lift()
mainwindow.attributes('-topmost', True)
mainwindow.after_idle(mainwindow.attributes, '-topmost', False)
mainwindow.update()

