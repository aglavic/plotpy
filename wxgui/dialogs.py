# -*- encoding: utf-8 -*-
'''
  Dialogs derived from wxWidgets.
''' 

#TODO: !!!!!!!!!! Needs to be transfered to wx !!!!!!!!!

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import wx
import sys, os
import array

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Unusable"


def connect_stdout_dialog():
  '''
    Replace sys.stdout with a dialog window.
    
    @return The dialog window.
  '''
  status_dialog = StatusDialog('Import Status', buttons=('Close', 0))
  status_dialog.Bind( event=wx.EVT_CLOSE, handler=lambda *ignore: status_dialog.Hide())
  status_dialog.SetSize( wx.Size(800, 600) )
  status_dialog.Show()
  status_dialog.fileno=lambda : 1
  status_dialog.flush=lambda : True
  sys.stdout = status_dialog
  return status_dialog


#++++++++++++++++++++++++ StatusDialog to show an updated text +++++++++++++++++++++++++

class StatusDialog(wx.Dialog):
  '''
    A Dialog to show a changing text with scrollbar.
  '''
  

  def __init__(self, title=None, parent=None, flags=0, buttons= (), initial_text=''):
    '''
      Class constructor. Creates a Dialog window with scrollable TextView.
    '''
    if len(buttons)%2 == 1:
      print 'StatusDialog.__init__: illegal parameter buttons =', buttons
      print 'len(buttons) % 2 ist nicht 0'
      return
 
    wx.Dialog.__init__(self, parent=parent, title='StatusDialog')

    self.vbox   = wx.BoxSizer( wx.VERTICAL )
    self.SetSizer( self.vbox )
    self.textview = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE )
    self.textview.SetValue( initial_text )
    self.vbox.Add( self.textview, 0, wx.EXPAND|wx.ALL, 3)

    ll = len(buttons)
    if ll>0:
       butBox      = wx.StaticBox( self, wx.ID_ANY, style=wx.BORDER_DOUBLE|wx.BORDER_RAISED )
       butBoxSizer = wx.StaticBoxSizer( butBox, wx.HORIZONTAL )
       but = []
       for i in range(len(buttons)/2 ):
           print 'create but i = ', i
           but.append(wx.Button( self, wx.ID_ANY, label=buttons[2*i]) )
           but[i].Bind(event= wx.EVT_BUTTON, handler=lambda  evt, arg1=buttons[2*i+1]:  self.EndModal(arg1) )
           butBoxSizer.Add(but[i],     0, wx.EXPAND|wx.ALL, border=3)
       self.vbox.Add( butBoxSizer, 0, wx.EXPAND|wx.ALL, border=5 )

    self.Bind( event=wx.EVT_CLOSE, handler=lambda *ign:self.EndModal(22) )


  def write(self, text):
    '''
      Append a string to the buffer and scroll at the end, if it was visible before.
    '''
    if type(text) is not unicode:
      utext=unicode(text, errors='ignore')
    else:
      utext=text

    print 'self.textview append text ',utext
    self.textview.AppendText(utext)

#    while gtk.events_pending():
#      gtk.main_iteration()

#------------------------ StatusDialog to show an updated text -------------------------


#++++++++++++++++++++++++++ PreviewDialog to select one plot +++++++++++++++++++++++++++

