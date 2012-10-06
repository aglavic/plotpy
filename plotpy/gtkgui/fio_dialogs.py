#-*- coding: utf8 -*-
'''
  Dialogs for file input and output options.
'''

import gtk
import os
from fnmatch import fnmatch
from plotpy.configobj import ConfigObj

class ReaderOptionDialog(gtk.Dialog):
  '''
    A automatically generated dialog to enter options
    for a file reader. A default dictrionary is used
    to select the appropriate entries to choose.
  '''

  def __init__(self, reader, name, defaults, default_units={}, default_description={}, path='.'):
    gtk.Dialog.__init__(self, title="%s"%name, buttons=('OK', 1, 'Cancel', 0))
    self.defaults=defaults
    self.units=default_units
    self.descriptions=default_description
    self.file_name=name
    self.fpath=os.path.abspath(path)
    self.entries_OK=set()
    label=gtk.Label('Set parameters for %s reader:'%reader)
    self.vbox.pack_start(label, False)
    label.show()
    self._build_entries()
    self.check_label=gtk.Label()
    self.check_label.set_markup('<span color="red">Check the entries!</span>')
    self.vbox.pack_end(self.check_label, False)
    self.check_label.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
    self._build_applies_to()

  def _build_entries(self):
    self.entries=[]
    for key, value in self.defaults:
      line=gtk.HBox()
      label=gtk.Label(key.replace('_', ' '))
      entry=self._get_entry(key, value)
      if key in self.units:
        unit=self.units[key]
        if unit.startswith('file'):
          entry.set_position(-1)
          entry.connect('changed', self._check_file)
          fbutton=gtk.FileChooserButton('Select %s file'%key)
          fbutton.set_focus_on_click(False)
          fbutton.set_current_folder(os.path.dirname(self.fpath))
          fbutton.set_filename(os.path.basename(self.fpath))
          fbutton.connect('file-set', self._select_file, entry)
          if '(' in unit:
            wildcard=unit.split('(', 1)[1].rsplit(')')[0]
            filter_=gtk.FileFilter()
            filter_.set_name('Filtered')
            filter_.add_pattern(wildcard.lower())
            filter_.add_pattern(wildcard.upper())
            fbutton.add_filter(filter_)
            fbutton.set_filter(filter_)
            filter_=gtk.FileFilter()
            filter_.set_name('All')
            filter_.add_pattern('*')
            fbutton.add_filter(filter_)
            for pattern in wildcard[1:]:
              filter_.add_pattern(pattern)

          line.pack_end(fbutton, False)
          fbutton.show()
        else:
          ulabel=gtk.Label(unit)
          line.pack_end(ulabel, False)
          ulabel.show()
      if key in self.descriptions:
        description=self.descriptions[key]
        label.set_tooltip_text(description)
        entry.set_tooltip_text(description)
      line.pack_start(label, False)
      line.pack_end(entry, True)
      self.vbox.add(line)
      label.show()
      entry.show()
      line.show()
      self.entries.append(entry)
    def_style=self.entries[0].get_style().text
    self.default_colors=(
                         def_style[gtk.STATE_NORMAL],
                         def_style[gtk.STATE_SELECTED]
                         )

  def _build_applies_to(self):
    '''
      Create options for the user to define if this applies to other
      files as well.
    '''
    vbox=gtk.VBox()
    label=gtk.Label('Use these settings:')
    vbox.add(label)

    buttons=[gtk.RadioButton(group=None, label='Once')]
    buttons[0].set_active(True)
    hbox=gtk.HBox()
    hbox.add(buttons[-1])
    buttons.append(gtk.RadioButton(group=buttons[0], label='Whole Session'))
    hbox.add(buttons[-1])
    vbox.add(hbox)
    buttons.append(gtk.RadioButton(group=buttons[0],
                   label='Store in plotpy_config.ini of this folder for Files matching pattern:'))
    blabel=buttons[-1].get_children()[0]
    blabel.set_line_wrap(True)
    blabel.set_use_underline(False)
    vbox.add(buttons[-1])

    self.applies_to_file=gtk.Entry()
    self.applies_to_file.set_text(self.file_name)
    self.applies_to_file.connect('changed', self._check_selffile)
    vbox.add(self.applies_to_file)

    self.applies_to_buttons=buttons
    self.vbox.pack_end(vbox, False)
    vbox.show_all()

  def _get_entry(self, key, value):
    '''
      Choose an appropriate entry for a specific value.
    '''
    tp=type(value)
    if tp in [int, float]:
      entry=gtk.Entry()
      entry.set_text(str(value))
      entry.connect('changed', self._check_number, tp)
      entry.connect('activate', lambda *ignore: self.response(1))
    elif tp in [str, unicode]:
      entry=gtk.Entry()
      entry.set_text(str(value))
      entry.connect('activate', lambda *ignore: self.response(1))
    elif tp is tuple:
      # tuples are used for a discrete set of selections
      # the first entry is the default
      entry=gtk.combo_box_new_text()
      for item in value:
        entry.append_text(item)
      entry.set_active(0)
    elif tp is bool:
      entry=gtk.CheckButton()
      entry.set_active(value)
    return entry

  def _check_number(self, entry, tp):
    # change color of the entry when it is no number of type tp
    try:
      tp(entry.get_text())
    except ValueError:
      self.entries_OK.add(entry)
      entry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
      entry.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse('yellow'))
    else:
      # reset style
      if entry in self.entries_OK:
        self.entries_OK.remove(entry)
        if self.entries_OK==set():
          self.check_label.hide()
      entry.modify_text(gtk.STATE_NORMAL, self.default_colors[0])
      entry.modify_text(gtk.STATE_SELECTED, self.default_colors[1])

  def _select_file(self, fbutton, entry):
    entry.set_text(fbutton.get_filename())
    entry.set_position(-1)

  def _check_file(self, entry):
    # change color of the entry if the file does not exist
    if not os.path.exists(entry.get_text()):
      self.entries_OK.add(entry)
      entry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
      entry.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse('yellow'))
    else:
      # reset style
      if entry in self.entries_OK:
        self.entries_OK.remove(entry)
        if self.entries_OK==set():
          self.check_label.hide()
      entry.modify_text(gtk.STATE_NORMAL, self.default_colors[0])
      entry.modify_text(gtk.STATE_SELECTED, self.default_colors[1])

  def _check_selffile(self, entry):
    # change color of the entry is no valid glob pattern for the file
    if not fnmatch(self.file_name, entry.get_text()):
      self.entries_OK.add(entry)
      entry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
      entry.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse('yellow'))
    else:
      # reset style
      if entry in self.entries_OK:
        self.entries_OK.remove(entry)
        if self.entries_OK==set():
          self.check_label.hide()
      entry.modify_text(gtk.STATE_NORMAL, self.default_colors[0])
      entry.modify_text(gtk.STATE_SELECTED, self.default_colors[1])

  def _collect_entries(self):
    '''
      Collect the result of all entries and return it
      as a dictionary.
    '''
    result={}
    for i, entry in enumerate(self.entries):
      key, default=self.defaults[i]
      tp=type(default)
      if tp is str:
        # make sure to only work with unicode strings internally
        tp=unicode
      if tp is tuple:
        value=default[entry.get_active()]
      elif tp is bool:
        value=entry.get_active()
      else:
        value=tp(entry.get_text())

      result[key]=value
    return result

  def _collect_applies_to(self):
    for i, button in enumerate(self.applies_to_buttons):
      if button.get_active():
        return i

  def run(self):
    result=gtk.Dialog.run(self)
    while result and not self.entries_OK==set():
      self.check_label.show()
      result=gtk.Dialog.run(self)
    if result:
      return (self._collect_applies_to(),
              self.applies_to_file.get_text()), self._collect_entries()
    else:
      return None, self.defaults

