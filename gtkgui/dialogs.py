# -*- encoding: utf-8 -*-
'''
  Dialogs derived from GTK.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
import cairo
import sys, os
from config import gnuplot_preferences

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7rc2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


def connect_stdout_dialog():
  '''
    Replace sys.stdout with a dialog window.
    
    @return The dialog window.
  '''
  status_dialog=StatusDialog('Import Status', buttons=('Close', 0))
  status_dialog.connect('response', lambda *ignore: status_dialog.hide())
  status_dialog.set_default_size(800, 600)
  status_dialog.show_all()
  status_dialog.move(0, 0)
  status_dialog.fileno=lambda : 1
  status_dialog.flush=lambda : True
  sys.stdout=status_dialog
  return status_dialog

#++++++++++++++++++++++++ StatusDialog to show an updated text +++++++++++++++++++++++++
 
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
    # scroll back if text containes backspace characters
    if u'\b' in utext:
      back_split_utext=utext.split(u'\b')
      for utext in back_split_utext[:-1]:
        self.buffer.insert(self.end_iter, utext)
        # remove one character
        iter1=self.end_iter
        iter2=iter1.copy()
        iter2.backward_char()
        self.buffer.delete(iter2, iter1)
      utext=back_split_utext[-1]
    self.buffer.insert(self.end_iter, utext)
    if end_visible:
      self.textview.scroll_to_mark(self.end_mark, 0.)
    while gtk.events_pending():
      gtk.main_iteration()
  
#------------------------ StatusDialog to show an updated text -------------------------


#++++++++++++++++++++++++++ PreviewDialog to select one plot +++++++++++++++++++++++++++

class PreviewDialog(gtk.Dialog):
  '''
    A dialog to show a list of plot previews to give the user the possibility to
    select one or more plots.
  '''
  main_table=None
  
  def __init__(self, data_dict, show_previews=False, single_selection=False, **opts):
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
    # if true, only one plot can be selected.
    self.single_selection=single_selection
    self.show_previews=gtk.CheckButton('Show Previews', use_underline=False)
    if show_previews:
      self.show_previews.set_active(True)
    self.vbox.add(self.get_scrolled_main_table())
    for key, datalist in sorted(data_dict.items()):
      self.add_line(key, datalist)
    self.show_previews.connect('toggled', self.toggle_previews)
    bottom_table=gtk.Table(3, 1, False)
    bottom_table.attach(self.show_previews, # X direction #   # Y direction
                                            0, 1,                  0, 1,  0,0,  0,0)
    select_all_button=gtk.Button('Select Everything')
    bottom_table.attach(select_all_button, # X direction #   # Y direction
                                            1, 2,                  0, 1,  0,0,  0,0)
    select_all_button.connect('button_press_event', self.select_all)
    select_none_button=gtk.Button('Select Nothing')
    bottom_table.attach(select_none_button, # X direction #   # Y direction
                                            2, 3,                  0, 1,  0,0,  0,0)
    select_none_button.connect('button_press_event', self.select_none)
    bottom_table.show_all()
    self.vbox.pack_end(bottom_table, False)
  
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
    while len(self.unset_previews)>0:
      if self.stop_preview:
        return self.response_id
      self.create_preview()
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
    label=gtk.Label(os.path.split(key)[1])
    table=gtk.Table(len(datalist), 2, False)
    align=gtk.Alignment(0, 0.5, 0, 0)
    align.add(table)
    align.show()
    if not self.single_selection:
      select_all=gtk.Button('Select All')
      select_none=gtk.Button('Unselect')
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
    show_previews=self.show_previews.get_active()
    for i, dataset in enumerate(datalist):
      if self.single_selection:
        if len(self.check_boxes.values())>0:
          group=self.check_boxes.values()[0][0]
        elif i>0:
          group=check_boxes[0]
        else:
          group=None
        check_box=gtk.RadioButton(group=group, label="[%i] %s" % (i, dataset.short_info[:10]), use_underline=True)
      else:
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
      if show_previews:
        image.show()
      eventbox=gtk.EventBox()
      eventbox.add(image)
      eventbox.show()
      eventbox.add_events(gtk.gdk.BUTTON_PRESS_MASK)
      eventbox.connect("button_press_event", self.toggle_check_box, check_box)
      table.attach(eventbox, 
            # X direction #          # Y direction
            i, i+1,                   0, 1,
            0,                       gtk.FILL,
            0,                         0)      
    self.check_boxes[key]=check_boxes
    if not self.single_selection:
      select_all.connect('clicked', self.toggle_entries, check_boxes, True)
      select_none.connect('clicked', self.toggle_entries, check_boxes, False)
  
  def toggle_check_box(self, widget, action, check_box):
    if type(check_box) is gtk.CheckButton:
      check_box.set_active(not check_box.get_active())
    else:
      check_box.set_active(True)

  def toggle_entries(self, widget, check_boxes, set_value):
    '''
      Toggle all entreis in check_boxes to set_value.
    '''
    for check_box in check_boxes:
      check_box.set_active(set_value)
  
  def select_none(self, widget, action):
    '''
      Unselect all entries of all files.
    '''
    for boxes in self.check_boxes.values():
      for box in boxes:
        box.set_active(False)
  
  def select_all(self, widget, action):
    '''
      Select all entries of all files.
    '''
    for boxes in self.check_boxes.values():
      for box in boxes:
        box.set_active(True)
  
  def get_preview(self, dataset):
    '''
      Create an image as preview, if the dataset has no preview, add it to the
      list of unset previews.
    '''
    image=gtk.Image()
    if getattr(dataset, 'preview', False):
      image.set_from_pixbuf(dataset.preview)
    else:
      self.unset_previews.append( (image, dataset) )
    return image
  
  def set_preview_parameters(self, plot_function, session, temp_file):
    '''
      Connect objects needed for preview creation.
    '''
    self.preview_plot=plot_function
    self.preview_session=session
    self.preview_temp_file=temp_file
  
  def create_preview(self):
    '''
      Create an preview of the dataset and render it onto image.
    '''
    if getattr(self, 'preview_plot', False) and self.show_previews.get_active():
      image, dataset=self.unset_previews.pop(0)
      self.preview_plot(self.preview_session,
                                  [dataset],
                                  'preview',
                                  dataset.short_info,
                                  [object.short_info for object in dataset.plot_together],
                                  main_window.errorbars, 
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
      Return a list of data object for which the checkbox is set.
    '''
    active_dict=self.get_active_keys()
    data_dict=self.data_dict
    output=[]
    for key, active_list in sorted(active_dict.items()):
      for i in active_list:
        output.append(data_dict[key][i])
    return output
  
  def get_active_objects_with_key(self):
    '''
      Return a list of data object for which the checkbox is set.
    '''
    active_dict=self.get_active_keys()
    data_dict=self.data_dict
    output=[]
    for key, active_list in sorted(active_dict.items()):
      for i in active_list:
        output.append((key, data_dict[key][i]))
    return output
  
  def toggle_previews(self, widget):
    '''
      Show or hide all previews.
    '''
    if self.show_previews.get_active():
      for image in self.images:
        image.show()
    else:
      for image in self.images:
        image.hide()
      
