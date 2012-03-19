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
from plot_script.config import gnuplot_preferences
from plot_script.measurement_data_structure import PlotStyle
from plot_script.option_types import * #@UnusedWildImport
from plot_script.read_data import AsciiImportFilter, defined_filters
from plot_script.config import templates

#----------------------- importing modules --------------------------


__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"


def connect_stdout_dialog():
  '''
    Replace sys.stdout with a dialog window.
    
    :return: The dialog window.
  '''
  status_dialog=StatusDialog('Import Status', buttons=('Close', 0))
  status_dialog.connect('response', lambda*ignore: status_dialog.hide())
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

  def show(self):
    self.scrollwidget.show()
    self.textview.show()
    gtk.Dialog.show(self)


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
    end_visible=((adj.value+adj.page_size)>=adj.upper*0.98)
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
      gtk.main_iteration(False)

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
                                            0, 1, 0, 1, 0, 0, 0, 0)
    select_all_button=gtk.Button('Select Everything')
    bottom_table.attach(select_all_button, # X direction #   # Y direction
                                            1, 2, 0, 1, 0, 0, 0, 0)
    select_all_button.connect('button_press_event', self.select_all)
    select_none_button=gtk.Button('Select Nothing')
    bottom_table.attach(select_none_button, # X direction #   # Y direction
                                            2, 3, 0, 1, 0, 0, 0, 0)
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
    def stop_preview_creation(dialog, id_):
      # Stop the preview creation on a response signal
      self.stop_preview=True
      self.response_id=id_
    self.show()
    self.stop_preview=False
    self.connect('response', stop_preview_creation)
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
      
      :return: The Table widget
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
      
      :param key: The name of the file the previews in this line belong to.
      :param datalist: List of MeasurementData object.
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
              0, 1, line+1, line+2,
              0, 0,
              0, 0)
      select_all.show()
      main_table.attach(select_none,
              # X direction #          # Y direction
              1, 2, line+1, line+2,
              0, 0,
              0, 0)
      select_none.show()
    main_table.attach(label,
            # X direction #          # Y direction
            0, 2, line, line+1,
            0, gtk.FILL,
            0, 0)
    label.show()
    main_table.attach(align,
            # X direction #          # Y direction
            2, 3, line, line+2,
            gtk.FILL, gtk.FILL,
            0, 0)
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
        check_box=gtk.RadioButton(group=group, label="[%i] %s"%(i, dataset.short_info[:10]), use_underline=True)
      else:
        check_box=gtk.CheckButton(label="[%i] %s"%(i, dataset.short_info[:10]), use_underline=True)
      check_box.show()
      check_boxes.append(check_box)
      table.attach(check_box,
            # X direction #          # Y direction
            i, i+1, 1, 2,
            0, gtk.FILL,
            0, 0)
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
            i, i+1, 0, 1,
            0, gtk.FILL,
            0, 0)
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
      self.unset_previews.append((image, dataset))
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
    import main_window
    if getattr(self, 'preview_plot', False) and self.show_previews.get_active():
      image, dataset=self.unset_previews.pop(0)
      self.preview_plot(self.preview_session,
                                  [dataset],
                                  'preview',
                                  dataset.short_info,
                                  [item.short_info for item in dataset.plot_together],
                                  main_window.errorbars,
                                  output_file=self.preview_temp_file,
                                  fit_lorentz=False)
      buf=gtk.gdk.pixbuf_new_from_file(self.preview_temp_file).scale_simple(
                                              100, 50, gtk.gdk.INTERP_BILINEAR)
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
      
      :param entries: a list of tuples containing the values name, start value and function for type conversion.
    '''
    # Initialize this dialog
    opts['title']=title
    opts['buttons']=('OK', 1, 'Cancel', 0)
    if 'description' in opts:
      description=gtk.Label(opts['description'])
      del(opts['description'])
    else:
      description=None
    gtk.Dialog.__init__(self, *args, **opts)
    self.entries={}
    self.values={}
    self.conversions={}
    if description is not None:
      self.vbox.add(description)
      description.show()
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
      if len(entry_list)<2 or len(entry_list)>4:
        raise ValueError, "All entries have to be tuples with 2,3 or 4 items"
      if len(entry_list)==2:
        # the entry should be a True/False option
        key=entry_list[0]
        checkbox=gtk.CheckButton(key, use_underline=False)
        checkbox.show()
        checkbox.set_active(entry_list[1])
        self.entries[key]=checkbox
        self.values[key]=entry_list[1]
        self.conversions[key]=None
        self.table.attach(checkbox,
              # X direction #          # Y direction
              0, 3, i, i+1,
              gtk.FILL, gtk.FILL,
              0, 0)
      else:
        key=entry_list[0]
        label=gtk.Label(key+': ')
        label.show()
        # If entry is a list, there will be a dropdown menu to choose from
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
          entry.connect('activate', lambda*ignore: self.response(1))
          self.entries[key]=entry
          self.values[key]=entry_list[1]
          self.conversions[key]=entry_list[2]
        self.table.attach(label,
              # X direction #          # Y direction
              0, 1, i, i+1,
              gtk.FILL, gtk.FILL,
              0, 0)
        self.table.attach(entry,
              # X direction #          # Y direction
              1, 2, i, i+1,
              gtk.FILL|gtk.EXPAND, gtk.FILL,
              0, 0)
        if len(entry_list)==4:
          self.table.attach(entry_list[3],
              # X direction #          # Y direction
              2, 3, i, i+1,
              gtk.FILL, gtk.FILL,
              0, 0)
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
      def set_result(widget, id_):
        self._result=id_
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
      elif self.conversions[key] is None:
        self.values[key]=entry.get_active()
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
          raise KeyError, "item %s not in dialog entries"%item[0]
        if item[1]>5:
          raise IndexError, "position tuple only has 6 items"
    self.mouse_position_entries=entries
    self.mouse_position_step=0
    for key, ignore in entries[0]:
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

#++++++++++++++++++ MouseReader dialog to get a single xy position +++++++++++++++++++++

class MouseReader(gtk.Dialog):
  '''
    A simple dialog window used to retrieve a position on the plot.
  '''
  mouse_position=(0., 0.)
  _window=None

  def __init__(self, title, window):
    gtk.Dialog.__init__(self, title=title, parent=window)

    self._window=window
    x, y=window.get_position()
    self.set_default_size(400, 50)
    self.move(x+150, y)
    window.mouse_position_callback=self.callback
    self.vbox.add(gtk.Label(title))


  def run(self):
    '''
      Like Dialog.run but works with mouse callback. 
    '''
    self._result=None
    def set_result(widget, id_):
      self._result=id_
    self.connect('response', set_result)
    self.show_all()
    while self._result is None:
      while gtk.events_pending():
        gtk.main_iteration(False)
      sleep(0.1)
    self.cleanup()
    self.hide()
    return self.mouse_position

  def callback(self, position):
    '''
      Called when the mouse button is pressed on the plot.
    '''
    self.mouse_position=position[0:2]
    self._result=1

  def cleanup(self):
    self._window.mouse_position_callback=None


#------------------ MouseReader dialog to get a single xy position ---------------------

#++++++++++++ MultipeakDialog to fit a peak function at different positions +++++++++++++

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

  def __init__(self, fit_class, fit_object, main_window, *args, **opts):
    '''
      Class constructor.
      
      Additional keyword arguments:
        xyparams    : tuple of x0 and y0 parameter index of the used peak function
        startparams : list of start parameters used instead of the normal function default
        fitruns     : list of tuples with parameter indices to be fitted in sequential steps
        fitwidth    : half width of the region where each peak is fitted
      
      :param fit_class: FitFunction derived object
      :param fit_object: FitSession object to attach the functions to
    '''
    self.fit_class=fit_class
    self.fit_object=fit_object
    self._callback_window=main_window
    self._evaluate_options(opts)
    opts['parent']=main_window
    # Initialize this dialog
    opts['buttons']=('Pop Last', 2, 'Finished', 1, 'Cancel', 0)
    gtk.Dialog.__init__(self, *args, **opts)
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
      opts['title']='Multipeak Fit...'
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
    self.new_peak_table.attach(gtk.Label('x-position'), 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.new_peak_table.attach(gtk.Label('y-position'), 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    self.new_peak_table.attach(peak_x, 0, 1, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    self.new_peak_table.attach(peak_y, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    self.new_peak_table.attach(fit_button, 2, 3, 0, 2, gtk.FILL, gtk.FILL, 0, 0)
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
      
      :param fit: FitFunction object.
      :param cov: Covariance matrix of the last fit
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
    label=gtk.Label("%i: \t%f±%f"%(fits, x, dx))
    label.show()
    self.peak_labels.append(label)
    self.table.attach(label,
                      0, 4, fits, fits+1,
                      gtk.FILL, gtk.FILL, 0, 0
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
      def set_result(widget, response_id):
        self._result=response_id
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
    if opts['action']==gtk.FILE_CHOOSER_ACTION_SAVE:
      # Get the top moste table widget from the dialog
      table=self.vbox.get_children()[0].get_children()[0].get_children()[0].get_children()[0]
    elif opts['action']==gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
      # Introduce a new table right of the location entry
      table=gtk.Table(2, 2, False)
      try:
        self.vbox.get_children()[0].get_children()[0].get_children()[0].\
                                        get_children()[1].pack_end(table, False)
      except AttributeError:
        self.vbox.get_children()[0].get_children()[0].get_children()[0].\
                                        get_children()[1].add(table)
    label=gtk.Label('width')
    table.attach(label,
            # X direction #          # Y direction
            3, 4, 0, 1,
            0, gtk.FILL,
            0, 0)
    label=gtk.Label('height')
    table.attach(label,
            # X direction #          # Y direction
            4, 5, 0, 1,
            0, gtk.FILL,
            0, 0)
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
            3, 4, 1, 2,
            0, gtk.FILL,
            0, 0)
    table.attach(height_ent,
            # X direction #          # Y direction
            4, 5, 1, 2,
            0, gtk.FILL,
            0, 0)
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
last_filter=None

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

      :param current_folder: Folder uppond dialog start.
      :param wildcards: sequance of items (name, pattern1, pattern2, ...).
    '''
    if template_folder is None:
      template_folder=templates.TEMPLATE_DIRECTORY
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
    # Define filters for the file types.
    filter_=gtk.FileFilter()
    filter_.set_name('All Files')
    filter_.add_pattern('*')
    self.add_filter(filter_)
    if last_filter=='All Files':
      self.set_filter(filter_)
    filter_=gtk.FileFilter()
    filter_.set_name('Binary Plot.py')
    filter_.add_pattern('*.mdd')
    filter_.add_pattern('*.mdd.gz')
    filter_.add_pattern('*.mds')
    filter_.add_pattern('*.mds.gz')
    self.add_filter(filter_)
    if last_filter=='Binary Plot.py':
      self.set_filter(filter_)
    self.add_wildcards(wildcards)
    self.add_ascii_wildcards()
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logopurple.png").replace('library.zip', ''))

  def add_wildcards(self, wildcards):
    '''
      Add a list of wildcards to the dialogs list.
      
      :param wildcards: sequance of items (name, pattern1, pattern2, ...).
    '''
    global last_filter
    # the first wildcard will be active
    wildcard=wildcards[0]
    filter_=gtk.FileFilter()
    filter_.set_name(wildcard[0])
    for pattern in wildcard[1:]:
      filter_.add_pattern(pattern)
    self.add_filter(filter_)
    if last_filter is None or last_filter==wildcard[0]:
      self.set_filter(filter_)
    for wildcard in wildcards[1:]:
      filter_=gtk.FileFilter()
      filter_.set_name(wildcard[0])
      for pattern in wildcard[1:]:
        filter_.add_pattern(pattern)
      self.add_filter(filter_)
      if last_filter==wildcard[0]:
        self.set_filter(filter_)

  def add_ascii_wildcards(self):
    '''
      Add a list of wildcards for known ascii import filters.
    '''
    self.ascii_filters=[]
    # selection to autodetect the filter_ to use
    if len(defined_filters)>0:
      filter_=gtk.FileFilter()
      filter_.set_name('ASCII-import (auto-select)')
      for afilter in defined_filters:
        for ftype in afilter.file_types:
          filter_.add_pattern('*.'+ftype)
      self.add_filter(filter_)
      if last_filter in ['ASCII-import (auto-select)', 'ASCII-import (new)']:
        self.set_filter(filter_)
      self.ascii_filters.append(filter_)
    else:
      self.ascii_filters.append(None)
    # selection for single filter_
    for afilter in defined_filters:
      filter_=gtk.FileFilter()
      filter_.set_name('ASCII-import (%s)'%afilter.name)
      for ftype in afilter.file_types:
        filter_.add_pattern('*.'+ftype)
      self.add_filter(filter_)
      if last_filter=='ASCII-import (%s)'%afilter.name:
        self.set_filter(filter_)
      self.ascii_filters.append(filter_)
    # create a new filter_
    filter_=gtk.FileFilter()
    filter_.set_name('ASCII-import (new)')
    filter_.add_pattern('*.*')
    self.add_filter(filter_)
    self.ascii_filters.insert(1, filter_)


  def clear_wildcards(self):
    '''
      Remove all wildcards active at the moment.
    '''
    filters=self.list_filters()
    for filter_ in filters[1:]:
      self.remove_filter(filter_)

  def run(self):
    '''
      Open the dialog and wait for response. Returns the selected
      files, folder, template name.
    '''
    global last_filter
    files=[]
    folder=self.starting_folder
    self.show_all()
    response=gtk.FileChooserDialog.run(self)
    if response==gtk.RESPONSE_OK:
      folder=self.get_current_folder()
      files=self.get_filenames()
      filter_=self.get_filter()
      last_filter=filter_.get_name()
      # define filter_ status (-3: none, -2: auto, -1: new, +i: index for filter_ in list)
      if filter_ in self.ascii_filters:
        fidx=self.ascii_filters.index(filter_)
        ascii_filter=fidx-2
      else:
        ascii_filter=-3
      return files, folder, self.template, ascii_filter
    elif response==66:
      self.run_template_chooser()
      return self.run()
    else:
      return None, None, None,-3

  def run_template_chooser(self):
    '''
      Open a dialog to select a specific template for file import.
    '''
    import plot_script.sessions.templates
    tcdia=gtk.FileChooserDialog(title='Choose template file...',
                                parent=self,
                                action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
                                )
    filter_=gtk.FileFilter()
    filter_.set_name('Template (.py)')
    filter_.add_pattern('*.py')
    tcdia.add_filter(filter_)
    tcdia.set_current_folder(self.template_folder)
    result=tcdia.run()
    if result==gtk.RESPONSE_OK:
      template_file=tcdia.get_filename()
      self.template=plot_script.sessions.templates.DataImportTemplate(template_file)
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
      
      :param datasets: A list of MeasurementData objects
      :param main_window: The active ApplicationMainWindow instance
      :param resolution: The resolution the printer, only if A4 is selected.
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
    old_terminal=gnuplot_preferences.set_output_terminal_image
    terminal_items=old_terminal.split()
    for i, item in enumerate(terminal_items):
      if item in ['lw', 'linewidth']:
        # scale the linewidth
        terminal_items[i+1]=str(int(terminal_items[i+1])*(self.width/1600.))
    terminal_items+=['crop']
    gnuplot_preferences.set_output_terminal_image=" ".join(terminal_items)
    print_op=gtk.PrintOperation()
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
    print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.main_window)
    gnuplot_preferences.set_output_terminal_image=old_terminal

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
      
      :param operation: gtk.PrintOperation
      :param context: gtk.PrintContext
      :param current: page number
    '''
    print "Plotting page %i/%i"%(page_nr+1, len(self.datasets))
    if self.use_multiplot:
      self.multiplot(self.datasets)
    else:
      dataset=self.datasets[page_nr]
      self.plot(dataset)
    # get the cairo context to draw in
    cairo_context=context.get_cairo_context()
    p_width=context.get_width()
    p_height=context.get_height()
    # import the image
    surface=cairo.ImageSurface.create_from_png(self.main_window.active_session.TEMP_DIR+'plot_temp.png')
    # scale and center the image to fit the drawable area
    scale=min(p_width/surface.get_width(), p_height/surface.get_height())
    move_x=(p_width-scale*surface.get_width())/scale/2
    move_y=(p_height-scale*surface.get_height())/scale/2
    cairo_context.scale(scale, scale)
    cairo_context.set_source_surface(surface, move_x, move_y)
    cairo_context.paint()
    print "Sending page  %i/%i"%(page_nr+1, len(self.datasets))
    return

  def plot(self, dataset):
    '''
      Method to create one plot in print quality.
    '''
    session=self.main_window.active_session
    session.picture_width=str(int(self.width))
    session.picture_height=str(int(self.width/1.414))
    window=self.main_window
    import main_window
    window.plot(session,
                [dataset],
                session.active_file_name,
                dataset.short_info,
                [object_.short_info for object_ in dataset.plot_together],
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
    import main_window
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
    self.clipboard=gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    if 'parent' in opts:
      # Somhow the dialog doesn't recognize the parent option, this fixes it.
      self.pre_parent=opts['parent']
    self.preview_button=gtk.Button('Create Previews')
    self.preview_button.connect('button_press_event', self.create_preview)
    expand=gtk.Button('Expand')
    expand.connect('button_press_event', self.expand_all)
    button_hbox=gtk.HBox()
    button_hbox.add(self.preview_button)
    button_hbox.add(expand)
    self.vbox.pack_end(button_hbox, False)

  def show_all(self):
    '''
      Chow the dialog and make it transient for it's parent.
    '''
    gtk.Dialog.show_all(self)
    if self.pre_parent is not None:
      self.set_transient_for(self.pre_parent)
      self.connect('key_press_event', self.keyPress)

  def create_columns(self):
    '''
      Add columns to the treeview.
    '''
    textrenderer=gtk.CellRendererText()
    picturerenderer=gtk.CellRendererPixbuf()
    # Add the columns
    column=gtk.TreeViewColumn('Preview', picturerenderer, pixbuf=0)
    self.treeview.append_column(column)
    column=gtk.TreeViewColumn('Imported Items', textrenderer, text=1)
    self.treeview.append_column(column)

  def add_data(self):
    '''
      Add the data from the dictionary to the treeview.
    '''
    self.treestore.clear()
    for name, datasets in sorted(self.data_dict.items()):
      iter_=self.treestore.append(None, [None, name])
      for i, dataset in enumerate(datasets):
        preview=getattr(dataset, 'preview', None)
        self.treestore.append(iter_, [preview, "%3i: %s"%(i, dataset.short_info)])
      if self.expand_column==name:
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

  def expand_all(self, widget, action):
    '''
      Expand all files.
    '''
    self.treeview.expand_all()

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
            import main_window
            self.preview_plot(self.preview_session,
                              [dataset],
                              'preview',
                              dataset.short_info,
                              [object_.short_info for object_ in dataset.plot_together],
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

  def keyPress(self, widget, event):
    if (event.state&gtk.gdk.CONTROL_MASK or \
          event.state&gtk.gdk.MOD1_MASK):
      # propagate any <control>+Key and <alt>+Key to the main window.
      self.pre_parent.emit('key_press_event', event)

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
    self.liststore=gtk.ListStore(int, *[float for ignore in range(len(columns))])
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
    self.clipboard=gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logogreen.png").replace('library.zip', ''))

  def create_columns(self, columns):
    '''
      Add columns to the treeview.
    '''
    textrenderer=gtk.CellRendererText()
    textrenderer.set_property('editable', True)
    textrenderer.connect("edited", self.edit_data)
    # Add the columns
    column=gtk.TreeViewColumn('Point', textrenderer, text=0)
    column.set_sort_column_id(0)
    self.treeview.append_column(column)
    for i, col in enumerate(columns):
      column=gtk.TreeViewColumn('%s [%s]'%(col[0], col[1]), textrenderer, text=i+1)
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
      new_item=float(new_text.replace(',', '.'))
    except ValueError:
      return
    self.liststore[row][column+1]=new_item
    if column<len(self.dataset.data):
      self.dataset.data[column][real_row]=new_item
    else:
      i=len(self.dataset.data)-1
      for ignore, col in self.dataset.data:
        if col.has_error:
          i+=1
        if i==column:
          col[real_row]=new_item

  def key_press_response(self, widget, event):
    keyname=gtk.gdk.keyval_name(event.keyval)
    if event.state&gtk.gdk.CONTROL_MASK:
      # copy selection
      if keyname=='c':
        ignore, selection=self.treeview.get_selection().get_selected_rows()
        indices=map(lambda select: self.liststore[select][0], selection)
        items=map(lambda index: "\t".join(map(str, self.dataset[index])), indices)
        clipboard_content="\n".join(items)
        self.clipboard.set_text(clipboard_content)
      if keyname=='a':
        self.treeview.get_selection().select_all()

#------------------- Dialog to display the columns of a dataset -------------------------

#+++++++++++ Wizard dialog to import data using the AsciiImportFilter +++++++++++++++++++

class OptionSwitchSelection(gtk.Table):
  '''
    A widget containing a radio button selector to choose
    between different subentries. Every not selected entries
    are deactivated.
  '''
  _init_complet=False

  def __init__(self, options):
    '''
      Constructor, which creates the radio buttons etc.
    '''
    gtk.Table.__init__(self)
    self.button_group=None
    self.options=options
    self._create_entries()
    self._create_buttons()
    self._init_complet=True

  def _create_entries(self):
    '''
      Create a set of entries according to the type of options given.
    '''
    options=self.options
    entries=[]
    for active, name, vtype, default in options.items():
      if vtype is type(None):
        entries.append((name, []))
      elif vtype is float:
        entry=gtk.SpinButton(climb_rate=0.1, digits=2)
        entry.set_increments(0.1, 1)
        entry.set_range(-1e10, 1e10)
        if active:
          entry.set_value(options.value)
        elif default is not None:
          entry.set_value(default)
        entry.connect('value-changed', self._value_set, float)
        entries.append((name, [entry]))
      elif vtype is int:
        entry=gtk.SpinButton(climb_rate=1, digits=0)
        entry.set_increments(1, 1)
        entry.set_range(-1e10, 1e10)
        if active:
          entry.set_value(options.value)
        elif default is not None:
          entry.set_value(default)
        entry.connect('value-changed', self._value_set, int)
        entries.append((name, [entry]))
      elif vtype is str:
        entry=gtk.Entry()
        if active:
          entry.set_text(options.value)
        elif default is not None:
          entry.set_text(default)
        entry.connect('changed', self._entry_set)
        entries.append((name, [entry]))
      elif vtype is list:
        entries.append((name, vtype))
      elif vtype is tuple:
        pass
      elif vtype is bool:
        button=gtk.CheckButton()
        entries.append((name, [button]))
      elif vtype is StringList:
        entry=StringListEntry(default)
        entries.append((name, [entry]))
      elif vtype is PatternList:
        entry=PatternListEntry(default)
        entries.append((name, [entry]))
      elif vtype is FixedList:
        entry=FixedListEntry(default)
        entries.append((name, [entry]))
      else:
        raise NotImplementedError, "Type %s not defined for this widget"%vtype
    self._entries=entries

  def _create_buttons(self):
    '''
      Create all buttons and place them next to the according entries.
    '''
    buttons=[]
    options=self.options
    group=self.button_group
    entries=self._entries
    for i, entry in enumerate(entries):
      name, widgets=entry
      button=gtk.RadioButton(group, name)
      group=button
      button.show()
      buttons.append(button)
      button.connect("clicked", self._button_clicked)
      self.attach(button,
                  0, 1, i, i+1,
                  gtk.FILL, gtk.FILL
                  )
      for j, widget in enumerate(widgets):
        self.attach(widget,
                  j+1, j+2, i, i+1,
                  gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL
                  )
        widget.show()
    self.button_group=buttons[0]
    self.buttons=buttons
    for i in range(len(entries)):
      if i==options:
        buttons[i].set_active(True)
    self._button_clicked(None)

  def _button_clicked(self, widget):
    '''
      Called when one of the RadioButtons get pressed.
      Sets all widgets insensitive except the ones after
      the active button.
    '''
    buttons=self.buttons
    for j, entry in enumerate(self._entries):
      active=buttons[j].get_active()
      for widget in entry[1]:
        widget.set_sensitive(active)
      if self._init_complet and active:
        if self.options.value_types[j] is type(None):
          self.options.value=None
        elif type(widget) is StringListEntry:
          self.options.value=widget.string_list
        elif type(widget) is PatternListEntry:
          self.options.value=widget.pattern_list
        elif self.options.value_defaults[j] is not None:
          self.options.value=self.options.value_defaults[j]

  def _value_set(self, widget, vtype):
    '''
      Change the options value to a numeric value.
    '''
    self.options.value=vtype(widget.get_value())

  def _entry_set(self, widget):
    '''
      Change the options value to a string value.
    '''
    self.options.value=widget.get_text()

class StringListEntry(gtk.Table):
  '''
    An entry for string lists which contains entries and add/remove buttons.
  '''

  def __init__(self, string_list):
    '''
      Class constructor creating the table structure.
    '''
    self.string_list=string_list
    gtk.Table.__init__(self)
    self._entries=[]
    self._create_entries()

  def _create_entries(self):
    '''
      Creat two buttons and entries for the strings.
    '''
    button=gtk.Button('-')
    button.show()
    self.attach(button, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
    button.connect('clicked', self._remove_button_press)
    button=gtk.Button('+')
    button.show()
    self.attach(button, 1, 2, 0, 1, gtk.FILL, gtk.FILL)
    button.connect('clicked', self._add_button_press)
    for i, item in enumerate(self.string_list):
      entry=gtk.Entry()
      entry.set_text(item)
      entry.show()
      entry.set_width_chars(1)
      self._entries.append(entry)
      self.attach(entry, 2+i, 3+i, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)
      entry.connect('changed', self._change_entry, i)


  def _add_button_press(self, widget):
    '''
      Create a new text entry.
    '''
    i=len(self.string_list)
    self.string_list.append("")
    entry=gtk.Entry()
    self._entries.append(entry)
    entry.show()
    entry.set_width_chars(1)
    self.attach(entry, 2+i, 3+i, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)
    entry.connect('changed', self._change_entry, i)

  def _remove_button_press(self, widget):
    '''
      Remove the last entry from the list.
    '''
    self.string_list.pop(-1)
    self.remove(self._entries.pop(-1))


  def _change_entry(self, widget, index):
    '''
      Change a text entry.
    '''
    self.string_list[index]=widget.get_text()


class PatternListEntry(gtk.Table):
  '''
    An entry for string lists which contains entries and add/remove buttons.
  '''

  def __init__(self, pattern_list):
    '''
      Class constructor creating the table structure.
    '''
    self.pattern_list=pattern_list
    gtk.Table.__init__(self)
    self._entries=[]
    self._create_entries()

  def _create_entries(self):
    '''
      Creat two buttons and entries for the strings.
    '''
    button=gtk.Button('-')
    button.show()
    self.attach(button, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
    button.connect('clicked', self._remove_button_press)
    button=gtk.Button('+')
    button.show()
    self.attach(button, 1, 2, 0, 1, gtk.FILL, gtk.FILL)
    button.connect('clicked', self._add_button_press)
    for i, item in enumerate(self.pattern_list.description):
      label=gtk.Label(item)
      label.show()
      self.attach(label, 2+i, 3+i, 0, 1, gtk.FILL, gtk.FILL)
    for j, items in enumerate(self.pattern_list):
      entry_list=[]
      self._entries.append(entry_list)
      for i, item in enumerate(items):
        entry=gtk.Entry()
        entry.set_text(str(item))
        entry.show()
        entry.set_width_chars(1)
        entry_list.append(entry)
        self.attach(entry, 2+i, 3+i, 1+j, 2+j, gtk.EXPAND|gtk.FILL, gtk.FILL)
        entry.connect('changed', self._change_entry, i, j)


  def _add_button_press(self, widget):
    '''
      Create a new text entry.
    '''
    j=len(self.pattern_list)
    self.pattern_list.append(map(lambda item: item(), self.pattern_list.pattern))
    entry_list=[]
    self._entries.append(entry_list)
    items=self.pattern_list[-1]
    for i, item in enumerate(items):
      entry=gtk.Entry()
      entry.set_text(str(item))
      entry.show()
      entry.set_width_chars(1)
      entry_list.append(entry)
      self.attach(entry, 2+i, 3+i, 1+j, 2+j, gtk.EXPAND|gtk.FILL, gtk.FILL)
      entry.connect('changed', self._change_entry, i, j)

  def _remove_button_press(self, widget):
    '''
      Remove the last entry from the list.
    '''
    self.pattern_list.pop(-1)
    items=self._entries.pop(-1)
    for item in items:
      self.remove(item)


  def _change_entry(self, widget, i, j):
    '''
      Change a text entry.
    '''
    try:
      widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))
      self.pattern_list[j][i]=self.pattern_list.pattern[i](widget.get_text())
    except:
      widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))

class FixedListEntry(gtk.Table):
  '''
    Multiple item entry with labels.
  '''

  def __init__(self, fixed_list):
    '''
      Class constructor creating the table structure.
    '''
    self.fixed_list=fixed_list
    gtk.Table.__init__(self)
    self._entry_types=[]
    self._create_entries()

  def _create_entries(self):
    items=zip(self.fixed_list.entry_names, self.fixed_list)
    for i, item in enumerate(items):
      label=gtk.Label(item[0])
      label.show()
      entry=gtk.Entry()
      entry.set_text(str(item[1]))
      entry.set_width_chars(1)
      entry.show()
      entry.connect('changed', self._entry_changed, i)
      self.attach(label, i, i+1, 0, 1, gtk.FILL)
      self.attach(entry, i, i+1, 1, 2, gtk.EXPAND|gtk.FILL)
      self._entry_types.append(type(item[1]))

  def _entry_changed(self, widget, i):
    try:
      self.fixed_list[i]=self._entry_types[i](widget.get_text())
      widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))
    except:
      widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))

class SettingsNotebook(gtk.Notebook):
  '''
    A notebook widget which automatically build entries
    for a supplied object with a defined set of parameter names.
    The objects parameters are automatically changed when entries
    are changed.
  '''
  origin_object=None

  def __init__(self, object_, pages):
    '''
      Create the notebook with defined pages.
    '''
    self.origin_object=object_
    gtk.Notebook.__init__(self)
    for name, page, page_info in pages:
      self.add_settings_page(name, page, page_info)

  def add_settings_page(self, page_name, page, page_info):
    '''
      Add page with entries for each parameter supplied
      as a list (name, parameter).
    '''
    page_table=gtk.Table()
    i=0
    if page_info is not None:
      label=gtk.Label(page_info)
      page_table.attach(label,
                        0, 1, 0, 2,
                        gtk.EXPAND|gtk.FILL, 0)
      i=1
    for name, parameter in page:
      label=gtk.Label(name)
      label.show()
      page_table.attach(label,
                        0, 1, i*2, i*2+1,
                        gtk.EXPAND|gtk.FILL, 0)
      entry=self.get_settings_entry(parameter)
      entry.show()
      page_table.attach(entry,
                        0, 1, i*2+1, i*2+2,
                        gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL)
      i+=1
    page_table.show()
    sw=gtk.ScrolledWindow()
    sw.add_with_viewport(page_table)
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.show()

    label=gtk.Label(page_name)
    label.show()
    self.append_page(sw, label)

  def get_settings_entry(self, parameter):
    '''
      Retrieve an attribute of the origin object and
      add an entry according to the type of the attribute.
    '''
    attrib=getattr(self.origin_object, parameter)
    atype=type(attrib)
    # Standart types
    if atype is int:
      entry=gtk.SpinButton(climb_rate=1, digits=0)
      entry.set_increments(1, 10)
      entry.set_range(-1e10, 1e10)
      entry.set_value(attrib)
      entry.connect('value-changed', self._spin_value_changed, parameter, int)
    elif atype is float:
      entry=gtk.SpinButton(climb_rate=0.1, digits=2)
      entry.set_increments(0.1, 10)
      entry.set_range(-1e10, 1e10)
      entry.set_value(attrib)
      entry.connect('value-changed', self._spin_value_changed, parameter, float)
    elif atype is str:
      entry=gtk.Entry()
      entry.set_text(attrib)
      entry.connect('changed', self._entry_changed, parameter)
    # Custom types
    elif atype is Selection:
      entry=gtk.combo_box_new_text()
      for i, item in enumerate(attrib.items):
        entry.append_text(item)
        if i==attrib:
          entry.set_active(i)
      entry.connect('changed', self._selection_changed, parameter)
    elif atype is StringList:
      entry=StringListEntry(attrib)
    elif atype is PatternList:
      entry=PatternListEntry(attrib)
    elif atype is OptionSwitch:
      entry=OptionSwitchSelection(attrib)
    elif atype is FixedList:
      entry=FixedListEntry(attrib)
    else:
      raise NotImplementedError, "No widget defined for type '%s'"%atype.__name__
    return entry

  def _spin_value_changed(self, widget, parameter, atyp):
    '''
      Called when the value of a spinner entry changes.
    '''
    setattr(self.origin_object, parameter, atyp(widget.get_value()))

  def _entry_changed(self, widget, parameter):
    '''
      Called when the value of a spinner entry changes.
    '''
    setattr(self.origin_object, parameter, widget.get_text())

  def _selection_changed(self, widget, parameter):
    getattr(self.origin_object, parameter).selection=widget.get_active()

class ImportWizard(gtk.Dialog):
  '''
    A wizard dialog to import data using an AsciiImportFilter object.
    The results can be interactively observed while changing settings.
  '''


  def __init__(self, file_name, title='Define ASCII import filter...', presets=None):
    '''
      Constructor creating the dialog and all entry widgets needed.
    '''
    gtk.Dialog.__init__(self,
                        title=title,
                        buttons=('Preview', 2, 'Finish', 1, 'Cancel', 0))
    self.set_default_size(600, 600)
    self.import_filter=AsciiImportFilter('Untitled', presets)
    if presets is None:
      self.import_filter.file_types.append(file_name.rsplit('.', 1)[1])
    self.file_name=file_name
    # Insert upper level widgets
    self.notebook=SettingsNotebook(self.import_filter, [ # pages of the notebook
                                                        ['General settings',
                                                         [('Name', 'name'),
                                                          ('File Types', 'file_types'),
                                                          ],
                                                         None],
                                                        ['Splitting',
                                                         [('Header', 'header_lines'),
                                                          ('Footer', 'footer_lines'),
                                                          ('Sequences', 'split_sequences'),
                                                          ('Column separator', 'separator'),
                                                          ('Comment', 'comment_string'),
                                                          ],
                                                         None],
                                                        ['Columns',
                                                         [
                                                          ('Column definition', 'columns'),
                                                          ('Column selection-x', 'select_x'),
                                                          ('Column selection-y', 'select_y'),
                                                          ('Column selection-z', 'select_z'),
                                                          ('Calculate errors', 'post_calc_errors'),
                                                          ('Calculate new columns', 'post_calc_columns'),
                                                          ('Recalculate columns', 'post_recalc_columns'),
                                                          ],
                                                         None],
                                                        ['Metainfo',
                                                         [('Search in header', 'header_search'),
                                                          ('Search in footer', 'footer_search'),
                                                          ('Autoextract', 'auto_search'),
                                                          ],
                                                         None],
                                                        ['Naming',
                                                         [('Sample name', 'sample_name'),
                                                          ('Measurement info', 'short_info'),
                                                          ],
                                                         None],
                                                        ])
    self.notebook.show()
    self.vbox.add(self.notebook)
    self.info_box=gtk.Table()
    self.info_box.show()
    self.vbox.pack_end(self.info_box, False)

    self.file_text=gtk.TextView()
    self.file_text.set_editable(False)
    self.file_text.show()
    sw=gtk.ScrolledWindow()
    sw.add_with_viewport(self.file_text)
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.show()
    self.notebook.append_page(sw, gtk.Label('Text'))

    self.progressbar=gtk.ProgressBar()
    self.progressbar.show()
    self.vbox.pack_end(self.progressbar, False)

    self._set_filetext()

  def _set_filetext(self):
    buffer_=self.file_text.get_buffer()
    if self.file_name.endswith('.gz'):
      import gzip
      text=gzip.open(self.file_name, 'r').read()
    else:
      text=open(self.file_name, 'r').read()
    line_text=""
    for i, line in enumerate(text.splitlines()):
      line_text+="%03i:%s\n"%(i, line)
    buffer_.set_text(line_text)

  def run(self):
    '''
      Until OK or Cancel is pressed test the filter as preview.
    '''
    result=gtk.Dialog.run(self)
    while result==2:
      self.preview()
      result=gtk.Dialog.run(self)
    return result

  def preview(self):
    result=self.import_filter.simulate_readout(
               input_file=self.file_name,
               step_function=self._step_function,
               report=None)
    d=gtk.Dialog(title='Preview...', parent=self, flags=0, buttons=('Close', 0))
    d.set_default_size(600, 600)
    tv=gtk.TextView()
    tv.set_editable(False)
    tv.get_buffer().set_text(result)
    sw=gtk.ScrolledWindow()
    sw.add_with_viewport(tv)
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.show()
    d.vbox.add(sw)
    d.show_all()
    d.run()
    d.destroy()

  def _step_function(self, fraction, step):
    self.progressbar.set_fraction(fraction)
    self.progressbar.set_text(step)
    while gtk.events_pending():
      gtk.main_iteration(False)



#----------- Wizard dialog to import data using the AsciiImportFilter -------------------

#+++++++++++++++++ Dialog to change the color and style of a plot +++++++++++++++++++++++

class ColorDialog(gtk.ColorSelectionDialog):
  '''
    A specific color selection to select plot colors.
  '''
  _activation_callback=None

  def __init__(self, title='Select Color...', activation_callback=None, auto_apply=True):
    '''
      Create a new color selection dialog. If the activation_callback parameter is set
      to a function which takes one parameter it is called on any color change with
      the dialogs color selection as parameter.
    '''
    self._activation_callback=activation_callback
    gtk.ColorSelectionDialog.__init__(self, title)
    color_selection=self.get_color_selection()
    color_selection.set_has_palette(True)
    if activation_callback is not None:
      if auto_apply:
        color_selection.connect('color-changed', self._change_color)
      else:
        self.add_buttons('Apply', gtk.RESPONSE_APPLY)
    gp_line=gtk.HBox()
    gp_line.show()
    label=gtk.Label('Use Gnuplot Color:')
    label.show()
    gp_line.add(label)
    box=gtk.combo_box_new_text()
    box.show()
    box.append_text('<none>')
    box.set_active(0)
    for i in range(16):
      box.append_text('%i'%i)
    gp_line.add(box)
    self.vbox.add(gp_line)
    self.gp_box=box
    box.connect('changed', self._change_color)


  def _change_color(self, widget):
    '''
      If defined call the function set on init.
    '''
    if self._activation_callback is not None:
      try:
        self._activation_callback(int(self.gp_box.get_active_text()))
      except ValueError:
        self._activation_callback(self.get_color_selection())

  def run(self):
    '''
      Keep running if apply button is pressed.
    '''
    result=gtk.ColorSelectionDialog.run(self)
    self._change_color(None)
    while result==gtk.RESPONSE_APPLY:
      result=gtk.ColorSelectionDialog.run(self)
      self._change_color(None)
    return result

class StyleLine(gtk.Table):
  '''
    A line of options for plot styles.
  '''

  def __init__(self, plot_options, callback):
    '''
      Show entries to select plot options.
    '''
    gtk.Table.__init__(self, rows=1, columns=10, homogeneous=False)
    self.plot_options=plot_options
    self.callback=callback
    self._create_entries()
    self._update_active_entries()
    self._connect_events()

  def _create_entries(self):
    '''
      Fill the list with entries.
    '''
    if type(self.plot_options._special_plot_parameters) is PlotStyle:
      style=self.plot_options._special_plot_parameters
      options={
               'lw': str(style.linewidth),
               'ps': str(style.pointsize),
               'style': style.style,
               'substyle': style.substyle,
               'pointtype': style.pointtype,
               }
      if style._color is None:
        options['color']='<auto>'
      elif type(style._color) is int:
        options['color']='<%i>'%style._color
      else:
        options['color']="#%.2X%.2X%.2X"%tuple(style.color)
    else:
      options={
               'lw': str(PlotStyle.linewidth),
               'ps': str(PlotStyle.pointsize),
               'style': PlotStyle.style,
               'substyle': PlotStyle.substyle,
               'color': '<auto>',
               'pointtype': PlotStyle.pointtype,
               }
    self.toggle_custom=gtk.CheckButton(label='Custom Style  ', use_underline=True)
    self.toggle_custom.show()
    self.attach(self.toggle_custom, 0, 1, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    if type(self.plot_options._special_plot_parameters) is PlotStyle:
      self.toggle_custom.set_active(True)
    self.toggle_custom.connect('toggled', self.toggle_custom_action)
    # entries
    entries={}
    self.entries=entries
    style_selection=gtk.combo_box_new_text()
    for i, style in enumerate(sorted(PlotStyle._basic_styles.keys())):
      style_selection.append_text(style)
      if style==options['style']:
        style_selection.set_active(i)
    self.attach(style_selection, 1, 2, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    style_selection.show()
    entries['style']=style_selection
    style_selection=gtk.combo_box_new_text()
    if options['style'] in PlotStyle._substyles:
      for i, style in enumerate(sorted(PlotStyle._substyles[options['style']].keys())):
        style_selection.append_text(style)
        if style==options['substyle']:
          style_selection.set_active(i)
      style_selection.show()
    self.attach(style_selection, 2, 3, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    entries['substyle']=style_selection

    label=gtk.Label('Line Width:')
    self.attach(label, 3, 4, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    label.show()
    entries['lw-label']=label
    entry=gtk.Entry()
    entry.set_text(options['lw'])
    self.attach(entry, 4, 5, 0, 1, xoptions=gtk.EXPAND|gtk.FILL, yoptions=0, xpadding=0, ypadding=0)
    entry.show()
    entry.set_width_chars(5)
    entries['lw-entry']=entry

    label=gtk.Label('Color:')
    self.attach(label, 5, 6, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    label.show()
    entries['color-label']=label
    color_button=gtk.Button(options['color'])
    self.attach(color_button, 6, 7, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    color_button.show()
    entries['color-button']=color_button

    pointtype_selection=gtk.combo_box_new_text()
    for i, pointtype in enumerate(PlotStyle._point_types):
      pointtype_selection.append_text("%i: %s"%(pointtype[1], pointtype[0]))
      if pointtype[1]==options['pointtype']:
        pointtype_selection.set_active(i)
    self.attach(pointtype_selection, 7, 8, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    pointtype_selection.show()
    entries['pointtype']=pointtype_selection

    label=gtk.Label('Point Size:')
    self.attach(label, 8, 9, 0, 1, xoptions=0, yoptions=0, xpadding=0, ypadding=0)
    label.show()
    entries['ps-label']=label
    entry=gtk.Entry()
    entry.set_text(options['ps'])
    self.attach(entry, 9, 10, 0, 1, xoptions=gtk.EXPAND|gtk.FILL, yoptions=0, xpadding=0, ypadding=0)
    entry.show()
    entry.set_width_chars(5)
    entries['ps-entry']=entry

  def _update_active_entries(self):
    '''
      If the corresponding dataset has a style set,
      make all usable entries active.
    '''
    if type(self.plot_options._special_plot_parameters) is PlotStyle:
      ps=self.plot_options._special_plot_parameters
      for entry in self.entries.values():
        entry.set_sensitive(True)
      if not ps.style in ps._has_points:
        self.entries['ps-label'].set_sensitive(False)
        self.entries['ps-entry'].set_sensitive(False)
        self.entries['pointtype'].set_sensitive(False)
    else:
      for entry in self.entries.values():
        entry.set_sensitive(False)

  def _connect_events(self):
    '''
      Connect changes to the automated callback function.
    '''
    for key, entry in self.entries.items():
      if type(entry) is gtk.Label:
        continue
      elif type(entry) is gtk.Entry:
        entry.connect('activate', self.process_changes, key)
      elif type(entry) is gtk.ComboBox:
        if key=='substyle':
          self._substyle_handler=entry.connect('changed', self.process_changes, key)
        else:
          entry.connect('changed', self.process_changes, key)
      elif type(entry) is gtk.Button:
        entry.connect('clicked', self.change_color)

  def toggle_custom_action(self, widget):
    '''
      Activate or deactivate custom settings for the plot.
    '''
    if self.toggle_custom.get_active():
      self.plot_options._special_plot_parameters=PlotStyle()
      self.entries['color-button'].set_label('<auto>')
    else:
      self.plot_options._special_plot_parameters=None
    self._update_active_entries()
    self.callback()

  def process_changes(self, widget, key):
    '''
      Change style properties and activate the callback function.
    '''
    style=self.plot_options._special_plot_parameters
    if key=='style':
      style_list=sorted(PlotStyle._basic_styles.keys())
      style.style=style_list[widget.get_active()]
      if style.style in style._substyles:
        style_selection=self.entries['substyle']
        style_selection.handler_block(self._substyle_handler)
        # clear all entries:
        for i in range(20):
          style_selection.remove_text(0)
        style_selection.show()
        for i, items in enumerate(sorted(style._substyles[style.style].keys())):
          style_selection.append_text(items)
          if items==style.substyle:
            style_selection.set_active(i)
        style_selection.show()
        style_selection.handler_unblock(self._substyle_handler)
      else:
        style.substyle='default'
        self.entries['substyle'].hide()
      self._update_active_entries()
    if key=='pointtype':
      style.pointtype=PlotStyle._point_types[widget.get_active()][1]
    elif key=='lw-entry':
      try:
        lw=float(widget.get_text())
        style.linewidth=lw
      except ValueError:
        return
    elif key=='ps-entry':
      try:
        ps=float(widget.get_text())
        style.pointsize=ps
      except ValueError:
        return
    elif key=='substyle':
      substyle_list=sorted(style._substyles[style.style].keys())
      style.substyle=substyle_list[widget.get_active()]
    self.callback()

  def change_color(self, widget):
    '''
      Open a color selection dialog.
    '''
    old_color=self.plot_options._special_plot_parameters.color
    color_dia=ColorDialog(activation_callback=self._update_color, auto_apply=False)
    if type(old_color) is int:
      color_dia.gp_box.set_active(old_color+1)

    result=color_dia.run()
    if result==gtk.RESPONSE_OK:
      color=self.plot_options._special_plot_parameters.color
      if type(color) is int:
        self.entries['color-button'].set_label('<%i>'%color)
      else:
        self.entries['color-button'].set_label('#%.2X%.2X%.2X'%tuple(color))
    else:
      self._update_color(old_color)
      if old_color is None:
        self.entries['color-button'].set_label('<auto>')
      elif type(old_color) is int:
        self.entries['color-button'].set_label('<%i>'%old_color)
      else:
        self.entries['color-button'].set_label('#%.2X%.2X%.2X'%tuple(old_color))
    color_dia.destroy()
    self.callback()

  def _update_color(self, color_selection):
    self.plot_options._special_plot_parameters.color=color_selection
    self.callback()

#----------------- Dialog to change the color and style of a plot -----------------------

#+++++++++++++ Dialog to define labels, arrows and lines on the plot ++++++++++++++++++++

class LabelArrowDialog(gtk.Dialog):
  '''
    A tabed dialog with entries for labels, arrows/lines.
  '''
  _callback_entries=None

  def __init__(self, dataset, parent, title='Labels/Lines/Arrows/Rectangles',
               buttons=('New', 3, 'Apply', 2, 'OK', 1, 'Cancel', 0)):
    gtk.Dialog.__init__(self, title=title, buttons=buttons, parent=parent)
    self.plot_window=parent
    self.dataset=dataset
    self._first_init=True
    self.notebook=gtk.Notebook()
    self.label_table=gtk.Table()
    self.arrow_table=gtk.Table()
    self.rectangle_table=gtk.Table()
    self.notebook.append_page(self.label_table, gtk.Label('Labels'))
    self.notebook.append_page(self.arrow_table, gtk.Label('Lines/Arrows'))
    self.notebook.append_page(self.rectangle_table, gtk.Label('Rectangles'))
    self.notebook.show_all()
    self.vbox.add(self.notebook)
    self._init_all()
    self.connect('response', self._handle_response)
    self.connect('key_press_event', self.keyPress)

  def _init_all(self):
    '''
      Create entries for all Notebook tabs tables.
    '''
    self._init_labels()
    self._init_arrows()
    self._init_rectangles()
    self._first_init=False

  def _init_labels(self):
    '''
      Create entries of the labels table and connect user input actions.
    '''
    labels=self.dataset.plot_options.labels
    table=self.label_table
    if self._first_init:
      table.attach(gtk.Label('Position'), 0, 3, 0, 1)
      table.attach(gtk.Label('Text'), 3, 4, 0, 1)
      table.attach(gtk.Label('Front'), 4, 5, 0, 1)
      table.attach(gtk.Label('Point'), 5, 6, 0, 1)
      table.attach(gtk.Label('Frame'), 6, 7, 0, 1)
      table.attach(gtk.Label('Center'), 7, 8, 0, 1)
      table.attach(gtk.Label('Custom Options'), 8, 9, 0, 1)
    i=1
    self.label_entries=[]
    for position, text, front, point, center, frame, settings in labels:
      entries=[]
      self.label_entries.append(entries)
      for j, p in enumerate(position):
        p_entry=gtk.Entry()
        p_entry.set_text("%g"%p)
        p_entry.set_width_chars(4)
        table.attach(p_entry, j, j+1, i, i+1)
        entries.append(p_entry)
        p_entry.connect('activate', self._apply)
      for p_entry in entries[0:2]:
        p_entry.connect('focus-in-event', self._entry_focus_in,
                        entries[0], entries[1])
      text_entry=gtk.Entry()
      text_entry.set_text(text)
      #text_entry.set_width_chars(16)
      table.attach(text_entry, 3, 4, i, i+1)
      entries.append(text_entry)
      text_entry.connect('activate', self._apply)

      front_toggle=gtk.CheckButton()
      front_toggle.set_active(front)
      table.attach(front_toggle, 4, 5, i, i+1)
      entries.append(front_toggle)
      front_toggle.connect('toggled', self._apply)

      point_toggle=gtk.CheckButton()
      point_toggle.set_active(point)
      table.attach(point_toggle, 5, 6, i, i+1)
      entries.append(point_toggle)
      point_toggle.connect('toggled', self._apply)

      frame_toggle=gtk.CheckButton()
      frame_toggle.set_active(frame)
      table.attach(frame_toggle, 6, 7, i, i+1)
      entries.append(frame_toggle)
      frame_toggle.connect('toggled', self._apply)

      center_toggle=gtk.CheckButton()
      center_toggle.set_active(center)
      table.attach(center_toggle, 7, 8, i, i+1)
      entries.append(center_toggle)
      center_toggle.connect('toggled', self._apply)

      settings_entry=gtk.Entry()
      settings_entry.set_text(settings)
      #settings_entry.set_width_chars()
      table.attach(settings_entry, 8, 9, i, i+1)
      entries.append(settings_entry)
      settings_entry.connect('activate', self._apply)

      del_button=gtk.Button('DEL')
      del_button.connect('clicked', self._delete, 'label', i)
      table.attach(del_button, 9, 10, i, i+1)
      entries.append(del_button)
      i+=1
    table.show_all()

  def _get_labels(self, *ignore):
    '''
      Collect all entries for labels.
    '''
    new_labels=[]
    for entries in self.label_entries:
      try:
        posx=float(entries[0].get_text())
        posy=float(entries[1].get_text())
        posz=float(entries[2].get_text())
        text=entries[3].get_text()
        front=entries[4].get_active()
        point=entries[5].get_active()
        frame=entries[6].get_active()
        center=entries[7].get_active()
        settings=entries[8].get_text()
        new_labels.append([(posx, posy, posz), text, front, point, frame, center, settings])
      except:
        pass
    self.dataset.plot_options.labels=new_labels

  def _init_arrows(self):
    '''
      Create entries of the arrows/lines table and connect user input actions.
    '''
    arrows=self.dataset.plot_options.arrows
    table=self.arrow_table
    if self._first_init:
      table.attach(gtk.Label('From'), 0, 3, 0, 1)
      table.attach(gtk.Label('To'), 3, 6, 0, 1)
      table.attach(gtk.Label('Arrow'), 6, 7, 0, 1)
      table.attach(gtk.Label('Front'), 7, 8, 0, 1)
      table.attach(gtk.Label('Custom Options'), 8, 9, 0, 1)
    i=1
    self.arrow_entries=[]
    for position, nohead, front, settings in arrows:
      from_pos, to_pos=position
      entries=[]
      self.arrow_entries.append(entries)
      for j, p in enumerate(from_pos):
        p_entry=gtk.Entry()
        p_entry.set_text("%g"%p)
        p_entry.set_width_chars(4)
        table.attach(p_entry, j, j+1, i, i+1)
        entries.append(p_entry)
        p_entry.connect('activate', self._apply)
      for p_entry in entries[0:2]:
        p_entry.connect('focus-in-event', self._entry_focus_in,
                        entries[0], entries[1])
      for j, p in enumerate(to_pos):
        p_entry=gtk.Entry()
        p_entry.set_text("%g"%p)
        p_entry.set_width_chars(4)
        table.attach(p_entry, j+3, j+4, i, i+1)
        entries.append(p_entry)
        p_entry.connect('activate', self._apply)
      for p_entry in entries[3:5]:
        p_entry.connect('focus-in-event', self._entry_focus_in,
                        entries[3], entries[4])

      arrow_toggle=gtk.CheckButton()
      arrow_toggle.set_active(not nohead)
      table.attach(arrow_toggle, 6, 7, i, i+1)
      entries.append(arrow_toggle)
      arrow_toggle.connect('toggled', self._apply)

      front_toggle=gtk.CheckButton()
      front_toggle.set_active(front)
      table.attach(front_toggle, 7, 8, i, i+1)
      entries.append(front_toggle)
      front_toggle.connect('toggled', self._apply)

      settings_entry=gtk.Entry()
      settings_entry.set_text(settings)
      #settings_entry.set_width_chars()
      table.attach(settings_entry, 8, 9, i, i+1)
      entries.append(settings_entry)
      settings_entry.connect('activate', self._apply)

      del_button=gtk.Button('DEL')
      del_button.connect('clicked', self._delete, 'arrow', i)
      table.attach(del_button, 9, 10, i, i+1)
      entries.append(del_button)
      i+=1
    table.show_all()

  def _get_arrows(self, *ignore):
    '''
      Collect all entries for labels.
    '''
    new_arrows=[]
    for entries in self.arrow_entries:
      try:
        pos_fx=float(entries[0].get_text())
        pos_fy=float(entries[1].get_text())
        pos_fz=float(entries[2].get_text())
        pos_tx=float(entries[3].get_text())
        pos_ty=float(entries[4].get_text())
        pos_tz=float(entries[5].get_text())
        nohead=not entries[6].get_active()
        front=entries[7].get_active()
        settings=entries[8].get_text()
        new_arrows.append([((pos_fx, pos_fy, pos_fz), (pos_tx, pos_ty, pos_tz)),
                             nohead, front, settings])
      except:
        pass
    self.dataset.plot_options.arrows=new_arrows

  def _init_rectangles(self):
    '''
      Create entries of the rectangle table and connect user input actions.
    '''
    rectangles=self.dataset.plot_options.rectangles
    table=self.rectangle_table
    if self._first_init:
      table.attach(gtk.Label('From'), 0, 3, 0, 1)
      table.attach(gtk.Label('To'), 3, 6, 0, 1)
      table.attach(gtk.Label('Front'), 6, 7, 0, 1)
      table.attach(gtk.Label('Filled'), 7, 8, 0, 1)
      table.attach(gtk.Label('Occ.'), 8, 9, 0, 1)
      table.attach(gtk.Label('F. Color'), 9, 10, 0, 1)
      table.attach(gtk.Label('Border'), 10, 11, 0, 1)
      table.attach(gtk.Label('B. Color'), 11, 12, 0, 1)
      table.attach(gtk.Label('Custom Options'), 12, 13, 0, 1)
    i=1
    self.rectangle_entries=[]
    for position, front, filled, transp, fc, border, bc, settings in rectangles:
      from_pos, to_pos=position
      entries=[]
      self.rectangle_entries.append(entries)
      for j, p in enumerate(from_pos):
        p_entry=gtk.Entry()
        p_entry.set_text("%g"%p)
        p_entry.set_width_chars(4)
        table.attach(p_entry, j, j+1, i, i+1)
        entries.append(p_entry)
        p_entry.connect('activate', self._apply)
      for p_entry in entries[0:2]:
        p_entry.connect('focus-in-event', self._entry_focus_in,
                        entries[0], entries[1])
      for j, p in enumerate(to_pos):
        p_entry=gtk.Entry()
        p_entry.set_text("%g"%p)
        p_entry.set_width_chars(4)
        table.attach(p_entry, j+3, j+4, i, i+1)
        entries.append(p_entry)
        p_entry.connect('activate', self._apply)
      for p_entry in entries[3:5]:
        p_entry.connect('focus-in-event', self._entry_focus_in,
                        entries[3], entries[4])

      front_toggle=gtk.CheckButton()
      front_toggle.set_active(front)
      table.attach(front_toggle, 6, 7, i, i+1)
      entries.append(front_toggle)
      front_toggle.connect('toggled', self._apply)

      filled_toggle=gtk.CheckButton()
      filled_toggle.set_active(filled)
      table.attach(filled_toggle, 7, 8, i, i+1)
      entries.append(filled_toggle)
      filled_toggle.connect('toggled', self._apply)

      transp_entry=gtk.Entry()
      transp_entry.set_text("%g"%transp)
      transp_entry.set_width_chars(4)
      table.attach(transp_entry, 8, 9, i, i+1)
      entries.append(transp_entry)
      transp_entry.connect('activate', self._apply)

      fc_entry=gtk.Entry()
      fc_entry.set_text(fc)
      fc_entry.set_width_chars(8)
      table.attach(fc_entry, 9, 10, i, i+1)
      entries.append(fc_entry)
      fc_entry.connect('activate', self._apply)

      border_toggle=gtk.CheckButton()
      border_toggle.set_active(border)
      table.attach(border_toggle, 10, 11, i, i+1)
      entries.append(border_toggle)
      border_toggle.connect('toggled', self._apply)

      bc_entry=gtk.Entry()
      bc_entry.set_text(bc)
      bc_entry.set_width_chars(8)
      table.attach(bc_entry, 11, 12, i, i+1)
      entries.append(bc_entry)
      bc_entry.connect('activate', self._apply)

      settings_entry=gtk.Entry()
      settings_entry.set_text(settings)
      #settings_entry.set_width_chars()
      table.attach(settings_entry, 12, 13, i, i+1)
      entries.append(settings_entry)
      settings_entry.connect('activate', self._apply)

      del_button=gtk.Button('DEL')
      del_button.connect('clicked', self._delete, 'rectangle', i)
      table.attach(del_button, 13, 14, i, i+1)
      entries.append(del_button)
      i+=1
    table.show_all()

  def _get_rectangles(self, *ignore):
    '''
      Collect all entries for labels.
    '''
    new_rectangles=[]
    for entries in self.rectangle_entries:
      try:
        pos_fx=float(entries[0].get_text())
        pos_fy=float(entries[1].get_text())
        pos_fz=float(entries[2].get_text())
        pos_tx=float(entries[3].get_text())
        pos_ty=float(entries[4].get_text())
        pos_tz=float(entries[5].get_text())
        front=entries[6].get_active()
        filled=entries[7].get_active()
        transp=float(entries[8].get_text())
        fc=entries[9].get_text()
        border=entries[10].get_active()
        bc=entries[11].get_text()
        settings=entries[12].get_text()
        new_rectangles.append([((pos_fx, pos_fy, pos_fz), (pos_tx, pos_ty, pos_tz)),
                             front, filled, transp, fc,
                             border, bc, settings])
      except ValueError:
        pass
    self.dataset.plot_options.rectangles=new_rectangles

  def _clear_all(self, *ignore):
    '''
      Remove all entries form label, arrow ane line tables.
    '''
    if self._callback_entries is not None:
      self.plot_window.mouse_position_callback=None
      self._callback_entries[0].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
      self._callback_entries[1].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
      self._callback_entries=None
    for entries in self.label_entries:
      for entry in entries:
        self.label_table.remove(entry)
    for entries in self.arrow_entries:
      for entry in entries:
        self.arrow_table.remove(entry)
    for entries in self.rectangle_entries:
      for entry in entries:
        self.rectangle_table.remove(entry)


  def _apply(self, *ignore):
    if self._callback_entries is not None:
      self.plot_window.mouse_position_callback=None
      self._callback_entries[0].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
      self._callback_entries[1].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
      self._callback_entries=None
    self._get_labels()
    self._get_arrows()
    self._get_rectangles()
    self.plot_window.replot()

  def _entry_focus_in(self, widget, event, xentry, yentry):
    '''
      Focused position entries connect to the mouse click of the main window
      to allow positions to be defined easily.
    '''
    xentry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
    yentry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
    if self._callback_entries is not None:
      self._callback_entries[0].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
      self._callback_entries[1].modify_text(gtk.STATE_NORMAL,
                                            gtk.gdk.color_parse('black'))
    self._callback_entries=[xentry, yentry]
    self.plot_window.mouse_position_callback=self._mouse_callback

  def _mouse_callback(self, position):
    '''
      Activated when mouse selection has been made.
    '''
    xentry, yentry=self._callback_entries
    xentry.set_text(str(position[0]))
    yentry.set_text(str(position[1]))

  def change_dataset(self, new_dataset):
    self._clear_all()
    self.dataset=new_dataset
    self._init_all()

  def _delete(self, button, part, index):
    if part=='label':
      self._clear_all()
      self.dataset.plot_options.labels.pop(index-1)
      self._init_all()
    elif part=='arrow':
      self._clear_all()
      self.dataset.plot_options.arrows.pop(index-1)
      self._init_all()
    elif part=='rectangle':
      self._clear_all()
      self.dataset.plot_options.rectangles.pop(index-1)
      self._init_all()
    self._apply()

  def update(self, *ignore):
    self._clear_all()
    self._init_all()

  def _handle_response(self, dialog, response_id):
    if response_id==3: # New
      active_page=self.notebook.get_current_page()
      if active_page==0:
        self.dataset.plot_options.labels.append([(0, 0, 1), '',
                                                 True, False, False, False, ''])
      elif active_page==1:
        self.dataset.plot_options.arrows.append([((0, 0, 1), (0, 0, 1)),
                                                 True, True, ''])
      elif active_page==2:
        self.dataset.plot_options.rectangles.append([
                                ((0, 0, 1), (0, 0, 1)),
                                True, True, 0.3, 'white',
                                True, 'black', ''])
      self._clear_all()
      self._init_all()
    elif response_id==2: # Apply
      self._apply()
    elif response_id==1: # OK
      self._apply()
      self.plot_window.label_arrow_dialog=None
      self.destroy()
    else: # Cancel
      self.plot_window.label_arrow_dialog=None
      self.destroy()

  def keyPress(self, widget, event):
    if (event.state&gtk.gdk.CONTROL_MASK or \
          event.state&gtk.gdk.MOD1_MASK):
      # propagate any <control>+Key and <alt>+Key to the main window.
      self.plot_window.emit('key_press_event', event)

  def destroy(self, *args, **kwargs):
    if self._callback_entries is not None:
      self.plot_window.mouse_position_callback=None
    return gtk.Dialog.destroy(self, *args, **kwargs)


#------------- Dialog to define labels, arrows and lines on the plot --------------------
