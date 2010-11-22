# -*- encoding: utf-8 -*-
'''
  4circle GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
from time import time

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7RC1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class CircleGUI:
  '''
    GUI functions for the GTK toolkit
  '''

  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string='''
      <menu action='4CircleMenu'>
        <menuitem action='ReloadFile' />
        <menuitem action='Autoreload' />
        <menuitem action='ToggleCPS' />
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "4CircleMenu", None,                             # name, stock id
                "4 Circle", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
           ( "ReloadFile", None,                             # name, stock id
                "Reload File", "F5",                    # label, accelerator
                None ,                                   # tooltip
                self.reload_active_measurement ),
           ( "Autoreload", None,                             # name, stock id
                "Toggle Autoreload", None,                    # label, accelerator
                None ,                                   # tooltip
                self.autoreload_dataset ),
           ( "ToggleCPS", None,                             # name, stock id
                "Toggle CPS", None,                    # label, accelerator
                None ,                                   # tooltip
                self.toggle_cps ),
)
    return string,  actions

  def toggle_cps(self, action, window):
    '''
      Change couts to cps and vice verca.
    '''
    dataset=self.active_file_data[window.index_mess]
    if 'counts/s' in dataset.units():
      self.cps_to_counts(dataset)
    else:
      self.counts_to_cps(dataset)
    window.replot()

  def reload_active_measurement(self, action, window):
    '''
      Reload the data of the active file.
    '''
    new_data=self.read_file(self.active_file_name)
    for i, dataset in enumerate(new_data):
      if i<len(self.active_file_data):
        self.active_file_data[i].data=dataset.data
      else:
        self.active_file_data.append(dataset)
    index=window.index_mess
    window.change_active_file_object((self.active_file_name, self.file_data[self.active_file_name]))    
    window.index_mess=index
    window.replot()
  
  def autoreload_dataset(self, action, window):
    '''
      Enter a mode where the active measurement is automatically reloaded onece per second.
    '''
    if self.autoreload_active:
      print "Deactivate Autoreload"
      self.autoreload_active=False
    else:
      print "Activate Autoreload"
      self.autoreload_active=True
      while self.autoreload_active:
        last=time()
        self.reload_active_measurement(action, window)
        while (time()-last)<1.:
          gtk.main_iteration()

  