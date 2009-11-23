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
import sys
exit=sys.exit
##---add_python_path_here---## # Place holder to add installation directory to python path for non superuser installation.

# own modules
# parent class
from sessions.generic import GenericSession

#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6b4"
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
                         'squid': ('squid', 'SquidSession', ['dat', 'raw', 'DAT', 'RAW']), 
                         '4circle': ('circle', 'CircleSession', ['spec']), 
                         'refl': ('reflectometer', 'ReflectometerSession', ['UXD', 'uxd']), 
                         'treff': ('treff', 'TreffSession', ['___']), 
                         'in12': ('in12', 'IN12Session', ['___']), 
                         'dns': ('dns', 'DNSSession', ['d_dat']), 
                         }

  
class RedirectOutput:
  '''
    Class to redirect all print statements to the statusbar when useing the GUI.
  '''
  
  def __init__(self, plotting_session):
    '''
      Class consturctor.
      
      @param plotting_session A session object derived from GenericSession.
    '''
    self.content = []
    self.plotting_session=plotting_session

  def write(self, string):
    '''
      Add content.
      
      @param string Output string of stdout
    '''
    string=string.replace('\b', '')
    self.content.append(string)
    while '\n' in self.content:
      self.content.remove('\n')
    if (len(string.splitlines())>0) and string.splitlines()[-1]!='':
      self.plotting_session.statusbar.push(0, string.splitlines()[-1])
    if (len(self.content)>0):
      self.plotting_session.statusbar.push(0, self.content[-1])
    while gtk.events_pending():
      gtk.main_iteration(False)
  
  def flush(self):
    '''
      Show last content line in statusbar.
    '''
    if (len(self.content)>0):
      self.plotting_session.statusbar.push(0, self.content[-1])
      while gtk.events_pending():
        gtk.main_iteration(False)
  
  def fileno(self):
    return 1

class RedirectError(RedirectOutput):
  '''
    Class to redirect all error messages to a message dialog when useing the GUI.
    The message dialog has an option to export a bugreport, which includes the active
    measurement to help debugging.
  '''
  
  def __init__(self, plotting_session):
    '''
      Class constructor, as in RedirectOutput and creates the message dialog.
    '''
    RedirectOutput.__init__(self, plotting_session)
    self.messagebox=gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK_CANCEL, message_format='Errorbox')
    self.messagebox.connect('response', self.response)
    self.messagebox.set_title('Unecpected Error!')
  
  def write(self, string):
    '''
      Add content and show the dialog.
      
      @param string Output string of stderr
    '''
    string=string.replace('\b', '')
    self.content.append(string)
    while '\n' in self.content:
      self.content.remove('\n')
    self.messagebox.set_markup('An unexpected error has occured:\n'+'\n'.join(self.content)+\
                              '\n\nDo you want to create a debug logfile?')
    self.messagebox.show_all()
  
  def response(self, dialog, response_id):
    '''
      Hide the dialog on response and export debug information if response was OK.
      
      @param dialog The message dialog
      @param response_id The dialog response ID
    '''
    self.messagebox.hide()
    import time
    from cPickle import dumps
    if response_id==-5:
      debug_log=open('debug.log', 'w')
      debug_log.write('# This is a debug log file created by plot.py\n# The following error(s) have occured at %s.\n' % time.strftime('%D %T', time.localtime()))
      debug_log.write('# The script has been started with the options:\n %s \n' % ' ; '.join(sys.argv))
      debug_log.write('\n# Error Messages: \n\n')
      debug_log.write('\n'.join(self.content))
      debug_log.write('\n\n#-----------------------------start of pickled datasets-----------------------\n')
      debug_log.write(dumps(self.plotting_session.active_session.active_file_data))
      debug_log.write('\n#-----------------------------end of pickled datasets-----------------------\n')
      debug_log.close()
      msg=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, message_format="Log file debug.log has been created.\n\nPlease upload it to the bugreport forum at\n\nhttp://atzes.homeip.net/plotwiki\n\nwith some additional information.\nFor larger files, please use zip or gzip first.")
      msg.run()
      msg.destroy()

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
    
    @param arguments The command line arguments to pass to the object
    @param measurement_type The names of the module and object to import
    
    @return The class instance for the measurement type
  '''
  active_session_class = getattr(__import__('sessions.'+measurement_type[0], globals(), locals(), 
                                      [measurement_type[1]]), measurement_type[1])
  return active_session_class(arguments)


def initialize(arguments):  
  ''' 
    initialize session and read data files 
  '''
  if (len(arguments) == 0):
    # if no input parameter given, print the short help string
    print GenericSession.SHORT_HELP
    exit()
  elif arguments[0] in known_measurement_types:
    # type is found in dictionary, using specific session
    measurement_type=known_measurement_types[arguments[0]]
    active_session=import_session_from_name(arguments[1:], measurement_type)
  else:
    found_sessiontype=False
    suffixes=map(lambda arg: arg.split('.')[-1], arguments)
    for name, measurement_type in known_measurement_types.items():
      if found_sessiontype:
        break
      for suffix in measurement_type[2]:
        if suffix in suffixes:
          print "Setting session type to " + name + '.'
          active_session=import_session_from_name(arguments, measurement_type)
          found_sessiontype=True
          break
    if not found_sessiontype:
      # type is not found, using generic session
      active_session=GenericSession(arguments)
  return active_session

def initialize_gui(session):
  '''
    initialize the gui window and import the needed modules
  '''
  global gtk, plotting_gui
  # GUI module
  import plotting_gui
  import gtk
  return plotting_gui.ApplicationMainWindow(session)

if __name__ == '__main__':    #code to execute if called from command-line
  active_session=initialize(sys.argv[1:])  
  if active_session.use_gui: # start a new gui session
    plotting_session=initialize_gui(active_session)
    if not active_session.DEBUG:
      # redirect script output to session objects
      active_session.stdout=RedirectOutput(plotting_session)
      active_session.stderr=RedirectError(plotting_session)
      sys.stdout=active_session.stdout
      sys.stderr=active_session.stderr  
    gtk.main() # start GTK engine
  else: # in command line mode, just plot the selected data.
    active_session.plot_all()

  # delete temporal files and folders after the program ended
  active_session.os_cleanup()

def test_mpl(arguments):
  '''
    Testing the matplotlib plotting stuff
  '''
  active_session=initialize(arguments)  
  plotting_session=initialize_gui(active_session)
  import gtk
  from matplotlib.figure import Figure
  from numpy import arange, sin, pi
  from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
  from matplotlib.backends.backend_gtk import NavigationToolbar2GTK as NavigationToolbar

  vbox = gtk.VBox()
  plotting_session.frame1.remove(plotting_session.frame1.child)
  plotting_session.frame1.add(vbox)

  fig = Figure(figsize=(5,4), dpi=100)
  ax = fig.add_subplot(111)
  t = arange(0.0,3.0,0.01)
  s = sin(2*pi*t)

  ax.plot(t,s)


  canvas = FigureCanvas(fig)  # a gtk.DrawingArea
  vbox.pack_start(canvas)
  toolbar = NavigationToolbar(canvas, plotting_session)
  vbox.pack_start(toolbar, False, False)


  vbox.show_all()
  return plotting_session, (vbox, fig, ax, canvas, toolbar)
