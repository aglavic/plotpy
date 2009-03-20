#!/usr/bin/env python
#################################################################################################
#                  Script for graphical user interface to plot measurement data                 #
#                                       last changes:                                           #
#                                        18.12.2008                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Additional Files: measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                                                                                               #
# Features at the moment:                                                                       #
# -show plots from any MeasurementData structure defined in measurement_data_structure.py       #
# -change x,y and yerror columns via menu selection                                             #
# -export single or multiple files and combine data in one plot                                 #
# -print one or all plots (at the moment via linux command line)                                #
# -posibility to use different gnuplot preferences as xrange and more                           #
# -fit lorentzian function                                                                      #
#                                                                                               #
# To do:                                                                                        #
# -create print dialog to select Printer and other print parameters                             #
# -more fitting options                                                                         #
# -code cleanup                                                                                 #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing. 

import os
import gobject
import gtk
# Module to save and load variables from/to config files
from configobj import ConfigObj
import measurement_data_plotting
from gnuplot_preferences import output_file_name,print_command,titles
import gnuplot_preferences
import globals

#++++++++++++++++++++++++ ApplicationMainWindow Class +++++++++++++++++++++++++++++++++#
# Everything the GUI does is in this Class
class ApplicationMainWindow(gtk.Window):
#+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
    def __init__(self, measurement, name, parent=None, script=False, script_suf='',preferences_file='',plugin_widget=None):
	if globals.debug:
	  globals.debug_file.write('construct ApplicationMainWindow (self,'+str(measurement)+','+str(name)+','+ str(parent)+ ','+ str(script)+ ','+ str(script_suf)+ ','+ str(preferences_file)+ ')')
	global errorbars
    # set class variables
	self.height=600 # window height
	self.width=700  # window width
	self.heightf=100
	self.widthf=100
	self.set_file_type=output_file_name.rsplit('.',1)[1] # export file type
	self.measurement=measurement
	self.input_file_name=name # name of source data file
	self.script_suf=script_suf # suffix for script mode gnuplot input data
	self.index_mess=0 # which data sequence is plotted at the moment
	self.multiplot=[] # list for sequences combined in multiplot
	self.x_range='set autoscale x'
	self.y_range='set autoscale y'
	self.z_range='set autoscale z\nset autoscale cb'
	self.fit_lorentz=False
	self.preferences_file=preferences_file
	self.plugin_widget=plugin_widget
	self.plot_options_window_open=False
	errorbars=False # show errorbars?
	if script: # define the plotting function depending on script mode flag
	  self.plot=self.splot
	else:
	  self.plot=measurement_data_plotting.gnuplot_plot
	# Create a text view widget. When a text view is created it will
	# create an associated textbuffer by default.
	self.plot_options_view = gtk.TextView()
	# Retrieving a reference to a textbuffer from a textview. 
	self.plot_options_buffer = self.plot_options_view.get_buffer()

    # Reading config file
	self.read_config_file()
    # Create the toplevel window
        gtk.Window.__init__(self)
        try:
            self.set_screen(parent.get_screen())
        except AttributeError:
	    self.connect('destroy', lambda *w: self.main_quit())
        self.set_title('Plotting GUI - '+measurement[0].sample_name)
        self.set_default_size(self.width, self.height)

