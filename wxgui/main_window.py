# -*- encoding: utf-8 -*-
'''
  Main module of the GTK2 toolkit providing the main window class "ApplicationMainWindow".
'''
#  
#  For creating another toolkit ApplicationMainWindow must provide the methods:
#  replot - Create a new plot and show the result in the main window
#  rebuild_menus - Recreate the menus of the main window 
#                  (some parts can chnge when the dataset changes)

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++
# python modules
import os
import sys
try:
  import IPython.gui.wx.ipython_view
except ImportError:
  pass
from time import sleep, time
import wx
import wx.grid 

# own modules
# Module to save and load variables from/to config files
from sessions.squid import SquidSession 
from configobj import ConfigObj
from measurement_data_structure import MeasurementData
import measurement_data_plotting
from config.gnuplot_preferences import output_file_name,PRINT_COMMAND,titles
from config import gnuplot_preferences
from diverse_classes import PlotProfile, RedirectOutput, RedirectError
import file_actions
from config.gui import DOWNLOAD_PAGE_URL
from dialogs import SimpleEntryDialog, PreviewDialog, StatusDialog, ExportFileChooserDialog
from PrintDatasetDialog import PrintDatasetDialog


from MyClasses import MyMessageDialog

#----------------------- importing modules --------------------------

__author__     = "Artur Glavic"
__copyright__  = "Copyright 2008-2010"
__credits__    = []
__license__    = "None"
__version__    = "0.7beta1"
__maintainer__ = "Artur Glavic"
__email__      = "a.glavic@fz-juelich.de"
__status__     = "Development"

WXAPPLICATION=wx.App(0)

def main_loop(session):
  WXAPPLICATION.MainLoop()

# window IDs ( wichtig fuer event handling)
idShowConfigPath    = wx.ID_HIGHEST + 1
idOpenConsole       = wx.ID_HIGHEST + 2
idShowPlotParameter = wx.ID_HIGHEST + 3
idShowImportInfo    = wx.ID_HIGHEST + 4

idLabel             = wx.ID_HIGHEST + 10
idLabel2            = wx.ID_HIGHEST + 11
idViewLeft          = wx.ID_HIGHEST + 20
idViewUp            = wx.ID_HIGHEST + 21
idViewDown          = wx.ID_HIGHEST + 22
idViewRight         = wx.ID_HIGHEST + 23

class GenericGUI:
  def create_menu(self):
    '''
      Create a specifig menu for the session. Only child classes
      will add anything here.
    '''
    print 'generic.py: Entry GenericGUI create_menu'
    return '',  ()  

#+++++++++++++++++++++++++ ApplicationMainWindow Class ++++++++++++++++++++++++++++++++++#
class ApplicationMainWindow( wx.Frame ):
  '''
    Main window of the GUI.
    Everything the GUI does is in this Class.
  '''
  
  status_dialog = None
  garbage       = []

  def get_active_dataset(self):
    return self.measurement[self.index_mess]

  active_dataset       = property(get_active_dataset)
  geometry             = ((0,0), (800,600))
  active_plot_geometry = (780, 550)
  
  #+++++++++++++++++++++++++++++++Window Constructor+++++++++++++++++++++++++++++++++++++#
  def __init__(self, active_session, parent=None, script_suf='', status_dialog=None):
    '''
      Class constructor which builds the main window with its menus, buttons and the plot area.
      
      @param active_session A session object derived from GenericSession.
      @param parant Parent window.
      @param script_suf Suffix for script file name.
    '''
    global errorbars

    print 'generic.py: Entry class ApplicationMainWindow __init__'

    # Create the toplevel window
    print 'generic.py: class ApplicationMainWindow create top level window'
    wx.Frame.__init__(self, parent, size=(850,700) )


    # TODO: remove global errorbars variable and put in session or m_d_structure
    #+++++++++++++++++ set class variables ++++++++++++++++++

    self.last_makro      = None
    self.heightf         = 100                                # picture frame height
    self.widthf          = 100                                # pricture frame width
    self.set_file_type   = output_file_name.rsplit('.',1)[1]  # export file type
    self.measurement     = active_session.active_file_data    # active data file measurements
    self.input_file_name = active_session.active_file_name    # name of source data file
    self.active_session  = active_session                     # session object passed by plot.py
    self.script_suf      = script_suf                         # suffix for script mode gnuplot input data
    self.index_mess      = 0                                  # which data sequence is plotted at the moment
    self.multiplot       = []                                 # list for sequences combined in multiplot
    self.x_range         = 'set autoscale x'
    self.y_range         = 'set autoscale y'
    self.z_range         = 'set autoscale z\nset autoscale cb'
    self.active_multiplot         = False
    self.plot_options_window_open = False                     # is the dialog window for the plot options active?
    self.bmp             = wx.EmptyBitmap(100,100)
    errorbars            = False                              # show errorbars?
    self.active_folder   = os.path.realpath('.')              # For file dialogs to stay in the active directory
    self.file_actions    = file_actions.FileActions(self)
    if active_session.gnuplot_script:                         # define the plotting function depending on script mode flag
      self.plot = self.splot
    else:
      self.plot=measurement_data_plotting.gnuplot_plot
    # list of active winows, that will be closed with this main window
    self.open_windows = []
    self.action_dict  = {}                                    # dictionary for Menu-Items Ids
    # Create a text view widget. When a text view is created it will
    # create an associated textbuffer by default.
#####    self.plot_options_view = wx.TextCtrl(self, style=wx.TE_MULTILINE)
    # Retrieving a reference to a textbuffer from a textview.
    # TODO: call buffer directly from textview widget
    self.plot_options_buffer =  '' #self.plot_options_view.GetValue() # list den gesamten Text aus wx.TextCtrl
