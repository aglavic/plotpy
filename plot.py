#!/usr/bin/env python
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
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
#import plot_SQUID_data
#import plot_4circle_data
#import plot_reflectometer_data
# dictionary for the known measurement types
known_measurement_types={}
'''                         'squid': plot_SQUID_data.squid_session, 
                         '4circle': plot_4circle_data.circle_session, 
                         'reflectometer': plot_reflectometer_data.reflectometer_session, 
                         }'''

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
\t\t-e\t\tPlot with errorbars
\t\t-scp\t\tUse script mode, no GUI will be shown

""" + specific_help + """

The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in SQUID_preferences.py.
"""
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_data={} # dictionary for the data objects indexed by filename
  active_file_data=None
  index=0
  # options:
  use_gui=True # activate graphical user interface
  seq=[1, 10000] # use sequences from 1 to 10 000
  seq_inc=1 # use every sequence
  single_picture=False # plot all sequences in one picture
  list_all=False # show a list of sequences found in the file
  list_sequences=False # show a list of sequences found in the file which are selected for plotting
  gnuplot_script=False # use script mode
  do_output=False # export .out files
  info_in_file=True # write header in output files
  plot_data=True # plot the data (otherwise only convert files)
  plot_with_errorbars=False # use errorbars in plot
  print_plot=False # send plots to printer
  unit_transformation=True # make transformations as set in preferences file
  own_pid=None
  #------------------ local variables -----------------

  '''
    Class constructor which is called with the command line arguments.
    Evaluates the command line arguments, creates a file list and
    starts the data readout procedure.
  '''
  def __init__(self, arguments):
    #++++++++++++++++ evaluate command line +++++++++++++++++++++++
    files=self.read_arguments(arguments) # get filenames and set options
    if files==None: # read_arguments returns none, if help option is set
      print self.long_help
      return None
    elif len(files) < 1: # show help, if there is no file in the list
      print self.short_help
      return None
    files.sort()
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    for filename in files:
      self.add_data(self.read_file(filename), filename)
    self.active_file_data=self.file_data[files[0]]
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    os_path_stuff() # create temp folder according to OS
    if (not self.gnuplot_script): # verify gnuplot.py is installed
      try:
        import Gnuplot
      except ImportError:
        print "Gnuplot.py not available, falling back to script mode!"
        self.gnuplot_script=True
    if self.plot_with_GUI: # verify pygtk is installed
      try:
        import gtk
      except ImportError:
        print "You have to install pygtk to run in GUI-mode, falling back to command-line mode!"
        self.plot_with_GUI=False
    #---------------- class consturction over ---------------------

    

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
            self.seq=[int(argument),self.seq[1]]
            last_argument_option=[True,'s2']
          elif last_argument_option[1]=='s2':
            self.seq=[self.seq[0],int(argument)]
            last_argument_option=[False,'']
          elif last_argument_option[1]=='i':
            self.seq_inc=int(argument)
            last_argument_option=[False,'']
          elif self.read_argument_add(argument,  last_argument_option):
            continue
          else:
            input_file_names.append(argument)
            last_argument_option=[False,'']
        elif argument=='-a':
          self.single_picture=True
        elif argument=='-l':
          self.list_all=True
        elif argument=='-ls':
          self.list_sequences=True
        elif argument=='-gs':
          self.gnuplot_script=True
        elif argument=='-o':
          self.do_output=True
        elif argument=='-ni':
          self.info_in_file=False
        elif argument=='-c':
          self.plot_data=False
        elif argument=='-e':
          self.plot_with_errorbars=True
        elif argument=='-p':
          self.print_plot=True
        elif argument=='-scp':
          self.use_gui=False
        elif argument=='-no-trans':
          self.unit_transformation=False
        elif argument=='--help':
          print self.long_help
        elif self.read_argument_add(argument):
          continue
        else:
          try:
            ['s','s2','i','gs','o','ni','c','l','sc','st','sxy','e','scp','p'].index(argument[1:len(argument)])
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
    Create the session temp directory
  '''
  def os_path_stuff(self):
    self.own_pid=str(os.getpid())
    if (os.getenv("TEMP")==None):
    # Linux case
      self.temp_dir="/tmp/"
      # name of the gnuplot command under linux
      self.gnuplot_command="gnuplot"
    else:
    # Windows case
      self.temp_dir=os.getenv("TEMP")+'\\'
      # name of the gnuplot command under windows
      self.gnuplot_command="pgnuplot"
      def replace_systemdependent(self, string): # replace backthlash by double backthlash for gnuplot under windows
        return string.replace('\\','\\\\').replace('\\\\\n','\\\n')
      self.replace_systemdependent=replace_systemdependent
    self.temp_dir=self.temp_dir+'plottingscript-'+self.own_pid+os.sep
    os.mkdir(self.temp_dir) # create the temporal directory



  '''
    function for path name replacements under windows,
    in linux this is just a dummi method
  '''
  def replace_systemdependent(self, string):
    return string

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
if (len(sys.argv) == 1):
  print generic_session.short_help
  exit()
elif sys.argv[1] in known_measurement_types:
  active_session=known_measurement_types[sys.argv[1]](sys.argv[2:])
else:
  active_session=generic_session(sys.argv[1:])
  
'''
if active_session.use_gui: # start a new gui session
   plotting_gui.ApplicationMainWindow(active_session)
   gtk.main()
else:
   active_session.plot_all()
'''
