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
#                   SQUID_preferences.py - settings for the squid session                       #
#                   SQUID_read_data.py - functions for data extraction                          #
#                   plot_4circle_data.py - 4circle session class for spec data                  #
#                   circle_preferences.py - settings for the 4circle session                    #
#                   circle_read_data.py - functions for data extraction                         #
#                   plot_reflectometer_data.py - reflectometer session class                    #
#                   reflectometer_preferences.py - settings for the reflectometer session(+fit) #
#                   reflectometer_read_data.py - functions for data extraction                  #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                                                                                               #
#################################################################################################

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import sys

# own modules
# GUI module
import plotting_gui
# specific measurement classes
# parent class
from plot_generic_data import GenericSession
# derived classes
from plot_SQUID_data import SquidSession
from plot_4circle_data import CircleSession
from plot_reflectometer_data import ReflectometerSession
from plot_treff_data import TreffSession
#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.2"
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
                         'squid': SquidSession, 
                         '4circle': CircleSession, 
                         'refl': ReflectometerSession, 
                         'treff': TreffSession, 
                         }

  
class RedirectOutput:
  '''
    Class to redirect all print statements when useing the GUI.
  '''
  def __init__(self, plotting_session):
    '''Class consturctor.'''
    self.content = []
    self.plotting_session=plotting_session
    #self.gtk=gtk

  def write(self, string):
    '''Add content.'''
    string=string.replace('\b', '')
    self.content.append(string)
    while '\n' in self.content:
      self.content.remove('\n')
    if (len(string.splitlines())>0) and string.splitlines()[-1]!='':
      self.plotting_session.statusbar.push(0, string.splitlines()[-1])
  
  def flush(self):
    '''Show last content line in statusbar.'''
    if (len(self.content)>0):
      self.plotting_session.statusbar.push(0, self.content[-1])
      gtk.main_iteration(False)



'''
############################################################################
  Here the actual script starts. It creates one session object according
  to the selected type of the data and reads all files specified by the
  user. The session object is then ither used for a direct plotting or
  piped to a plotting_gui for later use.
############################################################################
'''

# initialize session and read data files
if (len(sys.argv) == 1):
  # if no input parameter given, print the short help string
  print GenericSession.SHORT_HELP
  exit()
elif sys.argv[1] in known_measurement_types: 
  # type is found in dictionary, using specific session
  active_session=known_measurement_types[sys.argv[1]](sys.argv[2:])
else:
  # type is not found, using generic session
  active_session=GenericSession(sys.argv[1:])


if active_session.use_gui: # start a new gui session
  import gtk
  plotting_session=plotting_gui.ApplicationMainWindow(active_session)
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
