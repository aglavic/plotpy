# -*- encoding: utf-8 -*-
'''
  4circle GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import os
import gtk
from time import time, sleep
import dialogs
import fit_data
from measurement_data_structure import MeasurementData, PhysicalProperty, PhysicalConstant

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.8.4"
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
        <menuitem action='FitPositions' />
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
           ( "FitPositions", None,                             # name, stock id
                "Fit Θ2Θ-scan positions", '<control><shift>F',                    # label, accelerator
                None ,                                   # tooltip
                self.fit_positions ),
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
    if hasattr(self.active_file_data[-1], 'last_import'):
      if self.active_file_data[-1].last_import>=os.path.getctime(self.active_file_name):
        return
    new_data=self.read_file(self.active_file_name)
    for i, dataset in enumerate(new_data):
      if i<len(self.active_file_data):
        self.active_file_data[i].data=dataset.data
      else:
        self.active_file_data.append(dataset)
    self.active_file_data[-1].last_import=os.path.getctime(self.active_file_name)
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
        while gtk.events_pending():
          gtk.main_iteration(False)
        sleep(0.1)

  def fit_positions(self, action, window):
    '''
      Fit a peak at the center of a scan with Voigt-profile.
    '''
    dataset=self.active_file_data[window.index_mess]
    if dataset.fit_object is None:
      window.file_actions.activate_action('create_fit_object')
    if dataset.x.dimension=='h':
      dataset.xdata=dataset.dimensions().index('q_x')
      window.replot()
    if dataset.x.dimension=='k':
      dataset.xdata=dataset.dimensions().index('q_y')
      window.replot()
    if dataset.x.dimension=='l':
      dataset.xdata=dataset.dimensions().index('q_z')
      window.replot()
    dialog=dialogs.MultipeakDialog(fit_data.FitCuK, 
                                   dataset.fit_object, 
                                   window, 
                                   title='Crystal Diffraction Peaks...', 
                                   startparams=[1,0, 0.00125,0.001,0,2,0.99752006],
                                   fitwidth=0.1, 
                                   fitruns=[[0, 1], [0, 1, 3, 4]],
                                   )
    window.open_windows.append(dialog)
    positions, result=dialog.run()
    if result and len(positions)>=2:
      peak_data=MeasurementData()
      indices=self._get_indices([position[0] for position in positions])
      x=PhysicalProperty('Index', '', indices)
      y=PhysicalProperty('Peak Position', dataset.x.unit, [position[0] for position in positions], 
                                                          [position[1] for position in positions])
      p=PhysicalProperty('Peak Intensities', dataset.y.unit, [position[2] for position in positions], 
                                                            [position[3] for position in positions])
      peak_data.data=[x, y, p]
      peak_data.sample_name=dataset.sample_name
      peak_data.short_info=' - Fitted Peak Positions'
      window.index_mess+=1
      peak_data.number=str(window.index_mess)
      self.active_file_data.insert(window.index_mess, peak_data)
      window.file_actions.activate_action('create_fit_object')
      th_correction=fit_data.ThetaCorrection([y[0]/x[0], 0.])
      peak_data.fit_object.functions.append([th_correction, True, True, False, False])
      peak_data.fit_object.fit()
      peak_data.fit_object.simulate()
      peak_data.plot_options.xrange=[0., x[-1]+1]
      peak_data.plot_options.yrange[0]=0.
      window.replot()

  def _get_indices(self, positions):
    '''
      Estimate the indices for peaks where only the positions are given
    '''
    for i in range(1, 20):
      ids=[round(pos/(positions[0]/i)) for pos in positions[1:]]
      divs=[abs(pos-(positions[0]/i*id)) for pos, id in zip(positions[1:], ids)]
      if sum(divs)/(len(positions)-1.)<(0.25/i):
        break
    return [round(pos/(positions[0]/i)) for pos in positions]
