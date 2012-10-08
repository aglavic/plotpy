#-*- coding: utf8 -*-
'''
  Function to initialize the program either with command line or GTK+ interface.
  
  The scripts create one session object according
  to the selected type of the data and reads all files specified by the
  user. The session object is then either used for a direct plotting or
  piped to a plotting_gui for later use.
'''

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import sys, os
import warnings

from glob import glob

# will be defined by initialize_gui_toolkit function
gui_main=None

import message
#----------------------- importing modules --------------------------

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
  active_session_class=getattr(__import__('plotpy.sessions.'+measurement_type[0], {}, {},
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

def initialize(argv):
  ''' 
    initialize session and read data files 
  '''
  from sessions import sessions
  from plotpy.fio import reader
  if not '--debug' in argv:
    try:
      import numpy
      # don't write numpy information on errors to stdout
      numpy.seterr(all='ignore')
    except:
      pass
  else:
    # switch of multiprocessing in debug mode
    from plotpy.fio import baseread
    baseread.USE_MP=False
  if (len(argv)==0):
    return None
  elif argv[0] in sessions.keys():
    # type is found in dictionary, using specific session
    if argv[0] in reader.sessions:
      # promote all readers for the selected session
      for sreader in reader.sessions[argv[0]]:
        reader._promote(sreader, 2)
    return sessions[argv[0]](argv[1:])
  else:
    # get session from importing data
    for i, item in enumerate(argv):
      try:
        read_data=reader.open(item)
      except message.PlotpyError:
        continue
      if len(read_data)>0 and read_data[0] is not None and read_data[0].session in sessions.keys():
        session=sessions[read_data[0].session](argv[:i]+argv[i+1:])
        fname=os.path.join(*read_data[0].origin)
        session.file_data[fname]=read_data[0]
        session.active_file_data=read_data[0]
        session.active_file_name=fname
        return session
    return None

def initialize_gui_toolkit():
  '''
    Load GUI modules dependent on the toolkit.
  '''
  global gui_main, status_dialog
  import plotpy.gtkgui.main_window as gui_main #@UnusedImport
  if '--help' not in sys.argv and '--debug' not in sys.argv and len(sys.argv)>1:
    import plotpy.gtkgui.message_dialog as dialogs
    status_dialog=dialogs.connect_stdout_dialog()
  else:
    status_dialog=None
  # keyword dialog for file imports
  from plotpy.gtkgui.fio_dialogs import reader_kwd_callback
  from plotpy.fio import reader
  reader.kwds_callback=reader_kwd_callback

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

def get_types():
  from plotpy.fio import reader
  types=reader.types
  types+=[item+'.gz' for item in types]
  types+=[item.upper() for item in types]
  return types

def get_sessions():
  from plotpy.sessions import sessions
  return sessions.keys()

def run(argv=None):
  '''
    Start the program.
  '''
  if argv is None:
    argv=sys.argv[1:]
  argv=map(lambda arg: unicode(arg, message.in_encoding), argv)
  # interfact to autogenerate bash completion
  if argv[0]=='--types':
    print u" ".join(get_types())
    exit(0)
  if argv[0]=='--sessions':
    print u" ".join(get_sessions())
    exit(0)
  #+++++++++++++ Limit Memory Usage ++++++++++++++
  if not "--nolimit" in sys.argv:
    try:
      import resource
      # Maximum memory usage is GiB, otherwise the program could cause
      # the system to hang dew to excessive swap memory access
      resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    except ImportError:
      pass
  if '--debug' in argv:
    initialize_debug()
  else:
    # ignore python warnings if not in debug mode
    warnings.simplefilter('ignore')
    message.messenger=message.NiceMessenger()
  if not ('-scp' in argv or '-ipdrop' in argv):
    initialize_gui_toolkit()
  active_session=initialize(argv)
  if active_session is None or active_session.use_gui: # start a new gui session
    plotting_session=initialize_gui(active_session, status_dialog)
    gui_main.main_loop(plotting_session)
  else: # in command line mode, just plot the selected data.
    if '-ipdrop' in argv:
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


