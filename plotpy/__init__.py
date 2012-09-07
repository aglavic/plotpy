#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Plot-script package for data plotting and analyzing for different instruments.
  
  The data model is based on the following hirarchy:
  
    =================  ===  ====================================================
    GUI-Interface      <->         session-Object
                                        session.file_data
    gnuplot-Interface  <->  MeasurementData-Object (mds)
                            MeasurementData.data
                            PhysicalProperty-Objects (mds)
    =================  ===  ====================================================
  
    As top level the session-object (which is different for each instrument) handles the
    data readout and storage. The active session object stores the data read from each file in
    a dictionary. The dictionary key is the input file name and the value as a list of 
    MeasurementData object. The MeasurementData object stands for one Measurement/Scan and stores
    plot specific information and the measured data as PhysicalProperty-Objects (derived from numpy.ndarray).
'''
#################################################################################################
#                    Script to plot different measurements with gnuplot                         #
#                  including a graphical user interface and easy andling                        #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                                    please report bugs to                                      #
#                  http://plotpy.sourceforge.net/plotwiki/doku.php?id=bug-reports               #
#                                                                                               #
# Additional Files: plot_generic_data.py - session class, parent for the other sessions         #
#                   mds.py - classes storing the measured data           #
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
import sys, os
import warnings
exit=sys.exit #@ReservedAssignment
from glob import glob
try:
  sys.path.append(os.path.split(__file__)[0])
# in py2exe this creates a NameError, so skip it
except NameError:
  pass

# will be defined by initialize_gui_toolkit function
gui_main=None

#+++++++++++++ Limit Memory Usage ++++++++++++++
if not "--nolimit" in sys.argv:
  try:
    import resource
    # Maximum memory usage is GiB, otherwise the program could cause
    # the system to hang dew to excessive swap memory access
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
  except ImportError:
    pass

#----------------------- importing modules --------------------------

# set default encoding
#try:
  ## this is just a hack as wx can lead to unicode errors
  ## the site.py module removes sys.setdefaultencoding
  ## so we reload it to use the function until we get this fixed
  #reload(sys)
#  sys.setdefaultencoding('utf8')
#except AttributeError:
  #sys.setappdefaultencoding('utf8')

__author__="Artur Glavic"
__credits__=[]
from info import __copyright__, __license__, __version__, __maintainer__, __email__
__status__="Production"

import config, config.gui

known_measurement_types={
                         'squid': ('squid', 'SquidSession', ['dat', 'raw', 'DAT', 'RAW'], []),
                         '4circle': ('circle', 'CircleSession', ['spec'], []),
                         'p09': ('circle', 'CircleSession', ['fio'], []),
                         'refl': ('reflectometer', 'ReflectometerSession', ['UXD', 'uxd', 'xrdml'], []),
                         'treff': ('treff', 'TreffSession', ['___'], []),
                         'maria': ('treff', 'TreffSession', ['___'], ['-maria']),
                         'in12': ('in12', 'IN12Session', ['___'], []),
                         'dns': ('dns', 'DNSSession', ['d_dat'], []),
                         'kws2': ('kws2', 'KWS2Session', ['DAT'], []),
                         'mbe': ('mbe', 'MBESession', ['png', 'log'], []),
                         'sas': ('sas', 'SASSession', ['___'], []),
                         'gisas': ('kws2', 'KWS2Session', ['DAT', 'edf', 'cmb', 'tif', 'bmp'], []),
                         'shg': ('shg', 'SHGSession', ['par'], []),
                         'generic': ('generic', 'GenericSession', ['___'], []),
                         }
'''
  Dictionary for the known measurement types, to create a new measureing type
  it is only needed to create the seesion class and add it to this dictionary.
  
  Although the commandline parameter order is not importent for all other options
  the type has to be set first, as the other parameters are evaluated according to
  the session.
'''

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
    
    :param arguments: The command line arguments to pass to the object
    :param measurement_type: The names of the module and object to import
    
    :return: The class instance for the measurement type
  '''
  # Check for wildcards in input
  new_args=[]
  for item in arguments:
    if '*' in item or '?' in item:
      new_args+=glob(item)
    else:
      new_args.append(item)
  arguments=new_args
  active_session_class=getattr(__import__('sessions.'+measurement_type[0], {}, {},
                                      [measurement_type[1]]), measurement_type[1])
  return active_session_class(arguments)

