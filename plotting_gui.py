# -*- encoding: utf-8 -*-
'''
  Module for GTK GUI from plot.py program. 
  All general GUI functions are defined here.
'''
#################################################################################################
#                  Script for graphical user interface to plot measurement data                 #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -show plots from any MeasurementData structure defined in measurement_data_structure.py       #
# -change x,y and yerror columns via menu selection                                             #
# -export single or multiple files and combine data in one plot                                 #
# -print one or all plots (at the moment via linux command line)                                #
# -posibility to user define different gnuplot preferences freely                               #
# -posibility to store preferences in profiles and reload them later                            #
# -show and (export) gnuplot settings file                                                      #
# -show gnuplot errors in frontend                                                              #
# -fit pseudo voigt function                                                                    #
#                                                                                               #
# To do:                                                                                        #
# -create print dialog to select Printer and other print parameters                             #
# -fit any type of function                                                                     #
# -code cleanup                                                                                 #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing. 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import os, sys
import subprocess
import gobject
import gtk
import cairo
from time import sleep, time
# own modules
# Module to save and load variables from/to config files
from configobj import ConfigObj
from measurement_data_structure import MeasurementData
import measurement_data_plotting
from config.gnuplot_preferences import output_file_name,PRINT_COMMAND,titles
import config
from config import gnuplot_preferences
import file_actions
#----------------------- importing modules --------------------------

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = ["Werner Schweika", "Emmanuel Kenzinger", "Paul Zakalek", "Daniel Schumacher",  "All other Tester!"]
__license__ = "None"
__version__ = "0.6.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

DOWNLOAD_PAGE_URL='http://atzes.homeip.net/plotwiki/tiki-index.php?page=Download+Area'

