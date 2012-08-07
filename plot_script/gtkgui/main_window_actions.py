# -*- encoding: utf-8 -*-
'''
  Main window action class for all sessions.
'''

import gtk
import os
import sys
import subprocess
import numpy
from copy import deepcopy
from time import time

import file_actions
from dialogs import PreviewDialog, PlotTree, PrintDatasetDialog, NotebookDialog
from plot_script import measurement_data_plotting, config
from plot_script.config import user_config
from plot_script.config.gui import DOWNLOAD_PAGE_URL
from plot_script.configobj import ConfigObj
import main_window_plotting as mwp
from main_window_file import MainFile
from main_window_data_treatment import MainData
from main_window_plotting import MainPlotting
from main_window_mouse import MainMouse

__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"


class MainActions(MainFile, MainData, MainPlotting, MainMouse):
  '''
    Combined actions used in the main window.
  '''

  def activate_about(self, action):
    '''
      Show the about dialog.
    '''
    dialog=gtk.AboutDialog()
    try:
      dialog.set_program_name("Plotting GUI")
    except AttributeError:
      pass
    dialog.set_version("v%s"%__version__)
    dialog.set_authors([__author__]+__credits__)

    gp=self.gnuplot_info
    pyversion="%i.%i.%i"%(sys.version_info[0],
                          sys.version_info[1],
                          sys.version_info[2])
    try:
      import IPython
      ipversion=IPython.__version__
    except ImportError:
      ipversion="not installed"
    npversion=numpy.version.short_version
    try:
      import scipy
      spversion="version %s"%scipy.version.short_version
    except ImportError:
      spversion="not installed"
    dialog.set_comments(
                        '''
Python interpreter version %s
IPython %s
Numpy version %s
Scipy %s

Gnuplot version %.1f patchlevel %i with terminals:
%s
                        '''%(
        pyversion,
        ipversion,
        npversion,
        spversion,
        gp['version'], gp['patch'], "/".join(gp['terminals']),
                        ))

    dialog.set_copyright("© Copyright 2008-2012 Artur Glavic\n artur.glavic@gmail.com")
    if os.path.exists(os.path.join(self.active_session.SCRIPT_PATH, 'gpl.txt')):
      dialog.set_license(open(
                os.path.join(self.active_session.SCRIPT_PATH, 'gpl.txt'),
                              'r').read())
    else:
      dialog.set_license('''                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007
                       
      The license can be found in the program directory as gpl.pdf''')
    dialog.set_website("http://sourceforge.net/projects/plotpy/index.html")
    dialog.set_website_label('Webseite @ SorceForge')
    ## Close dialog on user response
    dialog.connect ("response", lambda d, r: d.destroy())
    dialog.show()

  def show_config_path(self, action):
    '''
      Show a dialog with the path to the config files.
    '''
    dialog=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE,
                message_format='The configuration files can be found at: \n%s'%
                                                            config.__path__[0]) #@UndefinedVariable
    dialog.run()
    dialog.destroy()

  def iterate_through_measurements(self, action):
    ''' 
      Change the active plot with arrows in toolbar.
    '''
    action_name=action.get_name()
    # change number for active plot put it in the plot page entry box at the bottom
    self.file_actions.activate_action('iterate_through_measurements', action_name)
    # close all open dialogs
    for window in self.open_windows:
      window.destroy()
    # recreate the menus, if the columns for this dataset aren't the same
    self.rebuild_menus()
    self.reset_statusbar()
    # plot the data
    self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)

  def show_plot_tree(self, action=None):
    '''
      Show the plot tree window.
    '''
    if self.plot_tree is None:
      # Create a window for plot preview and selection
      self.plot_tree=PlotTree(self.active_session.file_data, self.update_tree,
                              expand=self.active_session.active_file_name, parent=self)
      self.plot_tree.set_title('Plotting - Imported Datasets')
      self.plot_tree.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
      self.plot_tree.connect('configure_event', self.plot_tree_configure)
      self.plot_tree.connect('delete_event', self.plot_tree_on_delete)
      self.plot_tree.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
      self.plot_tree.set_default_size(*self.config_object['plot_tree']['size'])
      self.plot_tree.move(*self.config_object['plot_tree']['position'])
      self.config_object['plot_tree']['shown']=True
      self.plot_tree.set_icon_from_file(os.path.join(
                              os.path.split(
                             os.path.realpath(__file__))[0],
                             "..", "config", "logoblue.png").replace('library.zip', ''))
      self.plot_tree.show_all()
    else:
      self.plot_tree.destroy()
      self.plot_tree=None
      self.config_object['plot_tree']['shown']=False

  def remove_active_plot(self, action):
    '''
      Remove the active plot from this session.
    '''
    if len(self.measurement)>1:
      self.garbage.append(self.measurement.pop(self.index_mess))
      self.file_actions.activate_action('iterate_through_measurements', 'Prev')
      self.rebuild_menus()
      self.replot()
      print "Plot removed."

  def change_session(self, action=None, transfere=None):
    '''
      Change the session type used to import Data.
      
      :param transfere: A dictionary of measurements to be trasfered to the new session
    '''
    session_dialog=gtk.Dialog(title='Select Session Type...', buttons=('OK', 1, 'Cancel', 0))
    sessions={
              'SQUID/PPMS': ('squid', 'SquidSession'),
              '4-Circle': ('circle', 'CircleSession'),
              'DNS': ('dns', 'DNSSession'),
              'SAS': ('sas', 'SASSession'),
              'GISAS': ('kws2', 'KWS2Session'),
              'Reflectometer': ('reflectometer', 'ReflectometerSession'),
              'TREFF/MARIA': ('treff', 'TreffSession'),
              'MBE': ('mbe', 'MBESession'),

              }

    table=gtk.Table(1, len(sessions.keys()), False)
    buttons=[]
    for i, name in enumerate(sorted(sessions.keys())):
      if i==0:
        buttons.append(gtk.RadioButton(label=name))
      else:
        buttons.append(gtk.RadioButton(group=buttons[0], label=name))
      table.attach(buttons[i], 0, 1, i, i+1)
    table.show_all()
    session_dialog.vbox.add(table)
    result=session_dialog.run()
    if result==1:
      if self.active_session is not None:
        self.deactivate_plugins()
      for button in buttons:
        if button.get_active():
          name=button.get_label()
          session_dialog.destroy()
          break
      # If session already in suspended sessions, just switch
      for i, session in enumerate(self.suspended_sessions):
        if session.__module__=='sessions.%s'%sessions[name][0]:
          self.suspended_sessions.append(self.active_session)
          self.active_session=self.suspended_sessions.pop(i)
          self.measurement=self.active_session.active_file_data
          self.index_mess=0
          if transfere is not None:
            for name, datasets in transfere.items():
              self.active_session.add_data(datasets, name)
          self.rebuild_menus()
          self.activate_plugins()
          self.replot()
          return True
      new_session_class=getattr(__import__('sessions.'+sessions[name][0], globals(), locals(),
                                      [sessions[name][1]]), sessions[name][1])
      new_session=new_session_class([])
      if self.active_session is not None:
        self.suspended_sessions.append(self.active_session)
        self.active_session=new_session
        if transfere is None:
          self.add_file()
        else:
          # Add transfered data to the session
          for name, datasets in transfere.items():
            self.active_session.add_data(datasets, name)
          file_name=sorted(transfere.keys())[0]
          self.active_session.active_file_data=self.active_session.file_data[file_name]
          self.measurement=self.active_session.file_data[file_name]
          self.index_mess=0
          self.active_session.active_file_name=file_name
          self.rebuild_menus()
          self.replot()
      else:
        self.active_session=new_session
      self.activate_plugins()
      return True
    if result==0:
      session_dialog.destroy()
      return False

  def transfere_datasets(self, action):
    '''
      Open a selection dialog to transfere datasets to another session.
    '''
    selection_dialog=PreviewDialog(self.active_session.file_data, show_previews=True,
                                   buttons=('Transfere', 1, 'Cancel', 0),
                                   title='Select dataset to be transfered...')
    selection_dialog.set_default_size(800, 600)
    selection_dialog.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
    result=selection_dialog.run()
    if result==1:
      transfere=selection_dialog.get_active_dictionary()
      selection_dialog.destroy()
      if transfere=={}:
        return
      self.change_session(transfere=transfere)
      return
    selection_dialog.destroy()

  def change_active_file(self, action):
    '''
      Change the active datafile for plotted sequences.
    '''
    index=int(action.get_name().split('-')[-1])
    measurements=sorted(self.active_session.file_data.items())[index]
    self.change_active_file_object(measurements)

  def show_status_dialog(self, action):
    '''
      Show the dialog which holds the file import informations.
    '''
    if self.status_dialog:
      self.status_dialog.show_all()

  def fit_dialog(self, action, size=None, position=None):
    '''
      A dialog to fit the data with a set of functions.
      
      :param size: Window size (x,y)
      :param position: Window position (x,y)
    '''
    if size is None:
      if 'FitDialog' in self.config_object:
        size=self.config_object['FitDialog']['size']
        position=self.config_object['FitDialog']['position']
      else:
        size=(800, 250)
    if not self.active_session.ALLOW_FIT:
      message_dialog=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE,
                                   message_format="You don't have the system requirenments for Fitting.\nNumpy and Scipy must be installed.")
      message_dialog.run()
      message_dialog.destroy()
      return None
    dataset=self.active_dataset
    if (dataset.fit_object==None):
      self.file_actions.activate_action('create_fit_object')
    fit_session=dataset.fit_object
    fit_dialog=gtk.Dialog(title='Fit...')
    fit_dialog.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logopurple.png").replace('library.zip', ''))
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    align, buttons, progress_bar=fit_session.get_dialog(self, fit_dialog)
    sw.add_with_viewport(align) # add fit dialog
    fit_dialog.vbox.add(sw)
    actions_table=gtk.Table(len(buttons), 2, False)
    for i, button in enumerate(buttons):
      actions_table.attach(button, i, i+1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    actions_table.attach(progress_bar, 0, len(buttons), 1, 2, gtk.FILL|gtk.EXPAND, gtk.FILL, 0, 0)
    #try:
    #  fit_dialog.get_action_area().pack_end(actions_table, expand=False, fill=True, padding=0)
    #except AttributeError:
    fit_dialog.vbox.pack_end(actions_table, expand=False, fill=True, padding=0)
    fit_dialog.set_default_size(*size)
    if position is not None:
      fit_dialog.move(*position)
    fit_dialog.show_all()
    def store_fit_dialog_gemometry(widget, event):
      self.config_object['FitDialog']={
                                       'size': widget.get_size(),
                                       'position': widget.get_position()
                                       }
    fit_dialog.connect('configure-event', store_fit_dialog_gemometry)
    self.open_windows.append(fit_dialog)

  def multi_fit_dialog(self, action, size=(800, 250), position=None):
    '''
      A dialog to fit several data with a set of functions.
      
      :param size: Window size (x,y)
      :param position: Window position (x,y)
    '''
    if not self.active_session.ALLOW_FIT:
      fit_dialog=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE,
                                   message_format="You don't have the system requirenments for Fitting.\nNumpy and Scipy must be installed.")
      #fit_dialog.set_markup()
      fit_dialog.run()
      fit_dialog.destroy()
      return None
    #from fit_data import FitSession
    #multi_fit_object=FitSession(dataset)


  def add_multiplot(self, action):
    '''
      Add or remove the active dataset from multiplot list, 
      which is a list of plotnumbers of the same Type.
    '''
    if not self.active_multiplot:
      if (action.get_name()=='AddAllMultiplot')&(len(self.measurement)<40): # dont autoadd more than 40
        for i in range(len(self.measurement)):
          self.do_add_multiplot(i)
      elif action.get_name()=='ClearMultiplot':
        self.clear_multiplot()
      elif action.get_name()=='NewMultiplot':
        self.multiplot.new_item()
        self.do_add_multiplot(self.index_mess)
      else:
        self.do_add_multiplot(self.index_mess)
    elif action.get_name()=='AddMultiplot':
      self.multiplot.sort_add()

  def toggle_multiplot_copymode(self, action):
    '''
      Toggle between copy and non-copy mode in multiplot.
    '''
    if self.multiplot.items.copy_mode:
      self.multiplot.items.copy_mode=False
      print "New multiplot items will be linked to their originals"
    else:
      self.multiplot.items.copy_mode=True
      print "New multiplot items will independent copies of their originals"

  def print_plot(self, action):
    '''
      Dummy function for systems not supported for printing.
    '''
    msg=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE,
                          message_format="""
    Sorry,
                          
        Printing is only supported for PyGTK >=2.10.""")
    msg.run()
    msg.destroy()

  def unix_lpr_pring(self, action):
    '''
      Print plot with unix commandline tool.
    '''
    errorbars=mwp.errorbars
    dialog=gtk.Dialog('Print with unix command...',
                      buttons=('OK', 1, 'Cancel', 0))
    label=gtk.Label("""
    Sorry,
                          
        Printing is only supported for PyGTK >=2.10.
        You can use a linux commandline tool for plotting.
        %s will be replaced by the filename(s).
        
    Enter the Linux command to print the plots.
    """)
    global PRINT_COMMAND
    entry=gtk.Entry()
    entry.set_text(PRINT_COMMAND)
    dialog.vbox.add(label)
    dialog.vbox.add(entry)
    dialog.show_all()
    entry.connect('activate', lambda*ignore: dialog.response(1))
    result=dialog.run()
    print_command=entry.get_text()
    dialog.destroy()
    if result!=1:
      return
    PRINT_COMMAND=print_command
    if action.get_name()=='Print':
      self.last_plot_text=self.plot(self.active_session,
                                    [self.active_dataset],
                                    self.input_file_name,
                                    self.active_dataset.short_info,
                                    [ds.short_info for ds in self.active_dataset.plot_together],
                                    errorbars,
                                    output_file=self.active_session.TEMP_DIR+'plot_temp.ps',
                                    fit_lorentz=False)
      print 'Printing with: '+(print_command%self.active_session.TEMP_DIR+'plot_temp.ps')
      subprocess.call((print_command%self.active_session.TEMP_DIR+'plot_temp.ps').split())
    elif action.get_name()=='PrintAll':
      dialog=PreviewDialog(self.active_session.file_data, title='Select Plots for Printing...',
                           buttons=('OK', 1, 'Cancel', 0), parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
      dialog.set_default_size(800, 600)
      dialog.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
      result=dialog.run()
      if result==1:
        plot_list=dialog.get_active_objects()
        dialog.destroy()
      else:
        dialog.destroy()
        return
      combined_file=open(self.active_session.TEMP_DIR+'plot_temp.ps', 'w')
      for i, dataset in enumerate(plot_list): # combine all plot files in one print statement
        self.last_plot_text=self.plot(self.active_session,
                                      [dataset],
                                      self.input_file_name,
                                      dataset.short_info,
                                      [ds.short_info for ds in dataset.plot_together],
                                      errorbars,
                                      output_file=self.active_session.TEMP_DIR+'plot_temp_%i.ps'%i,
                                      fit_lorentz=False)
        # combine the documents into one postscript file
        if i>0:
          combined_file.write('false 0 startjob pop\n')
        combined_file.write(open(self.active_session.TEMP_DIR+('plot_temp_%i.ps'%i), 'r').read())

      combined_file.close()
      print 'Printing with: '+print_command%self.active_session.TEMP_DIR+'plot_temp.ps'
      subprocess.call((print_command%self.active_session.TEMP_DIR+'plot_temp.ps').split())

  def print_plot_dialog(self, action):
    '''
      Opens a Print dialog to print the active or a selection of plots.
    '''
    if action.get_name()=='PrintAll':
      dialog=PreviewDialog(self.active_session.file_data, title='Select Plots for Printing...',
                           buttons=('OK', 1, 'Cancel', 0), parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
      dialog.set_default_size(800, 600)
      dialog.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
      result=dialog.run()
      if result==1:
        plot_list=dialog.get_active_objects()
        dialog.destroy()
        PrintDatasetDialog(plot_list, self)
      else:
        dialog.destroy()
    else:
      if self.active_multiplot:
        PrintDatasetDialog(self.multiplot, self, multiplot=True)
      else:
        measurements=[self.active_dataset]
        PrintDatasetDialog(measurements, self)

  # not all gtk platforms support printing, other linux systems can print .ps from commandline
  if gtk.pygtk_version[1]>=10:
    print_plot=print_plot_dialog
  elif 'linux' in sys.platform:
    print_plot=unix_lpr_pring

  def run_action_makro(self, action):
    '''
      Execute a list of actions as a makro.
      The actions are given in a textfield, in the future
      there will be makro recording and saving functions.
    '''
    text=gtk.TextView()
    text.get_buffer().set_text('')
    text.show_all()
    #message=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, 
    #                              message_format=str(self.file_actions.store()))
    message=gtk.Dialog(title='Run Makro...')
    message.vbox.add(text)
    message.add_button('Execute Actions', 1)
    message.add_button('Cancel', 0)
    response=message.run()
    if response==1:
      makro=file_actions.MakroRepr()
      buffer_=text.get_buffer()
      makro_text=buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter())
      makro.from_string(makro_text)
      self.last_makro=makro
      self.file_actions.run_makro(makro)
      self.rebuild_menus()
      self.replot()
    message.destroy()

  def run_last_action_makro(self, action):
    '''
      Reexecute the last makro.
    '''
    if getattr(self, 'last_makro', False):
      self.file_actions.run_makro(self.last_makro)
      self.rebuild_menus()
      self.replot()

  def action_history(self, action):
    '''
      A list of all previous actions, that can be executed as makro actions.
      Will be rewritten as log and makro recording functions.
    '''
    text=gtk.TextView()
    text.get_buffer().set_text(str(self.file_actions.store()))
    text.show_all()
    #message=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, 
    #                              message_format=str(self.file_actions.store()))
    message=gtk.Dialog(title='Action History')
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(text) # add fit dialog
    sw.show_all()
    message.vbox.add(sw)
    message.set_default_size(400, 500)
    message.add_button('OK', 1)
    message.run()
    message.destroy()

  def open_tabdialog(self, action=None):
    dia=NotebookDialog(self, title='Plot.py Notebook')
    dia.set_default_size(600, 400)
    dia.show()

  def open_ipy_console(self, action=None, commands=[], show_greetings=True):
    '''
      This opens a window with an IPython console,
      which has direct access to all important objects.
    '''
    import IPython
    if IPython.__version__<'0.11':
      from ipython_view import IPythonView, MenuWrapper, FitWrapper #@UnusedImport
      import IPython.ipapi as ipapi #@UnusedImport @UnresolvedImport
    else:
      from ipython_view_new import IPythonView, MenuWrapper, FitWrapper #@Reimport
      import IPython.core.ipapi as ipapi #@Reimport
    from plot_script import  measurement_data_structure
    import pango
    try:
      import scipy
    except ImportError:
      scipy=None
    from glob import glob
    from plot_script.fit_data import new_function
    from plot_script.gtkgui.autodialogs import FunctionHandler

    if getattr(self, 'active_ipython', False):
      # if there is already an ipython console, show it and exit
      self.active_ipython.deiconify()
      self.active_ipython.present()
      return

    FONT="Mono 8"
    oldstd=[sys.stdout, sys.stderr]

    ipython_dialog=gtk.Dialog(title="Plotting GUI - IPython Console")
    self.active_ipython=ipython_dialog
    if 'IPython' in self.config_object:
      ipython_dialog.set_default_size(*self.config_object['IPython']['size'])
      ipython_dialog.move(*self.config_object['IPython']['position'])
      if self.config_object['IPython']['size'][0]<700:
        show_greetings=False
    else:
      ipython_dialog.set_default_size(750, 600)
    ipython_dialog.set_resizable(True)
    ipython_dialog.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logoyellow.png").replace('library.zip', ''))
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    greeting="""    This is an interactive IPython session with direct access to the program.
    You have the whole python functionality and can interact with the programs objects.
    You can use tab-completion and inspect any object (get help) by writing "object?".

    Functions:
      replot \tFunction to replot the dataset
      dataset \tGet the active MeasurementData object (see attributes x,y,z,data)
      newxyz/ \tCreate a new plot with changed columns, takes three/several lists or 
        newall\tarrays as input. For line plots the last parameter is 'None'.
      mapdata \tApply a function to all datasets in the active file data (see mapall)
      newfit  \tAdd a function to the fit dialog functions, should be defined as
              \tither f(p,x) of f(p,x,y) for 2d or 3d datasets respectively.
      newmenu \tAdd a menu entry which opens a dialog for parameter entry (see newmenu?)
      makefit \tClass which holds all fittable functions as properties. To fit
              \te.g. a linear regression to the current dataset use:
              \tmakefit.Linear_Regression([0.5, 2]) (-> parameters after fit)
      apihelp \tOpen the api reference manual
    Objects:
      session \tThe active session containing the data objects and settings
              \tAll imported data can be accessed via the session.file_data dictionary
              \tThe data for the selected file is in session.active_file_data
      plot_gui \tThe window object with all window related funcitons
      macros  \tDictionary containing all functions which can be run as 'macros'
      menus   \tAccess all GUI menus as properties of this object.
      action_history \tList of macros activated through the GUI (key, (parameters)).
    Modules:
      np \tNumpy
      sp \tScipy
      mds \tMeasurement_data_strunctur module with PhysicalProperty, MeasurementData
          \tand other data treatment Classes.\n"""
    if show_greetings:
      ipview=IPythonView(greeting)
    else:
      ipview=IPythonView('')
    ipview.modify_font(pango.FontDescription(FONT))
    ipview.set_wrap_mode(gtk.WRAP_CHAR)
    sys.stderr=ipview
    sw.add(ipview)
    ipython_dialog.vbox.add(sw)
    # Change the color scheme to have a black background
    #ipview.modify_base('normal', gtk.gdk.Color('#000'))
    #ipview.modify_text('normal', gtk.gdk.Color('#fff'))
    #ipview.modify_cursor(gtk.gdk.Color('#aaa'), None)
    ipython_dialog.show_all()
    ipython_dialog.connect('configure-event', self.update_ipy_console_size)
    ipython_dialog.connect('destroy', self.closed_ipy_console, oldstd)
    # lets the widget propagate <control>+Key and <alt>+key to this window
    ipview.propagate_key_parent=self
    if IPython.__version__<'0.11':
      ip=ipapi.get()
    else:
      ip=ipview.IP
    ip.magic("colors Linux")
    # create functions for the use with ipython
    def getxyz():
      # returns numpy arrays of x,y and z
      d=self.get_active_dataset()
      x=d.x
      y=d.y
      z=d.z
      # if the dataset has an error value that is not
      # empedded into the PhysicalProperty it is added to the output
      if d._yerror>=0:
        if z is not None:
          z.error=d.data[d._yerror]
        else:
          y.error=d.data[d._yerror]
      return x, y, z
    def getall():
      # returns a list of all columns as nump arrays
      return self.get_active_dataset().data
    def newxyz(x, y, z=None, sample_name=None,):
      # create new plot of changed x,y and z columns
      mds=measurement_data_structure
      d=self.get_active_dataset()
      if not hasattr(x, 'dimension'):
        x=mds.PhysicalProperty(d.x.dimension, d.x.unit, x)
      if not hasattr(y, 'dimension'):
        y=mds.PhysicalProperty(d.y.dimension, d.y.unit, y)
      if z is not None and not hasattr(z, 'dimension'):
        z=mds.PhysicalProperty(d.z.dimension, d.z.unit, z)
      newd=mds.MeasurementData()
      newd.append_column(x)
      newd.append_column(y)
      if z is not None:
        newd.zdata=2
        newd.append_column(z)
      newd.short_info=""
      if sample_name is None:
        newd.sample_name=d.sample_name
      else:
        newd.sample_name=sample_name
      self.measurement.append(newd)
      self.index_mess=len(self.measurement)-1
      newd.number=str(self.index_mess)
      self.replot()
    def newall(new_list):
      # create a new plot from a list of given columns
      mds=measurement_data_structure
      d=self.get_active_dataset()
      for i, col in enumerate(new_list):
        if not hasattr(col, 'dimension'):
          new_list[i]=mds.PhysicalProperty(d.data[i].dimension, d.data[i].unit, col)
      newd=deepcopy(d)
      newd.data=new_list
      newd.short_info+=" processed"
      self.measurement.append(newd)
      self.index_mess=len(self.measurement)-1
      newd.number=str(self.index_mess)
      self.replot()
    def mapdata(function):
      # apply a given function to all datasets of the active file
      output=[]
      for dataset in self.measurement:
        output.append(function(dataset))
      return output
    def mapall(function):
      # apply a given function to all datasets of all files
      output={}
      for key, datasets in self.active_session.file_data.items():
        output[key]=[]
        for dataset in datasets:
          output[key].append(function(dataset))
      return output
    def newmenu(function, menu_entry=None, description=None, shortcut=None):
      '''
        Create an entry in the "User-Func." menu which opens a parameter
        dialog and after that calls the function. The dialog is created
        directly from function inspection so the function needs to have
        one of the following two forms:
        
          my_function(dataset, param1=12., param2=23, param3='abc')
          my_function(datasets, d_index, param1=12., param2=23, param3='abc')
          
        Where the naming convention of dataset/datasets/d_index is fixed
        while the parameters can be named as desired. Parameters must be 
        ither int, float, str or list of only one type of these. 
        The docstring of the function can be used to further change the 
        dialog appearance of the parameters by supplieng lines of type:
        
          :param param1: [lower_bound:upper_bound] - param item name - description
          or
          :param param1: param item name - description
          or
          :param param1: description
        
        If this is not supplied the dialog will use the parameter names and leave
        empty descriptions.
        
        The optional arguments to newmenu can define the name of the menu item,
        a descriptive text at the top of the dialog and a keystroke shortcut
        as "<control>U".
      '''
      FunctionHandler.add_function(function, menu_entry, description, shortcut)
      self.rebuild_menus()

    # add variables to ipython namespace
    ipview.updateNamespace({
                       'session': self.active_session,
                       'plot_gui': self,
                       'self': ipview,
                       'dataset': self.get_active_dataset,
                       'replot': self.replot,
                       'getxyz': getxyz,
                       'newxyz': newxyz,
                       'getall': getall,
                       'glob': glob,
                       'newall': newall,
                       'mapdata': mapdata,
                       'mapall': mapall,
                       'np': numpy,
                       'sp': scipy,
                       'mds': measurement_data_structure,
                       'apihelp': apihelp,
                       'macros': self.file_actions.actions,
                       'action_history': self.file_actions.history,
                       'menus': MenuWrapper(self.menu_bar),
                       'newfit': new_function,
                       'makefit': FitWrapper(self, self.active_session),
                       'newmenu': newmenu,
                       })
    # add common mathematic functions to the namespace
    math_functions=['exp', 'log', 'log10', 'pi',
                    'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh',
                    'sqrt', 'abs']
    ipview.updateNamespace(dict([(item, getattr(numpy, item, None)) for item in math_functions]))
    if hasattr(self, 'ipython_user_namespace'):
      # reload namespace of an earlier session
      ipview.updateNamespace(self.ipython_user_namespace)
      ipview.IP.user_ns['In']+=self.ipython_user_history
      if IPython.__version__<'0.11':
        ipview.IP.outputcache.prompt_count=len(self.ipython_user_history)
      if sys.platform.startswith('win'):
        ipview.externalExecute('color_info')
      else:
        ipview.externalExecute('')
    if len(commands)>0:
      while gtk.events_pending():
        gtk.main_iteration(False)
      for command in commands:
      #  ipview.IP.push(command)
        ipview.externalExecute(command)
    self.active_ipview=ipview
    # redefine ls and cat as it doesn't work properly
    if IPython.__version__<'0.11':
      del(ipview.IP.alias_table['ls'])
      if 'cat' in ipview.IP.alias_table:
        del(ipview.IP.alias_table['cat'])
      def _ls_new(self, arg):
        ip=self.api
        if arg=='':
          arg='*'
        ip.ex("from glob import glob; last_ls=glob('%s'); print 'last_ls=',last_ls"%arg)
      def _cat_new(self, arg):
        ip=self.api
        if arg=='':
          ip.ex("print 'No file supplied.'")
        ip.ex("print open('%s','r').read()"%arg)
      ip.expose_magic('ls', _ls_new)
      ip.expose_magic('cat', _cat_new)

  def connect_cluster(self, action):
    '''
      Open a dialog to connect to IPython Cluster.
    '''
    from plot_script import parallel
    if parallel.dview is not None:
      parallel.disconnect()
      return

    parameters=user_config['Parallel']
    parameters=",\n".join(map(lambda item: "%s=%s"%(item[0], repr(item[1])),
                            parameters.items()))
    dialog=gtk.Dialog(title='IPython Cluster Options...',
                      buttons=('OK', 1, 'Cancel', 0))
    param_entry=gtk.TextView()
    text_buffer=param_entry.get_buffer()
    text_buffer.set_text(parameters)
    param_entry.show()
    dialog.vbox.add(param_entry)
    dialog.set_default_size(300, 200)
    result=dialog.run()

    if result:
      buff_text=text_buffer.get_text(text_buffer.get_start_iter(),
                                     text_buffer.get_end_iter())
      parameters=eval('dict('+buff_text+')')
      user_config['Parallel']=parameters
      status_dialog=self.status_dialog
      status_dialog.show()
      sys.stdout.second_output=status_dialog
      connected=parallel.connect()
      sys.stdout.second_output=None
      if connected:
        status_dialog.hide()
    dialog.destroy()

  def edit_user_config(self, action):
    '''
      Open a dialog to edit the user config file.
    '''
    user_config.write()
    dialog=gtk.Dialog(title='Edit User Config...',
                      buttons=('Ok', 1, 'Cancel', 0))
    dialog.set_default_size(400, 600)
    entry=gtk.TextView()
    entry.show()
    buffer_=entry.get_buffer()
    buffer_.set_text(open(user_config.filename, 'r').read())
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(entry)
    sw.show()
    dialog.vbox.add(sw)
    result=dialog.run()
    while result==1:
      text=buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter())
      try:
        tmpfile=os.path.join(self.active_session.TEMP_DIR, 'user_config.ini')
        open(tmpfile, 'w').write(text)
        ConfigObj(tmpfile, unrepr=True)
        open(user_config.filename, 'w').write(text)
        print "User config changed"
        user_config.clear()
        user_config._errors=[]
        user_config._load(tmpfile, user_config._original_configspec)
        break
      except Exception, error:
        print "Error in text, config not saved. %s"%error
        result=dialog.run()
    dialog.destroy()

  #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
  def update_size(self, widget, event):
    '''
      If resize event is triggered the window size variables are changed.
    '''
    geometry=(self.get_position(), self.get_size())
    if geometry!=self.geometry:
      self.geometry=geometry
      self.widthf=self.frame1.get_allocation().width
      self.heightf=self.frame1.get_allocation().height
      # ConfigObj Window parameters
      self.config_object['Window']={
                                    'size': self.geometry[1],
                                    'position': self.geometry[0],
                                    }

  def tab_switched(self, notebook, page, page_num):
    if page_num==1:
      self.multiplot.update_labels()

  #----------------------------Interrupt Events----------------------------------#

  def update_tree(self, key, index):
    '''
      Update the active plot from the treeview.
    '''
    session=self.active_session
    self.change_active_file_object((key, session.file_data[key]), index)
    self.plot_tree.expand_column=key
    self.plot_tree.add_data()
    self.plot_tree.set_focus_item(key, index)
    self.present()

  def plot_tree_on_delete(self, *ignore):
    '''
      Store closed plot tree dialog option.
    '''
    self.config_object['plot_tree']['shown']=False
    self.plot_tree=None

  def plot_tree_configure(self, widget, event):
    '''
      Store plot tree dialog position and size.
    '''
    self.config_object['plot_tree']['size']=widget.get_size()
    self.config_object['plot_tree']['position']=widget.get_position()

  def activate_plugins(self):
    '''
      If a plugin defines an activate function and the active session is in the list
      of sessions the function gets called.
    '''
    session=self.active_session
    activated=False
    for plugin in session.plugins:
      if hasattr(plugin, 'activate') and ('all' in plugin.SESSIONS or session.__class__.__name__ in plugin.SESSIONS):
        plugin.activate(self, session)
        activated=True
    if activated:
      try:
        self.rebuild_menus()
      except:
        pass

  def deactivate_plugins(self):
    '''
      If a plugin defines an activate function and the active session is in the list
      of sessions the function gets called.
    '''
    session=self.active_session
    for plugin in session.plugins:
      if hasattr(plugin, 'deactivate') and ('all' in plugin.SESSIONS or session.__class__.__name__ in plugin.SESSIONS):
        plugin.deactivate(self, session)

  def change_active_file_object(self, measurements, index_mess=0):
    '''
      Change the active file measurements from which the plotted sequences are extracted.
      
      :param measurements: A list of MeasurementData objects from one file
    '''
    self.active_session.change_active(measurements)
    self.measurement=self.active_session.active_file_data
    self.input_file_name=measurements[0]
    # reset index to the first sequence in that file
    self.index_mess=index_mess
    self.active_multiplot=False
    self.plot_page_entry.set_width_chars(len(str(len(self.measurement)))+1)
    self.plot_page_entry.set_text(str('0'))
    for window in self.open_windows:
      window.destroy()
    self.reset_statusbar()
    self.rebuild_menus()
    self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)

  def set_delete_name(self, action):
    '''
      Set self.delete_name from entry object.
    '''
    self.delete_name=action.get_label()

  def get_position_selection(self, action, int_points, position_table):
    '''
      Return selection entries for x,y positions.
    '''
    label=gtk.Label("x-position: ")
    position_table.attach(label,
                # X direction #          # Y direction
                0, 1, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    x_pos=gtk.Entry()
    x_pos.set_width_chars(6)
    position_table.attach(x_pos,
                # X direction #          # Y direction
                1, 2, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    label=gtk.Label(" y-position: ")
    position_table.attach(label,
                # X direction #          # Y direction
                2, 3, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    y_pos=gtk.Entry()
    y_pos.set_width_chars(6)
    position_table.attach(y_pos,
                # X direction #          # Y direction
                3, 4, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    label=gtk.Label(" radius: ")
    position_table.attach(label,
                # X direction #          # Y direction
                4, 5, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    radius=gtk.Entry()
    radius.set_width_chars(6)
    position_table.attach(radius,
                # X direction #          # Y direction
                5, 6, len(int_points), len(int_points)+1,
                0, gtk.FILL,
                0, 0);
    position_table.show_all()
    int_points.append((x_pos, y_pos, radius))

  def get_dataset_selection(self, action, datasets, dataset_table, data_list):
    '''
      Create a selection button for datasets and attach it to the dataset_table widget.
    '''
    dataset=gtk.combo_box_new_text()
    for entry in data_list:
      dataset.append_text("%s[%i] - %s"%(os.path.split(entry[0])[1], entry[1], entry[2]))
    entry=gtk.Entry()
    entry.set_width_chars(12)
    datasets.append((entry, dataset))
    entry.show()
    dataset.show()
    dataset_table.attach(entry,
                # X direction #          # Y direction
                0, 2, len(datasets), len(datasets)+1,
                0, gtk.FILL,
                0, 0);
    dataset_table.attach(dataset,
                # X direction #          # Y direction
                2, 3, len(datasets), len(datasets)+1,
                0, gtk.FILL,
                0, 0);

  def do_multi_fit(self, action, entries, fit_dialog, window):
    '''
      Called when the fit button on a multi fit dialog is pressed.
    '''
    self.open_windows.remove(fit_dialog)
    fit_dialog.destroy()

  def clear_multiplot(self):
      self.multiplot.clear()
      self.active_multiplot=False
      self.replot()
      print "Multiplots cleared."

  def do_add_multiplot(self, index):
    '''
      Add one item to multiplot list devided by plots of the same type.
    '''
    if self.active_multiplot:
      return
    active_data=self.measurement[index]
    if active_data in self.multiplot and not self.multiplot.items.copy_mode:
      self.multiplot.remove(active_data)
      print 'Plot '+active_data.number+' removed.'
    else:
      appended=self.multiplot.append((active_data, self.active_session.active_file_name))
      if appended:
        print 'Plot '+active_data.number+' added.'
      else:
        self.multiplot.new_item()
        self.multiplot.append((active_data, self.active_session.active_file_name))
        print 'New Multiplot created and Plot '+active_data.number+' added.'

  def get_first_in_mp(self):
    '''
      Return the first dataset in an active multiplot.
    '''
    if self.active_multiplot:
      return self.multiplot[0][0]
    else:
      return self.active_dataset

  def reset_statusbar(self):
    '''
      Clear the statusbar.
    '''
    self.statusbar.pop(0)
    self.statusbar.push(0, '')

  def closed_ipy_console(self, widget, oldstd):
    '''
      Unregister the ipython dialog when it gets destroyed.
    '''
    sys.stdout=oldstd[0]
    sys.stderr=oldstd[1]
    self.ipython_user_namespace=dict(
        [(key, value) for key, value in self.active_ipview.IP.user_ns.items() \
              if not (key.startswith('_') or key in ['self', 'In', 'Out'])])
    self.ipython_user_history=self.active_ipview.IP.user_ns['In']
    self.active_ipython=None
    self.active_ipview=None

  def update_ipy_console_size(self, *ignore):
    self.config_object['IPython']={}
    self.config_object['IPython']['size']=self.active_ipython.get_size()
    self.config_object['IPython']['position']=self.active_ipython.get_position()

  def check_for_update_now(self):
    '''
      Read the wiki download area page to see, if there is a new version available.
      
      :return: Newer version number or None
    '''
    import socket
    import urllib
    # Open the wikipage, timeout if server is offline
    socket.setdefaulttimeout(3)
    # Download the update information and run the installation
    try:
      download_page=urllib.urlopen(DOWNLOAD_PAGE_URL)
    except IOError, ertext:
      print 'Error accessing update server: %s'%ertext
      return None
    script_data=download_page.read()
    exec script_data
    if __version__ not in VERSION_HISTORY: #@UndefinedVariable
      version_index=0
    else:
      version_index=VERSION_HISTORY.index(__version__) #@UndefinedVariable
    if self.config_object['Update']['CheckBeta']:
      check_index=VERSION_HISTORY.index(BETA_UPDATE) #@UndefinedVariable
      update_item=BETA_UPDATE #@UndefinedVariable
    else:
      check_index=VERSION_HISTORY.index(NORMAL_UPDATE) #@UndefinedVariable
      update_item=NORMAL_UPDATE #@UndefinedVariable
    if version_index<check_index:
      dialog=gtk.MessageDialog(parent=self, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_OK_CANCEL ,
        message_format="There is a new version (%s) ready to download. Do you want to install it?"%(update_item))
      result=dialog.run()
      dialog.destroy()
      if result==gtk.RESPONSE_OK:
        # run update function defined on the webpage
        perform_update_gtk(__version__, update_item) #@UndefinedVariable
    else:
      print "Softwar is up to date."

  def check_for_updates(self, action=None):
    '''
      Function to check for upates if this was selected and to show a dialog,
      if an updat is possible.
    '''
    if not 'Update' in self.config_object:
      dia=gtk.MessageDialog(parent=self, type=gtk.MESSAGE_QUESTION,
                            message_format='You are starting the GUI the first time, do you want to search for updates automatically?')
      dia.add_button('Yes, only Stable', 1)
      dia.add_button('Yes, all Versions', 2)
      dia.add_button('No', 0)
      result=dia.run()
      if result>0:
        cb=(result==2)
        c=True
      else:
        c, cb=False, False
      self.config_object['Update']={
                                    'Check': c,
                                    'NextCheck': None,
                                    'CheckBeta': cb,
                                    }
      dia.destroy()
    if (self.config_object['Update']['Check'] and time()>self.config_object['Update']['NextCheck']) or action is not None:
      print "Checking for new Version."
      self.config_object['Update']['NextCheck']=time()+24.*60.*60
      self.check_for_update_now()


def apihelp(*ignore):
  '''
    Open the API reference manual in a webbrowser.
    
    :return: Return value of webbrowser.open
  '''
  import webbrowser
  # get the path of the program
  file_path=os.path.split(measurement_data_plotting.__file__)[0].split("library.zip")[0]
  help_file=os.path.join(
                              file_path
                              , 'doc'
                              , 'index.html'
                              )
  return webbrowser.open(help_file)

