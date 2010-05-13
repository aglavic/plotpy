#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Plot-script package for data plotting and analyzing for different instruments.
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
import config.gui

# will be defined by initialize_gui_toolkit function
gui_main=None

#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7a"
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
                         #'scd': ('single_diff', 'SingleDiffSession', ['___']), 
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

def initialize_gui_toolkit():
  '''
    Load GUI modules dependent on the toolkit.
  '''
  global gui_main, status_dialog
  gui_main=__import__( config.gui.toolkit+'gui.main_window' , fromlist=["main_window"])
  if '--help' not in sys.argv and '--debug' not in sys.argv and len(sys.argv)>1:
    dialogs=__import__( config.gui.toolkit+'gui.dialogs' , fromlist=["dialogs"])
    status_dialog=dialogs.connect_stdout_dialog()
  else:
    status_dialog=None

def initialize_gui(session, status_dialog=None):
  '''
    Initialize the gui main window.
      
    @param session An object derived from sessions.generic.GenericSession
    
    @return An ApplicationMainWindow instance ( class defined in {toolkit}gui.generic )
  '''
  if not gui_main:
    initialize_gui_toolkit()
  return gui_main.ApplicationMainWindow(session, status_dialog=status_dialog)

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
  
def _run():
  '''
    Start the program.
  '''
  if '--debug' in sys.argv:
    initialize_debug()
  initialize_gui_toolkit()
  active_session=initialize(sys.argv[1:])  
  if active_session.use_gui: # start a new gui session
    plotting_session=initialize_gui(active_session, status_dialog)
    gui_main.main_loop(plotting_session)
  else: # in command line mode, just plot the selected data.
    active_session.plot_all()
  # delete temporal files and folders after the program ended
  active_session.os_cleanup()

if __name__ == '__main__':    #code to execute if called from command-line
  _run()