temporary_settings={}

def check_indict(compare_dict, name):
  for key in compare_dict.keys():
    if fnmatch(name, key):
      return True
  return False

def get_from_dict(compare_dict, name):
  for key, value in compare_dict.items():
    if fnmatch(name, key):
      return dict(value)

def reader_kwd_callback(reader, path, name):
  '''
    Check if there are appropriate preset settings for the file and
    reader and if not open a dialog for the user to define these settings.
  '''
  if reader.name in temporary_settings and path in temporary_settings[reader.name]:
    # take temporary settings for this path
    return dict(temporary_settings[reader.name][path])
  path_config=ConfigObj(os.path.join(path, 'plotpy_config.ini'), unrepr=True)
  if reader.name in path_config and check_indict(path_config[reader.name], name):
    # take stored configuration for this file
    return get_from_dict(path_config[reader.name], name)
  dialog=ReaderOptionDialog(reader.name, name, reader.parameters,
                            reader.parameter_units, reader.parameter_description,
                            path)
  result, kwds=dialog.run()
  dialog.destroy()
  if result:
    if result[0]==1:
      # store settings temporary
      if not reader.name in temporary_settings:
        temporary_settings[reader.name]={}
      temporary_settings[reader.name][path]=kwds
    elif result[0]==2:
      # store settings in path configuration file
      # these apply to files defined in the dialog
      if not reader.name in path_config:
        path_config[reader.name]={}
      path_config[reader.name][result[1]]=kwds
      path_config.write()
    return kwds
  else:
    return {}
