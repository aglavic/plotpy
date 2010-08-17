'''
  Module that provides a Class for storing view profiles of a plot.
'''

from config import gnuplot_preferences
import config.gui

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#++++++++++++++++++++++++++++++ PlotProfile Class +++++++++++++++++++++++++++++++++++++++#
class PlotProfile:
  '''
    Class for storing a profile of plot options for later use.
  '''
  name='default'
  set_output_terminal_png=''
  set_output_terminal_ps=''
  x_label=''
  y_label=''
  z_label=''
  font_size=26.
  plotting_parameters=''
  plotting_parameters_errorbars=''
  plotting_parameters_3d=''
  settings_3d=''
  settings_3dmap=''
  additional_commands=''

  def __init__(self,name):
    '''
      Class constructor.
    '''
    self.name=name

  def save(self, active_class):
    '''
      Save the active plot settings as a Profile.
    '''
    print 'plot_profile.py: Entry def save config.gui.toolkit = %s'%(config.gui.toolkit)

    self.set_output_terminal_png=gnuplot_preferences.set_output_terminal_png
    self.set_output_terminal_ps=gnuplot_preferences.set_output_terminal_ps
    self.x_label=gnuplot_preferences.x_label
    self.y_label=gnuplot_preferences.y_label
    self.z_label=gnuplot_preferences.z_label
    self.plotting_parameters=gnuplot_preferences.plotting_parameters
    self.plotting_parameters_errorbars=gnuplot_preferences.plotting_parameters_errorbars
    self.plotting_parameters_3d=gnuplot_preferences.plotting_parameters_3d
    self.settings_3d=gnuplot_preferences.settings_3d
    self.settings_3dmap=gnuplot_preferences.settings_3dmap
    self.font_size=active_class.active_session.font_size

  def load(self, active_class):
    '''
      Load a stored plot options profile.
    '''
    active_class.measurement[active_class.index_mess].plot_options = self.additional_commands
    active_class.plot_options_buffer.set_text(self.additional_commands)
    gnuplot_preferences.set_output_terminal_png=self.set_output_terminal_png
    gnuplot_preferences.set_output_terminal_ps=self.set_output_terminal_ps
    gnuplot_preferences.x_label=self.x_label
    gnuplot_preferences.y_label=self.y_label
    gnuplot_preferences.z_label=self.z_label
    gnuplot_preferences.plotting_parameters=self.plotting_parameters
    gnuplot_preferences.plotting_parameters_errorbars=self.plotting_parameters_errorbars
    gnuplot_preferences.plotting_parameters_3d=self.plotting_parameters_3d
    gnuplot_preferences.settings_3d=self.settings_3d
    gnuplot_preferences.settings_3dmap=self.settings_3dmap
    active_class.active_session.font_size=self.font_size
    active_class.font_size.set_text(str(self.font_size))
    active_class.replot() # plot with new settings

  def prnt(self):
    '''
      Show the profile settings.
    '''
    print self.name,self.set_output_terminal_png,self.set_output_terminal_ps,\
      self.x_label,self.y_label,self.z_label,self.plotting_parameters, \
      self.plotting_parameters_errorbars,self.plotting_parameters_3d,self.additional_commands

  def write(self,config_object):
    '''
      Export the profile settings to a dictionary which is needed
      to store it with the ConfigObj.
    '''
    print 'plot_profile.py: Entry write'
    config_object[self.name]={}
    config=config_object[self.name]
    config['set_output_terminal_png']=self.set_output_terminal_png
    config['set_output_terminal_ps']=self.set_output_terminal_ps
    config['x_label']=self.x_label
    config['y_label']=self.y_label
    config['z_label']=self.z_label
    config['plotting_parameters']=self.plotting_parameters
    config['plotting_parameters_errorbars']=self.plotting_parameters_errorbars
    config['plotting_parameters_3d']=self.plotting_parameters_3d
    config['additional_commands']=self.additional_commands
    config['settings_3d']=self.settings_3d
    config['settings_3dmap']=self.settings_3dmap
    config['font_size']=self.font_size
    print 'plot_profile.py: Return from write'

  def read(self,config_object):
    '''
      Read a profile from a dictionary, see write.
    '''
    print 'plot_profile.py: Entry read'
    config=config_object[self.name]
    self.set_output_terminal_png=config['set_output_terminal_png']
    self.set_output_terminal_ps=config['set_output_terminal_ps']
    self.x_label=config['x_label']
    self.y_label=config['y_label']
    self.z_label=config['z_label']
    self.plotting_parameters=config['plotting_parameters']
    self.plotting_parameters_errorbars=config['plotting_parameters_errorbars']
    self.plotting_parameters_3d=config['plotting_parameters_3d']
    self.additional_commands=config['additional_commands']
    self.settings_3d=config['settings_3d']
    self.settings_3dmap=config['settings_3dmap']
    self.additional_commands=config['additional_commands']
    self.font_size=float(config['font_size'])




#------------------------------ PlotProfile Class ---------------------------------------#


class RedirectOutput:
  '''
    Class to redirect all print statements to the statusbar when useing the GUI.
  '''
  
  def __init__(self, plotting_session):
    '''
      Class constructor.
      
      @param plotting_session A session object derived from GenericSession.
    '''
    print 'generic.py: class RedirectOutput: __init__'

  def write(self, string):
    '''
      Add content.
      
      @param string Output string of stdout
    '''
    print 'generic.py: class RedirectOutput: write'
  
  def flush(self):
    '''
      Show last content line in statusbar.
    '''
    print 'generic.py: class RedirectOutput: flush'
  
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
    print 'generic.py: class RedirectError: __init__'

  
  def write(self, string):
    '''
      Add content and show the dialog.
      
      @param string Output string of stderr
    '''
    print 'generic.py: class RedirectError: write'
  
  def response(self, dialog, response_id):
    '''
      Hide the dialog on response and export debug information if response was OK.
      
      @param dialog The message dialog
      @param response_id The dialog response ID
    '''
    print 'generic.py: class RedirectError: response'
