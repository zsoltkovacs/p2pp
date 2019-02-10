__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__version__ = '3.0.0'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'



try:
    from Tkinter import *
    import Tkinter as tk
    import tkMessageBox
except ImportError:
    from tkinter import *
    import tkinter as tk
    from tkinter import messagebox as tkMessageBox

import os

root = Tk()
root.iconbitmap(os.path.dirname(sys.argv[0])+'\\favicon.ico')
root.iconify()


def center(win, width, height):
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))


def clicked():
    root.destroy()


def user_error(body_text):
    tkMessageBox.showerror("P2PP - Error Occurred", body_text)


def show_warnings(warning_list):
    root.title("P2PP - Process Warnings")
    center(root, 800, 600)
    root.deiconify()

    lbl = Label(root, text="P2PP - Process Warnings", padx=5, pady=5, font=("Arial Bold", 24), fg="red")
    lbl.pack(side=TOP, fill=Y)

    canvas = Canvas(root)
    canvas.pack(side=TOP, fill=BOTH, expand=1, padx=10, pady=10)
    sb = Scrollbar(canvas)
    warn = Text(canvas)

    sb.pack(side=RIGHT, fill=Y)
    for warning in range(len(warning_list)-4):
        warn.insert(END, warning_list[warning+4][1:])
    warn.pack(side=LEFT, fill=BOTH, expand=1)
    sb.config(command=warn.yview)

    btn = Button(root, text='Close', command=clicked)
    btn.pack(side=BOTTOM, fill=Y, pady=10)
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    root.mainloop()
