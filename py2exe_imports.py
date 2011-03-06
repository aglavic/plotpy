# -*- encoding: utf-8 -*-
'''
  Just a short script to import modules otherwise overseen from py2exe
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

import __init__
import numpy
import scipy
import scipy.special
import scipy.misc.common
from scipy.misc.common import factorial
scipy.factorial=factorial
from scipy import factorial
import scipy.optimize
import scipy.special
import scipy.interpolate
import gtkgui.ipython_view
import IPython
import IPython.Extensions
import IPython.ipapi
import gtk
import gtk._lazyutils
from gtk import keysyms
import pygame.font
import sessions.reflectometer
import sessions.circle
import sessions.dns
import sessions.generic
import sessions.in12
import sessions.squid
import sessions.treff
import sessions.kws2
import sessions.single_diff
import gtkgui.main_window
import gtkgui.circle
import gtkgui.dialogs
import gtkgui.diverse_classes
import gtkgui.dns
import gtkgui.file_actions
import gtkgui.gui_fit_data
import gtkgui.in12
import gtkgui.ipython_view
import gtkgui.kws2
import gtkgui.reflectometer
import gtkgui.reflectometer_functions
import gtkgui.squid
import gtkgui.treff

import IPython.Shell
if __name__=='__main__':
  ips=IPython.Shell.start()
  from IPython.Extensions import ipy_profile_none, ipy_defaults
  ips.mainloop()