#+++++++Build widgets in table structure++++++++#
        table = gtk.Table(3, 6, False)
        self.add(table)

    # Menu and toolbar creation
	ui_info=self.build_menu() # build structure of menu and toolbar
        self.UIManager = gtk.UIManager()
        self.set_data("ui-manager", self.UIManager)
	self.toolbar_action_group=self.__create_action_group()
        self.UIManager.insert_action_group(self.toolbar_action_group, 0) # create action groups for menu and toolbar
        self.add_accel_group(self.UIManager.get_accel_group())
        try:
            self.toolbar_ui_id = self.UIManager.add_ui_from_string(ui_info)
        except gobject.GError, msg:
            print "building menus failed: %s" % msg
        self.menu_bar = self.UIManager.get_widget("/MenuBar")
        self.menu_bar.show()

    # put menu at top position, only expand in x direction
        table.attach(self.menu_bar,
            # X direction #          # Y direction
            0, 2,                      0, 1,
            gtk.EXPAND | gtk.FILL,     0,
            0,                         0);
    # put toolbar at below menubar, only expand in x direction
        bar = self.UIManager.get_widget("/ToolBar")
        bar.set_tooltips(True)
        bar.show()
        table.attach(bar,
            # X direction #       # Y direction
            0, 2,                   1, 2,
            gtk.EXPAND | gtk.FILL,  0,
            0,                      0)



    # custom widget on the right, can be used to include specific settings
	if not self.plugin_widget==None:
	  align=gtk.Alignment(0, 0.05, 1, 0)
	  align.add(self.plugin_widget)
	  table.attach(align,
	      # X direction #       # Y direction
	      2, 3,                   3, 4,
	      gtk.FILL,  gtk.EXPAND | gtk.FILL,
	      0,                      0)

    # create image region and image for the plot
	top_table=gtk.Table(2, 1, False)
        self.label = gtk.Entry()
	self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
	self.label.set_text(self.measurement[self.index_mess].sample_name)
	self.label.connect("activate",self.change)
        self.label2 = gtk.Entry()
	self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
	self.label2.set_text(self.measurement[self.index_mess].short_info)
	self.label2.connect("activate",self.change)

	self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)
	self.plot_options_view.show()

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
        align = gtk.Alignment(0.5, 0.5, 0, 0)
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
        align = gtk.Alignment(0.5, 0.5, 1, 1)
        align.add(self.frame1)

    # image object for the plots
	self.image = gtk.Image()	
	self.image_shown=False # variable to decrease changes in picture size
	self.frame1.add(self.image)

    # put image below label on left column, expand frame in all directions
        table.attach(align,
            # X direction           Y direction
            0, 1,                   3, 4,
            gtk.EXPAND | gtk.FILL,  gtk.EXPAND | gtk.FILL,
            0,                      0)

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


    # Create additional setting input for the plot
	align = gtk.Alignment(0,0,0,0)
	align_table = gtk.Table(12, 2, False)
      # jumpt to sequence input
	page_label=gtk.Label()
	page_label.set_markup('Go to Plot:')
	align_table.attach(page_label,0,1,0,1,gtk.FILL,gtk.FILL,0,0)
	self.plot_page_entry=gtk.Entry(max=int(self.measurement[-1].number))
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
	self.logx=gtk.CheckButton(label='log x', use_underline=True)
	self.logy=gtk.CheckButton(label='log y', use_underline=True)
	self.logx.connect("toggled",self.change)
	self.logy.connect("toggled",self.change)
	align_table.attach(self.logx,9,10,0,1,gtk.FILL,gtk.FILL,0,0)
	align_table.attach(self.logy,10,11,0,1,gtk.FILL,gtk.FILL,0,0)
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
	self.logz.connect("toggled",self.change)
      # 3d Viewpoint buttons
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
	align.add(align_table)

    # put plot settings below Plot
	table.attach(align,
            # X direction           Y direction
            0, 2,                   4, 5,
            gtk.FILL,  gtk.FILL,
            0,                      0)

    # Create statusbar
        self.statusbar = gtk.Statusbar()

    # put statusbar below everything
        table.attach(self.statusbar,
            # X direction           Y direction
            0, 2,                   5, 6,
            gtk.EXPAND | gtk.FILL,  0,
            0,                      0)

#+++++++Build widgets in table structure++++++++#

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

#-------------------------------Window Constructor-------------------------------------#