#+++++++++++++++++++++++++ ApplicationMainWindow Class ++++++++++++++++++++++++++++++++++#
# TODO: Move some functions to other modules to have a smaller file
class ApplicationMainWindow(gtk.Window):
  '''
    Main window of the GUI.
    Everything the GUI does is in this Class.
  '''
  status_dialog=None
  
  def get_active_dataset(self):
    return self.measurement[self.index_mess]

  active_dataset=property(get_active_dataset)
  geometry=((0, 0), (800, 600))
  active_plot_geometry=(780, 550)
  
  #+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
  def __init__(self, active_session, parent=None, script_suf='', status_dialog=None):
    '''
      Class constructor which builds the main window with it's menus, buttons and the plot area.
      
      @param active_session A session object derived from GenericSession.
      @param parant Parent window.
      @param script_suf Suffix for script file name.
    '''
    global errorbars
    # TODO: remove global errorbars variable and put in session or m_d_structure
    #+++++++++++++++++ set class variables ++++++++++++++++++
    self.status_dialog=status_dialog
    self.heightf=100 # picture frame height
    self.widthf=100 # pricture frame width
    self.set_file_type=output_file_name.rsplit('.',1)[1] # export file type
    self.measurement=active_session.active_file_data # active data file measurements
    self.input_file_name=active_session.active_file_name # name of source data file
    self.active_session=active_session # session object passed by plot.py
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
    # TODO: call buffer directly from textview widget
    self.plot_options_buffer = self.plot_options_view.get_buffer()
    self.active_folder=os.path.realpath('.') # For file dialogs to stay in the active directory
    #----------------- set class variables ------------------


    # Create the toplevel window
    gtk.Window.__init__(self)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0]
                           , "config", "logo.png").replace('library.zip', ''))
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
        print "building menus failed: %s" % msg
    self.menu_bar = self.UIManager.get_widget("/MenuBar")
    self.menu_bar.show()

    # put menu at top position, only expand in x direction
    table.attach(self.menu_bar,
        # X direction #          # Y direction
        0, 3,                      0, 1,
        gtk.EXPAND | gtk.FILL,     0,
        0,                         0);
    # put toolbar at below menubar, only expand in x direction
    bar = self.UIManager.get_widget("/ToolBar")
    bar.set_tooltips(True)
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
    align = gtk.Alignment(0.5, 0.5, 0, 0) # center the entrys
    align.add(top_table)
    # put label below menubar on left column, only expand in x direction
    table.attach(align,
        # X direction           Y direction
        0, 1,                   2, 3,
        gtk.FILL,  gtk.FILL,
        0,                      0)

    # frame region for the image
    self.frame1 = gtk.Notebook()
    # TODO: do we need alignment?
    align = gtk.Alignment(0.5, 0.5, 1, 1)
    align.add(self.frame1)
    # image object for the plots
    # TODO: Reconsider image resizing.
    self.image = gtk.Image()    
    self.image_shown=False # variable to decrease changes in picture size
    self.image.set_size_request(0, 0)
    self.image_do_resize=False
    self.frame1.append_page(self.image, gtk.Label("Plot"))
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
    # put multiplot list right from the picture, expand only in y
    self.frame1.append_page(align, gtk.Label("Multiplot List"))

    #++++++++++ Create additional setting input for the plot ++++++++++
    align_table = gtk.Table(12, 2, False)
    # input for jumping to a data sequence
    page_label=gtk.Label()
    page_label.set_markup('Go to Plot:')
    align_table.attach(page_label,0,1,0,1,gtk.FILL,gtk.FILL,0,0)
    self.plot_page_entry=gtk.Entry()
    self.plot_page_entry.set_width_chars(4)
    self.plot_page_entry.set_text('0')
    align_table.attach(self.plot_page_entry,1,2,0,1,gtk.FILL,gtk.FILL,0,0)
    # checkbox for more Settings
    self.check_add=gtk.CheckButton(label='Show more options.', use_underline=True)
    align_table.attach(self.check_add,2,3,0,1,gtk.EXPAND|gtk.FILL,gtk.FILL,0,0)
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
    self.font_size_label.set_markup('Font size:')
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
      self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5) # title width
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5) # title width
      self.label2.set_text(self.measurement[self.index_mess].short_info)
      # TODO: put this to a different location
      self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)
      self.logx.set_active(self.measurement[self.index_mess].logx)
      self.logy.set_active(self.measurement[self.index_mess].logy)
      self.logz.set_active(self.measurement[self.index_mess].logz)
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

    # show the window, hide advanced settings and catch resize events
    self.show_all()
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

    if not self.active_session.DEBUG:
      # redirect script output to session objects
      self.active_session.stdout=RedirectOutput(self)
      self.active_session.stderr=RedirectError(self)
      sys.stdout=self.active_session.stdout
      sys.stderr=self.active_session.stderr

    while len(self.measurement)==0:
      while gtk.events_pending():
        gtk.main_iteration(False)
      return_status_ok=self.add_file(None)
      if not return_status_ok:
        self.main_quit(store_config=False)
        self.destroyed_directly=True
        return
    self.check_add.set_active(True)
    self.check_add.toggled()
    if self.status_dialog:
      self.status_dialog.hide()

    #+++++++++++++ connecting events ++++++++++++++
    self.connect("event-after", self.update_picture)
    self.connect("event-after", self.update_size)
    self.label.connect("activate",self.change) # changed entry triggers change() function 
    self.label2.connect("activate",self.change) # changed entry triggers change() function 
    self.image.connect('size-allocate', self.image_resize)
    self.plot_page_entry.connect("activate",self.iterate_through_measurements)
    self.check_add.connect("toggled",self.show_add_info)
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
    
    #------------- connecting events --------------

    self.replot()
    
    self.geometry=(self.get_position(), self.get_size())
    self.check_for_updates()

  #-------------------------------Window Constructor-------------------------------------#

  #++++++++++++++++++++++++++++++++++Event hanling+++++++++++++++++++++++++++++++++++++++#

  #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
  def update_size(self, widget, event):
    '''
      If resize event is triggered the window size variables are changed.
    '''
    if event.type==gtk.gdk.CONFIGURE:
      geometry= (self.get_position(), self.get_size())
      if geometry!=self.geometry:
        self.geometry=geometry
        self.widthf=self.frame1.get_allocation().width
        self.heightf=self.frame1.get_allocation().height

  def update_picture(self, widget, event):
    '''
      After releasing the mouse the picture gets replot.
    '''
    if event.type==gtk.gdk.FOCUS_CHANGE and self.active_plot_geometry!=(self.widthf, self.heightf):
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
      # ConfigObj Window parameters
      self.config_object['Window']={
                                    'size': self.geometry[1], 
                                    'position': self.geometry[0], 
                                    }
      self.config_object.write()
    for window in self.open_windows:
      window.destroy()
    try:
      # if the windows is destoryed before the main loop has started.
      gtk.main_quit()
    except RuntimeError:
      pass

  def activate_about(self, action):
    '''
      Show the about dialog.
    '''
    dialog = gtk.AboutDialog()
    dialog.set_program_name("Plotting GUI")
    dialog.set_version("v%s" % __version__)
    dialog.set_authors([__author__]+__credits__)
    dialog.set_copyright("© Copyright 2008-2010 Artur Glavic\n a.glavic@fz-juelich.de")
    dialog.set_website("http://www.fz-juelich.de/iff/Glavic_A/")
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
      self.measurement[self.index_mess].xdata=self.measurement[self.index_mess].dimensions().index(dim)
    elif action.get_name()[0]=='y':
      dim=action.get_name()[2:]
      self.measurement[self.index_mess].ydata=self.measurement[self.index_mess].dimensions().index(dim)
    elif action.get_name()[0]=='z':
      dim=action.get_name()[2:]
      self.measurement[self.index_mess].zdata=self.measurement[self.index_mess].dimensions().index(dim)
    elif action.get_name()[0]=='d':
      dim=action.get_name()[3:]
      self.measurement[self.index_mess].yerror=self.measurement[self.index_mess].dimensions().index(dim)
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
    # TODO: check if realy log was triggering this action
    else:
      self.measurement[self.index_mess].logx=self.logx.get_active()
      self.measurement[self.index_mess].logy=self.logy.get_active()
      self.measurement[self.index_mess].logz=self.logz.get_active()
    self.replot() # plot with new Settings
  
  def change_active_file(self, action):
    '''
      Change the active datafile for plotted sequences.
    '''
    index=int(action.get_name().split('-')[-1])
    object=sorted(self.active_session.file_data.items())[index]
    self.change_active_file_object(object)
  
  def change_active_file_object(self, object):
    '''
      Change the active file object from which the plotted sequences are extracted.
      
      @param object A list of MeasurementData objects from one file
    '''
    self.active_session.change_active(object)
    self.measurement=self.active_session.active_file_data
    self.input_file_name=object[0]
    # reset index to the first sequence in that file
    self.index_mess=0
    self.active_multiplot=False
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    for window in self.open_windows:
      window.destroy() 
    self.reset_statusbar()
    self.rebuild_menus()
    self.replot()
  
  def add_file(self, action):
    '''
      Import one or more new datafiles of the same type.
      
      @return List of names that have been imported.
    '''
    file_names=[]
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new datafile...', 
                                      action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                      buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    file_dialog.set_select_multiple(True)
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    file_dialog.set_current_folder(self.active_folder)
    for wildcard in self.active_session.FILE_WILDCARDS:
      filter = gtk.FileFilter()
      filter.set_name(wildcard[0])
      for pattern in wildcard[1:]:
        filter.add_pattern(pattern)
      file_dialog.add_filter(filter)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      self.active_folder=file_dialog.get_current_folder()
      file_names=file_dialog.get_filenames()
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
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
    # try to import the selected files and append them to the active sesssion
    if self.active_session.ONLY_IMPORT_MULTIFILE:
      self.active_session.add_file(file_names, append=True)
    else:
      for file_name in file_names:
        datasets=self.active_session.add_file(file_name, append=True)
        if len(datasets)>0:
          self.active_session.change_active(name=file_name)
    # set the last imported file as active
    self.measurement=self.active_session.active_file_data
    if len(self.measurement)==0:
      # file was selected but without producing any result
      # this can only be triggered when importing at startup
      if type(sys.stdout)!=file:
        sys.stdout.second_output=None
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
      status_dialog.hide()
    self.rebuild_menus()
    self.replot()
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
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
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
        name=file_dialog.get_filenames()[0]
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
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
        name=file_dialog.get_filenames()[0]
        if not name.endswith(".mdd"):
          name+=".mdd"
      elif response == gtk.RESPONSE_CANCEL:
        file_dialog.destroy()
        return False
      file_dialog.destroy()
      #----------------File selection dialog-------------------#
    self.active_session.reload_snapshot(name)
    self.measurement=self.active_session.active_file_data
    self.replot()

  def change_range(self,action):
    '''
      Change plotting range according to textinput.
    '''
    # set the font size
    try:
      self.active_session.font_size=float(self.font_size.get_text())
      self.replot()
    except ValueError:
      self.active_session.font_size=24.
      self.font_size.set_text('24')
      self.replot()
    # get selected ranges
    xin=self.x_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
    yin=self.y_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
    zin=self.z_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
    # erase old settings
    lines_old=self.measurement[self.index_mess].plot_options.split('\n')
    lines_new=[]
    for line in lines_old:
      # remove lines, which contain scaling settings
      if not ((' autoscale ' in line)|\
        (' xrange ' in line)|\
        (' yrange ' in line)|\
        (' zrange ' in line)|\
        (' cbrange ' in line)):
        lines_new.append(line)
    self.measurement[self.index_mess].plot_options="\n".join(lines_new)
    # only use settings, if they are valid numbers
    if (len(xin)==2) and\
        ((xin[0].replace('-','').replace('e','').replace('.','',1).isdigit())|\
          (xin[0]==''))&\
        ((xin[1].replace('-','').replace('e','').replace('.','',1).isdigit())|\
        (xin[1]=='')):
      self.x_range='set xrange ['+str(xin[0])+':'+str(xin[1])+']'
    else:
      self.x_range='set autoscale x'
      self.x_range_in.set_text('')
    if (len(yin)==2) and\
        ((yin[0].replace('-','').replace('e','').replace('.','',1).isdigit())|\
          (yin[0]==''))&\
        ((yin[1].replace('-','').replace('e','').replace('.','',1).isdigit())|\
        (yin[1]=='')):
      self.y_range='set yrange ['+str(yin[0])+':'+str(yin[1])+']'
    else:
      self.y_range='set autoscale y'
      self.y_range_in.set_text('')
    if (len(zin)==2) and\
        ((zin[0].replace('-','').replace('e','').replace('.','',1).isdigit())|\
          (zin[0]==''))&\
        ((zin[1].replace('-','').replace('e','').replace('.','',1).isdigit())|\
        (zin[1]=='')):
      self.z_range='set zrange ['+str(zin[0])+':'+str(zin[1])+']\nset cbrange ['+str(zin[0])+':'+str(zin[1])+']'
    else:
      self.z_range='set autoscale z\nset autoscale cb'
      self.z_range_in.set_text('')
    # add the ranges to the plot options
    self.measurement[self.index_mess].plot_options=self.measurement[self.index_mess].plot_options+\
    self.x_range+\
    '\n'+self.y_range+\
    '\n'+self.z_range+'\n'
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
    text_filed.set_markup(plot_text)
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
    filter_dialog=gtk.Dialog(title='Filter the plotted data:', parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
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
    # add dialog buttons
    filter_dialog.add_button('New Filter',3)
    filter_dialog.add_button('OK',1)
    filter_dialog.add_button('Apply changes',2)
    filter_dialog.add_button('Cancel',0)
    filter_dialog.show_all()
    # open dialog and wait for a response
    filter_dialog.connect("response", self.change_data_filter_response, table, table_rows, filters, data)

  def change_data_filter_response(self, filter_dialog, response, table, table_rows, filters, data):
    '''
      Response actions for the add data filter dialog.
    '''
    # if the response is 'New Filter' add a new filter row and rerun the dialog
    if response==3:
      filters.append(self.get_new_filter(table,table_rows,data))
      table_rows+=1
      table.resize(table_rows,5)
      filter_dialog.show_all()
    # if response is apply change the dataset filters
    if response==1 or response==2:
      new_filters=[]
      for filter_widgets in filters:
        if filter_widgets[0].get_active()==0:
          continue
        new_filters.append(\
          (filter_widgets[0].get_active()-1,\
          float(filter_widgets[1].get_text()),\
          float(filter_widgets[2].get_text()),\
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
      transformations_dialog.add_button('Add transformation',2)
      transformations_dialog.add_button('Apply changes',1)
      transformations_dialog.add_button('Cancel',0)
    except AttributeError:
      transformations_dialog.vbox.pack_end(trans_box,False)
      button=gtk.Button('Add transformation')
      button.connect('clicked', lambda *ignore: transformations_dialog.response(2))
      transformations_dialog.vbox.pack_end(button,False)
      button=gtk.Button('Apply changes')
      button.connect('clicked', lambda *ignore: transformations_dialog.response(1))
      transformations_dialog.vbox.pack_end(button,False)
      button=gtk.Button('Cancel')
      button.connect('clicked', lambda *ignore: transformations_dialog.response(0))
      transformations_dialog.vbox.pack_end(button,False)
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
      if did_calculate:
        self.replot()
    eii_dialog.destroy()
    if len(int_int_values)>0:
      self.show_integrated_intensities(int_int_values)

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
    cps_dialog=gtk.Dialog(title='Select new color pattern:')
    pattern_box=gtk.combo_box_new_text()
    # drop down menu for the pattern selection
    for pattern in pattern_names:
      pattern_box.append_text(pattern)
    pattern_box.show_all()
    cps_dialog.vbox.add(pattern_box)
    cps_dialog.add_button('OK', 1)
    cps_dialog.add_button('Cancel', 0)
    result=cps_dialog.run()
    if result==1:
      self.file_actions.activate_action('change_color_pattern', 
                                        gnuplot_preferences.defined_color_patterns[pattern_names[pattern_box.get_active()]])
    cps_dialog.destroy()
    self.replot()



  def fit_dialog(self,action, size=(800, 250), position=None):
    '''
      A dialog to fit the data with a set of functions.
      
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
    dataset=self.measurement[self.index_mess]
    if (dataset.fit_object==None):
      self.file_actions.activate_action('create_fit_object')
    fit_session=dataset.fit_object
    fit_dialog=gtk.Dialog(title='Fit...')
    fit_dialog.set_default_size(size[0], size[1])
    if position!=None:
      fit_dialog.move(position[0], position[1])
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    align, buttons=fit_session.get_dialog(self, fit_dialog)
    sw.add_with_viewport(align) # add fit dialog
    fit_dialog.vbox.add(sw)
    actions_table=gtk.Table(len(buttons),1,False)
    for i, button in enumerate(buttons):
      actions_table.attach(button, i, i+1, 0, 1, gtk.FILL, gtk.FILL, 0, 0);
    try:
      fit_dialog.get_action_area().pack_end(actions_table, expand=False, fill=True, padding=0)
    except AttributeError:
      fit_dialog.vbox.pack_end(actions_table, expand=False, fill=True, padding=0)
    fit_dialog.show_all()
    self.open_windows.append(fit_dialog)

  def show_add_info(self,action):
    '''
      Show or hide advanced options widgets.
    '''
    # TODO: Do we realy need this?
    if self.check_add.get_active():
#      if action==None: # only resize picture if the length of additional settings changed
#        if (self.logz.get_property('visible') & (self.measurement[self.index_mess].zdata<0))\
#        |((not self.logz.get_property('visible')) & (self.measurement[self.index_mess].zdata>=0)):
#          self.image.hide()
#          self.image_shown=False
#      else:
#        self.image.hide()
#        self.image_shown=False
      self.x_range_in.show()
      self.x_range_label.show()
      self.y_range_in.show()
      self.y_range_label.show()
      self.font_size.show()
      self.check_add.set_label('')
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
    else:
      if not action==None: # only change picture size if chack_add button is triggered
        self.image.hide()
        self.image_shown=False
      self.x_range_in.hide()
      self.x_range_label.hide()
      self.y_range_in.hide()
      self.y_range_label.hide()
      self.z_range_in.hide()
      self.z_range_label.hide()
      self.font_size.hide()
      self.logx.hide()
      self.logy.hide()
      self.plot_options_button.hide()
      self.logz.hide()
      self.view_left.hide()
      self.view_up.hide()
      self.view_down.hide()
      self.view_right.hide()
      self.check_add.set_label('Show more options.')

      

  def apply_to_all(self,action): 
    '''
      Apply changed plotsettings to all plots. This includes x,y,z-ranges,
      logarithmic plotting and the custom plot settings.
    '''
    # TODO: Check if all options are included here
    for dataset in self.measurement:
      dataset.xdata=self.measurement[self.index_mess].xdata
      dataset.ydata=self.measurement[self.index_mess].ydata
      dataset.zdata=self.measurement[self.index_mess].zdata
      dataset.yerror=self.measurement[self.index_mess].yerror
      dataset.logx=self.measurement[self.index_mess].logx
      dataset.logy=self.measurement[self.index_mess].logy
      dataset.logz=self.measurement[self.index_mess].logz
      dataset.plot_options=self.measurement[self.index_mess].plot_options
      self.reset_statusbar()
      print 'Applied settings to all Plots!'

  def add_multiplot(self,action): 
    '''
      Add or remove the active dataset from multiplot list, 
      which is a list of plotnumbers of the same Type.
    '''
    # TODO: Review the multiplot stuff!
    if (action.get_name()=='AddAll')&(len(self.measurement)<40): # dont autoadd more than 40
      for i in range(len(self.measurement)):
        self.do_add_multiplot(i)
    else:
      self.do_add_multiplot(self.index_mess)

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
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
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
      response = file_dialog.run()
      if response != gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        file_dialog.destroy()
        return None
      common_file_prefix=file_dialog.get_filename().rsplit('.gp', 1)[0]
      file_dialog.destroy()
      if self.active_multiplot:
        for plotlist in self.multiplot:
          itemlist=[item[0] for item in plotlist]
          if self.measurement[self.index_mess] in itemlist:
            plot_text=measurement_data_plotting.create_plot_script(
                                          self.active_session, 
                                          [item[0] for item in plotlist], 
                                          common_file_prefix, 
                                          plotlist.title, 
                                          plotlist[0][0].short_info, 
                                          [item[0].short_info for item in plotlist], 
                                          errorbars,
                                          common_file_prefix + '.png',
                                          fit_lorentz=False, 
                                          output_file_prefix=common_file_prefix, 
                                          sample_name=plotlist.sample_name)
        file_numbers=[]
        for j, dataset in enumerate(itemlist):
          for i, attachedset in enumerate(dataset.plot_together):
            file_numbers.append(str(j)+'-'+str(i))
            attachedset.export(common_file_prefix+str(j)+'-'+str(i)+'.out')
      else:
        plot_text=measurement_data_plotting.create_plot_script(
                           self.active_session, 
                           [self.measurement[self.index_mess]],
                           common_file_prefix, 
                           '', 
                           self.measurement[self.index_mess].short_info,
                           [object.short_info for object in self.measurement[self.index_mess].plot_together],
                           errorbars, 
                           output_file=common_file_prefix + '.png',
                           fit_lorentz=False, 
                           output_file_prefix=common_file_prefix)
        file_numbers=[]
        j=0
        dataset=self.measurement[self.index_mess]
        for i, attachedset in enumerate(dataset.plot_together):
          file_numbers.append(str(j)+'-'+str(i))
          attachedset.export(common_file_prefix+str(j)+'-'+str(i)+'.out')
      open(common_file_prefix+'.gp', 'w').write(plot_text+'\n')
      
      #----------------File selection dialog-------------------#      
    elif action.get_name()=='ExportAll':
      for dataset in self.measurement:
        self.last_plot_text=self.plot(self.active_session, 
                                      dataset.plot_together,
                                      self.input_file_name,
                                      dataset.short_info,
                                      [object.short_info for object in dataset.plot_together],
                                      errorbars,
                                      fit_lorentz=False)
        self.reset_statusbar()
        print 'Export plot number '+dataset.number+'... Done!'
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
            multi_file_name=file_dialog.get_filename()
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
          self.active_folder=file_dialog.get_current_folder()
          self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
          new_name=file_dialog.get_filename()
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
      print 'Printed with: '+(print_command % self.active_session.TEMP_DIR+'plot_temp.ps')
      subprocess.call((print_command % self.active_session.TEMP_DIR+'plot_temp.ps').split(" ", 1))
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
      for i, dataset in enumerate(plot_list): # combine all plot files in one print statement
        self.last_plot_text=self.plot(self.active_session, 
                                      [dataset],
                                      self.input_file_name,
                                      dataset.short_info,
                                      [object.short_info for object in dataset.plot_together],
                                      errorbars, 
                                      output_file=self.active_session.TEMP_DIR+'plot_temp_%i.ps' % i,
                                      fit_lorentz=False)
        print_string+=self.active_session.TEMP_DIR+('plot_temp_%i.ps ' % i)
      print 'Printed with: ' + print_command % print_string
      subprocess.call((print_command % print_string).split(" ", 1))

  def print_plot_dialog(self, action):
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
      measurements=[self.measurement[self.index_mess]]
      PrintDatasetDialog(measurements, self)

  if False and gtk.pygtk_version[1]>=10:
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

  def open_ipy_console(self, action):
    '''
      In debug mode this opens a window with an IPython console,
      which has direct access to all important objects.
    '''
    from ipython_view import IPythonView
    import pango
    import sys
    import numpy
    import scipy
    from copy import deepcopy

    FONT = "Mono 8"

    ipython_dialog= gtk.Dialog(title="IPython Console", parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
    ipython_dialog.set_size_request(750,550)
    ipython_dialog.set_resizable(True)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
    ipview = IPythonView("""    This is an interactive IPython session with direct access to the program.
    You have the whole python functionality and can interact with the programs objects.

    Functions:
      replot \tFunction to replot the dataset
      dataset \tFunction to get the active MeasurementData object
      get_xyz \tReturn 3 numpy arrays of the x,y and z columns from the active dataset
      get_all \tReturn all data columns of the active dataset
      new_xyz \tCreate a new plot with changed columns, takes three lists or 
              \tarrays as input. For line plots the last parameter is 'None'.
      new_all \tCreate a new plot from a list of all data columns, the list 
              \thas to have the same length as returned by get_all

    Objects:
      session \tThe active session containing the data objects and settings
      plot_gui \tThe window object with all window related funcitons
      self \t\tThe IPythonView object.
    Modules:
      np \tNumpy
      sp \tScipy

    Remark: This functionality is mainly for developers. If you are a user experienced
            in python it is recommanded to use the get_... and new_... functions.\n\n""")
    ipview.modify_font(pango.FontDescription(FONT))
    ipview.set_wrap_mode(gtk.WRAP_CHAR)
    sys.stderr=ipview
    sw.add(ipview)
    ipython_dialog.vbox.add(sw)
    ipython_dialog.show_all()
    ipython_dialog.connect('delete_event',lambda x,y:False)
    def reset(action):
      sys.stdout=sys.__stdout__
      sys.stderr=sys.__stderr__
    ipython_dialog.connect('destroy', reset)
    x=self.get_active_dataset().data[self.get_active_dataset().xdata].values
    y=self.get_active_dataset().data[self.get_active_dataset().ydata].values
    z=self.get_active_dataset().data[self.get_active_dataset().zdata].values
    # create functions for the use with ipython
    def get_xyz():
      # returns numpy arrays of x,y and z
      d=self.get_active_dataset()
      xi=d.xdata
      yi=d.ydata
      zi=d.zdata
      x=numpy.array(d.data[xi].values)
      y=numpy.array(d.data[yi].values)
      if zi>=0:
        z=numpy.array(d.data[zi].values)
      else:
        z=None
      return x, y, z
    def get_all():
      # returns a list of all columns as nump arrays
      d=self.get_active_dataset()
      units=d.units()
      dims=d.dimensions()
      data_list=[numpy.array(item.values) for item in d.data]
      print "Returning columns: [" +\
          ",\n                    ".join(["%2i: %s [%s]" % (i, dims[i], units[i]) for i in range(len(units)) ]) +"]"
      return data_list
    def new_xyz(x, y, z=None):
      # create new plot of changed x,y and z columns
      d=self.get_active_dataset()
      xi=d.xdata
      yi=d.ydata
      zi=d.zdata
      newd=deepcopy(d)
      newd.data[xi].values=list(x)
      newd.data[yi].values=list(y)
      if zi>0:
        newd.data[zi].values=list(z)
      newd.short_info+=" processed"
      self.measurement.append(newd)
      self.index_mess=len(self.measurement)-1
      self.replot()
    def new_all(new_list):
      # create a new plot from all columns
      d=self.get_active_dataset()
      newd=deepcopy(d)
      for i, col in enumerate(newd.data):
        col.values=list(new_list[i])
      newd.short_info+=" processed"
      self.measurement.append(newd)
      self.index_mess=len(self.measurement)-1
      self.replot()
      
    # add variables to ipython namespace
    ipview.updateNamespace({
                       'session': self.active_session, 
                       'plot_gui': self, 
                       'self': ipview, 
                       'dataset': self.get_active_dataset, 
                       'replot': self.replot, 
                       'get_xyz': get_xyz, 
                       'new_xyz': new_xyz, 
                       'get_all': get_all, 
                       'new_all': new_all, 
                       'np': numpy, 
                       'sp': scipy, 
                       })

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
    
    self.read_window_config()
    return True

  def read_window_config(self):
    '''
      Read the window config parameters from the ConfigObj.
    '''
    if 'Window' in self.config_object:
      x, y=self.config_object['Window']['position']
      width, height=self.config_object['Window']['size']
      # Set the main windwo size to default or the last settings saved in config file
      self.set_default_size(width, height)
      self.move(x, y)
    else:
      self.set_default_size(700, 600)

  def check_for_update_now(self):
    '''
      Read the wiki download area page to see, if there is a new version available.
      
      @return Newer version number or None
    '''
    import socket
    import urllib
    # Open the wikipage, timeout if server is offline
    socket.setdefaulttimeout(3)
    try:
      download_page=urllib.urlopen(DOWNLOAD_PAGE_URL)
    except IOError, ertext:
      print 'Error accessing update server: %s' % ertext
      return None
    lines=download_page.readlines()
    if self.config_object['Update']['CheckBeta']:
      lines=filter(lambda line: 'Latest' in line and 'Version' in line, lines)
    else:
      lines=filter(lambda line: 'Latest stable Version' in line, lines)
    try:
      version=max(map(lambda line: line.split('Version')[-1].split(':')[0].strip(), lines))
      if version>__version__:
        return version
      else:
        return None
    except ValueError:
      return None

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
      if new_version:
        dia= gtk.MessageDialog(parent=self, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, 
                               message_format="There is a new version (%s) at %s ." % (new_version, DOWNLOAD_PAGE_URL))
        dia.run()
        dia.destroy()
  
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
    self.image.set_from_pixbuf(pixbuf)
    return True

  def image_resize(self, widget, rectangel):
    '''
      Scale the image during a resize.
    '''
    if self.image_do_resize:
      self.image_do_resize=False
      try:
        # if no image was set, there is not self.image_pixbuf
        pixbuf=self.image_pixbuf.scale_simple(rectangel.width, rectangel.height, gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
      except AttributeError:
        pass
    else:
      self.image_do_resize=True

  def splot(self, session, datasets, file_name_prefix, title, names, 
            with_errorbars, output_file=gnuplot_preferences.output_file_name, 
            fit_lorentz=False, sample_name=None, show_persistent=False):
    '''
      Plot via script file instead of using python gnuplot pipeing.
      
      @return Gnuplot error messages, which have been reported
    '''
    return measurement_data_plotting.gnuplot_plot_script(session, 
                                                         datasets,
                                                         file_name_prefix, 
                                                         self.script_suf, 
                                                         title,
                                                         names,
                                                         with_errorbars,
                                                         output_file,
                                                         fit_lorentz=False, 
                                                         sample_name=sample_name, 
                                                         show_persistent=show_persistent)

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
      self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
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

  def replot(self):
    '''
      Recreate the current plot and clear statusbar.
    '''
    global errorbars
    # change label and plot other picture
    self.show_add_info(None)
    # set log checkbox according to active measurement
    self.logx.set_active(self.measurement[self.index_mess].logx)
    self.logy.set_active(self.measurement[self.index_mess].logy)
    self.logz.set_active(self.measurement[self.index_mess].logz)
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
          self.label.set_width_chars(len(plotlist.sample_name)+5)
          self.label.set_text(plotlist.sample_name)
          self.label2.set_width_chars(len(plotlist.title)+5)
          self.label2.set_text(plotlist.title)
    else:
      self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
      self.label.set_text(self.measurement[self.index_mess].sample_name)
      self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
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
      print 'Gnuplot error!'
      self.show_last_plot_params(None)
    else:
      self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
      self.active_plot_geometry=(self.widthf, self.heightf)
      self.reset_statusbar()
      self.set_image()
      if not self.active_multiplot:
        self.measurement[self.index_mess].preview=self.image_pixbuf.scale_simple(100, 50, gtk.gdk.INTERP_BILINEAR)
    self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)

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
  # TODO: Add unit transformation to GUI.
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
      for dimension in self.measurement[self.index_mess].dimensions():
        output+="         <menuitem action='x-"+dimension+"'/>\n"
        self.added_items=self.added_items+(("x-"+dimension, None,dimension,None,None,self.change),)
      output+='''
            </menu>
            <menu action='yMenu'>
              <menuitem action='y-number'/>
        '''
      for dimension in self.measurement[self.index_mess].dimensions():
        output+="            <menuitem action='y-"+dimension+"'/>\n"
        self.added_items=self.added_items+(("y-"+dimension, None,dimension,None,None,self.change),)
      if self.measurement[self.index_mess].zdata>=0:
        output+='''
              </menu>
              <placeholder name='zMenu'>
              <menu action='zMenu'>
          '''
        for dimension in self.measurement[self.index_mess].dimensions():
          output+="          <menuitem action='z-"+dimension+"'/>\n"
          self.added_items=self.added_items+(("z-"+dimension, None,dimension,None,None,self.change),)
        output+="</menu></placeholder>\n"
      else:
        output+='''
              </menu>      
              <placeholder name='zMenu'/>'''
      output+='''
            <menu action='dyMenu'>
        '''
      for dimension in self.measurement[self.index_mess].dimensions():
        output+="              <menuitem action='dy-"+dimension+"'/>\n"
        self.added_items=self.added_items+(("dy-"+dimension, None,dimension,None,None,self.change),)
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
        <menuitem action='Next'/>
        <menuitem action='Prev'/>
        <menuitem action='First'/>
        <menuitem action='Last'/>
        <separator name='static3'/>
        <menuitem action='AddMulti'/>
        <menuitem action='AddAll'/>
        <separator name='static4'/>
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
          </placeholder>        
          <placeholder name='y-actions'/>'''
      else:
        output+='''
          <placeholder name='z-actions'/>
          <placeholder name='y-actions'>
          <menuitem action='CombinePoints'/>
          </placeholder>'''
    output+='''
        <separator name='static6'/>
      </menu>
      <menu action='ExtrasMenu'>
        <menuitem action='Makro'/>
        <menuitem action='LastMakro'/>
        <menuitem action='History'/>
        <menuitem action='OpenConsole'/>
      </menu>
      <separator name='static13'/>
      <menu action='HelpMenu'>
        <menuitem action='ShowConfigPath'/>
        <menuitem action='About'/>
        '''
    if self.active_session.DEBUG:
      output+='''
      '''
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
      <toolitem action='ErrorBars'/>
      <separator name='static11'/>
      <toolitem action='AddMulti'/>
      <toolitem action='MultiPlot'/>
      <separator name='static12'/>
      <toolitem action='SaveSnapshot'/>
      <toolitem action='LoadSnapshot'/>
      <separator name='static13'/>
      <toolitem action='ShowPersistent'/>
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
        "Print All Plots...", "<control><shift>P",                       # label, accelerator
        None,                          # tooltip
        self.print_plot ),
      ( "Quit", gtk.STOCK_QUIT,                    # name, stock id
        "_Quit", "<control>Q",                     # label, accelerator
        "Quit",                                    # tooltip
        self.main_quit ),
      ( "About", None,                             # name, stock id
        "About", None,                    # label, accelerator
        "About",                                   # tooltip
        self.activate_about ),
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
        "Show File Import Informations", None,                     # label, accelerator
        "Show the information from the file import in this session.",                                    # tooltip
        self.show_status_dialog),
      ( "FilterData", None,                    # name, stock id
        "Filter the data points", None,                     # label, accelerator
        None,                                    # tooltip
        self.change_data_filter),
      ( "TransformData", None,                    # name, stock id
        "Transform the Units/Dimensions", None,                     # label, accelerator
        None,                                    # tooltip
        self.unit_transformation),
      ( "CrossSection", None,                    # name, stock id
        "Cross-Section...", None,                     # label, accelerator
        None,                                    # tooltip
        self.extract_cross_section),
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
      ( "SelectColor", None,                    # name, stock id
        "Color Pattern...", None,                     # label, accelerator
        None,                                    # tooltip
        self.change_color_pattern),
      ( "Apply", gtk.STOCK_CONVERT,                    # name, stock id
        "Apply", None,                     # label, accelerator
        "Apply current plot settings to all sequences",                                    # tooltip
        self.apply_to_all),
      ( "ExportAll", gtk.STOCK_EXECUTE,                    # name, stock id
        "Exp. _All", None,                     # label, accelerator
        "Export all sequences",                                    # tooltip
        self.export_plot),
      ( "ErrorBars", gtk.STOCK_ADD,                    # name, stock id
        "E.Bars", None,                     # label, accelerator
        "Toggle errorbars",                                    # tooltip
        self.toggle_error_bars),
      ( "AddMulti", gtk.STOCK_JUMP_TO,                    # name, stock id
        "_Add", '<alt>a',                     # label, accelerator
        "Add/Remove plot to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "AddAll", gtk.STOCK_JUMP_TO,                    # name, stock id
        "Add all to Multiplot", None,                     # label, accelerator
        "Add/Remove all sequences to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "FitData", None,                    # name, stock id
        "_Fit data...", "<control>F",                     # label, accelerator
        "Dialog for fitting of a function to the active dataset.",                                    # tooltip
        self.fit_dialog),
      ( "MultiPlot", gtk.STOCK_YES,                    # name, stock id
        "Multi", None,                     # label, accelerator
        "Show Multi-plot",                                    # tooltip
        self.export_plot),
      ( "MultiPlotExport", None,                    # name, stock id
        "Export Multi-plots", None,                     # label, accelerator
        "Export Multi-plots",                                    # tooltip
        self.export_plot),
      ( "OpenConsole", None,                    # name, stock id
        "Open IPython Console", None,                     # label, accelerator
        None,                                    # tooltip
        self.open_ipy_console),
      ( "ShowPersistent", gtk.STOCK_FULLSCREEN,                    # name, stock id
        "Open Persistent Gnuplot Window", None,                     # label, accelerator
        None,                                    # tooltip
        self.plot_persistent),
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

#------------------------- ApplicationMainWindow Class ----------------------------------#

class StatusDialog(gtk.Dialog):
  '''
    A Dialog to show a changing text with scrollbar.
  '''
  
  def __init__(self, title=None, parent=None, flags=0, buttons=None, initial_text=''):
    '''
      Class constructor. Creates a Dialog window with scrollable TextView.
    '''
    gtk.Dialog.__init__(self, title, parent, flags, buttons)
    self.textview=gtk.TextView()
    self.buffer=self.textview.get_buffer()
    self.buffer.set_text(initial_text)
    # attach the textview inside a scrollbar widget
    self.scrollwidget=gtk.ScrolledWindow()
    self.scrollwidget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.scrollwidget.add(self.textview)
    self.vbox.add(self.scrollwidget)
    self.end_iter=self.buffer.get_end_iter()
    self.end_mark=self.buffer.create_mark('End', self.end_iter, False)
  
  def write(self, text):
    '''
      Append a string to the buffer and scroll at the end, if it was visible before.
    '''
    if type(text) is not unicode:
      utext=unicode(text, errors='ignore')
    else:
      utext=text
    # if the scrollbar is below 98% it is set to be at the bottom.
    adj=self.scrollwidget.get_vadjustment()
    end_visible= ((adj.value + adj.page_size) >= adj.upper*0.98)
    self.buffer.insert(self.end_iter, utext)
    if end_visible:
      self.textview.scroll_to_mark(self.end_mark, 0.)
    while gtk.events_pending():
      gtk.main_iteration()


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
    self.additional_commands=\
      active_class.plot_options_buffer.get_text(\
        active_class.plot_options_buffer.get_start_iter(),\
        active_class.plot_options_buffer.get_end_iter())
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

  def read(self,config_object):
    '''
      Read a profile from a dictionary, see write.
    '''
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
    string=string.replace('\b', '')
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
  
  def __init__(self, plotting_session):
    '''
      Class constructor, as in RedirectOutput and creates the message dialog.
    '''
    RedirectOutput.__init__(self, plotting_session)
    self.messagebox=gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK_CANCEL, 
                                      message_format='Errorbox')
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
    message_text='An unexpected error has occured:\n'
    message_text+='\n'.join(self.content)
    message_text+='\n\nDo you want to create a debug logfile?'
    # < signs can cause an gtk.Warning message because they get confused with markup tags
    message_text=message_text.replace('<', '[').replace('>', ']')
    self.messagebox.set_markup(unicode(message_text, 'utf-8', 'ignore'))
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
      debug_log.write('# This is a debug log file created by plot.py\n# The following error(s) have occured at %s.\n' % time.strftime('%m/%d/%y %H:%M:%S', time.localtime()))
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
    else:
      self.content=[]

