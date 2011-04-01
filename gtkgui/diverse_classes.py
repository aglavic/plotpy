# -*- encoding: utf-8 -*-
'''
  Additional classes which use GTK functionalities.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
import sys, os

from config import gnuplot_preferences

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.4"
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
  log_xyz=[False, False, False]
  xrange=''
  yrange=''
  zrange=''

  def __init__(self,name):
    '''
      Class constructor.
    '''
    self.name=name

  def save(self, active_class):
    '''
      Save the active plot settings as a Profile.
    '''
    self.additional_commands=\
      active_class.plot_options_buffer.get_text(\
        active_class.plot_options_buffer.get_start_iter(),\
        active_class.plot_options_buffer.get_end_iter())
    try:
      self.log_xyz=[
                  active_class.logx.get_active(), 
                  active_class.logy.get_active(), 
                  active_class.logz.get_active()
                  ]
      self.xrange=active_class.x_range_in.get_text()
      self.yrange=active_class.y_range_in.get_text()
      self.zrange=active_class.z_range_in.get_text()
    except AttributeError:
      self.log_xyz=[False, False, False]
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
    active_class.x_range_in.set_text(self.xrange)
    active_class.y_range_in.set_text(self.yrange)
    active_class.z_range_in.set_text(self.zrange)
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
    active_class.measurement[active_class.index_mess].logx=self.log_xyz[0]
    active_class.measurement[active_class.index_mess].logy=self.log_xyz[1]
    active_class.measurement[active_class.index_mess].logz=self.log_xyz[2]
    active_class.replot() # plot with new settings

  def prnt(self):
    '''
      Show the profile settings.
    '''
    output=''
    for key, value in self.__dict__.items():
      output+=key + ': ' + value.__repr__()
    print output

  def write(self,config_object):
    '''
      Export the profile settings to a dictionary which is needed
      to store it with the ConfigObj.
    '''
    config_object[self.name]=self.__dict__

  def read(self,config_object):
    '''
      Read a profile from a dictionary, see write.
    '''
    self.__dict__=config_object[self.name]



#------------------------------ PlotProfile Class ---------------------------------------#

#++++++++++++++++++++++++++++ Redirection Filelike Objects +++++++++++++++++++++++++++++

class RedirectOutput(object):
  '''
    Class to redirect all print statements to the statusbar when useing the GUI.
  '''
  
  second_output=None

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
    #string=string.replace('\b', '')
    if self.second_output:
      self.second_output.write(string)
    self.content+=string.splitlines()
    while '' in self.content:
      self.content.remove('')
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
  message_pending=False
  
  def __init__(self, plotting_session):
    '''
      Class constructor, as in RedirectOutput and creates the message dialog.
    '''
    RedirectOutput.__init__(self, plotting_session)
    self.messagebox=gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, 
                                      buttons=gtk.BUTTONS_OK_CANCEL,
                                      message_format='Errorbox')
    self.messagebox.connect('response', self.response)
    self.messagebox.set_title('Unecpected Error!')
    # make sure all error messages get reported if the program exits
    import atexit
    atexit.register(self.flush)
  
  def write(self, string):
    '''
      Add content and show the dialog.
      
      @param string Output string of stderr
    '''
    string=string.replace('\b', '')
    self.content.append(string)
    while '\n' in self.content:
      self.content.remove('\n')
    message_text='An unexpected error has occured:\n'
    message_add='\n'.join(self.content)
    # Maximum length is 15 lines and 100 chars per line
    if len(message_add.splitlines())>15:
      message_text+='... '
    message_text+="\n".join(map(lambda line: line[:100], message_add.splitlines()[-15:]))
    message_text+='\n\nDo you want to create a debug logfile?'
    # < signs can cause an gtk.Warning message because they get confused with markup tags
    message_text=message_text.replace('<', '[').replace('>', ']')
    self.messagebox.set_markup(message_text)
    self.messagebox.show_all()
    self.message_pending=True
  
  def flush(self):
    '''
      Make sure the dialog is shown and it is waited for response before the program exits/continues.
    '''
    if self.message_pending:
      self.messagebox.run()

  def response(self, dialog, response_id):
    '''
      Hide the dialog on response and export debug information if response was OK.
      
      @param dialog The message dialog
      @param response_id The dialog response ID
    '''
    self.messagebox.hide()
    self.message_pending=False
    import time
    import gzip 
    from glob import glob
    from cPickle import dumps
    if response_id==-5:
      debug_log=gzip.open('debug.log.gz', 'w')
      debug_log.write('# This is a debug log file created by plot.py\n# The following error(s) have occured at %s.\n' % time.strftime('%m/%d/%y %H:%M:%S', time.localtime()))
      debug_log.write('# The script has been started with the options:\n %s \n' % ' ; '.join(sys.argv))
      debug_log.write('\n# Error Messages: \n\n')
      debug_log.write('\n'.join(self.content))
      debug_log.write('\n\n# Content of the Temporary Folder: \n')
      tempfiles=glob(os.path.join(self.plotting_session.active_session.TEMP_DIR, '*'))
      debug_log.write(' ; '.join(tempfiles))
      debug_log.write('\n\n#-----------------------------start of pickled datasets-----------------------\n')
      try:
        dumpstring=dumps(self.plotting_session.active_session.active_file_data)
      except TypeError:
        try:
          dumpstring=dumps([item for item in self.plotting_session.active_session.active_file_data])
        except TypeError, errorcode:
          dumpstring='Object not Pickable: %s' % errorcode
      debug_log.write(dumpstring)
      debug_log.write('\n#-----------------------------end of pickled datasets-----------------------\n')
      for tempfile in tempfiles:
        debug_log.write('\n#-----------------------------start of tempfile %s------------\n' % tempfile)
        try:
          debug_log.write(open(tempfile, 'r').read())
        except:
          pass
        debug_log.write('\n#-----------------------------end of tempfile %s------------\n' % tempfile)
      debug_log.close()
      msg=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, message_format="Log file debug.log.gz has been created.\n\n"+\
        "Please upload it to the bugreport at\n\nhttp://iffwww.iff.kfa-juelich.de/~glavic/plotwiki\n\nwith some additional information.")
      msg.run()
      msg.destroy()
    else:
      self.content=[]

#---------------------------- Redirection Filelike Objects -----------------------------

class MultiplotList(list):
  '''
    A list of measurements for a multiplot.
  '''
  def __init__(self, input_list):
    self.title="Multiplot"
    self.sample_name=str(input_list[0][0].sample_name)
    list.__init__(self, input_list)
