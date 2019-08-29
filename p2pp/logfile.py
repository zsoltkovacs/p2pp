__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2019, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.variables as v
import gui


# ################################################################
# ######################### COMPOSE WARNING BLOCK ################
# ################################################################
def log_warning(text):
    v.process_warnings.append(";" + text)
    gui.create_logitem(text,"red")
