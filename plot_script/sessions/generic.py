# -*- encoding: utf-8 -*-
'''
  Generic session class, parent class for all sessions. This includes command
  line argument processing, help text, generic file readout, 
  OS specific temp file handling and storing of global variables.
'''

# importing python modules
import os
import sys

from time import sleep
import subprocess
from cPickle import load, dumps, dump
from plot_script import  measurement_data_structure
from plot_script import  measurement_data_plotting
from plot_script import  parallel
from plot_script.config import gnuplot_preferences, transformations, user_config
from plot_script.config import templates as template_config
from plot_script.read_data import GENERIC_FORMATS

# importing own modules

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

# if python version < 2.5 set the sys.exit function as exit
if hex(sys.hexversion)<'0x2050000':
  exit=sys.exit #@ReservedAssignment

# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.generic', fromlist=['GenericGUI']).GenericGUI
except ImportError:
  class GUI: pass

class GenericSession(GUI):
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
  LONG_HELP="""
Script to plot data of measurements using gnuplot by Artur Glavic.
\t\tVersion: %s \t Contact: %s

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
\t-ipy "[line]"\tAfter opening the GUI start the ipython console and execute a line given in "".
\t-ipr script.py\tSame as '-ipy "run -i script.py"'
\t\t\tThis option can be given multiple times to define a sequence of lines to be executed.
\t\t\tI would recomand writing a script and just adding the option '-ipy "run -i script.py"'.
\t-no-trans\tdon't make a unit transformation

\tAdvanced settings:
\t-ipdrop \tRead data and drop to IPython console without running the GUI
\t-ipmp \tConnect to IPython multiprocessing cluster for e.g. faster fit calculation
\t--nolimit\tDon't limit the amount of memory consumed by the program so there will not be a MemoryError 
\t\t\t(be carefull, can lead to a non responsive system from operations causing to high memory usage)
\t--debug\t\tDon't redirect the output to any GUI windows but show it on the command line, writes additional 
\t\t\tinformation to a log file.
\t--logmodules\t\tIn debug mode also logg all modules listed after this options (so the options should be 
\t\t\at the end of the input line

"""%(__version__, __email__)

  # TODO: implement these settings
#  '''   
#
#  \t-l\t\tList sequences in file.
#  \t-ls\t\tList selected Sequences.
#
#  \t-o\t\tOutput the data to .out files for later use in other programms.
#  \t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
#  \t-c\t\tJust convert files, do not plot anything
#  \t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
#  \t-p\t\tSend plots to printer specified in gnuplot_perferences.py
#  
#  \t-gui [tk]\tSet the gui toolkit to tk (gtk/wx)
#  '''

  LONG_HELP_END=\
