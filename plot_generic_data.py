#!/usr/bin/env python
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
#                    this is the class used as parent for every session                         #
#                                       last changes:                                           #
#                                        31.03.2008                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#################################################################################################

# importing python modules
import os
import math

# importing own modules
from measurement_data_structure import *
import measurement_data_plotting
from gnuplot_preferences import print_command

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
\t\t type can be one of 'squid', '4circle', 'refl' or none

Options:
\t--help\t\tPrint this information, start plot.py [type] --help for a type specific help

\tSequence settings:
\t-a\t\tPlot all sequences in one picture
\t-s [a] [b]\tOnly plot sequence a to b (standard is 1 to 10000)
\t-s2 [b]\t\tSet last sequence to be plotted
\t-i [inc]\tPlot only every inc sequence
\t-l\t\tList sequences in file.
\t-ls\t\tList selected Sequences.

\tOutput settings:
\t-gs\t\tUse gnuplot in script mode, in the case Gnuplot.py is not working (slower)
\t-o\t\tOutput the data to .out files for later use in other programms.
\t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
\t-c\t\tJust convert files, do not plot anything
\t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
\t-p\t\tSend plots to printer specified in gnuplot_perferences.py

\tPlott settings:
\t-e\t\tPlot with errorbars
\t-logx\t\tPlot with errorbars
\t-logy\t\tPlot with errorbars
\t-scp\t\tUse script mode, no GUI will be shown

\tGeneral Data treatment:
\t-no-trans\tdon't make a unit transformation
"""
  long_help_end=\
"""
The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in SQUID_preferences.py.
"""
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_data={} # dictionary for the data objects indexed by filename
  active_file_data=None
  active_file_name=''
  index=0
  file_wildcards=(('all files', '*'))
  options=['s','s2','i','gs','o','ni','c','l','sc','st','sxy','e', 'logx', 'logy','scp', 'no-trans','help']
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
  logx=False
  logy=False
  print_plot=False # send plots to printer
  unit_transformation=True # make transformations as set in preferences file
  transformations=[] # a list of unit transformations, that will be performed on the data
  own_pid=None # stores session process ID
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
      print self.long_help + self.specific_help + self.long_help_end
      exit()
    elif len(files) < 1: # show help, if there is no file in the list
      print self.short_help
      exit()
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    self.os_path_stuff() # create temp folder according to OS
    if (not self.gnuplot_script): # verify gnuplot.py is installed
      try:
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
    files.sort()
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    for filename in files:
      self.add_file(filename)
    self.active_file_data=self.file_data[files[0]]
    self.active_file_name=files[0]
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
          elif self.read_argument_add(argument,  last_argument_option)[0]:
            last_argument_option=self.read_argument_add(argument,  last_argument_option)[1]
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
        elif argument=='-logx':
          self.logx=True
        elif argument=='-logy':
          self.logy=True
        elif argument=='-p':
          self.print_plot=True
        elif argument=='-scp':
          self.use_gui=False
        elif argument=='-no-trans':
          self.unit_transformation=False
        elif argument=='--help':
          return None
        elif self.read_argument_add(argument,  last_argument_option)[0]:
          last_argument_option=self.read_argument_add(argument,  last_argument_option)[1]
        else:
          if argument[1:len(argument)] in self.options:
            last_argument_option=[True,argument[1:len(argument)]]
          else:
            print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
      else:
        input_file_names.append(argument)
    return input_file_names
      
  '''
    Dummi function for child classes, which makes it possible to
    add command line options for them.
  '''
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    # as function does not contain new options it returns false
    return (False, last_argument_option)

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
    delete temporal files and folder
  '''
  def os_cleanup(self):
    for file_name in os.listdir(self.temp_dir):
      os.remove(self.temp_dir+file_name)
    os.rmdir(self.temp_dir)

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
    dataset=None
    if os.path.exists(filename):
      input_file_lines=open(filename,'r').readlines()
      for line in input_file_lines:
        if line[0]=='#':
          continue
        if (dataset==None and len(line.split())>=2):
          columns=['col-'+str(number) for number in range(len(line.split()))]
          dataset=MeasurementData(columns,[], 0, 1, 2)
          try:
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
    else:
      print 'File '+filename+' does not exist.'
    return data_list
  
  '''
    give the sequences numbers with leading zeros
  '''
  def create_numbers(self, datasets):
    filtered_datasets=[]
    for i, dataset in enumerate(datasets):
      j=i+1
      # only use sequences inside the boundaries and with the right increment
      if (j>=self.seq[0]) and (j<=self.seq[1]) and (((j-self.seq[0]) % self.seq_inc) == 0):
        filtered_datasets.append(dataset)
        # set number string depending on the length of the last number
        dataset.number='000000'.replace('0','',6-len(str(len(datasets)+1))+len(str(i+1)))+str(i+1)
    return filtered_datasets
  
  '''
    Make unit transformations of a list of datasets
  '''
  def make_transformations(self, datasets):
    for dataset in datasets:
      dataset.unit_trans(self.transformations)

  '''
    Function which ither adds file data to the object or replaces
    all data by a new list.
  '''
  def add_data(self, data_list, name, append=True):
    if not append:
      self.file_data={}
    self.file_data[name]=data_list
  
  '''
    Add the data of a new file to the session.
    Transformations are also done here, so childs
    will change this function.
  '''
  def add_file(self, filename, append=True):
    print "Trying to import '" + filename + "'."
    datasets=self.read_file(filename)
    datasets=self.create_numbers(datasets) # enumerate the sequences and sort out unselected
    if self.unit_transformation:
      self.make_transformations(datasets) # make unit transformations
    self.add_data(datasets, filename, append)
    #++++++++++++++++ datatreatment ++++++++++++++++++++++
    if self.unit_transformation: # make unit transfomation on all datasets
      self.make_transformations(datasets)
    for dataset in datasets:
      dataset.logx=self.logx
      dataset.logy=self.logy
    return datasets # for reuse in child class
  
  def __iter__(self): # see next()
    return self

  ''' 
    function to iterate through the file_data dictionary, object can be used in "for name in data:"
    also changes the active_file_data and active_file_name
  '''
  def next(self): 
    name_list=[item[0] for item in self.file_data.items()]
    name_list.sort()
    if self.index == len(name_list):
      self.index=0
      raise StopIteration
    self.index=self.index+1
    self.active_file_data=self.file_data[name_list[self.index-1]]
    self.active_file_name=name_list[self.index-1]
    return self.active_file_name

  '''
    Plots the active datasets
  '''
  def plot_active(self):
    if not self.single_picture:
      for dataset in self.active_file_data:
        self.plot([dataset], self.active_file_name, dataset.short_info, [''])
    else:
      self.plot(self.active_file_data, self.active_file_name, '', [dataset.short_info for dataset in self.active_file_data])

  '''
    plot everything selected from all files
  '''
  def plot_all(self):
    for name in self:
      print "Plotting '"+ name +"' sequences."
      self.plot_active()
  
  '''
    Plot one or a list of datasets
  '''
  def plot(self, datasets, file_name_prefix, title, names):
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

  '''
    change the active dataset by object or name
  '''
  def change_active(self, object=None, name=None):
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
  
  '''
    create a specifig menu for the session
  '''
  def create_menu(self):
    return '',  ()