#-------------------------- PreviewDialog to select one plot ---------------------------

#+++++++++++++++ SimpleEntryDialog to get a list of values from the user +++++++++++++++

class SimpleEntryDialog(gtk.Dialog):
  '''
    A dialog with user defined entries. The values of the entries are converted to a
    given type and then returned when run() is called.
  '''
  
  def __init__(self, title, entries, **opts):
    '''
      Class constructor. Creates the dialog and label + entries from the list of entries supplied above.
      
      @param entries a list of tuples containing the values name, start value and function for type conversion.
    '''
    # Initialize this dialog
    gtk.Dialog.__init__(self, title=title, buttons=('OK', 1, 'Cancel', 0), **opts)
    self.entries={}
    self.values={}
    self.conversions={}
    self.table=gtk.Table(3, len(entries), False)
    self.table.show()
    self.vbox.add(self.table)
    self._init_entries(entries)
  
  def _init_entries(self, entries):
    '''
      Append labels and entries to the main table and the objects dictionaries and show them. 
    '''
    for i, entry_list in enumerate(entries):
      if len(entry_list)<3 or len(entry_list)>4:
        raise ValueError, "All entries have to be tuples with 3 or 4 items"
      key=entry_list[0]
      label=gtk.Label(key + ': ')
      label.show()
      # If entry is a list, there will be a dropdown menu to choose
      if hasattr(entry_list[1], '__iter__'):
        entry=gtk.combo_box_new_text()
        for selection_entry in entry_list[1]:
          entry.append_text(selection_entry)        
        entry.set_active(entry_list[2])
        entry.show()
        self.entries[key]=entry
        self.values[key]=entry_list[1][entry_list[2]]
        self.conversions[key]=entry_list[1]
      else:
        entry=gtk.Entry()
        entry.show()
        entry.set_text(str(entry_list[1]))
        entry.connect('activate', lambda *ignore: self.response(1))
        self.entries[key]=entry
        self.values[key]=entry_list[1]
        self.conversions[key]=entry_list[2]
      self.table.attach(label, 
            # X direction #          # Y direction
            0, 1,                      i, i+1,
            gtk.FILL,                       gtk.FILL,
            0,                         0)
      self.table.attach(entry, 
            # X direction #          # Y direction
            1, 2,                      i, i+1,
            gtk.FILL|gtk.EXPAND,                       gtk.FILL,
            0,                         0)
      if len(entry_list)==4:
        self.table.attach(entry_list[3], 
            # X direction #          # Y direction
            2, 3,                      i, i+1,
            gtk.FILL,                       gtk.FILL,
            0,                         0)
        entry_list[3].show()
  
  def run(self):
    '''
      Show the dialog and wait for input. Return the result as Dictionary 
      and a boolen definig if the Dialog was closed or OK was pressed.
    '''
    result=gtk.Dialog.run(self)
    self.collect_entries()
    self.hide()
    return self.values, result==1
  
  def collect_entries(self):
    '''
      Get values from all entry widgets and convert them. If conversion fails
      don't change the values.
    '''
    for key, entry in self.entries.items():
      if hasattr(entry, 'get_text'):
        text=entry.get_text()
        try:
          value=self.conversions[key](text)
          self.values[key]=value
        except ValueError:
          pass
      else:
        self.values[key]=self.conversions[key][entry.get_active()]

