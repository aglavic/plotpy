#-*- coding: utf8 -*-
'''
  Drag and drop handling for the gui.
'''

import gtk

class ImageDND(object):
  '''
    Handling of Drag&Drop for the main image.
  '''
  _rec_targets=[
            ("text/plain", 0, 1),
            ]
  _send_targets=[
            ("text/plain", 0, 1),
            ]

  def __init__(self, main_window):
    self.main_window=main_window
    # activate DnD for the image
    # set up drop for file import
    self.main_window.image.drag_dest_set(gtk.DEST_DEFAULT_MOTION|
                                         gtk.DEST_DEFAULT_HIGHLIGHT|
                                         gtk.DEST_DEFAULT_DROP,
                                         self._rec_targets,
                                         gtk.gdk.ACTION_COPY)
    self.main_window.image.connect("drag_data_received", self.receive_data)

  ### Destinatione event handling  ###

  def receive_data(self, widget, context, x, y, selection, targetType, time):
    '''
      Extract the file names and import the files.
    '''
    if context.get_source_widget() is not None:
      return
    items=selection.get_text().strip().split('\n')
    file_names=[item.split('file://')[1] for item in items if item.startswith('file://')]
    self.main_window.add_file(file_names=file_names)

  ### Source event handling ###

  def set_drag_icon(self, widget, drag_context, data):
    '''
      Set up the drag icon.
    '''
    widget.drag_source_set_icon_pixbuf(self.main_window.image.get_pixbuf())

  def send_data(self, widget, context, selection, targetType, eventTime):
    '''
      Drag the image to a folder.
    '''
    selection.set(selection.target, 8, 'ABC')
