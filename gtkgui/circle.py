# -*- encoding: utf-8 -*-
'''
  4circle GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
from time import time, sleep

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.2"
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
        <menuitem action='FitCentral' />
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
                "Toggle Autoreload", "<control>F5",                    # label, accelerator
                None ,                                   # tooltip
                self.autoreload_dataset ),
           ( "ToggleCPS", None,                             # name, stock id
                "Toggle CPS", None,                    # label, accelerator
                None ,                                   # tooltip
                self.toggle_cps ),
           ( "FitCentral", None,                             # name, stock id
                "Fit Central Peak", '<control><shift>F',                    # label, accelerator
                None ,                                   # tooltip
                self.fit_central_peak ),
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
          gtk.main_iteration(False)
        sleep(0.1)

  def fit_central_peak(self, action, window):
    '''
      Fit a peak at the center of a scan with Voigt-profile.
    '''
    window.file_actions.activate_action('create_fit_object')
    window.file_actions.activate_action('add_function', 'Voigt',)
    dataset=window.measurement[window.index_mess]
    x0=float(dataset.x.mean())
    I0=float(dataset.y.max())
    sigma0=float((dataset.x.max()-dataset.x.min())/10.)
    window.file_actions.activate_action('set_function_parameters', 
                                        0, [I0, 
                                             x0, 
                                             sigma0, 
                                             sigma0, 
                                             0.0, 
                                             None, 
                                             None, 
                                             'I=[I] x_0=[x0] \xcf\x83=[\xcf\x83|2] \xce\xb3=[\xce\xb3|2]'])
    window.file_actions.activate_action('fit_functions')
    window.file_actions.activate_action('simmulate_functions')
    window.replot()
