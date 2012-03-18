# -*- encoding: utf-8 -*-
'''
  Widgets for multiplot storage and displaying.
'''

import os
import gtk
from plot_script.measurement_data_structure import MultiplotList
from dialogs import PreviewDialog
from copy import deepcopy

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"


class MultiplotItem(gtk.HBox):
  '''
    A list which contains all subplots for a multiplot.
  '''

  def __init__(self, items=None):
    gtk.HBox.__init__(self)
    if items is None:
      items=MultiplotList()
    self.items=items
    label=gtk.Label('   File:   \n   Info:   ')
    label.show()
    self._labels=[]
    self.add(label)
    for item in items:
      self.append(item, just_labels=True)

  def __getitem__(self, index):
    return self.items[index]

  def append(self, item, just_labels=False):
    '''
      Add a dataset to the list of items.
      The dataset gets copied to make it possible
      to change plot settings and columns multiplot specific.
    '''
    dataset, name=item
    name=os.path.split(name)[1]
    if not just_labels:
      oldfit=dataset.fit_object
      dataset.fit_object=None
      self.items.append((deepcopy(dataset), name))
      dataset.fit_object=oldfit
    label=gtk.Label('%s\n%s'%(name, dataset.short_info))
    label.show()
    self._labels.append(label)
    self.add(label)

  def update_labels(self):
    '''
      Redefine the labels for all datasets.
    '''
    labels=self._labels
    for i, item in enumerate(self.items):
      labels[i].set_text('%s\n%s'%(os.path.split(item[1])[1],
                                item[0].short_info))

  def index(self, item):
    return self.items.index(item)

  def pop(self, index):
    item=self.items[index]
    self.remove(item)
    return item

  def __contains__(self, item):
    return item in self.items

  def remove(self, item):
    index=self.items.index(item)
    children=self._labels
    gtk.HBox.remove(self, children[index])
    self.items.remove(item)
    self._labels.pop(index)

  def reorder_child(self, child, position):
    '''
      Change the order of the MultiplotList and the displayed
      items.
    '''
    index=self.items.index(child)
    label=self._labels.pop(index)
    self._labels.insert(position-1, label)
    item=self.items.pop(index)
    self.items.insert(position-1, item)
    gtk.HBox.reorder_child(self, label, position)

  def clear(self):
    for ignore in range(len(self.items)):
      self.pop(0)



class MultiplotCanvas(gtk.Table):
  '''
    A list of MultiplotItem objects with buttons to select one
    and additional options.
  '''
  button_group=None
  active_mp=None

  def __init__(self, parent):
    self.parent_gui=parent
    gtk.Table.__init__(self, 2, 2, False)
    self.multiplots=[]
    self.item_tables=[]
    self.selectors=[]
    self.item_box=gtk.VBox()
    self.item_box.show()
    self.attach(self.item_box,
                0, 2, 1, 2,
                gtk.EXPAND|gtk.FILL, gtk.EXPAND, gtk.FILL)
    self.new_item()

  def new_item(self, items=None):
    '''
      Add a new MultiplotItem to the list.
    '''
    newitem=MultiplotItem(items=items)
    self.active_mp=newitem
    self.multiplots.append(newitem)
    table=gtk.Table(1, 4, False)
    self.item_tables.append(table)
    selector=gtk.RadioButton(group=self.button_group, label='')
    self.selectors.append(selector)
    selector.set_active(True)
    selector.connect('toggled', self.select, newitem)
    self.button_group=selector
    delbutton=gtk.Button("Delete")
    delbutton.connect('clicked', self.delete_item, table)
    addbutton=gtk.Button("Sort/Add")
    addbutton.connect('clicked', self.sort_add, newitem)

    table.show()
    newitem.show()
    selector.show()
    addbutton.show()
    delbutton.show()
    table.attach(selector,
                0, 1, 0, 1,
                0, 0)
    table.attach(newitem,
                3, 4, 0, 1,
               gtk.EXPAND|gtk.FILL, 0)
    table.attach(delbutton,
                2, 3, 0, 1,
                0, 0)
    table.attach(addbutton,
                1, 2, 0, 1,
                0, 0)
    self.item_box.add(table)

  def select_item(self, index):
    '''
      Define the active selection.
    '''
    self.selectors[index].set_active(True)

  def _get_item_index(self):
    for i, selector in enumerate(self.selectors):
      if selector.get_active():
        return i

  item_index=property(_get_item_index, select_item)

  def __len__(self):
    return len(self.items.items)

  def select(self, button, item):
    if button.get_active():
      self.active_mp=item

  def delete_item(self, button, table):
    self.item_box.remove(table)
    index=self.item_tables.index(table)
    self.item_tables.pop(index)
    self.multiplots.pop(index)
    selector=self.selectors.pop(index)
    if len(self.multiplots)==0:
      self.new_item()
    elif selector.get_active():
      self.selectors[0].set_active(True)

  def clear(self, refill=True):
    for table in self.item_tables:
      self.item_box.remove(table)
    self.item_tables=[]
    self.selectors=[]
    self.multiplots=[]
    if refill:
      self.new_item()

  def append(self, dataset):
    try:
      self.items.append(dataset)
      self.update_labels()
      return True
    except ValueError:
      return False

  def __contains__(self, item):
    return item in self.items

  def __getitem__(self, item):
    self.update_labels()
    return self.items.items[item]

  def __iter__(self):
    self.update_labels()
    return self.items.items.__iter__()

  def remove(self, item):
    self.items.remove(item)
    self.update_labels()

  def _get_item(self):
    self.update_labels()
    return self.active_mp

  def _get_title(self):
    return self.items.items.title

  def _set_title(self, newtitle):
    self.items.items.title=newtitle

  def _get_sample_name(self):
    return self.items.items.sample_name

  def _set_sample_name(self, newname):
    self.items.items.sample_name=newname

  def _get_plot_options(self):
    return self.items.items[0][0].plot_options

  def _set_plot_options(self, options):
    self.items.items[0][0].plot_options=options

  items=property(_get_item)
  title=property(_get_title, _set_title)
  sample_name=property(_get_sample_name, _set_sample_name)
  plot_options=property(_get_plot_options, _set_plot_options)

  def sort_add(self, ignore=None, items=None):
    if items is None:
      items=self.items
      do_replot=True
    else:
      do_replot=(items==self.items)
    dialog=ItemSortAdd(items, self.parent_gui, do_replot=do_replot)
    if do_replot:
      self.parent_gui.frame1.set_current_page(0)
      if not self.parent_gui.active_multiplot:
        self.parent_gui.active_multiplot=True
        self.parent_gui.replot()
    dialog.run()
    dialog.destroy()

  def update_labels(self):
    '''
      Reload all labels of all MultiplotItem objects.
    '''
    for item in self.multiplots:
      item.update_labels()

  def get_list(self):
    '''
      Return a list of MultiplotList objects.
    '''
    return [item.items for item in self.multiplots]

  def new_from_list(self, items_list):
    '''
      Clear all multiplots and creat new ones from a list of items.
    '''
    if len(items_list)==0:
      return
    self.clear(refill=False)
    for items in items_list:
      self.new_item(items=items)