######
#Zeilen von TextCtrl lesen: 
#    for line in range(from, to+1)
#        str += GetLineText(line -1)  
######
    print 'Ende set class variables'
    #----------------- Ende set class variables ------------------


    # Reading config file
    self.read_config_file()
    # Set the title of the window, will be changed when the active plot changes
    self.SetLabel('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))

# Create statusBar
    self.create_statusBar()

# Create toolBar
    self.create_toolBar()


    table = wx.BoxSizer( wx.VERTICAL ) 
    self.SetSizer(table)
    
    #++++++++++ create image region and image for the plot ++++++++++
    top_table = wx.BoxSizer( wx.HORIZONTAL ) 
    # first entry for sample name part of title
    # plot title label entries
    # TODO: don't lose entry when not pressing enter

    self.label = wx.TextCtrl(self, id=idLabel, style=wx.TE_PROCESS_ENTER)                  # style=wx.TE_PROCESS_ENTER  

    # second entry for additional information part of title
    self.label2 = wx.TextCtrl(self, id=idLabel2, style=wx.TE_PROCESS_ENTER)

    # TODO: put this to a different location
##    self.plot_options_buffer.set_text(self.measurement[self.index_mess].plot_options)

##     self.plot_options_view.show()
    # attach entrys to sub table
    top_table.Add( self.label )
    top_table.Add( self.label2)
    table.Add( top_table,0, wx.ALL|wx.CENTER|wx.EXPAND, 5 )

    self.frame1 = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP )

    # frame region for the image
    self.image = wx.Panel(self.frame1, wx.ID_ANY)
    self.image.SetBackgroundColour(wx.WHITE)
    self.frame1.AddPage(self.image, 'Plot', True) 
    wx.InitAllImageHandlers()
    self.image.Bind( event=wx.EVT_PAINT, handler=self.onPaint ) 
 
    #frame for multiplot list
    self.multi_list = wx.TextCtrl(self.frame1, wx.ID_ANY, style=wx.TE_MULTILINE|wx.TE_CENTRE)
    self.frame1.AddPage( self.multi_list, 'Multiplot List', False)

    table.Add( self.frame1, 1, wx.ALL|wx.CENTER|wx.EXPAND, 5)

    self.image_shown = False                                                         # variable to decrease changes in picture size

    #++++++++++ Create additional settings input for the plot ++++++++++
    bottom_table    = wx.BoxSizer( wx.HORIZONTAL ) 
    self.page_label = wx.StaticText(self, wx.ID_ANY, 'Go to Plot:' )
    bottom_table.Add(self.page_label, 0, wx.ALL|wx.CENTER, 3)
    self.plot_page_entry = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
    id = self.plot_page_entry.GetId()
    self.plot_page_entry.ChangeValue( '0' )
    self.plot_page_entry.Bind(event=wx.EVT_TEXT_ENTER, handler=self.iterate_through_measurements, id=id )
    self.action_dict[id] = 'activate'
    bottom_table.Add(self.plot_page_entry, 0, wx.ALL|wx.CENTER, 3)


    # x,y ranges
    self.x_range_label = wx.StaticText(self, wx.ID_ANY, 'x-range:')
    self.x_range_in    = wx.TextCtrl(self,   wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
    self.y_range_label = wx.StaticText(self, wx.ID_ANY, 'y-range:')
    self.y_range_in    = wx.TextCtrl(self,   wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
    self.x_range_in.Bind( event=wx.EVT_TEXT_ENTER, handler=self.change_range )
    self.y_range_in.Bind( event=wx.EVT_TEXT_ENTER, handler=self.change_range )


    bottom_table.Add(self.x_range_label, 0, wx.ALL|wx.CENTER, 3)
    bottom_table.Add(self.x_range_in,    0, wx.ALL|wx.CENTER, 3)
    bottom_table.Add(self.y_range_label, 0, wx.ALL|wx.CENTER, 3)
    bottom_table.Add(self.y_range_in,    0, wx.ALL|wx.CENTER, 3)


    # checkboxes for log x, log y 
    self.logx = wx.CheckBox(self, wx.ID_ANY, 'log x')
    self.logy = wx.CheckBox(self, wx.ID_ANY, 'log y')
    self.logx.Bind(wx.EVT_CHECKBOX, handler=self.change )
    self.logy.Bind(wx.EVT_CHECKBOX, handler=self.change )


    bottom_table.Add(self.logx, 0, wx.ALL|wx.CENTER, 3)
    bottom_table.Add(self.logy, 0, wx.ALL|wx.CENTER, 3)
#
    # font size entry
    self.font_size_label = wx.StaticText(self, wx.ID_ANY, 'font-size:' )
    self.font_size       = wx.TextCtrl(self,   wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    self.font_size.ChangeValue( str(self.active_session.font_size) )
    self.font_size.Bind( event=wx.EVT_TEXT_ENTER, handler=self.change_range)
    bottom_table.Add(self.font_size_label, 0, wx.ALL|wx.CENTER, 3)
    bottom_table.Add(self.font_size,       0, wx.ALL|wx.CENTER, 3)

    table.Add( bottom_table, 0, wx.ALL|wx.EXPAND )


    bottom_z_table    = wx.BoxSizer( wx.HORIZONTAL )

    self.z_range_label = wx.StaticText(self, wx.ID_ANY, 'z-range:')
    self.z_range_in    = wx.TextCtrl(self,   wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
    self.logz          = wx.CheckBox(self, wx.ID_ANY, 'log z')

    # 3d Viewpoint buttons to rotate the view
#   buttons spaeter ersetzen durch bitmapButtons
    self.view_left  = wx.Button(self, id=idViewLeft,  label='Left')
    self.view_up    = wx.Button(self, id=idViewUp,    label='Up')
    self.view_down  = wx.Button(self, id=idViewDown,  label='Down')
    self.view_right = wx.Button(self, id=idViewRight, label='Right')
  
    bottom_z_table.Add(self.z_range_label, 0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.z_range_in,    0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.view_left,     0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.view_up,       0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.view_down,     0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.view_right,    0, wx.ALL|wx.CENTER, 3)
    bottom_z_table.Add(self.logz, 0, wx.ALL|wx.CENTER, 3)

    self.z_range_in.Bind( event=wx.EVT_TEXT_ENTER, handler=self.change_range )
    self.logz.Bind(       event=wx.EVT_CHECKBOX,   handler=self.change )
    self.view_left.Bind(  event=wx.EVT_BUTTON,     handler=self.change)
    self.view_up.Bind(    event=wx.EVT_BUTTON,     handler=self.change)
    self.view_down.Bind(  event=wx.EVT_BUTTON,     handler=self.change)
    self.view_right.Bind( event=wx.EVT_BUTTON,     handler=self.change)



    table.Add ( bottom_z_table, 0, wx.ALL|wx.EXPAND, 3)

    bottom_table_2    = wx.BoxSizer( wx.HORIZONTAL ) 

    # checkbox for more Settings
    self.check_add = wx.CheckBox(self, wx.ID_ANY, 'Show more options')
    self.check_add.Bind(wx.EVT_CHECKBOX, handler=self.show_add_info)
    bottom_table_2.Add(self.check_add, 0, wx.ALL|wx.CENTER, 3)

    #   button to open additional plot options dialog
    #   evt. ersetzen durch wx.BitmapButton, wennn bitmap vorhanden
    self.plot_options_button = wx.Button(self, label='Add custom Gnuplot commands')
    self.plot_options_button.SetToolTip(wx.ToolTip('Add custom Gnuplot commands') )
    self.plot_options_button.Bind( event=wx.EVT_BUTTON ,handler=self.open_plot_options_window )
    bottom_table_2.Add(self.plot_options_button, 0, wx.ALL|wx.CENTER, 3 )

    table.Add( bottom_table_2, 0, wx.ALL|wx.EXPAND, 3 )

    # no input file selected
    while len(self.measurement)==0:
      result=self.add_file(None)
      WXAPPLICATION.ProcessPendingEvents()
      if not result:
        self.main_quit()
        return
      self.measurement=self.active_session.active_file_data


    # Create menuBar
    self.create_menuBar()

    # entry settings
    # SetValue generates a wx.wxEVT_COMMAND_TEXT_UPDATED event
    self.label.ChangeValue(self.measurement[self.index_mess].sample_name)
    self.label.Bind(event=wx.EVT_TEXT_ENTER, handler=self.change )                         # Enter entry triggers change() function
    self.label2.ChangeValue( self.measurement[self.index_mess].short_info )
    self.label2.Bind(event=wx.EVT_TEXT_ENTER, handler=self.change)                         # Enter entry triggers change() function 
    self.plot_options_buffer = self.measurement[self.index_mess].plot_options
    self.logx.SetValue(self.measurement[self.index_mess].logx)
    self.logy.SetValue(self.measurement[self.index_mess].logy)
    self.logz.SetValue(self.measurement[self.index_mess].logz)

    self.x_range_in.Disable()
    self.y_range_in.Disable()
    self.z_range_in.Disable()
    self.x_range_label.Disable()
    self.y_range_label.Disable()
    self.z_range_label.Disable()
    self.z_range_in.Disable(  )
    self.logx.Disable()
    self.logy.Disable()
    self.logz.Disable()
    self.plot_options_button.Disable()
    self.view_left.Disable()
    self.view_up.Disable()
    self.view_down.Disable()
    self.view_right.Disable()

    self.Show(True)


#    self.Bind(event=wx.EVT_MOUSE_EVENTS, handler=self.update_picture) # process all mouse events
    self.Bind(event=wx.EVT_ENTER_WINDOW, handler=self.update_picture)
    self.Bind(event=wx.EVT_SIZE,         handler=self.update_size)
    self.replot()

    self.check_add.SetValue(False)
##     self.check_add.toggled()
    self.geometry = (self.GetPosition(), self.GetSize() )
   
    self.check_for_updates()

  #-------------------------------Window Constructor-------------------------------------#

  #++++++++++++++++++++++++++++++++++Event hanling+++++++++++++++++++++++++++++++++++++++#

  #++++++++++++++++++++++++++++Interrupt Events++++++++++++++++++++++++++++++++++#
  def update_size(self, event):
     '''
       If resize event is triggered the window size variables are changed.
     '''
     geometry = (self.GetPosition(), self.GetSize() )
     if geometry != self.geometry:
        self.geometry = geometry
        size          = self.frame1.GetSize()
        self.widthf   = size.GetWidth()
        self.heightf  = size.GetHeight()


  def update_picture(self, event):
     '''
       After releasing the mouse the picture gets replot.
     '''
     if self.active_plot_geometry != (self.widthf, self.heightf):
        self.replot()

##   #----------------------------Interrupt Events----------------------------------#

##   #++++++++++++++++++++++++++Menu/Toolbar Events+++++++++++++++++++++++++++++++++#
  def main_quit(self, action=None):
    '''
      When window is closed save the settings in home folder.
      All open dialogs are closed before exit.
    '''
    print 'generic.py: Entry main_quit'
    try:
      os.mkdir(os.path.expanduser('~')+'/.plotting_gui')
    except OSError:
      pass
    try:
      # ConfigObj config structure for profiles
      self.config_object['profiles']={}
      for name, profile in self.profiles.items():
        profile.write(self.config_object['profiles'])
      del self.config_object['profiles']['default']
      # ConfigObj Window parameters
      self.config_object['Window']={ 
                                  'size':     ( self.geometry[1][0], self.geometry[1][1] ),
                                  'position': ( self.geometry[0][0], self.geometry[0][1] )
                                 }
      self.config_object.write()
    except AttributeError:
      pass
    for window in self.open_windows:
      window.Destroy()

    print 'return from main quit'


  def activate_about(self, action):
     '''
       Show the about dialog.
     '''
     about_info = wx.AboutDialogInfo()
     about_info.SetName( 'Plotting GUI' )
     about_info.SetVersion( 'v%s'%__version__ )
     about_info.SetDevelopers( ['Artur Glavic'] )
     about_info.SetCopyright( '\302\251 Copyright 2008-2010 Artur Glavic\n a.glavic@fz-juelich.de' )
     about_info.SetWebSite("http://www.fz-juelich.de/iff/Glavic_A/")
     dialog = wx.AboutBox( about_info )
  
  def show_config_path(self, action):
     '''
       Show a dialog with the path to the config files.
     '''
     import config
     dialog = wx.MessageDialog(self, 
                               'The configuration files can be found at: \n%s'%config.__path__[0],
                               'Configuration files',
                                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP )
     dialog.ShowModal()
     dialog.Destroy()

      
  def iterate_through_measurements(self, event):
     ''' 
       Change the active plot with arrows in toolbar.
     '''
     print 'generic.py: Entry iterate_through_measurements'
     id   = event.GetId()
     print 'event.GetId = ',id
     name = self.action_dict[id]

     # change number for active plot put it in the plot page entry box at the bottom
     self.file_actions.activate_action('iterate_through_measurements', name)
     # check for valid number
     if self.index_mess>=len(self.measurement):
       self.index_mess=len(self.measurement)-1
     if self.index_mess<0:
       self.index_mess=0
     # close all open dialogs
     for window in self.open_windows:
       window.Destroy()

     self.active_multiplot=False
     # recreate the menus, if the columns for this dataset aren't the same
     self.rebuild_menus()
     # plot the data
     self.replot()

  def remove_active_plot(self, action):
    '''
      Remove the active plot from this session.
    '''
    if len(self.measurement)>1:
      self.garbage.append(self.measurement.pop(self.index_mess))
      self.file_actions.activate_action('iterate_through_measurements', 'Prev')
      self.replot()
      print "Plot removed."


  def change(self, event):
     '''
       Change different plot settings triggered by different events.
      
       @param action The action that triggered the event
     '''
#
#    mit wx.ID_ANY eine id vom System geben lassen und speichern: 
#        (x-number , id_nn) usw.
#        (x-time , id_nn) usw. d; x-time wird erzeugt aus 'x-' und Eintrag in dictionary:
#                                 dict = {} 
#                                 dict[id1] = 'x-number'
#                                 dict[id2] = 'x-time'

#

     id   = event.GetId()
     if self.action_dict.__contains__(id): 
       name = self.action_dict[ id ]
     else:
       name = 'undefined'

 
     # change the plotted columns
     if name == 'x-number':
       self.measurement[self.index_mess].xdata = -1

     elif name == 'y-number':
       self.measurement[self.index_mess].ydata = -1
   
     elif name[0] == 'x':
       dim = name[2:]
       self.measurement[self.index_mess].xdata=self.measurement[self.index_mess].dimensions().index(dim)

     elif name[0]=='y':
       dim = name[2:]
       self.measurement[self.index_mess].ydata=self.measurement[self.index_mess].dimensions().index(dim)

     elif name[0]=='z':
       dim = name()[2:]
       self.measurement[self.index_mess].zdata=self.measurement[self.index_mess].dimensions().index(dim)

     elif name[0]=='d':
       dim = name[3:]
       self.measurement[self.index_mess].yerror=self.measurement[self.index_mess].dimensions().index(dim)

     # change 3d view position
     elif id == idViewLeft:
       if self.measurement[self.index_mess].view_z>=10:
         self.measurement[self.index_mess].view_z=self.measurement[self.index_mess].view_z-10
       else:
         self.measurement[self.index_mess].view_z=350
     elif id == idViewRight:
       if self.measurement[self.index_mess].view_z<=340:
         self.measurement[self.index_mess].view_z=self.measurement[self.index_mess].view_z+10
       else:
         self.measurement[self.index_mess].view_z=0
     elif id == idViewUp:
       if self.measurement[self.index_mess].view_x<=160:
         self.measurement[self.index_mess].view_x=self.measurement[self.index_mess].view_x+10
       else:
         self.measurement[self.index_mess].view_x=0
     elif id == idViewDown:
       if self.measurement[self.index_mess].view_x>=10:
         self.measurement[self.index_mess].view_x=self.measurement[self.index_mess].view_x-10
       else:
         self.measurement[self.index_mess].view_x=170

     # change plot title labels
     elif id == idLabel or id == idLabel2:
       self.measurement[self.index_mess].sample_name=self.label.GetValue()
       self.measurement[self.index_mess].short_info=self.label2.GetValue()

     # change log settings
     # TODO: check if realy log was triggering this action
     else:
       self.measurement[self.index_mess].logx = self.logx.GetValue()
       self.measurement[self.index_mess].logy = self.logy.GetValue()
       self.measurement[self.index_mess].logz = self.logz.GetValue()


     print 'generic.py change: vor replot'
     self.replot()                           # plot with new Settings


  
  def change_active_file(self, action):
     '''
       Change the active datafile for plotted sequences.
     '''
     print 'generic.py: Entry change_active_file'
     id   = action.GetId()
     if self.action_dict.__contains__(id): 
       name = self.action_dict[ id ]
     else:
       name = 'undefined'

     print 'name = ',name
     index=int(name.split('-')[-1])
     object=sorted(self.active_session.file_data.items())[index]
     self.change_active_file_object(object)
  


  def change_active_file_object(self, object):
     '''
       Change the active file object from which the plotted sequences are extracted.
    
       @param object A list of MeasurementData objects from one file
     '''
     print 'generic.py: Entry change_active_session_file_object'
     self.active_session.change_active(object)
     self.measurement=self.active_session.active_file_data
     self.input_file_name=object[0]
     # reset index to the first sequence in that file
     self.index_mess=0
     self.plot_page_entry.SetValue(str(int(self.measurement[0].number)))
     self.plot_page_entry.SetMaxLength(len(self.measurement[-1].number))
     for window in self.open_windows:
       window.Destroy()    
     self.replot()
  


  def add_file(self, action):
     '''
       Import one or more new datafiles of the same type.
      
       @return List of names that have been imported.
     '''
     print 'generic.py: Entry add_file'
     file_names=[]
     #++++++++++++++++File selection dialog+++++++++++++++++++#

     file_dialog = wx.FileDialog(self, message='Open new datafile',
                                 style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
#    bei Return: response ist wx.ID_OK
#    Achtung: SetWildcard --> der String darf keine zusaetlichen Blanks enthalten



     print 'FILE_WILDCARDS =', self.active_session.FILE_WILDCARDS
     filter = ''
     for wildcard in self.active_session.FILE_WILDCARDS:
       filter += wildcard[0] + '|' 
       for pattern in wildcard[1:]:
           filter += pattern + ';'
       filter += '|'

     filter += 'All files (*.*)|*.*'
#    Achtung: Filter darf nicht mit '|' enden --> auf MAC Fehler
     
     print 'filter = ',filter

     file_dialog.SetWildcard( filter )

     response = file_dialog.ShowModal()

     print 'Return from filedialog: ',response
     if response == wx.ID_OK:
        print 'respone = ok'
        files = file_dialog.GetFilenames()
        dir   = file_dialog.GetDirectory()
        file_names = [dir+'/'+item for item in files]
        print 'file_names = ', file_names
     elif response == wx.ID_CANCEL:
        print 'response = cancel'
        file_dialog.Destroy()
        return False
    
     file_dialog.Destroy()


     #----------------File selection dialog-------------------#
     # try to import the selected files and append them to the active sesssion
     if self.active_session.ONLY_IMPORT_MULTIFILE:
       self.active_session.add_file(file_names, append=True)
     else:
       for file_name in file_names:
         self.active_session.add_file(file_name, append=True)
         self.active_session.change_active(name=file_name)
     # set the last imported file as active
     self.measurement=self.active_session.active_file_data
     self.input_file_name=self.active_session.active_file_name
     self.index_mess=0
     self.plot_page_entry.SetValue(str(int(self.measurement[0].number)))
     self.plot_page_entry.SetMaxLength(len(self.measurement[-1].number))
     for window in self.open_windows:
       window.Destroy()

       
     if getattr(self, 'menu_bar', False):
       self.replot()
       self.rebuild_menus()
     # TODO: do we need to return the file name?
     print 'return from add_file: file_names = ', file_names
     return file_names


  def save_snapshot(self, action, action_name):
    '''
      Save a snapshot of the active work.
    '''
    print 'main_window.py: entry save_snapshot action_name = ', action_name
      
    if action_name == 'SaveSnapshot':
      name = None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog = wx.FileDialog(self, message='Save Snapshot to File...',
                                  style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR )

      file_dialog.SetDirectory(self.active_folder)
      if sys.platform == 'darwin':
        file_dialog.SetPath(self.active_session.active_file_name+'.mdd')
      else:
        file_dialog.SetFilename(self.active_session.active_file_name+'.mdd')
        
      filter  = ''
      filter += 'Snapshots (*.mdd)|*.mdd'
      filter += '|All files|*'
      file_dialog.SetWildcard( filter )

      response = file_dialog.ShowModal()
      if response == wx.ID_OK:
        self.active_folder = file_dialog.GetDirectory()
        name               = file_dialog.GetPath()
        if not name.endswith(".mdd"):
          name += ".mdd"
      elif response == wx.ID_CANCEL:
        file_dialog.Destroy()
        return False
      file_dialog.Destroy()
      #----------------File selection dialog-------------------#



    self.active_session.store_snapshot(name)
  
  def load_snapshot(self, action, action_name):
    '''
      Load a snapshot of earlier work.
    '''
    print 'main_window.py: entry load_snapshot action_name = ', action_name


    if action_name == 'LoadSnapshot':
      name = None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog = wx.FileDialog(self, message='Load Snapshot from File...',
                                  style = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_CHANGE_DIR )
      file_dialog.SetDirectory(self.active_folder)
      filter  = ''
      filter += 'Snapshots (*.mdd)|*.mdd'
      filter += '|All files|*'
      file_dialog.SetWildcard( filter )

      response = file_dialog.ShowModal()
      if response == wx.ID_OK:
        self.active_folder = file_dialog.GetDirectory()
        name = file_dialog.GetPath()
        if not name.endswith(".mdd"):
          name+=".mdd"
      elif response == wx.ID_CANCEL:
        file_dialog.Destroy()
        return False
      file_dialog.Destroy()
      #----------------File selection dialog-------------------#


    self.active_session.reload_snapshot( name )
    self.measurement = self.active_session.active_file_data
    self.replot()

  def change_range(self,action):
     '''
       Change plotting range according to textinput.
     '''
     print 'generic.py: Entry change_range'
     # set the font size
     try:
       self.active_session.font_size = float(self.font_size.GetValue())
       self.replot()
     except ValueError:
       self.active_session.font_size=24.
       self.font_size.SetValue('24')
       self.replot()
     # get selected ranges
     xin = self.x_range_in.GetValue().lstrip('[').rstrip(']').split(':',1)
     yin = self.y_range_in.GetValue().lstrip('[').rstrip(']').split(':',1)
     zin = self.z_range_in.GetValue().lstrip('[').rstrip(']').split(':',1)
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
       self.x_range_in.SetValue('')
     if (len(yin)==2) and\
         ((yin[0].replace('-','').replace('e','').replace('.','',1).isdigit())|\
           (yin[0]==''))&\
         ((yin[1].replace('-','').replace('e','').replace('.','',1).isdigit())|\
         (yin[1]=='')):
       self.y_range='set yrange ['+str(yin[0])+':'+str(yin[1])+']'
     else:
       self.y_range='set autoscale y'
       self.y_range_in.SetValue('')
     if (len(zin)==2) and\
         ((zin[0].replace('-','').replace('e','').replace('.','',1).isdigit())|\
           (zin[0]==''))&\
         ((zin[1].replace('-','').replace('e','').replace('.','',1).isdigit())|\
         (zin[1]=='')):
       self.z_range='set zrange ['+str(zin[0])+':'+str(zin[1])+']\nset cbrange ['+str(zin[0])+':'+str(zin[1])+']'
     else:
       self.z_range='set autoscale z\nset autoscale cb'
       self.z_range_in.SetValue('')
     # add the ranges to the plot options
     self.measurement[self.index_mess].plot_options=self.measurement[self.index_mess].plot_options+\
     self.x_range+\
     '\n'+self.y_range+\
     '\n'+self.z_range+'\n'
     self.replot()                                   # plot with new settings



  def open_plot_options_window(self,action):
     '''
       Open a dialog window to insert additional gnuplot commands.
       After opening the button is rerouted.
     '''
     print 'generic.py: Entry open_plot_options_window'
     self.dialog = wx.Dialog(self, wx.ID_ANY, title='Custom Gnuplot settings', size=(800,650), 
                        style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
     table = wx.BoxSizer( wx.VERTICAL ) 
     self.dialog.SetSizer(table)

     # TODO: Add gnuplot help functions and character selector
     #+++++++++++++++++ Adding input fields in table +++++++++++++++++
     # PNG terminal
     label1 = wx.StaticText( self.dialog )
     label1.SetLabel('Terminal for PNG export (as shown in GUI Window):')
     table.Add( label1, 0, wx.ALIGN_CENTER, 3 )

     self.terminal_png = wx.TextCtrl( self.dialog )
     self.terminal_png.ChangeValue( gnuplot_preferences.set_output_terminal_png )
     table.Add( self.terminal_png, 0, wx.EXPAND, 3 )

     # PS terminal
     label2 = wx.StaticText( self.dialog )
     label2.SetLabel('Terminal for PS export:')
     table.Add( label2, 0, wx.ALIGN_CENTER, 3)

     self.terminal_ps = wx.TextCtrl( self.dialog )
     self.terminal_ps.SetLabel( gnuplot_preferences.set_output_terminal_ps )
     table.Add( self.terminal_ps, 0, wx.EXPAND, 3 )

     # x-,y- and z-label
     hbox         = wx.BoxSizer( wx.HORIZONTAL )
     xlabel       = wx.StaticText( self.dialog )
     self.x_label = wx.TextCtrl( self.dialog )
     xlabel.SetLabel( 'x-label:' )
     self.x_label.SetLabel( gnuplot_preferences.x_label )

     ylabel       = wx.StaticText( self.dialog )
     self.y_label = wx.TextCtrl( self.dialog )
     ylabel.SetLabel( 'y-label:' )
     self.y_label.SetLabel( gnuplot_preferences.y_label )

     zlabel       = wx.StaticText( self.dialog )
     self.z_label = wx.TextCtrl( self.dialog )
     zlabel.SetLabel( 'z-label:' )
     self.z_label.SetLabel( gnuplot_preferences.z_label )

     hbox.Add( xlabel,       0,  wx.ALL|wx.CENTER,    3 )
     hbox.Add( self.x_label, 1, wx.EXPAND|wx.CENTER, 3 )
     hbox.Add( ylabel,       0, wx.ALL|wx.CENTER,    3 )
     hbox.Add( self.y_label, 1, wx.EXPAND|wx.CENTER, 3 )
     hbox.Add( zlabel,       0, wx.ALL|wx.CENTER,    3 )
     hbox.Add( self.z_label, 1, wx.EXPAND|wx.CENTER, 3 )
      
     table.Add( hbox, 0, wx.EXPAND|wx.ALL, 3 )


     # parameters for plot
     label3 = wx.StaticText(self.dialog )
     label3.SetLabel('Parameters for normal plot:' )
     self.plotting_parameters = wx.TextCtrl( self.dialog )
     self.plotting_parameters.SetLabel(gnuplot_preferences.plotting_parameters )
     table.Add( label3, 0, wx.ALL|wx.CENTER, 3 )
     table.Add( self.plotting_parameters, 0, wx.EXPAND|wx.CENTER, 3 )

     # parameters for plot with errorbars
     label4 = wx.StaticText( self.dialog )
     label4.SetLabel( 'Parameters for plot with errorbars:' )
     self.plotting_parameters_errorbars = wx.TextCtrl( self.dialog )
     self.plotting_parameters_errorbars.SetLabel( gnuplot_preferences.plotting_parameters_errorbars )
     table.Add( label4, 0, wx.ALL|wx.CENTER, 3 )
     table.Add( self.plotting_parameters_errorbars, 0, wx.EXPAND|wx.CENTER, 3 )

     # parameters for plot in 3d
     label3d = wx.StaticText( self.dialog )
     label3d.SetLabel('Parameters for 3d plot:')
     table.Add( label3d, 0, wx.ALL|wx.CENTER, 3  )

     box3d   = wx.BoxSizer( wx.HORIZONTAL )

     self.plotting_parameters_3d = wx.TextCtrl( self.dialog )
     self.plotting_parameters_3d.SetLabel( gnuplot_preferences.plotting_parameters_3d )
     box3d.Add( self.plotting_parameters_3d, 1, wx.ALL, 3 )

     box3dr   = wx.BoxSizer( wx.VERTICAL )
     self.plotting_settings_3d    = wx.TextCtrl( self.dialog, wx.ID_ANY, style=wx.TE_MULTILINE )
     self.plotting_settings_3dmap = wx.TextCtrl( self.dialog, wx.ID_ANY, style=wx.TE_MULTILINE )
     self.plotting_settings_3d.SetLabel( gnuplot_preferences.settings_3d )
     self.plotting_settings_3dmap.SetLabel( gnuplot_preferences.settings_3dmap )
     box3dr.Add( self.plotting_settings_3d,    1, wx.ALL|wx.EXPAND, 3 )
     box3dr.Add( self.plotting_settings_3dmap, 1, wx.ALL|wx.EXPAND, 3 )
     box3d.Add( box3dr, 1, wx.ALL, 3 )
     table.Add( box3d,  0, wx.EXPAND|wx.CENTER, 3)
     

     # additional Gnuplot commands
     label5 = wx.StaticText( self.dialog )
     label5.SetLabel( 'Gnuplot commands executed additionally:' )
     sw     = wx.TextCtrl( self.dialog, wx.ID_ANY, style=wx.TE_MULTILINE )
     table.Add( label5, 0, wx.ALL|wx.CENTER,    3 )
     table.Add( sw,     0, wx.EXPAND|wx.CENTER, 3 )


     print ' self.measurement[self.index_mess].zdata = ',self.measurement[self.index_mess].zdata 
     if self.measurement[self.index_mess].zdata<0:
       label3d.Disable()
       self.plotting_parameters_3d.Disable()
       self.plotting_settings_3d.Disable()
       self.plotting_settings_3dmap.Disable()


     add_button = wx.Button(self.dialog, label='Apply and Replot')                        # button replot has handler_id 1
     table.Add( add_button, 0, wx.ALL|wx.EXPAND,  3 )



     add_button.Bind( wx.EVT_BUTTON, handler= self.change_plot_options )
     self.dialog.Bind( wx.EVT_CLOSE, handler=self.close_plot_options_window )

     self.dialog.ShowModal(  )
     self.plot_options_window_open = True
     

##     # reroute the button to close the dialog, not open it
##     self.plot_options_button.disconnect(self.plot_options_handler_id)
##     self.plot_options_handler_id=self.plot_options_button.connect("clicked",lambda *w: dialog.destroy())
     # connect dialog to main window
     self.open_windows.append(self.dialog)
##     dialog.connect("destroy", lambda *w: self.open_windows.remove(dialog))    




  def close_plot_options_window(self, event):
     '''
       Reroute the plot options button and remove the textbox when dialog is closed.
       If this is not done, the textbox gets destroyed and we can't reopen the dialog.
      
       @param dialog The dialog widget that will be closed
       @param sw The scrolledWindow to be unpluged before closing.
     '''
     print 'generic.py: Entry close_plot_options_window'
     self.dialog.Destroy()
     self.plot_options_window_open = False


##  def close_plot_options_window(self,dialog,sw):
##     sw.remove(self.plot_options_view)
##     # reroute the button to open a new window
##     self.plot_options_button.disconnect(self.plot_options_handler_id)
##     self.plot_options_handler_id=self.plot_options_button.connect("clicked",self.open_plot_options_window)



  def change_plot_options(self, event ):
      print 'generic.py: Entry change_plot_options'
      '''
       Plot with new commands from dialog window. Gets triggerd when the apply
       button is pressed.
      '''
      self.measurement[self.index_mess].plot_options = self.plot_options_buffer
##      self.measurement[self.index_mess].plot_options = self.plot_options_buffer.get_text(\
##                                                       self.plot_options_buffer.get_start_iter(),\
##                                                       self.plot_options_buffer.get_end_iter() )
      gnuplot_preferences.set_output_terminal_png       = self.terminal_png.GetValue()
      gnuplot_preferences.set_output_terminal_ps        = self.terminal_ps.GetValue()
      gnuplot_preferences.x_label                       = self.x_label.GetValue()
      gnuplot_preferences.y_label                       = self.y_label.GetValue()
      gnuplot_preferences.z_label                       = self.z_label.GetValue()
      gnuplot_preferences.plotting_parameters           = self.plotting_parameters.GetValue()
      gnuplot_preferences.plotting_parameters_errorbars = self.plotting_parameters_errorbars.GetValue()
      gnuplot_preferences.plotting_parameters_3d        = self.plotting_parameters_3d.GetValue()
      gnuplot_preferences.settings_3d                   = self.plotting_settings_3d.GetValue()
      gnuplot_preferences.settings_3dmap                = self.plotting_settings_3dmap.GetValue()

      print 'gnuplot_preferences.set_output_terminal_png       = ',gnuplot_preferences.set_output_terminal_png
      print 'gnuplot_preferences.set_output_terminal_ps        = ',gnuplot_preferences.set_output_terminal_ps
      print 'gnuplot_preferences.x_label                       = ',gnuplot_preferences.x_label
      print 'gnuplot_preferences.y_label                       = ',gnuplot_preferences.y_label
      print 'gnuplot_preferences.z_label                       = ',gnuplot_preferences.z_label
      print 'gnuplot_preferences.plotting_parameters           = ',gnuplot_preferences.plotting_parameters
      print 'gnuplot_preferences.plotting_parameters_errorbars = ',gnuplot_preferences.plotting_parameters_errorbars
      print 'gnuplot_preferences.settings_3d                   = ',gnuplot_preferences.settings_3d
      print 'gnuplot_preferences.settings_3dmap                = ',gnuplot_preferences.settings_3dmap

      self.replot()                                                           # plot with new settings


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
     name = wx.GetTextFromUser('Enter profile name:', default_value='Enter Name', parent=self)
     # add the profile to the profiles dictionary
     print 'generic.py: save_profile name = ',name
     self.profiles[name] = PlotProfile(name)
     self.profiles[name].save(self)
     # new profile has to be added to the menu
     self.menuProfile.Insert(0, wx.ID_ANY,name)

  def delete_profile(self,action):
     '''
       Delete a plot profile.
     '''
     # open a dialog for selecting the profiel to be deleted
     self.delete_name = wx.GetSingleChoice('Delete profile:', 'Delete profile', self.profiles.keys())

     # only delete when the response is 'Ok'
     if  self.delete_name != '':
       id = self.menuProfile.FindItem( self.delete_name)
       self.menuProfile.Delete( id )
       del self.profiles[self.delete_name]
       del self.delete_name


  def set_delete_name(self,action):
     '''
       Set self.delete_name from entry object.
     '''
     print 'generic.py: entry set_delete_name'
     self.delete_name = action.GetLabel()

  def show_last_plot_params(self,action):
     '''
       Show a text window with the text, that would be used for gnuplot to
       plot the current measurement. Last gnuplot errors are shown below,
       if there have been any.
     '''    
     global errorbars
     print 'generic.py: Entry show_last_plot_params'
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
       plot_text = measurement_data_plotting.create_plot_script(
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
     param_dialog = wx.Dialog(self, wx.ID_ANY, title='Last plot parameters:', size=(600,400), 
                        style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE|wx.VSCROLL)
     table = wx.BoxSizer( wx.VERTICAL ) 
     param_dialog.SetSizer(table)
    
     # Label
     label = wx.StaticText( param_dialog )
     label.SetLabel('Gnuplot input for the last plot:')
     table.Add( label, 0, wx.ALL|wx.CENTER, 10 )

     # plot options
     sBox      = wx.StaticBox(param_dialog)
     sBoxSizer = wx.StaticBoxSizer( sBox, wx.VERTICAL )
     sw = wx.TextCtrl( param_dialog, wx.ID_ANY, style=wx.ALIGN_LEFT|wx.TE_MULTILINE|wx.TE_READONLY, size=(500,300) )
     sw.SetValue( plot_text )
     table.Add(sBoxSizer, 0, wx.ALL|wx.EXPAND, 0)
     sBoxSizer.Add( sw, 0, wx.ALIGN_LEFT|wx.EXPAND )

     # errors of the last plot
     if self.last_plot_text!='':
       # Label
       label = wx.StaticText( param_dialog )
       label.SetLabel('Error during execution:')
       table.Add( label, 0, wx.ALL|wx.CENTER, 10 )
       sBox      = wx.StaticBox(param_dialog)
       sBoxSizer = wx.StaticBoxSizer( sBox, wx.VERTICAL )
       sw = wx.TextCtrl( param_dialog, wx.ID_ANY, style=wx.ALIGN_LEFT|wx.TE_MULTILINE|wx.TE_READONLY, size=(500,200) )
       sw.SetValue( self.last_plot_text ) 
       sw.SetValue( self.last_plot_text ) 
       table.Add(sBoxSizer, 0, wx.ALL|wx.EXPAND, 0)
       sBoxSizer.Add( sw, 0, wx.ALIGN_LEFT|wx.EXPAND )

     # connect dialog to main window
     self.open_windows.append(param_dialog)
##     param_dialog.connect("destroy", lambda *w: self.open_windows.remove(param_dialog))  
     param_dialog.ShowModal()  
     print 'generic.py: Return from show_last_plot_params'


  def show_status_dialog(self, action ):
      '''
        Show the dialog which holds the file import informations.
      '''
      print 'main_window.py: Entry show_status_dialog'
      if self.status_dialog:
        self.status_dialog.show_all()
        


  def change_data_filter(self,action):
     '''
       A dialog to select filters, that remove points from the plotted dataset.
     '''
     # TODO: let filter dialog stay open while replotting

     def butClicked(  event ):
         id = event.GetId()
         ret = 0
         if id == idBut1:
           ret = 2
         elif id == idBut2:
           ret = 1
         filter_dialog.EndModal( ret )



     print 'generic.py: Entry change_data_filter'
     filters = []
     data    = self.measurement[self.index_mess]
     filter_dialog = wx.Dialog(self, wx.ID_ANY, title='Filter the plotted data:', size=(500,150),
                               style=wx.RESIZE_BORDER )
     table = wx.BoxSizer( wx.VERTICAL )
     filter_dialog.SetSizer( table )
     

     filterBox = wx.GridBagSizer( )
     row = 1

     # add lines for every active filter
     print 'data.filters = ', data.filters
     for data_filter in data.filters:
       filters.append(self.get_new_filter(filter_dialog, filterBox, row, data, data_filter))
       row += 1

     filters.append(self.get_new_filter(filter_dialog, filterBox, row, data))
     row += 1

     table.Add(filterBox, 0, wx.ALL, 3)

     # add dialog buttons
     butSizer = wx.BoxSizer( wx.HORIZONTAL )
     but1 = wx.Button( filter_dialog, wx.ID_ANY, label='New Filter')       # returns 2
     but1.Bind( wx.EVT_BUTTON, handler=butClicked )
     idBut1 = but1.GetId()
     but2 = wx.Button( filter_dialog, wx.ID_ANY, label='Apply changes' )   # returns 1    
     but2.Bind( wx.EVT_BUTTON, handler=butClicked )
     idBut2 = but2.GetId()
     but3 = wx.Button( filter_dialog, wx.ID_ANY, label='Cancel' )          # returns 0  
     but3.Bind( wx.EVT_BUTTON, handler=butClicked )
     idBut3 = but3.GetId()
     butSizer.Add( but1, 0, wx.ALL|wx.EXPAND, 3 )  
     butSizer.Add( but2, 0, wx.ALL|wx.EXPAND, 3 )  
     butSizer.Add( but3, 0, wx.ALL|wx.EXPAND, 3 )  

     table.Add( butSizer, 0, wx.EXPAND|wx.CENTER, 3 )

     # open dialog and wait for a response
     response = filter_dialog.ShowModal()
     print 'response = ', response

     # if the response is 'New Filter' add a new filter row and rerun the dialog
     while(response==2):
       print ' new filter'
       filters.append(self.get_new_filter(filter_dialog, filterBox, row, data))
       row += 1
       filter_dialog.Fit()
       print 'hinter filter_dialog.Fit()'
       response = filter_dialog.ShowModal()

     # if response is apply change the dataset filters
     if response==1:
       print 'Apply changes'
       new_filters=[]
       print 'fiilters = ', filters
       for filter_widgets in filters:
         if (filter_widgets[0].GetSelection() == wx.NOT_FOUND) | (filter_widgets[0].GetSelection() == 0):
           continue
         new_filters.append(\
           (filter_widgets[0].GetSelection()-1,\
           float(filter_widgets[1].GetValue()),\
           float(filter_widgets[2].GetValue()),\
           filter_widgets[3].IsChecked())\
           )
       self.file_actions.activate_action('change filter', new_filters)
       data.filters=new_filters
     # close dialog and replot
     self.replot()
    
  def get_new_filter( self, dialog, filterBox, row, data, parameters=(-1,0,0,False)):
     ''' 
       Create all widgets for the filter selection of one filter in 
       change_data_filter dialog and place them in a table.
      
       @return Sequence of the created widgets.
     '''
     print 'Entry get_new_filter: row = ', row

     hBox = wx.BoxSizer( wx.HORIZONTAL )

     column = wx.ComboBox( dialog )
     column.Append('None')
     
     # drop down menu for the columns present in the dataset
     for column_dim in data.dimensions():
       column.Append(column_dim)

     column.SetSelection(parameters[0]+1)
     hBox.Add(column, 0, wx.ALL, 3 )

     from_data = wx.TextCtrl( dialog, wx.ID_ANY )
     from_data.SetMaxLength(8)
     from_data.SetValue(str(parameters[1]))
     hBox.Add( from_data, 0, wx.ALL|wx.EXPAND, 3 )

     to_data = wx.TextCtrl( dialog, wx.ID_ANY )
     to_data.SetMaxLength(8)
     to_data.SetValue(str(parameters[2]))
     hBox.Add( to_data, 0, wx.ALL|wx.EXPAND, 3 )

     include = wx.CheckBox(dialog, wx.ID_ANY, label='include region')
     include.SetValue(parameters[3])
     hBox.Add( include, 0, wx.ALL|wx.EXPAND, 3 )

     filterBox.Add( hBox, wx.GBPosition(row-1,0) )

     return (column,from_data,to_data,include)
  
  def unit_transformation(self, action):
     '''
       Open a dialog to transform the units and dimensions of one dataset.
       A set of common unit transformations is stored in config.transformations.
     '''
     def butClicked(  event ):
         id = event.GetId()
         ret = 0
         if id == idBut1:
           ret = 2
         elif id == idBut2:
           ret = 1
         transformation_dialog.EndModal( ret )


     # TODO: More convinient entries.
     print 'generic.py: Entry unit_transformation'
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

     transformation_dialog = wx.Dialog(self, wx.ID_ANY, title='Transform Units/Dimensions:', size=(900,200),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
     table = wx.GridBagSizer(  )
     transformation_dialog.SetSizer( table )

     trans_box = wx.ComboBox(transformation_dialog)
     trans_box.Append('empty')
     for trans in allowed_trans:
       trans_box.Append('%s -> %s' % (trans[0], trans[-1]))
     try:
       but1 = wx.Button( transformation_dialog, wx.ID_ANY, label='Add transformation')       # returns 2
       but1.Bind( wx.EVT_BUTTON, handler=butClicked )
       but2 = wx.Button( transformation_dialog, wx.ID_ANY, label='Apply changes')            # returns 1
       but2.Bind( wx.EVT_BUTTON, handler=butClicked )
       but3 = wx.Button( transformation_dialog, wx.ID_ANY, label='Cancel')                   # returns 0
       but3.Bind( wx.EVT_BUTTON, handler=butClicked )

       idBut1 = but1.GetId()
       idBut2 = but2.GetId()
       idBut3 = but3.GetId()
       table.Add( but3, wx.GBPosition(1,0), flag=wx.EXPAND)
       table.Add( but2, wx.GBPosition(2,0), flag=wx.EXPAND)
       table.Add( but1, wx.GBPosition(3,0), flag=wx.EXPAND )


     except AttributeError:
         pass
##       transformations_dialog.vbox.pack_end(trans_box,False)
##       button=gtk.Button('Add transformation')
##       button.connect('clicked', lambda *ignore: transformations_dialog.response(2))
##       transformations_dialog.vbox.pack_end(button,False)
##       button=gtk.Button('Apply changes')
##       button.connect('clicked', lambda *ignore: transformations_dialog.response(1))
##       transformations_dialog.vbox.pack_end(button,False)
##       button=gtk.Button('Cancel')
##       button.connect('clicked', lambda *ignore: transformations_dialog.response(0))
##       transformations_dialog.vbox.pack_end(button,False)

     table.Add( trans_box, wx.GBPosition(4,0), flag=wx.EXPAND )

     result = transformation_dialog.ShowModal()
     print 'result = ', result
   
     transformations_list=[]
     while(result==2):
       index = trans_box.GetSelection()
       if index>0:
         trans=allowed_trans[index-1]
       else:
         trans=['', '', 1., 0, '', '']

       self.get_new_transformation(trans, transformation_dialog, table, transformations_list)
       trans_box.SetSelection(0)
       result = transformation_dialog.ShowModal()

     if result==1:
       transformations=self.create_transformations(transformations_list, units, dimensions)
       self.file_actions.activate_action('unit_transformations', transformations)
       self.replot()
       self.rebuild_menus()


  def get_new_transformation(self, transformations, transformation_dialog, dialog_table,  list):
     '''
       Create a entry field line for a unit transformation.
     '''
     print 'generic.py: Entry get_new_transformation'
     table = wx.BoxSizer( wx.HORIZONTAL )
     entry_list=[]
     entry = wx.TextCtrl( transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(transformations[0])
     entry_list.append(entry)
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )

     entry = wx.TextCtrl( transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(transformations[1])
     else:
       entry.SetValue(transformations[0])
     entry_list.append(entry)
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )
    
     label = wx.StaticText( transformation_dialog, label=' * ')
     table.Add( label, 0, wx.ALL|wx.CENTER, 3 )

     entry = wx.TextCtrl(transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(str(transformations[2]))
     else:
       entry.SetValue(str(transformations[1]))
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )
     entry_list.append(entry)

     label = wx.StaticText( transformation_dialog, label=' + ')
     table.Add( label, 0, wx.ALL|wx.CENTER, 3 )

     entry = wx.TextCtrl(transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(str(transformations[3]))
     else:
       entry.SetValue(str(transformations[2]))
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )
     entry_list.append(entry)

     label = wx.StaticText( transformation_dialog, label=' -> ')
     table.Add( label, 0, wx.ALL|wx.CENTER, 3 )

     entry = wx.TextCtrl(transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(transformations[4])
     else:
       entry.SetValue(transformations[3])
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )
     entry_list.append(entry)


     entry = wx.TextCtrl(transformation_dialog, wx.ID_ANY )
     entry.SetMaxLength(8)
     if len(transformations)>4:
       entry.SetValue(transformations[5])
     table.Add( entry, 0, wx.ALL|wx.CENTER, 3 )
     entry_list.append(entry)

     dialog_table.Add( table, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND )

     transformation_dialog.Fit()                  # Update und Groesse anpassen

     item=(table, entry_list)
     list.append(item)

     button = wx.Button( transformation_dialog, wx.ID_ANY, label='DEL')
     table.Add( button, 0, wx.ALL, 3 )
     button.Bind( wx.EVT_BUTTON, handler=self.remove_transformation )

  
  def remove_transformation(self, event):
     '''
       Nothing jet.
     '''
     print 'generic.py: Entry remove_transformation'
     pass
  
  def create_transformations(self, items, units, dimensions):
     '''
       Read the transformation values from the entry widgets in 'items'.
     '''
     print 'generic.py: Entry create_transformations'
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

     def butClicked(  event ):
         id = event.GetId()
         print 'generic.py: combine_data_points butClicked: id = ', id
         ret = 0
         if id == idBut1:
           ret = 1
         cd_dialog.EndModal( ret )

     def textEnter(  event ):
         print 'generic.py: combine_data_points textEnter'
         ret = 1
         cd_dialog.EndModal( ret )

     print 'generic.py: Entry combine_data_points'
     cd_dialog = wx.Dialog(self, wx.ID_ANY, title='Combine data points:', size=(300,200),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
     vbox = wx.BoxSizer( wx.VERTICAL )
     cd_dialog.SetSizer( vbox  )


     table = wx.GridBagSizer(  )
     label = wx.StaticText(cd_dialog, label='Binning:')
     table.Add( label, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND )

     binning = wx.TextCtrl( cd_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     binning.SetMaxLength(4)
     binning.SetValue('1')
     binning.Bind( event=wx.EVT_TEXT_ENTER, handler=textEnter )  
     table.Add( binning, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cd_dialog, label='Stepsize:\n(overwrites Binning)' )
     table.Add( label, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND )

     bin_distance = wx.TextCtrl( cd_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     bin_distance.SetMaxLength(4)
     bin_distance.SetValue('None')
     bin_distance.Bind( event=wx.EVT_TEXT_ENTER, handler=textEnter )  
     table.Add( bin_distance, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND )

     vbox.Add( table, wx.CENTER|wx.EXPAND )

     butBox = wx.BoxSizer( wx.HORIZONTAL )
   
     but1 = wx.Button( cd_dialog, wx.ID_ANY, label='Ok')                       # returns 1
     idBut1 = but1.GetId()
     but2 = wx.Button( cd_dialog, wx.ID_ANY, label='Cancel')                   # returns 0
     but1.Bind( wx.EVT_BUTTON, handler=butClicked )
     but2.Bind( wx.EVT_BUTTON, handler=butClicked )
     butBox.Add( but1, wx.CENTER|wx.EXPAND )
     butBox.Add( but2, wx.CENTER|wx.EXPAND )

     vbox.Add( butBox, wx.CENTER|wx.EXPAND )

     cd_dialog.Fit()
     result = cd_dialog.ShowModal()
     print 'result = ', result

     if result==1:
       try:
         bd=float(bin_distance.GetValue())
       except ValueError:
         bd=None
       self.file_actions.activate_action('combine-data', 
                                         int(binning.GetValue()), 
                                         bd
                                         )

     self.rebuild_menus()
     self.replot()      


  def savitzky_golay( self, action ):
    '''
     Filter the dataset with Savitzky_Golay filter.
    '''
    print 'main_window.py: Entry savitzky_golay'
    parameters, result=SimpleEntryDialog(None, 'Savitzky Golay Filter...', 
                         (('Window Size', 5, int), ('Polynomial Order', 2, int),
                         ('Maximal Derivative', 1, int))).run()
#   Rueckgabewert result ist True oder False

    if parameters['Polynomial Order']>parameters['Window Size']-2:
      parameters['Polynomial Order']=parameters['Window Size']-2
    if parameters['Maximal Derivative']+1>parameters['Polynomial Order']:
      parameters['Maximal Derivative']=parameters['Polynomial Order']-1
    if result:
      # create a new dataset with the smoothed data and all derivatives till the selected order
      self.file_actions.activate_action('savitzky_golay', 
                        parameters['Window Size'], 
                        parameters['Polynomial Order'], 
                        parameters['Maximal Derivative']+1)
      self.rebuild_menus()
      self.replot()

  def colorcode_points( self, action ):
    '''
     Show points colorcoded by their number.
    '''
    print 'main_window.py: Entry colorcode_points'
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

     def butClicked(  event ):
         id = event.GetId()
         print 'generic.py: extract_coss_section: butClicked: id = ', id
         ret = 0
         if id == idBut1:
           ret = 1
         cs_dialog.EndModal( ret )

     def textEnter(  event ):
         print 'generic.py: extract_cross_section textEnter'
         ret = 1
         cs_dialog.EndModal( ret )


     print 'generic.py: Entry extract_cross_section'
     data=self.measurement[self.index_mess]
     dimension_names=[]
     dims=data.dimensions()
     dimension_names.append(dims[data.xdata])
     dimension_names.append(dims[data.ydata])
     del(dims)

     cs_dialog = wx.Dialog(self, wx.ID_ANY, title='Create a cross-section:', size=(300,200),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
     vbox  = wx.BoxSizer( wx.VERTICAL )
     cs_dialog.SetSizer( vbox )

     table = wx.GridBagSizer()

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label='Direction:')
     table.Add( label, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND ) 

     label = wx.StaticText ( cs_dialog, wx.ID_ANY, label=dimension_names[0], style=wx.ALIGN_RIGHT)
     table.Add( label, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND ) 

     line_x = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     line_x.SetMaxLength(6)
     line_x.SetValue('1')
     table.Add( line_x, wx.GBPosition(0,2), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label=dimension_names[1], style=wx.ALIGN_RIGHT)
     table.Add( label, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND ) 

     line_y = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     line_y.SetMaxLength(6)
     line_y.SetValue('0')
     table.Add( line_y, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label='Start point:' )
     table.Add( label, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND ) 

     label = wx.StaticText ( cs_dialog, wx.ID_ANY, label=dimension_names[0], style=wx.ALIGN_RIGHT )
     table.Add( label, wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND ) 

     line_x0 = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     line_x0.SetMaxLength(6)
     line_x0.SetValue('0')
     table.Add( line_x0, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText ( cs_dialog, wx.ID_ANY, label=dimension_names[1], style=wx.ALIGN_RIGHT)
     table.Add( label, wx.GBPosition(3,1), flag=wx.CENTER|wx.EXPAND ) 

     line_y0 = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     line_y0.SetMaxLength(6)
     line_y0.SetValue('0')
     table.Add( line_y0, wx.GBPosition(3,2), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label='Width:' )
     table.Add( label, wx.GBPosition(5,0), flag=wx.CENTER|wx.EXPAND ) 

     line_width = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     line_width.SetMaxLength(6)
     line_width.SetValue('1')
     table.Add( line_width, wx.GBPosition(5,1), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label='Binning:' )
     table.Add( label, wx.GBPosition(6,0), flag=wx.CENTER|wx.EXPAND ) 

     binning = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     binning.SetMaxLength(4)
     binning.SetValue('1')
     table.Add( binning, wx.GBPosition(6,1), flag=wx.CENTER|wx.EXPAND )


     weight = wx.CheckBox( cs_dialog, wx.ID_ANY, 'Gauss weighting, Sigma:')
     table.Add( weight, wx.GBPosition(7,0), flag=wx.CENTER|wx.EXPAND )
     sigma = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     sigma.SetMaxLength(4)
     sigma.SetValue('1e10')
     table.Add( sigma, wx.GBPosition(7,1), flag=wx.CENTER|wx.EXPAND )

     label = wx.StaticText( cs_dialog, wx.ID_ANY, label='Stepsize:\n(overwrites Binning)' )
     table.Add( label, wx.GBPosition(8,0), flag=wx.CENTER|wx.EXPAND ) 
     bin_distance = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
     bin_distance.SetMaxLength(4)
     bin_distance.SetValue('None')
     table.Add( bin_distance, wx.GBPosition(8,1), flag=wx.CENTER|wx.EXPAND )


     vbox.Add ( table, 0, wx.EXPAND|wx.CENTER, 3 )
 
     butBox = wx.BoxSizer( wx.HORIZONTAL )
     but1 = wx.Button( cs_dialog, wx.ID_ANY, label='OK' )
     idBut1 = but1.GetId()
     but2 = wx.Button( cs_dialog, wx.ID_ANY, label='Cancel' )
     butBox.Add( but1, wx.CENTER|wx.EXPAND )
     butBox.Add( but2, wx.CENTER|wx.EXPAND )

     vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10 )

     # Enty activation triggers calculation, too
     but1.Bind( event=wx.EVT_BUTTON,             handler=butClicked )
     but2.Bind( event=wx.EVT_BUTTON,             handler=butClicked )
     line_x.Bind( event=wx.EVT_TEXT_ENTER,       handler=textEnter )
     line_y.Bind( event=wx.EVT_TEXT_ENTER,       handler=textEnter )
     line_x0.Bind( event=wx.EVT_TEXT_ENTER,      handler=textEnter )
     line_y0.Bind( event=wx.EVT_TEXT_ENTER,      handler=textEnter )
     line_width.Bind( event=wx.EVT_TEXT_ENTER,   handler=textEnter )
     binning.Bind( event=wx.EVT_TEXT_ENTER,      handler=textEnter )
     bin_distance.Bind( event=wx.EVT_TEXT_ENTER, handler=textEnter )
     sigma.Bind( event=wx.EVT_TEXT_ENTER,        handler=textEnter )

     cs_dialog.Fit()
     result = cs_dialog.ShowModal()
     print 'result = ', result

     if result==1:
       try:
         bd=float(bin_distance.GetValue())
       except ValueError:
         bd=None

       gotit=self.file_actions.activate_action('cross-section', 
                                         float(line_x.GetValue()), 
                                         float(line_x0.GetValue()), 
                                         float(line_y.GetValue()), 
                                         float(line_y0.GetValue()), 
                                         float(line_width.GetValue()), 
                                         int(binning.GetValue()), 
                                         weight.IsChecked(), 
                                         float(sigma.GetValue()), 
                                         False, 
                                         bd
                                         )
       if not gotit:
         message = wx.MessageDialog(self, 
                                'No point in selected area.',
                                'Information',
                                wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP )
         message.ShowModal()
         message.Destroy()

     else:
       gotit=False
     cs_dialog.Destroy()
     if gotit:
       self.rebuild_menus()
       self.replot()      

     return gotit

  def change_color_pattern(self, action):
     '''
       Open a dialog to select a different color pattern.
       The colorpatterns are defined in config.gnuplot_preferences.
     '''
     def butClicked(  event ):
         id = event.GetId()
         print 'generic.py: change_color_pattern: butClicked: id = ', id
         ret = 0
         if id == idBut1:
           ret = 1
         cps_dialog.EndModal( ret )

     print 'generic.py: Entry change_color_pattern'
     pattern_names=sorted(gnuplot_preferences.defined_color_patterns.keys())
     cps_dialog = wx.Dialog(self, wx.ID_ANY, title='Select new color pattern:', size=(200,100),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
     vbox = wx.BoxSizer( wx.VERTICAL ) 
     cps_dialog.SetSizer( vbox )

     pattern_box = wx.ComboBox( cps_dialog )
     # drop down menu for the pattern selection
     for pattern in pattern_names:
       pattern_box.Append(pattern)

     vbox.Add( pattern_box, 0, wx.ALL|wx.CENTER|wx.EXPAND, 3)

     butBox = wx.BoxSizer( wx.HORIZONTAL )
     but1 = wx.Button( cps_dialog, wx.ID_ANY, label='OK' )
     idBut1 = but1.GetId()
     but2 = wx.Button( cps_dialog, wx.ID_ANY, label='Cancel' )
     butBox.Add( but1, wx.CENTER|wx.EXPAND )
     butBox.Add( but2, wx.CENTER|wx.EXPAND )
     but1.Bind( event=wx.EVT_BUTTON,             handler=butClicked )
     but2.Bind( event=wx.EVT_BUTTON,             handler=butClicked )
 
     vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10 )

     cps_dialog.Fit()
     result = cps_dialog.ShowModal()
     print 'result = ',result

     if result==1:
       self.file_actions.activate_action('change_color_pattern', 
                                         gnuplot_preferences.defined_color_patterns[pattern_names[pattern_box.GetSelection()]])
     cps_dialog.Destroy()
     self.replot()



  def fit_dialog(self,action, size=(900, 350), position=None):
     '''
       A dialog to fit the data with a set of functions.
      
       @param size Window size (x,y)
       @param position Window position (x,y)
     '''

     print 'generic.py: Entry fit_dialog'
     print 'generic.py: self.active_session.ALLOW_FIT =',self.active_session.ALLOW_FIT

     if not self.active_session.ALLOW_FIT:
       msg_dialog = wx.MessageDialog(self, 
                                       "You don't have the system requirenments for Fitting.\nNumpy and Scipy must be installed and a fit_data module must be inside the GUI toolkit package.", 'Fit',
                                wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP )
       msg_dialog.ShowModal()
       msg_dialog.Destroy()
       return None

     dataset=self.measurement[self.index_mess]
     if (dataset.fit_object==None):
       self.file_actions.activate_action('create_fit_object')

     fit_session=dataset.fit_object

     fit_dialog = wx.Dialog(self, wx.ID_ANY, title='Fit ...', size=(size[0],size[1]),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
     vbox = wx.BoxSizer( wx.VERTICAL ) 
     fit_dialog.SetSizer( vbox )

     if position!=None:
       fit_dialog.Move(wx.Point(position[0], position[1]) )
     
     print 'vor Aufruf von get_dialog: self       = ', self
     print 'vor Aufruf von get_dialog: fit_dialog = ', fit_dialog

     sw = wx.ScrolledWindow( fit_dialog, wx.ID_ANY, style=wx.HSCROLL|wx.VSCROLL )
     sw.SetScrollRate(10, 10 )

     align_table, buttons = fit_session.get_dialog(self,  fit_dialog, sw)
     print 'align_table size = ',align_table.GetSize()

     actions_table = wx.BoxSizer( wx.HORIZONTAL )
     print 'len buttons =',len(buttons)
     for i, button in enumerate(buttons):
       actions_table.Add(button, 0, wx.ALIGN_LEFT|wx.ALL, 3)

     sw.SetSizer( align_table )
     vbox.Add( sw, 1, wx.ALL|wx.EXPAND, 10 )
     vbox.Add( actions_table, 0, wx.ALIGN_LEFT  )

     def fit_dialog_close(  self, parent ):
       parent.open_windows.remove(fit_dialog)
       fit_dialog.Destroy()

     fit_dialog.Bind( wx.EVT_CLOSE,  handler=lambda evt, arg1=self: fit_dialog_close( evt, arg1 ) )

     fit_dialog.Show()
     self.open_windows.append(fit_dialog)

  def show_add_info(self,action):
     '''
       Show or hide advanced options widgets.
     '''
     print 'generic.py: Entry show_add_info'
     # TODO: Do we realy need this?
     if self.check_add.IsChecked():
       self.x_range_in.Enable()
       self.x_range_label.Enable()
       self.y_range_in.Enable()
       self.y_range_label.Enable()
       self.font_size.Enable()
       self.check_add.SetLabel('')
       self.logx.Enable()
       self.logy.Enable()
       self.plot_options_button.Enable()
       if self.measurement[self.index_mess].zdata>=0:
          self.logz.Enable()
          self.z_range_in.Enable()
          self.z_range_label.Enable()
          self.view_left.Enable()
          self.view_up.Enable()
          self.view_down.Enable()
          self.view_right.Enable()
       else:
          self.logz.Disable()
          self.z_range_in.Disable()
          self.z_range_label.Disable()
          self.view_left.Disable()
          self.view_up.Disable()
          self.view_down.Disable()
          self.view_right.Disable()
     else:
##       if not action==None: # only change picture size if chack_add button is triggered
##         self.image.hide()
##         self.image_shown=False
       self.x_range_in.Disable()
       self.x_range_label.Disable()
       self.y_range_in.Disable()
       self.y_range_label.Disable()
       self.z_range_in.Disable()
       self.z_range_label.Disable()
       self.font_size.Disable()
       self.logx.Disable()
       self.logy.Disable()
       self.plot_options_button.Disable()
       self.logz.Disable()
       self.view_left.Disable()
       self.view_up.Disable()
       self.view_down.Disable()
       self.view_right.Disable()
       self.check_add.SetLabel('Show more options.')

      
  def apply_to_all(self,action): 
     '''
       Apply changed plotsettings to all plots. This includes x,y,z-ranges,
       logarithmic plotting and the custom plot settings.
     '''
     # TODO: Check if all options are included here
     print 'generic.py: Entry apply_to_all'
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
       self.statusbar.PushStatusText('Applied settings to all Plots!',0)

  def add_multiplot(self,action, action_name): 
     '''
       Add or remove the active dataset from multiplot list, 
       which is a list of plotnumbers of the same Type.
     '''
     # TODO: Review the multiplot stuff!
     print 'generic.py: Entry add_multiplot: action_name = ', action_name
     if (action_name == 'AddAll')&(len(self.measurement)<40): # dont autoadd more than 40
       for i in range(len(self.measurement)):
         self.do_add_multiplot(i)
     elif (action_name == 'ClearMultiplot'):
       self.multiplot = []
       self.active_multiplot = False
       self.replot()
       print 'Multiplots cleared.'
       self.multi_list.SetValue(' Multiplot List: \n' )
     else:
       self.do_add_multiplot(self.index_mess)

  def do_add_multiplot(self,index): 
     '''
       Add one item to multiplot list devided by plots of the same type.
     '''
     print 'generic.py: Entry do_add_multiplot: index = ', index
     changed=False
     active_data=self.measurement[index]
     for plotlist in self.multiplot:
       itemlist=[item[0] for item in plotlist]
       if active_data in itemlist:
         plotlist.pop(itemlist.index(active_data))
         self.reset_statusbar()
         self.statusbar.PushStatusText('Plot ' + active_data.number + ' removed.',0)
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
           self.statusbar.PushStatusText('Plot ' + active_data.number + ' added.',0)
           changed=True
           break
     # recreate the shown multiplot list
     if not changed:
       self.multiplot.append([(active_data, self.active_session.active_file_name)])
       self.reset_statusbar()
       self.statusbar.PushStatusText('Plot ' + active_data.number + ' added.',0)
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
     self.multi_list.SetValue(' Multiplot List: \n' + mp_list)

  def toggle_error_bars(self,action):
     '''
       Show or remove error bars in plots.
     '''
     global errorbars
     print 'generic.py: Entry toggle_error_bars'
     errorbars= not errorbars
     self.reset_statusbar()
     self.replot()
     self.statusbar.PushStatusText('Show errorbars='+str(errorbars), 0)

##   def export_plot(self, action, action_name): 
##      '''
##        Function for every export action. 
##        Export is made as .png or .ps depending on the selected file name.
##        Save is made as gnuplot file and output files.
##      '''
##      print 'generic.py: Entry export_plot: action_name = ',action_name
##      global errorbars
##      self.active_session.picture_width='1600'
##      self.active_session.picture_height='1200'
##      if action_name == 'MultiPlot':
##        if len(self.multiplot)>0:
##          self.active_multiplot=not self.active_multiplot
##        else:
##          self.active_multiplot = False
         
##        return self.replot()

##      if action_name == 'SaveGPL':
##        #++++++++++++++++File selection dialog+++++++++++++++++++#
##        file_dialog = wx.FileDialog(self, message='Save Gnuplot(.gp) and Datafiles(.out) ...',
##                                     style=wx.FD_SAVE |wx.FD_OVERWRITE_PROMPT )
##        if self.active_multiplot:
##          file_dialog.SetFilename(self.active_session.active_file_name + '_multi_')
##        else:
##          file_dialog.SetFilename(self.active_session.active_file_name + '_')

##        # create the filters in the file selection dialog
##        filter = ''
##        filter += 'Gnuplot (*.gp)|*.gp'
##        filter += '|All Files|*.*'
##        file_dialog.SetWildcard( filter )

##        response = file_dialog.ShowModal()
##        if response != wx.ID_OK:
##          file_dialog.Destroy()
##          return None

##        self.active_folder = file_dialog.GetDirectory()
##        common_folder, common_file_prefix = os.path.split(file_dialog.GetFilename().rsplit('.gp', 1)[0] )
##        print 'common_file_prefix = ', common_file_prefix
##        file_dialog.Destroy()
##        if self.active_multiplot:
##          for plotlist in self.multiplot:
##            itemlist=[item[0] for item in plotlist]
##            if self.measurement[self.index_mess] in itemlist:
##              plot_text=measurement_data_plotting.create_plot_script(
##                                            self.active_session, 
##                                            [item[0] for item in plotlist], 
##                                            common_file_prefix, 
##                                            '', 
##                                            plotlist[0][0].short_info, 
##                                            [item[0].short_info for item in plotlist], 
##                                            errorbars,
##                                            common_file_prefix + '.png',
##                                            fit_lorentz=False, 
##                                            output_file_prefix=common_file_prefix)
##          file_numbers=[]
##          for j, dataset in enumerate(itemlist):
##            for i, attachedset in enumerate(dataset.plot_together):
##              file_numbers.append(str(j)+'-'+str(i))
##              attachedset.export(common_file_prefix+str(j)+'-'+str(i)+'.out')
##        else:
##          plot_text=measurement_data_plotting.create_plot_script(
##                             self.active_session, 
##                             [self.measurement[self.index_mess]],
##                             common_file_prefix, 
##                             '', 
##                             self.measurement[self.index_mess].short_info,
##                             [object.short_info for object in self.measurement[self.index_mess].plot_together],
##                             errorbars, 
##                             output_file=common_file_prefix + '.png',
##                             fit_lorentz=False, 
##                             output_file_prefix=common_file_prefix)
##          file_numbers=[]
##          j=0
##          dataset=self.measurement[self.index_mess]
##          for i, attachedset in enumerate(dataset.plot_together):
##            file_numbers.append(str(j)+'-'+str(i))
##            attachedset.export(common_file_prefix+str(j)+'-'+str(i)+'.out')

##        open(common_file_prefix+'.gp', 'w').write(plot_text+'\n')
##        #----------------File selection dialog-------------------#   
   
##      elif action_name == 'ExportAll':
##        for dataset in self.measurement:
##          self.last_plot_text=self.plot(self.active_session, 
##                                        dataset.plot_together,
##                                        self.input_file_name,
##                                        dataset.short_info,
##                                        [object.short_info for object in dataset.plot_together],
##                                        errorbars,
##                                        fit_lorentz=False)
##          self.reset_statusbar()
##          self.statusbar.PushStatusText('Export plot number '+dataset.number+'... Done!', 0)

##      elif action_name == 'MultiPlotExport':
##        for plotlist in self.multiplot:
##          #++++++++++++++++File selection dialog+++++++++++++++++++#

##          file_dialog = wx.FileDialog(self, message='Export multi-plot as ...',
##                                       style=wx.FD_SAVE |wx.FD_OVERWRITE_PROMPT )
##          file_dialog.SetFilename(self.input_file_name + '_multi_'+ \
##                                  plotlist[0][0].number + '.' + self.set_file_type)


##          # create the filters in the file selection dialog
##          filter = ''
##          filter += 'Images (png/ps)|*.png;*.ps'
##          filter += '|All Files|*.*'
##          file_dialog.SetWildcard( filter )

##          # show multiplot on screen before the file is actually selected
##          self.last_plot_text=self.plot(self.active_session, 
##                                        [item[0] for item in plotlist], 
##                                        plotlist[0][1], 
##                                        plotlist[0][0].short_info, 
##                                        [item[0].short_info for item in plotlist], 
##                                        errorbars,
##                                        self.active_session.TEMP_DIR+'plot_temp.png',
##                                        fit_lorentz=False)     
##          self.label.set_width_chars(len('Multiplot title')+5)
##          self.label.set_text('Multiplot title')
##          self.set_image()

##          response = file_dialog.ShowModal()
##          if response == wx.ID_OK:
##            multi_file_name=file_dialog.get_filename()
##            self.last_plot_text=self.plot(self.active_session, 
##                                          [item[0] for item in plotlist], 
##                                          plotlist[0][1], 
##                                          plotlist[0][0].short_info, 
##                                          [item[0].short_info for item in plotlist], 
##                                          errorbars,
##                                          multi_file_name,
##                                          fit_lorentz=False)
##            # give user information in Statusbar
##            self.reset_statusbar()
##            self.statusbar.PushStatusText('Export multi-plot ' + multi_file_name + '... Done!', 0)
##          file_dialog.destroy()
##          #----------------File selection dialog-------------------#

##      else:
##        new_name=output_file_name

##        if action_name == 'ExportAs':
##          #++++++++++++++++File selection dialog+++++++++++++++++++#
##          file_dialog = wx.FileDialog(self, message='Export plot as ...',
##                                      style=wx.FD_SAVE |wx.FD_OVERWRITE_PROMPT )
##          file_dialog.SetFilename(self.input_file_name+'_'+ self.measurement[self.index_mess].number+'.'+self.set_file_type)

##          # create the filters in the file selection dialog
##          filter = ''
##          filter += 'Images (png/ps)|*.png;*.ps'
##          filter += '|All Files|*.*'
##          file_dialog.SetWildcard( filter )

##          response = file_dialog.ShowModal()
##          if response == wx.ID_OK:
##            new_name = file_dialog.GetFilename()
##          elif response == wx.ID_CANCEL:
##            file_dialog.Destroy()
##            return False

##          file_dialog.Destroy()
##        #----------------File selection dialog-------------------#


##        self.last_plot_text=self.plot(self.active_session, 
##                                      [self.measurement[self.index_mess]], 
##                                      self.input_file_name, 
##                                      self.measurement[self.index_mess].short_info,
##                                      [object.short_info for object in self.measurement[self.index_mess].plot_together],
##                                      errorbars,
##                                      new_name,
##                                      fit_lorentz=False)
##        self.reset_statusbar()
##        self.statusbar.PushStatusText('Export plot number '+self.measurement[self.index_mess].number+'... Done!',0)

  def export_plot(self,action, action_name): 
    '''
      Function for every export action. 
      Export is made as .png or .ps depending on the selected file name.
      Save is made as gnuplot file and output files.
    '''
    global errorbars
    self.active_session.picture_width='1600'
    self.active_session.picture_height='1200'
    if action_name == 'MultiPlot':
      if len(self.multiplot)>0:
        self.active_multiplot=not self.active_multiplot
      else:
        self.active_multiplot=False
      return self.replot()
    if action_name == 'SaveGPL':
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog = wx.FileDialog(self, message='Save Gnuplot(.gp) and Datafiles(.out)...',
                                        style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT )

      file_dialog.set_current_folder(self.active_folder)
      if self.active_multiplot:
        file_dialog.set_current_name(os.path.split(self.active_session.active_file_name + '_multi_')[1])
      else:
        file_dialog.set_current_name(os.path.split(self.active_session.active_file_name + '_')[1])
      # create the filters in the file selection dialog
      filter = ''
      filter += 'Gnuplot (*.gp)|*.gp'
      filter += '|All Files|*.*'
      file_dialog.SetWildcard( filter )

      # add to checkboxes if the picture should be created and if it should be .ps
#
#   Gesonderter Dialog wg. width und height
#
      ps_dialog = wx.Dialog(None, wx.ID_ANY, title='Picture as Postscript',
                            style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
      ps_sizer = wx.BoxSizer( wx.VERTICAL )
      ps_box   = wx.CheckBox(ps_dialog, wx.ID_ANY, label='Picture as Postscript')
      ps_sizer.Add( ps_box, 0, wx.EXPAND|wx.ALL, border=3 )
      pic_box  = wx.CheckBox( ps_dialog, wx.ID_ANY, label='Also create Picture' )
      ps_box.SetValue( True )
      pic_box.SetValue( True )
      ps_dialog.SetSizerAndFit( ps_sizer )
      ps_dialog.ShowModal()
      ps_box_val  = ps_box.GetValue()
      pic_box_val = pic_box.GetValue()
      ps_dialog.Destroy()
      
##       ps_box=gtk.CheckButton('Picture as Postscript', True)
##       ps_box.show()
##       pic_box=gtk.CheckButton('Also create Picture', True)
##       pic_box.set_active(True)
##       pic_box.show()
##       file_dialog.vbox.get_children()[-1].pack_start(ps_box, False)
##       file_dialog.vbox.get_children()[-1].pack_start(pic_box, False)
##       file_dialog.vbox.get_children()[-1].reorder_child(ps_box, 0)
##       file_dialog.vbox.get_children()[-1].reorder_child(pic_box, 0)
#
#   Ende Gesonderter Dialog wg. width und height
#

      response = file_dialog.ShowModal()
      if response != wx.ID_OK:
        file_dialog.Destroy()
        return None
      
      self.active_folder = file_dialog.GetDirectory()
      print 'main_window.py: export_plot self.active_folder = ',self.active_folder
      common_folder, common_file_prefix=os.path.split(file_dialog.GetFilename().rsplit('.gp', 1)[0])
      if ps_box_val:
         picture_type='.ps'
      else:
         picture_type='.png'
      
      file_dialog.Destroy()
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
            attachedset.export(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.out'))
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
          attachedset.export(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.out'))
      write_file=open(os.path.join(common_folder, common_file_prefix+'.gp'), 'w')
      write_file.write(plot_text+'\n')
      write_file.close()
      if pic_box_val:
        proc=subprocess.Popen([self.active_session.GNUPLOT_COMMAND, 
                         common_file_prefix+'.gp'], 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        stdin=subprocess.PIPE, 
                        cwd=common_folder
                        )
      #----------------File selection dialog-------------------#      
    elif action_name == 'ExportAll':
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
        if action_name == 'ExportAs':
          #++++++++++++++++File selection dialog+++++++++++++++++++#
          file_dialog=ExportFileChooserDialog(self.active_session.picture_width, 
                                            self.active_session.picture_height, 
                                            title='Export multi-plot as...')

          file_dialog.SetFilename(os.path.split(plotlist[0][1] + '_multi_'+ \
                                       plotlist[0][0].number + '.' + self.set_file_type)[1])
          file_dialog.SetDirectory(self.active_folder)
          # create the filters in the file selection dialog
          filter = ''
          filter += 'Images (png/ps)|*.png;*.ps'
          filter += '|All Files|*.*'
          file_dialog.SetWildcard(filter)
          response = file_dialog.ShowModal()
          if response == wx.ID_OK:
            self.active_folder = file_dialog.GetDirectory()
            self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
            multi_file_name = file_dialog.GetFilename()
          file_dialog.Destroy()
          if response != wx.ID_OK:
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
      if action_name == 'ExportAs':
        #++++++++++++++++File selection dialog+++++++++++++++++++#
        file_dialog = ExportFileChooserDialog(self.active_session.picture_width, 
                                            self.active_session.picture_height, 
                                            title='Export plot as...')
        file_dialog.SetFilename(os.path.split(
                      self.input_file_name+'_'+ self.measurement[self.index_mess].number+'.'+self.set_file_type)[1])
        file_dialog.SetDirectory(self.active_folder)
        filter = ''
        filter += 'Images (png/ps)|*png;*.ps'
        filter += '|All Files|*.*'
        file_dialog.SetWildcard(filter)
        # get hbox widget for the entries
        response = file_dialog.ShowModal()
        if response == wx.ID_OK:
          self.active_folder = file_dialog.GetDirectory()
          self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
          new_name = file_dialog.GetFilename()
        elif response == wx.ID_CANCEL:
          file_dialog.Destroy()
          return False
        file_dialog.Destroy()
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

##   def print_plot(self,action, action_name): 
##      '''
##        Send plot to printer, can also print every plot.
##      '''
##      global errorbars
##      print 'generic.py: Entry print_plot: action_name =  ',action_name
##      print "os.popen2(PRINT_COMMAND+self.active_session.TEMP_DIR+'plot_temp.ps') = ",PRINT_COMMAND+self.active_session.TEMP_DIR+'plot_temp.ps'
##      if action_name == 'Print':
##        term='postscript landscape enhanced colour'
##        self.last_plot_text=self.plot(self.active_session, 
##                                      [self.measurement[self.index_mess]],
##                                      self.input_file_name, 
##                                      self.measurement[self.index_mess].short_info,
##                                      [object.short_info for object in self.measurement[self.index_mess].plot_together],
##                                      errorbars, 
##                                      output_file=self.active_session.TEMP_DIR+'plot_temp.ps',
##                                      fit_lorentz=False)
##        self.reset_statusbar()
##        self.statusbar.PushStatusText('Printed with: '+PRINT_COMMAND, 0)
##        os.popen2(PRINT_COMMAND+self.active_session.TEMP_DIR+'plot_temp.ps')

##      elif action_name == 'PrintAll':
##        term='postscript landscape enhanced colour'
##        print_string=PRINT_COMMAND
##        for dataset in self.measurement: # combine all plot files in one print statement
##          self.last_plot_text=self.plot(self.active_session, 
##                                        [dataset],
##                                        self.input_file_name,
##                                        dataset.short_info,
##                                        [object.short_info for object in self.measurement[self.index_mess].plot_together],
##                                        errorbars, 
##                                        output_file=self.active_session.TEMP_DIR+'plot_temp_'+dataset.number+'.ps',
##                                        fit_lorentz=False)
##          print_string=print_string+self.active_session.TEMP_DIR+'plot_temp_'+dataset.number+'.ps '

##        self.reset_statusbar()
##        self.statusbar.PushStatusText('Printed with: '+PRINT_COMMAND, 0)
##        os.popen2(print_string)

##      # TODO: In the future, setting up propper printing dialog here:
##      #operation=gtk.PrintOperation()
##      #operation.set_job_name('Print SQUID Data Nr.'+str(self.index_mess))
##      #operation.set_n_pages(1)
##      #response=operation.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG)
##      #if response == gtk.PRINT_OPERATION_RESULT_ERROR:
##      #   error_dialog = gtk.MessageDialog(parent,
##      #                                    gtk.DIALOG_DESTROY_WITH_PARENT,
##      #                                    gtk.MESSAGE_ERROR,
##      #                                     gtk.BUTTONS_CLOSE,
##      #                                     "Error printing file:\n")
##      #   error_dialog.connect("response", lambda w,id: w.destroy())
##      #   error_dialog.show()
##      #elif response == gtk.PRINT_OPERATION_RESULT_APPLY:
##      #    settings = operation.get_print_settings()

  def print_plot(self, action, action_name):
    '''
     Dummy function for systems not supported for printing.
    '''
    message = wx.MessageDialog(self, 
                                  'Sorry, Printing is not supported!',
                                  'Information',
                                  wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP)
    message.ShowModal()
    message.Destroy()

  def print_plot_dialog( self, action, action_name ):

    print 'mainw_window.py: Entry print_plot_dialog: action_name           = ', action_name
    print 'mainw_window.py: Entry print_plot_dialog: self.active_multiplot = ', self.active_multiplot

    prt      = wx.Printer(  )
    if action_name == 'PrintAll':

      dialog = PreviewDialog(self, self.active_session.file_data,
                             title='Select Plots for Printing...',
                             buttons=('OK', 1, 'Cancel', 0),
                             style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP
                             )
      dialog.SetSize( wx.Size(800,600) )
      dialog.set_preview_parameters( self.plot, self.active_session,
                                     self.active_session.TEMP_DIR+'plot_temp.png' )
      result = dialog.run()
      print 'main_window.py: print_plot_dialog Preview result = ', result
      if result == 1:
        plot_list = dialog.get_active_objects()
        dialog.Destroy()
        prt_out = PrintDatasetDialog( plot_list, self )
        print  'nach prt_out =', prt_out
        rc      = prt.Print( self, prt_out, True )
        print 'rc = ', rc
      else:
        dialog.Destroy()

    else:                                    # else if action_name

      if self.active_multiplot:
         print 'self.active_multiplot  ist true'
         for plotlist in self.multiplot:
            itemlist = [item[0] for item in plotlist]
            if self.measurement[self.index_mess] in itemlist:
               prt_out = PrintDatasetDialog( plotlist, self,  multiplot=True )
               rc      = prt.Print( self, prt_out, True )
               print 'rc = ', rc

      else:                                  # else self.active.multi_plot
         print 'self.active_multiplot  ist false'
         measurements = [self.measurement[self.index_mess]]
         prt_out  = PrintDatasetDialog( measurements, self) 
         print 'vor prt.Print'
         rc = prt.Print( self, prt_out, True )
         print 'rc = ', rc
         last_err = prt.GetLastError()
         print 'last_err             = ', last_err
         print 'wx.PRINTER_NO_ERROR  = ',wx.PRINTER_NO_ERROR
         print 'wx.PRINTER_CANCELLED = ',wx.PRINTER_CANCELLED
         print 'wx.PRINTER_ERROR     = ',wx.PRINTER_ERROR

  #=============================
  print_plot = print_plot_dialog
  #=============================
    
  def run_action_makro(self, action):
     '''
       Execute a list of actions as a makro.
       The actions are given in a textfield, in the future
       there will be makro recording and saving functions.
     '''

     def butClicked(  event ):
         id = event.GetId()
         print 'generic.py: entry run_action_makro butClicked'
         ret = 0
         if id == idBut1:
           ret = 1
         message.EndModal( ret )

     print 'generic.py: Entry run_action_makro'
     message = wx.Dialog(self, wx.ID_ANY, title='Run Makro...', size=wx.Size(250,100),
                         style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP)

     vbox = wx.BoxSizer(wx.VERTICAL)
     message.SetSizer(vbox)

     text = wx.TextCtrl(message, wx.ID_ANY, style=wx.TE_MULTILINE)
     vbox.Add( text, 1, wx.ALL|wx.CENTER|wx.EXPAND, 3)

     butBox = wx.BoxSizer( wx.HORIZONTAL )
     butExecute = wx.Button( message, wx.ID_ANY, label='Execute Actions')       # returns 1
     butCancel  = wx.Button( message, wx.ID_ANY, label='Cancel')                # returns 0
     idBut1 = butExecute.GetId()
     butExecute.Bind(wx.EVT_BUTTON, handler=butClicked )   
     butCancel.Bind(wx.EVT_BUTTON,  handler=butClicked )
     butBox.Add( butExecute, 0, wx.ALL|wx.EXPAND, 3)
     butBox.Add( butCancel, 0, wx.ALL|wx.EXPAND, 3)

     vbox.Add( butBox,0, wx.ALL|wx.EXPAND|wx.CENTER, 3)

     response = message.ShowModal()

     if response==1:
       makro=file_actions.MakroRepr()
       makro_text = text.GetValue()
       makro.from_string(makro_text)
       self.last_makro=makro
       self.file_actions.run_makro(makro)
       self.rebuild_menus()
       self.replot()
     message.Destroy()

  def run_last_action_makro(self, action):
     '''
       Reexecute the last makro.
     '''
     print 'generic.py: Entry run_last_action_makro'
     if not self.last_makro is None:
       self.file_actions.run_makro(self.last_makro)
       self.rebuild_menus()
       self.replot()
  
  def action_history(self, action):
     '''
       A list of all previous actions, that can be executed as makro actions.
       Will be rewritten as log and makro recording functions.
     '''
     print 'generic.py: Entry action_history'


     message = wx.Dialog(self, wx.ID_ANY, title='Action History', size=wx.Size(400,500),
                         style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP)

     vbox = wx.BoxSizer(wx.VERTICAL)
     message.SetSizer(vbox)

     text = wx.TextCtrl(message, wx.ID_ANY, style=wx.TE_MULTILINE)
     text.SetValue( str(self.file_actions.store()) )
     vbox.Add( text, 1, wx.ALL|wx.CENTER|wx.EXPAND, 3)

     butOk = wx.Button( message, wx.ID_ANY, label='OK') 
     vbox.Add( butOk, 0, wx.ALL|wx.EXPAND, 3)
 
     message.ShowModal()
     message.Destroy()


  def open_ipy_console(self, action):
     '''
       In debug mode this opens a window with an IPython console,
       which has direct access to all important objects.
     '''
     import sys
     print 'generic.py: Entry open_ipy_console'


     ipython_dialog= wx.Dialog(self, wx.ID_ANY, title="IPython Console",
                                     size  = wx.Size(750,550),
                                     style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )

     vbox = wx.BoxSizer(wx.VERTICAL)
     ipython_dialog.SetSizer( vbox )

     ipview = IPython.gui.wx.ipython_view.IPShellWidget( ipython_dialog , 
              intro="""      This is an interactive IPython session with direct access to the program.
      You have the whole python functionality and can interact with the programs objects.

      Objects:
      session \tThe active session containing the data objects and settings
      plot_gui \tThe window object with all window related funcitons
      self \t\tThe IPythonView object.\n""")
     vbox.Add(ipview ,1, wx.EXPAND )

     ipython_dialog.Show(True)



     def reset(action):
       print 'generic.py: Entry reset'
       sys.stdout=sys.__stdout__
       sys.stderr=sys.__stderr__
       ipython_dialog.Destroy()

     ipython_dialog.Bind( wx.EVT_CLOSE, handler=reset )

    
     # add variables to ipython namespace
     print 'update namespace'
     ipview.IP.update_namespace({
                        'session': self.active_session, 
                        'plot_gui': self, 
                        'self': ipview, 
                        })

##   #--------------------------Menu/Toolbar Events---------------------------------#

##   #----------------------------------Event handling---------------------------------------#

##   #+++++++++++++++++++++++++++Functions for initializing etc+++++++++++++++++++++++++++++#

  def read_config_file(self):
     '''
       Read the options that have been stored in a config file in an earlier session.
       The ConfigObj python module is used to save the settings in an .ini file
       as this is an easy way to store dictionaries.
      
       @return If the import was successful.
     '''
     # create the object with association to an inifile in the user folder
     # have to test if this works under windows
     print 'Entry read_config_file'
#    $HOME/.plotting_gui/config.ini

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
      self.profiles = {'default': PlotProfile('default')}
      self.profiles['default'].save(self)
      for name in self.config_object['profiles'].items():
          self.profiles[name[0]] = PlotProfile(name[0])
          self.profiles[name[0]].read(self.config_object['profiles'])
      print 'end try'
     except KeyError:
     # create a new object if the file did not exist.
       self.config_object['profiles']={}
       self.profiles={'default': PlotProfile('default')}
       self.profiles['default'].save(self)
    
     self.read_window_config()
     print 'Return from read_config_file'
     return True


  def read_window_config(self):
     '''
      Read the window config parameters from the ConfigObj.
     '''
     print 'Entry read_window_config'
     if 'Window' in self.config_object:
       x, y=self.config_object['Window']['position']
       width, height=self.config_object['Window']['size']
       # Set the main window size to default or the last settings saved in config file
       self.SetSize(wx.Size(width, height))
       self.Move(wx.Point(x, y))
     else:
       self.SetSize(wx.Size(700, 600))
     print 'Return from read_window_config'


  def check_for_update_now(self):
     '''
       Read the wiki download area page to see, if there is a new version available.
      
       @return Newer version number or None
     '''
     import urllib
     print 'generic.py: check_for_update_now'
     # Open the wikipage
     try:
       download_page=urllib.urlopen(DOWNLOAD_PAGE_URL)
     except IOError:
       return None
     lines=download_page.readlines()
     if self.config_object['Update']['CheckBeta']:
       lines=filter(lambda line: 'Latest' in line and 'Version' in line, lines)
     else:
       lines=filter(lambda line: 'Latest stable Version' in line, lines)
     version=max(map(lambda line: line.split('Version')[-1].split(':')[0].strip(), lines))
     if version>__version__:
       return version
     else:
      return None

  def check_for_updates(self):
     '''
       Function to check for upates if this was selected and to show a dialog,
       if an updat is possible.
     '''
     print 'generic.py: Entry check_for_updates'


     if not 'Update' in self.config_object:
       dia    = MyMessageDialog( self,  title='Welcome' )
       result = dia.ShowModal()
       print 'result = ', result
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
       dia.Destroy()
     if self.config_object['Update']['Check'] and time()>self.config_object['Update']['NextCheck']:
       print "Checking for new Version."
       self.config_object['Update']['NextCheck']=time()+24.*60.*60
       new_version=self.check_for_update_now()
       print 'new_version = ', new_version
       if new_version:
         dia = wx.MessageDialog(self, 
                                'There is a new version (%s) at %s .' % (new_version, DOWNLOAD_PAGE_URL),
                                'New version',
                                wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP )
         dia.ShowModal()
         dia.Destroy()
  
##   #---------------------------Functions for initializing etc-----------------------------#

##   #++++++++++++++Functions for displaying graphs plotting and status infos+++++++++++++++#

  def set_image(self):
     '''
       Set the image created by gnuplot.
     '''
     print 'generic.py: Entry set_image'
     # in windows we have to wait for the picture to be written to disk
     print 'self.active_session.OPERATING_SYSTEM = ', self.active_session.OPERATING_SYSTEM
     if self.active_session.OPERATING_SYSTEM=='windows':
       sleep(0.1)
       for i in range(100):
         if os.path.exists(self.active_session.TEMP_DIR + 'plot_temp.png'):
           if os.path.getsize(self.active_session.TEMP_DIR + 'plot_temp.png') > 1000:
             break
           sleep(0.1)
         else:
           sleep(0.1)
     # TODO: errorhandling
     print 'self.active_session.TEMP_DIR = ',self.active_session.TEMP_DIR
     fn = self.active_session.TEMP_DIR + 'plot_temp.png'
     self.bmp = wx.Image( fn, wx.BITMAP_TYPE_PNG ).ConvertToBitmap()



  def onPaint( self, event ):
    '''
      Show the image created by Gnuplot.
    '''
    print 'generic.py: Entry onPaint'
    self.pdc = wx.PaintDC( self.image )
    self.pdc.BeginDrawing()
    self.pdc.DrawBitmap( self.bmp, 1,1, False )
    self.pdc.EndDrawing()
    print 'self.Update()'
    self.Update()




  def splot(self, session, datasets, file_name_prefix, title, names, 
             with_errorbars, output_file=gnuplot_preferences.output_file_name, fit_lorentz=False,
             sample_name=None, show_persistent=False):
     '''
       Plot via script file instead of using python gnuplot pipeing.
44      
       @return Gnuplot error messages, which have been reported
     '''
     print 'generic.py: Entry splot'
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
    print 'main_window.py: Entry plot_persistent'
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
      self.label.SetMaxLength(min(len(self.measurement[self.index_mess].sample_name)+5, 
                                                          45))
      self.label.SetValue(self.measurement[self.index_mess].sample_name)
      self.label2.SetMaxLength(min(len(self.measurement[self.index_mess].short_info)+5, 
                                                           45))
      self.label2.SetValue(self.measurement[self.index_mess].short_info)
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


  def replot(self, action=None): 
     '''
       Recreate the current plot and clear statusbar.
     '''
     global errorbars
     print 'generic.py: Entry replot'

     # change label and plot other picture
     self.show_add_info(None)
     # set log checkbox according to active measurement

     print 'self.index_mess       = ',self.index_mess
     self.logx.SetValue(self.measurement[self.index_mess].logx)
     self.logy.SetValue(self.measurement[self.index_mess].logy)
     self.logz.SetValue(self.measurement[self.index_mess].logz)
     
     self.Layout()
     WXAPPLICATION.ProcessPendingEvents()

     self.active_session.picture_width  = str(self.frame1.GetClientSize().GetWidth()-20)
     self.active_session.picture_height = str(self.frame1.GetClientSize().GetHeight()-45)

     print 'self.active_multiplot = ',self.active_multiplot
     if self.active_multiplot:
       for plotlist in self.multiplot:
         itemlist=[item[0] for item in plotlist]
         if self.measurement[self.index_mess] in itemlist:
           self.last_plot_text=self.plot(self.active_session, 
                                         [item[0] for item in plotlist], 
                                         plotlist[0][1], 
                                         plotlist[0][0].short_info, 
                                         [item[0].short_info for item in plotlist], 
                                         errorbars,
                                         self.active_session.TEMP_DIR+'plot_temp.png',
                                         fit_lorentz=False)   
           self.label.SetMaxLength(len(itemlist[0].short_info)+5)
           self.label.SetValue(itemlist[0].short_info)
     else:
       self.label.SetMaxLength(len(self.measurement[self.index_mess].sample_name)+5)
       self.label.SetValue(self.measurement[self.index_mess].sample_name)
       self.label2.SetMaxLength(len(self.measurement[self.index_mess].short_info)+5)
       self.label2.SetValue(self.measurement[self.index_mess].short_info)
       self.last_plot_text = self.plot(self.active_session, 
                                   [self.measurement[self.index_mess]],
                                   self.input_file_name, 
                                   self.measurement[self.index_mess].short_info,
                                   [object.short_info for object in self.measurement[self.index_mess].plot_together],
                                   errorbars, 
                                   output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                   fit_lorentz=False)

     if self.last_plot_text!='':
       self.statusbar.PushStatusText('Gnuplot error!')
       self.show_last_plot_params(None)
     else:
       self.set_image()
       self.SetTitle('Plotting GUI - ' + self.input_file_name + " - " + str(self.index_mess))
       self.active_plot_geometry=(self.widthf, self.heightf)
          
     self.Refresh()
     self.plot_options_buffer = self.measurement[self.index_mess].plot_options


  def reset_statusbar(self): 
     '''
       Clear the statusbar.
     '''
     self.statusbar.PopStatusText( )
     self.statusbar.PushStatusText('',0)

##   #--------------Functions for displaying graphs plotting and status infos---------------#

##   #+++++++++++++++++++++Functions responsible for menus and toolbar++++++++++++++++++++++#

##   def build_menu(self):
##     '''
##       Create XML text for the menu and toolbar creation. In addition the variable
##       actions are stored in a list. (See __create_action_group function)
##       The XML text is used for the UIManager to create the bars,for more 
##       information see the pygtk documentation for the UIManager.
      
##       @return XML string for all menus and toolbar.
##     '''
##     self.added_items=(( "xMenu", None,                             # name, stock id
##         "_x-axes", None,                    # label, accelerator
##         "xMenu",                                   # tooltip
##         None ),
##     ( "yMenu", None,                             # name, stock id
##         "_y-axes", None,                    # label, accelerator
##         "yMenu",                                   # tooltip
##         None ),
##     ( "zMenu", None,                             # name, stock id
##         "_z-axes", None,                    # label, accelerator
##         "zMenu",                                   # tooltip
##         None ),
##     ( "dyMenu", None,                             # name, stock id
##         "y-_error", None,                    # label, accelerator
##         "dyMenu",                                   # tooltip
##         None ),
##     ( "Profiles", None,                             # name, stock id
##         "_Profiles", None,                    # label, accelerator
##         "Load or save a plot profile",                                   # tooltip
##         None ),
##     ( "SaveProfile", None,                             # name, stock id
##         "Save Profile", None,                    # label, accelerator
##         "Save a plot profile",                                   # tooltip
##         self.save_profile ),
##     ( "DeleteProfile", None,                             # name, stock id
##         "Delete Profile", None,                    # label, accelerator
##         "Delete a plot profile",                                   # tooltip
##         self.delete_profile ),
##     ( "x-number", None,                             # name, stock id
##         "Point Number", None,                    # label, accelerator
##         None,                                   # tooltip
##         self.change ),
##     ( "y-number", None,                             # name, stock id
##         "Point Number", None,                    # label, accelerator
##         None,                                   # tooltip
##         self.change ),
##     ( "FilesMenu", None,                             # name, stock id
##         "Change active file", None,                    # label, accelerator
##         None,                                   # tooltip
##         self.change ),)
##   # Menus allways present
##   # TODO: Add unit transformation to GUI.
##     output='''<ui>
##     <menubar name='MenuBar'>
##       <menu action='FileMenu'>
##         <menuitem action='OpenDatafile'/>
##         <menuitem action='SaveGPL'/>
##         <separator name='static14'/>
##         <menuitem action='Export'/>
##         <menuitem action='ExportAs'/>
##         <menuitem action='ExportAll'/>
##         <menuitem action='MultiPlotExport'/>
##         <separator name='static1'/>
##         <menuitem action='Print'/>
##         <menuitem action='PrintAll'/>
##         <separator name='static2'/>
##         <menuitem action='Quit'/>
##       </menu>
##       <menu action='ActionMenu'>
##         <menuitem action='Next'/>
##         <menuitem action='Prev'/>
##         <menuitem action='First'/>
##         <menuitem action='Last'/>
##         <separator name='static3'/>
##         <menuitem action='AddMulti'/>
##         <menuitem action='AddAll'/>
##         <separator name='static4'/>
##         <menuitem action='FitData'/>
##         <separator name='static5'/>
##         <menuitem action='FilterData'/>
##         <menuitem action='TransformData'/>'''
##     if self.measurement[self.index_mess].zdata>=0:
##       output+='''
##         <placeholder name='z-actions'>
##         <menuitem action='CrossSection'/>
##         <menuitem action='SelectColor'/>
##         </placeholder>        
##         <placeholder name='y-actions'/>'''
##     else:
##       output+='''
##         <placeholder name='z-actions'/>
##         <placeholder name='y-actions'>
##         <menuitem action='CombinePoints'/>
##         </placeholder>'''
##     output+='''
##         <separator name='static6'/>
##         <menuitem action='ShowPlotparams'/>
##         <menuitem action='Makro'/>
##         <menuitem action='LastMakro'/>
##       </menu>
##       <separator name='static6'/>'''
##     # Menus for column selection created depending on input measurement
##     output+='''
##       <menu action='xMenu'>
##         <menuitem action='x-number'/>
##       '''
##     for dimension in self.measurement[self.index_mess].dimensions():
##       output+="        <menuitem action='x-"+dimension+"'/>\n"
##       self.added_items=self.added_items+(("x-"+dimension, None,dimension,None,None,self.change),)
##     output+='''
##       </menu>
##       <menu action='yMenu'>
##         <menuitem action='y-number'/>
##       '''
##     for dimension in self.measurement[self.index_mess].dimensions():
##       output+="        <menuitem action='y-"+dimension+"'/>\n"
##       self.added_items=self.added_items+(("y-"+dimension, None,dimension,None,None,self.change),)
##     if self.measurement[self.index_mess].zdata>=0:
##       output+='''
##         </menu>
##         <placeholder name='zMenu'>
##         <menu action='zMenu'>
##         '''
##       for dimension in self.measurement[self.index_mess].dimensions():
##         output+="        <menuitem action='z-"+dimension+"'/>\n"
##         self.added_items=self.added_items+(("z-"+dimension, None,dimension,None,None,self.change),)
##       output+="</menu></placeholder>\n"
##     else:
##       output+='''
##         </menu>      
##         <placeholder name='zMenu'/>'''
##     output+='''
##       <menu action='dyMenu'>
##       '''
##     for dimension in self.measurement[self.index_mess].dimensions():
##       output+="        <menuitem action='dy-"+dimension+"'/>\n"
##       self.added_items=self.added_items+(("dy-"+dimension, None,dimension,None,None,self.change),)
##     # allways present stuff and toolbar
##     output+='''     </menu>
##       <separator name='static7'/>
##       <menu action='Profiles'>
##     '''
##     for name in sorted(self.profiles.items()):
##       output+="        <menuitem action='"+\
##         name[0]+"' position='top'/>\n"
##       self.added_items+=((name[0], None,'_'+name[0],None,None,self.load_profile),)
##     output+=''' <separator name='static8'/>
##         <menuitem action='SaveProfile' position="bottom"/>
##         <menuitem action='DeleteProfile' position="bottom"/>
##       </menu>
##       <separator name='static9'/>
##       <menu action='FilesMenu'>
##       '''
##     for i, name in enumerate([object[0] for object in sorted(self.active_session.file_data.items())]):
##       output+="        <menuitem action='File-"+ str(i) +"'/>\n"
##       self.added_items+=(("File-"+ str(i), None, name, None, None, self.change_active_file),)
##     output+='''
##       </menu>
##       <separator name='static12'/>'''



##     #++++++++++++++ create session specific menu ++++++++
##     specific_menu_items=self.active_session.create_menu()
##     output+=specific_menu_items[0]
##     self.session_added_items=specific_menu_items[1]
##     #-------------- create session specific menu --------



##     output+='''
##       <separator name='static13'/>
##       <menu action='HelpMenu'>
##         <menuitem action='ShowConfigPath'/>
##         <menuitem action='About'/>
##         <menuitem action='History'/>
##         '''
##     if self.active_session.DEBUG:
##       output+='''
##         <menuitem action='OpenConsole'/>
##       '''
##     output+=    '''
##       </menu>
##     </menubar>
##     <toolbar  name='ToolBar'>
##       <toolitem action='First'/>
##       <toolitem action='Prev'/>
##       <toolitem action='Next'/>
##       <toolitem action='Last'/>
##       <separator name='static10'/>
##       <toolitem action='Apply'/>
##       <toolitem action='ExportAll'/>
##       <toolitem action='ErrorBars'/>
##       <separator name='static11'/>
##       <toolitem action='AddMulti'/>
##       <toolitem action='MultiPlot'/>
##     </toolbar>
##     </ui>'''
##     return output

##   def __create_action_group(self):
##     '''
##       Create actions for menus and toolbar.
##       Every entry creates a gtk.Action and the function returns a gtk.ActionGroup.
##       When the action is triggered it calls a function.
##       For more information see the pygtk documentation for the UIManager and ActionGroups.
      
##       @return ActionGroup for all menu entries.
##     '''
##     entries = (
##       ( "FileMenu", None, "_File" ),               # name, stock id, label
##       ( "ActionMenu", None, "A_ction" ),               # name, stock id, label
##       ( "HelpMenu", None, "_Help" ),               # name, stock id, label
##       ( "ToolBar", None, "Toolbar" ),               # name, stock id, label
##       ( "OpenDatafile", gtk.STOCK_OPEN,                    # name, stock id
##         "_Open File","<control>O",                      # label, accelerator
##         "Open a new datafile",                       # tooltip
##         self.add_file ),
##       ( "SaveGPL", gtk.STOCK_SAVE,                    # name, stock id
##         "_Save this dataset (.out)...","<control>S",                      # label, accelerator
##         "Save Gnuplot and datafile",                       # tooltip
##         self.export_plot ),
##       ( "Export", gtk.STOCK_SAVE,                    # name, stock id
##         "_Export (.png)","<control>E",                      # label, accelerator
##         "Export current Plot",                       # tooltip
##         self.export_plot ),
##       ( "ExportAs", gtk.STOCK_SAVE,                  # name, stock id
##         "E_xport As (.png/.ps)...", '<alt>E',                       # label, accelerator
##         "Export Plot under other name",                          # tooltip
##         self.export_plot ),
##       ( "Print", gtk.STOCK_PRINT,                  # name, stock id
##         "_Print...", "<control>P",                       # label, accelerator
##         None,                          # tooltip
##         self.print_plot ),
##       ( "PrintAll", gtk.STOCK_PRINT,                  # name, stock id
##         "Print All Plots...", None,                       # label, accelerator
##         None,                          # tooltip
##         self.print_plot ),
##       ( "Quit", gtk.STOCK_QUIT,                    # name, stock id
##         "_Quit", "<control>Q",                     # label, accelerator
##         "Quit",                                    # tooltip
##         self.main_quit ),
##       ( "About", None,                             # name, stock id
##         "About", None,                    # label, accelerator
##         "About",                                   # tooltip
##         self.activate_about ),
##       ( "ShowConfigPath", None,                             # name, stock id
##         "Show Config Path...", None,                    # label, accelerator
##         "Show Configfile Path",                                   # tooltip
##         self.show_config_path ),
##       ( "History", None,                             # name, stock id
##         "Action History", None,                    # label, accelerator
##         "History",                                   # tooltip
##         self.action_history ),
##       ( "Makro", None,                             # name, stock id
##         "Run Makro...", None,                    # label, accelerator
##         "Run Makro",                                   # tooltip
##         self.run_action_makro ),
##       ( "LastMakro", None,                             # name, stock id
##         "Run Last Makro", "<control>M",                    # label, accelerator
##         "Run Last Makro",                                   # tooltip
##         self.run_last_action_makro ),
##       ( "First", gtk.STOCK_GOTO_FIRST,                    # name, stock id
##         "First", "<control><shift>B",                     # label, accelerator
##         "First Plot",                                    # tooltip
##         self.iterate_through_measurements),
##       ( "Prev", gtk.STOCK_GO_BACK,                    # name, stock id
##         "Prev", "<control>B",                     # label, accelerator
##         "Previous Plot",                                    # tooltip
##         self.iterate_through_measurements),
##       ( "Next", gtk.STOCK_GO_FORWARD,                    # name, stock id
##         "_Next", "<control>N",                     # label, accelerator
##         "Next Plot",                                    # tooltip
##         self.iterate_through_measurements),
##       ( "Last", gtk.STOCK_GOTO_LAST,                    # name, stock id
##         "Last", "<control><shift>N",                     # label, accelerator
##         "Last Plot",                                    # tooltip
##         self.iterate_through_measurements),
##       ( "ShowPlotparams", None,                    # name, stock id
##         "Show plot parameters", None,                     # label, accelerator
##         "Show the gnuplot parameters used for plot.",                                    # tooltip
##         self.show_last_plot_params),
##       ( "FilterData", None,                    # name, stock id
##         "Filter the data points", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.change_data_filter),
##       ( "TransformData", None,                    # name, stock id
##         "Transform the Units/Dimensions", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.unit_transformation),
##       ( "CrossSection", None,                    # name, stock id
##         "Cross-Section", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.extract_cross_section),
##       ( "CombinePoints", None,                    # name, stock id
##         "Combine points", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.combine_data_points),
##       ( "SelectColor", None,                    # name, stock id
##         "Color Pattern...", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.change_color_pattern),
##       ( "Apply", gtk.STOCK_CONVERT,                    # name, stock id
##         "Apply", None,                     # label, accelerator
##         "Apply current plot settings to all sequences",                                    # tooltip
##         self.apply_to_all),
##       ( "ExportAll", gtk.STOCK_EXECUTE,                    # name, stock id
##         "Exp. _All", None,                     # label, accelerator
##         "Export all sequences",                                    # tooltip
##         self.export_plot),
##       ( "ErrorBars", gtk.STOCK_ADD,                    # name, stock id
##         "E.Bars", None,                     # label, accelerator
##         "Toggle errorbars",                                    # tooltip
##         self.toggle_error_bars),
##       ( "AddMulti", gtk.STOCK_JUMP_TO,                    # name, stock id
##         "_Add", '<alt>a',                     # label, accelerator
##         "Add/Remove plot to/from multi-plot list",                                    # tooltip
##         self.add_multiplot),
##       ( "AddAll", gtk.STOCK_JUMP_TO,                    # name, stock id
##         "Add all to Multiplot", None,                     # label, accelerator
##         "Add/Remove all sequences to/from multi-plot list",                                    # tooltip
##         self.add_multiplot),
##       ( "FitData", None,                    # name, stock id
##         "_Fit data...", "<control>F",                     # label, accelerator
##         "Dialog for fitting of a function to the active dataset.",                                    # tooltip
##         self.fit_dialog),
##       ( "MultiPlot", gtk.STOCK_YES,                    # name, stock id
##         "Multi", None,                     # label, accelerator
##         "Show Multi-plot",                                    # tooltip
##         self.export_plot),
##       ( "MultiPlotExport", None,                    # name, stock id
##         "Export Multi-plots", None,                     # label, accelerator
##         "Export Multi-plots",                                    # tooltip
##         self.export_plot),
##       ( "OpenConsole", None,                    # name, stock id
##         "Open IPython Console", None,                     # label, accelerator
##         None,                                    # tooltip
##         self.open_ipy_console),
##     )+self.added_items;
##     # Create the menubar and toolbar
##     action_group = gtk.ActionGroup("AppWindowActions")
##     action_group.add_actions(entries)
##     action_group.add_actions(self.session_added_items, self)
##     return action_group

  def rebuild_menus(self):
     '''
       Build new menu and toolbar structure.
     '''
     print 'generic.py: Entry rebuild_menue'
     self.update_menuBar()


##     ui_info=self.build_menu() # build structure of menu and toolbar
##     # remove old menu
##     self.UIManager.remove_ui(self.toolbar_ui_id)
##     self.UIManager.remove_action_group(self.toolbar_action_group)
##     self.toolbar_action_group=self.__create_action_group()
##     self.UIManager.insert_action_group(self.toolbar_action_group, 0) # create action groups for menu and toolbar
##     try:
##         self.toolbar_ui_id = self.UIManager.add_ui_from_string(ui_info)
##     except gobject.GError, msg:
##         print "building menus failed: %s" % msg


  def update_menuBar( self ):

    print 'generic.py: Entry update_menuBar'


#   update menu 'Change active file'
#   1. id_liste holen
#   2. ids aus dictionary action_dict loeschen
#   3. menu neu bilden 
#   4. Bindings neu bilden 
#   5. neu ids und action in action_dict eintragen

    title = 'Change'
    pos   = self.menu_bar.FindMenu( title )

    if pos != wx.NOT_FOUND:

      id_list =  [item.GetId() for item in self.menuChangeActFile.GetMenuItems()]
      print 'id_list = ', id_list
      for item in id_list:
        print 'del item ',item,', ',self.action_dict[item]
        del self.action_dict[item]

      self.menuChangeActFile = wx.Menu()
      for i, name in enumerate( [object[0] for object in sorted(self.active_session.file_data.items())] ):
          output = name
          id = self.menuChangeActFile.Append( wx.ID_ANY, output, output ).GetId()
          self.Bind(wx.EVT_MENU, self.change_active_file, id=id)
          self.action_dict[id] = 'File-'+str(i)
          print 'append item ',id,', ',id, self.action_dict[id]

      wxm = self.menu_bar.Replace(pos, self.menuChangeActFile, title )
      wxm.Destroy()

    else:
      print '!!!!!!!!!!! menubar item Change not found !!!!!!!!!!'

#   update submenu '&Axes' in menu '&View'
    title1 = '&View'
    title2 = '&Axes'
    axesFound  = self.menu_bar.FindMenuItem( title1, title2 )
    print 'found = ', axesFound

    
    if axesFound != wx.NOT_FOUND:

#     update submenu 'x-axes' in menu '&View->Axes'
      title = '&x-axes'
      pos   = self.menuAxes.FindItem( title )
      print 'pos x axes = ', pos
      if pos != wx.NOT_FOUND:

        id_list =  [item.GetId() for item in self.menuXAxes.GetMenuItems()]
        print 'id_list = ', id_list
        print 'self.action_dict = ',self.action_dict
        for item in id_list:
          print 'del item ',item
          del self.action_dict[item]
          self.menuXAxes.Delete( item)
        
        id = self.menuXAxes.Append(wx.ID_ANY, 'Point Number', 'Point Number').GetId()
        self.Bind(wx.EVT_MENU, self.change, id=id)
        self.action_dict[id] = 'x-number'
        print 'append item ',id

        for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuXAxes.Append( wx.ID_ANY, output, output ).GetId()
          self.Bind(wx.EVT_MENU, self.change, id=id)
          self.action_dict[id] = 'x-'+output
          print 'append item ',id

#        self.menuXAxes.Append( wx.ID_ANY, 'X Aenderungstest ', 'jjj' )


      else:
        print '!!!!!!!!!!! menubar item x-axes not found !!!!!!!!!!'


#     update submenu 'y-axes' in menu '&View->Axes'

      title = '&y-axes'
      pos   = self.menuAxes.FindItem( title )
      if pos != wx.NOT_FOUND:

        id_list =  [item.GetId() for item in self.menuYAxes.GetMenuItems()]
        print 'id_list = ', id_list
        for item in id_list:
          print 'del item ',item
          del self.action_dict[item]
          self.menuYAxes.Delete( item)

        id = self.menuYAxes.Append(wx.ID_ANY, 'Point Number', 'Point Number').GetId()
        self.Bind(wx.EVT_MENU, self.change, id=id)
        self.action_dict[id] = 'x-number'
        print 'append item ',id

        for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuYAxes.Append( wx.ID_ANY, output, output ).GetId()
          self.Bind(wx.EVT_MENU, self.change, id=id)
          self.action_dict[id] = 'y-'+output
          print 'append item ',id

#        self.menuYAxes.Append( wx.ID_ANY, 'Y Aenderungstest ', 'jjj' )

      else:
        print '!!!!!!!!!!! menu item y-axes not found !!!!!!!!!!'


#     update submenu 'z-axes' in menu '&View->Axes'

      title = '&z-axes'
      pos   = self.menuAxes.FindItem( title )
      if pos != wx.NOT_FOUND:

        id_list =  [item.GetId() for item in self.menuZAxes.GetMenuItems()]
        print 'id_list = ', id_list
        for item in id_list:
          print 'del item ',item
          del self.action_dict[item]
          self.menuZAxes.Delete( item)

        id = self.menuZAxes.Append(wx.ID_ANY, 'Point Number',
                           'Point Number').GetId()
        self.Bind( wx.EVT_MENU, self.change, id=id )
        self.action_dict[id] = 'z-number'
        print 'append item ',id
        if self.measurement[self.index_mess].zdata<0:
           self.menuZAxes.Enable(id, False)

        for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuZAxes.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'z-'+output
          if self.measurement[self.index_mess].zdata<0:
             self.menuZAxes.Enable(id, False)

          print 'append item ',id

#        self.menuZAxes.Append( wx.ID_ANY, 'Z Aenderungstest ', 'jjj' )


      else:
        print '!!!!!!!!!!! menubar item z-axes not found !!!!!!!!!!'


#     update submenu 'y-&error' in menu '&View->Axes'

      title = 'y-&error'
      pos   = self.menuAxes.FindItem( title )
      if pos != wx.NOT_FOUND:

        id_list =  [item.GetId() for item in self.menuYError.GetMenuItems()]
        print 'id_list = ', id_list
        for item in id_list:
          print 'del item ',item
          del self.action_dict[item]
          self.menuYError.Delete( item)

        for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuYError.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'dy-'+output
          print 'append item ',id

#        self.menuYError.Append( wx.ID_ANY, 'error Aenderungstest ', 'jjj' )

      else:
        print '!!!!!!!!!!! menubar item y-error not found !!!!!!!!!!'

#     Ende  if axesFound != wx.NOT_FOUND:

#   update Submenu 'Profiles' in 'View
    title1 = '&View'
    title2 = '&Profiles'
    found  = self.menu_bar.FindMenuItem( title1, title2 )
    print 'found = ', found

    if found != wx.NOT_FOUND:
        id_list =  [item.GetId() for item in self.menuProfile.GetMenuItems()]
        print 'id_list = ', id_list
        for item in id_list:
          print 'del item ',item
          self.menuProfile.Delete( item)

        if pos != wx.NOT_FOUND:
 
          self.menuProfile.AppendSeparator()
          id = self.menuProfile.Append(wx.ID_ANY, 'Save Profile',
                                        'Save Profile').GetId()
          self.Bind(wx.EVT_MENU, self.save_profile, id=id)

          id = self.menuProfile.Append(wx.ID_ANY, 'Delete Profile',
                                        'Delete Profile').GetId()
          self.Bind(wx.EVT_MENU, self.delete_profile, id=id)

          for name in sorted(self.profiles.items()):
            id = self.menuProfile.Insert(0, wx.ID_ANY, name[0] )

    else:
      print '!!!!!!!!!!! menub Profiles in View not found !!!!!!!!!!'

#     Ende  if found != wx.NOT_FOUND:
#   next menu item ...


    self.menu_bar.Refresh()


    
#---------------------Functions responsible for menus and toolbar----------------------#
# event handler
  def OnExit(self, event):
      print 'generic.py: Entry OnExit'
      self.main_quit()
      self.Close(True)



  def create_statusBar(self):
      print 'Entry create_statusBar'
      self.statusbar = self.CreateStatusBar()
      self.statusbar.PushStatusText('')            # wg. MAC: sonst Fehler bei reset_statusbar

  def create_menuBar(self):
      print 'Entry create_menuBar'
      self.menu_bar = wx.MenuBar()
      mb = self.menu_bar

#     File Menu
      menuFile = wx.Menu()
#                                               Dieser text erscheint in derr statusBar
      menuFile.Append(wx.ID_OPEN, '&Open file\tCtrl-O', 'Open a file') 
      self.Bind(wx.EVT_MENU, self.add_file, id=wx.ID_OPEN )


      id = menuFile.Append(wx.ID_ANY, '&Save this dataset (.out)...\tCtrl-S',
                                  'Save this dataset as *.out' ).GetId()
      self.Bind( wx.EVT_MENU, id=id,
                 handler=lambda evt, arg1='SaveGPL': 
                         self.export_plot(evt, arg1) )
      
      # submenu Snapshots
      menuSnapshot = wx.Menu()

      id = menuSnapshot.Append( wx.ID_SAVE, 'Save Snapshot\tShift+Ctrl+S', 'Save Snapshot ...').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler = lambda evt, arg1='SaveSnapshot':
                           self.save_snapshot(evt, arg1 ) )
      id = menuSnapshot.Append( wx.ID_ANY, 'Save Snapshot As', 'Save Snapshot as...').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler = lambda evt, arg1='SaveSnapshotAs':
                           self.save_snapshot(evt, arg1 ) )
      id = menuSnapshot.Append( wx.ID_ANY, 'Load Snapshot\tShift+Ctrl+O', 'Load Snapshot ...').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler = lambda evt, arg1='LoadSnapshot':
                           self.load_snapshot(evt, arg1 ) )
      id = menuSnapshot.Append( wx.ID_ANY, 'Load Snapshot From\tCtrl+O', 'Load Snapshot from...').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler = lambda evt, arg1='LoadSnapshotFrom':
                           self.load_snapshot(evt, arg1 ) )
        
      menuFile.AppendSubMenu(menuSnapshot, 'Snapshots', 'Save/Load snapshots ...')


      menuFile.AppendSeparator()
      id = menuFile.Append(wx.ID_ANY, '&Export (.png)\tCtrl+E',
                                  'Export as *.png').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler=lambda evt, arg1='Export':
                         self.export_plot(evt, arg1) )

      id = menuFile.Append(wx.ID_ANY, 'E&xport As (.png/.ps)\tShift+Ctrl+E',
                                  'Export as *.png or *.ps').GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler=lambda evt, arg1='ExportAs':
                         self.export_plot(evt, arg1) )

      id = menuFile.Append(wx.ID_ANY, 'Export All',
                                  'Export all').GetId()
      self.Bind( wx.EVT_MENU, id=id,
                 handler=lambda evt, arg1='ExportAll': 
                         self.export_plot(evt, arg1) )


      id = menuFile.Append(wx.ID_ANY, 'Export Multi-plots',
                                  'Export multi plots' ).GetId() 
      self.Bind( wx.EVT_MENU, id=id,
                 handler=lambda evt, arg1='MultiPlotExport': 
                         self.export_plot(evt, arg1) )

      menuFile.AppendSeparator()

      id = menuFile.Append(wx.ID_PRINT, '&Print...\tCtrl+P',
                                   'Print').GetId()
      self.Bind( wx.EVT_MENU, id=id,
                 handler=lambda evt, arg1='Print': 
                         self.print_plot(evt, arg1) )

      id = menuFile.Append(wx.ID_ANY, 'Print Selection ...\tShift+Ctrl+P',
                                    'Print all plots' ).GetId()
      self.Bind( wx.EVT_MENU, id=id,
                 handler=lambda evt, arg1='PrintAll': 
                         self.print_plot(evt, arg1) )

      menuFile.AppendSeparator()
      menuFile.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit this program')
      self.Bind(wx.EVT_MENU, self.OnExit,   id=wx.ID_EXIT )

      mb.Append(menuFile, '&File')


#     change active File
      self.menuChangeActFile = wx.Menu()
      for i, name in enumerate( [object[0] for object in sorted(self.active_session.file_data.items())] ):
#          output = unicode(name, 'utf-8' )
          output = name
          id = self.menuChangeActFile.Append( wx.ID_ANY, output, output ).GetId()
          self.Bind(wx.EVT_MENU, self.change_active_file, id=id)
          self.action_dict[id] = 'File-'+str(i)

      mb.Append(self.menuChangeActFile, 'Change' )


#     View Menu
      self.menuView = wx.Menu()

#     Axes Sub-Menu
      self.menuAxes = wx.Menu()

#     x-axes Sub-Menu
      self.menuXAxes = wx.Menu()
      id = self.menuXAxes.Append(wx.ID_ANY, 'Point Number',
                           'Point Number').GetId()
      self.Bind( wx.EVT_MENU, self.change, id=id )
      self.action_dict[id] = 'x-number'
#
#     Menues for column selection created depending on input measurement
      for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuXAxes.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'x-'+output

      self.menuAxes.AppendSubMenu(self.menuXAxes, '&x-axes' )
       

#     y-axes Sub-Menu
      self.menuYAxes = wx.Menu()

      id = self.menuYAxes.Append(wx.ID_ANY, 'Point Number',
                           'Point Number').GetId()
      self.Bind( wx.EVT_MENU, self.change, id=id )
      self.action_dict[id] = 'y-number'

      for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuYAxes.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'y-'+output

      self.menuAxes.AppendSubMenu(self.menuYAxes, '&y-axes' )

#     z-axis Sub-Menu
      self.menuZAxes = wx.Menu()
      id = self.menuZAxes.Append(wx.ID_ANY, 'Point Number',
                           'Point Number').GetId()
      self.Bind( wx.EVT_MENU, self.change, id=id )
      self.action_dict[id] = 'z-number'
      if self.measurement[self.index_mess].zdata<0:
         self.menuZAxes.Enable(id, False)
 
      for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuZAxes.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'z-'+output
          if self.measurement[self.index_mess].zdata<0:
             self.menuZAxes.Enable(id, False)
      self.menuAxes.AppendSubMenu(self.menuZAxes, '&z-axes')
    

#     y-error Sub-Menu
      self.menuYError = wx.Menu()

      for dimension in self.measurement[self.index_mess].dimensions():
          output = dimension
          id = self.menuYError.Append(wx.ID_ANY, output, 
                              output).GetId()
          self.Bind( wx.EVT_MENU, self.change, id=id )
          self.action_dict[id] = 'dy-'+output

      self.menuAxes.AppendSubMenu(self.menuYError, 'y-&error')

      self.menuView.AppendSubMenu(self.menuAxes, '&Axes')

 
#     profiles Sub-Menu
      self.menuProfile = wx.Menu()
      
      self.menuProfile.AppendSeparator()
      id = self.menuProfile.Append(wx.ID_ANY, 'Save Profile',
                                    'Save Profile').GetId()
      self.Bind(wx.EVT_MENU, self.save_profile, id=id)

      id = self.menuProfile.Append(wx.ID_ANY, 'Delete Profile',
                                    'Delete Profile').GetId()
      self.Bind(wx.EVT_MENU, self.delete_profile, id=id)

      for name in sorted(self.profiles.items()):
          id = self.menuProfile.Insert(0, wx.ID_ANY, name[0] )

      self.menuView.AppendSubMenu(self.menuProfile, '&Profiles' )

#     Color pattern
      id = self.menuView.Append( wx.ID_ANY, 'Color Pattern ...',
                                          'color pattern').GetId()
      self.Bind( wx.EVT_MENU, self.change_color_pattern, id=id)

      self.menuView.AppendSeparator()


      self.menuView.Append( wx.ID_FORWARD, '&Next\tCtrl+N',
                                     'Next')   
      self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=wx.ID_FORWARD )
      self.action_dict[wx.ID_FORWARD] = 'Next'

      self.menuView.Append( wx.ID_BACKWARD, 'Prev\tCtrl+B', 
                                   'Previous')
      self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=wx.ID_BACKWARD )
      self.action_dict[wx.ID_BACKWARD] = 'Prev'

      id = self.menuView.Append( wx.ID_ANY, '&First\tShift+Ctrl+B', 
                                     'First').GetId()
      self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id )
      self.action_dict[id] = 'First'

      id = self.menuView.Append( wx.ID_ANY, 'Last\tShift+Ctrl+N', 
                                   'Last').GetId()
      self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id )
      self.action_dict[id] = 'Last'


      self.menuView.AppendSeparator()


      id = self.menuView.Append(wx.ID_ADD, '&Add\tAlt+A', 
                                   'Add' ).GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler=lambda evt, arg1='AddMulti': self.add_multiplot(evt, arg1) )

      id = self.menuView.Append(wx.ID_ANY, 'Add all to Multiplot\tShift+Alt+A', 
                                   'Add all to Multiplot' ).GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler=lambda evt, arg1='AddAll': self.add_multiplot(evt, arg1) )


      id = self.menuView.Append(wx.ID_ANY, 'Clear Multiplot List', 
                                   'Clear Multiplot List ...' ).GetId()
      self.Bind( wx.EVT_MENU, id = id,
                 handler=lambda evt, arg1='ClearMultiplot': self.add_multiplot(evt, arg1) )

      self.menuView.AppendSeparator()

      self.menuView.Append(idShowPlotParameter, 'Show plot parameters',
                                   'Show plot parameters' )
      wx.EVT_MENU( self, idShowPlotParameter, self.show_last_plot_params )
      
      self.menuView.Append(idShowImportInfo, 'Show File Import Informations',
                                   'Show file import informations' )
      wx.EVT_MENU( self, idShowImportInfo, self.show_status_dialog )



      mb.Append(self.menuView, '&View')


#     Data treatment Menu
      menuDataTreatment = wx.Menu()
      

#++++++++++++++ create session specific menu ++++++++
#     z.B. SQUID Menu

      home = self
      specific_menu_items = self.active_session.create_menu( home )

      print 'specific_menu_items = ',specific_menu_items
      print 'len specific_menu_items = ',len(specific_menu_items)
      for j, item in enumerate(specific_menu_items):
          nitems = item[0].GetMenuItemCount()
          print 'nitems = ', nitems
          print 'item[0] = ', item[0]
          print 'item[1] = ', item[1]
          if nitems>=0:
            menuDataTreatment.AppendSubMenu( item[0],item[1])


#-------------- create session specific menu --------
      id = menuDataTreatment.Append(wx.ID_ANY, '&Fit data...\tCtrl+F', 
                                   'Fit data' ).GetId()
      self.Bind( wx.EVT_MENU, self.fit_dialog, id=id)

      menuDataTreatment.AppendSeparator()

      id = menuDataTreatment.Append( wx.ID_ANY, 'Filter the data points', 
                             'Filter the data points' ).GetId()
      self.Bind( wx.EVT_MENU, self.change_data_filter , id=id)
      id = menuDataTreatment.Append(wx.ID_ANY, 'Transform the Units/Dimensions',
                                   'Transform the Units/Dimensions' ).GetId()
      self.Bind( wx.EVT_MENU, self.unit_transformation, id=id )
      
      menuDataTreatment.AppendSeparator()


      if self.measurement[self.index_mess].zdata>0:
        #3D
        id = menuDataTreatment.Append( wx.ID_ANY, 'Cross-Section',
                                           'Cross section').GetId()
        self.Bind( wx.EVT_MENU, self.extract_cross_section, id=id)

      else:
        # 2D
        id = menuDataTreatment.Append(wx.ID_ANY, 'Combine points',
                                   'Combine points').GetId()
        self.Bind( wx.EVT_MENU, self.combine_data_points, id=id)

      id = menuDataTreatment.Append(wx.ID_ANY, 'Savitzky Golay Filtering',
                                    'Savitzky Golay filtering').GetId()
      self.Bind(wx.EVT_MENU, self.savitzky_golay, id = id)

      id = menuDataTreatment.Append(wx.ID_ANY, 'Show Colorcoded Points',
                                    'Show colorcoded points').GetId()
      self.Bind(wx.EVT_MENU, self.colorcode_points, id = id)

      menuDataTreatment.AppendSeparator()

      id = menuDataTreatment.Append( wx.ID_ANY, 'Remove the active Plot (no way back!)',
                                     'Remove the active plot').GetId()
      self.Bind( wx.EVT_MENU, self.remove_active_plot, id=id )

      mb.Append(menuDataTreatment, '&Data treatment')

#     Extras Menu
#     Stichwort "stock items"
      menuExtras = wx.Menu()

      id = menuExtras.Append(wx.ID_ANY, 'Run Makro...',
                                   'Run Makro' ).GetId()
      self.Bind( wx.EVT_MENU, id=id,
                              handler=self.run_action_makro )
      id = menuExtras.Append(wx.ID_ANY, 'Run Last Makro\tCtrl+M',
                                   'Run Last Makro' ).GetId()
      self.Bind( wx.EVT_MENU, id=id,
                              handler=self.run_last_action_makro )
      
      id = menuExtras.Append( wx.ID_ANY, 'Action History',
                                  'Action History').GetId()
      self.Bind( wx.EVT_MENU, id=id, handler=self.action_history)


      menuExtras.Append( idOpenConsole, 'Open IPython Console',
                                  'Open IPython Console')
      wx.EVT_MENU( self, idOpenConsole,       self.open_ipy_console )

      mb.Append(menuExtras, '&Extras')






#     help Menu
      menuHelp = wx.Menu()

      menuHelp.Append( idShowConfigPath, 'Show Config Path...',
                                  'Show Config Path')
      wx.EVT_MENU( self, idShowConfigPath,    self.show_config_path )

      menuHelp.Append( wx.ID_ABOUT, 'About',
                                    'About')
      wx.EVT_MENU( self, wx.ID_ABOUT,  self.activate_about )


      mb.Append(menuHelp, '&Help' )



#    event binding (2 Moeglichhkeiten)
#    
#      self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT )
#      self.Bind(wx.EVT_MENU, self.open_ipy_console, id=wx.ID_HIGHEST+1 )
#
#     default IDs

#     eigene window-IDs

      self.SetMenuBar( mb )
      print 'generic.py: return from create_menubar()' 
     
  def create_toolBar(self):
    print 'Entry create_toolBar'
    tb = self.CreateToolBar(style=wx.TB_TEXT)

#     Action
#      bmp = wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD )
    id = tb.AddLabelTool( wx.ID_ANY, 'First', wx.ArtProvider.GetBitmap( wx.ART_GO_BACK, wx.ART_TOOLBAR ),
                                 shortHelp='First Plot',
                                 longHelp='First Plot').GetId()
    self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id)
    self.action_dict[id] = 'First'

    id = tb.AddLabelTool( wx.ID_BACKWARD, 'Prev', wx.ArtProvider.GetBitmap( wx.ART_GO_BACK, wx.ART_TOOLBAR ),
                                 shortHelp='Previous Plot',
                                 longHelp='Previous Plot').GetId()
    self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id)
    self.action_dict[id] = 'Prev'

    id = tb.AddLabelTool( wx.ID_DOWN, 'Next', wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD, wx.ART_TOOLBAR ),
                                 shortHelp='Next Plot',
                                 longHelp='Next Plot').GetId()

    self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id)
    self.action_dict[id] = 'Next'

    id = tb.AddLabelTool( wx.ID_ANY, 'Last',  wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD, wx.ART_TOOLBAR ),
                                 shortHelp='Last Plot',
                                 longHelp='Last Plot').GetId()
    self.Bind( wx.EVT_MENU, self.iterate_through_measurements, id=id)
    self.action_dict[id] = 'Last'

    tb.AddSeparator()

    id = tb.AddLabelTool( wx.ID_APPLY, 'Apply',  wx.ArtProvider.GetBitmap( wx.ART_PASTE, wx.ART_TOOLBAR ),
                                 shortHelp='Apply current plot settings to all sequences',
                                 longHelp='Apply current plot settings to all sequences').GetId()
    self.Bind( wx.EVT_MENU, self.apply_to_all, id = id )

    id = tb.AddLabelTool( wx.ID_ANY, 'Exp. All',  wx.ArtProvider.GetBitmap( wx.ART_FILE_SAVE, wx.ART_TOOLBAR ),
                                 shortHelp='Export all sequences',
                                 longHelp='Export all sequences').GetId()
    self.Bind( wx.EVT_MENU, id=id,
               handler=lambda evt, arg1='ExportAll': self.export_plot(evt, arg1) )


    id = tb.AddLabelTool( wx.ID_ANY, 'E.Bars',  wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK, wx.ART_TOOLBAR ),
                                 shortHelp='Toggle error bars',
                                 longHelp='Toggle error bars').GetId()  
    self.Bind( wx.EVT_MENU, id = id, handler=self.toggle_error_bars)

    tb.AddSeparator()

    id = tb.AddLabelTool( wx.ID_ADD, 'Add',  wx.ArtProvider.GetBitmap( wx.ART_ADD_BOOKMARK, wx.ART_TOOLBAR ),
                                 shortHelp='Add/Remove plot to/from multi-plot list',
                                 longHelp='Add/Remove plot to/from multi-plot list').GetId()
    self.Bind( wx.EVT_MENU, id = id,
               handler=lambda evt, arg1='AddMulti': self.add_multiplot(evt, arg1) )

    id = tb.AddLabelTool( wx.ID_ANY, 'Multi',  wx.ArtProvider.GetBitmap( wx.ART_HELP_PAGE, wx.ART_TOOLBAR ),
                                 shortHelp='Show multi-plot',
                                 longHelp='Show multi-plot').GetId()
    self.Bind( wx.EVT_MENU, id = id,
               handler=lambda evt, arg1='MultiPlot': self.export_plot(evt, arg1) )

    tb.AddSeparator()

    id = tb.AddLabelTool( wx.ID_ANY, 'Save Snapshot', wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR),
                          shortHelp='save snapshot',
                          longHelp='save snapshot..').GetId()
    self.Bind( wx.EVT_MENU, id = id,
               handler=lambda evt, arg1='SaveSnapshot': self.save_snapshot(evt, arg1) )
    
    id = tb.AddLabelTool( wx.ID_ANY, 'Load Snapshot', wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR),
                          shortHelp='load snapshot',
                          longHelp='load snapshot..').GetId()
    self.Bind( wx.EVT_MENU, id = id,
               handler=lambda evt, arg1='LoadSnapshot': self.load_snapshot(evt, arg1) )

    tb.AddSeparator()
    
    id = tb.AddLabelTool( wx.ID_ANY, 'Open Persistent\nGnuplot Window', wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR),
                          shortHelp='',
                          longHelp='').GetId()
    self.Bind( wx.EVT_MENU, id = id,  handler=self.plot_persistent )

    tb.Realize()



#------------------------- ApplicationMainWindow Class ----------------------------------#