#---------------------------- Redirection Filelike Objects -----------------------------

#++++++++++++++++++++++++++ PreviewDialog to select one plot +++++++++++++++++++++++++++

class PreviewDialog(gtk.Dialog):
  '''
    A dialog to show a list of plot previews to give the user the possibility to
    select one or more plots.
  '''
  main_table=None
  
  def __init__(self, data_dict, show_previews=True, **opts):
    '''
      Constructor setting up a gtk.Dialog with a table of preview items.
    '''
    gtk.Dialog.__init__(self, **opts)
    self.data_dict=data_dict
    # List to store unset previews to be created after the dialog is shown
    self.unset_previews=[]
    # List of image objects to be able to show or hide them
    self.images=[]
    # Will store the checkboxes corresponding to one plot
    self.check_boxes={}
    self.show_previews=show_previews
    self.vbox.add(self.get_scrolled_main_table())
    for key, datalist in sorted(data_dict.items()):
      self.add_line(key, datalist)
    toggle_previews=gtk.CheckButton('Show Previews', use_underline=False)
    toggle_previews.show()
    if show_previews:
      toggle_previews.set_active(True)
    toggle_previews.connect('toggled', self.toggle_previews)
    self.vbox.pack_end(toggle_previews, False)
  
  def run(self):
    '''
      Called to show the dialog and create unset previews.
    '''
    def stop_preview_creation(dialog, id):
      # Stop the preview creation on a response signal
      self.stop_preview=True
      self.response_id=id
    self.show()
    self.stop_preview=False
    self.connect('response',  stop_preview_creation)
    while gtk.events_pending():
      gtk.main_iteration(False)
    for image, dataset in self.unset_previews:
      if self.stop_preview:
        return self.response_id
      self.create_preview(image, dataset)
    return gtk.Dialog.run(self)
  
  def get_scrolled_main_table(self):
    '''
      Create the Table which holds all previews with scrollbars.
      
      @return The Table widget
    '''
    if self.main_table:
      return self.main_table
    self.last_line=0
    self.main_table=gtk.Table(4, 1, False)
    self.main_table.show()
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(self.main_table)
    sw.show()
    return sw
  
  def add_line(self, key, datalist):
    '''
      Add one line of previews to the main table.
      
      @param key The name of the file the previews in this line belong to.
      @param datalist List of MeasurementData object.
    '''
    if key.endswith('|raw_data'):
      return
    main_table=self.main_table
    line=self.last_line
    select_all=gtk.Button('Select All')
    select_none=gtk.Button('Unselect')
    label=gtk.Label(key)
    table=gtk.Table(len(datalist), 2, False)
    align=gtk.Alignment(0, 0.5, 0, 0)
    align.add(table)
    align.show()
    main_table.attach(select_all, 
            # X direction #          # Y direction
            0, 1,                      line+1, line+2,
            0,                       0,
            0,                         0)
    select_all.show()
    main_table.attach(select_none, 
            # X direction #          # Y direction
            1, 2,                      line+1, line+2,
            0,                       0,
            0,                         0)
    select_none.show()
    main_table.attach(label, 
            # X direction #          # Y direction
            0, 2,                      line, line+1,
            0,                       gtk.FILL,
            0,                         0)
    label.show()
    main_table.attach(align, 
            # X direction #          # Y direction
            2, 3,                      line, line+2,
            gtk.FILL,                       gtk.FILL,
            0,                         0)
    table.show()
    self.last_line+=2
    check_boxes=[]
    for i, dataset in enumerate(datalist):
      check_box=gtk.CheckButton(label="[%i] %s" % (i, dataset.short_info[:10]), use_underline=True)
      check_box.show()
      check_boxes.append(check_box)
      table.attach(check_box, 
            # X direction #          # Y direction
            i, i+1,                   1, 2,
            0,                       gtk.FILL,
            0,                         0)
      image=self.get_preview(dataset)
      self.images.append(image)
      # toggle the checkbox when button gets pressed
      #image.add_events(gtk.gdk.BUTTON_PRESS_MASK)
      #image.connect('button_press_event', lambda *ignore: check_box.toggle(True))
      if self.show_previews:
        image.show()
      eventbox=gtk.EventBox()
      eventbox.add(image)
      eventbox.show()
      eventbox.add_events(gtk.gdk.BUTTON_PRESS_MASK)
      eventbox.connect("button_press_event", self.test, check_box)
      table.attach(eventbox, 
            # X direction #          # Y direction
            i, i+1,                   0, 1,
            0,                       gtk.FILL,
            0,                         0)      
    self.check_boxes[key]=check_boxes
    select_all.connect('clicked', self.toggle_entries, check_boxes, True)
    select_none.connect('clicked', self.toggle_entries, check_boxes, False)
  
  def test(self, widget, action, check_box):
    check_box.set_active(not check_box.get_active())

  def toggle_entries(self, widget, check_boxes, set_value):
    '''
      Toggle all entreis in check_boxes to set_value.
    '''
    for check_box in check_boxes:
      check_box.set_active(set_value)
  
  def get_preview(self, dataset):
    '''
      Create an image as preview, if the dataset has no preview, add it to the
      list of unset previews.
    '''
    image=gtk.Image()
    if getattr(dataset, 'preview', False):
      image.set_from_pixbuf(dataset.preview)
    else:
      self.unset_previews.append( (image, dataset))
    return image
  
  def set_preview_parameters(self, plot_function, session, temp_file):
    '''
      Connect objects needed for preview creation.
    '''
    self.preview_plot=plot_function
    self.preview_session=session
    self.preview_temp_file=temp_file
  
  def create_preview(self, image, dataset):
    '''
      Create an preview of the dataset and render it onto image.
    '''
    if getattr(self, 'preview_plot', False):
      self.preview_plot(self.preview_session,
                                  [dataset],
                                  'preview',
                                  dataset.short_info,
                                  [object.short_info for object in dataset.plot_together],
                                  errorbars, 
                                  output_file=self.preview_temp_file,
                                  fit_lorentz=False)
      buf=gtk.gdk.pixbuf_new_from_file(self.preview_temp_file).scale_simple(100, 50, gtk.gdk.INTERP_BILINEAR)
      image.set_from_pixbuf(buf)
      dataset.preview=buf
    while gtk.events_pending():
      gtk.main_iteration(False)
  
  def get_active_keys(self):
    '''
      Return the keys and indices of the activeded check_box widgets.
    '''
    output={}
    for key, checkbox_list in self.check_boxes.items():
      output[key]=[]
      for i, check_box in enumerate(checkbox_list):
        if check_box.get_active():
          output[key].append(i)
    return output

  def get_active_objects(self):
    '''
      Return a list of data object for which the chackbox is set.
    '''
    active_dict=self.get_active_keys()
    data_dict=self.data_dict
    output=[]
    for key, active_list in sorted(active_dict.items()):
      for i in active_list:
        output.append(data_dict[key][i])
    return output
  def toggle_previews(self, widget):
    '''
      Show or hide all previews.
    '''
    if self.show_previews:
      self.show_previews=False
      for image in self.images:
        image.hide()
    else:
      self.show_previews=True
      for image in self.images:
        image.show()
      
  
