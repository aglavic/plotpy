#!/usr/bin/env python
'''
  Gneric session class, parent class for all sessions. This includes commandline argument
  processing, help text, generic file readout, os specific temp file handling and storing
  of global variables.
'''
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
#                    this is the class used as parent for every session                         #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -process command line parameters                                                              #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -send all files to printer after processing (linux commandline printing)                      #
#                                                                                               #
#################################################################################################

# importing python modules
import os
import math
import subprocess
from cPickle import load, dump
from measurement_data_structure import MeasurementData
import measurement_data_plotting
from config.gnuplot_preferences import PRINT_COMMAND

# importing own modules

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class GenericSession:
  '''
    This is the class valid the whole session to read the files 
    and store the measurement data objects.
    It contains the common functions used for every type of data
    plus data reading for space separated common files.

    Specific measurements are childs of this class!
  '''
  #++++++++++++++++++ help text strings +++++++++++++++
  SHORT_HELP=\
"""
\tUsage: plot.py [type] [files] [options]
\tRun plot.py --help for more information.
"""
  SPECIFIC_HELP='' # help text for child classes
  LONG_HELP=\
"""
Script to plot data of measurements using gnuplot.

Usage: plot.py [type] [files] [options]
\t\t type can be one of 'squid', '4circle', 'refl', 'treff' or none (than it tries to find the type itself)

Options:
\t--help\t\tPrint this information, start plot.py [type] --help for a type specific help

\tSequence settings:
\t-a\t\tPlot all sequences in one picture
\t-s [a] [b]\tOnly plot sequence a to b (standard is 1 to 10000)
\t-s2 [b]\t\tSet last sequence to be plotted
\t-i [inc]\tPlot only every inc sequence

\tInput/Output settings:
\t-gs\t\tUse gnuplot in script mode, in the case Gnuplot.py is not working (slower)
\t-rd\t\tRead file directly, do not use .mds file created in earlier runs.
\t-no-mds\t\tDon't create .mds files. (.mds files are used for faster reaccessing)

\tPlott settings:
\t-e\t\tPlot with errorbars
\t-logx\t\tPlot logarithmic in x
\t-logy\t\tPlot logarithmic in y
\t-logz\t\tPlot logarithmic in z
\t-scp\t\tUse script mode, no GUI will be shown

\tGeneral Data treatment:
\t-no-trans\tdon't make a unit transformation
"""
  # TODO: implement these settings
  '''    from cPickle import load, dump

  \t-l\t\tList sequences in file.
  \t-ls\t\tList selected Sequences.

  \t-o\t\tOutput the data to .out files for later use in other programms.
  \t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
  \t-c\t\tJust convert files, do not plot anything
  \t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
  \t-p\t\tSend plots to printer specified in gnuplot_perferences.py
  '''

  LONG_HELP_END=\