"""
The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
"""
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_data={} #: dictionary for the data objects indexed by filename
  multiplots=None
  active_file_data=None # pointer for the data of the current file
  active_file_name='' # the name of the current file
  index=0
  FILE_WILDCARDS=[('All', '*')] # wildcards for the file open dialog of the GUI
  # known command line options list
  COMMANDLINE_OPTIONS=['s', 's2', 'i', 'gs', 'rd', 'no-mds', 'o', 'ni', 'c', 'sc', 'st', 'sxy', 'e', 'logx', 'logy', 'logz', 'scp',
                        'template', 'no-trans', '-help', '-debug', '-nolimit', 'startuppath', 'mpl',
                        'ipy', 'ipr', 'ipdrop', 'ipmp']
  # options:
  use_gui=True # activate graphical user interface
  seq=[1, 10000] # use sequences from 1 to 10 000
  seq_inc=1 # use every sequence
  single_picture=False # plot all sequences in one picture
  list_all=False # show a list of sequences found in the file
  list_sequences=False # show a list of sequences found in the file which are selected for plotting
  gnuplot_script=True # use script mode
  do_output=False # export .out files
  info_in_file=True # write header in output files
  plot_data=True # plot the data (otherwise only convert files)
  plot_with_errorbars=False # use errorbars in plot
  logx=False # plot logarithmic in x direction
  logy=False # plot logarithmic in y direction
  logz=False # plot logarithmic in z direction
  picture_width='1600'
  picture_height='1200'
  font_size=24.
  # TODO: command line file printing hast to be added.
  print_plot=False # send plots to printer
  unit_transformation=True # make transformations as set in preferences file
  TRANSFORMATIONS=[] # a list of unit TRANSFORMATIONS, that will be performed on the data
  read_directly=False # don't use pickled file, read the data diretly
  mds_create=True
  ONLY_IMPORT_MULTIFILE=False
  DEBUG=False
  ipdrop=False
  file_actions_addon={}
  ipython_commands=[]
  plugins=[]
  #------------------ local variables -----------------

  def __init__(self, arguments):
    '''
      Class constructor which is called with the command line arguments.
      Evaluates the command line arguments, creates a file list and
      starts the data readout procedure.
      
      :param arguments: The command line arguments passed to the constructor.
    '''
    # The object can be initialized without data by using None as arguments.
    if type(arguments) is list:
      #++++++++++++++++ evaluate command line +++++++++++++++++++++++
      files=self.read_arguments(arguments) # get filenames and set options
      if files is None: # read_arguments returns none, if help option is set
        print self.LONG_HELP+self.SPECIFIC_HELP+self.LONG_HELP_END
        sys.exit()
      elif len(files)<1 and not self.use_gui and not self.ipdrop: # show help, if there is no file in the list
        print self.SHORT_HELP
        sys.exit()
    else:
      files=[]
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    self.os_path_stuff() # create temp folder according to OS
    self.try_import_externals()
    if 'plot' in user_config and 'font-size' in user_config['plot']:
      self.font_size=user_config['plot']['font-size']
    self.import_plugins() # search the plugin folder for modules
    files.sort()
    remove=[]
    transformations.known_transformations+=self.TRANSFORMATIONS
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    for filename in files:
      if self.add_file(filename)==[]:
        # if a file is empty or a reading error occured remove it.
        remove.append(filename)
    for rem in remove:
      files.remove(rem)

    if type(arguments) is list:
      if len(files)==0: # show help, if there is no valid file in the list
        if not self.use_gui and not self.ipdrop:
          print "No valid datafile found!"
          print self.SHORT_HELP
          sys.exit()
        self.active_file_data=[]
        self.active_file_name="None"
      else:
        try:
          self.active_file_data=self.file_data[files[0]]
          self.active_file_name=files[0]
        except KeyError:
          self.active_file_data=self.file_data[files[0].rsplit('.mdd', 1)[0].rsplit('.mds', 1)[0]]
          self.active_file_name=files[0].rsplit('.mdd', 1)[0].rsplit('.mds', 1)[0]

  def initialize_gnuplot(self):
    '''
      Start a gnuplot instance for the main plotting.
    '''
    if measurement_data_plotting.gnuplot_instance is None:
      # if fontconfig is available use it to set GDLibrarayPath
      from plot_script.config import fontconfig
      if fontconfig.font_config is not None:
        font_paths=fontconfig.fc.get_font_folders()
        os.environ['GDLIBRARYPATH']=":".join(font_paths)
        opts=gnuplot_preferences.image_terminal_options['png']
        for i, opt in enumerate(opts):
          if '[font-path]/[font-file]' in opt:
            opts[i]=opt.replace('[font-path]/[font-file]', '[font]')
      program=self.GNUPLOT_COMMAND
      try:
        if gnuplot_preferences.EMMULATE_SHELL:
          # run test instance to catch execution error as with shell execution there is no error
          test=subprocess.Popen([program],
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                      shell=False)
          test.stdin.write('exit\n')
          test.communicate()
        # run the real instance
        measurement_data_plotting.gnuplot_instance=subprocess.Popen([program],
                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                  shell=gnuplot_preferences.EMMULATE_SHELL,
                  creationflags=gnuplot_preferences.PROCESS_FLAGS)
        # try to set encoding once, it is not altered by the reset function
        measurement_data_plotting.gnuplot_instance.stdin.write(#@UndefinedVariable
                  'set encoding '+gnuplot_preferences.ENCODING+'\n')

      except:
        raise RuntimeError, "Problem communicating with Gnuplot, please check your system settings! Gnuplot command used: %s"%program

  def try_import_externals(self):
    '''
      Try to import modules not part of core python.
      Gnuplot.py has no error reporting, so we change some settings
      to make it work.
    '''
    try: # verify mathematic modules needed for fitting
      import numpy #@UnusedImport
      self.ALLOW_FIT=True
    except ImportError:
      print "Numpy is not installed, fitting will not be possible."
      self.ALLOW_FIT=False

  def read_arguments(self, arguments):
    '''
      Function to evaluate the command line arguments.
      Returns a list of filenames.
      
      :param arguments: The command line arguments to evaluate.
      :return: A list of file names to import.
    '''
    input_file_names=[]
    last_argument_option=[False, '']
    for argument in arguments: # iterate through all options
      if (argument[0]=='-')|last_argument_option[0]:
          # Cases of arguments:
        if last_argument_option[0]:
          if last_argument_option[1]=='s':
            self.seq=[int(argument), self.seq[1]]
            last_argument_option=[True, 's2']
          elif last_argument_option[1]=='s2':
            self.seq=[self.seq[0], int(argument)]
            last_argument_option=[False, '']
          elif last_argument_option[1]=='i':
            self.seq_inc=int(argument)
            last_argument_option=[False, '']
          elif last_argument_option[1]=='template':
            import templates
            #self.user_template=argument
            print "Using template %s."%argument
            if argument.endswith('.py'):
              template_file=argument
            else:
              template_file=os.path.join(template_config.TEMPLATE_DIRECTORY, argument+'.py') #@UndefinedVariable
            template=templates.DataImportTemplate(template_file)
            self.read_file=template
            self.FILE_WILDCARDS=[[template.name]+template.wildcards]
            # reset the addfile function to the standard
            self.ONLY_IMPORT_MULTIFILE=False
            self.add_file=lambda*args, **opts: GenericSession.add_file(self, *args, **opts)
            last_argument_option=[False, '']
          elif last_argument_option[1]=='startuppath':
            os.chdir(os.path.abspath(argument))
            last_argument_option=[False, '']
          elif last_argument_option[1]=='ipy':
            self.ipython_commands.append(argument)
            last_argument_option=[False, '']
          elif last_argument_option[1]=='ipr':
            self.ipython_commands.append("run -i %s"%argument)
            last_argument_option=[False, '']
          else:
            found_add, last_argument_option=self.read_argument_add(argument, last_argument_option, input_file_names)
            if not found_add:
              input_file_names.append(argument)
              last_argument_option=[False, '']
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
        elif argument in ['-scp', '-ipdrop']:
          self.use_gui=False
          if argument=='-ipdrop':
            self.ipdrop=True
        elif argument=='-ipmp':
          parallel.connect()
        elif argument=='-no-trans':
          self.unit_transformation=False
        elif argument=='--help':
          return None
        elif argument=='--debug':
          self.DEBUG=True
        else:
          # evaluate child arguments
          found_add, last_argument_option=self.read_argument_add(argument, last_argument_option, input_file_names)
          if not found_add:
            if argument[1:len(argument)] in self.COMMANDLINE_OPTIONS:
              last_argument_option=[True, argument[1:len(argument)]]
            else:
              print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
      else:
        input_file_names.append(argument)
    return input_file_names

  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      Dummi function for child classes, which makes it possible to
      add command line options for them.
      
      :return: A Squence depending on the found parameters.
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
    if "library.zip" in SCRIPT_PATH:
      # py2exe puts all modules into a zipfile, so we get the own folder from sys.argv
      SCRIPT_PATH=SCRIPT_PATH.split('library.zip')[0]
    if os.path.isfile(SCRIPT_PATH):
      # for cxFreeze remove the script name from the path
      SCRIPT_PATH=os.path.split(SCRIPT_PATH)[0]
    self.GNUPLOT_COMMAND=gnuplot_preferences.GNUPLOT_COMMAND
    gnuplot_preferences.FONT_PATH=gnuplot_preferences.FONT_PATH.replace('[script-path]',
                                                                        SCRIPT_PATH)
    if 'linux' in sys.platform:
      # Linux case
      self.OPERATING_SYSTEM='linux'
      self.TEMP_DIR="/tmp/"
      self.SCRIPT_PATH=SCRIPT_PATH+'/'
      # name of the gnuplot command under linux
    elif 'darwin' in sys.platform:
      # MacOS case
      self.OPERATING_SYSTEM='darwin'
      self.TEMP_DIR="/tmp/"
      self.SCRIPT_PATH=SCRIPT_PATH+'/'
      # name of the gnuplot command under linux
    else:
      # Windows case
      self.OPERATING_SYSTEM='windows'
      self.TEMP_DIR=os.getenv("TEMP")+'\\'
      self.SCRIPT_PATH=SCRIPT_PATH+'\\'
      self.gnuplot_scripts=True
      def replace_systemdependent(string): # replace backthlash by double backthlash for gnuplot under windows
        return string.replace('\\', '\\\\').replace('\\\\\n', '\\\n').replace('\\\\\\\\', '\\\\')
      self.replace_systemdependent=replace_systemdependent
      try:
        # if win32process module is installed Popen can be called withouth shell emmulation
        import win32process
        gnuplot_preferences.PROCESS_FLAGS=win32process.CREATE_NO_WINDOW
      except ImportError:
        gnuplot_preferences.EMMULATE_SHELL=True
    self.TEMP_DIR=self.TEMP_DIR+'plottingscript-'+self.OWN_PID+os.sep
    measurement_data_structure.TEMP_DIR=self.TEMP_DIR
    try:
      os.mkdir(self.TEMP_DIR) # create the temporal directory
    except OSError:
      print "Warning: Temporary directory already exists!"

  def os_cleanup(self):
    '''
      Delete temporal files and folder.
    '''
    # close gnuplot
    try:
      measurement_data_plotting.gnuplot_instance.stdin.write('exit') #@UndefinedVariable
      measurement_data_plotting.gnuplot_instance.communicate() #@UndefinedVariable
    except:
      pass
    # remove temp files
    for file_name in os.listdir(self.TEMP_DIR):
      os.remove(self.TEMP_DIR+file_name)
    os.rmdir(self.TEMP_DIR)

  def import_plugins(self):
    '''
      Import plugins from the users plugin directory.
    '''
    from plot_script.plugins import all_plugins
    self.plugins=all_plugins

  def replace_systemdependent(self, string):
    '''
      Function for path name replacements. Only under windows,
      in linux this is just a dummi method returning the same
      string.
      
      :return: The replaced string.
    '''
    return string

  def read_file(self, filename):
    '''
      Function which reads one datafile and returns a list
      of measurement_data_structure objects splitted into
      sequences. Every child class will overwrite this.
      
      :return: A list of datasets that has been found.
    '''
    data_list=[]
    dataset=None
    if os.path.exists(filename): # Test if the file exists
      input_file_lines=open(filename, 'r').readlines()
      # iterate through all lines and split the columns.
      for line in input_file_lines:
        if line[0]=='#': # ignore comment lines
          continue
        if (dataset==None and len(line.split())>=2):
          columns=[('col-'+str(number), '') for number in range(len(line.split()))]
          dataset=measurement_data_structure.MeasurementData(columns, [], 0, 1, 2)
          try: # only import numbers
            dataset.append([float(number) for number in line.split()])
          except ValueError:
            print 'Unknown data type in file '+filename+'. Skipped!'
            return []
          dataset.info=filename+'-'+str(len(data_list)+1)
        else:
          if  len(line.split())<2: # empty line is treated as sequence splitting
            if dataset!=None:
              data_list.append(dataset)
            dataset=None
            continue
          try:
            dataset.append([float(number) for number in line.split()])
          except ValueError:
            print 'Unknown data type in file "'+filename+'". Skipped!'
            return []
      if not dataset is None:
        data_list.append(dataset)
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
      
      :return: The filtered list with the numbers set.
    '''
    filtered_datasets=[]
    for i, dataset in enumerate(datasets):
      j=i+1
      # only use sequences inside the boundaries and with the right increment
      if (j>=self.seq[0]) and (j<=self.seq[1]) and (((j-self.seq[0])%self.seq_inc)==0):
        filtered_datasets.append(dataset)
        # set number string depending on the length of the last number
        dataset.number='000000'.replace('0', '', 6-len(str(len(datasets)+1))+len(str(i+1)))+str(i+1)
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
    if len(data_list)>0:
      self.file_data[name]=data_list

  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      Transformations are also done here, so childs
      will change this function.
      
      :return: A list of datasets that have been found in the file.
    '''
    # for faster access the MeasurementData objects are saved via cPickle
    # when this file exists it is used to reload it.
    # This can be ignored by the command line option '-rd'
    # if the script is newer than the .mds file, reimport it
    own_path=os.path.abspath(__file__)
    if 'library.zip' in own_path:
      own_path=own_path.split('library.zip')[0]+'library.zip'
    if filename.endswith('.mds.gz') or filename.endswith('.mds') or \
      filename.endswith('.mdd.gz') or filename.endswith('.mdd'):
      # import binary files from this program
      ds_name=filename.rsplit('.mds', 1)[0].rsplit('.mdd', 1)[0]
      self.active_file_name=ds_name
      loaded_multiplot=self.reload_snapshot(filename)
      if not loaded_multiplot:
        return self.active_file_data
      else:
        return []
    if filename.endswith('.gz'):
      zip_mds=True
      mds_name=filename.rsplit('.', 1)[0]+'.mds.gz'
    else:
      zip_mds=False
      mds_name=filename+'.mds'
    # only use mds file if it is newer than the original data and this script
    if os.path.exists(mds_name) and not self.read_directly and \
        (os.path.getmtime(own_path)<os.path.getmtime(mds_name)) and \
        (not os.path.exists(filename) or \
        (os.path.getmtime(filename)<os.path.getmtime(mds_name))):
      print "Importing previously saved data from '"+mds_name+"'."
      if zip_mds:
        import gzip
        pickled=gzip.open(mds_name, 'rb')
      else:
        pickled=open(mds_name, 'rb')
      datasets=load(pickled)
      pickled.close()
    else:
      print "Trying to import '"+filename+"'."
      is_generic=False
      for suffix, item in GENERIC_FORMATS.items():
        if filename.endswith(suffix):
          datasets=item[1](filename)
          is_generic=True
          break
      if not is_generic:
        datasets=self.read_file(filename)
      if datasets!=[] and datasets!='NULL' and self.mds_create:
        if zip_mds:
          import gzip #@Reimport
          pickling=gzip.open(mds_name, 'wb')
        else:
          pickling=open(mds_name, 'wb')
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
    if self.logx:
      dataset.logx=True
    if self.logy:
      dataset.logy=True
    if self.logz:
      dataset.logz=True

  def __iter__(self): # see next()
    return self

  def next(self): #@ReservedAssignment
    ''' 
      Function to iterate through the file_data dictionary. Object can be used in "for name in data:".
      Also changes the active_file_data and active_file_name.
    '''
    name_list=[item[0] for item in self.file_data.items()]
    name_list.sort()
    if self.index==len(name_list): # after last stop iteration and go to first again
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
        self.plot(dataset.plot_together, self.active_file_name, dataset.short_info, ['' for ignore in range(len(dataset.plot_together))])
        sleep(0.0001) # Can get into troubles without waiting.
    else:
      self.plot(self.active_file_data, self.active_file_name, '', [dataset.short_info for dataset in self.active_file_data])

  def plot_all(self):
    '''
      Plot everything selected from all files.
    '''
    for name in self:
      print "Plotting '"+name+"' sequences."
      self.active_file_data=self.file_data[name]
      self.plot_active()

  def plot(self, datasets, file_name_prefix, title, names):
    '''
      Plot one or a list of datasets.
      
      :return: The stderr and stdout of gnuplot.
    '''
    # TODO: Use one plot function for GUI and script mode with less parameters.
    if len(datasets)>1:
      add_info='multi_'
    else:
      add_info=''
    output=measurement_data_plotting.gnuplot_plot_script\
      (self, datasets, file_name_prefix, '.out', title, names, self.plot_with_errorbars, additional_info=add_info)
    return output

  def change_active(self, object_=None, name=None):
    '''
      Change the active data file by object or name.
    '''
    name_list=[item[0] for item in self.file_data.items()]
    name_list.sort()
    if object_ is not None:
      self.active_file_name=object_[0]
      self.active_file_data=object_[1]
      self.index=name_list.index(object_[0])
    elif name!=None:
      try:
        self.active_file_data=self.file_data[name]
        self.active_file_name=name
        self.index=name_list.index(name)
      except KeyError:
        None
    else:
      None

  def store_snapshot(self, name=None, multiplots=False):
    '''
      Create a snapshot of the active measurement to reload it later.
      The method uses cPickle to create a file with the content of
      the active_file_data list and stores it in active_file_name.mdd.
    '''
    dump_obj=self.create_snapshot_obj(multiplots=multiplots)
    dump_str=dumps(dump_obj,-1)
    if not name:
      if len(dump_str)>(1024*1024*10):
        name=self.active_file_name+'.mdd.gz'
      else:
        name=self.active_file_name+'.mdd'
    if name.endswith('.gz'):
      import gzip
      dump_file=gzip.open(name, 'wb')
    else:
      if not (name.endswith('.mdd') or name.endswith('.mds')):
        name+='.mdd'
      dump_file=open(name, 'wb')
    print "Writing snapshot to file %s..."%(os.path.split(name)[1])
    dump_file.write(dump_str)
    dump_file.close()

  def reload_snapshot(self, name=None):
    '''
      Reload a snapshot created with store_snapshot.
    '''
    if not name:
      if os.path.exists(self.active_file_name+'.mdd'):
        name=self.active_file_name+'.mdd'
      elif os.path.exists(self.active_file_name+'.mdd.gz'):
        name=self.active_file_name+'.mdd.gz'
      else:
        name=self.active_file_name
    if name.endswith('.gz'):
      import gzip
      if os.path.exists(name):
        dump_file=gzip.open(name, 'rb')
      else:
        print "No snapshot file found."
        return False
    else:
      if not (name.endswith('.mdd') or name.endswith('.mds')):
        name+='.mdd'
      if os.path.exists(name):
        dump_file=open(name, 'rb')
      else:
        print "No snapshot file found."
        return False
    print "Reading snapshot from file %s..."%name
    dump_obj=load(dump_file)
    dump_file.close()
    return self.extract_snapshot_obj(dump_obj)

  def create_snapshot_obj(self, multiplots=False):
    '''
      Create a python object that should be pickled as snapshot.
      Child classes can overwrite this to save additional parts in the snapshot.
      The main class only stores the active_file_data list.
    '''
    # create new type snapshot including version and supporting info
    # gives the possiblity to add future features to the snapshots
    # while keeping backwards compatibility
    output={
            'version': __version__,
            'session': str(self.__class__),
            'module': str(self.__module__),
            'origin': self.active_file_name,
            'multiplots': multiplots,
            }
    if multiplots:
      output['data']=self.multiplots
      output['origin']='Multiplot'
    else:
      output['data']=self.active_file_data
      output['origin']=self.active_file_name
    return output

  def extract_snapshot_obj(self, dump_obj):
    '''
      Extract a python object that was pickled as snapshot to the associated objects.
      Child classes can overwrite this to load additional parts from the snapshot.
      The main class only loads the active_file_data list.
    '''
    if type(dump_obj) is dict:
      # new type snapshot
      if 'multiplots' in dump_obj and dump_obj['multiplots']:
        self.multiplots=dump_obj['data']
        return True
      else:
        self.file_data[self.active_file_name]=dump_obj['data']
    else:
      # old type snapshot
      self.file_data[self.active_file_name]=dump_obj
    self.active_file_data=self.file_data[self.active_file_name]
    for i, ds in enumerate(self.active_file_data):
      if ds.number=='':
        ds.number="%i"%i
    return False

  def get_active_file_info(self):
    '''
      Return a string with information about the active file.
    '''
    return "Data read from %s.\n"%(self.active_file_name)