#-------------------------- PreviewDialog to select one plot ---------------------------

#+++++++++++++++++++ FileChooserDialog with entries for with and height ++++++++++++++++

class ExportFileChooserDialog(gtk.FileChooserDialog):
  '''
    A file chooser dialog with two entries for with and height of an export image.
  '''
  
  def __init__(self, width, height, *args, **opts):
    '''
      Class constructor which adds two entries for with and height.
    '''
    opts['action']=gtk.FILE_CHOOSER_ACTION_SAVE
    opts['buttons']=(gtk.STOCK_CANCEL, 
                     gtk.RESPONSE_CANCEL, 
                     gtk.STOCK_SAVE, 
                     gtk.RESPONSE_OK)
    gtk.FileChooserDialog.__init__(self, *args, **opts)
    self.width=width
    self.height=height
    # Get the top moste table widget from the dialog
    table=self.vbox.get_children()[0].get_children()[0].get_children()[0].get_children()[0]
    label=gtk.Label('width')
    table.attach(label, 
            # X direction #          # Y direction
            3, 4,                      0, 1,
            0,                       gtk.FILL,
            0,                         0)
    label=gtk.Label('height')
    table.attach(label, 
            # X direction #          # Y direction
            4, 5,                      0, 1,
            0,                       gtk.FILL,
            0,                         0)
    width_ent=gtk.Entry()
    width_ent.set_text(width)      
    width_ent.set_width_chars(4)
    self.width_entry=width_ent
    height_ent=gtk.Entry()
    height_ent.set_text(height) 
    height_ent.set_width_chars(4)
    self.height_entry=height_ent
    table.attach(width_ent, 
            # X direction #          # Y direction
            3, 4,                      1, 2,
            0,                       gtk.FILL,
            0,                         0)
    table.attach(height_ent, 
            # X direction #          # Y direction
            4, 5,                      1, 2,
            0,                       gtk.FILL,
            0,                         0)
    table.show_all()
    
  def get_with_height(self):
    '''
      Return width and height of the entries.
    '''
    width=self.width
    height=self.height
    try:
      int_width=int(self.width_entry.get_text())
      width=str(int_width)
    except ValueError:
      pass
    try:
      int_height=int(self.height_entry.get_text())
      height=str(int_height)
    except ValueError:
      pass
    return width, height

