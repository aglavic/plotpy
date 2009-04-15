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
# Additional Files: measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   SQUID_read_data.py - functions for data extraction                          #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   gnuplot_preferences_SQID.py - additional settings only for this script      #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert .out space(and other)seperated text files, splitted by sequences                     #
# -plot every sequence as extra picture or in one graph                                         #
# -process more than one file (wild cards possible)                                             #
# -select columns to be plotted                                                                 #
# -convert units to SI (or any selected)                                                        #
# -send all files to printer after processing (linux commandline printing)                      #
# -GUI with many features                                                                       #
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
from plot_generic_data import generic_session
# derived classes
from plot_SQUID_data import squid_session
from plot_4circle_data import circle_session
from plot_reflectometer_data import reflectometer_session
#----------------------- importing modules --------------------------

'''
  Dictionary for the known measurement types, to create a new measureing type
  it is only needed to create the seesion class and add it to this dictionary.
  
  Although the commandline parameter order is not importent for all other options
  the type has to be set first, as the other parameters are evaluated according to
  the session.
'''
known_measurement_types={
                         'squid': squid_session, 
                         '4circle': circle_session, 
                         'refl': reflectometer_session, 
                         }

  
class RedirectOutput:
  '''
    Class to redirect the all print statements when useing the GUI.
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
  print generic_session.short_help
  exit()
elif sys.argv[1] in known_measurement_types: 
  # type is found in dictionary, using specific session
  active_session=known_measurement_types[sys.argv[1]](sys.argv[2:])
else:
  # type is not found, using generic session
  active_session=generic_session(sys.argv[1:])


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