"""
The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in config.squid.py.
"""
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_data={} #: dictionary for the data objects indexed by filename
  active_file_data=None # pointer for the data of the current file
  active_file_name='' # the name of the current file
  index=0
  FILE_WILDCARDS=(('all files', '*')) # wildcards for the file open dialog of the GUI
  # known command line options list
  COMMANDLINE_OPTIONS=['s','s2','i','gs','rd', 'no-mds', 'o','ni','c','sc','st','sxy','e', 'logx', 'logy', 'logz','scp', 'no-trans','help']
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
  logx=False # plot logarithmic in x direction
  logy=False # plot logarithmic in y direction
  logz=False # plot logarithmic in z direction
  picture_width='800'
  picture_height='600'
  # TODO: command line file printing hast to be added.
  print_plot=False # send plots to printer
  unit_transformation=True # make transformations as set in preferences file
  TRANSFORMATIONS=[] # a list of unit TRANSFORMATIONS, that will be performed on the data
  read_directly=False # don't use pickled file, read the data diretly
  mds_create=True
  #------------------ local variables -----------------

  def __init__(self, arguments):
    '''
      Class constructor which is called with the command line arguments.
      Evaluates the command line arguments, creates a file list and
      starts the data readout procedure.
      
      @param arguments The command line arguments passed to the constructor.
    '''
    #++++++++++++++++ evaluate command line +++++++++++++++++++++++
    files=self.read_arguments(arguments) # get filenames and set options
    if files==None: # read_arguments returns none, if help option is set
      print self.LONG_HELP + self.SPECIFIC_HELP + self.LONG_HELP_END
      exit()
    elif len(files) < 1: # show help, if there is no file in the list
      print self.SHORT_HELP
      exit()
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    self.os_path_stuff() # create temp folder according to OS
    self.try_import_externals()
    files.sort()
    remove=[]
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    for filename in files:
      if self.add_file(filename)==[]:
        # if a file is empty or a reading error occured remove it.
        remove.append(filename)
    for rem in remove:
      files.remove(rem)

    if len(files) == 0: # show help, if there is no valid file in the list
      print "No valid datafile found!"
      print self.SHORT_HELP
      exit()
    self.active_file_data=self.file_data[files[0]]
    self.active_file_name=files[0]

  #---------------- class consturction over ---------------------

  def try_import_externals(self):
    '''
      Try to import modules not part of core python.
      Gnuplot.py has no error reporting, so we change some settings
      to make it work.
    '''
    if (not self.gnuplot_script): # verify gnuplot.py is installed
      try:
        # replace os.popen function to make the output readable
        def new_popen(cmd, ignore, bufsize=0):
          proc=subprocess.Popen(cmd, 
                                shell=True, 
                                bufsize=bufsize, 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
          self.gnuplot_output=(proc.stdout, proc.stderr)
          return proc.stdin
        os.popen=new_popen        
        import Gnuplot
      except ImportError:
        print "Gnuplot.py not available, falling back to script mode!"
        self.gnuplot_script=True
    if self.use_gui: # verify pygtk is installed
      try:
        import gtk
      except ImportError:
        print "You have to install pygtk to run in GUI-mode, falling back to command-line mode!"
        self.use_gui=False
    try: # verify mathematic modules needed for fitting
      import numpy
      import scipy
      self.ALLOW_FIT=True
    except ImportError:
      print "Numpy and/or Scipy is not installed, fitting will not be possible."
      self.ALLOW_FIT=False

  def read_arguments(self, arguments):
    '''
      Function to evaluate the command line arguments.
      Returns a list of filenames.
      
      @param arguments The command line arguments to evaluate.
      @return A list of file names to import.
    '''
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
          elif self.read_argument_add(argument,  last_argument_option)[0]:
            last_argument_option=self.read_argument_add(argument,  last_argument_option)[1]
          else:
            input_file_names.append(argument)
            last_argument_option=[False,'']
        elif argument=='-a':
          self.single_picture=True
       # elif argument=='-l':
       #   self.list_all=True
       # elif argument=='-ls':
       #   self.list_sequences=True
        elif argument=='-gs':
          self.gnuplot_script=True
        elif argument=='-rd':
          self.read_directly=True
        elif argument=='-no-mds':
          self.mds_create=False
        elif argument=='-o':
          self.do_output=True
        elif argument=='-ni':
          self.info_in_file=False
        elif argument=='-c':
          self.plot_data=False
        elif argument=='-e':
          self.plot_with_errorbars=True
        elif argument=='-logx':
          self.logx=True
        elif argument=='-logy':
          self.logy=True
        elif argument=='-logz':
          self.logz=True
        elif argument=='-p':
          self.print_plot=True
        elif argument=='-scp':
          self.use_gui=False
        elif argument=='-no-trans':
          self.unit_transformation=False
        elif argument=='--help':
          return None
        # evaluate child arguments
        elif self.read_argument_add(argument,  last_argument_option)[0]:
          last_argument_option=self.read_argument_add(argument,  last_argument_option)[1]
        else:
          if argument[1:len(argument)] in self.COMMANDLINE_OPTIONS:
            last_argument_option=[True,argument[1:len(argument)]]
          else:
            print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
      else:
        input_file_names.append(argument)
    return input_file_names
      
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      Dummi function for child classes, which makes it possible to
      add command line options for them.
      
      @return A Squence depending on the found parameters.
    '''
    # as function does not contain new options it returns false
    return (False, last_argument_option)

  def os_path_stuff(self):
    '''
      Create the session temp directory. Is only called once
      when initializing the session. Has not been tested in
      OSX.
    '''
    self.OWN_PID=str(os.getpid())
    SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__).replace('sessions', ''))
    if (os.getenv("TEMP")==None):
    # Linux case
      self.OPERATING_SYSTEM='linux'
      self.TEMP_DIR="/tmp/"
      self.SCRIPT_PATH=SCRIPT_PATH + '/'
      # name of the gnuplot command under linux
      self.GNUPLOT_COMMAND="gnuplot"
    else:
    # Windows case
      self.OPERATING_SYSTEM='windows'
      self.TEMP_DIR=os.getenv("TEMP")+'\\'
      self.SCRIPT_PATH=SCRIPT_PATH + '\\'
      # name of the gnuplot command under windows
      self.GNUPLOT_COMMAND="pgnuplot"
      def replace_systemdependent( string): # replace backthlash by double backthlash for gnuplot under windows
        return string.replace('\\','\\\\').replace('\\\\\n','\\\n')
      self.replace_systemdependent=replace_systemdependent
    self.TEMP_DIR=self.TEMP_DIR+'plottingscript-'+self.OWN_PID+os.sep
    try:
      os.mkdir(self.TEMP_DIR) # create the temporal directory
    except WindowsError:
      pass

  def os_cleanup(self):
    '''
      Delete temporal files and folder.
    '''
    for file_name in os.listdir(self.TEMP_DIR):
      os.remove(self.TEMP_DIR+file_name)
    os.rmdir(self.TEMP_DIR)

  def replace_systemdependent(self, string):
    '''
      Function for path name replacements. Only under windows,
      in linux this is just a dummi method returning the same
      string.
      
      @return The replaced string.
    '''
    return string

  def read_file(self, filename):
    '''
      Function which reads one datafile and returns a list
      of measurement_data_structure objects splitted into
      sequences. Every child class will overwrite this.
      
      @return A list of datasets that has been found.
    '''
    data_list=[]
    dataset=None
    if os.path.exists(filename): # Test if the file exists
      input_file_lines=open(filename,'r').readlines()
      # iterate through all lines and split the columns.
      for line in input_file_lines:
        if line[0]=='#': # ignore comment lines
          continue
        if (dataset==None and len(line.split())>=2):
          columns=[('col-'+str(number), '') for number in range(len(line.split()))]
          dataset=MeasurementData(columns,[], 0, 1, 2)
          try: # only import numbers
            dataset.append([float(number) for number in line.split()])
          except ValueError:
            print 'Unknown data type in file '+filename+'. Skipped!'
            return []
          dataset.info=filename+'-'+str(len(data_list)+1)
        if  len(line.split())<2: # empty line is treated as sequence splitting
          if dataset!=None:
            data_list.append(dataset)
          dataset=None
          continue
        else:
          try:
            dataset.append([float(number) for number in line.split()])
          except ValueError:
            print 'Unknown data type in file "' + filename + '". Skipped!'
            return []
      return data_list
    else:
      print 'File '+filename+' does not exist.'
  
  def create_numbers(self, datasets):
    '''
      Give the sequences numbers with leading zeros depending on the
      number of sequences present in the file. Mostly usefull for
      file name perpose.
      This function also filteres the dataset for the values given
      by "-s from to" and "-i increment".
      
      @return The filtered list with the numbers set.
    '''
    filtered_datasets=[]
    for i, dataset in enumerate(datasets):
      j=i+1
      # only use sequences inside the boundaries and with the right increment
      if (j>=self.seq[0]) and (j<=self.seq[1]) and (((j-self.seq[0]) % self.seq_inc) == 0):
        filtered_datasets.append(dataset)
        # set number string depending on the length of the last number
        dataset.number='000000'.replace('0','',6-len(str(len(datasets)+1))+len(str(i+1)))+str(i+1)
    return filtered_datasets
  
  def make_transformations(self, datasets):
    '''
      Make unit transformations of a list of datasets.
    '''
    for dataset in datasets:
      dataset.unit_trans(self.TRANSFORMATIONS)

  def add_data(self, data_list, name, append=True):
    '''
      Function which ither adds file data to the object or replaces
      all data by a new dictionary.
    '''
    if not append:
      self.file_data={}
    self.file_data[name]=data_list
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      Transformations are also done here, so childs
      will change this function.
      
      @return A list of datasets that have been found in the file.
    '''
    # for faster access the MeasurementData objects are saved via cPickle
    # when this file exists it is used to reload it.
    # This can be ignored by the command line option '-rd'
    if os.path.exists(filename + '.mds') and not self.read_directly:
      print "Importing previously saved data from '" +filename + ".mds'."
      pickled=open(filename + '.mds', 'rb')
      datasets=load(pickled)
      pickled.close()
    else:
      print "Trying to import '" + filename + "'."
      datasets=self.read_file(filename)
      if datasets!=[] and self.mds_create:
        pickling=open(filename + '.mds', 'wb')
        dump(datasets, pickling, 2)
        pickling.close()
    if datasets=='NULL':
      return []
    datasets=self.create_numbers(datasets) # enumerate the sequences and sort out unselected
    self.add_data(datasets, filename, append)
    #++++++++++++++++ datatreatment ++++++++++++++++++++++
    self.new_file_data_treatment(datasets)
    return datasets # for reuse in child class

  def new_file_data_treatment(self, datasets):
    '''
      Perform common datatreatment tasks on all Datasets.
    '''
    if self.unit_transformation: # make unit transfomation on all datasets
      self.make_transformations(datasets)
    for dataset in datasets:
      self.single_dataset_data_treatment(dataset)

  def single_dataset_data_treatment(self, dataset):
    '''
      Perform actions on every dataset that is imported.
    '''
    dataset.logx=self.logx
    dataset.logy=self.logy
    dataset.logz=self.logz

  def __iter__(self): # see next()
    return self

  def next(self): 
    ''' 
      Function to iterate through the file_data dictionary. Object can be used in "for name in data:".
      Also changes the active_file_data and active_file_name.
    '''
    # TODO: In GUI export all files at once.
    name_list=[item[0] for item in self.file_data.items()]
    name_list.sort()
    if self.index == len(name_list): # after last stop iteration and go to first again
      self.index=0
      raise StopIteration
    self.index=self.index+1
    self.active_file_data=self.file_data[name_list[self.index-1]]
    self.active_file_name=name_list[self.index-1]
    return self.active_file_name

  def plot_active(self):
    '''
      Plots the active datasets.
    '''
    if not self.single_picture:
      for dataset in self.active_file_data:
        self.plot(dataset.plot_together, self.active_file_name, dataset.short_info, ['' for i in range(len(dataset.plot_together))])
    else:
      self.plot(self.active_file_data, self.active_file_name, '', [dataset.short_info for dataset in self.active_file_data])

  def plot_all(self):
    '''
      Plot everything selected from all files.
    '''
    for name in self:
      print "Plotting '" + name + "' sequences."
      self.plot_active()
  
  def plot(self, datasets, file_name_prefix, title, names):
    '''
      Plot one or a list of datasets.
      
      @return The stderr and stdout of gnuplot.
    '''
    # TODO: Use one plot function for GUI and script mode with less parameters.
    if len(datasets)>1:
      add_info='multi_'
    else:
      add_info=''
    if self.gnuplot_script:
      output=measurement_data_plotting.gnuplot_plot_script\
        (self, datasets,file_name_prefix, '.out', title,names,self.plot_with_errorbars,additional_info=add_info)
      return output
    else:
      return measurement_data_plotting.gnuplot_plot\
        (self, datasets,file_name_prefix, title,names,self.plot_with_errorbars,additional_info=add_info)

  def change_active(self, object=None, name=None):
    '''
      Change the active data file by object or name.
    '''
    name_list=[item[0] for item in self.file_data.items()]
    name_list.sort()
    if object!=None:
      self.active_file_name=object[0]
      self.active_file_data=object[1]
      self.index=name_list.index(object[0])
    elif name!=None:
      try:
        self.active_file_data=self.file_data[name]
        self.active_file_name=name
        self.index=name_list.index(name)
      except KeyError:
        None
    else:
      None
  
  def create_menu(self):
    '''
      Create a specifig menu for the session. Only child classes
      will add anything here.
    '''
    return '',  ()