#!/usr/bin/env python
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

# own modules
# specific measurement classes
# parent class
from sessions.generic import GenericSession

#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# if python version < 2.5 set the sys.exit function as exit
if hex(sys.hexversion)<'0x2050000':
  exit=sys.exit

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
                         }

  
class RedirectOutput:
  '''
    Class to redirect all print statements when useing the GUI.
  '''
  def __init__(self, plotting_session):
    '''
      Class consturctor.
      
      @param plotting_session A session object derived from GenericSession.
    '''
    self.content = []
    self.plotting_session=plotting_session
    #self.gtk=gtk

  def write(self, string):
    '''
      Add content.
      
      @param string Output string of stderr or stdout
    '''
    string=string.replace('\b', '')
    self.content.append(string)
    while '\n' in self.content:
      self.content.remove('\n')
    if (len(string.splitlines())>0) and string.splitlines()[-1]!='':
      self.plotting_session.statusbar.push(0, string.splitlines()[-1])
    if (len(self.content)>0):
      self.plotting_session.statusbar.push(0, self.content[-1])
    while gtk.events_pending():
      gtk.main_iteration(False)
  
  def flush(self):
    '''
      Show last content line in statusbar.
    '''
    if (len(self.content)>0):
      self.plotting_session.statusbar.push(0, self.content[-1])
      while gtk.events_pending():
        gtk.main_iteration(False)



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
  '''
  active_session_class = getattr(__import__('sessions.'+measurement_type[0], globals(), locals(), 
                                      [measurement_type[1]]), measurement_type[1])
  return active_session_class(arguments)

if __name__ == '__main__':    #code to execute if called from command-line
  # initialize session and read data files

  if (len(sys.argv) == 1):
    # if no input parameter given, print the short help string
    print GenericSession.SHORT_HELP
    exit()
  elif sys.argv[1] in known_measurement_types:
    # type is found in dictionary, using specific session
    measurement_type=known_measurement_types[sys.argv[1]]
    active_session=import_session_from_name(sys.argv[2:], measurement_type)
  else:
    found_sessiontype=False
    suffixes=map(lambda arg: arg.split('.')[-1], sys.argv[1:])
    for name, measurement_type in known_measurement_types.items():
      if found_sessiontype:
        break
      for suffix in measurement_type[2]:
        if suffix in suffixes:
          print "Setting session type to " + name + '.'
          active_session=import_session_from_name(sys.argv[1:], measurement_type)
          found_sessiontype=True
          break
    if not found_sessiontype:
      # type is not found, using generic session
      active_session=GenericSession(sys.argv[1:])

  if active_session.use_gui: # start a new gui session
    # GUI module
    import plotting_gui
    import gtk
    plotting_session=plotting_gui.ApplicationMainWindow(active_session)
    if not active_session.DEBUG:
      # redirect script output to session objects
      active_session.stdout=RedirectOutput(plotting_session)
      active_session.stderr=RedirectOutput(plotting_session)
      sys.stdout=active_session.stdout
      sys.stderr=active_session.stderr  
    gtk.main() # start GTK engine
  else: # in command line mode, just plot the selected data.
    active_session.plot_all()

  # delete temporal files and folder
  active_session.os_cleanup()