class PreviewDialog(wx.Dialog):
  '''
    A dialog to show a list of plot previews to give the user the possibility to
    select one or more plots.
  '''
  main_table=None
    
  def __init__(self, parent, data_dict, show_previews=False, buttons=('OK', 1, 'Cancel', 0), single_selection=True,
                     title='Dialog', **opts):
    '''
      Constructor setting up a wx.Dialog with a table of preview items.
    '''

    print 'dialogs.py: __init__: data_dict        = ', data_dict
    print 'dialogs.py: __init__: show_previews    = ', show_previews
    print 'dialogs.py: __init__: buttons          = ', buttons
    print 'dialogs.py: __init__: len(buttons)%2   = ', len(buttons)%2
    print 'dialogs.py: __init__: len(buttons)/2   = ', len(buttons)/2
    print 'dialogs.py: __init__: single_selection = ', single_selection
    print 'dialogs.py: __init__: title            = ', title
    print 'dialogs.py: __init__: opts             = ', opts
    if len(buttons)%2 == 1:
      print 'PreviewDialog.__init__: illegal parameter buttons =', buttons
      print 'len(buttons) % 2 ist nicht 0'
      return

    wx.Dialog.__init__(self, parent, title=title, **opts)


    self.single_selection = single_selection
    self.data_dict        = data_dict
    # List to store unset previews to be created after the dialog is shown
    self.unset_previews = []
    # List of image objects to be able to show or hide them
    self.images         = []
    self.images_dc_win  = []
    # Will store the checkboxes corresponding to one plot
    self.check_boxes    = {}
    self.show_previews  = show_previews


    self.vbox   = wx.BoxSizer( wx.VERTICAL )
    self.SetSizer( self.vbox )

    butBox      = wx.StaticBox( self, wx.ID_ANY, style=wx.BORDER_DOUBLE|wx.BORDER_RAISED )
    butBoxSizer = wx.StaticBoxSizer( butBox, wx.HORIZONTAL )
    

    self.vbox.Add( self.get_scrolled_main_table() )

    for key, datalist in sorted(data_dict.items()):
      print 'key = ', key
      print 'datalist = ', datalist
      self.add_line(key, datalist)
      

    hbox = wx.BoxSizer( wx.HORIZONTAL )
    toggle_previews = wx.CheckBox(self, wx.ID_ANY, label='Show Previews')
    hbox.Add( toggle_previews )
    self.vbox.Add(hbox)
    
    if show_previews:
      toggle_previews.SetValue(True)
      
    toggle_previews.Bind( event=wx.EVT_CHECKBOX, handler=self.toggle_previews)

    but = []
    for i in range(len(buttons)/2 ):
     print 'create but i = ', i
     but.append(wx.Button( self, wx.ID_ANY, label=buttons[2*i]) )
     but[i].Bind(event= wx.EVT_BUTTON, handler=lambda evt, arg1=buttons[2*i+1]: self.EndModal( arg1) )
     butBoxSizer.Add(but[i],     0, wx.EXPAND|wx.ALL, border=3)
      
    self.vbox.Add( butBoxSizer, 0, wx.EXPAND|wx.ALL, border=5 )
 
    self.Bind( event=wx.EVT_CLOSE, handler = lambda evt: self.EndModal( wx.ID_CANCEL ) )
    
    
 
  def run(self):
    '''
      Called to show the dialog and create unset previews.
    '''
    def stop_preview_creation( evt):
      # Stop the preview creation on a response signal
      self.stop_preview = True
      self.response_id  = evt.GetId()
      print 'stop_preview_creation id = ', self.response_id
      
      
    self.stop_preview = False
#    self.Bind(event=wx.EVT_CLOSE,  handler=lambda evt, func=stop_preview_creation: func(evt) )

###    while gtk.events_pending():
##      gtk.main_iteration(False)
      
    for image, dataset in self.unset_previews:
      if self.stop_preview:
        return self.response_id
      self.create_preview(image, dataset)
      print 'dialogs.py in run() nach self.create_preview: dataset.preview      = ',dataset.preview

    result = self.ShowModal( )
    print 'result       = ', result
    return result


  def get_scrolled_main_table(self):
    '''
      Create the Table which holds all previews with scrollbars.
      
      @return The Table widget
    '''
    print 'Entry get_scrolled_main_table'
    if self.main_table:
      print 'main_table ist vorhanden'
      return self.main_table

    self.last_line = 0

    self.main_table = wx.GridBagSizer()

    self.sw              = wx.ScrolledWindow( self, wx.ID_ANY )
    self.sw.SetSizer( self.main_table )
