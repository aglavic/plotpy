# -*- encoding: utf-8 -*-
'''
  Dialogs derived from GTK.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
import cairo
import sys, os
from time import sleep
from math import sqrt
from config import gnuplot_preferences
import config.templates

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.6.3"
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
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logogreen.png").replace('library.zip', ''))    
  
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
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))        
  
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
  
  def get_active_dictionary(self):
    '''
      Return a dictionary with lists of active objects.
    '''
    data_items=self.get_active_objects_with_key()
    output={}
    for key, item in data_items:
      if key in output:
        output[key].append(item)
      else:
        output[key]=[item]
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
  _callback_window=None
  _result=None
  
  def __init__(self, title, entries, *args, **opts):
    '''
      Class constructor. Creates the dialog and label + entries from the list of entries supplied above.
      
      @param entries a list of tuples containing the values name, start value and function for type conversion.
    '''
    # Initialize this dialog
    gtk.Dialog.__init__(self, *args, title=title, buttons=('OK', 1, 'Cancel', 0), **opts)
    self.entries={}
    self.values={}
    self.conversions={}
    self.table=gtk.Table(3, len(entries), False)
    self.table.show()
    self.vbox.add(self.table)
    self._init_entries(entries)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))    
    self.connect('destroy', self.cleanup)
  
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
    if self._callback_window is None:
      result=gtk.Dialog.run(self)
    else:
      # if a mouse callback is registered it doesn't
      # work with Dialog.run
      self._result=None
      def set_result(widget, id):
        self._result=id
      self.connect('response', set_result)
      self.show_all()
      while self._result is None:
        while gtk.events_pending():
          gtk.main_iteration(False)
        sleep(0.1)
      result=self._result
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

  def register_mouse_callback(self, window, entries):
    '''
      Set the callback function to be used when selecting a position with the mouse button.
    '''
    window.mouse_position_callback=self._mouse_callback
    self._callback_window=window
    if self.transient_parent is None:
      self.set_transient_for(window)
    if len(entries)==0:
      raise ValueError, "You need to set at least one entry."
    for entry in entries:
      for item in entry:
        if len(item)!=2:
          raise ValueError, "All entry items need to be tuples of a key and index"
        if item[0] not in self.entries:
          raise KeyError, "item %s not in dialog entries" % item[0]
        if item[1]>5:
          raise IndexError, "position tuple only has 6 items"
    self.mouse_position_entries=entries
    self.mouse_position_step=0
    for key, index in entries[0]:
      self.entries[key].modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
      self.entries[key].modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse('yellow'))
  
  def _mouse_callback(self, position):
    '''
      Activated when mouse selection has been made.
    '''
    entry_steps=self.mouse_position_entries[self.mouse_position_step]
    for key, index in entry_steps:
      self.entries[key].set_text(str(position[index]))
      self.entries[key].modify_text(gtk.STATE_NORMAL, None)      
      self.entries[key].modify_text(gtk.STATE_SELECTED, None)      
    self.mouse_position_step+=1
    if self.mouse_position_step>=len(self.mouse_position_entries):
      self.mouse_position_step=0
    for key, index in self.mouse_position_entries[self.mouse_position_step]:
      self.entries[key].modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
      self.entries[key].modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse('yellow'))

  def cleanup(self, action):
    '''
      On delete remove the callback function.
    '''
    if self._callback_window is not None:
      self._callback_window.mouse_position_callback=None
    self._result=0

#--------------- SimpleEntryDialog to get a list of values from the user ---------------

#++++++++++++ MultipeakDialog to fit a peak function at differnt positions +++++++++++++

class MultipeakDialog(gtk.Dialog):
  '''
    A dialog to fit multiple peaks to a given dataset.
  '''
  _callback_window=None
  _result=None
  fit_class=None
  # define which parameter from the fit function are x0 and y0 values
  x_parameter=1
  y_parameter=0
  # start parameters used for the fit function
  _start_parameters=None
  # defines a list of fit runs to be made (e.g. first just x position than x,y,width)
  fit_runs=None
  # half width of the region where the fit should take place
  _fit_width=None
  
  def __init__(self, fit_class, fit_object, main_window,  *args, **opts):
    '''
      Class constructor.
      
      Additional keyword arguments:
        xyparams    : tuple of x0 and y0 parameter index of the used peak function
        startparams : list of start parameters used instead of the normal function default
        fitruns     : list of tuples with parameter indices to be fitted in sequential steps
        fitwidth    : half width of the region where each peak is fitted
      
      @param fit_class FitFunction derived object
      @param fit_object FitSession object to attach the functions to
    '''
    self.fit_class=fit_class
    self.fit_object=fit_object
    self._callback_window=main_window
    self._evaluate_options(opts)
    opts['parent']=main_window
    # Initialize this dialog
    gtk.Dialog.__init__(self, *args, buttons=('Pop Last',2, 'Finished', 1, 'Cancel', 0), **opts)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))    
    self.connect('destroy', self.cleanup)
    self.register_mouse_callback()
    self.table=gtk.Table(4, 5, False)
    self.table.show()
    self.new_peak_table=gtk.Table(3, 2, False)
    self.new_peak_table.show()
    self.vbox.pack_start(self.table, True)
    align=gtk.Alignment(0.5, 0, 0, 0)
    align.add(self.new_peak_table)
    align.show()
    self.vbox.pack_end(align, False)
    # List of FitFunction objects already finished
    self.finished_fits=[]
    self.peak_labels=[]
    self.peak_data=[]
    self._init_entries()
  
  def _evaluate_options(self, opts):
    '''
      Evaluate the keyword arguments supplied to the constructor.
    '''
    if not 'title' in opts:
      title=opts['title']='Multipeak Fit...'
    if 'xyparams' in opts:
      self.x_parameter, self.y_parameter=opts['xyparams']
      del(opts['xyparams'])
    if 'startparams' in opts:
      self._start_parameters=opts['startparams']
      del(opts['startparams'])
    else:
      self._start_parameters=list(self.fit_class.parameters)
    if 'fitruns' in opts:
      self.fit_runs=opts['fitruns']
      del(opts['fitruns'])
    else:
      self.fit_runs=[None]
    if 'fitwidth' in opts:
      self._fit_width=opts['fitwidth']
      del(opts['fitwidth'])
  
  def _init_entries(self):
    '''
      Append labels and entries to the main table and the objects dictionaries and show them. 
    '''
    # Entries for a new peak
    peak_x=gtk.Entry()
    peak_x.set_text('0')
    peak_x.set_width_chars(10)
    peak_y=gtk.Entry()
    peak_y.set_text('Auto')
    peak_y.set_width_chars(10)
    self.peak_entries=[peak_x, peak_y]
    fit_button=gtk.Button('Fit')
    fit_button.connect('clicked', self.fit_peak)
    peak_x.connect('activate', self.fit_peak)
    peak_y.connect('activate', self.fit_peak)
    self.new_peak_table.attach(gtk.Label('x-position'), 0,1, 0,1, gtk.FILL,gtk.FILL, 0,0)
    self.new_peak_table.attach(gtk.Label('y-position'), 1,2, 0,1, gtk.FILL,gtk.FILL, 0,0)
    self.new_peak_table.attach(peak_x, 0,1, 1,2, gtk.FILL,gtk.FILL, 0,0)
    self.new_peak_table.attach(peak_y, 1,2, 1,2, gtk.FILL,gtk.FILL, 0,0)
    self.new_peak_table.attach(fit_button, 2,3, 0,2, gtk.FILL,gtk.FILL, 0,0)
    self.new_peak_table.show_all()
  
  def fit_peak(self, widget=None, action=None):
    '''
      Fit a new function to the peak position defined in the dialog or by mouse click.
    '''
    peak_x, peak_y=self.peak_entries
    try:
      x=float(peak_x.get_text())
    except ValueError:
      peak_x.set_text('')
      return
    try:
      y=float(peak_y.get_text())
    except ValueError:
      if peak_y.get_text()=='Auto':
        y=self._start_parameters[self.y_parameter]
      else:
        peak_y.set_text('Auto')
        return
    start_params=list(self._start_parameters)
    start_params[self.x_parameter]=x
    start_params[self.y_parameter]=y
    fit=self.fit_class(start_params)
    if not self._fit_width is None:
      fit.x_from=x-self._fit_width
      fit.x_to=x+self._fit_width
    self.fit_object.functions.append([fit, True, True, False, False])
    for fit_params in self.fit_runs:
      if fit_params is not None:
        fit.refine_parameters=fit_params
      cov=self.fit_object.fit()[-1]
    self.fit_object.functions[-1][1]=False
    self.fit_object.simulate()
    self.add_peak(fit, cov)
    self._callback_window.replot()

  def add_peak(self, fit, cov):
    '''
      Add a new peak to the table of fits and the dialog.
      
      @param fit FitFunction object.
      @param cov Covariance matrix of the last fit
    '''
    self.finished_fits.append(fit)
    fits=len(self.finished_fits)
    x=fit.parameters[self.x_parameter]
    y=fit.parameters[self.y_parameter]
    if cov is None:
      dx=x/10.
      dy=y/10.
    else:
      dx=sqrt(cov[self.x_parameter][self.x_parameter])
      dy=sqrt(cov[self.y_parameter][self.y_parameter])
    label=gtk.Label("%i: \t%f±%f" % (fits, x, dx))
    label.show()
    self.peak_labels.append(label)
    self.table.attach(label, 
                      0,4,  fits, fits+1, 
                      gtk.FILL,gtk.FILL, 0,0
                      )
    self.peak_data.append([x, dx, y, dy])
  
  def remove_peak(self):
    '''
      Remove the last fited peak.
    '''
    self.peak_data.pop(-1)
    self.finished_fits.pop(-1)
    self.fit_object.functions.pop(-1)
    self.fit_object.simulate()
    self.table.remove(self.peak_labels.pop(-1))
    self._callback_window.replot()
  
  def run(self):
    '''
      Show the dialog and wait for input. Return the result as Dictionary 
      and a boolen definig if the Dialog was closed or OK was pressed.
    '''
    if self._callback_window is None:
      result=gtk.Dialog.run(self)
      while result==2:
        self.remove_peak()
        result=gtk.Dialog.run(self)
    else:
      # if a mouse callback is registered it doesn't
      # work with Dialog.run
      self._result=None
      def set_result(widget, id):
        self._result=id
      self.connect('response', set_result)
      self.show_all()
      while self._result is None or self._result==2:
        if self._result==2:
          self._result=None
          self.remove_peak()
        while gtk.events_pending():
          gtk.main_iteration(False)
        sleep(0.1)
      result=self._result
    self.hide()
    self.cleanup()
    return self.collect_positions(), result==1
  
  def collect_positions(self):
    '''
      Get values from all fits.
    '''
    output=list(self.peak_data)
    output.sort()
    return output

  def register_mouse_callback(self):
    '''
      Set the callback function to be used when selecting a position with the mouse button.
    '''
    window=self._callback_window
    window.mouse_position_callback=self._mouse_callback
  
  def _mouse_callback(self, position):
    '''
      Activated when mouse selection has been made.
    '''
    peak_x, peak_y=self.peak_entries
    peak_x.set_text(str(position[0]))
    peak_y.set_text(str(position[1]))
    self.fit_peak()

  def cleanup(self, action=None):
    '''
      On delete remove the callback function.
    '''
    if self._callback_window is not None:
      self._callback_window.mouse_position_callback=None
    self._result=0

  def __del__(self, *ignore):
    self.cleanup()

#------------- MultipeakDialog to fit a peak function at differnt positions -------------

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
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))    
    
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

#+++++++++++++++++++ FileImportDialog with additions for template import ++++++++++++++++

class FileImportDialog(gtk.FileChooserDialog):
  '''
    File chooser dialog with additional options for import templates.
  '''
  starting_folder=''
  template=None
  
  def __init__(self, current_folder, wildcards, template_folder=None, **options):
    '''
      Create a dialog for reading datafiles including an option for
      using templates.

      @param current_folder Folder uppond dialog start.
      @param wildcards sequance of items (name, pattern1, pattern2, ...).
    '''
    if template_folder is None:
      template_folder=config.templates.TEMPLATE_DIRECTORY
    if not 'title' in options:
      options['title']='Open new datafile...'
    options['action']=gtk.FILE_CHOOSER_ACTION_OPEN
    if not 'buttons' in options:
      options['buttons']=('Use Template', 66, gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    gtk.FileChooserDialog.__init__(self, **options)
    self.set_select_multiple(True)
    self.set_default_response(gtk.RESPONSE_OK)
    self.starting_folder=current_folder
    self.template_folder=template_folder
    self.set_current_folder(current_folder)
    filter = gtk.FileFilter()
    filter.set_name('All Files')
    filter.add_pattern('*')
    self.add_filter(filter)
    self.add_wildcards(wildcards)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logopurple.png").replace('library.zip', ''))    

  def add_wildcards(self, wildcards):
    '''
      Add a list of wildcards to the dialogs list.
      
      @param wildcards sequance of items (name, pattern1, pattern2, ...).
    '''
    # the first wildcard will be active
    wildcard=wildcards[0]
    filter = gtk.FileFilter()
    filter.set_name(wildcard[0])
    for pattern in wildcard[1:]:
      filter.add_pattern(pattern)
    self.add_filter(filter)
    self.set_filter(filter)
    for wildcard in wildcards[1:]:
      filter = gtk.FileFilter()
      filter.set_name(wildcard[0])
      for pattern in wildcard[1:]:
        filter.add_pattern(pattern)
      self.add_filter(filter)
  
  def clear_wildcards(self):
    '''
      Remove all wildcards active at the moment.
    '''
    filters=self.list_filters()
    for filter in filters[1:]:
      self.remove_filter(filter)

  def run(self):
    '''
      Open the dialog and wait for response. Returns the selected
      files, folder, template name.
    '''
    files=[]
    folder=self.starting_folder
    self.show_all()
    response = gtk.FileChooserDialog.run(self)
    if response == gtk.RESPONSE_OK:
      folder=self.get_current_folder()
      files=self.get_filenames()
      return files, folder, self.template
    elif response == 66:
      self.run_template_chooser()
      return self.run()
    else:
      return None, None, None

  def run_template_chooser(self):
    '''
      Open a dialog to select a specific template for file import.
    '''
    import sessions.templates
    tcdia=gtk.FileChooserDialog(title='Choose template file...', 
                                parent=self, 
                                action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
                                )
    filter = gtk.FileFilter()
    filter.set_name('Template (.py)')
    filter.add_pattern('*.py')
    tcdia.add_filter(filter)
    tcdia.set_current_folder(self.template_folder)
    result=tcdia.run()
    if result==gtk.RESPONSE_OK:
      template_file=tcdia.get_filename()
      self.template=sessions.templates.DataImportTemplate(template_file)
      self.clear_wildcards()
      self.add_wildcards([[self.template.name]+self.template.wildcards])
    tcdia.destroy()

#------------------- FileImportDialog with additions for template import ----------------

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
    cairo_context = context.get_cairo_context()
    p_width=context.get_width()
    p_height=context.get_height()
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

#++++++++++++++++++++ Dialog storing all imported dataset names +++++++++++++++++++++++++

class PlotTree(gtk.Dialog):
  '''
    A dialog containing a gtk.TreeView widget with gtk.TreeStore to display plots 
    imported from all files.
  '''
  expand_column=None
  pre_parent=None
  ignore_cursor_change=False
  preview_creation_active=False
  
  def __init__(self, data_dict, connected_function, *args, **opts):
    '''
      Create a dialog and place in the vbox a gtk.TreeView widget.
    '''
    if 'expand' in opts:
      self.expand_column=opts['expand']
      del(opts['expand'])
    gtk.Dialog.__init__(self, *args, **opts)
    self.data_dict=data_dict
    # Create the treeview widget
    self.treestore=gtk.TreeStore(gtk.gdk.Pixbuf, str)
    self.treeview=gtk.TreeView(self.treestore)
    self.connected_function=connected_function
    self.treeview.connect('cursor-changed', self.cursor_changed)
    self.create_columns()
    # insert the treeview in the dialog
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(self.treeview)
    sw.show_all()
    self.vbox.add(sw)
    # insert the data into the treeview
    self.add_data()
    self.clipboard = gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    if 'parent' in opts:
      # Somhow the dialog doesn't recognize the parent option, this fixes it.
      self.pre_parent=opts['parent']
    self.preview_button=gtk.Button('Create Previews')
    self.preview_button.connect('button_press_event', self.create_preview)
    self.vbox.pack_end(self.preview_button, False)

  def show_all(self):
    '''
      Chow the dialog and make it transient for it's parent.
    '''
    gtk.Dialog.show_all(self)
    if self.pre_parent is not None:
      self.set_transient_for(self.pre_parent)

  def create_columns(self):
    '''
      Add columns to the treeview.
    '''
    textrenderer = gtk.CellRendererText()
    picturerenderer = gtk.CellRendererPixbuf()
    # Add the columns
    column = gtk.TreeViewColumn('Preview', picturerenderer, pixbuf=0)
    self.treeview.append_column(column)
    column = gtk.TreeViewColumn('Imported Items', textrenderer, text=1)
    self.treeview.append_column(column)

  def add_data(self):
    '''
      Add the data from the dictionary to the treeview.
    '''
    self.treestore.clear()
    for name, datasets in sorted(self.data_dict.items()):
      iter=self.treestore.append(None, [None, name])
      for i, dataset in enumerate(datasets):
        preview=getattr(dataset,  'preview', None)
        self.treestore.append(iter, [preview, "%3i: %s" % (i, dataset.short_info)])
      if self.expand_column == name:
        self.treeview.expand_to_path(sorted(self.data_dict.keys()).index(name))
  
  def set_focus_item(self, key, index):
    '''
      Highlight an item.
    '''
    self.ignore_cursor_change=True
    path=(sorted(self.data_dict.keys()).index(key), index)
    self.treeview.expand_to_path(path)
    self.treeview.set_cursor(path)
    self.ignore_cursor_change=False
  
  def cursor_changed(self, widget):
    ''' 
      If an item is selected call a function with the corresponding
      key and index.
    '''
    if self.ignore_cursor_change:
      return
    cursor=self.treeview.get_cursor()[0]
    if len(cursor)==1:
      index=0
      key=self.treestore[cursor][1]
    else:
      index=cursor[1]
      key=self.treestore[cursor[0]][1]
    self.connected_function(key, index)
  
  def set_preview_parameters(self, plot_function, session, temp_file):
    '''
      Connect objects needed for preview creation.
    '''
    self.preview_plot=plot_function
    self.preview_session=session
    self.preview_temp_file=temp_file
  
  def create_preview(self, widget, action):
    '''
      Create a preview of the datasets and render it onto an image.
    '''
    if self.preview_creation_active:
      self.preview_button.set_label('Create Previews')
      self.preview_creation_active=False
      return
    if getattr(self, 'preview_plot', False):
      self.ignore_cursor_change=True
      self.preview_creation_active=True
      self.preview_button.set_label('Stop')
      for key, datasets in self.preview_session.file_data.items():
        for index, dataset in enumerate(datasets):
          if not self.preview_creation_active:
            return
          if getattr(dataset, 'preview', None) is None:
            self.preview_plot(self.preview_session,
                              [dataset],
                              'preview',
                              dataset.short_info,
                              [object.short_info for object in dataset.plot_together],
                              main_window.errorbars, 
                              output_file=self.preview_temp_file,
                              fit_lorentz=False)
            dataset.preview=gtk.gdk.pixbuf_new_from_file(self.preview_temp_file).scale_simple(100, 50, gtk.gdk.INTERP_BILINEAR)
            self.add_data()
            self.set_focus_item(key, index)
            while gtk.events_pending():
              gtk.main_iteration(False)
      self.add_data()
      self.set_focus_item(key, index)
      while gtk.events_pending():
        gtk.main_iteration(False)
      self.preview_button.set_label('Create Previews')
      self.preview_creation_active=False
      self.ignore_cursor_change=False
  
#-------------------- Dialog storing all imported dataset names -------------------------

#+++++++++++++++++++ Dialog to display the columns of a dataset +++++++++++++++++++++++++

class DataView(gtk.Dialog):
  '''
    A dialog containing a gtk.TreeView widget with gtk.ListStore to display data from
    a MeasurementData object.
  '''
  
  def __init__(self, dataset, *args, **opts):
    '''
      Create a dialog an place in the vbox a gtk.TreeView widget.
    '''
    gtk.Dialog.__init__(self, *args, **opts)
    self.dataset=dataset
    # Create the treeview widget
    columns=zip(dataset.dimensions(), dataset.units())
    self.liststore=gtk.ListStore(int, *[float for i in range(len(columns))])
    self.treeview=gtk.TreeView(self.liststore)
    self.treeview.connect('key-press-event', self.key_press_response)
    self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    self.treeview.set_rubber_banding(True)
    self.create_columns(columns)
    # insert the treeview in the dialog
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(self.treeview)
    sw.show_all()
    self.vbox.add(sw)
    # insert the data into the treeview
    self.add_data()
    self.clipboard = gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0], 
                           "..", "config", "logogreen.png").replace('library.zip', ''))    
  
  def create_columns(self, columns):
    '''
      Add columns to the treeview.
    '''
    textrenderer = gtk.CellRendererText()
    textrenderer.set_property('editable', True)
    textrenderer.connect("edited", self.edit_data)
    # Add the columns
    column = gtk.TreeViewColumn('Point', textrenderer, text=0)
    column.set_sort_column_id(0)
    self.treeview.append_column(column)
    for i, col in enumerate(columns):
      column = gtk.TreeViewColumn('%s [%s]' % (col[0], col[1]), textrenderer, text=i+1)
      column.set_sort_column_id(i+1)
      self.treeview.append_column(column)

  def add_data(self):
    '''
      Add the data from the dataset to the treeview.
    '''
    self.liststore.clear()
    for i, point in enumerate(self.dataset):
      self.liststore.append([i]+list(point))
  
  def edit_data(self, cellrenderertext, path, new_text):
    '''
      Change data inserted by user.
    '''
    row, column=self.treeview.get_cursor()
    real_row=self.liststore[row[0]][0]
    column=self.treeview.get_columns().index(column)-1
    if column==-1:
      return
    try:
      new_item=float(new_text)
    except ValueError:
      return
    self.liststore[row][column+1]=new_item
    if column<len(self.dataset.data):
      self.dataset.data[column][real_row]=new_item
    else:
      i=len(self.dataset.data)-1
      for j, col in self.dataset.data:
        if col.has_error:
          i+=1
        if i==column:
          col[real_row]=new_item

  def key_press_response(self, widget, event):
    keyname = gtk.gdk.keyval_name(event.keyval)
    if event.state & gtk.gdk.CONTROL_MASK:
      # copy selection
      if keyname=='c':
        model, selection=self.treeview.get_selection().get_selected_rows()
        indices=map(lambda select: self.liststore[select][0], selection)
        items=map(lambda index: "\t".join(map(str, self.dataset[index])), indices)
        clipboard_content="\n".join(items)
        self.clipboard.set_text(clipboard_content)
      if keyname=='a':
        self.treeview.get_selection().select_all()

#------------------- Dialog to display the columns of a dataset -------------------------

# import last as this uses some of the classes
import main_window