#+++++++++++ Additional functions for general usage ++++++++++++++

def read_full_snapshot(name):
    '''
      Extract a python object that was pickled as snapshot to the associated objects.
      For new style snapshots return the data with the associated namd,module and class
      to start a new session, old style snapshots are read into a generic session.
    '''
    if not os.path.exists(name):
      print "No snapshot file found."
      return None
    if name.endswith('.gz'):
      import gzip
      dump_file=gzip.open(name, 'rb')
    else:
      dump_file=open(name, 'rb')
    # prepare plugin folders
    user_folder=os.path.join(os.path.expanduser('~'), '.plotting_gui')
    if not os.path.join(user_folder, 'plugins') in sys.path:
      sys.path.append(os.path.join(user_folder, 'plugins'))
    from plot_script.plugins import global_plugins #@UnusedImport
    print "Reading snapshot from file %s..."%name
    dump_obj=load(dump_file)
    dump_file.close()
    if type(dump_obj) is dict:
      data=dump_obj['data']
      file_name=dump_obj['origin']
      module=dump_obj['module']
      session=dump_obj['session'].split(module+'.')[1]
    else:
      data=dump_obj
      file_name=name.rsplit('.mdd', 1)[0]
      module='sessions.generic'
      session='GenericSession'
    return data, file_name, (module, session)