class ItemSortAdd(gtk.Dialog):
  '''
    A dialog to sort a MultiplotItem list or add new items.
  '''

  def __init__(self, items, parent, do_replot=True):
    gtk.Dialog.__init__(self, title='Sort Multiplot List...',
                        buttons=('Add...', 2, 'Exit', 0))
    self.parent_gui=parent
    self.items=items
    self._do_replot=do_replot
    self._item_list=[]
    self._init_entries()

  def run(self):
    result=1
    while result>0:
      result=gtk.Dialog.run(self)
      if result==2:
        pd=PreviewDialog(self.parent_gui.active_session.file_data,
                         show_previews=False, single_selection=False,
                         buttons=('OK', 1, 'Cancel', 0))
        pd.set_default_size(800, 600)
        result=pd.run()
        if result:
          items=pd.get_active_objects_with_key()
          for name, dataset in items:
            self.items.append([dataset, os.path.split(name)[1]])
            self._add_item(self.items[-1])
          if self._do_replot:
            self.parent_gui.replot()
        pd.destroy()
    return result

  def _init_entries(self):
    for item in self.items.items:
      self._add_item(item)

  def _add_item(self, item):
    hbox=gtk.HBox()
    hbox.show()
    self.vbox.add(hbox)
    #self._item_list.append(hbox)
    up=gtk.Button('↑')
    up.connect('clicked', self._move_item, hbox,-1)
    up.show()
    hbox.pack_start(up, expand=False)
    down=gtk.Button('↓')
    down.connect('clicked', self._move_item, hbox,+1)
    down.show()
    hbox.pack_start(down, expand=False)
    delbutton=gtk.Button('del')
    delbutton.connect('clicked', self._delete_item, hbox)
    delbutton.show()
    hbox.pack_start(delbutton, expand=False)
    label=gtk.Label(item[1])
    label.show()
    hbox.pack_start(label, expand=False)
    entry=gtk.Entry()
    entry.set_text(item[0].short_info)
    #entry.set_width_chars(20)
    entry.show()
    entry.connect("activate", self._change_info, item[0])
    hbox.pack_end(entry, expand=True)

  def _move_item(self, button, hbox, direction):
    index=self.vbox.get_children().index(hbox)
    if (index+direction)<0 or (index+direction)>=len(self.vbox.get_children()):
      return
    self.vbox.reorder_child(hbox, index+direction+1)
    item=self.items[index]
    self.items.reorder_child(item, index+direction+1)
    if self._do_replot:
      self.parent_gui.replot()

  def _delete_item(self, button, hbox):
    index=self.vbox.get_children().index(hbox)
    self.vbox.remove(hbox)
    self.items.pop(index)
    if self._do_replot:
      self.parent_gui.replot()

  def _change_info(self, entry, dataset):
    dataset.short_info=entry.get_text()
    if self._do_replot:
      self.parent_gui.replot()
