# -*- encoding: utf-8 -*-
'''
  4circle GTK GUI class.
'''

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import os
import gobject
from time import sleep
from threading import Thread
import dialogs
from plotpy import  fitdata
from plotpy.mds import MeasurementData, PhysicalProperty

#----------------------- importing modules --------------------------


class CircleGUI:
  '''
    GUI functions for the GTK toolkit
  '''
  autoreload_thread=None

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
            ("4CircleMenu", None, # name, stock id
                "4 Circle", None, # label, accelerator
                None, # tooltip
                None),
           ("ReloadFile", None, # name, stock id
                "Reload File", "F5", # label, accelerator
                None , # tooltip
                self.reload_active_measurement),
           ("Autoreload", None, # name, stock id
                "Toggle Autoreload", "<control>F5", # label, accelerator
                None , # tooltip
                self.autoreload_dataset),
           ("ToggleCPS", None, # name, stock id
                "Toggle CPS", None, # label, accelerator
                None , # tooltip
                self.toggle_cps),
           ("FitPositions", None, # name, stock id
                "Fit Θ2Θ-scan positions", '<control><shift>F', # label, accelerator
                None , # tooltip
                self.fit_positions),
)
    return string, actions

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
    if window is None:
      window=self._window
    if hasattr(self.active_file_data[-1], 'last_import'):
      if self.active_file_data[-1].last_import>=os.path.getmtime(self.active_file_name):
        return
    new_data=self.read_file(self.active_file_name)
    for i, dataset in enumerate(new_data):
      self.counts_to_cps(dataset)
      if i<len(self.active_file_data):
        self.active_file_data[i].data=dataset.data
      else:
        self.active_file_data.append(dataset)
    self.active_file_data[-1].last_import=os.path.getmtime(self.active_file_name)
    window.replot(echo=False)
    window.statusbar.push(0, 'Filedata Updated')

  def autoreload_dataset(self, action, window):
    '''
      Enter a mode where the active measurement is automatically reloaded onece per second.
    '''
    if self.autoreload_active:
      print "Deactivate Autoreload"
      self.autoreloader_off()
    else:
      print "Activate Autoreload"
      self.autoreload_active=True
      if self.autoreload_thread is not None:
        self.autoreloader_off()
      self._window=window
      self.autoreload_thread=Thread(target=self.autoreloader)
      self.autoreload_thread.start()
      if not self.autoreloader_off in window.active_threads:
        window.active_threads.append(self.autoreloader_off)

  def autoreloader_off(self):
    if self.autoreload_thread is not None:
      self.autoreload_active=False
      self.autoreload_thread.join()
      self.autoreload_thread=None

  def autoreloader(self):
    '''
      Function called as new thread to check if the file changed.
    '''
    last_change=os.path.getmtime(self.active_file_name)
    while self.autoreload_active:
      if last_change!=os.path.getmtime(self.active_file_name):
        gobject.idle_add(self.reload_active_measurement, None, None)
        last_change=os.path.getmtime(self.active_file_name)
      sleep(0.1)

  def fit_positions(self, action, window):
    '''
      Fit a peak at the center of a scan with Voigt-profile.
    '''
    dataset=self.active_file_data[window.index_mess]
    # remove earlier fits
    dataset.fit_object=None
    window.file_actions.activate_action('create_fit_object')
    if dataset.x.dimension=='h':
      dataset.xdata=dataset.dimensions().index('Q_x')
      window.replot()
    if dataset.x.dimension=='k':
      dataset.xdata=dataset.dimensions().index('Q_y')
      window.replot()
    if dataset.x.dimension=='l':
      dataset.xdata=dataset.dimensions().index('Q_z')
      window.replot()
    dialog=dialogs.MultipeakDialog(fitdata.FitCuK,
                                   dataset.fit_object,
                                   window,
                                   title='Crystal Diffraction Peaks...',
                                   startparams=[1, 0, 0.00125, 0.001, 0, 2, 0.99752006],
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
      th_correction=fitdata.ThetaCorrection([y[0]/x[0], 0.])
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
      divs=[abs(pos-(positions[0]/i*id_)) for pos, id_ in zip(positions[1:], ids)]
      if sum(divs)/(len(positions)-1.)<(0.25/i):
        break
    return [round(pos/(positions[0]/i)) for pos in positions]