#+++++++++++++++++++ FileChooserDialog with entries for with and height ++++++++++++++++

class MultiplotList(list):
  '''
    A list of measurements for a multiplot.
  '''
  def __init__(self, input_list):
    self.title="Multiplot"
    self.sample_name=str(input_list[0][0].sample_name)
    list.__init__(self, input_list)


#+++ Printing Dialog which imports creates PNG files for the datasets and sends it to a printer +++

class PrintDatasetDialog:
  '''
    Creating this class will create a gtk.PrintOperation and open a printing Dialog to
    print the datasets, supplied to the constructor.
    The datasets are exported to high-resolution PNG files and after processing through cairo
    get send to the Printer.
  '''
  
  def __init__(self, datasets, main_window, resolution=300):
    '''
      Constructor setting setting the objects datasets and running the dialog
      
      @param datasets A list of MeasurementData objects
      @param main_window The active ApplicationMainWindow instance
      @param resolution The resolution the printer, only if A4 is selected.
    '''
    self.datasets=datasets
    self.main_window=main_window
    self.width=resolution*11.666
    self.do_print()

  def do_print(self):
    '''
      Create a PrintOperation with the number of pages corresponding to the number of datasets.
      Afterwards the Printing dialog is run.
    '''
    old_terminal=gnuplot_preferences.set_output_terminal_png
    terminal_items=old_terminal.split()
    for i, item in enumerate(terminal_items):
      if item in ['lw', 'linewidth']:
        # scale the linewidth
        terminal_items[i+1]=str(int(terminal_items[i+1])*(self.width/1600.))
    terminal_items+=['crop']
    gnuplot_preferences.set_output_terminal_png=" ".join(terminal_items)
    print_op = gtk.PrintOperation()
    print_op.set_n_pages(len(self.datasets))
    # set landscape as default page orientation
    page_setup=gtk.PageSetup()
    page_setup.set_orientation(gtk.PAGE_ORIENTATION_LANDSCAPE)
    print_op.set_default_page_setup(page_setup)
    # connect the objects print method
    print_op.connect("draw_page", self.print_page)
    # connect preview method
    print_op.connect("preview", self.preview)
    # Custom entries to the print dialog
    print_op.connect("create-custom-widget", self.create_custom_widgets)
    print_op.connect("custom-widget-apply", self.read_custom_widgets)
    print_op.set_property('custom-tab-label', 'Plot Settings')
    # run the dialog
    res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.main_window)
    gnuplot_preferences.set_output_terminal_png=old_terminal

  def create_custom_widgets(self, operation):
    '''
      Create a table with custom entries for the print Dialog.
    '''
    table=gtk.Table(2, 2, False)
    label=gtk.Label('            Resolution: ')
    self.entry=gtk.Entry()
    self.entry.set_text(str(int(self.width/11.666)))
    table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    table.attach(self.entry, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    table.show_all()
    return table
  
  def read_custom_widgets(self, operation, widget):
    '''
      Read the settings supplied by the user.
    '''
    try:
      res=float(self.entry.get_text())
      self.width=res*11.666
    except ValueError:
      pass

  def print_page(self, operation=None, context=None, page_nr=None):
    '''
      Method called for every page to be rendered. Creates the plot and imports,draws it with cairo.
      
      @param operation gtk.PrintOperation
      @param context gtk.PrintContext
      @param current page number
    '''
    print "Plotting page %i/%i" % (page_nr+1, len(self.datasets))
    dataset=self.datasets[page_nr]
    self.plot(dataset)
    # get the cairo context to draw in
    page_setup=context.get_page_setup()
    cairo_context = context.get_cairo_context()
    p_width=page_setup.get_page_width('inch')*72
    p_height=page_setup.get_page_height('inch')*72
    # import the image
    surface=cairo.ImageSurface.create_from_png(self.main_window.active_session.TEMP_DIR+'plot_temp.png')
    # scale and center the image to fit the drawable area
    scale=min(p_width/surface.get_width(), p_height/surface.get_height())
    move_x=(p_width-scale*surface.get_width())/scale/2
    move_y=(p_height-scale*surface.get_height())/scale/2
    cairo_context.scale(scale,scale)
    cairo_context.set_source_surface(surface, move_x, move_y)
    cairo_context.paint()
    print "Sending page  %i/%i" % (page_nr+1, len(self.datasets))
    return

  def plot(self, dataset):
    '''
      Method to create one plot in print quality.
    '''
    session=self.main_window.active_session
    session.picture_width=str(int(self.width))
    session.picture_height=str(int(self.width/1.414))
    window=self.main_window
    window.plot(session,
                [dataset],
                session.active_file_name,
                dataset.short_info,
                [object.short_info for object in dataset.plot_together],
                errorbars, 
                output_file=session.TEMP_DIR+'plot_temp.png',
                fit_lorentz=False)
    
  def preview(self, operation, preview, context, parent):
    '''
      Create a preview of the plots to be printed.
    '''
    pass
