# -*- encoding: utf-8 -*-
'''
  Main window class for all sessions.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import os, sys
import subprocess
import gobject
import gtk
import numpy
import warnings
from time import sleep, time
from copy import deepcopy
# own modules
# Module to save and load variables from/to config files
from configobj import ConfigObj
from measurement_data_structure import MeasurementData
import measurement_data_plotting
from config.gnuplot_preferences import output_file_name,PRINT_COMMAND,titles
import config
from config import gnuplot_preferences
from config.gui import DOWNLOAD_PAGE_URL
import file_actions
from dialogs import PreviewDialog, StatusDialog, ExportFileChooserDialog, PrintDatasetDialog, \
                    SimpleEntryDialog, DataView, PlotTree,  FileImportDialog
from diverse_classes import MultiplotList, PlotProfile, RedirectError, RedirectOutput

if not sys.platform.startswith('win'):
  WindowsError=RuntimeError
#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika', 
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
__license__ = "GPL v3"
__version__ = "0.7.8"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def main_loop(session):
  '''
    Start the main loop.
  '''
  if getattr(session, 'destroyed_directly', False):
    while gtk.events_pending():
      gtk.main_iteration(False)
  else:
    gtk.main() # start GTK engine
  
 #+++++++++++++++++++++++++ ApplicationMainWindow Class ++++++++++++++++++++++++++++++++++#
# TODO: Move some functions to other modules to have a smaller file
class ApplicationMainWindow(gtk.Window):
  '''
    Main window of the GUI.
    Everything the GUI does is in this Class.
  '''
  status_dialog=None
  init_complete=False
  gnuplot_initialized=False
  destroyed_directly=False
  # used for mouse tracking and interaction on the picture
  mouse_mode=True
  mouse_data_range=[(0., 1., 0., 1.), (0., 1., 0., 1., False, False)]
  mouse_position_callback=None 
  mouse_arrow_starting_point=None
  active_zoom_from=None
  active_zoom_last_inside=None
  active_fit_selection_from=None
  # sub-windows can set a function which gets called on button press
  # with the active position of the mouse on the plot
  garbage=[]
  plot_tree=None
  open_windows=[]
  
  def get_active_dataset(self):
    # convenience method to get the active dataset
    return self.measurement[self.index_mess]

  active_dataset=property(get_active_dataset)
  # stores the geometry of the window an image
  geometry=((0, 0), (800, 600))
  active_plot_geometry=(780, 550)
  
  #+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
  def __init__(self, active_session=None, parent=None, script_suf='', status_dialog=None):
    '''
      Class constructor which builds the main window with it's menus, buttons and the plot area.
      
      @param active_session A session object derived from GenericSession.
      @param parant Parent window.
      @param script_suf Suffix for script file name.
      @param status_dialog The dialog used to show import information.
    '''
    # List of sessions which are suspended after changing to another session.
    self.suspended_sessions=[]
    self.active_session=active_session # session object passed by plot.py
    if active_session is None:
      if self.change_session():
        active_session=self.active_session
      else:
        self.destroyed_directly=True
        return
    if not active_session.DEBUG:
      # redirect script output to session objects
      active_session.stdout=RedirectOutput(self)
      active_session.stderr=RedirectError(self)
      sys.stdout=active_session.stdout
      sys.stderr=active_session.stderr

    global errorbars
    # TODO: remove global errorbars variable and put in session or m_d_structure
    #+++++++++++++++++ set class variables ++++++++++++++++++
    self.status_dialog=status_dialog
    self.heightf=100 # picture frame height
    self.widthf=100 # pricture frame width
    self.set_file_type=output_file_name.rsplit('.',1)[1] # export file type
    self.measurement=active_session.active_file_data # active data file measurements
    self.input_file_name=active_session.active_file_name # name of source data file
    self.script_suf=script_suf # suffix for script mode gnuplot input data
    self.index_mess=0 # which data sequence is plotted at the moment
    self.multiplot=[] # list for sequences combined in multiplot
    self.x_range='set autoscale x'
    self.y_range='set autoscale y'
    self.z_range='set autoscale z\nset autoscale cb'
    self.active_multiplot=False
    self.plot_options_window_open=False # is the dialog window for the plot options active?
    errorbars=False # show errorbars?
    self.file_actions=file_actions.FileActions(self)
    if active_session.gnuplot_script: # define the plotting function depending on script mode flag
      self.plot=self.splot
    else:
      self.plot=measurement_data_plotting.gnuplot_plot
    # list of active winows, that will be closed with this main window
    self.open_windows=[]
    # Create a text view widget. When a text view is created it will
    # create an associated textbuffer by default.
    self.plot_options_view = gtk.TextView()
    # Retrieving a reference to a textbuffer from a textview.
    self.plot_options_buffer = self.plot_options_view.get_buffer()
    self.active_folder=os.path.realpath('.') # For file dialogs to stay in the active directory
    #----------------- set class variables ------------------


    # Create the toplevel window
    gtk.Window.__init__(self)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logo.png").replace('library.zip', ''))
    # Reading config file
    self.read_config_file()
    # When the window gets destroyed, process some cleanup and save the configuration
    self.connect('destroy', lambda *w: self.main_quit())
    # Set the title of the window, will be changed when the active plot changes
    self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))

    #+++++++Build widgets in table structure++++++++
    table = gtk.Table(3, 6, False) # the main table
    self.add(table)

    #++++++++++ Menu and toolbar creation ++++++++++
    '''
      We use the UIManager to create the menus and toolbar. 
      It creates widgets and actions according to the XML string
      created by build_menu() and gtk.ActionGroup created by
      __create_action_group(). See the pygtk documentation
      for more information.
    '''
    ui_info=self.build_menu() # build XML structure of menu and toolbar
    self.UIManager = gtk.UIManager() # construct a new UIManager object
    self.set_data("ui-manager", self.UIManager)
    self.toolbar_action_group=self.__create_action_group() # create action group
    self.UIManager.insert_action_group(self.toolbar_action_group, 0)
    self.add_accel_group(self.UIManager.get_accel_group())
    # don't crash if the menu creation fails
    try:
        self.toolbar_ui_id = self.UIManager.add_ui_from_string(ui_info)
    except gobject.GError, msg:
        raise RuntimeError, "building menus failed: %s" % msg
    self.menu_bar = self.UIManager.get_widget("/MenuBar")
    self.menu_bar.show()

    # put menu at top position, only expand in x direction
    table.attach(self.menu_bar,
        # X direction #          # Y direction
        0, 3,                      0, 1,
        gtk.EXPAND | gtk.FILL,     0,
        0,                         0);
    # put toolbar below menubar, only expand in x direction
    bar = self.UIManager.get_widget("/ToolBar")
    bar.set_tooltips(True)
    bar.set_style(gtk.TOOLBAR_ICONS)
    bar.show()
    table.attach(bar,
        # X direction #       # Y direction
        0, 3,                   1, 2,
        gtk.EXPAND | gtk.FILL,  0,
        0,                      0)
    #---------- Menu and toolbar creation ----------

    #++++++++++ create image region and image for the plot ++++++++++
    # plot title label entries
    # TODO: don't lose entry when not pressing enter
    top_table=gtk.Table(2, 1, False)
    # first entry for sample name part of title
    self.label = gtk.Entry()
    # second entry for additional infor part ofr title
    self.label2 = gtk.Entry()
    self.plot_options_view.show()
    # attach entrys to sub table
    top_table.attach(self.label,
        # X direction           Y direction
        0, 1,                   0, 1,
        gtk.FILL,  gtk.FILL,
        0,                      0)
    top_table.attach(self.label2,
        # X direction           Y direction
        1, 2,                   0, 1,
        gtk.FILL,  gtk.FILL,
        0,                      0)
    align = gtk.Alignment(0.5, 0., 0., 0) # center the entrys
    align.add(top_table)
    # put label below menubar on left column, only expand in x direction
    table.attach(align,
        # X direction           Y direction
        0, 1,                   2, 3,
        gtk.FILL,  gtk.FILL,
        0,                      0)

    # frame region for the image
    self.frame1 = gtk.Notebook()
    align = gtk.Alignment(0.5, 0.5, 1, 1)
    align.add(self.frame1)
    # image object for the plots
    if active_session.USE_MATPLOTLIB:
      self.initialize_matplotlib()
    else:
      self.image=gtk.Image()    
      self.image_shown=False # variable to decrease changes in picture size
      self.image.set_size_request(0, 0)
      self.image_do_resize=False
    # put image in an eventbox to catch e.g. mouse events
    self.event_box=gtk.EventBox()
    self.event_box.add(self.image)
    self.frame1.append_page(self.event_box, gtk.Label("Plot"))
    table.attach(align,
        # X direction           Y direction
        0, 3,                   3, 4,
        gtk.EXPAND | gtk.FILL,  gtk.EXPAND | gtk.FILL,
        0,                      0)
    #---------- create image region and image for the plot ----------

    # Create region for multiplot list
    self.multi_list = gtk.Label();
    self.multi_list.set_markup(' Multiplot List: ')
    align = gtk.Alignment(0, 0.05, 1, 0) # align top
    align.add(self.multi_list)
    # put multiplot list
    self.frame1.append_page(align, gtk.Label("Multiplot List"))
    # Create region for Dataset Info
    self.info_label = gtk.Label();
    self.info_label.set_markup('')
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(self.info_label)
    # put Dataset Info
    self.frame1.append_page(sw, gtk.Label("Dataset Info"))

    #++++++++++ Create additional setting input for the plot ++++++++++
    align_table = gtk.Table(12, 2, False)
    # input for jumping to a data sequence
    page_label=gtk.Label()
    page_label.set_markup('P.:')
    align_table.attach(page_label,0,1,0,1,gtk.FILL,gtk.FILL,0,0)
    self.plot_page_entry=gtk.Entry()
    self.plot_page_entry.set_width_chars(4)
    self.plot_page_entry.set_text('0')
    align_table.attach(self.plot_page_entry,1,2,0,1,gtk.FILL,gtk.FILL,0,0)
    # x,y ranges
    self.x_range_in=gtk.Entry()
    self.x_range_in.set_width_chars(6)
    self.x_range_label=gtk.Label()
    self.x_range_label.set_markup('x-range:')
    self.y_range_in=gtk.Entry()
    self.y_range_in.set_width_chars(6)
    self.y_range_label=gtk.Label()
    self.y_range_label.set_markup('y-range:')
    align_table.attach(self.x_range_label,3,4,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.x_range_in,4,5,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.y_range_label,5,7,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.y_range_in,7,9,0,1,gtk.FILL,gtk.FILL,0,0)
    # font size entry
    self.font_size=gtk.Entry()
    self.font_size.set_width_chars(5)
    self.font_size.set_text(str(self.active_session.font_size))
    self.font_size_label=gtk.Label()
    self.font_size_label.set_markup('F. size:')
    self.font_size_label.set_padding(5, 0)
    align_table.attach(self.font_size,12,13,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.font_size_label,11,12,0,1,gtk.FILL,gtk.FILL,0,0)
    # checkboxes for log x and log y
    self.logx=gtk.CheckButton(label='log x', use_underline=True)
    self.logy=gtk.CheckButton(label='log y', use_underline=True)
    align_table.attach(self.logx,9,10,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.logy,10,11,0,1,gtk.FILL,gtk.FILL,0,0)
    # button to open additional plot options dialog
    self.plot_options_button=gtk.ToolButton(gtk.STOCK_PREFERENCES)
    try:
      self.plot_options_button.set_tooltip_text('Add custom Gnuplot commands')
    except AttributeError:
      # for earlier versions of gtk, this is deprecated in python 2.6
      self.plot_options_button.set_tooltip(gtk.Tooltips(),'Add custom Gnuplot commands')
    align_table.attach(self.plot_options_button,13,14,0,2,gtk.FILL,gtk.FILL,0,0)
    # z range and log z checkbox
    self.z_range_in=gtk.Entry()
    self.z_range_in.set_width_chars(6)
    self.z_range_label=gtk.Label()
    self.z_range_label.set_markup('z-range:')
    self.logz=gtk.CheckButton(label='log z', use_underline=True)
    # 3d Viewpoint buttons to rotate the view
    self.view_left=gtk.ToolButton(gtk.STOCK_GO_BACK)
    self.view_up=gtk.ToolButton(gtk.STOCK_GO_UP)
    self.view_down=gtk.ToolButton(gtk.STOCK_GO_DOWN)
    self.view_right=gtk.ToolButton(gtk.STOCK_GO_FORWARD)
    align_table.attach(self.z_range_label,3,4,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.z_range_in,4,5,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.view_left,5,6,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.view_up,6,7,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.view_down,7,8,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.view_right,8,9,1,2,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.logz,9,10,1,2,gtk.FILL,gtk.FILL,0,0)
    # add all those options
    align = gtk.Alignment(0,0,0,0) # align the table left
    align.add(align_table)
    # put plot settings below Plot
    table.attach(align,
        # X direction           Y direction
        0, 2,                   4, 5,
        gtk.FILL,  gtk.FILL,
        0,                      0)
    #---------- Create additional setting input for the plot ----------

    #+++ Creating entries and options according to the active measurement +++
    if len(self.measurement)>0:
      self.label.set_width_chars(min(len(self.measurement[self.index_mess].sample_name)+5, 
                                                          40)) # title width
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(min(len(self.measurement[self.index_mess].short_info)+5, 
                                                           40)) # title width
      self.label2.set_text(self.measurement[self.index_mess].short_info)
      # TODO: put this to a different location
      self.plot_options_buffer.set_text(str(self.measurement[self.index_mess].plot_options))
      self.logx.set_active(self.measurement[self.index_mess].logx)
      self.logy.set_active(self.measurement[self.index_mess].logy)
      self.logz.set_active(self.measurement[self.index_mess].logz)
    
    #--- Creating entries and options according to the active measurement ---

    # Create statusbar
    self.statusbar = gtk.Statusbar()
    self.statusbar.set_has_resize_grip(True)
    # put statusbar below everything
    table.attach(self.statusbar,
        # X direction           Y direction
        0, 3,                   5, 6,
        gtk.EXPAND | gtk.FILL,  0,
        0,                      0)

    #-------Build widgets in table structure--------

    # show the window settings and catch resize events
    self.x_range_in.hide()
    self.y_range_in.hide()
    self.z_range_in.hide()
    self.x_range_label.hide()
    self.y_range_label.hide()
    self.z_range_label.hide()
    self.logx.hide()
    self.logy.hide()
    self.plot_options_button.hide()
    self.logz.hide()
    self.view_left.hide()
    self.view_up.hide()
    self.view_down.hide()
    self.view_right.hide()

    while len(self.measurement)==0:
      # if there is no measurement loaded, open a file selction dialog
      while gtk.events_pending():
        gtk.main_iteration(False)
      return_status_ok=self.add_file(None, hide_status=False)
      if not return_status_ok:
        self.main_quit(store_config=False)
        self.destroyed_directly=True
        if self.status_dialog:
          bounds=self.status_dialog.buffer.get_bounds()
          sys.__stdout__.write(self.status_dialog.buffer.get_text(*bounds))
          sys.stdout=sys.__stdout__
          self.status_dialog.destroy()
        return
    
    # Display the window
    if self.status_dialog:
      # hide thw status dialog to make it possible to reshow it
      self.status_dialog.hide()

    #+++++++++++++ Show window and connecting events ++++++++++++++
    self.read_window_config()
    self.show_all()
    # resize events
    self.connect("event-after", self.update_picture)
    self.connect("configure-event", self.update_size)
    self.image.connect('size-allocate', self.image_resize)
    # entries
    self.label.connect("activate",self.change) # changed entry triggers change() function 
    self.label2.connect("activate",self.change) # changed entry triggers change() function 
    self.plot_page_entry.connect("activate", self.iterate_through_measurements)
    self.x_range_in.connect("activate",self.change_range)
    self.y_range_in.connect("activate",self.change_range)
    self.font_size.connect("activate",self.change_range)
    self.logx.connect("toggled",self.change)
    self.logy.connect("toggled",self.change)
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)
    self.z_range_in.connect("activate",self.change_range)
    self.logz.connect("toggled",self.change)
    self.view_left.connect("clicked",self.change)
    self.view_up.connect("clicked",self.change)
    self.view_down.connect("clicked",self.change)
    self.view_right.connect("clicked",self.change)
    # mouse and keyboad events
    self.event_box.connect('button-press-event', self.mouse_press)
    self.event_box.connect('button-release-event', self.mouse_release)
    self.connect('motion-notify-event', self.catch_mouse_position)    
    #------------- connecting events --------------
    
    # create the first plot
    try:
      self.active_session.initialize_gnuplot()
    except (RuntimeError, WindowsError), error_message:
      # user can select the gnuplot executable via a file selection dialog
      info_dialog=gtk.Dialog(parent=self, title='Gnuplot Error..', buttons=('Select Gnuplot Executable', 1, 
                                                                            'Exit Program', -1))
      info_dialog.vbox.add(gtk.Label(error_message))
      info_dialog.show_all()
      result=info_dialog.run()
      if result==1:
        info_dialog.destroy()
        file_chooser=gtk.FileChooserDialog(parent=self, title='Select Gnuplot executable...', 
                                      action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                      buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        file_chooser.set_select_multiple(False)
        result=file_chooser.run()
        if result==gtk.RESPONSE_OK:
          self.active_session.GNUPLOT_COMMAND=file_chooser.get_filename()
          file_chooser.destroy()
          self.active_session.initialize_gnuplot()
          message=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, 
            message_format='To make this executable persistent you need to change the GNUPLOT_COMMAND option in %s to %s' % \
              (os.path.join(config.__path__[0], 'gnuplot_preferences.py'), self.active_session.GNUPLOT_COMMAND))
          message.run()
          message.destroy()
        else:
          file_chooser.destroy()
          self.destroy()
      else:
        info_dialog.destroy()
        self.destroy()
        return
    self.replot()
    self.geometry=(self.get_position(), self.get_size())
    self.check_for_updates()
    # open the plot tree dialog
    if self.config_object['plot_tree']['shown']:
      self.show_plot_tree()
    # if plugins are installed activate session specific options
    self.activate_plugins()
    self.init_complete=True
    # execute ipython commands supplied via commandline
    if len(self.active_session.ipython_commands)>0:
      while gtk.events_pending():
        gtk.main_iteration(False)
      self.open_ipy_console(commands=self.active_session.ipython_commands, show_greetings=False)

  #-------------------------------Window Constructor-------------------------------------#

  #++++++++++++++++++++++++++++++++++Event hanling+++++++++++++++++++++++++++++++++++++++#

  #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
  def update_size(self, widget, event):
    '''
      If resize event is triggered the window size variables are changed.
    '''
    geometry= (self.get_position(), self.get_size())
    if geometry!=self.geometry:
      self.geometry=geometry
      self.widthf=self.frame1.get_allocation().width
      self.heightf=self.frame1.get_allocation().height
      # ConfigObj Window parameters
      self.config_object['Window']={
                                    'size': self.geometry[1], 
                                    'position': self.geometry[0], 
                                    }                    

  def update_picture(self, widget, event):
    '''
      After releasing the mouse the picture gets replot.
    '''
    if event.type==gtk.gdk.FOCUS_CHANGE and self.active_plot_geometry!=(self.widthf, self.heightf) and self.init_complete:
      self.replot()

  #----------------------------Interrupt Events----------------------------------#

  #++++++++++++++++++++++++++Menu/Toolbar Events+++++++++++++++++++++++++++++++++#
  def main_quit(self, action=None, store_config=True):
    '''
      When window is closed save the settings in home folder.
      All open dialogs are closed before exit.
    '''
    if store_config:
      if not os.path.exists(os.path.expanduser('~')+'/.plotting_gui'):
        os.mkdir(os.path.expanduser('~')+'/.plotting_gui')
      # ConfigObj config structure for profiles
      self.config_object['profiles']={}
      for name, profile in self.profiles.items():
        profile.write(self.config_object['profiles'])
      del self.config_object['profiles']['default']
      self.config_object['MouseMode']={
                                   'active': self.mouse_mode
                                   }
      self.config_object.write()
    for window in self.open_windows:
      window.destroy()
    if getattr(self, 'active_ipython', False):
      self.active_ipython.destroy()
    try:
      # if the windows is destoryed before the main loop has started.
      self.destroy()
      gtk.main_quit()
    except RuntimeError:
      pass

  def activate_about(self, action):
    '''
      Show the about dialog.
    '''
    dialog = gtk.AboutDialog()
    try:
      dialog.set_program_name("Plotting GUI")
    except AttributeError:
      pass
    dialog.set_version("v%s" % __version__)
    dialog.set_authors([__author__]+__credits__)
    dialog.set_copyright("© Copyright 2008-2011 Artur Glavic\n a.glavic@fz-juelich.de")
    dialog.set_license('''                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007
                       
      The license can be found in the program directory as gpl.pdf''')
    dialog.set_website("http://iffwww.iff.kfa-juelich.de/~glavic/plotwiki")
    dialog.set_website_label('Webseite @ fz-juelich.de')
    ## Close dialog on user response
    dialog.connect ("response", lambda d, r: d.destroy())
    dialog.show()
  
  def show_config_path(self, action):
    '''
      Show a dialog with the path to the config files.
    '''
    import config
    dialog = gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='The configuration files can be found at: \n%s' % config.__path__[0])
    dialog.run()
    dialog.destroy()
      
  def iterate_through_measurements(self, action):
    ''' 
      Change the active plot with arrows in toolbar.
    '''
    action_name=action.get_name()
    # change number for active plot put it in the plot page entry box at the bottom
    self.file_actions.activate_action('iterate_through_measurements', action_name)
    # check for valid number
    if self.index_mess>=len(self.measurement):
      self.index_mess=len(self.measurement)-1
    if self.index_mess<0:
      self.index_mess=0
    # close all open dialogs
    for window in self.open_windows:
      window.destroy()
    self.active_multiplot=False
    # recreate the menus, if the columns for this dataset aren't the same
    self.rebuild_menus()
    self.reset_statusbar()
    # plot the data
    self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)

  def update_tree(self, key, index):
    '''
      Update the active plot from the treeview.
    '''
    session=self.active_session
    self.change_active_file_object( (key, session.file_data[key]), index)
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

  def change(self,action):
    '''
      Change different plot settings triggered by different events.
      
      @param action The action that triggered the event
    '''
    # change the plotted columns
    if action.get_name()=='x-number':
      self.measurement[self.index_mess].xdata=-1
    elif action.get_name()=='y-number':
      self.measurement[self.index_mess].ydata=-1
    elif action.get_name()[0]=='x':
      dim=action.get_name()[2:]
      self.measurement[self.index_mess].xdata=int(dim)
    elif action.get_name()[0]=='y':
      dim=action.get_name()[2:]
      self.measurement[self.index_mess].ydata=int(dim)
    elif action.get_name()[0]=='z':
      dim=action.get_name()[2:]
      self.measurement[self.index_mess].zdata=int(dim)
    elif action.get_name()[0]=='d':
      dim=action.get_name()[3:]
      self.measurement[self.index_mess].yerror=int(dim)
    # change 3d view position
    elif action==self.view_left:
      if self.measurement[self.index_mess].view_z>=10:
        self.measurement[self.index_mess].view_z=self.measurement[self.index_mess].view_z-10
      else:
        self.measurement[self.index_mess].view_z=350
    elif action==self.view_right:
      if self.measurement[self.index_mess].view_z<=340:
        self.measurement[self.index_mess].view_z=self.measurement[self.index_mess].view_z+10
      else:
        self.measurement[self.index_mess].view_z=0
    elif action==self.view_up:
      if self.measurement[self.index_mess].view_x<=160:
        self.measurement[self.index_mess].view_x=self.measurement[self.index_mess].view_x+10
      else:
        self.measurement[self.index_mess].view_x=0
    elif action==self.view_down:
      if self.measurement[self.index_mess].view_x>=10:
        self.measurement[self.index_mess].view_x=self.measurement[self.index_mess].view_x-10
      else:
        self.measurement[self.index_mess].view_x=170
    # change plot title labels
    elif action==self.label or action==self.label2:
      if self.active_multiplot:
        for plotlist in self.multiplot:
          if self.measurement[self.index_mess] in [item[0] for item in plotlist]:
            plotlist.sample_name=self.label.get_text()
            plotlist.title=self.label2.get_text()
      else:
        self.measurement[self.index_mess].sample_name=self.label.get_text()
        self.measurement[self.index_mess].short_info=self.label2.get_text()
    # change log settings
    elif action in (self.logx, self.logy, self.logz):
      logitems=self.measurement[self.index_mess]
      if self.active_multiplot:
        for mp in self.multiplot:
          for mpi, mpname in mp:
            if self.measurement[self.index_mess] is mpi:
              logitems=mp[0][0]
      logitems.logx=self.logx.get_active()
      logitems.logy=self.logy.get_active()
      logitems.logz=self.logz.get_active()
    self.replot() # plot with new Settings

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

  def change_session(self, action=None, transfere=None):
    '''
      Change the session type used to import Data.
      
      @param transfere A dictionary of measurements to be trasfered to the new session
    '''
    session_dialog=gtk.Dialog(title='Select Session Type...', buttons=('OK', 1, 'Cancel', 0))
    sessions={
              'SQUID/PPMS': ('squid', 'SquidSession'), 
              '4-Circle': ('circle', 'CircleSession'), 
              'DNS': ('dns', 'DNSSession'), 
              'GISAS': ('kws2', 'KWS2Session'), 
              'Reflectometer': ('reflectometer', 'ReflectometerSession'), 
              'TREFF/MARIA': ('treff', 'TreffSession'), 
              
              }
        
    table=gtk.Table(1, len(sessions.keys()), False)
    buttons=[]
    for i, name in enumerate(sorted(sessions.keys())):
      if i==0:
        buttons.append(gtk.RadioButton(label=name))
      else:
        buttons.append(gtk.RadioButton(group=buttons[0], label=name))
      table.attach( buttons[i], 0, 1, i, i+1 )
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
        if session.__module__=='sessions.%s' % sessions[name][0]:
          self.suspended_sessions.append(self.active_session)
          self.active_session=self.suspended_sessions.pop(i)
          self.measurement=self.active_session.active_file_data
          self.index_mess=0
          if transfere is not None:
            self.active_session.file_data.update(transfere)
          self.rebuild_menus()
          self.activate_plugins()
          self.replot()
          return True
      new_session_class = getattr(__import__('sessions.'+sessions[name][0], globals(), locals(), 
                                      [sessions[name][1]]), sessions[name][1])
      new_session=new_session_class([])
      if self.active_session is not None:
        self.suspended_sessions.append(self.active_session)
        self.active_session=new_session
        if transfere is None:
          self.add_file()
        else:
          # Add transfered data to the session
          self.active_session.file_data=transfere
          file_name=sorted(transfere.keys())[0]
          self.active_session.active_file_data=transfere[file_name]
          self.measurement=transfere[file_name]
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
    object=sorted(self.active_session.file_data.items())[index]
    self.change_active_file_object(object)
  
  def change_active_file_object(self, object, index_mess=0):
    '''
      Change the active file object from which the plotted sequences are extracted.
      
      @param object A list of MeasurementData objects from one file
    '''
    self.active_session.change_active(object)
    self.measurement=self.active_session.active_file_data
    self.input_file_name=object[0]
    # reset index to the first sequence in that file
    self.index_mess=index_mess
    self.active_multiplot=False
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    for window in self.open_windows:
      window.destroy() 
    self.reset_statusbar()
    self.rebuild_menus()
    self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)
  
  def add_file(self, action=None, hide_status=True):
    '''
      Import one or more new datafiles of the same type.
      
      @return List of names that have been imported.
    '''
    file_names=[]
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=FileImportDialog(self.active_folder, self.active_session.FILE_WILDCARDS)
    file_names, folder, template=file_dialog.run()
    file_dialog.destroy()
    if file_names is None:
      # process canceled
      return
    file_names=map(unicode, file_names)
    folder=unicode(folder)
    self.active_folder=folder
    #----------------File selection dialog-------------------#
    # show a status dialog for the file import
    if type(sys.stdout)!=file:
      if not self.status_dialog:
        status_dialog=StatusDialog('Import Status', flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  parent=self, buttons=('Close', 0))
        self.status_dialog=status_dialog
        status_dialog.connect('response', lambda *ignore: status_dialog.hide())
        status_dialog.set_default_size(800, 600)
      else:
        status_dialog=self.status_dialog
      status_dialog.show_all()
      sys.stdout.second_output=status_dialog
    # try to import the selected files and append them to the active sesssion
    if template is None:
      if self.active_session.ONLY_IMPORT_MULTIFILE:
        self.active_session.add_file(file_names, append=True)
      else:
        for file_name in file_names:
          datasets=self.active_session.add_file(file_name, append=True)
          if len(datasets)>0:
            self.active_session.change_active(name=file_name)
    else:
      # if a template was selected, read the files using this template
      session=self.active_session
      for file_name in file_names:
        datasets=template(file_name)
        if datasets=='NULL':
          continue
        datasets=session.create_numbers(datasets)
        session.add_data(datasets, file_name)
        session.new_file_data_treatment(datasets)
      session.active_file_data=session.file_data[file_names[0]]
      session.active_file_name=file_names[0]
    # set the last imported file as active
    self.measurement=self.active_session.active_file_data
    if len(self.measurement)==0:
      # file was selected but without producing any result
      # this can only be triggered when importing at startup
      if type(sys.stdout)!=file:
        sys.stdout.second_output=None
        if hide_status:
          status_dialog.hide()
      return True
    self.input_file_name=self.active_session.active_file_name
    self.index_mess=0
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    for window in self.open_windows:
      window.destroy()    
    if type(sys.stdout)!=file:
      sys.stdout.second_output=None
      if hide_status:
        status_dialog.hide()
    self.rebuild_menus()
    if hide_status:
      self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)
    return True

  def save_snapshot(self, action):
    '''
      Save a snapshot of the active work.
    '''
    if action.get_name()=='SaveSnapshot':
      name=None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Snapshot to File...', 
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE, 
                                        buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_select_multiple(False)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      file_dialog.set_current_name(self.active_session.active_file_name+'.mdd')
      filter = gtk.FileFilter()
      filter.set_name("Snapshots (*.mdd)")
      filter.add_pattern("*.mdd")
      file_dialog.add_filter(filter)
      filter = gtk.FileFilter()
      filter.set_name("All Files")
      filter.add_pattern("*")
      file_dialog.add_filter(filter)
      response = file_dialog.run()
      if response == gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        name=unicode(file_dialog.get_filenames()[0], 'utf-8')
        if not name.endswith(".mdd"):
          name+=".mdd"
      elif response == gtk.RESPONSE_CANCEL:
        file_dialog.destroy()
        return False
      file_dialog.destroy()
      #----------------File selection dialog-------------------#
    self.active_session.store_snapshot(name)
  
  def load_snapshot(self, action):
    '''
      Load a snapshot of earlier work.
    '''
    if action.get_name()=='LoadSnapshot':
      name=None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Snapshot to File...', 
                                        action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                        buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_select_multiple(False)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      filter = gtk.FileFilter()
      filter.set_name("Snapshots (*.mdd)")
      filter.add_pattern("*.mdd")
      file_dialog.add_filter(filter)
      filter = gtk.FileFilter()
      filter.set_name("All Files")
      filter.add_pattern("*")
      file_dialog.add_filter(filter)
      response = file_dialog.run()
      if response == gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        name=unicode(file_dialog.get_filenames()[0], 'utf-8')
        if not name.endswith(u".mdd"):
          name+=u".mdd"
      elif response == gtk.RESPONSE_CANCEL:
        file_dialog.destroy()
        return False
      file_dialog.destroy()
      #----------------File selection dialog-------------------#
    self.active_session.reload_snapshot(name)
    self.measurement=self.active_session.active_file_data
    self.replot()

  def change_range(self, action):
    '''
      Change plotting range according to textinput.
    '''
    # set the font size
    try:
      self.active_session.font_size=float(self.font_size.get_text())
    except ValueError:
      self.active_session.font_size=24.
      self.font_size.set_text('24')
    # get selected ranges which can be given as e.g. "[1:3]", "4:" , "3,4" , 3.2 4.5
    ranges_texts=[]
    ranges_texts.append(self.x_range_in.get_text().lstrip('[').rstrip(']'))
    ranges_texts.append(self.y_range_in.get_text().lstrip('[').rstrip(']'))
    ranges_texts.append(self.z_range_in.get_text().lstrip('[').rstrip(']'))
    for i, range in enumerate(ranges_texts):
      if ':' in range:
        ranges_texts[i]=range.replace(',', '.').split(':')
      elif ',' in range:
        ranges_texts[i]=range.split(',')
      else:
        ranges_texts[i]=range.strip().split()
    xin=ranges_texts[0]
    yin=ranges_texts[1]
    zin=ranges_texts[2]
    # change ranges
    plot_options=self.measurement[self.index_mess].plot_options
    if self.active_multiplot:
      for mp in self.multiplot:
        for mpi, mpname in mp:
          if self.measurement[self.index_mess] is mpi:
            plot_options=mp[0][0].plot_options
    if len(xin)==2:
      try:
        plot_options.xrange=xin
      except ValueError:
        pass
    else:
      plot_options.xrange=[None, None]
    if len(yin)==2:
      try:
        plot_options.yrange=yin
      except ValueError:
        pass
    else:
      plot_options.yrange=[None, None]
    if len(zin)==2:
      try:
        plot_options.zrange=zin
      except ValueError:
        pass
    else:
      plot_options.zrange=[None, None]
    self.replot() # plot with new settings

  def open_plot_options_window(self,action):
    '''
      Open a dialog window to insert additional gnuplot commands.
      After opening the button is rerouted.
    '''
    # TODO: Add gnuplot help functions and character selector
    #+++++++++++++++++ Adding input fields in table +++++++++++++++++
    dialog=gtk.Dialog(title='Custom Gnuplot settings')
    table=gtk.Table(6,13,False)
    
    # PNG terminal
    label=gtk.Label()
    label.set_markup('Terminal for PNG export (as shown in GUI Window):')
    table.attach(label, 0, 6, 0, 1, 0, 0, 0, 0);
    terminal_png=gtk.Entry()
    terminal_png.set_text(gnuplot_preferences.set_output_terminal_png)
    table.attach(terminal_png,
                # X direction #          # Y direction
                0, 6,                      1, 2,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    # PS terminal
    label=gtk.Label()
    label.set_markup('Terminal for PS export:')
    table.attach(label, 0, 6, 2, 3, 0, 0, 0, 0);
    terminal_ps=gtk.Entry()
    terminal_ps.set_text(gnuplot_preferences.set_output_terminal_ps)
    table.attach(terminal_ps,
                # X direction #          # Y direction
                0, 6,                      3, 4,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    # x-,y- and z-label
    label=gtk.Label()
    label.set_markup('x-label:')
    table.attach(label,0,1, 4,5, 0, 0, 0, 0);
    x_label=gtk.Entry()
    x_label.set_text(gnuplot_preferences.x_label)
    table.attach(x_label,1,2, 4,5, 0,0, 0,0);
    label=gtk.Label()
    label.set_markup('y-label:')
    table.attach(label,2,3, 4,5, 0, 0, 0, 0);
    y_label=gtk.Entry()
    y_label.set_text(gnuplot_preferences.y_label)
    table.attach(y_label,3,4, 4,5,0,0, 0,0);
    label=gtk.Label()
    label.set_markup('z-label:')
    table.attach(label,4,5, 4,5, 0, 0, 0, 0);
    z_label=gtk.Entry()
    z_label.set_text(gnuplot_preferences.z_label)
    table.attach(z_label,5,6, 4,5, 0,0, 0,0);

    # parameters for plot
    label=gtk.Label()
    label.set_markup('Parameters for normal plot:')
    table.attach(label, 0, 6, 5, 6, 0, 0, 0, 0);
    plotting_parameters=gtk.Entry()
    plotting_parameters.set_text(gnuplot_preferences.plotting_parameters)
    table.attach(plotting_parameters,
                # X direction #          # Y direction
                0, 3,                      6, 7,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    # parameters for plot with errorbars
    label=gtk.Label()
    label.set_markup('Parameters for plot with errorbars:')
    table.attach(label, 0, 6, 7, 8, 0, 0, 0, 0);
    plotting_parameters_errorbars=gtk.Entry()
    plotting_parameters_errorbars.set_text(gnuplot_preferences.plotting_parameters_errorbars)
    table.attach(plotting_parameters_errorbars,
                # X direction #          # Y direction
                0, 3,                      8, 9,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    # parameters for plot in 3d
    label3d=gtk.Label()
    label3d.set_markup('Parameters for 3d plot:')
    table.attach(label3d, 0, 6, 9, 10, 0, 0, 0, 0);
    plotting_parameters_3d=gtk.Entry()
    plotting_parameters_3d.set_text(gnuplot_preferences.plotting_parameters_3d)
    table.attach(plotting_parameters_3d,
                # X direction #          # Y direction
                0, 3,                      10, 12,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    plotting_settings_3d=gtk.TextView()
    plotting_settings_3d.get_buffer().set_text(gnuplot_preferences.settings_3d)
    table.attach(plotting_settings_3d,
                # X direction #          # Y direction
                3, 6,                      10, 11,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         5);
    plotting_settings_3dmap=gtk.TextView()
    plotting_settings_3dmap.get_buffer().set_text(gnuplot_preferences.settings_3dmap)
    table.attach(plotting_settings_3dmap,
                # X direction #          # Y direction
                3, 6,                      11, 12,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         5);

    # additional Gnuplot commands
    label=gtk.Label()
    label.set_markup('Gnuplot commands executed additionally:')
    table.attach(label, 0, 6, 12, 13, 0, 0, 0, 0);
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(self.plot_options_view) # add textbuffer view widget
    table.attach(sw,
                # X direction #          # Y direction
                0, 6,                      13, 14,
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    table.show_all()
    if self.measurement[self.index_mess].zdata<0:
      label3d.hide()
      plotting_parameters_3d.hide()
      plotting_settings_3d.hide()
      plotting_settings_3dmap.hide()
    #----------------- Adding input fields in table -----------------
    dialog.vbox.add(table) # add table to dialog box
    dialog.set_default_size(300,200)
    dialog.add_button('Apply and Replot',1) # button replot has handler_id 1
    dialog.connect("response", self.change_plot_options,
                               terminal_png, terminal_ps, 
                               x_label, 
                               y_label, 
                               z_label,
                               plotting_parameters, 
                               plotting_parameters_errorbars, 
                               plotting_parameters_3d, 
                               plotting_settings_3d, 
                               plotting_settings_3dmap)
    # befor the widget gets destroyed the textbuffer view widget is removed
    dialog.connect("destroy",self.close_plot_options_window,sw) 
    dialog.show()
    # reroute the button to close the dialog, not open it
    self.plot_options_button.disconnect(self.plot_options_handler_id)
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",lambda *w: dialog.destroy())
    self.plot_options_window_open=True
    # connect dialog to main window
    self.open_windows.append(dialog)
    dialog.connect("destroy", lambda *w: self.open_windows.remove(dialog))    

  def close_plot_options_window(self,dialog,sw):
    '''
      Reroute the plot options button and remove the textbox when dialog is closed.
      If this is not done, the textbox gets destroyed and we can't reopen the dialog.
      
      @param dialog The dialog widget that will be closed
      @param sw The scrolledWindow to be unpluged before closing.
    '''
    dialog.hide()
    sw.remove(self.plot_options_view)
    # reroute the button to open a new window
    self.plot_options_button.disconnect(self.plot_options_handler_id)
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)
    self.plot_options_window_open=False

  def change_plot_options(self,widget,action,
                          terminal_png,
                          terminal_ps,
                          x_label,
                          y_label,
                          z_label,
                          plotting_parameters,
                          plotting_parameters_errorbars,
                          plotting_parameters_3d, 
                          plotting_settings_3d, 
                          plotting_settings_3dmap):
    '''
      Plot with new commands from dialog window. Gets triggerd when the apply
      button is pressed.
    '''
    # only apply when the triggered action is realy the apply button.
    if action==1:
      found=False
      if self.active_multiplot:
        for mp in self.multiplot:
          for mpi, mpname in mp:
            if self.measurement[self.index_mess] is mpi:
              mp[0][0].plot_options=\
                self.plot_options_buffer.get_text(\
                  self.plot_options_buffer.get_start_iter(),\
                  self.plot_options_buffer.get_end_iter())
              found=True
      if not found:
        self.measurement[self.index_mess].plot_options=\
          self.plot_options_buffer.get_text(\
            self.plot_options_buffer.get_start_iter(),\
            self.plot_options_buffer.get_end_iter())
      gnuplot_preferences.set_output_terminal_png=terminal_png.get_text()
      gnuplot_preferences.set_output_terminal_ps=terminal_ps.get_text()
      gnuplot_preferences.x_label=x_label.get_text()
      gnuplot_preferences.y_label=y_label.get_text()
      gnuplot_preferences.z_label=z_label.get_text()
      gnuplot_preferences.plotting_parameters=plotting_parameters.get_text()
      gnuplot_preferences.plotting_parameters_errorbars=plotting_parameters_errorbars.get_text()
      gnuplot_preferences.plotting_parameters_3d=plotting_parameters_3d.get_text()
      buffer=plotting_settings_3d.get_buffer()
      gnuplot_preferences.settings_3d=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
      buffer=plotting_settings_3dmap.get_buffer()
      gnuplot_preferences.settings_3dmap=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
      self.replot() # plot with new settings

  def load_profile(self,action):
    '''
      Load a plot profile.
    '''
    # trigger load function from a profile in the dictionary
    self.profiles[action.get_name()].load(self)
    if self.plot_options_window_open:
      self.plot_options_button.emit("clicked")
      self.plot_options_button.emit("clicked")

  def save_profile(self,action):
    '''
      Save a plot profile.
    '''
    # open a dialog asking for the profile name
    name_dialog=gtk.Dialog(title='Enter profile name:')
    name_entry=gtk.Entry()
    name_entry.show()
    name_entry.set_text('Enter Name')
    name_entry.set_width_chars(20)
    name_dialog.add_action_widget(name_entry,1)
    response = name_dialog.run()
    name=name_entry.get_text()
    name_dialog.destroy()
    # add the profile to the profiles dictionary
    self.profiles[name]= PlotProfile(name)
    self.profiles[name].save(self)
    # new profile has to be added to the menu
    self.rebuild_menus()

  def delete_profile(self,action):
    '''
      Delete a plot profile.
    '''
    # open a dialog for selecting the profiel to be deleted
    delete_dialog=gtk.Dialog(title='Delete profile')
    self.delete_name=''
    radio_group=None
    # create a list of radio buttons for the profiles
    for profile in self.profiles.items():
      if radio_group==None:
        entry=gtk.RadioButton(group=None, label=profile[0])
        radio_group=entry
      else:
        entry=gtk.RadioButton(group=radio_group, label=profile[0])
      entry.connect("clicked",self.set_delete_name)
      entry.show()
      delete_dialog.vbox.add(entry)
    delete_dialog.add_button('Delete',1)
    delete_dialog.add_button('Abbort',2)
    response = delete_dialog.run()
    # only delet when the response is 'Delete'
    if (response == 1) & ( not self.delete_name == '' ):
      del self.profiles[self.delete_name]
    del self.delete_name
    delete_dialog.destroy()
    # remove the deleted profile from the menu
    self.rebuild_menus()

  def set_delete_name(self,action):
    '''
      Set self.delete_name from entry object.
    '''
    self.delete_name=action.get_label()

  def show_last_plot_params(self,action):
    '''
      Show a text window with the text, that would be used for gnuplot to
      plot the current measurement. Last gnuplot errors are shown below,
      if there have been any.
    '''    
    global errorbars
    if self.active_multiplot:
      for plotlist in self.multiplot:
        itemlist=[item[0] for item in plotlist]
        if self.measurement[self.index_mess] in itemlist:
          plot_text=measurement_data_plotting.create_plot_script(
                                        self.active_session, 
                                        [item[0] for item in plotlist], 
                                        self.active_session.active_file_name, 
                                        '', 
                                        plotlist[0][0].short_info, 
                                        [item[0].short_info for item in plotlist], 
                                        errorbars,
                                        self.active_session.TEMP_DIR+'plot_temp.png',
                                        fit_lorentz=False)   
    else:
      plot_text=measurement_data_plotting.create_plot_script(
                         self.active_session, 
                         [self.measurement[self.index_mess]],
                         self.active_session.active_file_name, 
                         '', 
                         self.measurement[self.index_mess].short_info,
                         [object.short_info for object in self.measurement[self.index_mess].plot_together],
                         errorbars, 
                         output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                         fit_lorentz=False)
    # create a dialog to show the plot text for the active data
    param_dialog=gtk.Dialog(title='Last plot parameters:')
    param_dialog.set_default_size(600,400)
    # alignment table
    table=gtk.Table(1,4,False)
    
    # Label
    label=gtk.Label()
    label.set_markup('Gnuplot input for the last plot:')
    table.attach(label, 0, 1, 0, 1, 0, 0, 0, 0);

    # plot options
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    text_filed=gtk.Label()
    text_filed.set_markup(plot_text.replace('<', '[').replace('>', ']'))
    sw.add_with_viewport(text_filed) # add textbuffer view widget
    table.attach(sw, 0, 1, 1, 2, gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL, 0, 0);
    # errors of the last plot
    if self.last_plot_text!='':
      # Label
      label=gtk.Label()
      label.set_markup('Error during execution:')
      table.attach(label, 0, 1, 2, 3, 0, 0, 0, 0);
      sw = gtk.ScrolledWindow()
      # Set the adjustments for horizontal and vertical scroll bars.
      # POLICY_AUTOMATIC will automatically decide whether you need
      # scrollbars.
      sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
      text_filed=gtk.Label()
      text_filed.set_markup(self.last_plot_text)
      sw.add_with_viewport(text_filed) # add textbuffer view widget
      table.attach(sw, 0, 1, 3, 4, gtk.EXPAND|gtk.FILL, gtk.FILL, 0, 0);
    param_dialog.vbox.add(table)
    param_dialog.show_all()
    # connect dialog to main window
    self.open_windows.append(param_dialog)
    param_dialog.connect("destroy", lambda *w: self.open_windows.remove(param_dialog))    

  def show_status_dialog(self, action):
    '''
      Show the dialog which holds the file import informations.
    '''
    if self.status_dialog:
      self.status_dialog.show_all()

  def change_data_filter(self,action):
    '''
      A dialog to select filters, that remove points from the plotted dataset.
    '''
    filters=[]
    data=self.measurement[self.index_mess]
    filter_dialog=gtk.Dialog(title='Filter the plotted data:', parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                             buttons=('New Filter',3, 'OK',1, 'Apply changes',2, 'Cancel',0))
    filter_dialog.set_default_size(600,150)
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    table_rows=1
    table=gtk.Table(1,5,False)
    sw.add_with_viewport(table) # add textbuffer view widget
    filter_dialog.vbox.add(sw)
    # add lines for every active filter
    for data_filter in data.filters:
      filters.append(self.get_new_filter(table,table_rows,data,data_filter))
      table_rows+=1
      table.resize(table_rows,5)
    filters.append(self.get_new_filter(table,table_rows,data))
    table_rows+=1
    table.resize(table_rows,5)
    filter_dialog.show_all()
    # open dialog and wait for a response
    filter_dialog.connect("response", self.change_data_filter_response, table, filters, data)

  def change_data_filter_response(self, filter_dialog, response, table, filters, data):
    '''
      Response actions for the add data filter dialog.
    '''
    # if the response is 'New Filter' add a new filter row and rerun the dialog
    if response==3:
      filters.append(self.get_new_filter(table,len(filters)+1,data))
      filter_dialog.show_all()
    # if response is apply change the dataset filters
    if response==1 or response==2:
      new_filters=[]
      for filter_widgets in filters:
        if filter_widgets[0].get_active()==0:
          continue
        try:
          ffrom=float(filter_widgets[1].get_text())
        except ValueError:
          ffrom=None
        try:
          fto=float(filter_widgets[2].get_text())
        except ValueError:
          fto=None
        new_filters.append(\
            (filter_widgets[0].get_active()-1,\
            ffrom,\
            fto,\
            filter_widgets[3].get_active())\
            )
      self.file_actions.activate_action('change filter', new_filters)
      self.replot()
    if response<2:
      # close dialog and replot
      filter_dialog.destroy()
    
  def get_new_filter(self,table,row,data,parameters=(-1,0,0,False)):
    ''' 
      Create all widgets for the filter selection of one filter in 
      change_data_filter dialog and place them in a table.
      
      @return Sequence of the created widgets.
    '''
    column=gtk.combo_box_new_text()
    column.append_text('None')
    # drop down menu for the columns present in the dataset
    for column_dim in data.dimensions():
      column.append_text(column_dim)
    column.set_active(parameters[0]+1)
    table.attach(column,
                # X direction #          # Y direction
                0, 1,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    from_data=gtk.Entry()
    from_data.set_width_chars(8)
    from_data.set_text('{from}')
    from_data.set_text(str(parameters[1]))
    table.attach(from_data,
                # X direction #          # Y direction
                1, 2,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    to_data=gtk.Entry()
    to_data.set_width_chars(8)
    to_data.set_text('{to}')
    to_data.set_text(str(parameters[2]))
    table.attach(to_data,
                # X direction #          # Y direction
                2, 3,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    include=gtk.CheckButton(label='include region', use_underline=False)
    include.set_active(parameters[3])
    table.attach(include,
                # X direction #          # Y direction
                3, 4,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    return (column,from_data,to_data,include)
  
  def unit_transformation(self, action):
    '''
      Open a dialog to transform the units and dimensions of one dataset.
      A set of common unit transformations is stored in config.transformations.
    '''
    # TODO: More convinient entries.
    from config.transformations import known_transformations
    units=self.active_session.active_file_data[self.index_mess].units()
    dimensions=self.active_session.active_file_data[self.index_mess].dimensions()
    allowed_trans=[]
    for trans in known_transformations:
      # Only unit transformation
      if len(trans) == 4:
        if trans[0] in units:
          allowed_trans.append(trans)
        elif trans[3] in units:
          allowed_trans.append([trans[3], 1./trans[1], -1*trans[2]/trans[1], trans[0]])
      else:
        if (trans[0] in dimensions) and (trans[1] in units):
          allowed_trans.append(trans)
        elif (trans[4] in dimensions) and (trans[5] in units):
          allowed_trans.append([trans[4], trans[5], 1./trans[2], -1*trans[3]/trans[2], trans[0], trans[1]])

    trans_box=gtk.combo_box_new_text()
    trans_box.append_text('empty')
    trans_box.set_active(0)
    for trans in allowed_trans:
      if len(trans)==4:
        trans_box.append_text('%s -> %s' % (trans[0], trans[3]))
      else:
        trans_box.append_text('%s -> %s' % (trans[0], trans[4]))
    transformations_dialog=gtk.Dialog(title='Transform Units/Dimensions:')
    transformations_dialog.set_default_size(600,150)
    try:
      transformations_dialog.get_action_area().pack_end(trans_box,False)
    except AttributeError:
      button_box=transformations_dialog.vbox.get_children()[-1]
      button_box.pack_end(trans_box,False)
    transformations_dialog.add_button('Add transformation',2)
    transformations_dialog.add_button('Apply changes',1)
    transformations_dialog.add_button('Cancel',0)
    table=gtk.Table(1,1,False)
    transformations_dialog.vbox.add(table)
    transformations_dialog.show_all()
    result=transformations_dialog.run()
    
    transformations_list=[]
    while(result==2):
      index=trans_box.get_active()
      if index>0:
        trans=allowed_trans[index-1]
      else:
        trans=['', '', 1., 0, '', '']
      self.get_new_transformation(trans, table, transformations_list, units, dimensions)
      trans_box.set_active(0)
      result=transformations_dialog.run()
    if result==1:
      transformations=self.create_transformations(transformations_list, units, dimensions)
      self.file_actions.activate_action('unit_transformations', transformations)
      self.replot()
      self.rebuild_menus()
    transformations_dialog.destroy()

  def get_new_transformation(self, transformations, dialog_table,  list, units, dimensions):
    '''
      Create a entry field line for a unit transformation.
    '''
    table=table=gtk.Table(11,1,False)
    entry_list=[]
    entry=gtk.Entry()
    entry.set_width_chars(10)
    if len(transformations)>4:
      entry.set_text(transformations[0])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    selector=gtk.MenuBar()
    selector_menu_button=gtk.MenuItem('↓')
    selector.add(selector_menu_button)
    selector_menu=gtk.Menu()
    def set_entry(action, dim, unit):
      # Put the selected unit and dimension in the entries
      entry_list[0].set_text(dim)
      entry_list[1].set_text(unit)
      entry_list[4].set_text(dim)
      entry_list[5].set_text(unit)
    for i, dim in enumerate(dimensions):
      add_menu=gtk.MenuItem("%s [%s]" % (dim, units[i]))
      add_menu.connect('activate', set_entry, dim, units[i])
      selector_menu.add(add_menu)
    selector_menu_button.set_submenu(selector_menu)
    
    table.attach(selector,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(transformations[1])
    else:
      entry.set_text(transformations[0])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    
    label=gtk.Label(' · ')
    table.attach(label,
                # X direction #          # Y direction
                3, 4,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(str(transformations[2]))
    else:
      entry.set_text(str(transformations[1]))
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                4, 5,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    label=gtk.Label(' + ')
    table.attach(label,
                # X direction #          # Y direction
                5, 6,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(str(transformations[3]))
    else:
      entry.set_text(str(transformations[2]))
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                6, 7,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    label=gtk.Label(' -> ')
    table.attach(label,
                # X direction #          # Y direction
                7, 8,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    entry=gtk.Entry()
    entry.set_width_chars(10)
    if len(transformations)>4:
      entry.set_text(transformations[4])
    else:
      entry.set_text(transformations[3])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                8, 9,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(transformations[5])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                9, 10,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    item=(table, entry_list)
    list.append(item)
    button=gtk.Button('DEL')
    table.attach(button,
                # X direction #          # Y direction
                10, 11,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    dialog_table.attach(table,
                # X direction #          # Y direction
                0, 1,                      len(list)-1, len(list),
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    table.show_all()
    button.connect('activate', self.remove_transformation, item, table, list)
  
  def remove_transformation(self, action, item, table, list):
    '''
      Nothing jet.
    '''
    pass
  
  def create_transformations(self, items, units, dimensions):
    '''
      Read the transformation values from the entry widgets in 'items'.
    '''
    transformations=[]
    for item in items:
      entries=map(lambda entry: entry.get_text(), item[1])
      # only unit transformation
      if entries[0]=='':
        if not entries[1] in units:
          continue
        else:
          try:
            transformations.append((entries[1], 
                                    float(entries[2]), 
                                    float(entries[3]), 
                                    entries[4]))
          except ValueError:
            continue
      else:
        if not ((entries[0] in dimensions) and (entries[1] in units)):
          continue
        else:
          try:
            transformations.append((entries[0], 
                                    entries[1], 
                                    float(entries[2]), 
                                    float(entries[3]), 
                                    entries[4], 
                                    entries[5]))
          except ValueError:
            continue
    return transformations

  def combine_data_points(self, action):
    '''
      Open a dialog to combine data points together
      to get a better statistic.
    '''
    cd_dialog=gtk.Dialog(title='Combine data points:')
    table=gtk.Table(3,4,False)
    label=gtk.Label()
    label.set_markup('Binning:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    binning=gtk.Entry()
    binning.set_width_chars(4)
    binning.set_text('1')
    table.attach(binning,
                # X direction #          # Y direction
                1, 3,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Stepsize:\n(overwrites Binning)')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      1, 2,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    bin_distance=gtk.Entry()
    bin_distance.set_width_chars(4)
    bin_distance.set_text('None')
    table.attach(bin_distance,
                # X direction #          # Y direction
                1, 3,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    table.show_all()
    # Enty activation triggers calculation, too
    binning.connect('activate', lambda *ign: cd_dialog.response(1))
    bin_distance.connect('activate', lambda *ign: cd_dialog.response(1))
    cd_dialog.vbox.add(table)
    cd_dialog.add_button('OK', 1)
    cd_dialog.add_button('Cancel', 0)
    result=cd_dialog.run()
    if result==1:
      try:
        bd=float(bin_distance.get_text())
      except ValueError:
        bd=None
      self.file_actions.activate_action('combine-data', 
                                        int(binning.get_text()), 
                                        bd
                                        )
    cd_dialog.destroy()
    self.rebuild_menus()
    self.replot()      

  def derivate_data(self, action):
    '''
      Derivate or smooth data using the local Savitzky Golay filter or the global
      spectral estimate method calculated with a Butterworth filter.
    '''
    parameters, result=SimpleEntryDialog('Derivate Data...', 
                                         [('Select Method',
                                          ['Spectral Estimate (Noisy or Periodic Data)', 'Moving Window (Low Errorbars)'], 
                                          0)]
                                         ).run()
    if not result:
      return
    if parameters['Select Method']=='Moving Window (Low Errorbars)':
      parameters, result=SimpleEntryDialog('Derivate Data - Moving Window Filter...', 
                                           (('Window Size', 5, int), 
                                              ('Polynomial Order', 2, int), 
                                              ('Derivative', 1, int))).run()
      if parameters['Polynomial Order']>parameters['Window Size']-2:
        parameters['Polynomial Order']=parameters['Window Size']-2
      if parameters['Derivative']+1>parameters['Polynomial Order']:
        parameters['Derivative']=parameters['Polynomial Order']-1
      if result:
        # create a new dataset with the smoothed data and all derivatives till the selected order
        self.file_actions.activate_action('savitzky_golay', 
                          parameters['Window Size'], 
                          parameters['Polynomial Order'], 
                          parameters['Derivative'])
        self.rebuild_menus()
        self.replot()
    else:
      parameters, result=SimpleEntryDialog('Derivate Data - Spectral Estimate Method...', 
                                           (('Filter Steepness', 6, int), 
                                              ('Noise Filter Frequency (0,1]', 0.5, float), 
                                              ('Derivative', 1, int))).run()
      if result:
        # create a new dataset with the smoothed data and all derivatives till the selected order
        self.file_actions.activate_action('butterworth', 
                          parameters['Filter Steepness'], 
                          parameters['Noise Filter Frequency (0,1]'], 
                          parameters['Derivative'])
        self.rebuild_menus()
        self.replot()
  
  def colorcode_points(self, action):
    '''
      Show points colorcoded by their number.
    '''
    global errorbars
    dataset=self.measurement[self.index_mess]
    if errorbars:
      errorbars=False
    dataset.plot_options.special_plot_parameters="w lines palette"
    dataset.plot_options.special_using_parameters=":0"   
    dataset.plot_options.settings['cblabel']=['"Pointnumber"']
    dataset.plot_options.settings['pm3d']=['map']
    dataset.plot_options.splot='s'
    self.replot()
    dataset.plot_options.special_plot_parameters=None
    dataset.plot_options.special_using_parameters=""
    dataset.plot_options.splot=''
    del(dataset.plot_options.settings['cblabel'])  
  
  def extract_cross_section(self, action):
    '''
      Open a dialog to select a cross-section through an 3D-dataset.
      The user can select a line and width for the cross-section,
      after this the data is extracted and appendet to the fileobject.
      
      @return If the extraction was successful
    '''
    data=self.measurement[self.index_mess]
    dimension_names=[]
    dims=data.dimensions()
    dimension_names.append(dims[data.xdata])
    dimension_names.append(dims[data.ydata])
    del(dims)
    cs_dialog=gtk.Dialog(title='Create a cross-section:')
    table=gtk.Table(3,7,False)
    label=gtk.Label()
    label.set_markup('Direction:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      1, 3,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[0])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    line_x=gtk.Entry()
    line_x.set_width_chars(6)
    line_x.set_text('1')
    table.attach(line_x,
                # X direction #          # Y direction
                2, 3,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[1])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      2, 3,
                0,                       gtk.FILL,
                0,                         0);
    line_y=gtk.Entry()
    line_y.set_width_chars(6)
    line_y.set_text('0')
    table.attach(line_y,
                # X direction #          # Y direction
                2, 3,                      2, 3,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Start Point:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      3, 5,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[0])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      3, 4,
                0,                       gtk.FILL,
                0,                         0);
    line_x0=gtk.Entry()
    line_x0.set_width_chars(6)
    line_x0.set_text('0')
    table.attach(line_x0,
                # X direction #          # Y direction
                2, 3,                      3, 4,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[1])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      4, 5,
                0,                       gtk.FILL,
                0,                         0);
    line_y0=gtk.Entry()
    line_y0.set_width_chars(6)
    line_y0.set_text('0')
    table.attach(line_y0,
                # X direction #          # Y direction
                2, 3,                      4, 5,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Width:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      5, 6,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    line_width=gtk.Entry()
    line_width.set_width_chars(6)
    line_width.set_text('1')
    table.attach(line_width,
                # X direction #          # Y direction
                1, 3,                      5, 6,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Binning:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      6, 7,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    binning=gtk.Entry()
    binning.set_width_chars(4)
    binning.set_text('1')
    table.attach(binning,
                # X direction #          # Y direction
                1, 3,                      6, 7,
                0,                       gtk.FILL,
                0,                         0);
    weight=gtk.CheckButton(label='Gauss weighting, Sigma:', use_underline=True)
    table.attach(weight,
                # X direction #          # Y direction
                0, 2,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    sigma=gtk.Entry()
    sigma.set_width_chars(4)
    sigma.set_text('1e10')
    table.attach(sigma,
                # X direction #          # Y direction
                2, 3,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Stepsize:\n(overwrites Binning)')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      8, 9,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    bin_distance=gtk.Entry()
    bin_distance.set_width_chars(4)
    bin_distance.set_text('None')
    table.attach(bin_distance,
                # X direction #          # Y direction
                1, 3,                      8, 9,
                0,                       gtk.FILL,
                0,                         0);
    table.show_all()
    # Enty activation triggers calculation, too
    line_x.connect('activate', lambda *ign: cs_dialog.response(1))
    line_x0.connect('activate', lambda *ign: cs_dialog.response(1))
    line_y.connect('activate', lambda *ign: cs_dialog.response(1))
    line_y0.connect('activate', lambda *ign: cs_dialog.response(1))
    line_width.connect('activate', lambda *ign: cs_dialog.response(1))
    binning.connect('activate', lambda *ign: cs_dialog.response(1))
    bin_distance.connect('activate', lambda *ign: cs_dialog.response(1))
    sigma.connect('activate', lambda *ign: cs_dialog.response(1))
    cs_dialog.vbox.add(table)
    cs_dialog.add_button('OK', 1)
    cs_dialog.add_button('Cancel', 0)
    result=cs_dialog.run()
    if result==1:
      try:
        bd=float(bin_distance.get_text())
      except ValueError:
        bd=None
      gotit=self.file_actions.activate_action('cross-section', 
                                        float(line_x.get_text()), 
                                        float(line_x0.get_text()), 
                                        float(line_y.get_text()), 
                                        float(line_y0.get_text()), 
                                        float(line_width.get_text()), 
                                        int(binning.get_text()), 
                                        weight.get_active(), 
                                        float(sigma.get_text()), 
                                        False, 
                                        bd
                                        )
      if not gotit:
        message=gtk.MessageDialog(parent=self, 
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
    else:
      gotit=False
    cs_dialog.destroy()
    if gotit:
      self.rebuild_menus()
      self.replot()      
    return gotit

  def extract_radial_integration(self, action):
    '''
      Open a dialog to select point as center of a radial integration.
      
      @return If the extraction was successful
    '''
    data=self.measurement[self.index_mess]
    dimension_names=[]
    dims=data.dimensions()
    dimension_names.append(dims[data.xdata])
    dimension_names.append(dims[data.ydata])
    ri_dialog=gtk.Dialog(title='Create a radial integration:')
    table=gtk.Table(3,7,False)
    label=gtk.Label()
    label.set_markup('Center Point:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[0])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    center_x0=gtk.Entry()
    center_x0.set_width_chars(6)
    center_x0.set_text('0')
    table.attach(center_x0,
                # X direction #          # Y direction
                2, 3,                      0, 1, 
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup(dimension_names[1])
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    center_y0=gtk.Entry()
    center_y0.set_width_chars(6)
    center_y0.set_text('0')
    table.attach(center_y0,
                # X direction #          # Y direction
                2, 3,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Stepsize:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      2, 3,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    delta_r=gtk.Entry()
    delta_r.set_width_chars(4)
    delta_r.set_text('0.001')
    table.attach(delta_r,
                # X direction #          # Y direction
                1, 3,                      2, 3,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Maximal Radius:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      3, 4,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    max_r=gtk.Entry()
    max_r.set_width_chars(4)
    max_r.set_text('1e10')
    table.attach(max_r,
                # X direction #          # Y direction
                1, 3,                      3, 4,
                0,                       gtk.FILL,
                0,                         0);
    table.show_all()
    # Enty activation triggers calculation, too
    center_x0.connect('activate', lambda *ign: ri_dialog.response(1))
    center_y0.connect('activate', lambda *ign: ri_dialog.response(1))
    delta_r.connect('activate', lambda *ign: ri_dialog.response(1))
    max_r.connect('activate', lambda *ign: ri_dialog.response(1))
    ri_dialog.vbox.add(table)
    ri_dialog.add_button('OK', 1)
    ri_dialog.add_button('Cancel', 0)
    result=ri_dialog.run()
    if result==1:
      try:
        dr=float(delta_r.get_text())
        x0=float(center_x0.get_text())
        y0=float(center_y0.get_text())
        mr=float(max_r.get_text())
      except ValueError:
        message=gtk.MessageDialog(parent=self, 
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
        return False
      gotit=self.file_actions.activate_action('radial_integration', 
                                        x0, y0, dr, mr, False
                                        )
      if not gotit:
        message=gtk.MessageDialog(parent=self, 
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
    else:
      gotit=False
    ri_dialog.destroy()
    if gotit:
      self.rebuild_menus()
      self.replot()      
    return gotit

  def extract_integrated_intensities(self, action):
    '''
      Open a dialog to select points and datasets for integration of intensities.
      Measured data around that point is avaridged and plotted agains a user defined value.
      
      @return If the extraction was successful
    '''
    eii_dialog=gtk.Dialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                          title='Select points and datasets to integrate intensities...')
    data_list=[]
    # Get all datasets with 3d data
    for key, value in sorted(self.active_session.file_data.items()):
      for i, dataset in enumerate(value):
        if dataset.zdata>=0:
          data_list.append((key, i, dataset.short_info))
    table=gtk.Table(6, 3, False)
    position_table=gtk.Table(6, 3, False)
    dataset_table=gtk.Table(3, 2, False)
    dimension=gtk.Entry()
    dimension.set_width_chars(10)
    dimension.set_text("Dimension")
    dataset_table.attach(dimension,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    unit=gtk.Entry()
    unit.set_width_chars(10)
    unit.set_text("Unit")
    dataset_table.attach(unit,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label("   Selected Dataset")
    dataset_table.attach(label,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    table.attach(position_table,
                # X direction #          # Y direction
                0, 5,                      0, 1,
                0,                       gtk.FILL,
                0,                         0);
    table.attach(dataset_table,
                # X direction #          # Y direction
                0, 5,                      1, 2,
                0,                       gtk.FILL,
                0,                         0);
    datasets=[]
    int_points=[]
    add_dataset_button=gtk.Button("Add Dataset")
    add_dataset_button.connect('clicked', self.get_dataset_selection, datasets, dataset_table, data_list)
    self.get_dataset_selection(None, datasets, dataset_table, data_list)
    add_position_button=gtk.Button("Add Position")
    add_position_button.connect('clicked', self.get_position_selection, int_points, position_table)
    self.get_position_selection(None, int_points, position_table)
    table.attach(add_dataset_button,
                # X direction #          # Y direction
                2, 5,                      2, 3,
                0,                       gtk.FILL,
                0,                         0);
    table.attach(add_position_button,
                # X direction #          # Y direction
                0, 2,                      2, 3,
                0,                       gtk.FILL,
                0,                         0);
    eii_dialog.add_button('OK', 1)
    eii_dialog.add_button('Cancel', 0)
    eii_dialog.vbox.add(table)
    table.show_all()
    result=eii_dialog.run()
    if result==1:
      # User pressed OK, try to get all entry values
      did_calculate=False
      # if only one dataset is selected the values and errors of
      # the integration are stored in a list an shown in a dialog afterwards
      int_int_values=[]
      for x_pos, y_pos, radius in int_points:
        try:
          x_pos=float(x_pos.get_text())
        except ValueError:
          continue
        try:
          y_pos=float(y_pos.get_text())
        except ValueError:
          continue
        try:
          radius=float(radius.get_text())
        except ValueError:
          continue
        data_indices=[]
        data_values=[]
        for entry in datasets:
          try:
            data_value=float(entry[0].get_text())
          except ValueError:
            data_value=0.0
          data_values.append(data_value)
          dataset=data_list[entry[1].get_active()]
          data_indices.append((dataset[0], dataset[1]))
        if len(data_indices)==0:
          print "You need to select at least one dataset."
          break
        elif len(data_indices)==1:
          dataset=self.active_session.file_data[data_indices[0][0]][data_indices[0][1]]
          value, error=self.file_actions.integrate_around_point(
                                          x_pos, y_pos, radius, dataset)
          int_int_values.append((x_pos, y_pos, value, error))
          continue
        self.file_actions.activate_action('integrate_intensities', x_pos, y_pos, radius, 
                                                dimension.get_text(), unit.get_text(), 
                                                data_indices, data_values)
        did_calculate=True
      eii_dialog.destroy()
      if did_calculate:
        self.replot()
      if len(int_int_values)>0:
        self.show_integrated_intensities(int_int_values)
    else:
      eii_dialog.destroy()

  def show_integrated_intensities(self, int_int_values):
    '''
      Show a Dialog with the values of the integrated intensities
      calculated in extract_integrated_intensities
      
      @param int_int_values List of (x-position,y-position,value,error) for the intensities
    '''
    message="Calculated integrated intensities:\n\n"
    for item in int_int_values:
      message+="(%.2f,%.2f)\t →   <b>%g</b> ± %g\n" % item
    dialog=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                             type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE)
    dialog.set_title('Result')
    dialog.set_markup(message)
    dialog.show_all()
    dialog.connect('response', lambda *ignore: dialog.destroy())

  def interpolate_and_smooth_dialog(self, action):
    '''
      Dialog to select the options for interpolation and smoothing of 2d-data
      into a regular grid.
    '''
    def int_or_none(input):
      try:
        return int(input)
      except ValueError:
        return None
    parameters, result=SimpleEntryDialog('Interpolate to regular grid and smooth data...', 
                         (('x-from', 0, float), 
                         ('x-to', 1, float), 
                         ('x-steps', '{auto}', int_or_none), 
                         ('σ-x', 0.01, float), 
                         ('y-from', 0, float), 
                         ('y-to', 1, float), 
                         ('y-steps', '{auto}', int_or_none), 
                         ('σ-y', 0.01, float), 
                         )).run()
    if result==1:
      self.file_actions.activate_action('interpolate_and_smooth', 
                      parameters['σ-x'], 
                      parameters['σ-y'], 
                      parameters['x-from'], 
                      parameters['x-to'], 
                      parameters['x-steps'], 
                      parameters['y-from'], 
                      parameters['y-to'], 
                      parameters['y-steps'], 
                      )
      self.replot()

  def rebin_3d_data_dialog(self, action):
    '''
      Dialog to select the options for interpolation and smoothing of 2d-data
      into a regular grid.
    '''
    def int_or_none(input):
      try:
        return int(input)
      except ValueError:
        return None
    parameters, result=SimpleEntryDialog('Rebin regular gridded data...', 
                         (('x-steps', 2, int), 
                         ('y-steps', '{same as x}', int_or_none), 
                         )).run()
    if result==1:
      self.file_actions.activate_action('rebin_2d', 
                      parameters['x-steps'], 
                      parameters['y-steps'], 
                      )
      self.replot()

  def get_position_selection(self, action, int_points, position_table):
    '''
      Return selection entries for x,y positions.
    '''
    label=gtk.Label("x-position: ")
    position_table.attach(label,
                # X direction #          # Y direction
                0, 1,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);
    x_pos=gtk.Entry()
    x_pos.set_width_chars(6)
    position_table.attach(x_pos,
                # X direction #          # Y direction
                1, 2,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);    
    label=gtk.Label(" y-position: ")                
    position_table.attach(label,
                # X direction #          # Y direction
                2, 3,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);
    y_pos=gtk.Entry()
    y_pos.set_width_chars(6)
    position_table.attach(y_pos,
                # X direction #          # Y direction
                3, 4,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);    
    label=gtk.Label(" radius: ")                
    position_table.attach(label,
                # X direction #          # Y direction
                4, 5,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);
    radius=gtk.Entry()
    radius.set_width_chars(6)
    position_table.attach(radius,
                # X direction #          # Y direction
                5, 6,                      len(int_points), len(int_points)+1,
                0,                       gtk.FILL,
                0,                         0);
    position_table.show_all()
    int_points.append((x_pos, y_pos, radius))

  def get_dataset_selection(self, action, datasets, dataset_table, data_list):
    '''
      Create a selection button for datasets and attach it to the dataset_table widget.
    '''
    dataset=gtk.combo_box_new_text()
    for entry in data_list:
      dataset.append_text("%s[%i] - %s" % (os.path.split(entry[0])[1], entry[1], entry[2]))
    entry=gtk.Entry()
    entry.set_width_chars(12)
    datasets.append((entry, dataset))
    entry.show()
    dataset.show()
    dataset_table.attach(entry, 
                # X direction #          # Y direction
                0, 2,                      len(datasets), len(datasets)+1,
                0,                       gtk.FILL,
                0,                         0);
    dataset_table.attach(dataset, 
                # X direction #          # Y direction
                2, 3,                      len(datasets), len(datasets)+1,
                0,                       gtk.FILL,
                0,                         0);

  def change_color_pattern(self, action):
    '''
      Open a dialog to select a different color pattern.
      The colorpatterns are defined in config.gnuplot_preferences.
    '''
    pattern_names=sorted(gnuplot_preferences.defined_color_patterns.keys())
    # get active name
    active_pattern='Default'
    for pattern in pattern_names:
      if gnuplot_preferences.defined_color_patterns[pattern] in gnuplot_preferences.settings_3dmap:
        active_pattern=pattern
    # plot available colormaps
    gptext="""# Script to plot colormaps with gnuplot
unset xtics
unset ytics
unset colorbox
set lmargin at screen 0.
set rmargin at screen 1.
set pm3d map
set term jpeg size 400,%i font "%s"
set output "%s"
set multiplot layout %i,1
    """ % (
           (len(pattern_names)*30), 
           os.path.join(gnuplot_preferences.FONT_PATH, 'Arial.ttf'), 
           os.path.join(self.active_session.TEMP_DIR, 'colormap.jpg').replace('\\', '\\\\'), 
           len(pattern_names), 
           )
    portions=1./len(pattern_names)
    for i, pattern in enumerate(pattern_names):
      gptext+='set tmargin at screen %f\nset bmargin at screen %f\n' % (1.-i*portions, 1.-(i+1.)*portions)
      gptext+='set label 1 "%s" at 50,1. center front\nset palette %s\nsplot [0:100][0:2] x w pm3d t ""\n' % (
                                  pattern, 
                                  gnuplot_preferences.defined_color_patterns[pattern])
    gptext+='unset multiplot\n'
    # send commands to gnuplot
    measurement_data_plotting.gnuplot_instance.stdin.write('reset\n')
    measurement_data_plotting.gnuplot_instance.stdin.write(gptext)
    measurement_data_plotting.gnuplot_instance.stdin.write('\nprint "|||"\n')
    output=measurement_data_plotting.gnuplot_instance.stdout.read(3)
    while output[-3:] != '|||':
      output+=measurement_data_plotting.gnuplot_instance.stdout.read(1)
    pattern_box=gtk.combo_box_new_text()
    # drop down menu for the pattern selection
    for pattern in pattern_names:
      pattern_box.append_text(pattern)
    pattern_box.show_all()
    cps_dialog=gtk.Dialog(title='Select new color pattern:')
    cps_dialog.set_default_size(400, 400)
    cps_dialog.vbox.pack_start(pattern_box, False)
    try:
      # Not all versions support jpg import
      pixbuf=gtk.gdk.pixbuf_new_from_file(os.path.join(self.active_session.TEMP_DIR, 'colormap.jpg'))
      image=gtk.Image()
      image.set_from_pixbuf(pixbuf)
      image.show()
      sw = gtk.ScrolledWindow()
      # Set the adjustments for horizontal and vertical scroll bars.
      # POLICY_AUTOMATIC will automatically decide whether you need
      # scrollbars.
      sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
      sw.add_with_viewport(image)
      sw.show()
      cps_dialog.vbox.pack_end(sw, True)
    except:
      pass
    cps_dialog.add_button('OK', 1)
    cps_dialog.add_button('Apply', 2)
    cps_dialog.add_button('Cancel', 0)
    result=cps_dialog.run()
    while result>0:
      self.file_actions.activate_action('change_color_pattern', 
              gnuplot_preferences.defined_color_patterns[pattern_names[pattern_box.get_active()]])
      self.replot()
      if result==1:
        break
      result=cps_dialog.run()
    # reset colorscale if cancel was pressed
    if result==0:
      self.file_actions.activate_action('change_color_pattern', 
              gnuplot_preferences.defined_color_patterns[active_pattern])     
      self.replot()
    cps_dialog.destroy()

  def fit_dialog(self,action, size=None, position=None):
    '''
      A dialog to fit the data with a set of functions.
      
      @param size Window size (x,y)
      @param position Window position (x,y)
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
    dataset=self.measurement[self.index_mess]
    if (dataset.fit_object==None):
      self.file_actions.activate_action('create_fit_object')
    fit_session=dataset.fit_object
    fit_dialog=gtk.Dialog(title='Fit...')
    fit_dialog.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    align, buttons, progress_bar=fit_session.get_dialog(self, fit_dialog)
    sw.add_with_viewport(align) # add fit dialog
    fit_dialog.vbox.add(sw)
    actions_table=gtk.Table(len(buttons),2,False)
    for i, button in enumerate(buttons):
      actions_table.attach(button, i, i+1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    actions_table.attach(progress_bar, 0, len(buttons), 1, 2, gtk.FILL|gtk.EXPAND, gtk.FILL, 0, 0)
    #try:
    #  fit_dialog.get_action_area().pack_end(actions_table, expand=False, fill=True, padding=0)
    #except AttributeError:
    fit_dialog.vbox.pack_end(actions_table, expand=False, fill=True, padding=0)
    fit_dialog.set_default_size(*size)
    if position!=None:
      fit_dialog.move(*position)
    fit_dialog.show_all()
    def store_fit_dialog_gemometry(widget, event):
      self.config_object['FitDialog']={
                                       'size': widget.get_size(), 
                                       'position': widget.get_position()
                                       }
    fit_dialog.connect('configure-event', store_fit_dialog_gemometry)
    self.open_windows.append(fit_dialog)

  def multi_fit_dialog(self,action, size=(800, 250), position=None):
    '''
      A dialog to fit several data with a set of functions.
      
      @param size Window size (x,y)
      @param position Window position (x,y)
    '''
    if not self.active_session.ALLOW_FIT:
      fit_dialog=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, 
                                   message_format="You don't have the system requirenments for Fitting.\nNumpy and Scipy must be installed.")
      #fit_dialog.set_markup()
      fit_dialog.run()
      fit_dialog.destroy()
      return None
    from fit_data import FitSession
    multi_fit_object=FitSession(dataset)
    
  
  def do_multi_fit(self, action, entries, fit_dialog, window):
    '''
      Called when the fit button on a multi fit dialog is pressed.
    '''
    self.open_windows.remove(fit_dialog)
    fit_dialog.destroy()

  def show_add_info(self,action):
    '''
      Show or hide advanced options widgets.
    '''
    self.x_range_in.show()
    self.x_range_label.show()
    self.y_range_in.show()
    self.y_range_label.show()
    self.font_size.show()
    self.logx.show()
    self.logy.show()
    self.plot_options_button.show()
    if self.measurement[self.index_mess].zdata>=0:
      self.logz.show()
      self.z_range_in.show()
      self.z_range_label.show()
      self.view_left.show()
      self.view_up.show()
      self.view_down.show()
      self.view_right.show()
    else:
      self.logz.hide()
      self.z_range_in.hide()
      self.z_range_label.hide()
      self.view_left.hide()
      self.view_up.hide()
      self.view_down.hide()
      self.view_right.hide()

  def apply_to_all(self,action): 
    '''
      Apply changed plotsettings to all plots. This includes x,y,z-ranges,
      logarithmic plotting and the custom plot settings.
    '''
    use_data=self.measurement[self.index_mess]
    use_dim=use_data.dimensions()
    use_maxcol=max([use_data.xdata, use_data.ydata, use_data.zdata, use_data.yerror])
    selection_dialog=PreviewDialog(self.active_session.file_data, buttons=('Apply', 0, 'Cancel', 1))
    selection_dialog.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
    selection_dialog.set_default_size(800, 600)
    if selection_dialog.run()==0:
      for dataset in selection_dialog.get_active_objects():
        dim=dataset.dimensions()
        # skip datasets which dont have enough columns
        if len(dim)<use_maxcol:
          continue
        # skip datasets which are 2d when this is 3d or vice vercer
        if (dataset.zdata<0) and (use_data.zdata>=0):
          continue
        dataset.xdata=use_data.xdata
        dataset.ydata=use_data.ydata
        dataset.zdata=use_data.zdata
        dataset.yerror=use_data.yerror
        dataset.logx=use_data.logx
        dataset.logy=use_data.logy
        dataset.logz=use_data.logz
        dataset.plot_options=use_data.plot_options.overwrite_copy(dataset.plot_options)
        self.reset_statusbar()
        print 'Applied settings to all Plots!'
    selection_dialog.destroy()

  def add_multiplot(self,action): 
    '''
      Add or remove the active dataset from multiplot list, 
      which is a list of plotnumbers of the same Type.
    '''
    # TODO: Review the multiplot stuff!
    if (action.get_name()=='AddAll')&(len(self.measurement)<40): # dont autoadd more than 40
      for i in range(len(self.measurement)):
        self.do_add_multiplot(i)
    elif action.get_name()=='ClearMultiplot':
      self.clear_multiplot()
    else:
      self.do_add_multiplot(self.index_mess)

  def clear_multiplot(self):
      self.multiplot=[]
      self.active_multiplot=False
      self.replot()
      print "Multiplots cleared."
      self.multi_list.set_markup(' Multiplot List: \n' )          

  def do_add_multiplot(self,index): 
    '''
      Add one item to multiplot list devided by plots of the same type.
    '''
    changed=False
    active_data=self.measurement[index]
    for plotlist in self.multiplot:
      itemlist=[item[0] for item in plotlist]
      if active_data in itemlist:
        plotlist.pop(itemlist.index(active_data))
        self.reset_statusbar()
        print 'Plot ' + active_data.number + ' removed.'
        changed=True
        if len(plotlist)==0:
          self.multiplot.remove(plotlist)
        break
      else:
        xi=active_data.xdata
        xj=plotlist[0][0].xdata
        yi=active_data.ydata
        yj=plotlist[0][0].ydata
        if ((active_data.units()[xi]==plotlist[0][0].units()[xj]) and \
            ((active_data.zdata==-1) or \
            (active_data.units()[yi]==plotlist[0][0].units()[yj]))):
          plotlist.append((active_data, self.active_session.active_file_name))
          self.reset_statusbar()
          print 'Plot ' + active_data.number + ' added.'
          changed=True
          break
    # recreate the shown multiplot list
    if not changed:
      self.multiplot.append(MultiplotList([(active_data, self.active_session.active_file_name)]))
      self.reset_statusbar()
      print 'Plot ' + active_data.number + ' added.'
    mp_list=''
    for i,plotlist in enumerate(self.multiplot):
      if i>0:
        mp_list=mp_list+'\n-------'
      plotlist.sort(lambda item1, item2: cmp(item1[0].number, item2[0].number))
      plotlist.sort(lambda item1, item2: cmp(item1[1], item2[1]))
      last_name=plotlist[0][1]
      mp_list+='\n' + last_name
      for item in plotlist:
        if item[1]!=last_name:
          last_name=item[1]
          mp_list+='\n' + last_name
        mp_list+='\n' + item[0].number
    self.multi_list.set_markup(' Multiplot List: \n' + mp_list)

  def toggle_error_bars(self,action):
    '''
      Show or remove error bars in plots.
    '''
    global errorbars
    errorbars= not errorbars
    self.reset_statusbar()
    self.replot()
    print 'Show errorbars='+str(errorbars)

  def toggle_xyprojections(self,action):
    '''
      Show or remove error bars in plots.
    '''
    measurement_data_plotting.maps_with_projection= not measurement_data_plotting.maps_with_projection
    self.reset_statusbar()
    self.replot()

  def export_plot(self,action): 
    '''
      Function for every export action. 
      Export is made as .png or .ps depending on the selected file name.
      Save is made as gnuplot file and output files.
    '''
    global errorbars
    self.active_session.picture_width='1600'
    self.active_session.picture_height='1200'
    if action.get_name()=='MultiPlot':
      if len(self.multiplot)>0:
        self.active_multiplot=not self.active_multiplot
      else:
        self.active_multiplot=False
      return self.replot()
    if action.get_name()=='SaveGPL':
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Gnuplot(.gp) and Datafiles(.out)...', 
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE, 
                                        buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_do_overwrite_confirmation(True)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      if self.active_multiplot:
        file_dialog.set_current_name(os.path.split(self.active_session.active_file_name + '_multi_')[1])
      else:
        file_dialog.set_current_name(os.path.split(self.active_session.active_file_name + '_')[1])
      # create the filters in the file selection dialog
      filter = gtk.FileFilter()
      filter.set_name("Gnuplot (.gp)")
      filter.add_pattern("*.gp")
      file_dialog.add_filter(filter)
      filter = gtk.FileFilter()
      filter.set_name("All files")
      filter.add_pattern("*")
      file_dialog.add_filter(filter)
      # add to checkboxes if the picture should be created and if it should be .ps
      ps_box=gtk.CheckButton('Picture as Postscript', True)
      ps_box.show()
      pic_box=gtk.CheckButton('Also create Picture', True)
      pic_box.set_active(True)
      pic_box.show()
      file_dialog.vbox.get_children()[-1].pack_start(ps_box, False)
      file_dialog.vbox.get_children()[-1].pack_start(pic_box, False)
      file_dialog.vbox.get_children()[-1].reorder_child(ps_box, 0)
      file_dialog.vbox.get_children()[-1].reorder_child(pic_box, 0)
      response = file_dialog.run()
      if response != gtk.RESPONSE_OK:
        file_dialog.destroy()
        return None
      self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
      common_folder, common_file_prefix=os.path.split(unicode(file_dialog.get_filename().rsplit('.gp', 1)[0], 'utf-8'))
      if ps_box.get_active():
        picture_type='.ps'
      else:
        picture_type='.png'
      file_dialog.destroy()
      if self.active_multiplot:
        for plotlist in self.multiplot:
          itemlist=[item[0] for item in plotlist]
          if self.measurement[self.index_mess] in itemlist:
            plot_text=measurement_data_plotting.create_plot_script(
                                          self.active_session, 
                                          [item[0] for item in plotlist], 
                                          common_file_prefix, 
                                          '', 
                                          plotlist.title, 
                                          [item[0].short_info for item in plotlist], 
                                          errorbars,
                                          common_file_prefix + picture_type,
                                          fit_lorentz=False, 
                                          output_file_prefix=common_file_prefix, 
                                          sample_name=plotlist.sample_name)
        file_numbers=[]
        for j, dataset in enumerate(itemlist):
          for i, attachedset in enumerate(dataset.plot_together):
            file_numbers.append(str(j)+'-'+str(i))
            if getattr(attachedset, 'is_matrix_data', False):
              attachedset.export_matrix(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.bin'))
            else:
              attachedset.export(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.out'))
        if itemlist[0].zdata>=0 and measurement_data_plotting.maps_with_projection:
          # export data of projections
          projections_name=os.path.join(common_folder, common_file_prefix+str(0)+'-'+str(0)+'.xy')
          itemlist[0].export_projections(projections_name)    
      else:
        plot_text=measurement_data_plotting.create_plot_script(
                           self.active_session, 
                           [self.measurement[self.index_mess]],
                           common_file_prefix, 
                           '', 
                           self.measurement[self.index_mess].short_info,
                           [object.short_info for object in self.measurement[self.index_mess].plot_together],
                           errorbars, 
                           output_file=common_file_prefix + picture_type,
                           fit_lorentz=False, 
                           output_file_prefix=common_file_prefix)
        file_numbers=[]
        j=0
        dataset=self.measurement[self.index_mess]
        for i, attachedset in enumerate(dataset.plot_together):
          file_numbers.append(str(j)+'-'+str(i))
          if  getattr(attachedset, 'is_matrix_data', False):
            attachedset.export_matrix(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.bin'))
          else:
            attachedset.export(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.out'))
        if dataset.zdata>=0 and measurement_data_plotting.maps_with_projection:
          # export data of projections
          projections_name=os.path.join(common_folder, common_file_prefix+str(0)+'-'+str(0)+'.xy')
          dataset.export_projections(projections_name)    
      write_file=open(os.path.join(common_folder, common_file_prefix+'.gp'), 'w')
      write_file.write(plot_text+'\n')
      write_file.close()
      if pic_box.get_active():
        proc=subprocess.Popen([self.active_session.GNUPLOT_COMMAND, 
                         common_file_prefix+'.gp'], 
                        shell=gnuplot_preferences.EMMULATE_SHELL, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        stdin=subprocess.PIPE, 
                        cwd=common_folder
                        )
      #----------------File selection dialog-------------------#      
    elif action.get_name()=='ExportAll':
      self.export_all()
    elif self.active_multiplot:
      for plotlist in self.multiplot:
        if not self.measurement[self.index_mess] in [item[0] for item in plotlist]:
          continue
        multi_file_name=plotlist[0][1] + '_multi_'+ plotlist[0][0].number + '.' + self.set_file_type
        if action.get_name()=='ExportAs':
          #++++++++++++++++File selection dialog+++++++++++++++++++#
          file_dialog=ExportFileChooserDialog(self.active_session.picture_width, 
                                            self.active_session.picture_height, 
                                            title='Export multi-plot as...')
          file_dialog.set_default_response(gtk.RESPONSE_OK)
          file_dialog.set_current_name(os.path.split(plotlist[0][1] + '_multi_'+ \
                                       plotlist[0][0].number + '.' + self.set_file_type)[1])
          file_dialog.set_current_folder(self.active_folder)
          # create the filters in the file selection dialog
          filter = gtk.FileFilter()
          filter.set_name("Images (png/ps)")
          filter.add_mime_type("image/png")
          filter.add_mime_type("image/ps")
          filter.add_pattern("*.png")
          filter.add_pattern("*.ps")
          file_dialog.add_filter(filter)
          filter = gtk.FileFilter()
          filter.set_name("All files")
          filter.add_pattern("*")
          file_dialog.add_filter(filter)
          response = file_dialog.run()
          if response == gtk.RESPONSE_OK:
            self.active_folder=file_dialog.get_current_folder()
            self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
            multi_file_name=unicode(file_dialog.get_filename(), 'utf-8')
          file_dialog.destroy()
          if response != gtk.RESPONSE_OK:
            return
          #----------------File selection dialog-------------------#
        self.last_plot_text=self.plot(self.active_session, 
                                      [item[0] for item in plotlist], 
                                      plotlist[0][1], 
                                      #plotlist[0][0].short_info, 
                                      plotlist.title, 
                                      [item[0].short_info for item in plotlist], 
                                      errorbars,
                                      multi_file_name,
                                      fit_lorentz=False, 
                                      sample_name=plotlist.sample_name)     
        # give user information in Statusbar
        self.reset_statusbar()
        print 'Export multi-plot ' + multi_file_name + '... Done!'
    else:
      new_name=output_file_name
      if action.get_name()=='ExportAs':
        #++++++++++++++++File selection dialog+++++++++++++++++++#
        file_dialog=ExportFileChooserDialog(self.active_session.picture_width, 
                                            self.active_session.picture_height, 
                                            title='Export plot as...')
        file_dialog.set_default_response(gtk.RESPONSE_OK)
        file_dialog.set_current_name(os.path.split(
                      self.input_file_name+'_'+ self.measurement[self.index_mess].number+'.'+self.set_file_type)[1])
        file_dialog.set_current_folder(self.active_folder)
        filter = gtk.FileFilter()
        filter.set_name("Images (png/ps)")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/ps")
        filter.add_pattern("*.png")
        filter.add_pattern("*.ps")
        file_dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        file_dialog.add_filter(filter)
        # get hbox widget for the entries
        file_dialog.show_all()
        response = file_dialog.run()
        if response == gtk.RESPONSE_OK:
          self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
          self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
          new_name=unicode(file_dialog.get_filename(), 'utf-8')
        elif response == gtk.RESPONSE_CANCEL:
          file_dialog.destroy()
          return False
        file_dialog.destroy()
        #----------------File selection dialog-------------------#
      self.last_plot_text=self.plot(self.active_session, 
                                    [self.measurement[self.index_mess]], 
                                    self.input_file_name, 
                                    self.measurement[self.index_mess].short_info,
                                    [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                    errorbars,
                                    new_name,
                                    fit_lorentz=False)
      self.reset_statusbar()
      print 'Export plot number '+self.measurement[self.index_mess].number+'... Done!'

  def export_all(self):
    '''
      Open a Dialog to select which Plots to export with additional options.
    '''
    # Dialog to select the destination folder
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=ExportFileChooserDialog(self.active_session.picture_width, 
                                        self.active_session.picture_height, 
                                        title='Select Destination Folder...', 
                                        action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, 
                                        buttons=(gtk.STOCK_OK, 
                                                 gtk.RESPONSE_OK, 
                                                 gtk.STOCK_CANCEL, 
                                                 gtk.RESPONSE_CANCEL
                                                 ))
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    file_dialog.set_current_folder(self.active_folder)
    file_dialog.show_all()
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
      self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
    else:
      file_dialog.destroy()
      return
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    # Dialog to select which plots to export
    selection_dialog=PreviewDialog(self.active_session.file_data, 
                                   buttons=('Export', 1, 'Cancel', 0))
    selection_dialog.set_default_size(800, 600)
    table=gtk.Table(2, 1, False)
    naming_entry=gtk.Entry()
    naming_entry.set_text('[name]_[nr].png')
    naming_entry.set_width_chars(20)
    naming_entry.connect('activate', lambda *ignore: selection_dialog.response(1))
    table.attach(naming_entry, 
              # X direction #          # Y direction
              0, 1,                      0, 1,
              0,                       0,
              0,                         0)
    description=gtk.Label("""      [name] \t- Name of the import file
      [sample]\t- left entry above the plot
      [title_add]\t- right entry above the plot
      [nr]\t\t- Number of the plot""")
    table.attach(description, 
              # X direction #          # Y direction
              1, 2,                      0, 1,
              0,                       0,
              0,                         0)
    table.show_all()
    selection_dialog.vbox.pack_end(table, False)
    selection_dialog.set_preview_parameters(self.plot, self.active_session, 
                                            self.active_session.TEMP_DIR+'plot_temp.png')
    if selection_dialog.run()==1:
      selection_dialog.hide()
      naming_text=naming_entry.get_text()
      for i, item in enumerate(selection_dialog.get_active_objects_with_key()):
        file_name, dataset=item
        file_name_raw=os.path.split(file_name)[1]
        naming=naming_text.replace('[name]', file_name_raw)
        self.last_plot_text=self.plot(self.active_session, 
                                      dataset.plot_together,
                                      file_name,
                                      dataset.short_info,
                                      [object.short_info for object in dataset.plot_together],
                                      errorbars,
                                      os.path.join(self.active_folder, naming), 
                                      fit_lorentz=False)
        self.reset_statusbar()
        print 'Export plot number %2i...' % i
      print 'Export Done!'
    selection_dialog.destroy()

  def print_plot(self,action): 
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
    entry.connect('activate', lambda *ignore: dialog.response(1))
    result=dialog.run()
    print_command=entry.get_text()
    dialog.destroy()
    if result!=1:
      return
    PRINT_COMMAND=print_command
    if action.get_name()=='Print':
      term='postscript landscape enhanced colour'
      self.last_plot_text=self.plot(self.active_session, 
                                    [self.measurement[self.index_mess]],
                                    self.input_file_name, 
                                    self.measurement[self.index_mess].short_info,
                                    [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                    errorbars, 
                                    output_file=self.active_session.TEMP_DIR+'plot_temp.ps',
                                    fit_lorentz=False)
      print 'Printing with: '+(print_command % self.active_session.TEMP_DIR+'plot_temp.ps')
      subprocess.call((print_command % self.active_session.TEMP_DIR+'plot_temp.ps').split())
    elif action.get_name()=='PrintAll':
      term='postscript landscape enhanced colour'
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
      print_string=''
      combined_file=open(self.active_session.TEMP_DIR+'plot_temp.ps', 'w')      
      for i, dataset in enumerate(plot_list): # combine all plot files in one print statement
        self.last_plot_text=self.plot(self.active_session, 
                                      [dataset],
                                      self.input_file_name,
                                      dataset.short_info,
                                      [object.short_info for object in dataset.plot_together],
                                      errorbars, 
                                      output_file=self.active_session.TEMP_DIR+'plot_temp_%i.ps' % i,
                                      fit_lorentz=False)
        # combine the documents into one postscript file
        if i>0:
          combined_file.write('false 0 startjob pop\n')
        combined_file.write(open(self.active_session.TEMP_DIR+('plot_temp_%i.ps' % i), 'r').read())
        
      combined_file.close()
      print 'Printing with: ' + print_command % self.active_session.TEMP_DIR+'plot_temp.ps'
      subprocess.call((print_command % self.active_session.TEMP_DIR+'plot_temp.ps').split())

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
        for plotlist in self.multiplot:
          itemlist=[item[0] for item in plotlist]
          if self.measurement[self.index_mess] in itemlist:
            PrintDatasetDialog(plotlist, self, multiplot=True)
      else:
        measurements=[self.measurement[self.index_mess]]
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
      buffer=text.get_buffer()
      makro_text=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
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
    sw = gtk.ScrolledWindow()
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

  def open_ipy_console(self, action=None, commands=[], show_greetings=True):
    '''
      In debug mode this opens a window with an IPython console,
      which has direct access to all important objects.
    '''
    from ipython_view import IPythonView, MenuWrapper, FitWrapper
    import measurement_data_structure
    import pango
    import sys
    import numpy
    try:
      import scipy
    except ImportError:
      scipy=None
    from copy import deepcopy
    from glob import glob
    from fit_data import register_function
    import IPython.ipapi
    
    if getattr(self, 'active_ipython', False):
      # if there is already an ipython console, show it and exit
      self.active_ipython.deiconify()
      self.active_ipython.present()
      return

    FONT = "Mono 8"
    oldstd=[sys.stdout, sys.stderr]

    ipython_dialog= gtk.Dialog(title="Plotting GUI - IPython Console")
    self.active_ipython=ipython_dialog
    if 'IPython' in self.config_object:
      ipython_dialog.set_default_size(*self.config_object['IPython']['size'])
      ipython_dialog.move(*self.config_object['IPython']['position'])
      if self.config_object['IPython']['size'][0]<700:
        show_greetings=False
    else:
      ipython_dialog.set_default_size(750,600)
    ipython_dialog.set_resizable(True)
    ipython_dialog.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logoyellow.png").replace('library.zip', ''))
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
    greeting="""    This is an interactive IPython session with direct access to the program.
    You have the whole python functionality and can interact with the programs objects.
    You can use tab-completion and inspect any object (get help) by writing "object?".

    Functions:
      replot \tFunction to replot the dataset
      dataset \tFunction to get the active MeasurementData object
      getxyz/\tReturn 3/all PhysicalProperty instances of the x,y and z columns 
        getall\tfrom the active dataset
      newxyz/ \tCreate a new plot with changed columns, takes three/several lists or 
        newall\tarrays as input. For line plots the last parameter is 'None'.
      mapdata \tApply a function to all datasets in the active file data
      mapall  \tApply a function to all datasets from all files
      newfit  \tAdd a function to the fit dialog functions, should be defined as
              \tither f(p,x) of f(p,x,y) for 2d or 3d datasets respectively.
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
      menus   \tAccess all GUI menus as properties of this object, e.g. "menus.File.Open_File()".
      action_history \tList of macros activated through the GUI (key, (parameters)).
    Modules:
      np \tNumpy
      sp \tScipy
      mds \tMeasurement_data_strunctur module with PhysicalProperty, MeasurementData
          \tand other data treatment Classes.\n"""
    if show_greetings:
      ipview = IPythonView(greeting)
    else:
      ipview = IPythonView('')
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
    ip=IPython.ipapi.get()
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
    def newxyz(x, y, z=None, sample_name=None, ):
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
                       'newfit': register_function, 
                       'makefit': FitWrapper(self, self.active_session), 
                       })
    # add common mathematic functions to the namespace
    math_functions=['exp','log', 'log10', 'pi', 
                    'sin', 'cos', 'tan', 'arcsin',  'arccos', 'arctan', 'sinh', 'cosh', 'tanh', 
                    'sqrt', 'abs']
    ipview.updateNamespace(dict([(item, getattr(numpy, item, None)) for item in math_functions]))
    if hasattr(self, 'ipython_user_namespace'):
      # reload namespace of an earlier session
      ipview.updateNamespace(self.ipython_user_namespace)
      ipview.IP.user_ns['In']+=self.ipython_user_history
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
    del(ipview.IP.alias_table['ls'])
    if 'cat' in ipview.IP.alias_table:
      del(ipview.IP.alias_table['cat'])
    def _ls_new(self, arg):
      ip = self.api
      if arg=='':
        arg='*'
      ip.ex("from glob import glob; last_ls=glob('%s'); print 'last_ls=',last_ls" % arg)
    def _cat_new(self, arg):
      ip = self.api
      if arg=='':
        ip.ex("print 'No file supplied.'")
      ip.ex("print open('%s','r').read()" % arg)
    ip.expose_magic('ls',_ls_new)
    ip.expose_magic('cat',_cat_new)

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

  def open_dataview_dialog(self, action):
    '''
      Open a Dialog with the data of the current plot, which can also be edited.
    '''
    dataset=self.measurement[self.index_mess]
    unchanged_dataset=deepcopy(dataset)
    dialog=DataView(dataset, buttons=('Replot', 1, 'Revert Changes', -1, 'Close', 0))
    dialog.set_default_size(800, 800)
    dialog.show()
    self.open_windows.append(dialog)
    dialog.connect('response', self.dataview_response, unchanged_dataset)
  
  def dataview_response(self, widget, id, unchanged_dataset):
    '''
      Button on dataview pressed.
    '''
    if id==0:
      widget.destroy()
    elif id==-1:
      self.measurement[self.index_mess]=unchanged_dataset
      self.replot()
      widget.dataset=deepcopy(unchanged_dataset)
      widget.add_data()
    else:
      self.replot()

  #--------------------------Menu/Toolbar Events---------------------------------#

  #----------------------------------Event hanling---------------------------------------#

  #+++++++++++++++++++++++++++Functions for initializing etc+++++++++++++++++++++++++++++#

  def read_config_file(self):
    '''
      Read the options that have been stored in a config file in an earlier session.
      The ConfigObj python module is used to save the settings in an .ini file
      as this is an easy way to store dictionaries.
      
      @return If the import was successful.
    '''
    # create the object with association to an inifile in the user folder
    # have to test if this works under windows
    try:
      self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotting_gui/config.ini', unrepr=True)
    except:
      # If the file is corrupted or with old format (without unrepr) rename it and create a new one
      print 'Corrupted .ini file, renaming it to config.bak.'
      os.rename(os.path.expanduser('~')+'/.plotting_gui/config.ini', os.path.expanduser('~')+'/.plotting_gui/config.bak')
      self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotting_gui/config.ini', unrepr=True)
    self.config_object.indent_type='\t'
    # If the inifile exists import the profiles but override default profile.
    try:
      self.profiles={'default': PlotProfile('default')}
      self.profiles['default'].save(self)
      for name in self.config_object['profiles'].items():
        self.profiles[name[0]]=PlotProfile(name[0])
        self.profiles[name[0]].read(self.config_object['profiles'])
    except KeyError:
      # create a new object if the file did not exist.
      self.config_object['profiles']={}
      self.profiles={'default': PlotProfile('default')}
      self.profiles['default'].save(self)
    if not 'plot_tree' in self.config_object:    
      self.config_object['plot_tree']={
                                       'shown': True, 
                                       'size': (350, 500), 
                                       'position': (0, 0), 
                                       }
    return True

  def read_window_config(self):
    '''
      Read the window config parameters from the ConfigObj.
    '''
    try:
      x, y=self.config_object['Window']['position']
      width, height=self.config_object['Window']['size']
      # Set the main window size to default or the last settings saved in config file
      self.set_default_size(width, height)
      self.move(x, y)
      if 'MouseMode' in self.config_object:
        self.mouse_mode=self.config_object['MouseMode']['active']
    except KeyError:
      self.set_default_size(700, 600)
      # ConfigObj Window parameters
      self.config_object['Window']={
                                    'size': (700, 600), 
                                    'position': self.get_position(), 
                                    }

  def check_for_update_now(self):
    '''
      Read the wiki download area page to see, if there is a new version available.
      
      @return Newer version number or None
    '''
    import socket
    import urllib
    # Open the wikipage, timeout if server is offline
    socket.setdefaulttimeout(3)
    # Download the update information and run the installation
    try:
      download_page=urllib.urlopen(DOWNLOAD_PAGE_URL)
    except IOError, ertext:
      print 'Error accessing update server: %s' % ertext
      return None
    script_data=download_page.read()
    exec(script_data)
    if self.config_object['Update']['CheckBeta']:
      if __version__ != BETA_HISTORY[-1]:
        dialog=gtk.MessageDialog(parent=self, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_OK_CANCEL , 
          message_format="There is a new version (%s) ready to download. Do you want to install it?" % (BETA_HISTORY[-1]))
        result=dialog.run()
        dialog.destroy()
        if result==gtk.RESPONSE_OK:
          # run update function defined on the webpage
          perform_update_gtk(__version__, BETA_HISTORY[-1])
      else:
        print "Softwar is up to date."
    else:
      if __version__ != VERSION_HISTORY[-1]:
        dialog=gtk.MessageDialog(parent=self, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_OK_CANCEL , 
          message_format="There is a new version (%s) ready to download. Do you want to install it?" % (BETA_HISTORY[-1]))
        result=dialog.run()
        dialog.destroy()
        if result==gtk.RESPONSE_OK:
          # run update function defined on the webpage
          perform_update_gtk(__version__, VERSION_HISTORY[-1])        
      else:
        print "Softwar is up to date."

  def check_for_updates(self):
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
    if self.config_object['Update']['Check'] and time()>self.config_object['Update']['NextCheck']:
      print "Checking for new Version."
      self.config_object['Update']['NextCheck']=time()+24.*60.*60
      new_version=self.check_for_update_now()  
  #---------------------------Functions for initializing etc-----------------------------#

  #++++++++++++++Functions for displaying graphs plotting and status infos+++++++++++++++#

  def set_image(self):
    '''
      Show the image created by gnuplot.
    '''
    # in windows we have to wait for the picture to be written to disk
    if self.active_session.OPERATING_SYSTEM=='windows':
      sleep(0.05)
      for i in range(100):
        if os.path.exists(self.active_session.TEMP_DIR + 'plot_temp.png'):
          if os.path.getsize(self.active_session.TEMP_DIR + 'plot_temp.png') > 1000:
            break
          sleep(0.1)
        else:
          sleep(0.1)
      if os.path.getsize(self.active_session.TEMP_DIR + 'plot_temp.png') < 1000:
        # if this was not successful stop trying.
        return False
    # TODO: errorhandling
    self.image_pixbuf=gtk.gdk.pixbuf_new_from_file(self.active_session.TEMP_DIR + 'plot_temp.png')
    s_alloc=self.image.get_allocation()
    pixbuf=self.image_pixbuf.scale_simple(s_alloc.width, s_alloc.height, gtk.gdk.INTERP_BILINEAR)
    if self.mouse_mode and self.measurement[self.index_mess].zdata>=0:
      try:
        # estimate the size of the plot by searching for lines with low pixel intensity (Black)
        original_filters = warnings.filters[:]
        # Ignore warnings.
        warnings.simplefilter("ignore")
        try:
          pixbuf_data=pixbuf.get_pixels_array()[:,:,:3]
        except RuntimeError:
          # not working at the moment
          raise RuntimeError
          # get raw pixel data
          pixels=pixbuf.get_pixels()
          pixbuf_data=numpy.fromstring(pixels, numpy.uint8)
          pixbuf_data=pixbuf_data.reshape(pixbuf.get_rowstride(), len(pixbuf_data)/pixbuf.get_rowstride())
          # create 2d array
          pixbuf_data=pixbuf_data[:pixbuf.get_width()*3,:pixbuf.get_height()]
          # create 3d color array
          pixbuf_data=pixbuf_data.transpose().reshape(len(pixbuf_data[0]), len(pixbuf_data)/3, 3)
          self.pixbuf_data=pixbuf_data
        warnings.filters=original_filters
        black_values=(numpy.mean(pixbuf_data, axis=2)==0.)
        # as first step get the region inside all captions including colorbar
        ysum=numpy.sum(black_values, axis=0)*1.
        xsum=numpy.sum(black_values, axis=1)*1.
        xsum/=float(len(ysum))
        ysum/=float(len(xsum))
        yids=numpy.where(xsum>xsum.max()*0.9)[0]
        xids=numpy.where(ysum>ysum.max()*0.9)[0]
        x0=float(xids[0])
        x1=float(xids[-1])
        y0=float(yids[0])
        y1=float(yids[-1])
        if not measurement_data_plotting.maps_with_projection:
          # try to remove the colorbar from the region
          whith_values_inside=(numpy.mean(pixbuf_data[int(y0):int(y1), int(x0):int(x1)], axis=2)==255.)
          ysum2=numpy.sum(whith_values_inside, axis=0)*1.
          ysum2/=float(y1-y0)
          xids=numpy.where(ysum2==1.)[0]
          x1=float(xids[0]+x0-1)
        x0/=len(ysum)
        x1/=len(ysum)
        y0/=len(xsum)
        y1/=len(xsum)
        self.mouse_data_range=((x0, x1-x0, 1.-y1, y1-y0), self.mouse_data_range[1])
      except:
        self.mouse_data_range=((0., 0., 0., 0.), self.mouse_data_range[1])
    self.image.set_from_pixbuf(pixbuf)
    return True

  def image_resize(self, widget, rectangel):
    '''
      Scale the image during a resize.
    '''
    if self.image_do_resize and not self.active_zoom_from and not self.active_fit_selection_from and self.mouse_arrow_starting_point is None:
      self.image_do_resize=False
      try:
        # if no image was set, there is not self.image_pixbuf
        pixbuf=self.image_pixbuf.scale_simple(rectangel.width, rectangel.height, gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
      except AttributeError:
        pass
    else:
      self.image_do_resize=True
  
  def catch_mouse_position(self, widget, action):
    '''
      Get the current mouse position when the pointer was mooved on to of the image.
    '''
    if not self.mouse_mode:
      return
    position=self.get_position_on_plot()
    if position is not None:
      if self.active_zoom_from is not None:
        # When a zoom drag is active draw a rectangle on the image
        self.active_zoom_last_inside=position
        az=self.active_zoom_from
        self.image_pixmap.draw_rectangle( self.get_style().black_gc, False, min(az[4], position[4]), 
                                                                            min(az[5], position[5]), 
                                         abs(position[4]-az[4]), abs(position[5]-az[5]))
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Zoom: x1=%6g  \ty1=%6g \t x2=%6g \ty2=%6g' % (az[0], az[1], position[0], position[1]))
        i=0
        while gtk.events_pending() and i<10:
          gtk.main_iteration(False)
          i+=1
        self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
      elif self.active_fit_selection_from is not None:
        # When a drag is active draw a rectangle on the image
        af=self.active_fit_selection_from
        self.image_pixmap.draw_rectangle( self.get_style().black_gc, False, min(af[4], position[4]), 
                                                                            min(af[5], position[5]), 
                                         abs(position[4]-af[4]), abs(position[5]-af[5]))
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Fit-region: x1=%6g  \ty1=%6g \t x2=%6g \ty2=%6g' % (af[0], af[1], position[0], position[1]))
        i=0
        while gtk.events_pending() and i<10:
          gtk.main_iteration(False)
          i+=1
        self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
      elif self.mouse_arrow_starting_point is not None:
        # if an arrow drag is active show a different status and draw a line from the starting
        # point to the active mouse position
        ma=self.mouse_arrow_starting_point
        self.image_pixmap.draw_line( self.get_style().black_gc, ma[4], ma[5], position[4], position[5] )
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Draw Arrow: x=%6g  \ty=%6g \t-> \tx=%6g \ty=%6g' % (ma[0], ma[1], position[0], position[1]))
        i=0
        while gtk.events_pending() and i<10:
          gtk.main_iteration(False)
          i+=1
        self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
      else:
        # show the position of the cusor on the plot
        info='x=%6g  \ty=%6g' % (position[0], position[1])
        if action.state.value_names==['GDK_CONTROL_MASK'] and self.measurement[self.index_mess].zdata<0:
          info+='\t\tFit peak with gaussian (left), voigt (middle) or lorentzian (right) profile.'
        elif action.state.value_names==['GDK_SHIFT_MASK']:
          info+='\t\tPlace label (left), draw arrow (middle) or label position (right).'
        else:
          if self.measurement[self.index_mess].zdata>=0:
            info+='\t\tZoom (right), unzoom (middle). <shift>-label/arrow'
          else:
            info+='\t\tZoom (right), unzoom (middle). <ctrl>-fit / <shift>-label/arrow'
        self.statusbar.push(0, info)
      try:
        # if the cusor is inside the plot we change it's icon to a crosshair
        self.image.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSSHAIR))
      except AttributeError:
        # catch an example when event is triggered after window got closed
        pass
    else:
      try:
        # reset the mouse icon
        self.image.window.set_cursor(None)
      except AttributeError:
        # catch an example when event is triggered after window got closed
        pass
  
  def mouse_press(self, widget, action):
    '''
      Catch mouse press event on image.
    '''
    if not self.mouse_mode:
      return
    position=self.get_position_on_plot()
    if 'GDK_CONTROL_MASK' in action.state.value_names and self.measurement[self.index_mess].zdata<0:
      # control was pressed during button press
      # fit a peak function to the active mouse position
      if position is not None:
        self.active_fit_selection_from=position
        self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
      else:
        self.active_fit_selection_from=None
    elif not 'GDK_SHIFT_MASK' in action.state.value_names:
      # no control/alt/shift button is pressed
      if action.button==3:
        # Zoom into region
        if position is not None:
          self.active_zoom_from=position
          self.active_zoom_last_inside=position
          self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
        else:
          self.active_zoom_from=None
      if action.button==1 and position is not None and self.mouse_position_callback is not None:
        # activate a function registered as callback
        self.mouse_position_callback(position)
      if action.button==2:
        # unzoom the plot
        self.measurement[self.index_mess].plot_options.xrange=[None, None]
        self.measurement[self.index_mess].plot_options.yrange=[None, None]
        self.x_range_in.set_text('')
        self.y_range_in.set_text('')
        self.replot()
    else:
      # shift pressed during button press leads to label or arrow
      # to be added to the plot
      if position is not None:
        ds=self.measurement[self.index_mess]
        if action.button==1:
          dialog=SimpleEntryDialog
          parameters, result=SimpleEntryDialog('Enter Label...', 
                                         [('Text', 'Label', str)]
                                         ).run()
          if result:
            ds.plot_options+='set label "%s" at %g,%g,1. front\n' % (parameters['Text'], position[0], position[1])
        if action.button==2:
          self.mouse_arrow_starting_point=position
          self.image_pixmap, self.image_mask= self.image_pixbuf.render_pixmap_and_mask()
        if action.button==3:
          dialog=SimpleEntryDialog
          parameters, result=SimpleEntryDialog('Enter Label...', 
                                         [('Text', '(%g,%g)' % (position[0], position[1]), str)]
                                         ).run()
          if result:
            ds.plot_options+='set label "%s" at %g,%g,1. point pt 6 front\n' % (parameters['Text'], position[0], position[1])
        self.replot()
          
  
  def mouse_release(self, widget, action):
    '''
      Catch mouse release event.
    '''
    position=self.get_position_on_plot()
    if self.active_zoom_from is not None:
      # Zoom in to the selected Area
      if position is None or abs(position[2]-self.active_zoom_from[2])<0.1 and abs(position[3]-self.active_zoom_from[3])<0.1:
        # if mouse is outside the ploted region, use the last position where it was inside
        position=self.active_zoom_last_inside
      dsp=self.measurement[self.index_mess].plot_options
      x0=min(position[0], self.active_zoom_from[0])
      x1=max(position[0], self.active_zoom_from[0])
      y0=min(position[1], self.active_zoom_from[1])
      y1=max(position[1], self.active_zoom_from[1])
      dsp.xrange=[x0, x1]
      dsp.yrange=[y0, y1]
      self.active_zoom_from=None
      self.replot()
    if self.mouse_arrow_starting_point is not None:
      # draw an arrow in the plot
      start=self.mouse_arrow_starting_point
      self.mouse_arrow_starting_point=None
      if position is not None:
        self.measurement[self.index_mess].plot_options+='set arrow from %g,%g,1. to %g,%g,1. front\n' % (start[0], start[1], position[0], position[1])
        self.replot()
    if self.active_fit_selection_from is not None:
      start=self.active_fit_selection_from
      self.active_fit_selection_from=None
      if position is None:
        return
      ds=self.measurement[self.index_mess]
      if ds.zdata>=0:
        return
      if (abs(start[2]-position[2])+abs(start[3]-position[3]))<0.03:
        # Position was only clicked
        width=(ds.x.max()-ds.x.min())/10.
        start_range=None
        end_range=None
        x_0=position[0]
        I=position[1]
        bg=0.
      else:
        # Position was dragged, define a range of plotting
        width=abs(position[0]-start[0])/4.
        start_range=min(position[0], start[0])
        end_range=max(position[0], start[0])
        x_0=(end_range-start_range)/2.+start_range
        I=abs(position[1]-start[1])/4.
        bg=min(position[1], start[1])
      if (ds.fit_object==None):
        self.file_actions.activate_action('create_fit_object')
      import fit_data
      if action.button==1:
        gaussian=fit_data.FitGaussian([ I, x_0, width, bg])
        gaussian.x_from=start_range
        gaussian.x_to=end_range
        gaussian.refine(ds.x, ds.y)
        ds.fit_object.functions.append([gaussian, False, True, False, False])
      if action.button==2:
        voigt=fit_data.FitVoigt([ I, x_0, width/2., width/2.,  bg])
        voigt.x_from=start_range
        voigt.x_to=end_range
        voigt.refine(ds.x, ds.y)
        ds.fit_object.functions.append([voigt, False, True, False, False])
      if action.button==3:
        lorentz=fit_data.FitLorentzian([ I, x_0, width, bg])
        lorentz.x_from=start_range
        lorentz.x_to=end_range
        lorentz.refine(ds.x, ds.y)
        ds.fit_object.functions.append([lorentz, False, True, False, False])
      self.file_actions.activate_action('simmulate_functions')
      self.replot()
  
  def get_position_on_plot(self):
    '''
      Calculate the position of the mouse cursor on the plot. If the cursor
      is outside, return None.
    '''
    position=self.image.get_pointer()
    img_size=self.image.get_allocation()
    img_width=float(img_size[2]-img_size[0])
    img_height=float(img_size[3]-img_size[1])
    mr, pr=self.mouse_data_range
    if mr[1]==0. or mr[3]==0.:
      return None
    mouse_x=position[0]/float(img_size.width)
    mouse_x-=mr[0]
    mouse_x/=mr[1]
    mouse_y=1.-position[1]/float(img_size.height)
    mouse_y-=mr[2]
    mouse_y/=mr[3]      
    if not (mouse_x>=0. and mouse_x<=1. and mouse_y>=0. and mouse_y<=1.):
      return None
    if pr[4]:
      x_position=10.**(mouse_x*(numpy.log10(pr[1])-numpy.log10(pr[0]))+numpy.log10(pr[0]))
    else:
      x_position=(pr[1]-pr[0])*mouse_x+pr[0]
    if pr[5]:
      y_position=10.**(mouse_y*(numpy.log10(pr[3])-numpy.log10(pr[2]))+numpy.log10(pr[2]))
    else:
      y_position=(pr[3]-pr[2])*mouse_y+pr[2]
    return x_position, y_position, mouse_x, mouse_y, position[0], position[1]
  
  def toggle_mouse_mode(self, action=None):
    '''
      Activate/Deactivate cursor mode.
    '''
    self.mouse_mode=not self.mouse_mode
    self.replot()
  
  def initialize_gnuplot(self):
    '''
      Check gnuplot version for capabilities.
    '''
    self.gnuplot_initialized=True
    gnuplot_version=measurement_data_plotting.check_gnuplot_version(self.active_session)
    if gnuplot_version[0]<4.4:
      # mouse mode only works with version 4.4 and higher
      self.mouse_mode=False
    elif not sys.platform == 'darwin':
      gnuplot_preferences.set_output_terminal_png=gnuplot_preferences.set_output_terminal_pngcairo

  def splot(self, session, datasets, file_name_prefix, title, names, 
            with_errorbars, output_file=gnuplot_preferences.output_file_name, 
            fit_lorentz=False, sample_name=None, show_persistent=False):
    '''
      Plot via script file instead of using python gnuplot pipeing.
      
      @return Gnuplot error messages, which have been reported
    '''
    if not self.gnuplot_initialized:
      self.initialize_gnuplot()
    try:
      output, variables= measurement_data_plotting.gnuplot_plot_script(session, 
                                                         datasets,
                                                         file_name_prefix, 
                                                         self.script_suf, 
                                                         title,
                                                         names,
                                                         with_errorbars,
                                                         output_file,
                                                         fit_lorentz=False, 
                                                         sample_name=sample_name, 
                                                         show_persistent=show_persistent, 
                                                         get_xy_ranges=self.mouse_mode)
    except RuntimeError:
      print "Gnuplot instance lost, try to restart ..."
      # gnuplot instance was somehow killed, try to restart
      self.active_session.initialize_gnuplot()
      return self.splot(session, datasets, file_name_prefix, title, names, 
            with_errorbars, output_file, fit_lorentz, sample_name, show_persistent)
    if output=='' and variables is not None and len(variables)==8:
      img_size=self.image.get_allocation()
      mr_x=variables[0]/img_size.width
      mr_width=(variables[1]-variables[0])/img_size.width
      mr_height=(variables[3]-variables[2])/img_size.height
      mr_y=(variables[3])/img_size.height-mr_height
      self.mouse_data_range=((mr_x, mr_width, mr_y, mr_height), variables[4:]+[
                                          self.measurement[self.index_mess].logx, 
                                          self.measurement[self.index_mess].logy])    
    return output

  def plot_persistent(self, action=None):
    '''
      Open a persistent gnuplot window.
    '''
    global errorbars
    i=0
    if self.active_multiplot:
      for plotlist in self.multiplot:
        itemlist=[item[0] for item in plotlist]
        if self.measurement[self.index_mess] in itemlist:
          self.last_plot_text=self.plot(self.active_session,
                                        [item[0] for item in plotlist],
                                        plotlist[0][1],
                                        #plotlist[0][0].short_info,
                                        plotlist.title, 
                                        [item[0].short_info for item in plotlist],
                                        errorbars,
                                        self.active_session.TEMP_DIR+'plot_temp.png',
                                        fit_lorentz=False, 
                                        sample_name=plotlist.sample_name, 
                                        show_persistent=True)
    else:
      self.label.set_width_chars(min(len(self.measurement[self.index_mess].sample_name)+5, 
                                                          40))
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(min(len(self.measurement[self.index_mess].short_info)+5, 
                                                           40))
      self.label2.set_text(self.measurement[self.index_mess].short_info)
      self.last_plot_text=self.plot(self.active_session,
                                  [self.measurement[self.index_mess]],
                                  self.input_file_name,
                                  self.measurement[self.index_mess].short_info,
                                  [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                  errorbars, 
                                  output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                  fit_lorentz=False, 
                                  show_persistent=True)
    if self.last_plot_text!='':
      print 'Gnuplot error!'
      self.show_last_plot_params(None)

  def toggle_plotfit(self, action):
    ds=self.measurement[self.index_mess]
    if ds.plot_together_zindex==-1:
      ds.plot_together_zindex=0
    elif action.get_name()=='TogglePlotFit':
      ds.plot_together_zindex=-1
    else:
      ds.plot_together_zindex+=1
      if ds.plot_together_zindex==len(ds.plot_together):
        ds.plot_together_zindex=0
    self.replot()

  def replot(self):
    '''
      Recreate the current plot and clear the statusbar.
    '''
    global errorbars
    # change label and plot other picture
    self.show_add_info(None)
    # set log checkbox according to active measurement
    logitems=self.measurement[self.index_mess]
    if self.active_multiplot:
      for mp in self.multiplot:
        for mpi, mpname in mp:
          if self.measurement[self.index_mess] is mpi:
            logitems=mp[0][0]
    else:
      options=self.measurement[self.index_mess].plot_options
      # If the dataset has ranges but the input settings are empty, fill them
      if (self.x_range_in.get_text()=="") and ((options.xrange[0] is not None) or (options.xrange[1] is not None)):
        range=str(options.xrange[0])+':'+str(options.xrange[1])
        self.x_range_in.set_text(range.replace('None', ''))
      if (self.y_range_in.get_text()=="") and ((options.yrange[0] is not None) or (options.yrange[1] is not None)):
        range=str(options.yrange[0])+':'+str(options.yrange[1])
        self.y_range_in.set_text(range.replace('None', ''))
      if (self.z_range_in.get_text()=="") and ((options.zrange[0] is not None) or (options.zrange[1] is not None)):
        range=str(options.zrange[0])+':'+str(options.zrange[1])
        self.z_range_in.set_text(range.replace('None', ''))
    self.logx.set_active(logitems.logx)
    self.logy.set_active(logitems.logy)
    self.logz.set_active(logitems.logz)
    
    # wait for all gtk events to finish to get the right size
    print "Plotting"
    i=0
    while gtk.events_pending() and i<10:
      gtk.main_iteration(False)
      i+=1
    self.frame1.set_current_page(0)
    self.active_session.picture_width=str(self.image.get_allocation().width)
    self.active_session.picture_height=str(self.image.get_allocation().height)
    if self.active_multiplot:
      for plotlist in self.multiplot:
        itemlist=[item[0] for item in plotlist]
        if self.measurement[self.index_mess] in itemlist:
          self.last_plot_text=self.plot(self.active_session,
                                        [item[0] for item in plotlist],
                                        plotlist[0][1],
                                        #plotlist[0][0].short_info,
                                        plotlist.title, 
                                        [item[0].short_info for item in plotlist],
                                        errorbars,
                                        self.active_session.TEMP_DIR+'plot_temp.png',
                                        fit_lorentz=False, 
                                        sample_name=plotlist.sample_name)
          self.label.set_width_chars(min(len(plotlist.sample_name)+5, 
                                         40))
          self.label.set_text(plotlist.sample_name)
          self.label2.set_width_chars(min(len(plotlist.title)+5, 
                                          40))
          self.label2.set_text(plotlist.title)
    else:
      self.label.set_width_chars(min(len(self.measurement[self.index_mess].sample_name)+5, 
                                                          40))
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(min(len(self.measurement[self.index_mess].short_info)+5, 
                                                           40))
      self.label2.set_text(self.measurement[self.index_mess].short_info)
      self.last_plot_text=self.plot(self.active_session,
                                  [self.measurement[self.index_mess]],
                                  self.input_file_name,
                                  self.measurement[self.index_mess].short_info,
                                  [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                  errorbars, 
                                  output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                  fit_lorentz=False)
    if self.last_plot_text!='':
      self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
      self.active_plot_geometry=(self.widthf, self.heightf)
      self.reset_statusbar()
      try:
        # try to read the plot image even if there was an error
        self.set_image()
      except:
        pass
      print 'Gnuplot error, see "View->Show Plot Parameters" for more details!'
      #self.show_last_plot_params(None)
    else:
      self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
      self.active_plot_geometry=(self.widthf, self.heightf)
      self.reset_statusbar()
      self.set_image()
      if not self.active_multiplot:
        self.measurement[self.index_mess].preview=self.image_pixbuf.scale_simple(100, 50, gtk.gdk.INTERP_BILINEAR)
    self.plot_options_buffer.set_text(str(self.measurement[self.index_mess].plot_options))
    text=self.active_session.get_active_file_info()+self.measurement[self.index_mess].get_info()
    self.info_label.set_markup(text.replace('<', '[').replace('>', ']'))

  def reset_statusbar(self): 
    '''
      Clear the statusbar.
    '''
    self.statusbar.pop(0)
    self.statusbar.push(0,'')

  #--------------Functions for displaying graphs plotting and status infos---------------#

  #+++++++++++++++++++++Functions responsible for menus and toolbar++++++++++++++++++++++#

  def build_menu(self):
    '''
      Create XML text for the menu and toolbar creation. In addition the variable
      actions are stored in a list. (See __create_action_group function)
      The XML text is used for the UIManager to create the bars,for more 
      information see the pygtk documentation for the UIManager.
      
      @return XML string for all menus and toolbar.
    '''
    self.added_items=(( "xMenu", None,                             # name, stock id
        "_x-axes", None,                    # label, accelerator
        "xMenu",                                   # tooltip
        None ),
        ( "yMenu", None,                             # name, stock id
        "_y-axes", None,                    # label, accelerator
        "yMenu",                                   # tooltip
        None ),
    ( "zMenu", None,                             # name, stock id
        "_z-axes", None,                    # label, accelerator
        "zMenu",                                   # tooltip
        None ),
    ( "dyMenu", None,                             # name, stock id
        "_error", None,                    # label, accelerator
        "dyMenu",                                   # tooltip
        None ),
    ( "Profiles", None,                             # name, stock id
        "_Profiles", None,                    # label, accelerator
        "Load or save a plot profile",                                   # tooltip
        None ),
    ( "SaveProfile", None,                             # name, stock id
        "Save Profile", None,                    # label, accelerator
        "Save a plot profile",                                   # tooltip
        self.save_profile ),
    ( "DeleteProfile", None,                             # name, stock id
        "Delete Profile", None,                    # label, accelerator
        "Delete a plot profile",                                   # tooltip
        self.delete_profile ),
    ( "x-number", None,                             # name, stock id
        "Point Number", None,                    # label, accelerator
        None,                                   # tooltip
        self.change ),
    ( "y-number", None,                             # name, stock id
        "Point Number", None,                    # label, accelerator
        None,                                   # tooltip
        self.change ),
    ( "FilesMenu", None,                             # name, stock id
        "_Change", None,                    # label, accelerator
        None,                                   # tooltip
        None ),)
  # Menus allways present
    output='''<ui>
    <menubar name='MenuBar'>
      <menu action='FileMenu'>
        <menuitem action='OpenDatafile'/>
        <menuitem action='SaveGPL'/>
        <menu action='SnapshotSub'>
          <menuitem action='SaveSnapshot'/>
          <menuitem action='SaveSnapshotAs'/>
          <menuitem action='LoadSnapshot'/>
          <menuitem action='LoadSnapshotFrom'/>
        </menu>
        <separator name='static14'/>
        <menuitem action='Export'/>
        <menuitem action='ExportAs'/>
        <menuitem action='ExportAll'/>
        <separator name='static1'/>
        <menuitem action='Print'/>
        <menuitem action='PrintAll'/>
        <separator name='static15'/>
        <menuitem action='ChangeSession'/>
        <menuitem action='TransfereDatasets'/>
        <separator name='static2'/>
        <menuitem action='Quit'/>
      </menu>
      <menu action='FilesMenu'>
      '''
    for i, name in enumerate([object[0] for object in sorted(self.active_session.file_data.items())]):
      output+="        <menuitem action='File-"+ str(i) +"'/>\n"
      self.added_items+=(("File-"+ str(i), None, 
                          os.path.split(name)[1], 
                          None, None, self.change_active_file),)
    output+='''
      </menu>
      <separator name='static12'/>
      <menu action='ViewMenu'>
        <menu action='AxesMenu'>
      '''
    if len(self.measurement)>0:
      # Menus for column selection created depending on input measurement
      output+='''
            <menu action='xMenu'>
              <menuitem action='x-number'/>
        '''
      for i, dimension in enumerate(self.measurement[self.index_mess].dimensions()):
        output+="         <menuitem action='x-"+str(i)+"'/>\n"
        self.added_items=self.added_items+(("x-"+str(i), None,dimension,None,None,self.change),)
      output+='''
            </menu>
            <menu action='yMenu'>
              <menuitem action='y-number'/>
        '''
      for i, dimension in enumerate(self.measurement[self.index_mess].dimensions()):
        output+="            <menuitem action='y-"+str(i)+"'/>\n"
        self.added_items=self.added_items+(("y-"+str(i), None,dimension,None,None,self.change),)
      if self.measurement[self.index_mess].zdata>=0:
        output+='''
              </menu>
              <placeholder name='zMenu'>
              <menu action='zMenu'>
          '''
        for i, dimension in enumerate(self.measurement[self.index_mess].dimensions()):
          output+="          <menuitem action='z-"+str(i)+"'/>\n"
          self.added_items=self.added_items+(("z-"+str(i), None,dimension,None,None,self.change),)
        output+="</menu></placeholder>\n"
      else:
        output+='''
              </menu>      
              <placeholder name='zMenu'/>'''
      output+='''
            <menu action='dyMenu'>
        '''
      for i, dimension in enumerate(self.measurement[self.index_mess].dimensions()):
        output+="              <menuitem action='dy-"+str(i)+"'/>\n"
        self.added_items=self.added_items+(("dy-"+str(i), None,dimension,None,None,self.change),)
      # allways present stuff and toolbar
      output+='''                   </menu>'''
    output+='''
        </menu>
        <menu action='Profiles'>
      '''
    for name in sorted(self.profiles.items()):
      output+="        <menuitem action='"+\
        name[0]+"' position='top'/>\n"
      self.added_items+=((name[0], None,'_'+name[0],None,None,self.load_profile),)
    output+='''  <separator name='static8'/>
          <menuitem action='SaveProfile' position="bottom"/>
          <menuitem action='DeleteProfile' position="bottom"/>
        </menu>
        <menuitem action='SelectColor'/>
        <separator name='static9'/>
        <menuitem action='AddAll'/>
        <menuitem action='ClearMultiplot'/>
        <menu action='ToolbarActions'>
          <menuitem action='Next'/>
          <menuitem action='Prev'/>
          <menuitem action='First'/>
          <menuitem action='Last'/>
          <separator name='static3'/>
          <menuitem action='ErrorBars'/>
          <menuitem action='AddMulti'/>
          <menuitem action='MultiPlot'/>
          <menuitem action='Apply'/>
        </menu>
        <separator name='static4'/>
        <menuitem action='ShowPlotTree'/>
        <menuitem action='ShowPlotparams'/>
        <menuitem action='ShowImportInfo'/>
      </menu>
      <menu action='TreatmentMenu'>
        '''
    #++++++++++++++ create session specific menu ++++++++
    specific_menu_items=self.active_session.create_menu()
    output+=specific_menu_items[0]
    self.session_added_items=specific_menu_items[1]
    #-------------- create session specific menu --------
    if len(self.measurement)>0:
      output+='''
          <menuitem action='FitData'/>
          <placeholder name='MultiFitData'/>
          <separator name='static5'/>
          <menuitem action='FilterData'/>
          <menuitem action='TransformData'/>
          <separator name='TreatmentStatic'/>'''
      if self.measurement[self.index_mess].zdata>=0:
        output+='''
          <placeholder name='z-actions'>
          <menuitem action='CrossSection'/>
          <menuitem action='RadialIntegration'/>
          <menuitem action='IntegrateIntensities'/>
          <separator name='z-sep1'/>
          <menuitem action='InterpolateSmooth'/>
          <menuitem action='RebinData'/>
          </placeholder>        
          <placeholder name='y-actions'/>'''
      else:
        output+='''
          <placeholder name='z-actions'/>
          <placeholder name='y-actions'>
          <menuitem action='CombinePoints'/>
          <menuitem action='Derivate'/>
          <menuitem action='ColorcodePoints'/>
          </placeholder>'''
    output+='''
        <separator name='static6'/>
        <menuitem action='RemovePlot'/>
      </menu>
      <menu action='ExtrasMenu'>
        <menuitem action='Makro'/>
        <menuitem action='LastMakro'/>
        <menuitem action='History'/>
        <menuitem action='OpenConsole'/>
        <separator name='extras1'/>
        <menuitem action='OpenDataView'/>
      </menu>
      <separator name='static13'/>
      <menu action='HelpMenu'>
        <menuitem action='ShowConfigPath'/>
        <menuitem action='APIReference'/>
      <separator name='help1'/>
        <menuitem action='About'/>
        '''
    if self.active_session.DEBUG:
      output+='''
      '''
    plugin_menu=''
    for plugin in self.active_session.plugins:
      if hasattr(plugin, 'menu') and ('all' in plugin.SESSIONS or self.active_session.__class__.__name__ in plugin.SESSIONS):
        string, actions=plugin.menu(self, self.active_session)
        plugin_menu+=string
        self.session_added_items=self.session_added_items+actions
    if plugin_menu!='':
      output+='''
        </menu>
        <menu action='PluginMenu'>
      '''+plugin_menu
      self.session_added_items=self.session_added_items+( ( "PluginMenu", None, "Plugins", None, None, None ), )
    output+=    '''
      </menu>
    </menubar>
    <toolbar  name='ToolBar'>
      <toolitem action='First'/>
      <toolitem action='Prev'/>
      <toolitem action='Next'/>
      <toolitem action='Last'/>
      <separator name='static10'/>
      <toolitem action='Apply'/>
      <toolitem action='ExportAll'/>
      '''
    if len(self.measurement)>0 and self.measurement[self.index_mess].zdata>=0:
      output+='''<toolitem action='XYProjections'/>
      '''        
    else:
      output+='''<toolitem action='ErrorBars'/>
      '''
    output+='''<toolitem action='ToggleMousemode' />
      <separator name='static11'/>
      <toolitem action='AddMulti'/>
      <toolitem action='MultiPlot'/>
      <separator name='static12'/>
      <toolitem action='SaveSnapshot'/>
      <toolitem action='LoadSnapshot'/>
      <separator name='static13'/>
      <toolitem action='ShowPersistent'/>
      '''
    if len(self.measurement)>0 and self.measurement[self.index_mess].zdata>=0 and len(self.measurement[self.index_mess].plot_together)>1:
      output+='''      <toolitem action='TogglePlotFit'/>
      <toolitem action='IteratePlotFit'/>'''
    output+='''
    </toolbar>
    </ui>'''
    return output

  def __create_action_group(self):
    '''
      Create actions for menus and toolbar.
      Every entry creates a gtk.Action and the function returns a gtk.ActionGroup.
      When the action is triggered it calls a function.
      For more information see the pygtk documentation for the UIManager and ActionGroups.
      
      @return ActionGroup for all menu entries.
    '''
    entries = (
      ( "FileMenu", None, "_File" ),               # name, stock id, label
      ( "ViewMenu", None, "_View" ),               # name, stock id, label
      ( "AxesMenu", None,  "_Axes"),                # name, stock id, label
      ( "TreatmentMenu", None, "_Data treatment" ),               # name, stock id, label
      ( "ExtrasMenu", None,  "_Extras"),                # name, stock id, label
      ( "HelpMenu", None, "_Help" ),               # name, stock id, label
      ( "ToolBar", None, "Toolbar" ),               # name, stock id, label
      ( "ToolbarActions", None, "Toolbar Actions" ),               # name, stock id, label
      ( "OpenDatafile", gtk.STOCK_OPEN,                    # name, stock id
        "_Open File","<control>O",                      # label, accelerator
        "Open a new datafile",                       # tooltip
        self.add_file ),
      ( "SnapshotSub", gtk.STOCK_EDIT,                    # name, stock id
        "Snapshots", None,                      # label, accelerator
        None, None),                       # tooltip
      ( "SaveSnapshot", gtk.STOCK_EDIT,                    # name, stock id
        "Save Snapshot","<control><shift>S",                      # label, accelerator
        "Save the current state for this measurement.",                       # tooltip
        self.save_snapshot ),
      ( "SaveSnapshotAs", gtk.STOCK_EDIT,                    # name, stock id
        "Save Snapshot As...", None,                      # label, accelerator
        "Save the current state for this measurement.",                       # tooltip
        self.save_snapshot ),
      ( "LoadSnapshot", gtk.STOCK_OPEN,                    # name, stock id
        "Load Snapshot", "<control><shift>O",                      # label, accelerator
        "Load a state for this measurement stored before.",                       # tooltip
        self.load_snapshot ),
      ( "LoadSnapshotFrom", gtk.STOCK_OPEN,                    # name, stock id
        "Load Snapshot From...", None,                      # label, accelerator
        "Load a state for this measurement stored before.",                       # tooltip
        self.load_snapshot ),
      ( "SaveGPL", gtk.STOCK_SAVE,                    # name, stock id
        "_Save this dataset (.out)...","<control>S",                      # label, accelerator
        "Save Gnuplot and datafile",                       # tooltip
        self.export_plot ),
      ( "Export", gtk.STOCK_SAVE,                    # name, stock id
        "_Export (.png)","<control>E",                      # label, accelerator
        "Export current Plot",                       # tooltip
        self.export_plot ),
      ( "ExportAs", gtk.STOCK_SAVE,                  # name, stock id
        "E_xport As (.png/.ps)...", '<control><shift>E',                       # label, accelerator
        "Export Plot under other name",                          # tooltip
        self.export_plot ),
      ( "Print", gtk.STOCK_PRINT,                  # name, stock id
        "_Print...", "<control>P",                       # label, accelerator
        None,                          # tooltip
        self.print_plot ),
      ( "PrintAll", gtk.STOCK_PRINT,                  # name, stock id
        "Print Selection...", "<control><shift>P",                       # label, accelerator
        None,                          # tooltip
        self.print_plot ),
      ( "ChangeSession", gtk.STOCK_LEAVE_FULLSCREEN,                  # name, stock id
        "Change Active Session...", None,                       # label, accelerator
        None,                          # tooltip
        self.change_session ),
      ( "TransfereDatasets", None,                  # name, stock id
        "Transfere Datasets to Session...", None,                       # label, accelerator
        None,                          # tooltip
        self.transfere_datasets),
      ( "Quit", gtk.STOCK_QUIT,                    # name, stock id
        "_Quit", "<control>Q",                     # label, accelerator
        "Quit",                                    # tooltip
        self.main_quit ),
      ( "About", None,                             # name, stock id
        "About", None,                    # label, accelerator
        "About",                                   # tooltip
        self.activate_about ),
      ( "APIReference", None,                             # name, stock id
        "API Reference...", None,                    # label, accelerator
        "Open API reference manual in a webbrowser",                                   # tooltip
        apihelp ),
      ( "ShowConfigPath", None,                             # name, stock id
        "Show Config Path...", None,                    # label, accelerator
        "Show Configfile Path",                                   # tooltip
        self.show_config_path ),
      ( "History", None,                             # name, stock id
        "Action History", None,                    # label, accelerator
        "History",                                   # tooltip
        self.action_history ),
      ( "Makro", None,                             # name, stock id
        "Run Makro...", None,                    # label, accelerator
        "Run Makro",                                   # tooltip
        self.run_action_makro ),
      ( "LastMakro", None,                             # name, stock id
        "Run Last Makro", "<control>M",                    # label, accelerator
        "Run Last Makro",                                   # tooltip
        self.run_last_action_makro ),
      ( "First", gtk.STOCK_GOTO_FIRST,                    # name, stock id
        "First", "<control><shift>B",                     # label, accelerator
        "First Plot",                                    # tooltip
        self.iterate_through_measurements),
      ( "Prev", gtk.STOCK_GO_BACK,                    # name, stock id
        "Prev", "<control>B",                     # label, accelerator
        "Previous Plot",                                    # tooltip
        self.iterate_through_measurements),
      ( "Next", gtk.STOCK_GO_FORWARD,                    # name, stock id
        "_Next", "<control>N",                     # label, accelerator
        "Next Plot",                                    # tooltip
        self.iterate_through_measurements),
      ( "Last", gtk.STOCK_GOTO_LAST,                    # name, stock id
        "Last", "<control><shift>N",                     # label, accelerator
        "Last Plot",                                    # tooltip
        self.iterate_through_measurements),
      ( "ShowPlotparams", None,                    # name, stock id
        "Show plot parameters", None,                     # label, accelerator
        "Show the gnuplot parameters used for plot.",                                    # tooltip
        self.show_last_plot_params),
      ( "ShowImportInfo", None,                    # name, stock id
        "Show File Import Informations", None,#'i',                     # label, accelerator
        "Show the information from the file import in this session.",                                    # tooltip
        self.show_status_dialog),
      ( "ShowPlotTree", None,                    # name, stock id
        "Show Tree of Datasets", "<control>T",#'i',                     # label, accelerator
        "Show Tree of Datasets...",                                    # tooltip
        self.show_plot_tree),
      ( "FilterData", None,                    # name, stock id
        "Filter the data points", None,#'f',                     # label, accelerator
        None,                                    # tooltip
        self.change_data_filter),
      ( "TransformData", None,                    # name, stock id
        "Transform the Units/Dimensions", None,#'t',                     # label, accelerator
        None,                                    # tooltip
        self.unit_transformation),
      ( "CrossSection", None,                    # name, stock id
        "Cross-Section...", None,#'s',                     # label, accelerator
        None,                                    # tooltip
        self.extract_cross_section),
      ( "InterpolateSmooth", None,                    # name, stock id
        "Interpolate to regular grid...", "<control>G",                     # label, accelerator
        None,                                    # tooltip
        self.interpolate_and_smooth_dialog),
      ( "RebinData", None,                    # name, stock id
        "Rebin data...", "<control><shift>G",                     # label, accelerator
        None,                                    # tooltip
        self.rebin_3d_data_dialog),
      ( "RadialIntegration", None,                    # name, stock id
        "Calculate Radial Integration...", None,                     # label, accelerator
        None,                                    # tooltip
        self.extract_radial_integration),
      ( "IntegrateIntensities", None,                    # name, stock id
        "Integrat Intensities...", None,                     # label, accelerator
        None,                                    # tooltip
        self.extract_integrated_intensities),
      ( "CombinePoints", None,                    # name, stock id
        "Combine points", None,                     # label, accelerator
        None,                                    # tooltip
        self.combine_data_points),
      ( "Derivate", None,                    # name, stock id
        "Derivate or Smoothe", '<control>D',                     # label, accelerator
        None,                                    # tooltip
        self.derivate_data),
      ( "ColorcodePoints", None,                    # name, stock id
        "Show Colorcoded Points", None,                     # label, accelerator
        None,                                    # tooltip
        self.colorcode_points),
      ( "SelectColor", None,                    # name, stock id
        "Color Pattern...", None,#'p',                     # label, accelerator
        None,                                    # tooltip
        self.change_color_pattern),
      ( "Apply", gtk.STOCK_CONVERT,                    # name, stock id
        "Apply", None,#'a',                     # label, accelerator
        "Apply current plot settings to all sequences",                                    # tooltip
        self.apply_to_all),
      ( "ExportAll", gtk.STOCK_EXECUTE,                    # name, stock id
        "Exp. Selection...", None,                     # label, accelerator
        "Export a selection of plots",                                    # tooltip
        self.export_plot),
      ( "ErrorBars", gtk.STOCK_ADD,                    # name, stock id
        "E.Bars", None,#'e',                     # label, accelerator
        "Toggle errorbars",                                    # tooltip
        self.toggle_error_bars),
      ( "XYProjections", gtk.STOCK_FULLSCREEN,                    # name, stock id
        "XY-Proj.", None,#'e',                     # label, accelerator
        "Toggle xy-projections",                                    # tooltip
        self.toggle_xyprojections),
      ( "AddMulti", gtk.STOCK_JUMP_TO,                    # name, stock id
        "_Add", '<alt>a',                     # label, accelerator
        "Add/Remove plot to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "AddAll", gtk.STOCK_JUMP_TO,                    # name, stock id
        "Add all to Multiplot", '<alt><shift>a',                     # label, accelerator
        "Add/Remove all sequences to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "ClearMultiplot", gtk.STOCK_JUMP_TO,                    # name, stock id
        "Clear Multiplot List",  None,#'c',                     # label, accelerator
        "Remove all multi-plot list entries",                                    # tooltip
        self.add_multiplot),
      ( "RemovePlot", None,                    # name, stock id
        "Remove the active Plot (no way back!)",  None,                     # label, accelerator
        "Remove the active Plot (no way back!)",                                    # tooltip
        self.remove_active_plot),
      ( "FitData", None,                    # name, stock id
        "_Fit data...", "<control>F",                     # label, accelerator
        "Dialog for fitting of a function to the active dataset.",                                    # tooltip
        self.fit_dialog),
      ( "MultiFitData", None,                    # name, stock id
        "Fit _Multiple datasets...", "<control><shift>M",                     # label, accelerator
        "Dialog for fitting of a function to the active dataset.",                                    # tooltip
        self.multi_fit_dialog),
      ( "MultiPlot", gtk.STOCK_YES,                    # name, stock id
        "Multi", None,#'m',                     # label, accelerator
        "Show Multi-plot",                                    # tooltip
        self.export_plot),
      ( "MultiPlotExport", None,                    # name, stock id
        "Export Multi-plots", None,                     # label, accelerator
        "Export Multi-plots",                                    # tooltip
        self.export_plot),
      ( "OpenConsole", None,                    # name, stock id
        "Open IPython Console", "<control>I",                     # label, accelerator
        None,                                    # tooltip
        self.open_ipy_console),
      ( "OpenDataView", None,                    # name, stock id
        "Show/Edit Data", "<control><shift>D",                     # label, accelerator
        None,                                    # tooltip
        self.open_dataview_dialog),
      ( "ShowPersistent", gtk.STOCK_FULLSCREEN,                    # name, stock id
        "Open Persistent Gnuplot Window", None,                     # label, accelerator
        "Open Persistent Gnuplot Window",                                    # tooltip
        self.plot_persistent),
      ( "ToggleMousemode", gtk.STOCK_GOTO_TOP,                    # name, stock id
        "Toggle Mousemode", None,                     # label, accelerator
        "Switch mouse navigation On/Off (Off speeds up map plots)",                                    # tooltip
        self.toggle_mouse_mode),
      ( "TogglePlotFit", gtk.STOCK_ZOOM_FIT,                    # name, stock id
        "Toggle between data,fit and combined plot", "<control><shift>T",                     # label, accelerator
        "Toggle between data,fit and combined plot",                                    # tooltip
        self.toggle_plotfit),
      ( "IteratePlotFit", gtk.STOCK_ZOOM_100,                    # name, stock id
        "Select between data and fits to plot", None,                     # label, accelerator
        "Select between data and fits to plot",                                    # tooltip
        self.toggle_plotfit),
    )+self.added_items;
    # Create the menubar and toolbar
    action_group = gtk.ActionGroup("AppWindowActions")
    action_group.add_actions(entries)
    action_group.add_actions(self.session_added_items, self)
    return action_group

  def rebuild_menus(self):
    '''
      Build new menu and toolbar structure.
    '''
    ui_info=self.build_menu() # build structure of menu and toolbar
    # remove old menu
    self.UIManager.remove_ui(self.toolbar_ui_id)
    self.UIManager.remove_action_group(self.toolbar_action_group)
    self.toolbar_action_group=self.__create_action_group()
    self.UIManager.insert_action_group(self.toolbar_action_group, 0) # create action groups for menu and toolbar
    try:
        self.toolbar_ui_id = self.UIManager.add_ui_from_string(ui_info)
    except gobject.GError, msg:
        print "building menus failed: %s" % msg
    
  #---------------------Functions responsible for menus and toolbar----------------------#
  
  #+++++++++ EXPERIMENTAL: usage of matplotlib widget for plotting ++++++++++++++++++++++#
  
  def initialize_matplotlib(self):
    '''
      Import and prepare everything for the use of matplotlib plotting widget.
    '''
    # supress the warning of matplotlib that configobj is already imported
    import warnings
    original_filters = warnings.filters[:]
    # Ignore warnings.
    warnings.simplefilter("ignore")
    try:
      # tell matplotlib to use gtk backend
      import matplotlib
      matplotlib.use('GTK')
      
      # import widget stuff
      from matplotlib.figure import Figure
      from matplotlib.axes import Subplot
      from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
      from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg as NavigationToolbar
      from matplotlib.widgets import SpanSelector
      # also toolbar throws warning
      figure=Figure()
      plot=figure.add_subplot(111)
      self.active_session.mpl_plot=plot
      mpl_widget=FigureCanvas(figure)
      self.active_session.mpl_widget=mpl_widget
      toolbar=NavigationToolbar(mpl_widget, self)
    except ImportError:
      raise ImportError, "Matplotlib is not installed."
    finally:
      # Restore the list of warning filters.
      warnings.filters = original_filters      
    vbox=gtk.VBox()
    vbox.pack_start(mpl_widget, expand=True, fill=True, padding=0)
    vbox.pack_end(toolbar, expand=False, fill=True, padding=0)
    
    self.image=vbox
    # redefine functions to be used with mpl
    self.plot=measurement_data_plotting.mpl_plot
    def do_nothing(*ignore):
      pass
    self.set_image=do_nothing
    self.update_picture=do_nothing
    self.update_size=do_nothing
    self.image_pixbuf=gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8,1,1)
    self.image_do_resize=False
    self.mouse_mode=False
  
  #--------- EXPERIMENTAL: usage of matplotlib widget for plotting ----------------------#

#------------------------- ApplicationMainWindow Class ----------------------------------#

def apihelp(*ignore):
  '''
    Open the API reference manual in a webbrowser.
    
    @return Return value of webbrowser.open
  '''
  import webbrowser
  # get the path of the program
  file_path=os.path.split(measurement_data_plotting.__file__)[0].split("library.zip")[0]
  help_file=os.path.join(
                              file_path
                              , 'doc'
                              , 'index-plot_script.html'
                              )
  return webbrowser.open(help_file)

