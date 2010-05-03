#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Main script which imports the other modules.
'''
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
#                  including a graphical user interface and easy andling                        #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Additional Files: plot_generic_data.py - session class, parent for the other sessions         #
#                   measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   plot_SQUID_data.py - squid session class for mpms,ppms data                 #
#                   config/squid.py - settings for the squid session                            #
#                   read_data/squid.py - functions for data extraction                          #
#                   plot_4circle_data.py - 4circle session class for spec data                  #
#                   config/circle.py - settings for the 4circle session                         #
#                   read_data/circle.py - functions for data extraction                         #
#                   plot_reflectometer_data.py - reflectometer session class                    #
#                   config/reflectometer.py - settings for the reflectometer session(+fit)      #
#                   read_data/reflectometer.py - functions for data extraction                  #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                                                                                               #
#################################################################################################

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import sys
exit=sys.exit
from glob import glob
##---add_python_path_here---## # Place holder to add installation directory to python path for non superuser installation.

# own modules
# parent class
from sessions.generic import GenericSession

#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


'''
  Dictionary for the known measurement types, to create a new measureing type
  it is only needed to create the seesion class and add it to this dictionary.
  
  Although the commandline parameter order is not importent for all other options
  the type has to be set first, as the other parameters are evaluated according to
  the session.
'''
known_measurement_types={
                         'squid': ('squid', 'SquidSession', ['dat', 'raw', 'DAT', 'RAW']), 
                         '4circle': ('circle', 'CircleSession', ['spec']), 
                         'refl': ('reflectometer', 'ReflectometerSession', ['UXD', 'uxd']), 
                         'treff': ('treff', 'TreffSession', ['___']), 
                         'in12': ('in12', 'IN12Session', ['___']), 
                         'dns': ('dns', 'DNSSession', ['d_dat']), 
                         'kws2': ('kws2', 'KWS2Session', ['DAT']),                         
                         'scd': ('single_diff', 'SingleDiffSession', ['___']), 
                         'generic': ('generic', 'GenericSession', ['___']), 
                         }

'''
############################################################################
  Here the actual script starts. It creates one session object according
  to the selected type of the data and reads all files specified by the
  user. The session object is then ither used for a direct plotting or
  piped to a plotting_gui for later use.
############################################################################
'''

def import_session_from_name(arguments, measurement_type):
  '''
    Import a session object from a string. 
    In this way we don't need to import all sessions in advance.
    
    @param arguments The command line arguments to pass to the object
    @param measurement_type The names of the module and object to import
    
    @return The class instance for the measurement type
  '''
  # Check for wildcards in input
  new_args=[]
  for item in arguments:
    if '*' in item or '?' in item:
      new_args+=glob(item)
    else:
      new_args.append(item)
  arguments=new_args
  active_session_class = getattr(__import__('sessions.'+measurement_type[0], globals(), locals(), 
                                      [measurement_type[1]]), measurement_type[1])
  return active_session_class(arguments)


def initialize(arguments):  
  ''' 
    initialize session and read data files 
  '''
  if (len(arguments) == 0):
    # if no input parameter given, print the short help string
    print GenericSession.SHORT_HELP
    exit()
  elif arguments[0] in known_measurement_types:
    # type is found in dictionary, using specific session
    measurement_type=known_measurement_types[arguments[0]]
    active_session=import_session_from_name(arguments[1:], measurement_type)
  else:
    found_sessiontype=False
    suffixes=map(lambda arg: arg.split('.')[-1], arguments)
    for name, measurement_type in known_measurement_types.items():
      if found_sessiontype:
        break
      for suffix in measurement_type[2]:
        if suffix in suffixes:
          print "Setting session type to " + name + '.'
          active_session=import_session_from_name(arguments, measurement_type)
          found_sessiontype=True
          break
    if not found_sessiontype:
      # type is not found, using generic session
      active_session=GenericSession(arguments)
  return active_session

def initialize_gui(session, status_dialog=None):
  '''
    initialize the gui window and import the needed modules
  '''
  global gtk, plotting_gui
  # GUI module
  import plotting_gui
  import gtk
  # TODO:  Set different fonts for windows, as the standart font doesn't support all characters
  return plotting_gui.ApplicationMainWindow(session, status_dialog=status_dialog)

def initialize_debug(log_file='debug.log'):
  '''
    Initialize logging and output for debug mode.
  '''
  import plotting_debug
  if '--logall' in sys.argv:
    level='DEBUG'
    sys.argv.remove('--logall')
  else:
    level='INFO'
  plotting_debug.initialize(log_file, level)
  

if __name__ == '__main__':    #code to execute if called from command-line
  if '--debug' in sys.argv:
    initialize_debug()
  if '--help' not in sys.argv and '--debug' not in sys.argv and len(sys.argv)>1:
    try:
      # initialize the session with stdoutput in gtk dialog.
      from plotting_gui import StatusDialog
      import gtk
      status_dialog=StatusDialog('Import Status', flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                 parent=None, buttons=('Close', 0))
      status_dialog.connect('response', lambda *ignore: status_dialog.hide())
      status_dialog.set_default_size(800, 600)
      status_dialog.show_all()
      status_dialog.fileno=lambda : 1
      status_dialog.flush=lambda : True
      sys.stdout=status_dialog
    except:
      pass
  else:
    status_dialog=None
  active_session=initialize(sys.argv[1:])  
  if active_session.use_gui: # start a new gui session
    plotting_session=initialize_gui(active_session, status_dialog)
    if getattr(plotting_session, 'destroyed_directly', False):
      while gtk.events_pending():
        gtk.main_iteration(False)
    else:
      gtk.main() # start GTK engine
  else: # in command line mode, just plot the selected data.
    active_session.plot_all()

  # delete temporal files and folders after the program ended
  active_session.os_cleanup()

def test_mpl(arguments):
  '''
    Testing the matplotlib plotting stuff
  '''
  active_session=initialize(arguments)  
  plotting_session=initialize_gui(active_session)
  import gtk
  from matplotlib.figure import Figure
  from numpy import arange, sin, pi
  from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
  from matplotlib.backends.backend_gtk import NavigationToolbar2GTK as NavigationToolbar

  vbox = gtk.VBox()
  plotting_session.frame1.remove(plotting_session.frame1.child)
  plotting_session.frame1.add(vbox)

  fig = Figure(figsize=(5,4), dpi=100)
  ax = fig.add_subplot(111)
  t = arange(0.0,3.0,0.01)
  s = sin(2*pi*t)

  ax.plot(t,s)


  canvas = FigureCanvas(fig)  # a gtk.DrawingArea
  vbox.pack_start(canvas)
  toolbar = NavigationToolbar(canvas, plotting_session)
  vbox.pack_start(toolbar, False, False)


  vbox.show_all()
  return plotting_session, (vbox, fig, ax, canvas, toolbar)
