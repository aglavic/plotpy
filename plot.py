#!/usr/bin/env python
#################################################################################################
#                    Script to plot different-measurements with gnuplot                         #
#                  including a graphical user interface and easy andling                        #
#                                       last changes:                                           #
#                                        25.03.2008                                             #
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
import os
import sys
import math

# importing own modules
from measurement_data_structure import *
import measurement_data_plotting
from gnuplot_preferences import print_command
import plotting_gui

# import specific measurement modules
import plot_SQUID_data
import plot_4circle_data
import plot_reflectometer_data
# dictionary for the known measurement types
known_measurement_types={
                         'squid': plot_SQUID_data.squid_session, 
                         '4circle': plot_4circle_data.circle_session, 
                         'reflectometer': plot_reflectometer_data.reflectometer_session, 
                         }

'''
  This is the class valid the whole session to read the files 
  and store the measurement data object.
  It contains the common functions used for every type of data
  plus data reading for space separated common files.

  Specific measurements are childs of this class!
'''
class generic_session():
  #++++++++++++++++++ help text strings +++++++++++++++
  short_help=\
"""
\tUsage: plot.py [type] [files] [options]
\tRun plot.py --help for more information.
"""
  specific_help='' # help text for child classes
  long_help=\
"""
Script to plot data of measurements using gnuplot.
Usage: plot.py [type] [files] [options]
\t\t type can be one of 'squid', '4circle', 'reflectometer' or none

\tOptions:
\t\t--help\t\tPrint this information, start plot.py [type] --help for a type specific help

Sequence settings:
\t\t-a\t\tPlot all sequences in one picture
\t\t-s [a] [b]\tOnly plot sequence a to b (standard is 1 to 10000)
\t\t-s2 [b]\t\tSet last sequence to be plotted
\t\t-i [inc]\tPlot only every inc sequence
\t\t-l\t\tList sequences in file.
\t\t-ls\t\tList selected Sequences.

Output settings:
\t\t-gs\t\tUse gnuplot in script mode, in the case Gnuplot.py is not working (slower)
\t\t-o\t\tOutput the data to .out files for later use in other programms.
\t\t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
\t\t-c\t\tJust convert files, do not plot anything
\t\t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
\t\t-p\t\tSend plots to printer specified in gnuplot_perferences.py

Plott settings:
\t\t-sc\t\tSelect columns different from SQUID_preferences.py settings
\t\t-st\t\tSelect measurement typs different from SQUID_preferences.py settings
\t\t-sxy\t\tSelect other x-,y- and dy- columns to plot
\t\t-e\t\tPlot with errorbars
\t\t-gui\t\tShow graphs in plotting GUI (experimental, pygtk package needed)

""" + self.specific_help + """

The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in SQUID_preferences.py.
"""
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_data={} # dictionary for the data objects indexed by filename
  active_file_data=None
  #------------------ local variables -----------------

  '''
    Class constructor which is called with the command line arguments.
    Evaluates the command line arguments, creates a file list and
    starts the data readout procedure.
  '''
  def __init__(self, arguments):
    files=self.read_arguments(arguments) # get filenames and set options
    if files==None: # read_arguments returns none, if help option is set
      print self.long_help
      return None
    elif len(files) < 1: # show help, if there is no file in the list
      print self.short_help
      return None
    for filename in files:
      self.add_data(self.read_file(filename), filename)
    active_file_data=file_data[files[0]]

  '''
    Function to evaluate the command line arguments.
    Returns a list of filenames.
  '''
  def read_arguments(self, arguments):
    input_file_names=[]
    last_argument_option=[False,'']
    for argument in arguments: # iterate through all options
      if (argument[0]=='-')|last_argument_option[0]:
          # Cases of arguments:
        if last_argument_option[0]:
          if last_argument_option[1]=='s':
            seq=[int(argument),seq[1]]
            last_argument_option=[True,'s2']
          elif last_argument_option[1]=='s2':
            seq=[seq[0],int(argument)]
            last_argument_option=[False,'']
          elif last_argument_option[1]=='i':
            inc=int(argument)
            last_argument_option=[False,'']
          elif read_argument_add(argument,  last_argument_option):
            continue
          else:
            input_file_names.append(argument)
            last_argument_option=[False,'']
        elif argument=='-a':
          single_picture=True
        elif argument=='-l':
          list_all=True
        elif argument=='-ls':
          list_sequences=True
        elif argument=='-gs':
          gnuplot_script=True
        elif argument=='-o':
          do_output=True
        elif argument=='-ni':
          info_in_file=False
        elif argument=='-c':
          plot_data=False
        elif argument=='-sc':
          select_columns=True
        elif argument=='-st':
          select_type=True
        elif argument=='-sxy':
          select_xy=True
        elif argument=='-e':
          plot_with_errorbars=True
        elif argument=='-p':
          print_plot=True
        elif argument=='-gui':
          plot_with_GUI=True
        elif argument=='-no-trans':
          unit_transformation=False
        elif argument=='--help':
          print help_statement()
        elif read_argument_add(argument):
          continue
        else:
          try:
            ['s','s2','i','gs','o','ni','c','l','sc','st','sxy','e','gui','p'].index(argument[1:len(argument)])
          except ValueError:
            print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
          else:
            last_argument_option=[True,argument[1:len(argument)]]
      else:
        input_file_names.append(argument)
    return input_file_names
      
  '''
    Dummi function for child classes, which makes it possible to
    add command line options for them.
  '''
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    # as function does not contain new options it returns false
    return False
   
  '''
    Function which reads one datafile and returns a list
    of measurement_data_structure objects splitted into
    sequences.
  '''
  def read_file(self, filename):
    data_list=[]
    # to be added
    return data_list

  '''
    Function which ither adds file data to the object or replaces
    all data by a new list.
  '''
  def add_data(self, data_list, name, append=True):
    if not append:
      self.file_data={}
    self.file_data[name]=data_list
  
'''
############################################################################
  Here the actual script starts. It creates one session object according
  to the selected type of the data and reads all files specified by the
  user. The session object is then ither used for a direct plotting or
  piped to a plotting_gui for later use.
############################################################################
'''
if len(sys.argv == 1):
  print generic_session.short_help
elif sys.argv[1] in known_measurement_types:
  active_session=known_measurement_types[sys.argv[1]](sys.argv[2:])
else:
  active_session=generic_session(sys.argv[1:])

if active_session.use_gui: # start a new gui session
   plotting_gui.ApplicationMainWindow(active_session)
   gtk.main()
else:
   active_session.plot_all()
   
