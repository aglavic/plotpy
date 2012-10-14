# -*- encoding: utf-8 -*-
'''
  Main window class for all sessions.
'''

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import os, sys
import gobject
import gtk
# own modules
# Module to save and load variables from/to config files
from plotpy import plotting, config
from plotpy.config import gnuplot_preferences
from plotpy.config import gui as gui_config
from plotpy.config import fontconfig
import file_actions
from main_window_actions import MainActions
from main_window_ui import MainUI
from dnd_handling import ImageDND
from multiplots import MultiplotCanvas
from diverse_classes import RedirectError, RedirectOutput

if not sys.platform.startswith('win'):
  WindowsError=RuntimeError
#----------------------- importing modules --------------------------


__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

def main_loop(session):
  '''
    Start the main loop.
  '''
  if getattr(session, 'destroyed_directly', False):
    while gtk.events_pending():
      gtk.main_iteration(False)
  else:
    # wrap main loop with thread_enter,
    # otherwise py2exe will crash on main loop enter
    # when using threads
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main() # start GTK engine
    gtk.gdk.threads_leave()


#+++++++++++++++++++++++++ ApplicationMainWindow Class ++++++++++++++++++++++++++++++++++#
class ApplicationMainWindow(gtk.Window, MainUI, MainActions):
  '''
    Main window of the GUI.
    Everything the GUI does is in this Class.
    User interface is defined in MainUI, actions in MainActions,
    which is derived from different other action classes
  '''
  status_dialog=None
  init_complete=False
  destroyed_directly=False
  # sub-windows can set a function which gets called on button press
  # with the active position of the mouse on the plot
  garbage=[]
  plot_tree=None
  open_windows=[]
  _ignore_change=False
  active_threads=[]

  def get_active_dataset(self):
    # convenience method to get the active dataset
    return self.measurement[self.index_mess]

  def set_active_dataset(self, dataset):
    if dataset in self.measurement:
      self.index_mess=self.measurement.index(dataset)
    else:
      found=False
      for name, measurement in self.active_session.file_data.items():
        if dataset in measurement:
          self.active_session.active_file_data=measurement
          self.active_session.active_file_name=name
          self.measurement=measurement
          self.index_mess=measurement.index(dataset)
          found=True
          break
      if not found:
        self.measurement[self.index_mess]=dataset

  active_dataset=property(get_active_dataset, set_active_dataset)
  # stores the geometry of the window and image
  geometry=((0, 0), (800, 600))
  active_plot_geometry=(780, 550)

  #+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
  def __init__(self, active_session=None, parent=None, script_suf='', status_dialog=None):
    '''
      Class constructor which builds the main window with it's menus, buttons and the plot area.
      
      :param active_session: A session object derived from GenericSession.
      :param parant: Parent window.
      :param script_suf: Suffix for script file name.
      :param status_dialog: The dialog used to show import information.
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

    #+++++++++++++++++ set class variables ++++++++++++++++++
    self.status_dialog=status_dialog
    self.heightf=100 # picture frame height
    self.widthf=100 # pricture frame width
    self.set_file_type=gnuplot_preferences.output_file_name.rsplit('.', 1)[1] # export file type
    self.measurement=active_session.active_file_data # active data file measurements
    self.input_file_name=active_session.active_file_name # name of source data file
    self.script_suf=script_suf # suffix for script mode gnuplot input data
    self.index_mess=0 # which data sequence is plotted at the moment
    self.x_range='set autoscale x'
    self.y_range='set autoscale y'
    self.z_range='set autoscale z\nset autoscale cb'
    self.active_multiplot=False
    self.plot_options_window_open=False # is the dialog window for the plot options active?
    self.file_actions=file_actions.FileActions(self)
    # list of active winows, that will be closed with this main window
    self.open_windows=[]
    # Create a text view widget. When a text view is created it will
    # create an associated textbuffer by default.
    self.plot_options_view=gtk.TextView()
    # Retrieving a reference to a textbuffer from a textview.
    self.plot_options_buffer=self.plot_options_view.get_buffer()
    self.active_folder=os.path.realpath('.') # For file dialogs to stay in the active directory
    #----------------- set class variables ------------------


    # Create the toplevel window
    gtk.Window.__init__(self)
    self.set_icon_from_file(gui_config.ICONS['Logo'])
    # Reading config file
    self.read_config_file()
    # When the window gets destroyed, process some cleanup and save the configuration
    self.connect('destroy', lambda*w: self.main_quit())
    # Set the title of the window, will be changed when the active plot changes
    self.set_title('Plotting GUI - '+self.input_file_name+" - "+str(self.index_mess))

    #+++++++Build widgets in table structure++++++++
    table=gtk.Table(3, 6, False) # the main table
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
    self.UIManager=gtk.UIManager() # construct a new UIManager object
    self.set_data("ui-manager", self.UIManager)
    self.toolbar_action_group=self.create_action_group() # create action group
    self.UIManager.insert_action_group(self.toolbar_action_group, 0)
    self.add_accel_group(self.UIManager.get_accel_group())
    # don't crash if the menu creation fails
    try:
        self.toolbar_ui_id=self.UIManager.add_ui_from_string(ui_info)
    except gobject.GError, msg:
        raise RuntimeError, "building menus failed: %s"%msg
    self.menu_bar=self.UIManager.get_widget("/MenuBar")
    # custom icons
    for item in gui_config.ICONS.items():
      self.replace_icon(*item)
    self.menu_bar.show()

    # put menu at top position, only expand in x direction
    table.attach(self.menu_bar,
        # X direction #          # Y direction
        0, 3, 0, 1,
        gtk.EXPAND|gtk.FILL, 0,
        0, 0)
    # put toolbar below menubar, only expand in x direction
    barbox=gtk.VBox()
    barbox.show()
    for i in gui_config['show_toolbars']:
      bar=self.UIManager.get_widget("/ToolBar%i"%(i+1))
      bar.set_tooltips(True)
      bar.set_style(gtk.TOOLBAR_ICONS)
      bar.show()
      barbox.add(bar)
    table.attach(barbox,
        # X direction #       # Y direction
        0, 3, 1, 2,
        gtk.EXPAND|gtk.FILL, 0,
        0, 0)
    #---------- Menu and toolbar creation ----------

    #++++++++++ create image region and image for the plot ++++++++++
    # plot title label entries
    # TODO: don't lose entry when not pressing enter
    top_table=gtk.Table(2, 1, False)
    # first entry for sample name part of title
    self.label=gtk.Entry()
    # second entry for additional infor part ofr title
    self.label2=gtk.Entry()
    self.plot_options_view.show()
    # attach entrys to sub table
    top_table.attach(self.label,
        # X direction           Y direction
        0, 1, 0, 1,
        gtk.FILL, gtk.FILL,
        0, 0)
    top_table.attach(self.label2,
        # X direction           Y direction
        1, 2, 0, 1,
        gtk.FILL, gtk.FILL,
        0, 0)
    align=gtk.Alignment(0.5, 0., 0., 0) # center the entrys
    align.add(top_table)
    # put label below menubar on left column, only expand in x direction
    table.attach(align,
        # X direction           Y direction
        0, 1, 2, 3,
        gtk.FILL, gtk.FILL,
        0, 0)

    # frame region for the image
    self.frame1=gtk.Notebook()
    self.frame1.set_group_id(0)
    align=gtk.Alignment(0.5, 0.5, 1, 1)
    align.add(self.frame1)
    table.attach(align,
        # X direction           Y direction
        0, 3, 3, 4,
        gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL,
        0, 0)
    # image object for the plots
    self.image=gtk.Image()
    self.image_shown=False # variable to decrease changes in picture size
    self.image.set_size_request(0, 0)
    self.image_do_resize=False
    # put image in an eventbox to catch e.g. mouse events
    self.event_box=gtk.EventBox()
    self.event_box.add(self.image)
    self.event_box.set_events(gtk.gdk.POINTER_MOTION_MASK
                              |gtk.gdk.BUTTON_PRESS_MASK
                              |gtk.gdk.BUTTON_RELEASE_MASK)
    self.frame1.append_page(self.event_box, gtk.Label("Plot"))
    self.frame1.set_tab_detachable(self.event_box, True)
    #---------- create image region and image for the plot ----------

    # Create region for multiplot list
    self.multiplot=MultiplotCanvas(self)
    self._multiplot_first_show=True
    self.multiplot.show()
    #self.multi_list=gtk.Label();
    #self.multi_list.set_markup(' Multiplot List: ')
    #align=gtk.Alignment(0, 0.05, 1, 0) # align top
    #align.add(self.multi_list)
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(self.multiplot)
    sw.show()
    # put multiplot list
    self.frame1.append_page(sw, gtk.Label("Multiplot List"))
    self.frame1.set_tab_detachable(sw, True)
    # Create region for Dataset Info
    self.info_label=gtk.Label();
    self.info_label.set_markup('')
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(self.info_label)
    # put Dataset Info
    self.frame1.append_page(sw, gtk.Label("Dataset Info"))
    self.frame1.set_tab_detachable(sw, True)

    #++++++++++ Create additional setting input for the plot ++++++++++
    align_table=gtk.Table(12, 2, False)
    # input for jumping to a data sequence
    self.plot_page_entry=gtk.Entry()
    self.plot_page_entry.set_width_chars(4)
    self.plot_page_entry.set_text('0')
    self.plot_page_entry.set_tooltip_text('Index of plot in active file')
    align_table.attach(self.plot_page_entry, 0, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    # x,y ranges
    self.x_range_in=gtk.Entry()
    self.x_range_in.set_width_chars(10)
    self.x_range_in.set_text(':')
    self.x_range_in.set_tooltip_text('x-range [from:to] (right click to select from other)')
    self.x_range_label=gtk.Label()
    self.x_range_label.set_markup('x')
    self.y_range_in=gtk.Entry()
    self.y_range_in.set_width_chars(10)
    self.y_range_in.set_text(':')
    self.y_range_in.set_tooltip_text('y-range [from:to] (right click to select from other)')
    self.y_range_label=gtk.Label()
    self.y_range_label.set_markup('y')
    align_table.attach(self.x_range_label, 3, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.x_range_in, 4, 5, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.y_range_label, 5, 7, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.y_range_in, 7, 9, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    # font size entry
    if fontconfig.font_config is not None \
        or 'pngcairo' in self.gnuplot_info['terminals']\
        or sys.platform.startswith('win'):
      self.font_size=gtk.FontButton()
      self.font_size.set_font_name(gnuplot_preferences.font+', '+
                                   str(self.active_session.font_size))
      self.font_size.set_title('Select Plot Font...')
      self.font_size.set_show_style(False)
      self.font_size.set_show_size(True)
      self.font_size.connect("font-set", self.change_font)
      self.font_size_label=None
    else:
      self.font_size=gtk.Entry()
      self.font_size.set_width_chars(5)
      self.font_size.set_text(str(self.active_session.font_size))
      self.font_size_label=gtk.Label()
      self.font_size_label.set_markup('F. size:')
      self.font_size_label.set_padding(5, 0)
      align_table.attach(self.font_size_label, 11, 12, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.font_size, 12, 13, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    # checkboxes for log x and log y
    self.logx=gtk.CheckButton(label='log x', use_underline=True)
    self.logy=gtk.CheckButton(label='log y', use_underline=True)
    align_table.attach(self.logx, 9, 10, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.logy, 10, 11, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    # button to open additional plot options dialog
    self.plot_options_button=gtk.ToolButton(gtk.STOCK_PREFERENCES)
    try:
      self.plot_options_button.set_tooltip_text('Add custom Gnuplot commands')
    except AttributeError:
      # for earlier versions of gtk, this is deprecated in python 2.6
      self.plot_options_button.set_tooltip(gtk.Tooltips(), 'Add custom Gnuplot commands')
    align_table.attach(self.plot_options_button, 13, 14, 0, 2, gtk.FILL, gtk.FILL, 0, 0)
    # z range and log z checkbox
    self.z_range_in=gtk.Entry()
    self.z_range_in.set_width_chars(10)
    self.z_range_in.set_text(':')
    self.z_range_in.set_tooltip_text('z-range [from:to] (right click to select from other)')
    self.z_range_label=gtk.Label()
    self.z_range_label.set_markup('z')
    self.logz=gtk.CheckButton(label='log z', use_underline=True)
    # 3d Viewpoint buttons to rotate the view
    self.view_left=gtk.ToolButton(gtk.STOCK_GO_BACK)
    self.view_up=gtk.ToolButton(gtk.STOCK_GO_UP)
    self.view_down=gtk.ToolButton(gtk.STOCK_GO_DOWN)
    self.view_right=gtk.ToolButton(gtk.STOCK_GO_FORWARD)
    box=gtk.HBox()
    box.add(self.view_left)
    box.add(self.view_right)
    box.add(self.view_up)
    box.add(self.view_down)
    align_table.attach(self.z_range_label, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.z_range_in, 4, 5, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(box, 5, 10, 1, 2, 0, gtk.FILL, 0, 0)
    #align_table.attach(self.view_up, 6, 7, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    #align_table.attach(self.view_down, 7, 8, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    #align_table.attach(self.view_right, 8, 9, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    align_table.attach(self.logz, 10, 11, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    # options for 4d plots
    self.y2_slicing=gtk.CheckButton(label='slicing', use_underline=True)
    align_table.attach(self.y2_slicing, 14, 15, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.y2_width=gtk.Entry()
    self.y2_width.set_text("0")
    self.y2_width.set_width_chars(6)
    self.y2_width.set_sensitive(False)
    align_table.attach(self.y2_width, 15, 16, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.grid_4dx=gtk.Entry()
    self.grid_4dx.set_text("100")
    self.grid_4dx.set_width_chars(4)
    align_table.attach(self.grid_4dx, 16, 17, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.grid_4dy=gtk.Entry()
    self.grid_4dy.set_text("100")
    self.grid_4dy.set_width_chars(4)
    align_table.attach(self.grid_4dy, 17, 18, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.y2_center=gtk.HScale()
    self.y2_center.set_draw_value(True)
    self.y2_center.set_sensitive(False)
    align_table.attach(self.y2_center, 14, 18, 1, 2, gtk.FILL|gtk.EXPAND, gtk.FILL, 0, 0)

    # add all those options
    #align=gtk.Alignment(0, 0, 0, 0) # align the table left
    #align.add(align_table)
    # put plot settings below Plot
    table.attach(align_table,
        # X direction           Y direction
        0, 3, 4, 5,
        gtk.FILL, gtk.FILL,
        0, 0)
    #---------- Create additional setting input for the plot ----------

    #+++ Creating entries and options according to the active measurement +++
    if len(self.measurement)>0:
      self.label.set_width_chars(30) # title width
      self.label.set_text(self.active_dataset.sample_name)
      self.label2.set_width_chars(30) # title width
      self.label2.set_text(self.active_dataset.short_info)
      # TODO: put this to a different location
      self.plot_options_buffer.set_text(str(self.active_dataset.plot_options))
      self.logx.set_active(self.active_dataset.logx)
      self.logy.set_active(self.active_dataset.logy)
      self.logz.set_active(self.active_dataset.logz)

    #--- Creating entries and options according to the active measurement ---

    # Create statusbar
    self.statusbar=gtk.Statusbar()
    self.statusbar.set_has_resize_grip(True)
    self.progressbar=gtk.ProgressBar()
    self.progressbar.set_size_request(40,-1)
    self.xindicator=gtk.Label()
    self.xindicator.set_width_chars(10)
    self.yindicator=gtk.Label()
    self.yindicator.set_width_chars(10)
    self.statusbar.pack_start(self.progressbar, False)
    self.statusbar.pack_end(self.yindicator, False)
    self.statusbar.pack_end(gtk.VSeparator(), False)
    self.statusbar.pack_end(self.xindicator, False)
    # put statusbar below everything
    if gui_config['show_statusbar']:
      table.attach(self.statusbar,
          # X direction           Y direction
          0, 3, 5, 6,
          gtk.EXPAND|gtk.FILL, 0,
          0, 0)

    #-------Build widgets in table structure--------

    #+++++++++++++ Show window and connecting events ++++++++++++++
    # show all widgets, load the last window position and size and show
    # the window
    table.show_all()
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
    self.y2_center.hide()
    self.y2_slicing.hide()
    self.y2_width.hide()
    self.grid_4dx.hide()
    self.grid_4dy.hide()
    self.view_left.hide()
    self.view_up.hide()
    self.view_down.hide()
    self.view_right.hide()
    self.frame1.set_current_page(0)
    self.read_window_config()

    while len(self.measurement)==0:
      # if there is no measurement loaded, open a file selection dialog
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

    self.show()
    # Display the window
    if self.status_dialog:
      # hide thw status dialog to make it possible to reshow it
      self.status_dialog.hide()
      self.status_dialog.connected_progress=self.progressbar
      self.status_dialog.connected_status=self.statusbar
      self.status_dialog.set_transient_for(self)

    # resize events
    self.connect("event-after", self.update_picture)
    self.connect("configure-event", self.update_size)
    self.image.connect('size-allocate', self.image_resize)
    # entries
    self.label.connect("activate", self.change) # changed entry triggers change() function 
    self.label2.connect("activate", self.change) # changed entry triggers change() function 
    self.plot_page_entry.connect("activate", self.iterate_through_measurements)
    self.x_range_in.connect("activate", self.change_range)
    self.x_range_in.connect('event', self.range_event)
    self.y_range_in.connect("activate", self.change_range)
    self.y_range_in.connect('event', self.range_event)
    self.font_size.connect("activate", self.change_range)
    self.logx.connect("toggled", self.change)
    self.logy.connect("toggled", self.change)
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",
                                                                self.open_plot_options_window)
    self.z_range_in.connect("activate", self.change_range)
    self.z_range_in.connect('event', self.range_event)
    self.logz.connect("toggled", self.change)
    self.y2_slicing.connect("toggled", self.change)
    self.y2_width.connect("activate", self.change)
    self.grid_4dx.connect("activate", self.change)
    self.grid_4dy.connect("activate", self.change)
    self.y2_center.connect("value-changed", self.change)
    self.view_left.connect("clicked", self.change)
    self.view_up.connect("clicked", self.change)
    self.view_down.connect("clicked", self.change)
    self.view_right.connect("clicked", self.change)
    # mouse and keyboad events
    self.event_box.connect('button-press-event', self.mouse_press)
    self.event_box.connect('button-release-event', self.mouse_release)
    self.event_box.connect('motion-notify-event', self.catch_mouse_position)
    # Drag & Drop
    self.DnD=ImageDND(self)
    self.connect('drag-data-get', self.send_image_on_drag)
    # misc
    self.frame1.connect('switch-page', self.tab_switched)
    #------------- connecting events --------------

    # create the first plot
    try:
      self.active_session.initialize_gnuplot()
    except (RuntimeError, WindowsError), error_message:
      # user can select the gnuplot executable via a file selection dialog
      info_dialog=gtk.Dialog(parent=self, title='Gnuplot Error..', buttons=('Select Gnuplot Executable', 1,
                                                                            'Exit Program',-1))
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
            message_format='To make this executable persistent you need to change the GNUPLOT_COMMAND option in %s to %s'%\
              (os.path.join(config.__path__[0], 'gnuplot_preferences.py'), repr(self.active_session.GNUPLOT_COMMAND))) #@UndefinedVariable
          message.run()
          message.destroy()
        else:
          file_chooser.destroy()
          self.destroy()
      else:
        info_dialog.destroy()
        self.destroy()
        return
    # open the plot tree dialog
    if self.config_object['plot_tree']['shown']:
      self.show_plot_tree()
    # if plugins are installed activate session specific options
    self.activate_plugins()
    self.check_for_updates()
    while gtk.events_pending():
      gtk.main_iteration(False)
    self.update_size(None, None) # make sure the image size is correct
    self.init_complete=True
    # plot the first image
    self.replot()
    # execute ipython commands supplied via commandline
    if len(self.active_session.ipython_commands)>0:
      while gtk.events_pending():
        gtk.main_iteration(False)
      self.open_ipy_console(commands=self.active_session.ipython_commands, show_greetings=False)

  #-------------------------------Window Constructor-------------------------------------#

  def main_quit(self, action=None, store_config=True):
    '''
      When window is closed save the settings in home folder.
      All open dialogs are closed before exit.
    '''
    # join active threads
    for thread_killer in self.active_threads:
      thread_killer()
    # exit persistent gnuplot instances
    persistent_plot_instances=plotting.persistent_plot_instances
    for p in persistent_plot_instances:
      try:
        p.stdin.write('\nquit\n')
        p.stdin.flush()
        p.communicate()
      except:
        pass
    # save settings to ini file
    if store_config:
      if not os.path.exists(os.path.expanduser('~')+'/.plotting_gui'):
        os.mkdir(os.path.expanduser('~')+'/.plotting_gui')
      # ConfigObj config structure for profiles
      self.config_object['profiles']={}
      for ignore, profile in self.profiles.items():
        profile.write(self.config_object['profiles'])
      del self.config_object['profiles']['default']
      self.config_object['MouseMode']={
                                   'active': self.mouse_mode
                                   }
      self.config_object.write()
    # close open subwindows
    for window in self.open_windows:
      window.destroy()
    # close ipython window
    if getattr(self, 'active_ipython', False):
      self.active_ipython.destroy()
    try:
      # if the windows is destroyed before the main loop has started.
      self.destroy()
      gtk.main_quit()
    except RuntimeError:
      pass

gobject.type_register(ApplicationMainWindow)
gobject.signal_new("plot-drawn", ApplicationMainWindow, gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, ())
