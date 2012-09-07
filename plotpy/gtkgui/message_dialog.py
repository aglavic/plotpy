'''
  GUI replacement for the default command line messenger.
'''

import os
import sys
import gtk
from plotpy import message

def connect_stdout_dialog():
  '''
    Replace sys.stdout with a dialog window.
    
    :return: The dialog window.
  '''
  status_dialog=GUIMessenger('Messages')
  status_dialog.connect('response', lambda*ignore: status_dialog.hide())
  status_dialog.set_default_size(500, 400)
  status_dialog.show_all()
  status_dialog.move(0, 0)
  status_dialog.fileno=lambda : 1
  status_dialog.flush=lambda : True
  sys.stdout=status_dialog
  return status_dialog

class GUIMessenger(gtk.Dialog):
  '''
    Messenger which does not raise any errors and goups output
    according to the group and item scheme. Progress is
    indicated independent of output as last line in the 
    console.
  '''
  active_group=None
  active_item=None
  last_message=None
  numitems=1
  item_count=0

  def __init__(self, title, progressbar=None, statusbar=None, parent=None,
               flags=0, buttons=None, initial_text=''):
    gtk.Dialog.__init__(self, parent=parent, title=title)
    gtk.Dialog.__init__(self, title, parent, flags, buttons)
    self.textview=gtk.TextView()
    self.buffer=self.textview.get_buffer()
    self.buffer.set_text(initial_text)
    # attach the textview inside a scrollbar widget
    self.scrollwidget=gtk.ScrolledWindow()
    self.scrollwidget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.scrollwidget.add(self.textview)
    self.scrollwidget.show()
    self.textview.show()
    self.vbox.add(self.scrollwidget)
    self.end_iter=self.buffer.get_end_iter()
    self.end_mark=self.buffer.create_mark('End', self.end_iter, False)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logogreen.png").replace('library.zip', ''))
    # Progressbar
    self.progressbar=gtk.ProgressBar()
    self.progressbar.show()
    self.connected_progress=progressbar
    self.connected_status=statusbar
    self.vbox.pack_end(self.progressbar, False)
    self.connect('delete-event', self._no_destroy)
    message.messenger=self

  def _no_destroy(self, widget, data=None):
    '''
      Make sure the window is not destoryed when it gets closed.
    '''
    self.hide()
    return True

  def write(self, text):
    '''
      Append a string to the buffer and scroll at the end, if it was visible before.
    '''
    if type(text) is not unicode:
      utext=unicode(text, encoding=sys.stdin.encoding, errors='ignore')
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
    if self.connected_status is not None:
      self.connected_status.push(0, text.strip())
    self.buffer.insert(self.end_iter, utext)
    if end_visible:
      self.textview.scroll_to_mark(self.end_mark, 0.)
    while gtk.events_pending():
      gtk.main_iteration(False)

  def _write(self, message=None, group=None, item=None, numitems=1, progress=None):
    if group is None:
      self.active_group=None
      self.active_item=None
      if not message==self.last_message and message is not None:
        self.write(message+'\n')
      self.progress(progress)
    elif group=='reset':
      self.active_group=None
      self.active_item=None
      if not message==self.last_message and message is not None:
        self.write(message+'\n')
      self.progress(progress)
    else:
      if item is None:
        if group==self.active_group:
          if not message==self.last_message and message is not None:
            self.write('    '+message+'\n')
          self.progress(progress)
        else:
          self.active_group=group
          self.numitems=numitems
          self.item_count=0
          self.write(group+':\n')
          if not message==self.last_message and message is not None:
            self.write('    '+message+'\n')
          self.progress(progress)
      elif item==self.active_item:
        if not message==self.last_message and message is not None:
          self.write('        '+message+'\n')
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(None)
      else:
        self.active_item=item
        self.item_count+=1
        self.write('    '+item+'\n')
        if not message==self.last_message and message is not None:
          self.write('        '+message+'\n')
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(100.*float(self.item_count-1)/self.numitems)
    self.last_message=message

  def info(self, message, group=None, item=None, numitems=1, progress=None):
    self._write(message, group, item, numitems, progress)

  def warn(self, message, group=None, item=None, numitems=1, progress=None):
    message='WARNING '+message
    self._write(message, group, item, numitems, progress)

  def error(self, message, group=None, item=None, numitems=1, progress=None):
    message='ERROR '+message
    self._write(message, group, item, numitems, progress)

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