#++++++++++++++++++++++++++++++++++Event hanling+++++++++++++++++++++++++++++++++++++++#

    #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
    def update_size(self, widget, event): # if resize event is triggered the window size variables are changed.
      if (not ((self.width==event.width)&(self.height==event.height))):
	self.image.hide()
	self.image_shown=False
	self.width=event.width
	self.height=event.height

    def update_frame_size(self, widget, event): # if resize event is triggered the window size variables are changed.
      self.heightf=event.height
      self.widthf=event.width

    def update_picture(self, widget, event): # the first event after starting to resize triggers rescaling the picture and showing it. Is only executed, if this event is not a resize event. So the picture is hidden while reesizing and reshown after.
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
      self.config_object['profiles']={}
      for name, profile in self.profiles.items():
	profile.write(self.config_object['profiles'])
      del self.config_object['profiles']['default']
      self.config_object.write()
      gtk.main_quit()

    def activate_about(self, action): # about dialog to show
        dialog = gtk.AboutDialog()
        dialog.set_name("Plotting GUI")
        dialog.set_copyright("\302\251 Copyright Artur Glavic")
        dialog.set_website("http://www.fz-juelich.de/iff")
        ## Close dialog on user response
        dialog.connect ("response", lambda d, r: d.destroy())
        dialog.show()
	
    def iterate_through_measurements(self, action): # change the plot with arrows in toolbar
	global errorbars
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
	if self.index_mess>=len(self.measurement):
	  self.index_mess=len(self.measurement)-1
	if self.index_mess<0:
	  self.index_mess=0
      # change label and plot other picture
	self.show_add_info(None)
	self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
	self.label.set_text(self.measurement[self.index_mess].sample_name)
	self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
	self.label2.set_text(self.measurement[self.index_mess].short_info)
	self.last_plot_text= self.plot([self.measurement[self.index_mess]],self.input_file_name, self.measurement[self.index_mess].short_info,[''],errorbars, output_file=globals.temp_dir+'plot_temp.png',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	self.set_image()
	self.reset_statusbar()
	self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)
	self.logx.set_active(self.measurement[self.index_mess].logx)
	self.logy.set_active(self.measurement[self.index_mess].logy)
	self.logz.set_active(self.measurement[self.index_mess].logz)
	self.rebuild_menus()

    def change(self,action): # change different plot settings triggered by different events
      if globals.debug:
	globals.debug_file.write('call ApplicationMainWindow.change(self,'+ str(action)+')')
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
      elif action.get_name()=='y-number':
	self.measurement[self.index_mess].ydata=-1
      elif action.get_name()=='FitLorentz':
	self.fit_lorentz = not self.fit_lorentz
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
      elif action==self.label:
	self.measurement[self.index_mess].sample_name=self.label.get_text()
      elif action==self.label2:
	self.measurement[self.index_mess].short_info=self.label2.get_text()
      else:
	self.measurement[self.index_mess].logx=self.logx.get_active()
	self.measurement[self.index_mess].logy=self.logy.get_active()
	self.measurement[self.index_mess].logz=self.logz.get_active()
      self.replot() # plot with new Settings

    def change_range(self,action): # change plotting range according to textinput
      xin=self.x_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
      yin=self.y_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
      zin=self.z_range_in.get_text().lstrip('[').rstrip(']').split(':',1)
      # erase old settings
      lines_old=self.measurement[self.index_mess].plot_options.split('\n')
      lines_new=[]
      for line in lines_old:
	if not ((' autoscale ' in line)|\
	  (' xrange ' in line)|\
	  (' yrange ' in line)|\
	  (' zrange ' in line)|\
	  (' cbrange ' in line)):
	  lines_new.append(line)
      self.measurement[self.index_mess].plot_options="\n".join(lines_new)

      if len(xin)==2:
	if xin[0].replace('-','').replace('e','').replace('.','',1).isdigit()&\
	  xin[1].replace('-','').replace('e','').replace('.','',1).isdigit():
	  self.x_range='set xrange ['+str(xin[0])+':'+str(xin[1])+']'
	else:
	  self.x_range='set autoscale x'
	  self.x_range_in.set_text('')
      else:
	self.x_range='set autoscale x'
	self.x_range_in.set_text('')
      if len(yin)==2:
	if yin[0].replace('-','').replace('e','').replace('.','',1).isdigit()&\
	  yin[1].replace('-','').replace('e','').replace('.','',1).isdigit():
	  self.y_range='set yrange ['+str(yin[0])+':'+str(yin[1])+']'
	else:
	  self.y_range='set autoscale y'
	  self.y_range_in.set_text('')
      else:
	self.y_range='set autoscale y'
	self.y_range_in.set_text('')
      if len(zin)==2:
	if zin[0].replace('-','').replace('e','').replace('.','',1).isdigit()&\
	  zin[1].replace('-','').replace('e','').replace('.','',1).isdigit():
	  self.z_range='set zrange ['+str(zin[0])+':'+str(zin[1])+']\nset cbrange ['+str(zin[0])+':'+str(zin[1])+']'
	else:
	  self.z_range='set autoscale z\nset autoscale cb'
	  self.z_range_in.set_text('')
      else:
	self.z_range='set autoscale z\nset autoscale cb'
	self.z_range_in.set_text('')
      self.measurement[self.index_mess].plot_options=self.measurement[self.index_mess].plot_options+\
      self.x_range+\
      '\n'+self.y_range+\
      '\n'+self.z_range+'\n'
      self.replot() # plot with new settings

    # open a dialog window to inser additional gnuplot commands
    # after opening the button is rerouted
    def open_plot_options_window(self,action):
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
      dialog.connect("response",self.change_plot_options,\
	terminal_png,terminal_ps,x_label,y_label,z_label,\
	plotting_parameters,plotting_parameters_errorbars,plotting_parameters_3d)
      # befor the widget gets destroyed the textbuffer view widget is removed
      dialog.connect("destroy",self.close_plot_options_window,sw) 
      dialog.show()
      # reroute the button to hide the windoe
      self.plot_options_button.disconnect(self.plot_options_handler_id)
      self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.button_close_plot_options_window,dialog)
      self.plot_options_window_open=True

    # remove the textbox when dialog is closed
    def close_plot_options_window(self,dialog,sw):
      dialog.hide()
      sw.remove(self.plot_options_view)
      # reroute the button to open a new window
      self.plot_options_button.disconnect(self.plot_options_handler_id)
      self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)
      self.plot_options_window_open=False

    # hide dialog window and reroute button
    def button_close_plot_options_window(self,button,dialog):
      dialog.destroy()

    # plot with new commands from dialog window
    def change_plot_options(self,widget,action,\
      terminal_png,terminal_ps,x_label,y_label,z_label,\
	plotting_parameters,plotting_parameters_errorbars,plotting_parameters_3d):
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

    # load a plot profile
    def load_profile(self,action):
      self.profiles[action.get_name()].load(self)
      if self.plot_options_window_open:
	self.plot_options_button.emit("clicked")
	self.plot_options_button.emit("clicked")


    # save a plot profile
    def save_profile(self,action):
      name_dialog=gtk.Dialog(title='Enter profile name:')
      name_entry=gtk.Entry()
      name_entry.show()
      name_entry.set_text('Enter Name')
      name_entry.set_width_chars(20)
      name_dialog.add_action_widget(name_entry,1)
      response = name_dialog.run()
      name=name_entry.get_text()
      name_dialog.destroy()
      self.profiles[name]= PlotProfile(name)
      self.profiles[name].save(self)
      self.rebuild_menus()

    # delete a plot profile
    def delete_profile(self,action):
      delete_dialog=gtk.Dialog(title='Delete profile')
      self.delete_name=''
      radio_group=None
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
      if (response == 1) & ( not self.delete_name == '' ):
	del self.profiles[self.delete_name]
      del self.delete_name
      delete_dialog.destroy()
      self.rebuild_menus()

    def set_delete_name(self,action):
      self.delete_name=action.get_label()

    def show_last_plot_params(self,action):
        global errorbars
        plot_text=measurement_data_plotting.create_plot_script([self.measurement[self.index_mess]],self.input_file_name, self.script_suf, self.measurement[self.index_mess].short_info,[''],errorbars, output_file=globals.temp_dir+'plot_temp.png',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
        param_dialog=gtk.Dialog(title='Last plot parameters:')
        param_dialog.set_default_size(600,400)
        sw = gtk.ScrolledWindow()
        # Set the adjustments for horizontal and vertical scroll bars.
        # POLICY_AUTOMATIC will automatically decide whether you need
        # scrollbars.
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        text_filed=gtk.Label()
        text_filed.set_markup(plot_text)
        sw.add_with_viewport(text_filed) # add textbuffer view widget
        param_dialog.vbox.add(sw)
        param_dialog.show_all()

    def change_data_filter(self,action):
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
      for data_filter in data.filters:
	filters.append(self.get_new_filter(table,table_rows,data,data_filter))
	table_rows+=1
	table.resize(table_rows,5)
      filters.append(self.get_new_filter(table,table_rows,data))
      table_rows+=1
      table.resize(table_rows,5)
      filter_dialog.add_button('New Filter',2)
      filter_dialog.add_button('Apply changes',1)
      filter_dialog.add_button('Cancel',0)
      filter_dialog.show_all()
      response=filter_dialog.run()
      while(response==2):
	filters.append(self.get_new_filter(table,table_rows,data))
	table_rows+=1
	table.resize(table_rows,5)
	filter_dialog.show_all()
	response=filter_dialog.run()
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
      filter_dialog.destroy()
      self.replot()
      

    # create all widgets for the filter selection and place them in a table
    def get_new_filter(self,table,row,data,parameters=(-1,0,0,False)):
      column=gtk.combo_box_new_text()
      column.append_text('None')
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

    def show_add_info(self,action): # show or hide advanced options
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

	

    def apply_to_all(self,action): # apply changed plotsettings to all plots
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

    def add_multiplot(self,action): # add or remove this item from multiplot list, which is a linst of plotnumbers of the same Type
      if (action.get_name()=='AddAll')&(len(self.measurement)<40): # dont autoadd more than 40
	for i in range(len(self.measurement)):
	  self.do_add_multiplot(i)
      else:
	self.do_add_multiplot(self.index_mess)

    def do_add_multiplot(self,index): # add one item to multiplot devided by plots of same type
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

    def toggle_error_bars(self,action): # show or remove error bars from plots
      global errorbars
      errorbars= not errorbars
      self.reset_statusbar()
      self.replot()
      self.statusbar.push(0,'Show errorbars='+str(errorbars))

    def export_plot(self,action): # function for every export action
      global errorbars
      if action.get_name()=='ExportAll':
	for dataset in self.measurement:
	  self.last_plot_text=self.plot([dataset],self.input_file_name,dataset.short_info,[''],errorbars,fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	  self.reset_statusbar()
	  self.statusbar.push(0,'Export plot number '+dataset.number+'... Done!')
      elif action.get_name()=='MultiPlotExport':
	for plotlist in self.multiplot:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
	  file_dialog=gtk.FileChooserDialog(title='Export multi-plot as...', action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
	  file_dialog.set_default_response(gtk.RESPONSE_OK)
	  file_dialog.set_current_name(self.input_file_name+'_multi_'+ self.measurement[plotlist[0]].number+'.'+self.set_file_type)
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
	  self.last_plot_text=self.plot([self.measurement[index] for index in plotlist], self.input_file_name, self.measurement[plotlist[0]].short_info, [self.measurement[index].short_info for index in plotlist], errorbars,globals.temp_dir+'plot_temp.png',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)	  
	  self.label.set_width_chars(len('Multiplot title')+5)
	  self.label.set_text('Multiplot title')
	  self.set_image()
	  response = file_dialog.run()
	  if response == gtk.RESPONSE_OK:
	    multi_file_name=file_dialog.get_filename()
	    self.last_plot_text=self.plot([self.measurement[index] for index in plotlist], self.input_file_name, self.measurement[plotlist[0]].short_info, [self.measurement[index].short_info for index in plotlist], errorbars,multi_file_name,fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	  # give user information in Statusbar
	    self.reset_statusbar()
	    self.statusbar.push(0,'Export multi-plot '+multi_file_name+'... Done!')
	  file_dialog.destroy()
      #----------------File selection dialog-------------------#
      elif action.get_name()=='MultiPlot':
	for plotlist in self.multiplot:
	  if self.index_mess in plotlist:
	    self.last_plot_text=self.plot([self.measurement[index] for index in plotlist], self.input_file_name, self.measurement[plotlist[0]].short_info, [self.measurement[index].short_info for index in plotlist], errorbars,globals.temp_dir+'plot_temp.png',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)	  
	    self.label.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
	    self.label.set_text(self.measurement[self.index_mess].short_info)
	    self.set_image()
      else:
	new_name=output_file_name
	if action.get_name()=='ExportAs':
      #++++++++++++++++File selection dialog+++++++++++++++++++#
	  file_dialog=gtk.FileChooserDialog(title='Export plot as...', action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
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
	self.last_plot_text=self.plot([self.measurement[self.index_mess]], self.input_file_name, self.measurement[self.index_mess].short_info,[''],errorbars,new_name,fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	self.reset_statusbar()
	self.statusbar.push(0,'Export plot number '+self.measurement[self.index_mess].number+'... Done!')

    def print_plot(self,action): # send plot to printer, can also print every Plot
      global errorbars
      if action.get_name()=='Print':
	term='postscript landscape enhanced colour'
	self.last_plot_text=self.plot([self.measurement[self.index_mess]],self.input_file_name, self.measurement[self.index_mess].short_info,[''],errorbars, output_file=globals.temp_dir+'plot_temp.ps',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	self.reset_statusbar()
	self.statusbar.push(0,'Printed with: '+print_command)
	os.popen2(print_command+globals.temp_dir+'plot_temp.ps')
      elif action.get_name()=='PrintAll':
	term='postscript landscape enhanced colour'
	print_string=print_command
	for dataset in self.measurement: # combine all plot files in one print statement
	  self.last_plot_text=self.plot([dataset],self.input_file_name,dataset.short_info,[''],errorbars, output_file=globals.temp_dir+'plot_temp_'+dataset.number+'.ps',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	  print_string=print_string+globals.temp_dir+'plot_temp_'+dataset.number+'.ps '
	self.reset_statusbar()
	self.statusbar.push(0,'Printed with: '+print_command)
	os.popen2(print_string)
      # In the future, setting up propper printing dialog here:
      #operation=gtk.PrintOperation()
      #operation.set_job_name('Print SQUID Data Nr.'+str(self.index_mess))
      #operation.set_n_pages(1)
      #response=operation.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG)
      #if response == gtk.PRINT_OPERATION_RESULT_ERROR:
      #   error_dialog = gtk.MessageDialog(parent,
      #                                    gtk.DIALOG_DESTROY_WITH_PARENT,
      #                                    gtk.MESSAGE_ERROR,
      #					  gtk.BUTTONS_CLOSE,
      #					  "Error printing file:\n")
      #   error_dialog.connect("response", lambda w,id: w.destroy())
      #   error_dialog.show()
      #elif response == gtk.PRINT_OPERATION_RESULT_APPLY:
      #	 settings = operation.get_print_settings()
    #--------------------------Menu/Toolbar Events---------------------------------#

#----------------------------------Event hanling---------------------------------------#

#+++++++++++++++++++++++++++Functions for initializing etc+++++++++++++++++++++++++++++#

    def read_config_file(self):
      self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotting_gui/config.ini')
      self.config_object.indent_type='\t'
      try:
	self.profiles={'default': PlotProfile('default')}
	self.profiles['default'].save(self)
	for name in self.config_object['profiles'].items():
	  self.profiles[name[0]]=PlotProfile(name[0])
	  self.profiles[name[0]].read(self.config_object['profiles'])
      except KeyError:
	self.config_object['profiles']={}
	self.profiles={'default': PlotProfile('default')}
	self.profiles['default'].save(self)
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

    def set_image(self): # resize and show temporary gnuplot image
      self.image.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file(globals.temp_dir+'plot_temp.png').scale_simple( self.widthf-20,self.heightf-20,gtk.gdk.INTERP_BILINEAR))

    def splot(self,datasets,file_name_prefix, title,names, with_errorbars,output_file='',fit_lorentz=False,add_preferences=''): # plot via script file instead of using python gnuplot pipeing
      return measurement_data_plotting.gnuplot_plot_script(datasets,file_name_prefix, self.script_suf, title,names,with_errorbars,output_file,fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)

    def replot(self,action=None): # recreate the current plot and clear Statusbar
	global errorbars
	self.label.set_width_chars(len(self.measurement[self.index_mess].sample_name)+5)
	self.label.set_text(self.measurement[self.index_mess].sample_name)
	self.label2.set_width_chars(len(self.measurement[self.index_mess].short_info)+5)
	self.label2.set_text(self.measurement[self.index_mess].short_info)
	self.last_plot_text=self.plot([self.measurement[self.index_mess]],self.input_file_name, self.measurement[self.index_mess].short_info,[''],errorbars, output_file=globals.temp_dir+'plot_temp.png',fit_lorentz=self.fit_lorentz,add_preferences=self.preferences_file)
	self.set_image()
	self.reset_statusbar()
	self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)


    def reset_statusbar(self): # clear statusbar
      self.statusbar.pop(0)
      self.statusbar.push(0,'')

#--------------Functions for displaying graphs plotting and status infos---------------#

#+++++++++++++++++++++Functions responsible for menus and toolbar++++++++++++++++++++++#

    def build_menu(self): # build the menu-/toolbar, especially for the x and y menus
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
)
    # Menus allways present
      output='''<ui>
      <menubar name='MenuBar'>
	<menu action='FileMenu'>
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
	  <menuitem action='FitLorentz'/>
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
      output+='''	<separator name='static8'/>
	  <menuitem action='SaveProfile' position="bottom"/>
	  <menuitem action='DeleteProfile' position="bottom"/>
	</menu>
	<separator name='static9'/>
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

    def __create_action_group(self): # define the actions for every menu-/toolbar entry
        entries = (
          ( "FileMenu", None, "_File" ),               # name, stock id, label
          ( "ActionMenu", None, "_Action" ),               # name, stock id, label
          ( "HelpMenu", None, "_Help" ),               # name, stock id, label
          ( "ToolBar", None, "_Toolbar" ),               # name, stock id, label
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
          ( "FitLorentz", None,                    # name, stock id
            "Fit with pseudo Voigt", None,                     # label, accelerator
            "Try to fit one peak with pseudo Voigt function",                                    # tooltip
            self.change),
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
        return action_group

  # Build new menu and toolbar structure
    def rebuild_menus(self):
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

#------------------------ ApplicationMainWindow Class ---------------------------------#

#+++++++++++++++++++++++++++++ PlotProfile Class ++++++++++++++++++++++++++++++++++++++#
# class for storing a profile of plot options for later use
class PlotProfile:
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
    self.name=name

  def save(self, active_class):
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
    print self.name,self.set_output_terminal_png,self.set_output_terminal_ps,\
      self.x_label,self.y_label,self.z_label,self.plotting_parameters, \
      self.plotting_parameters_errorbars,self.plotting_parameters_3d,self.additional_commands

  def write(self,config_object):
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




#----------------------------- PlotProfile Class --------------------------------------#
