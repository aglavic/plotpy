'''
  GUI replacement for the default command line messenger.
'''

import sys
import gtk
from time import strftime, time
from plotpy import message
from plotpy.config.gui import ICONS

def connect_stdout_dialog():
  '''
    Replace sys.stdout with a dialog window.
    
    :return: The dialog window.
  '''
  status_dialog=GUIMessenger('Messages')
  status_dialog.connect('response', lambda*ignore: status_dialog.hide())
  status_dialog.fileno=lambda : 1
  status_dialog.flush=lambda : True
  sys.stdout=status_dialog
  status_dialog.set_default_size(500, 400)
  status_dialog.show_all()
  status_dialog.move(0, 0)
  return status_dialog

class GUIMessenger(gtk.Dialog):
  '''
    Messenger which does not raise any errors and goups output
    according to the group and item scheme. Progress is
    indicated independent of output as last line in the 
    console.
  '''
  active_group=None
  active_group_iter=None
  active_item=None
  active_item_iter=None
  last_message=None
  numitems=1
  item_count=0
  _cell_odd=True
  _write_text=u''
  encoding='utf8'

  def __init__(self, title, progressbar=None, statusbar=None, parent=None, initial_text=''):
    gtk.Dialog.__init__(self, parent=parent, title=title,
                        flags=gtk.DIALOG_NO_SEPARATOR|gtk.DIALOG_DESTROY_WITH_PARENT)
    self._init_treeview()
    self.textview=gtk.TextView()
    self.buffer=self.textview.get_buffer()
    self.buffer.set_text(initial_text)
    # attach the textview inside a scrollbar widget
    self.scrollwidget=gtk.ScrolledWindow()
    self.scrollwidget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.scrollwidget.add(self.treeview)
    self.scrollwidget.show()
    self.textview.show()
    self.vbox.add(self.scrollwidget)
    self.end_iter=self.buffer.get_end_iter()
    self.end_mark=self.buffer.create_mark('End', self.end_iter, False)
    self.set_icon_from_file(ICONS['LogoG'])
    # Bottombar
    hbox=gtk.HBox()
    self.progressbar=gtk.ProgressBar()
    self.progressbar.show()
    self.connected_progress=progressbar
    self.connected_status=statusbar
    self.popup_toggle=gtk.CheckButton('Popup on warnings')
    self.popup_toggle.set_active(True)
    self.popup_toggle.show()
    hbox.pack_start(self.popup_toggle, False)
    hbox.add(self.progressbar)
    self.vbox.pack_end(hbox, False)
    self.connect('delete-event', self._no_destroy)
    message.messenger=self
    self._stored_position=self.get_size()

  def _no_destroy(self, widget, data=None):
    '''
      Make sure the window is not destoryed when it gets closed.
    '''
    self.hide()
    return True

  def show(self):
    self.set_default_size(*self._stored_position)
    gtk.Dialog.show(self)

  def hide(self):
    self._stored_position=self.get_size()
    gtk.Dialog.hide(self)

  def _init_treeview(self):
    self.treestore=gtk.TreeStore(str, str, str, str)
    self.treeview=gtk.TreeView(self.treestore)
    self.treeview.show()
    self.treeview.set_reorderable(False)
    self.group_column=gtk.TreeViewColumn('Item')
    self.message_column=gtk.TreeViewColumn('Message')
    self.time_column=gtk.TreeViewColumn('Time')
    self.treeview.append_column(self.group_column)
    self.treeview.append_column(self.message_column)
    self.treeview.append_column(self.time_column)
    cell=gtk.CellRendererText()
    cell.set_property('background-set', True)
    self.group_column.pack_start(cell, True)
    self.group_column.set_attributes(cell, text=0, background=3)
    cell=gtk.CellRendererText()
    cell.set_property('background-set', True)
    self.message_column.pack_start(cell, True)
    self.message_column.set_attributes(cell, text=1, background=3)
    cell=gtk.CellRendererText()
    cell.set_property('background-set', True)
    self.time_column.pack_start(cell, True)
    self.time_column.set_attributes(cell, text=2, background=3)
    #self.vbox.add(self.treeview)

  def write(self, text):
    '''
      Append a string to the buffer and scroll at the end, if it was visible before.
    '''
    if type(text) is not unicode:
      utext=unicode(text, encoding=message.in_encoding, errors='ignore').strip()
    else:
      utext=text.strip()
    while u'\b' in utext:
      idx=utext.index(u'\b')
      if idx>0:
        utext=utext[:idx-1]+utext[idx+1:]
      else:
        utext=utext[1:]
    if utext!=u'':
      self._write_text+='\n'+utext

  def flush(self):
    if self._write_text!='':
      self._write(self._write_text, group=None, item=None)
    self._write_text=u''

  def _write(self, text=None, group=None, item=None, numitems=1, progress=None,
             bgcolor='#ffffff'):
    # decode str input
    stext=u''
    if item is not None:
      if type(item) is str:
        item=unicode(item, message.in_encoding)
      stext=item+u'-'+stext
    if group is not None:
      if type(group) is str:
        group=unicode(group, message.in_encoding)
      stext=group+u'-'+stext
    if text is not None:
      if type(text) is str:
        text=unicode(text, message.in_encoding)
      stext+=text
    if self.connected_status is not None:
      self.connected_status.push(0, stext.strip().rstrip('-'))
    # get timesamp of current message
    timestr=strftime('%H:%M:%S')+str(time()%1)[1:5]
    if group is None or group=='reset':
      if not text==self.last_message and text is not None:
        #self.write(text+'\n')
        if group=='reset':
          self.treestore.append(self.active_group_iter, [text, '', timestr, bgcolor])
        else:
          self.treestore.append(None, ['', text, timestr, bgcolor])
      self.active_group=None
      self.active_group_iter=None
      self.active_item=None
      self.active_item_iter=None
      self.progress(progress)
    else:
      if item is None:
        if group==self.active_group:
          if not text==self.last_message and text is not None:
            self.treestore.append(self.active_group_iter, ['', text, timestr, bgcolor])

          self.progress(progress)
        else:
          self.active_group=group
          self.numitems=numitems
          self.item_count=0
          if not text==self.last_message and text is not None:
            if self.active_group_iter is None:
              self.active_group_iter=self.treestore.append(None,
                                                           [group, text, timestr, bgcolor])
            else:
              self.treestore.append(self.active_group_iter, ['', text, timestr, bgcolor])
          else:
            self.active_group_iter=self.treestore.append(None, [group, '', timestr, bgcolor])
          self.progress(progress)
      elif item==self.active_item:
        if not text==self.last_message and text is not None:
          self.treestore.append(self.active_item_iter, ['', text, timestr, bgcolor])
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(None)
      else:
        self.active_item=item
        self.item_count+=1
        if not text==self.last_message and text is not None:
          self.active_item_iter=self.treestore.append(self.active_group_iter,
                                                      [item, text, timestr, bgcolor])
        else:
          self.active_item_iter=self.treestore.append(self.active_group_iter,
                                                      [item, '', timestr, bgcolor])
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(100.*float(self.item_count-1)/self.numitems)
    # set color of group if error occured
    if self.active_group is not None:
      gcolor=self.treestore.get_value(self.active_group_iter, 3)
      if bgcolor=='#aaaaff' and gcolor=='#ffffff':
        self.treestore.set_value(self.active_group_iter, 3, bgcolor)
      elif bgcolor=='#ffaaaa' and gcolor!='#ffaaaa':
        self.treestore.set_value(self.active_group_iter, 3, bgcolor)
    # set color of item if error occured
    if self.active_item is not None:
      gcolor=self.treestore.get_value(self.active_item_iter, 3)
      if bgcolor=='#aaaaff' and gcolor=='#ffffff':
        self.treestore.set_value(self.active_item_iter, 3, bgcolor)
      elif bgcolor=='#ffaaaa' and gcolor!='#ffaaaa':
        self.treestore.set_value(self.active_item_iter, 3, bgcolor)
    self.last_message=text
    if self.active_item_iter is not None:
      path=self.treestore.get_path(self.active_item_iter)
    elif self.active_group_iter is not None:
      path=self.treestore.get_path(self.active_group_iter)
    else:
      return
    self.treeview.collapse_all()
    self.treeview.expand_to_path(path)
    self.treeview.scroll_to_cell(path)
    #while gtk.events_pending():
    # while loop too slow
    gtk.main_iteration(False)

  def info(self, message, group=None, item=None, numitems=1, progress=None):
    self._write(message, group, item, numitems, progress)

  def warn(self, message, group=None, item=None, numitems=1, progress=None):
    self._write(message, group, item, numitems, progress, bgcolor='#aaaaff')
    if self.popup_toggle.get_active():
      self.show()

  def error(self, message, group=None, item=None, numitems=1, progress=None):
    self._write(message, group, item, numitems, progress, bgcolor='#ffaaaa')
    self.show()

  def progress(self, progress):
    if progress is None:
      return
    fraction=progress/100.
    self.progressbar.set_fraction(fraction)
    self.progressbar.set_text("%i%%"%progress)
    if self.connected_progress is not None:
      self.connected_progress.set_fraction(fraction)
    while gtk.events_pending():
      gtk.main_iteration(False)