#--------------- SimpleEntryDialog to get a list of values from the user ---------------

#+++++++++++++++++++ FileChooserDialog with entries for width and height ++++++++++++++++

class ExportFileChooserDialog(gtk.FileChooserDialog):
  '''
    A file chooser dialog with two entries for with and height of an export image.
  '''
  
  def __init__(self, width, height, *args, **opts):
    '''
      Class constructor which adds two entries for with and height.
    '''
    if not 'action' in opts:
      opts['action']=gtk.FILE_CHOOSER_ACTION_SAVE
    if not 'buttons' in opts:
      opts['buttons']=(gtk.STOCK_SAVE, 
                     gtk.RESPONSE_OK, 
                     gtk.STOCK_CANCEL, 
                     gtk.RESPONSE_CANCEL
                     )
    gtk.FileChooserDialog.__init__(self, *args, **opts)
    self.width=width
    self.height=height
    if opts['action'] == gtk.FILE_CHOOSER_ACTION_SAVE:
      # Get the top moste table widget from the dialog
      table=self.vbox.get_children()[0].get_children()[0].get_children()[0].get_children()[0]
    elif opts['action'] == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
      # Introduce a new table right of the location entry
      table=gtk.Table(2, 2, False)
      self.vbox.get_children()[0].get_children()[0].get_children()[0].get_children()[1].pack_end(table, False)
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

#------------------- FileChooserDialog with entries for width and height ----------------

#+++ Printing Dialog which imports and creates PNG files for the datasets and sends it to a printer +++

class PrintDatasetDialog:
  '''
    Creating this class will create a gtk.PrintOperation and open a printing Dialog to
    print the datasets, supplied to the constructor.
    The datasets are exported to high-resolution PNG files and after processing through cairo
    get send to the Printer.
  '''
  
  def __init__(self, datasets, main_window, resolution=300, multiplot=False):
    '''
      Constructor setting setting the objects datasets and running the dialog
      
      @param datasets A list of MeasurementData objects
      @param main_window The active ApplicationMainWindow instance
      @param resolution The resolution the printer, only if A4 is selected.
    '''
    self.datasets=datasets
    self.main_window=main_window
    self.width=resolution*11.666
    self.use_multiplot=multiplot
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
    if not self.use_multiplot:
      print_op.set_n_pages(len(self.datasets))
    else:
      print_op.set_n_pages(1)
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
    if self.use_multiplot:
      self.multiplot(self.datasets)
    else:
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
                main_window.errorbars, 
                output_file=session.TEMP_DIR+'plot_temp.png',
                fit_lorentz=False)
    
  def multiplot(self, dataset_list):
    '''
      Method to create one multiplot in print quality.
    '''
    session=self.main_window.active_session
    session.picture_width=str(int(self.width))
    session.picture_height=str(int(self.width/1.414))
    window=self.main_window
    window.plot(session,
                [item[0] for item in dataset_list],
                dataset_list[0][1],
                #plotlist[0][0].short_info,
                dataset_list.title, 
                [item[0].short_info for item in dataset_list],
                main_window.errorbars,
                output_file=session.TEMP_DIR+'plot_temp.png',
                fit_lorentz=False, 
                sample_name=dataset_list.sample_name)
    
  def preview(self, operation, preview, context, parent):
    '''
      Create a preview of the plots to be printed.
    '''
    pass

#--- Printing Dialog which imports and creates PNG files for the datasets and sends it to a printer ---

# import last as this uses some of the classes
import main_window