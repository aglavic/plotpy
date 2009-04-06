#!/usr/bin/env python
'''
  main script which imports the other modules
'''
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
#                  including a graphical user interface and easy andling                        #
#                                       last changes:                                           #
#                                        31.03.2008                                             #
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

# importing python modules
import sys

# importing own modules
import plotting_gui

#+++++++++++++++++++++++ import specific measurement modules ++++++++++++++++++++++++++++++
from plot_generic_data import generic_session
from plot_SQUID_data import squid_session
from plot_4circle_data import circle_session
from plot_reflectometer_data import reflectometer_session
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
  print generic_session.short_help
  exit()
elif sys.argv[1] in known_measurement_types:
  active_session=known_measurement_types[sys.argv[1]](sys.argv[2:])
else:
  active_session=generic_session(sys.argv[1:])


if active_session.use_gui: # start a new gui session
  import gtk
  plotting_gui.ApplicationMainWindow(active_session)
  gtk.main()
else: # in command line mode, just plot the selected data.
  active_session.plot_all()

# delete temporal stuff
active_session.os_cleanup()
