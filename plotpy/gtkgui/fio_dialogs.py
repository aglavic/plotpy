#-*- coding: utf8 -*-
'''
  Dialogs for file input and output options.
'''

import gtk
import os

class ReaderOptionDialog(gtk.Dialog):
  '''
    A automatically generated dialog to enter options
    for a file reader. A default dictrionary is used
    to select the appropriate entries to choose.
  '''

  def __init__(self, name, defaults, default_units={}, default_description={}, path='.'):
    gtk.Dialog.__init__(self, title="%s"%name, buttons=('OK', 1, 'Cancel', 0))
    self.defaults=defaults
    self.units=default_units
    self.descriptions=default_description
    self.fpath=os.path.abspath(path)
    self.entries_OK=set()
    label=gtk.Label('Set parameters for %s reader:'%name)
    self.vbox.pack_start(label, False)
    label.show()
    self._build_entries()
    self.check_label=gtk.Label()
    self.check_label.set_markup('<span color="red">Check the entries!</span>')
    self.vbox.pack_end(self.check_label, False)
    self.check_label.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))

  def _build_entries(self):
    self.entries=[]
    for key, value in self.defaults:
      line=gtk.HBox()
      label=gtk.Label(key)
      entry=self._get_entry(key, value)
      if key in self.units:
        unit=self.units[key]
        if unit=='file':
          entry.set_text(self.fpath)
          entry.set_position(-1)
          entry.connect('changed', self._check_file)
          fbutton=gtk.FileChooserButton('Select %s file'%key)
          fbutton.set_focus_on_click(False)
          fbutton.set_current_folder(os.path.dirname(self.fpath))
          fbutton.set_filename(os.path.basename(self.fpath))
          fbutton.connect('file-set', self._select_file, entry)
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

  def _get_entry(self, key, value):
    '''
      Choose an appropriate entry for a specific value.
    '''
    tp=type(value)
    if tp in [int, float]:
      entry=gtk.Entry()
      entry.set_text(str(value))
      entry.connect('changed', self._check_number, tp)
    elif tp in [str, unicode]:
      entry=gtk.Entry()
      entry.set_text(str(value))
    entry.connect('activate', lambda *ignore: self.response(1))
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
    # change color of the entry when it is no number of type tp
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

  def _collect_entries(self):
    result={}
    for i, entry in enumerate(self.entries):
      key, default=self.defaults[i]
      tp=type(default)
      value=tp(entry.get_text())
      result[key]=value
    return result

  def run(self):
    result=gtk.Dialog.run(self)
    while result and not self.entries_OK==set():
      self.check_label.show()
      result=gtk.Dialog.run(self)
    if result:
      return True, self._collect_entries()
    else:
      return False, dict(self.defaults)


def reader_kwd_callback(reader, path, name):
  dialog=ReaderOptionDialog(reader.name, reader.parameters,
                            reader.parameter_units, reader.parameter_description)
  result, kwds=dialog.run()
  dialog.destroy()
  if result:
    return kwds
  else:
    return {}