def import_session_from_module_info(module_info, arguments):
  '''
    Import a session object from two strings containing module name and class. 
    
    :return: The class instance for the measurement type
  '''
  active_session_class=getattr(__import__(module_info[0], {}, {},
                                      [module_info[1]]), module_info[1])
  return active_session_class(arguments)

def initialize(arguments):
  ''' 
    initialize session and read data files 
  '''
  if not '--debug' in sys.argv:
    try:
      import numpy
      # don't write numpy information on errors to stdout
      numpy.seterr(all='ignore')
    except:
      pass
  # parent class
  from sessions.generic import GenericSession, read_full_snapshot
  if (len(arguments)==0):
    # if no input parameter given, print the short help string
    #print GenericSession.SHORT_HELP
    #exit()
    return None
  elif arguments[0] in known_measurement_types:
    # type is found in dictionary, using specific session
    measurement_type=known_measurement_types[arguments[0]]
    active_session=import_session_from_name(arguments[1:]+measurement_type[3], measurement_type)
  elif (arguments[0].endswith('.mdd') or arguments[0].endswith('.mdd.gz')):
    # open a snapshot with automatic session detection:
    data, file_name, module_info=read_full_snapshot(arguments[0])
    active_session=import_session_from_module_info(module_info, arguments[1:])
    print "Starting session type read from snapshot: %s"%module_info[1]
    active_session.file_data[file_name]=data
    active_session.active_file_data=data
    active_session.active_file_name=file_name
  else:
    found_sessiontype=False
    suffixes=map(lambda arg: arg.split('.')[-1], arguments)
    for name, measurement_type in known_measurement_types.items():
      if found_sessiontype:
        break
      for suffix in measurement_type[2]:
        if suffix in suffixes:
          print "Setting session type to "+name+'.'
          active_session=import_session_from_name(arguments+measurement_type[3], measurement_type)
          found_sessiontype=True
          break
    if not found_sessiontype:
      # type is not found, using generic session
      active_session=GenericSession(arguments+measurement_type[3])
  return active_session

def initialize_gui_toolkit():
  '''
    Load GUI modules dependent on the toolkit.
  '''
  if '-gui' in sys.argv:
    idx=sys.argv.index('-gui')
    sys.argv.pop(idx)
    toolkit=sys.argv.pop(idx)
    if toolkit in ['gtk', 'wx']:
      config.gui.toolkit=toolkit
      print "Setting GUI toolkit to %s."%toolkit
  if config.gui.toolkit=='wx':
    sys.argv.append('--debug')
  global gui_main, status_dialog
  gui_main=__import__('plotpy.'+config.gui.toolkit+'gui.main_window' , fromlist=["main_window"])
  if '--help' not in sys.argv and '--debug' not in sys.argv and len(sys.argv)>1:
    dialogs=__import__('plotpy.'+config.gui.toolkit+'gui.message_dialog' , fromlist=["message_dialog"])
    status_dialog=dialogs.connect_stdout_dialog()
  else:
    status_dialog=None

def initialize_gui(session, status_dialog=None):
  '''
    Initialize the gui main window.
      
    :param session: An object derived from sessions.generic.GenericSession
    
    :return: An ApplicationMainWindow instance ( class defined in {toolkit}gui.generic )
  '''
  if not gui_main:
    initialize_gui_toolkit()
  return gui_main.ApplicationMainWindow(session, status_dialog=status_dialog)

def initialize_debug(log_file='debug.log'):
  '''
    Initialize logging and output for debug mode.
  '''
  import debug
  if '--logmodules' in sys.argv:
    # log additional module functions and class methods
    idx=sys.argv.index('--logmodules')
    modules=sys.argv[idx+1:]
    debug.initialize(log_file, level='DEBUG', modules=modules)
    sys.argv=sys.argv[:idx]
  else:
    debug.initialize(log_file, level='DEBUG')

