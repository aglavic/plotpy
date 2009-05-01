#!/usr/bin/env python
'''
  class for GTK GUI
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
import os
import gobject
import gtk
# own modules
# Module to save and load variables from/to config files
from configobj import ConfigObj
import measurement_data_plotting
from gnuplot_preferences import output_file_name,print_command,titles
import gnuplot_preferences
#----------------------- importing modules --------------------------

#+++++++++++++++++++++++++ ApplicationMainWindow Class ++++++++++++++++++++++++++++++++++#
class ApplicationMainWindow(gtk.Window):
  '''
    Everything the GUI does is in this Class.
  '''
  #+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
  def __init__(self, active_session, parent=None, script_suf='',preferences_file='',plugin_widget=None):
    '''
      Class constructor which builds the main window with it's menus, buttons and the plot area.
    '''
    global errorbars
    # TODO: remove global errorbars variable and put in session or m_d_structure
    #+++++++++++++++++ set class variables ++++++++++++++++++
    self.height=600 # window height
    self.width=700  # window width
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
    self.fit_lorentz=False
    # TODO: remove preferences file (also from m_d_plotting
    self.preferences_file=preferences_file
    # TODO: remove or reactivate plugin_widget
    self.plugin_widget=plugin_widget
    self.plot_options_window_open=False # is the dialog window for the plot options active?
    errorbars=False # show errorbars?
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
    #----------------- set class variables ------------------


    # Reading config file
    self.read_config_file()
    # Create the toplevel window
    gtk.Window.__init__(self)
    # TODO: check if we can savely remove this check and connect destroy directly
    try:
        self.set_screen(parent.get_screen())
    except AttributeError:
        self.connect('destroy', lambda *w: self.main_quit())
    # Set the title of the window, will be changed when the active plot changes
    self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
    # Set the main windwo size to default or the last settings saved in config file
    self.set_default_size(self.width, self.height)

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

    # custom widget on the right, can be used to include specific settings
    if not self.plugin_widget==None:
      align=gtk.Alignment(0, 0.05, 1, 0)
      align.add(self.plugin_widget)
      table.attach(align,
          # X direction #       # Y direction
          2, 3,                   3, 4,
          gtk.FILL,  gtk.EXPAND | gtk.FILL,
          0,                      0)

    #++++++++++ create image region and image for the plot ++++++++++
    # plot title label entries
    # TODO: don't lose entry when not pressing enter
    top_table=gtk.Table(2, 1, False)
    # first entry for sample name part of title
    self.label = gtk.Entry()
    self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5) # title width
    self.label.set_text(self.measurement[self.index_mess].sample_name)
    self.label.connect("activate",self.change) # changed entry triggers change() function 
    # second entry for additional infor part ofr title
    self.label2 = gtk.Entry()
    self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5) # title width
    self.label2.set_text(self.measurement[self.index_mess].short_info)
    self.label2.connect("activate",self.change) # changed entry triggers change() function 
    # TODO: put this to a different location
    self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)
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
    self.frame1 = gtk.Frame()
    self.frame1.set_shadow_type(gtk.SHADOW_IN)
    # TODO: do we need alignment?
    align = gtk.Alignment(0.5, 0.5, 1, 1)
    align.add(self.frame1)
    # image object for the plots
    # TODO: faster resizeing with scrollable window perhaps?
    self.image = gtk.Image()    
    self.image_shown=False # variable to decrease changes in picture size
    self.frame1.add(self.image)
    # put image below label on left column, expand frame in all directions
    table.attach(align,
        # X direction           Y direction
        0, 1,                   3, 4,
        gtk.EXPAND | gtk.FILL,  gtk.EXPAND | gtk.FILL,
        0,                      0)
    #---------- create image region and image for the plot ----------

    # Create region for multiplot list
    self.multi_list = gtk.Label();
    self.multi_list.set_markup(' Multiplot List: ')
    align = gtk.Alignment(0, 0.05, 1, 0) # align top
    align.add(self.multi_list)
    # put multiplot list right from the picture, expand only in y
    table.attach(align,
        # X direction           Y direction
        1, 2,                   3, 4,
        gtk.FILL,  gtk.EXPAND | gtk.FILL,
        0,                      0)

    #++++++++++ Create additional setting input for the plot ++++++++++
    # TODO: allways show or save view status of plot settings, use it every time!
    align_table = gtk.Table(12, 2, False)
    # input for jumping to a data sequence
    page_label=gtk.Label()
    page_label.set_markup('Go to Plot:')
    align_table.attach(page_label,0,1,0,1,gtk.FILL,gtk.FILL,0,0)
    self.plot_page_entry=gtk.Entry(max=len(self.measurement[-1].number))
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    self.plot_page_entry.connect("activate",self.iterate_through_measurements)
    align_table.attach(self.plot_page_entry,1,2,0,1,gtk.FILL,gtk.FILL,0,0)
    # checkbox for more Settings
    self.check_add=gtk.CheckButton(label='Show more options.', use_underline=True)
    self.check_add.connect("toggled",self.show_add_info)
    align_table.attach(self.check_add,2,3,0,1,gtk.EXPAND|gtk.FILL,gtk.FILL,0,0)
    # x,y ranges
    self.x_range_in=gtk.Entry()
    self.x_range_in.set_width_chars(6)
    self.x_range_in.connect("activate",self.change_range)
    self.x_range_label=gtk.Label()
    self.x_range_label.set_markup('x-range:')
    self.y_range_in=gtk.Entry()
    self.y_range_in.set_width_chars(6)
    self.y_range_in.connect("activate",self.change_range)
    self.y_range_label=gtk.Label()
    self.y_range_label.set_markup('y-range:')
    align_table.attach(self.x_range_label,3,4,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.x_range_in,4,5,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.y_range_label,5,7,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.y_range_in,7,9,0,1,gtk.FILL,gtk.FILL,0,0)
    # checkboxes for log x and log y
    # TODO: toggle logx,y according to active setting
    self.logx=gtk.CheckButton(label='log x', use_underline=True)
    self.logy=gtk.CheckButton(label='log y', use_underline=True)
    self.logx.set_active(self.measurement[self.index_mess].logx)
    self.logy.set_active(self.measurement[self.index_mess].logy)
    self.logx.connect("toggled",self.change)
    self.logy.connect("toggled",self.change)
    align_table.attach(self.logx,9,10,0,1,gtk.FILL,gtk.FILL,0,0)
    align_table.attach(self.logy,10,11,0,1,gtk.FILL,gtk.FILL,0,0)
    # button to open additional plot options dialog
    self.plot_options_button=gtk.ToolButton(gtk.STOCK_EDIT)
    self.plot_options_button.set_tooltip(gtk.Tooltips(),'Add custom Gnuplot commands')
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)
    align_table.attach(self.plot_options_button,11,12,0,2,gtk.FILL,gtk.FILL,0,0)
    # z range and log z checkbox
    self.z_range_in=gtk.Entry()
    self.z_range_in.set_width_chars(6)
    self.z_range_in.connect("activate",self.change_range)
    self.z_range_label=gtk.Label()
    self.z_range_label.set_markup('z-range:')
    self.logz=gtk.CheckButton(label='log z', use_underline=True)
    self.logz.set_active(self.measurement[self.index_mess].logz)
    self.logz.connect("toggled",self.change)
    # 3d Viewpoint buttons to rotate the view
    self.view_left=gtk.ToolButton(gtk.STOCK_GO_BACK)
    self.view_up=gtk.ToolButton(gtk.STOCK_GO_UP)
    self.view_down=gtk.ToolButton(gtk.STOCK_GO_DOWN)
    self.view_right=gtk.ToolButton(gtk.STOCK_GO_FORWARD)
    self.view_left.connect("clicked",self.change)
    self.view_up.connect("clicked",self.change)
    self.view_down.connect("clicked",self.change)
    self.view_right.connect("clicked",self.change)
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

    # Create statusbar
    self.statusbar = gtk.Statusbar()
    self.statusbar.set_has_resize_grip(True)
    # put statusbar below everything
    table.attach(self.statusbar,
        # X direction           Y direction
        0, 2,                   5, 6,
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
    self.connect("configure-event", self.update_size)
    #self.frame1.connect("size-allocate", self.update_frame_size)
    self.connect("event-after", self.update_picture)
    self.replot()
    self.check_add.set_active(True)
    self.check_add.toggled()

  #-------------------------------Window Constructor-------------------------------------#

  #++++++++++++++++++++++++++++++++++Event hanling+++++++++++++++++++++++++++++++++++++++#

  #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
  def update_size(self, widget, event):
    '''
      If resize event is triggered the window size variables are changed.
    '''
    # TODO: review resize handling of the image
    if (not ((self.width==event.width)&(self.height==event.height))):
      self.image.hide()
      self.image_shown=False
      self.width=event.width
      self.height=event.height

  def update_frame_size(self, widget, event): 
    '''
      If resize event is triggered the window size variables are changed.
      Not in use, will be removed after review.
    '''
    self.heightf=event.height
    self.widthf=event.width

  def update_picture(self, widget, event):
    '''
      The first event after starting to resize triggers rescaling the picture and showing it. 
      Is only executed, if this event is not a resize event. 
      So the picture is hidden while reesizing and reshown after.
    '''
    if not ((event.type == gtk.gdk.EXPOSE)|(event.type == gtk.gdk.CONFIGURE)|(event.type == gtk.gdk.PROPERTY_NOTIFY)|(event.type==gtk.gdk.WINDOW_STATE)):
      if (not self.image_shown):
        self.widthf=self.frame1.get_allocation().width
        self.heightf=self.frame1.get_allocation().height
        self.set_image()
        self.image.show()
        self.image_shown=True


  #----------------------------Interrupt Events----------------------------------#

  #++++++++++++++++++++++++++Menu/Toolbar Events+++++++++++++++++++++++++++++++++#
  def main_quit(self, action=None):
    '''
      When window is closed save the settings in home folder.
      All open dialogs are closed before exit.
    '''
    # TODO: put window setting in ConfigObject
    # Own config structure
    try:
      os.mkdir(os.path.expanduser('~')+'/.plotting_gui')
    except OSError:
      print ''
    config_file=open(os.path.expanduser('~')+'/.plotting_gui/plotting_gui.config','w')
    config_file.write('[ploting_gui_config]\n\t[window]'+\
    '\n\t\t[width]\n\t\t'+str(self.width)+\
    '\n\t\t[/width]\n\t\t[height]\n\t\t'+str(self.height)+'\n\t\t[/height]'+\
    '\n\t[/window]\n')
    config_file.write('[/plotting_gui_config]\n')
    config_file.close()
    # ConfigObject config structure for profiles
    self.config_object['profiles']={}
    for name, profile in self.profiles.items():
      profile.write(self.config_object['profiles'])
    del self.config_object['profiles']['default']
    self.config_object.write()
    for window in self.open_windows:
      window.destroy()
    gtk.main_quit()

  def activate_about(self, action):
    '''
      Show the about dialog.
    '''
    dialog = gtk.AboutDialog()
    dialog.set_name("Plotting GUI")
    dialog.set_copyright("\302\251 Copyright Artur Glavic\n a.glavic@fz-juelich.de")
    dialog.set_website("http://www.fz-juelich.de/iff")
    ## Close dialog on user response
    dialog.connect ("response", lambda d, r: d.destroy())
    dialog.show()
      
  def iterate_through_measurements(self, action):
    ''' 
      Change the active plot with arrows in toolbar.
    '''
    global errorbars
    # change number for active plot put it in the plot page entry box at the bottom
    if action.get_name()=='Prev':
      self.index_mess=max(0,self.index_mess-1)
      self.plot_page_entry.set_text(str(int(self.measurement[self.index_mess].number)))
    elif action.get_name()=='First':
      self.index_mess=0
      self.plot_page_entry.set_text(str(int(self.measurement[self.index_mess].number)))
    elif action.get_name()=='Last':
      self.index_mess=len(self.measurement)-1
      self.plot_page_entry.set_text(str(int(self.measurement[self.index_mess].number)))
    elif action.get_name()=='Next':
      self.index_mess=min(len(self.measurement)-1,self.index_mess+1)
      self.plot_page_entry.set_text(str(int(self.measurement[self.index_mess].number)))
    else:
      for i,data in enumerate(self.measurement):
        if int(data.number)<=int(self.plot_page_entry.get_text()):
          self.index_mess=i
      self.plot_page_entry.set_text(str(int(self.measurement[self.index_mess].number)))
    # check for valid number
    if self.index_mess>=len(self.measurement):
      self.index_mess=len(self.measurement)-1
    if self.index_mess<0:
      self.index_mess=0
    # change label and plot other picture
    self.show_add_info(None)
    # set log checkbox according to active measurement
    self.logx.set_active(self.measurement[self.index_mess].logx)
    self.logy.set_active(self.measurement[self.index_mess].logy)
    self.logz.set_active(self.measurement[self.index_mess].logz)
    # close all open dialogs
    for window in self.open_windows:
      window.destroy()
    # recreate the menus, if the columns for this dataset aren't the same
    self.rebuild_menus()
    # plot the data
    self.replot()


  def change(self,action):
    '''
      Change different plot settings triggered by different events.    
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
    elif action.get_name()[0]=='d':
      dim=action.get_name()[3:]
      self.measurement[self.index_mess].yerror=self.measurement[self.index_mess].dimensions().index(dim)
    elif action.get_name()=='FitLorentz':
      self.fit_lorentz = not self.fit_lorentz
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
    elif action==self.label:
      self.measurement[self.index_mess].sample_name=self.label.get_text()
    elif action==self.label2:
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
    object=self.active_session.file_data.items()[index]
    self.active_session.change_active(object)
    self.measurement=self.active_session.active_file_data
    self.input_file_name=object[0]
    # reset index to the first sequence in that file
    self.index_mess=0
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    self.plot_page_entry.set_max_length(len(self.measurement[-1].number))
    self.replot()
  
  def add_file(self, action):
    '''
      Import one or more new datafiles of the same type.
    '''
    file_names=[]
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new datafile...', 
                                      action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                      buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    file_dialog.set_select_multiple(True)
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    for wildcard in self.active_session.file_wildcards:
      filter = gtk.FileFilter()
      filter.set_name(wildcard[0])
      filter.add_pattern(wildcard[1])
      file_dialog.add_filter(filter)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      file_names=file_dialog.get_filenames()
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    # try to import the selected files and append them to the active sesssion
    for file_name in file_names:
      self.active_session.add_file(file_name, append=True)
      self.active_session.change_active(name=file_name)
    # set the last imported file as active
    self.measurement=self.active_session.active_file_data
    self.input_file_name=self.active_session.active_file_name
    self.index_mess=0
    self.plot_page_entry.set_width_chars(len(self.measurement[-1].number))
    self.plot_page_entry.set_text(str(int(self.measurement[0].number)))
    self.plot_page_entry.set_max_length(len(self.measurement[-1].number))
    self.replot()
    self.rebuild_menus()
    # TODO: do we need to return the file name?
    return file_names

  def change_range(self,action):
    '''
      Change plotting range according to textinput.
    '''
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
        (yin[1]=='')):
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
    label=gtk.Label()
    label.set_markup('Parameters for 3d plot:')
    table.attach(label, 0, 6, 9, 10, 0, 0, 0, 0);
    plotting_parameters_3d=gtk.Entry()
    plotting_parameters_3d.set_text(gnuplot_preferences.plotting_parameters_3d)
    table.attach(plotting_parameters_3d,
                # X direction #          # Y direction
                0, 3,                      10, 11,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    # additional Gnuplot commands
    label=gtk.Label()
    label.set_markup('Gnuplot commands executed additionally:')
    table.attach(label, 0, 6, 11, 12, 0, 0, 0, 0);
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(self.plot_options_view) # add textbuffer view widget
    table.attach(sw,
                # X direction #          # Y direction
                0, 6,                      12, 13,
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    table.show_all()
    #----------------- Adding input fields in table -----------------
    dialog.vbox.add(table) # add table to dialog box
    dialog.set_default_size(300,200)
    dialog.add_button('Apply and Replot',1) # button replot has handler_id 1
    dialog.connect("response", self.change_plot_options,
                  terminal_png, terminal_ps, x_label, y_label, z_label,
                  plotting_parameters, plotting_parameters_errorbars, plotting_parameters_3d)
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
    '''
    dialog.hide()
    sw.remove(self.plot_options_view)
    # reroute the button to open a new window
    self.plot_options_button.disconnect(self.plot_options_handler_id)
    self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)
    self.plot_options_window_open=False

  def change_plot_options(self,widget,action,\
    terminal_png,terminal_ps,x_label,y_label,z_label,\
      plotting_parameters,plotting_parameters_errorbars,plotting_parameters_3d):
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
    self.delete_name=action.get_label()

  def show_last_plot_params(self,action):
    '''
      Show a text window with the text, that would be used for gnuplot to
      plot the current measurement.
    '''    
    global errorbars
    plot_text=measurement_data_plotting.create_plot_script(
                         self.active_session, 
                         self.measurement[self.index_mess].plot_together,
                         self.input_file_name, 
                         self.script_suf, 
                         self.measurement[self.index_mess].short_info,
                         [object.short_info for object in self.measurement[self.index_mess].plot_together],
                         errorbars, 
                         output_file=self.active_session.temp_dir+'plot_temp.png',
                         fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
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


  def change_data_filter(self,action):
    '''
      A dialog to select filters, that remove points from the plotted dataset.
    '''
    # TODO: let filter dialog stay open while replotting
    filters=[]
    data=self.measurement[self.index_mess]
    filter_dialog=gtk.Dialog(title='Filter the plotted data:')
    filter_dialog.set_default_size(600,150)
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
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
    filter_dialog.add_button('New Filter',2)
    filter_dialog.add_button('Apply changes',1)
    filter_dialog.add_button('Cancel',0)
    filter_dialog.show_all()
    # open dialog and wait for a response
    response=filter_dialog.run()
    # if the response is 'New Filter' add a new filter row and rerun the dialog
    while(response==2):
      filters.append(self.get_new_filter(table,table_rows,data))
      table_rows+=1
      table.resize(table_rows,5)
      filter_dialog.show_all()
      response=filter_dialog.run()
    # if response is apply change the dataset filters
    if response==1:
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
      data.filters=new_filters
    # close dialog and replot
    filter_dialog.destroy()
    self.replot()
    
  def get_new_filter(self,table,row,data,parameters=(-1,0,0,False)):
    ''' 
      Create all widgets for the filter selection of one filter in 
      change_data_filter dialog and place them in a table.
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
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    from_data=gtk.Entry()
    from_data.set_width_chars(8)
    from_data.set_text(str(parameters[1]))
    table.attach(from_data,
                # X direction #          # Y direction
                1, 2,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    to_data=gtk.Entry()
    to_data.set_width_chars(8)
    to_data.set_text(str(parameters[2]))
    table.attach(to_data,
                # X direction #          # Y direction
                2, 3,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    include=gtk.CheckButton(label='include region', use_underline=False)
    include.set_active(parameters[3])
    table.attach(include,
                # X direction #          # Y direction
                3, 4,                      row-1, row,
                gtk.EXPAND | gtk.FILL,     gtk.EXPAND | gtk.FILL,
                0,                         0);
    return (column,from_data,to_data,include)

  def fit_dialog(self,action):
    '''
      A dialog to fit the data with a set of functions.
    '''
    dataset=self.measurement[self.index_mess]
    if dataset.fit_object==None:
      from fit_data import FitSession
      dataset.fit_object=FitSession(dataset)
    fit_session=dataset.fit_object
    fit_dialog=gtk.Dialog(title='Fit...')
    fit_dialog.set_default_size(600,400)
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(fit_session.get_dialog(self, fit_dialog)) # add fit dialog
    fit_dialog.vbox.add(sw)
    response=fit_dialog.show_all()
    self.open_windows.append(fit_dialog)

  def show_add_info(self,action):
    '''
      Show or hide advanced options widgets.
    '''
    if self.check_add.get_active():
      if action==None: # only resize picture if the length of additional settings changed
        if (self.logz.get_property('visible') & (self.measurement[self.index_mess].zdata<0))\
        |((not self.logz.get_property('visible')) & (self.measurement[self.index_mess].zdata>=0)):
          self.image.hide()
          self.image_shown=False
      else:
        self.image.hide()
        self.image_shown=False
      self.x_range_in.show()
      self.x_range_label.show()
      self.y_range_in.show()
      self.y_range_label.show()
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
    for dataset in self.measurement:
      dataset.xdata=self.measurement[self.index_mess].xdata
      dataset.ydata=self.measurement[self.index_mess].ydata
      dataset.yerror=self.measurement[self.index_mess].yerror
      dataset.logx=self.measurement[self.index_mess].logx
      dataset.logy=self.measurement[self.index_mess].logy
      dataset.logz=self.measurement[self.index_mess].logz
      dataset.plot_options=self.measurement[self.index_mess].plot_options
      self.reset_statusbar()
      self.statusbar.push(0,'Applied settings to all Plots!')

  def add_multiplot(self,action): 
    '''
      Add or remove the active dataset from multiplot list, 
      which is a list of plotnumbers of the same Type.
    '''
    if (action.get_name()=='AddAll')&(len(self.measurement)<40): # dont autoadd more than 40
      for i in range(len(self.measurement)):
        self.do_add_multiplot(i)
    else:
      self.do_add_multiplot(self.index_mess)

  def do_add_multiplot(self,index): 
    '''
      Add one item to multiplot list devided by plots of the same type.
    '''
    # FIXME: does not work with differnt files
    changed=False
    for plotlist in self.multiplot:
      if index in plotlist:
        plotlist.remove(index)
        self.reset_statusbar()
        self.statusbar.push(0,'Plot '+self.measurement[index].number+' removed.')
        changed=True
        if len(plotlist)==0:
          self.multiplot.remove(plotlist)
      else:
        if ((self.measurement[index].dimensions()==self.measurement[plotlist[0]].dimensions())&\
            (self.measurement[index].xdata==self.measurement[plotlist[0]].xdata)&\
            (self.measurement[index].ydata==self.measurement[plotlist[0]].ydata)&\
            (self.measurement[index].zdata==self.measurement[plotlist[0]].zdata)):
          plotlist.append(index)
          self.reset_statusbar()
          self.statusbar.push(0,'Plot '+self.measurement[index].number+' added.')
          changed=True
    # recreate the shown multiplot list
    if not changed:
      self.multiplot.append([index])
      self.reset_statusbar()
      self.statusbar.push(0,'Plot '+self.measurement[index].number+' added.')
    mp_list=''
    for i,plotlist in enumerate(self.multiplot):
      if i>0:
        mp_list=mp_list+'\n-------'
      plotlist.sort()
      for index2 in plotlist:
        mp_list=mp_list+'\n'+self.measurement[index2].number
    self.multi_list.set_markup(' Multiplot List: \n'+mp_list)

  def toggle_error_bars(self,action):
    '''
      Show or remove error bars in plots.
    '''
    global errorbars
    errorbars= not errorbars
    self.reset_statusbar()
    self.replot()
    self.statusbar.push(0,'Show errorbars='+str(errorbars))

  def export_plot(self,action): 
    '''
      Function for every export action. Export is made as .png or .ps depending
      on the selected file name.
    '''
    global errorbars
    if action.get_name()=='ExportAll':
      for dataset in self.measurement:
        self.last_plot_text=self.plot(self.active_session, 
                                      dataset.plot_together,
                                      self.input_file_name,
                                      dataset.short_info,
                                      [object.short_info for object in dataset.plot_together],
                                      errorbars,
                                      fit_lorentz=self.fit_lorentz,
                                      add_preferences=self.preferences_file)
        self.reset_statusbar()
        self.statusbar.push(0,'Export plot number '+dataset.number+'... Done!')
    elif action.get_name()=='MultiPlotExport':
      for plotlist in self.multiplot:
        #++++++++++++++++File selection dialog+++++++++++++++++++#
        file_dialog=gtk.FileChooserDialog(title='Export multi-plot as...', action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        file_dialog.set_default_response(gtk.RESPONSE_OK)
        file_dialog.set_current_name(self.input_file_name + '_multi_'+ \
                                     self.measurement[plotlist[0]].number + '.' + self.set_file_type)
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
        # show multiplot on screen before the file is actually selected
        self.last_plot_text=self.plot(self.active_session, 
                                      [self.measurement[index] for index in plotlist], 
                                      self.input_file_name, 
                                      self.measurement[plotlist[0]].short_info, 
                                      [self.measurement[index].short_info for index in plotlist], 
                                      errorbars,self.active_session.temp_dir+'plot_temp.png',
                                      fit_lorentz=self.fit_lorentz,
                                      add_preferences=self.preferences_file)     
        self.label.set_width_chars(len('Multiplot title')+5)
        self.label.set_text('Multiplot title')
        self.set_image()
        response = file_dialog.run()
        if response == gtk.RESPONSE_OK:
          multi_file_name=file_dialog.get_filename()
          self.last_plot_text=self.plot(self.active_session, 
                                        [self.measurement[index] for index in plotlist], 
                                        self.input_file_name, 
                                        self.measurement[plotlist[0]].short_info, 
                                        [self.measurement[index].short_info for index in plotlist], 
                                        errorbars,
                                        multi_file_name,
                                        fit_lorentz=self.fit_lorentz,
                                        add_preferences=self.preferences_file)
          # give user information in Statusbar
          self.reset_statusbar()
          self.statusbar.push(0,'Export multi-plot ' + multi_file_name + '... Done!')
        file_dialog.destroy()
        #----------------File selection dialog-------------------#
    elif action.get_name()=='MultiPlot':
      for plotlist in self.multiplot:
        if self.index_mess in plotlist:
          self.last_plot_text=self.plot(self.active_session, 
                                        [self.measurement[index] for index in plotlist], 
                                        self.input_file_name, 
                                        self.measurement[plotlist[0]].short_info, 
                                        [self.measurement[index].short_info for index in plotlist], 
                                        errorbars,
                                        self.active_session.temp_dir+'plot_temp.png',
                                        fit_lorentz=self.fit_lorentz,
                                        add_preferences=self.preferences_file)   
          self.label.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
          self.label.set_text(self.measurement[self.index_mess].short_info)
          self.set_image()
    else:
      new_name=output_file_name
      if action.get_name()=='ExportAs':
        #++++++++++++++++File selection dialog+++++++++++++++++++#
        file_dialog=gtk.FileChooserDialog(title='Export plot as...', 
                                          action=gtk.FILE_CHOOSER_ACTION_SAVE, 
                                          buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        file_dialog.set_default_response(gtk.RESPONSE_OK)
        file_dialog.set_current_name(self.input_file_name+'_'+ self.measurement[self.index_mess].number+'.'+self.set_file_type)
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
          new_name=file_dialog.get_filename()
        elif response == gtk.RESPONSE_CANCEL:
          file_dialog.destroy()
          return False
        file_dialog.destroy()
        #----------------File selection dialog-------------------#
      self.last_plot_text=self.plot(self.active_session, 
                                    self.measurement[self.index_mess].plot_together, 
                                    self.input_file_name, 
                                    self.measurement[self.index_mess].short_info,
                                    [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                    errorbars,
                                    new_name,
                                    fit_lorentz=self.fit_lorentz,
                                    add_preferences=self.preferences_file)
      self.reset_statusbar()
      self.statusbar.push(0,'Export plot number '+self.measurement[self.index_mess].number+'... Done!')

  def print_plot(self,action): 
    '''
      Send plot to printer, can also print every plot.
    '''
    global errorbars
    if action.get_name()=='Print':
      term='postscript landscape enhanced colour'
      self.last_plot_text=self.plot(self.active_session, 
                                    self.measurement[self.index_mess].plot_together,
                                    self.input_file_name, 
                                    self.measurement[self.index_mess].short_info,
                                    [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                    errorbars, 
                                    output_file=self.active_session.temp_dir+'plot_temp.ps',
                                    fit_lorentz=self.fit_lorentz,
                                    add_preferences=self.preferences_file)
      self.reset_statusbar()
      self.statusbar.push(0,'Printed with: '+print_command)
      os.popen2(print_command+self.active_session.temp_dir+'plot_temp.ps')
    elif action.get_name()=='PrintAll':
      term='postscript landscape enhanced colour'
      print_string=print_command
      for dataset in self.measurement: # combine all plot files in one print statement
        self.last_plot_text=self.plot(self.active_session, 
                                      dataset.plot_together,
                                      self.input_file_name,
                                      dataset.short_info,
                                      [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                      errorbars, 
                                      output_file=self.active_session.temp_dir+'plot_temp_'+dataset.number+'.ps',
                                      fit_lorentz=self.fit_lorentz,
                                      add_preferences=self.preferences_file)
        print_string=print_string+self.active_session.temp_dir+'plot_temp_'+dataset.number+'.ps '
      self.reset_statusbar()
      self.statusbar.push(0,'Printed with: '+print_command)
      os.popen2(print_string)
      # TODO: In the future, setting up propper printing dialog here:
      #operation=gtk.PrintOperation()
      #operation.set_job_name('Print SQUID Data Nr.'+str(self.index_mess))
      #operation.set_n_pages(1)
      #response=operation.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG)
      #if response == gtk.PRINT_OPERATION_RESULT_ERROR:
      #   error_dialog = gtk.MessageDialog(parent,
      #                                    gtk.DIALOG_DESTROY_WITH_PARENT,
      #                                    gtk.MESSAGE_ERROR,
      #                                     gtk.BUTTONS_CLOSE,
      #                                     "Error printing file:\n")
      #   error_dialog.connect("response", lambda w,id: w.destroy())
      #   error_dialog.show()
      #elif response == gtk.PRINT_OPERATION_RESULT_APPLY:
      #    settings = operation.get_print_settings()
  #--------------------------Menu/Toolbar Events---------------------------------#

  #----------------------------------Event hanling---------------------------------------#

  #+++++++++++++++++++++++++++Functions for initializing etc+++++++++++++++++++++++++++++#

  def read_config_file(self):
    '''
      Read the options that have been stored in a config file in an earlier session.
      The ConfigObj python module is used to save the settings in an .ini file
      as this is an easy way to store dictionaries.
    '''
    # create the object with association to an inifile in the user folder
    # have to test if this works under windows
    self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotting_gui/config.ini')
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
    
    # Open the other config file which uses it's own format
    # TODO: Put all configurations in one file.
    try:
      config_file=open(os.path.expanduser('~')+'/.plotting_gui/plotting_gui.config','r')
    except IOError:
      return False
    # functions for different parts of config file
    config_parts={\
      '[window]' : lambda config_file : self.read_window_config(config_file),\
      '[/plotting_gui_config]' : lambda config_file : self.config_file_end(config_file),\
    }
    if config_file.readline()=='[ploting_gui_config]\n': # is this a valid config file?
      while config_file:
        line=config_file.readline().rstrip('\n').lstrip('\t')
        if line in config_parts:
          if not config_parts[line](config_file):
            break
      return True
    else:
      print 'Configuration file corrupted.'
      return False

  def read_window_config(self,config_file):
    '''
      Read the window config parameters from the old own format.
      This will be removed, when everything is saved in the .ini file.
    '''
    line=config_file.readline().rstrip('\n').lstrip('\t')
    while not line=='[/window]':
      if line=='[height]':
        self.height=int(config_file.readline().rstrip('\n').lstrip('\t'))
        if not config_file.readline().rstrip('\n').lstrip('\t')=='[/height]':
          print 'Configuration file corrupted.'
          return False
      if line=='[width]':
        self.width=int(config_file.readline().rstrip('\n').lstrip('\t'))
        if not config_file.readline().rstrip('\n').lstrip('\t')=='[/width]':
          print 'Configuration file corrupted.'
          return False
      line=config_file.readline().rstrip('\n').lstrip('\t')
    return True

  def config_file_end(self,config_file):
    return False

  #---------------------------Functions for initializing etc-----------------------------#

  #++++++++++++++Functions for displaying graphs plotting and status infos+++++++++++++++#

  def set_image(self):
    '''
      Resize and show temporary gnuplot image.
    '''
    # TODO: errorhandling
    self.image.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file(\
                              self.active_session.temp_dir + 'plot_temp.png'\
                              ).scale_simple(self.widthf-20,
                                            self.heightf-20,
                                            gtk.gdk.INTERP_BILINEAR))

  def splot(self, session, datasets, file_name_prefix, title, names, 
            with_errorbars, output_file='', fit_lorentz=False, add_preferences=''):
    '''
      Plot via script file instead of using python gnuplot pipeing.
    '''
    return measurement_data_plotting.gnuplot_plot_script(session, 
                                                         datasets,
                                                         file_name_prefix, 
                                                         self.script_suf, 
                                                         title,
                                                         names,
                                                         with_errorbars,
                                                         output_file,
                                                         fit_lorentz=self.fit_lorentz,
                                                         add_preferences=self.preferences_file)

  def replot(self, action=None): 
    '''
      Recreate the current plot and clear statusbar.
    '''
    global errorbars
    self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
    self.label.set_text(self.measurement[self.index_mess].sample_name)
    self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
    self.label2.set_text(self.measurement[self.index_mess].short_info)
    self.last_plot_text=self.plot(self.active_session, 
                                  self.measurement[self.index_mess].plot_together,
                                  self.input_file_name, 
                                  self.measurement[self.index_mess].short_info,
                                  [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                  errorbars, 
                                  output_file=self.active_session.temp_dir+'plot_temp.png',
                                  fit_lorentz=self.fit_lorentz,
                                  add_preferences=self.preferences_file)
    if self.last_plot_text!='':
      self.statusbar.push(0, 'Gnuplot error!')
      self.show_last_plot_params(None)
    else:
      self.set_image()
      self.reset_statusbar()
      self.set_title('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
    self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)



  def reset_statusbar(self): 
    '''
      Clear statusbar.
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
      information see the pygtk documentation for the UIManager
    '''
    self.added_items=(( "xMenu", None,                             # name, stock id
        "x-axes", None,                    # label, accelerator
        "xMenu",                                   # tooltip
        None ),
    ( "yMenu", None,                             # name, stock id
        "y-axes", None,                    # label, accelerator
        "yMenu",                                   # tooltip
        None ),
    ( "dyMenu", None,                             # name, stock id
        "y-error", None,                    # label, accelerator
        "dyMenu",                                   # tooltip
        None ),
    ( "Profiles", None,                             # name, stock id
        "Profiles", None,                    # label, accelerator
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
        "Change active file", None,                    # label, accelerator
        None,                                   # tooltip
        self.change ),)
  # Menus allways present
    output='''<ui>
    <menubar name='MenuBar'>
      <menu action='FileMenu'>
        <menuitem action='OpenDatafile'/>
        <separator name='static14'/>
        <menuitem action='Export'/>
        <menuitem action='ExportAs'/>
        <menuitem action='ExportAll'/>
        <menuitem action='MultiPlotExport'/>
        <separator name='static1'/>
        <menuitem action='Print'/>
        <menuitem action='PrintAll'/>
        <separator name='static2'/>
        <menuitem action='Quit'/>
      </menu>
      <menu action='ActionMenu'>
        <menuitem action='Next'/>
        <menuitem action='Prev'/>
        <menuitem action='First'/>
        <menuitem action='Last'/>
        <separator name='static3'/>
        <menuitem action='AddMulti'/>
        <menuitem action='AddAll'/>
        <separator name='static4'/>
        <menuitem action='FitData'/>
        <separator name='static5'/>
        <menuitem action='FilterData'/>
        <separator name='static6'/>
        <menuitem action='ShowPlotparams'/>
      </menu>
      <separator name='static6'/>'''
    # Menus for column selection created depending on input measurement
    output=output+'''
      <menu action='xMenu'>
        <menuitem action='x-number'/>
      '''
    for dimension in self.measurement[self.index_mess].dimensions():
      output=output+"<menuitem action='x-"+dimension+"'/>"
      self.added_items=self.added_items+(("x-"+dimension, None,dimension,None,None,self.change),)
    output=output+'''
      </menu>
      <menu action='yMenu'>
        <menuitem action='y-number'/>
      '''
    for dimension in self.measurement[self.index_mess].dimensions():
      output=output+"<menuitem action='y-"+dimension+"'/>"
      self.added_items=self.added_items+(("y-"+dimension, None,dimension,None,None,self.change),)
    output=output+'''
      </menu>
      <menu action='dyMenu'>
      '''
    for dimension in self.measurement[self.index_mess].dimensions():
      output=output+"<menuitem action='dy-"+dimension+"'/>"
      self.added_items=self.added_items+(("dy-"+dimension, None,dimension,None,None,self.change),)
    # allways present stuff and toolbar
    output+='''     </menu>
      <separator name='static7'/>
      <menu action='Profiles'>
    '''
    for name in self.profiles.items():
      output+="<menuitem action='"+\
        name[0]+"' position='top'/>\n"
      self.added_items+=((name[0], None,name[0],None,None,self.load_profile),)
    output+=''' <separator name='static8'/>
        <menuitem action='SaveProfile' position="bottom"/>
        <menuitem action='DeleteProfile' position="bottom"/>
      </menu>
      <separator name='static9'/>
      <menu action='FilesMenu'>
      '''
    for i, name in enumerate([object[0] for object in self.active_session.file_data.items()]):
      output+="<menuitem action='File-"+ str(i) +"'/>\n"
      self.added_items+=(("File-"+ str(i), None, name, None, None, self.change_active_file),)
    output+='''
      </menu>
      <separator name='static12'/>'''
    #++++++++++++++ create session specific menu ++++++++
    specific_menu_items=self.active_session.create_menu()
    output+=specific_menu_items[0]
    self.session_added_items=specific_menu_items[1]
    #-------------- create session specific menu --------
    output+='''
      <separator name='static13'/>
      <menu action='HelpMenu'>
        <menuitem action='About'/>
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
    </toolbar>
    </ui>'''
    return output

  def __create_action_group(self):
    '''
      Create actions for menus and toolbar.
      Every entry creates a gtk.Action and the function returns a gtk.ActionGroup.
      When the action is triggered it calls to a function.
      For more information see the pygtk documentation for the UIManager and ActionGroups.
    '''
    entries = (
      ( "FileMenu", None, "_File" ),               # name, stock id, label
      ( "ActionMenu", None, "_Action" ),               # name, stock id, label
      ( "HelpMenu", None, "_Help" ),               # name, stock id, label
      ( "ToolBar", None, "_Toolbar" ),               # name, stock id, label
      ( "OpenDatafile", gtk.STOCK_SAVE,                    # name, stock id
        "_Open File","<control>O",                      # label, accelerator
        "Open a new datafile",                       # tooltip
        self.add_file ),
      ( "Export", gtk.STOCK_SAVE,                    # name, stock id
        "_Export","<control>E",                      # label, accelerator
        "Export current Plot",                       # tooltip
        self.export_plot ),
      ( "ExportAs", gtk.STOCK_SAVE,                  # name, stock id
        "Export As...", None,                       # label, accelerator
        "Export Plot under other name",                          # tooltip
        self.export_plot ),
      ( "Print", gtk.STOCK_PRINT,                  # name, stock id
        "_Print...", "<control>P",                       # label, accelerator
        None,                          # tooltip
        self.print_plot ),
      ( "PrintAll", gtk.STOCK_PRINT,                  # name, stock id
        "Print All Plots...", None,                       # label, accelerator
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
      ( "FilterData", None,                    # name, stock id
        "Filter the data points", None,                     # label, accelerator
        None,                                    # tooltip
        self.change_data_filter),
      ( "Apply", gtk.STOCK_CONVERT,                    # name, stock id
        "Apply", None,                     # label, accelerator
        "Apply current plot settings to all sequences",                                    # tooltip
        self.apply_to_all),
      ( "ExportAll", gtk.STOCK_EXECUTE,                    # name, stock id
        "Exp. All", None,                     # label, accelerator
        "Export all sequences",                                    # tooltip
        self.export_plot),
      ( "ErrorBars", gtk.STOCK_ADD,                    # name, stock id
        "E.Bars", None,                     # label, accelerator
        "Toggle errorbars",                                    # tooltip
        self.toggle_error_bars),
      ( "AddMulti", gtk.STOCK_JUMP_TO,                    # name, stock id
        "Add", None,                     # label, accelerator
        "Add/Remove plot to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "AddAll", gtk.STOCK_JUMP_TO,                    # name, stock id
        "Add all to Multiplot", None,                     # label, accelerator
        "Add/Remove all sequences to/from multi-plot list",                                    # tooltip
        self.add_multiplot),
      ( "FitData", None,                    # name, stock id
        "Fit data...", None,                     # label, accelerator
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
        print "building menus failed: %s" % ms

    
  #---------------------Functions responsible for menus and toolbar----------------------#

#------------------------- ApplicationMainWindow Class ----------------------------------#

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
  plotting_parameters=''
  plotting_parameters_errorbars=''
  plotting_parameters_3d=''
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




#------------------------------ PlotProfile Class ---------------------------------------#
