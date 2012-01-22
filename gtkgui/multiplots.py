# -*- encoding: utf-8 -*-
'''
  Widgets for multiplot storage and displaying.
'''

import os
import gtk
from measurement_data_structure import MultiplotList

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__
__status__="Development"


class MultiplotItem(gtk.Table):
  '''
    A list which contains all subplots for a multiplot.
  '''

  def __init__(self, items=None):
    gtk.Table.__init__(self, 1, 1, False)
    if items is None:
      items=MultiplotList()
    self.items=items
    label=gtk.Label('   File:   \n   Info:   ')
    label.show()
    self._labels=[label]
    self.attach(label, 0, 1, 0, 1, 0, 0)

  def append(self, item):
    '''
      Add a dataset to the list of items.
    '''
    self.items.append(item)
    idx=len(self.items)
    label=gtk.Label('%s\n%s'%(os.path.split(item[1])[1],
                                item[0].short_info))
    label.show()
    self._labels.append(label)
    self.attach(label,
                idx, idx+1, 0, 1,
                0, 0)

  def index(self, item):
    return self.items.index(item)

  def clear(self):
    '''
      Remove all datasets from the list.
    '''
    pass

  def pop(self, index):
    items=self.get_children()

  def __contains__(self, item):
    return item in self.items

  def remove(self, item):
    index=self.items.index(item)
    children=self._labels
    move=children[index+2:]
    for label in children[index+1:]:
      gtk.Table.remove(self, label)
    for i, label in enumerate(move):
      self.attach(label,
                index+i+1, index+i+2, 0, 1,
                0, 0)
    self.items.remove(item)
    self._labels.pop(index+1)


class MultiplotCanvas(gtk.Table):
  '''
    A list of MultiplotItem objects with buttons to select one
    and additional options.
  '''
  button_group=None
  active_mp=None

  def __init__(self):
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

  def new_item(self):
    newitem=MultiplotItem()
    self.active_mp=newitem
    self.multiplots.append(newitem)
    table=gtk.Table(1, 3, False)
    self.item_tables.append(table)
    selector=gtk.RadioButton(group=self.button_group, label='')
    self.selectors.append(selector)
    selector.set_active(True)
    selector.connect('toggled', self.select, newitem)
    self.button_group=selector
    delbutton=gtk.Button("Delete")
    delbutton.connect('clicked', self.delete_item, table)

    table.show()
    newitem.show()
    selector.show()
    delbutton.show()
    table.attach(selector,
                0, 1, 0, 1,
                0, 0)
    table.attach(newitem,
                2, 3, 0, 1,
               gtk.EXPAND|gtk.FILL, 0)
    table.attach(delbutton,
                1, 2, 0, 1,
                0, 0)
    self.item_box.add(table)

  def select_item(self, index):
    self.selectors[index].set_active(True)

  def _get_item_index(self):
    for i, selector in enumerate(self.selectors):
      if selector.get_active():
        return i

  item_index=property(_get_item_index, select_item)

  def __len__(self):
    return len(self.multiplots)

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

  def clear(self):
    for table in self.item_tables:
      self.item_box.remove(table)
    self.item_tables=[]
    self.selectors=[]
    self.multiplots=[]

  def append(self, dataset):
    try:
      self.items.append(dataset)
      return True
    except ValueError:
      return False

  def __contains__(self, item):
    return item in self.items

  def __getitem__(self, item):
    return self.items.items[item]

  def __iter__(self):
    return self.items.items.__iter__()

  def remove(self, item):
    self.items.remove(item)

  def _get_item(self):
    return self.active_mp

  def _get_title(self):
    return self.items.items.title

  def _set_title(self, newtitle):
    self.items.items.title=newtitle

  def _get_sample_name(self):
    return self.items.items.sample_name

  def _set_sample_name(self, newname):
    self.items.items.sample_name=newname

  items=property(_get_item)
  title=property(_get_title, _set_title)
  sample_name=property(_get_sample_name, _set_sample_name)

  def clear(self):
    pass