def ipdrop(session):
  '''
    Inizialize some convenience functions and drop to an IPython console.
  '''
  import numpy as np
  try:
    import scipy as sp
  except ImportError:
    sp=None
    print "Scipy not installed"
  import plotting
  import mds

  index_mess=0
  errorbars=False

  autoplot=True
  # convenience functions
  def plot(ds, output_file):
    result=plotting.gnuplot_plotpy(session,
                           [ds],
                           'temp_plot',
                           '.png',
                           ds.short_info,
                           [ds.short_info],
                           errorbars,
                           output_file)
    if result!=('', []):
      print result[0]

  def replot(index=None):
    if index is None:
      index=_user_namespace['index_mess']
    # Plot the selected active file
    ds=session.active_file_data[index]
    _user_namespace['ds']=ds
    _user_namespace['plot_options']=ds.plot_options
    plot(ds, None)
  def select_file(name=None):
    # change the active plotted file
    if name is None:
      print "\n".join(["% 3i: %s"%item for item in enumerate(sorted(session.file_data.keys()))])
      index=int(raw_input('\tSelect new active file: '))
      name=sorted(session.file_data.keys())[index]
    session.active_file_data=session.file_data[name]
    session.active_file_name=name
    _user_namespace['index_mess']=0
    if _user_namespace['autoplot']:
      replot()
  def read_files(glob_pattern):
    # read all files fitting a given glob pattern and plot the last
    file_names=glob(glob_pattern)
    for file_name in file_names:
      session.add_file(file_name)
    select_file(file_names[-1])
  def next(rel=1): #@ReservedAssignment
    # switch to next plot
    _user_namespace['index_mess']=(_user_namespace['index_mess']+rel)%len(session.active_file_data)
    if _user_namespace['autoplot']:
      replot()
    print _user_namespace['index_mess']
  def prev():
    next(-1)
  def logy():
    # set/unset logscale
    session.active_file_data[_user_namespace['index_mess']].logy=\
       not session.active_file_data[_user_namespace['index_mess']].logy
    if _user_namespace['autoplot']:
      replot()
  def dataset():
    # return active dataset
    return session.active_file_data[_user_namespace['index_mess']]
  class plot_gui:
    def rebuild_menus(self):
      pass


  _user_namespace={
                         }
  _user_namespace.update(locals())
  _user_namespace.update({'_user_namespace':_user_namespace})

  session.initialize_gnuplot()
  plotting.check_gnuplot_version(session)
  import IPython
  banner='''
    This is an IPython console with access to Plot.py namespace.
    You can get access on help about objects with "object?".
    Special plot.py functions:
      plot(dataset, output_file) # export a plot to an image file
      replot(index=None) # show a gnuplot interactive plot of the selected dataset
      select_files(name=none) # select a loaded file and plot it, None shows the selectoin
      read_file(file_name) # import a data file
      next(rel=1) # move the selection in the active file
      logy() # set y-scale to log
      dataset() # return the active dataset object
  '''
  if IPython.__version__<'0.11':
    import IPython.Shell #@UnresolvedImport
    shell=IPython.Shell.IPShellEmbed(argv='', banner='', user_ns=_user_namespace)
    if len(session.ipython_commands)>0:
      # exectue commands
      shell.IP.runlines("\n".join(session.ipython_commands))
    shell(header='')
  else:
    from IPython.frontend.terminal.embed import InteractiveShellEmbed
    shell=InteractiveShellEmbed(user_ns=_user_namespace,
                                banner1=banner, display_banner=True)
    shell()


def _run():
  '''
    Start the program.
  '''
  if sys.platform.startswith('win'):
    # fix problems with windows and non ascii file names
    sys.argv=map(lambda arg: unicode(arg.decode('mbcs')), sys.argv)
  if '--debug' in sys.argv:
    initialize_debug()
  else:
    # ignore python warnings if not in debug mode
    warnings.simplefilter('ignore')
  if not ('-scp' in sys.argv or '-ipdrop' in sys.argv):
    initialize_gui_toolkit()
  active_session=initialize(sys.argv[1:])
  if active_session is None or active_session.use_gui: # start a new gui session
    plotting_session=initialize_gui(active_session, status_dialog)
    gui_main.main_loop(plotting_session)
  else: # in command line mode, just plot the selected data.
    if '-ipdrop' in sys.argv:
      ipdrop(active_session)
    else:
      active_session.plot_all()
  # delete temporal files and folders after the program ended
  if active_session is None:
    # if the session is initialized in the gui, use the active gui session for cleanup
    if not plotting_session.destroyed_directly:
      plotting_session.active_session.os_cleanup()
  else:
    active_session.os_cleanup()

if __name__=='__main__':    #code to execute if called from command-line
  _run()