#    self.sw.SetSizerAndFit( self.main_table )
#    self.sw.SetScrollRate(10, 10 )
    print 'return from get_scrolled_main_table: sw = ', self.sw
    print 'return from get_scrolled_main_table: self.main_table = ', self.main_table

    return self.sw 
  
  def add_line(self, key, datalist):
    '''
      Add one line of previews to the main table.
      
      @param key The name of the file the previews in this line belong to.
      @param datalist List of MeasurementData object.
    '''
    print 'entry add_line: key = ',key
    

    def paint_dc( event, datalist):
       print 'dialogs.py: Entry paint_dc: show_previews = ',self.show_previews
       if not self.show_previews:
         return
       print 'len datalist  = ',len(datalist)
       for i, dataset in enumerate( datalist ):
           win = self.images_dc_win[i]
           dc = wx.ClientDC( win )
           bmp = self.get_preview( dataset )
           dc.DrawBitmap( bmp, 0, 0 )
       
     

    if key.endswith('|raw_data'):
      return

    main_table = self.main_table
    line       = self.last_line
    sw         = self.sw
    ll = len(datalist)
    if not self.single_selection:
      select_all  = wx.Button(self.sw, wx.ID_ANY, label='Select All')
      select_none = wx.Button(self.sw, wx.ID_ANY, label='Unselect')
      main_table.Add(select_all,  wx.GBPosition(ll+1,0) ) 
      main_table.Add(select_none, wx.GBPosition(ll+1,1) ) 
       
    label = wx.StaticText(self.sw, wx.ID_ANY, label=os.path.split(key)[1] )

    main_table.Add(label,       wx.GBPosition(line,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 ) 

    self.last_line += 2
    check_boxes     = []
    for i, dataset in enumerate(datalist):
      print' i, dataset = ', i,',',dataset
      if self.single_selection:
        if len(self.check_boxes.values())>0:
          group = self.check_boxes.values()[0][0]
        elif i>0:
          group = check_boxes[0]
        else:
          group = None

        if i==0:
         check_box = wx.RadioButton(self.sw, wx.ID_ANY, label="[%i] %s" % (i, dataset.short_info[:10]), style=wx.RB_GROUP )
         check_box.SetValue( True )
        else:
         check_box = wx.RadioButton(self.sw, wx.ID_ANY, label="[%i] %s" % (i, dataset.short_info[:10]) )

      else:
        check_box = wx.CheckBox(self.sw, wx.ID_ANY, label="[%i] %s" % (i, dataset.short_info[:10]) )
 
      check_boxes.append(check_box)
      main_table.Add(check_box, wx.GBPosition(line+1,i+1) , flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3) 


      image = self.get_preview( dataset )
      self.images.append(image)


      self.dc_win = wx.Window(self.sw, size=(100,50) )
        
      main_table.Add( self.dc_win, wx.GBPosition(line,i+1), flag=wx.CENTER|wx.ALL|wx.EXPAND, border=3)
      self.images_dc_win.append(self.dc_win)
      self.dc_win.Bind( event=wx.EVT_ERASE_BACKGROUND, handler=lambda evt, func=paint_dc, arg1 = datalist: func(evt, datalist) )

    self.check_boxes[key] = check_boxes
    
    if not self.single_selection:
      select_all.Bind( event=wx.EVT_BUTTON, handler=lambda evt, func=self.toggle_entries, arg1=check_boxes, arg2=True:
                       func( evt, arg1, arg2) )
      select_none.Bind( event=wx.EVT_BUTTON, handler=lambda evt, func=self.toggle_entries, arg1=check_boxes, arg2=False:
                       func( evt, arg1, arg2) )

   
  def test(self, widget, action, check_box):
    check_box.SetValue(not check_box.IsChecked())

  def toggle_entries(self, event, check_boxes, set_value):
    '''
      Toggle all entries in check_boxes to set_value.
    '''
    print 'dialogs.py: Entry toggle_entries set_value   = ',set_value
    print 'dialogs.py: Entry toggle_entries check_boxes = ',check_boxes
    for check_box in check_boxes:
      check_box.SetValue(set_value)
  
  def get_preview(self, dataset):
    '''
      Create an image as preview, if the dataset has no preview, add it to the
      list of unset previews.
    '''
    print 'dialogs.py: Entry get_preview dataset = ', dataset
    image = wx.EmptyBitmap(50,50)
    if getattr(dataset, 'preview', False):
      print 'getattr returns true'
      image = dataset.preview 
    else:
      print 'getattr returns false'
      self.unset_previews.append( (image, dataset))
    return image
  
  def set_preview_parameters(self, plot_function, session, temp_file):
    '''
      Connect objects needed for preview creation.
    '''
    self.preview_plot      = plot_function
    self.preview_session   = session
    self.preview_temp_file = temp_file
    print 'dialogs.py: preview_plot       = ', self.preview_plot
    print 'dialogs.py: preview_session    = ', self.preview_session
    print 'dialogs.py: preview_temp_file  = ', self.preview_temp_file
  
  def create_preview(self, image, dataset):
    '''
      Create an preview of the dataset and render it onto image.
    '''
    print 'dialogs.py: Entry create_preview: image        = ', image
    print 'dialogs.py: Entry create_preview: dataset      = ', dataset
    if getattr(self, 'preview_plot', False):
      self.preview_plot(self.preview_session,
                                  [dataset],
                                  'preview',
                                  dataset.short_info,
                                  [object.short_info for object in dataset.plot_together],
                                  main_window.errorbars, 
                                  output_file=self.preview_temp_file,
                                  fit_lorentz=False)
      print 'create bitmap from file ',self.preview_temp_file
      img =  wx.Image(self.preview_temp_file)
      img.Rescale( 100,50, wx.IMAGE_QUALITY_HIGH)
      bmp =  img.ConvertToBitmap()
      dataset.preview = bmp.GetSubBitmap( wx.Rect(0,0, bmp.GetWidth(), bmp.GetHeight()) )
      print 'dataset.preview = ', dataset.preview
      print 'bmp             = ', bmp
      print 'getattr(dataset, preview ... = ', getattr(dataset, 'preview', False )
      print 'size dataset.preview = ', dataset.preview.GetSize()
      return 
      
##    while gtk.events_pending():
##      gtk.main_iteration(False)
  
  def get_active_keys(self):
    '''
      Return the keys and indices of the activeded check_box widgets.
    '''
    output={}
    for key, checkbox_list in self.check_boxes.items():
      output[key]=[]
      for i, check_box in enumerate(checkbox_list):
        if check_box.GetValue():
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
      print 'set show_previews false'
      for image in self.images_dc_win:
        image.Hide()
    else:
      self.show_previews=True
      print 'set show_previews true'
      for image in self.images_dc_win:
        image.Show()
        image.Refresh()
      
      
  
#-------------------------- PreviewDialog to select one plot ---------------------------


#+++++++++++++++ SimpleEntryDialog to get a list of values from the user +++++++++++++++

class SimpleEntryDialog(wx.Dialog):
  '''
    A dialog with user defined entries. The values of the entries are converted to a
    given type and then returned when run() is called.
  '''
  
  def __init__(self, parent, title, entries, **opts):
    '''
      Class constructor. Creates the dialog and label + entries from the list of entries supplied above.
      
      @param entries a list of tuples containing the values name, start value and function for type conversion.
    '''
    # Initialize this dialog
    wx.Dialog.__init__(self, parent, size=(300,200), title=title,
                             style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP)

    self.entries     = {}
    self.values      = {}
    self.conversions = {}
    
    self.vbox        = wx.BoxSizer( wx.VERTICAL )
    self.table       = wx.GridBagSizer()
    self._init_entries(entries)
    self.vbox.Add( self.table, 0, wx.EXPAND|wx.ALL, border=5)
    self.butbox      = self.CreateSeparatedButtonSizer( wx.OK|wx.CANCEL )
    self.vbox.Add( self.butbox, 0, wx.EXPAND|wx.ALL, border=5 )
    self.SetSizerAndFit( self.vbox )


  def _init_entries(self, entries):
    '''
      Append labels and entries to the main table and the objects dictionaries and show them. 
    '''
    for i, entry_list in enumerate(entries):
      if len(entry_list)<3 and len(entry_list)>4:
        raise ValueError, "All entries have to be tuples with 3 or 4 items"
      key   = entry_list[0]
      label = wx.StaticText(self, id = wx.ID_ANY, label = key + ': ', style=wx.ALIGN_CENTRE)

      entry = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
      entry.SetValue(str(entry_list[1]))

      entry.Bind(  event=wx.EVT_TEXT_ENTER,  handler=lambda *ignore: self.EndModal(wx.ID_OK))

      self.entries[key]     = entry
      self.values[key]      = entry_list[1]
      self.conversions[key] = entry_list[2]
      self.table.Add( label, wx.GBPosition(i,0), flag=wx.EXPAND|wx.ALL, border=3 )
      self.table.Add( entry, wx.GBPosition(i,1), flag=wx.EXPAND|wx.ALL, border=3 )

      if len(entry_list)==4:
        self.table.Add(entry_list[3](self),  wx.GBPosition(i,2), flag=wx.EXPAND|wx.ALL, border=3 )

  
  def run(self):
    '''
      Show the dialog and wait for input. Return the result as Dictionary 
      and a boolen definig if the Dialog was closed or OK was pressed.
    '''
    result     = self.ShowModal()
    
    self.collect_entries()

    return self.values, result==wx.ID_OK
  
  def collect_entries(self):
    '''
      Get values from all entry widgets and convert them. If conversion fails
      dont change the values.
    '''
    for key, entry in self.entries.items():
      text=entry.GetValue()
      try:
        value=self.conversions[key](text)
        self.values[key]=value
      except ValueError:
        pass

#--------------- SimpleEntryDialog to get a list of values from the user ---------------





#+++++++++++++++++++ FileChooserDialog with entries for width and height ++++++++++++++++

class ExportFileChooserDialog(wx.FileDialog):
  '''
    A file chooser dialog with two entries for with and height of an export image.
  '''
  
  def __init__(self, width, height, title='xxx', parent=None, *args, **opts):
    '''
      Class constructor which adds two entries for with and height.
    '''
    print 'dialogs.py: Entry ExportFileChooserDialog __init __: width = ', width,', height =',height
    
    self.width=width
    self.height=height
#
#   Gesonderter Dialog wg. width und height
#
    wh_dialog = wx.Dialog( None, wx.ID_ANY, title='width/height dialog', size = (200,100),
                           style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
    table = wx.GridBagSizer()
    label = wx.StaticText( wh_dialog, label='width' )
    table.Add( label, wx.GBPosition(0,0), flag = wx.CENTER|wx.ALL, border=3)
    label = wx.StaticText( wh_dialog, label='height' )
    table.Add( label, wx.GBPosition(0,1), flag = wx.CENTER|wx.ALL, border=3)
    width_ent  = wx.TextCtrl(wh_dialog, wx.ID_ANY)
    height_ent = wx.TextCtrl(wh_dialog, wx.ID_ANY)
    width_ent.SetMaxLength(4)
    height_ent.SetMaxLength(4)
    width_ent.SetValue( width )
    height_ent.SetValue( height )
    table.Add(width_ent,  wx.GBPosition(1,0), flag = wx.CENTER|wx.ALL, border=3)
    table.Add(height_ent, wx.GBPosition(1,1), flag = wx.CENTER|wx.ALL, border=3)
    wh_dialog.SetSizerAndFit( table )
    
    wh_dialog.ShowModal()
    wh_dialog.Destroy()

    self.height_entry = height_ent
    self.width_entry  = width_ent
#
#   Ende Gesonderter Dialog wg. width und height
#
    wx.FileDialog.__init__(self, parent, message=title, style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR )
    
    
  def get_with_height(self):
    '''
      Return width and height of the entries.
    '''
    width=self.width
    height=self.height
    try:
      int_width=int(self.width_entry.GetValue())
      width=str(int_width)
    except ValueError:
      pass
    try:
      int_height=int(self.height_entry.GetValue())
      height=str(int_height)
    except ValueError:
      pass
    return width, height

#------------------- FileChooserDialog with entries for width and height ----------------

#+++ Printing Dialog which imports and creates PNG files for the datasets and sends it to a printer +++

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
                self.main_window.errorbars, 
                output_file=session.TEMP_DIR+'plot_temp.png',
                fit_lorentz=False)
    
  def preview(self, operation, preview, context, parent):
    '''
      Create a preview of the plots to be printed.
    '''
    pass

#--- Printing Dialog which imports and creates PNG files for the datasets and sends it to a printer ---


if __name__ == '__main__':
  app = wx.App(False)
  
  fd = ExportFileChooserDialog(  '200', '100', title='export file chooser dialog')
  fd.ShowModal()

  sd = StatusDialog(title='test status dialog', buttons=('close',0), initial_text='hallo' ) 
  sd.write('jjjjjj\nkkkkkkkk')
  rc = sd.ShowModal()
  print 'rc status dialog = ', rc
  
  par, res = SimpleEntryDialog(None, 'test SimpleEntryDialog', ( ('Window Size',5, int,wx.TextCtrl),
                                                            ('Polynomial', 2, int),
                                                            ('Max der', 1, int) )  ).run()
  print 'res = ', res
  if res == 1:
    print 'res ist 1'
    
  print 'par = ', par

  app.MainLoop()
  
if __name__ != '__main__':
 import main_window
