# -*- encoding: utf-8 -*-
'''
  classes for reflectometer sessions and fits with fit.f90
'''
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -import uxd files                                                                             #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -complete GUI control over the fit program                                                    #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import buildin modules
import os
import sys
import math
import subprocess
import gtk
import time
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# import parameter class for fits
from reflectometer_fit.parameters import FitParameters, LayerParam, MultilayerParam
import reflectometer_fit.functions
# importing preferences and data readout
import read_data.reflectometer
import config.reflectometer
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class FitList(list):
  '''
    Class to store the fit parameters together with the list of MeasurementData objects.
  '''
  
  def __init__(self, *args):
    list.__init__(self, *args)
    self.fit_object=RefFitParameters() 
    self.fit_object_history=[]
    self.fit_object_future=[]

class ReflectometerSession(GenericSession):
  '''
    Class to handle reflectometer data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
  '''
  \tReflectometer-Data treatment:
  \t-counts\t\tShow actual counts, not counts/s
  \t-fit [layers] [thicknesses] [est._roughness]
  \t\t\t\tExport measurements for use with fit programm by Emmanuel Kentzinger and create .ent file for it.
  \t\t\t\tlayers is a list of layers with format L1-L2-L3-S or 5[L1_L2]-S, where L,S are the names
  \t\t\t\tof the compounds of the layers and substrate as provided in config.scattering_length_table.py
  \t\t\t\tthicknesses is a list of layer thicknesses with format LT1-LT2-LT3 or [LT1_LT2] in A
  \t\t\t\test._roughness is the estimated overall roughness to begin with
  \t-ref\t\tTry to refine the scaling factor, background and roughnesses.
  '''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('reflectometer (.UXD)','*.[Uu][Xx][Dd]'), ('gziped (.UXD.gz)','*.[Uu][Xx][Dd].gz'), ('All','*'))  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['fit', 'ref']
  #options:
  show_counts=False # dont convert to conts/s
  export_for_fit=False # make the changes needed for the fit program to work
  try_refine=False # try to refine scaling and roughnesses
  logy=True # standard reflectometer view is logarithmic
  x_from=0.005 # fit only x regions between x_from and x_to
  x_to=''
  max_iter=50 # maximal iterations in fit
  max_alambda=10 # maximal power of 10 which alamda should reach in fit.f90
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.RESULT_FILE=config.reflectometer.RESULT_FILE
    self.DATA_COLUMNS=config.reflectometer.DATA_COLUMNS # read data columns from preferences
    self.TRANSFORMATIONS=config.reflectometer.TRANSFORMATIONS # read TRANSFORMATIONS from preferences
    GenericSession.__init__(self, arguments)
    #for key in self.file_data.keys():
    #  self.file_data[key]=FitList(self.file_data[key])
    try:
      self.active_file_data=self.file_data[self.active_file_name]
    except KeyError:
      self.active_file_data=[]
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for reflectometer sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      if last_argument_option[0]:
        if last_argument_option[1]=='fit':
          self.export_for_fit=True
          self.fit_layers=argument
          last_argument_option=[True,'fit2']
        elif last_argument_option[1]=='fit2':
          self.fit_thicknesses=argument
          last_argument_option=[True,'fit3']
        elif last_argument_option[1]=='fit3':
          self.fit_est_roughness=float(argument)
          last_argument_option=[False,'']
      # Cases of arguments:
      elif argument=='-counts':
        self.show_counts=True
      elif argument=='-ref':
        self.try_refine=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      function to read data files
    '''
    return read_data.reflectometer.read_data(file_name,self.DATA_COLUMNS)
  
  def create_menu(self):
    '''
      create a specifig menu for the Reflectometer session
    '''
    # Create XML for squid menu
    string='''
      <menu action='ReflectometerMenu'>
        <menuitem action='ReflectometerFit'/>
        <menuitem action='ReflectometerExport'/>
        <menuitem action='ReflectometerImport'/>
        <separator name='Reflectometer1'/>
        <menuitem action='ReflectometerCombineScans'/>
        <menuitem action='ReflectometerCreateMap'/>
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "ReflectometerMenu", None,                             # name, stock id
                "Reflectometer", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "ReflectometerFit", None,                             # name, stock id
                "Fit...", "<control><shift>F",                    # label, accelerator
                None,                                   # tooltip
                self.fit_window ),
            ( "ReflectometerExport", None,                             # name, stock id
                "Export Fit Parameters...", None,                    # label, accelerator
                None,                                   # tooltip
                self.export_fit_dialog ),
            ( "ReflectometerImport", None,                             # name, stock id
                "Import Fit Parameters...", None,                    # label, accelerator
                None,                                   # tooltip
                self.import_fit_dialog ),
            ( "ReflectometerCombineScans", None,                             # name, stock id
                "Calculate Combination of Different Scans...", None,                    # label, accelerator
                None,                                   # tooltip
                self.combine_scans ),
            ( "ReflectometerCreateMap", None,                             # name, stock id
                "Create 3d Map from Rocking Scans", None,                    # label, accelerator
                None,                                   # tooltip
                self.combine_th_scans ),
             )
    return string,  actions
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to GenericSession counts per second
      corrections and fitting are performed here, too.  
    '''
    datasets=GenericSession.add_file(self, filename, append)
    #refinements=[]
    for dataset in datasets:
      self.time_col=1
      th=0
      twoth=0
      phi=0       
      for line in dataset.info.splitlines():
        strip=line.split('=')
        if strip[0]=='STEPTIME':
          self.time_col=float(strip[1])
        if strip[0]=='THETA':
          th=float(strip[1])
        if strip[0]=='2THETA':
          twoth=float(strip[1])
        if strip[0]=='PHI':
          phi=float(strip[1])
      if not self.show_counts:
        self.units=dataset.units()
        dataset.process_function(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      dataset.short_info=' started at Θ='+str(round(th,4))+' 2Θ='+str(round(twoth,4))+' φ='+str(round(phi,4))
      if self.export_for_fit: # export fit files
        self.export_fit(dataset,  filename)
        simu=read_data.reflectometer.read_simulation(self.TEMP_DIR+'fit_temp.sim')
        simu.number='sim_'+dataset.number
        simu.short_info='simulation'
        simu.sample_name=dataset.sample_name
        #refinements.append(simu)
        dataset.plot_together=[dataset, simu]
    # TODO: GUI selection to show only data or fit
    #if self.export_for_fit: # export fit files
     # self.add_data(refinements, filename+"_simulation")
    return datasets

  def add_data(self, data_list, name, append=True):
    '''
      Function which ither adds file data to the object or replaces
      all data by a new dictionary.
    '''
    if not append:
      self.file_data={}
    self.file_data[name]=FitList(data_list)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def counts_to_cps(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    for i,unit in enumerate(self.units): 
  # selection of the columns for counts
      if unit=='counts':
        counts_column.append(i)
    for counts in counts_column:
      output_data[counts]=output_data[counts]/self.time_col # calculate the cps
    return output_data
  
  def combine_th_scans(self, action, window):
    '''
      Create an alpha_i vs. alpha_f map of all Theta scans in the active data list.
    '''
    created_map=MeasurementData([['2Θ', '°'], 
                                 ['Θ', '°'],
                                 ['α_i', '°'], 
                                 ['α_f', '°'], 
                                 ['intensity', 'counts/s'], 
                                 ['error', 'counts/s']
                                 ], [], 2, 3, 5, 4)
    for dataset in self.active_file_data:
      if "DRIVE='THETA'" in dataset.info:
        two_theta=float(dataset.info.split('2THETA=')[1].split("\n")[0])
        for point in dataset:
          created_map.append([two_theta, point[0], point[0], two_theta-point[0], point[1], point[2]])
    self.active_file_data.append(created_map)
    window.index_mess=len(self.active_file_data)-1
    window.replot()
    window.logz.set_active(True)
  

  def combine_scans(self, action, window, preset=None):
    '''
      Add or substract measured scans from each other.
    '''
    # build a list of MeasurementData objects in active_file_data for the scans
    file_list=[object[0] for object in self.file_data.items()]
    file_list.remove(self.active_file_name)
    file_list.insert(0, self.active_file_name)
    scan_list=[]
    for file in file_list:
      scan_list+=[(object, file, i) for i, object in enumerate(self.file_data[file])]
    combine_list=[]
    def add_object():
      '''Subdialog to add one chanel to the separation.'''
      add_dialog=gtk.Dialog(title='Add scan:')
      add_dialog.set_default_size(100,50)
      add_dialog.add_button('OK', 1)
      add_dialog.add_button('Cancle', 0)
      align_table=gtk.Table(4,1,False)
      label=gtk.Label('sign: ')
      align_table.attach(label, 0,1, 0, 1, 0,0, 0,0);
      sign=gtk.Entry()
      sign.set_text('+')
      align_table.attach(sign, 1,2, 0, 1, 0,0, 0,0);
      multiplier=gtk.Entry()
      multiplier.set_text('1')
      align_table.attach(multiplier, 2,3, 0, 1, 0,0, 0,0);
      object_box=gtk.combo_box_new_text()
      for object in scan_list:
        if object[0].zdata>=0:
          continue
        else:
          object_box.append_text(os.path.split(object[1])[1]+' '+str(object[2])+'-('+object[0].short_info+')')
      object_box.set_active(0)
      align_table.attach(object_box, 3,4, 0,1, gtk.EXPAND|gtk.FILL,0, 0,0)
      add_dialog.vbox.add(align_table)
      add_dialog.show_all()
      result=add_dialog.run()
      if result==1:
        if sign.get_text() in ['+','-', '*', '/']:
          sign=sign.get_text()
        else:
          sign='+'
        combine_list.append( (object_box.get_active(), sign, float(multiplier.get_text())) )
        label=gtk.Label(sign+multiplier.get_text()+'*{'+object_box.get_active_text()+'}')
        label.show()
        function_table.attach(label, 0,1, len(combine_list)-1,len(combine_list), 0,0, 0,0)
      add_dialog.destroy()
    combine_dialog=gtk.Dialog(title='Combination of scans:')
    combine_dialog.set_default_size(150,50)
    combine_dialog.add_button('Add', 2)
    combine_dialog.add_button('OK', 1)
    combine_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,1,False)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text('Result')
    table.attach(input_filed,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    label=gtk.Label(" = ")
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                         0,
                0,                         0);
    function_table=gtk.Table(1,1,False)
    table.attach(function_table,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    combine_dialog.vbox.add(table)
    combine_dialog.show_all()
    # if a preset is used create the right list and show the function
    if preset is None:
      add_object()
    else:
      combine_list=preset
      for i, item in enumerate(combine_list):
        try:
          label=gtk.Label(item[1]+str(item[2])+'*{'+str(i)+'-('+scan_list[item[0]][0].short_info+')}')
          label.show()
          function_table.attach(label, 0,1, i,i+1, 0,0, 0,0)        
        except IndexError:
          combine_dialog.destroy()
          return None
    result=combine_dialog.run()
    while result>1:
      add_object()
      result=combine_dialog.run()
    if result==1:
      self.calculate_combination(combine_list, scan_list, input_filed.get_text())
      window.index_mess=len(self.active_file_data)-1
      window.replot()
    combine_dialog.destroy()
  
  def calculate_combination(self, combine_list, scan_list, title):
    '''
      Calculate a combination of polarization directions as
      set in the combine_list.
      
      @param combine_layers List of how the chanels should be combined
      @param scan_list The chanels which will be combined
      @param title Name of the new created chanel
    '''
    if combine_list[0][1] != '-':
      result=combine_list[0][2]*scan_list[combine_list[0][0]][0]
    else:
      result=-1.*combine_list[0][2]*scan_list[combine_list[0][0]][0]
    for object, sign, multiplier in combine_list[1:]:
      if sign == '+':
        result=result+multiplier*scan_list[object][0]
      elif sign == '*':
        result=result*(multiplier*scan_list[object][0])
      elif sign == '/':
        result=result/(multiplier*scan_list[object][0])
      else:
        result=result-multiplier*scan_list[object][0]
      if result is None:
        message=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='You can only combine scans with the same number of measured points!')
        message.run()
        message.destroy()
        return None
    result.short_info=title
    result.number=str(len(scan_list))
    self.active_file_data.append(result)

  #++++ functions for fitting with fortran program by E. Kentzinger ++++
  
  from reflectometer_fit.functions import \
      dialog_activate, \
      result_window_response, \
      fit_history, \
      rebuild_dialog, \
      delete_layer, \
      up_layer, \
      move_layer_up_in_list, \
      delete_multilayer, \
      open_status_dialog, \
      toggle_fit_option, \
      toggle_fit_bool_option, \
      read_fit_file, \
      user_constraint_dialog, \
      user_constraint_response
  

  #+++++++++++++++++++++++ GUI functions +++++++++++++++++++++++

  def fit_window(self, action, window, position=None, size=[580, 550]):
    '''
      create a dialog window for the fit options
    '''
    if self.active_file_data.fit_object.layers==[]:
      self.active_file_data.fit_object.append_layer('Unknown', 10., 5.)
      self.active_file_data.fit_object.append_substrate('Unknown', 5.)
    layer_options={}
    layer_index=0
    layer_params={}
    fit_params={
              'background':False, 
              'resolution':False, 
              'scaling':False, 
              'actually':False
              }
  #+++++++++++++++++ Adding input fields +++++++++++++++++
    dialog=gtk.Dialog(title='Fit parameters')
    if position!=None:
      dialog.move(position[0], position[1])
    #layer parameters
    for layer in self.active_file_data.fit_object.layers:
      layer_options[layer_index]=self.create_layer_options(layer, layer_index, layer_params, dialog, window)
      layer_index+=1
    #create table for widgets
    table=gtk.Table(1, layer_index + 5, False)
    table.set_row_spacings(10)
    # top parameter
    align_table=gtk.Table(3, 1, False)
    align_table.set_col_spacings(15)
    text_filed=gtk.Label()
    text_filed.set_markup('Beam energy: ')
    align_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    energy=gtk.Entry()
    energy.set_width_chars(10)
    energy.set_text(str(self.active_file_data.fit_object.radiation[0]))
    # activating the input will apply the settings, too
    energy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(energy, 1, 2,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('x-region')
    align_table.attach(text_filed, 2, 3,  0, 1, gtk.FILL, gtk.FILL, 0, 0)
    x_from=gtk.Entry()
    x_from.set_width_chars(10)
    x_from.set_text(str(self.x_from))
    # activating the input will apply the settings, too
    x_from.connect('activate', self.dialog_activate, dialog)
    align_table.attach(x_from, 3, 4,  0, 1, gtk.FILL, gtk.FILL, 0, 0)
    x_to=gtk.Entry()
    x_to.set_width_chars(10)
    x_to.set_text(str(self.x_to))
    # activating the input will apply the settings, too
    x_to.connect('activate', self.dialog_activate, dialog)
    align_table.attach(x_to, 4, 5, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    frame = gtk.Frame()
    frame.set_shadow_type(gtk.SHADOW_IN)
    frame.add(align_table)
    table.attach(frame, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
    # layer parameters in table
    for i in range(layer_index):
      table.attach(layer_options[i], 0, 1, i+1, i+2, gtk.FILL, gtk.FILL, 0, 0)
    # substrate parameters
    substrat_options=self.create_layer_options(self.active_file_data.fit_object.substrate, 0, fit_params, dialog, window, substrate=True)
    table.attach(substrat_options, 0, 1, layer_index+2, layer_index+3, gtk.FILL,  gtk.FILL, 0, 0)
    #bottom parameters
    align_table=gtk.Table(4, 4, False)
    align_table.set_col_spacings(10)
    text_filed=gtk.Label()
    text_filed.set_markup('Additional global parameters: ')
    align_table.attach(text_filed, 0, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 5)
    background_x=gtk.CheckButton(label='Background: ', use_underline=True)
    background_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'background')
    align_table.attach(background_x, 0, 1, 1, 2, gtk.FILL,  gtk.FILL, 0, 0)
    background=gtk.Entry()
    background.set_width_chars(10)
    background.set_text(str(self.active_file_data.fit_object.background))
    # activating the input will apply the settings, too
    background.connect('activate', self.dialog_activate, dialog)
    align_table.attach(background, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)   
    resolution_x=gtk.CheckButton(label='Resolution: ', use_underline=True)
    resolution_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'resolution')
    align_table.attach(resolution_x, 2, 3, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    resolution=gtk.Entry()
    resolution.set_width_chars(10)
    resolution.set_text(str(self.active_file_data.fit_object.resolution))
    # activating the input will apply the settings, too
    resolution.connect('activate', self.dialog_activate, dialog)
    align_table.attach(resolution, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)   
    scaling_x=gtk.CheckButton(label='Scaling: ', use_underline=True)
    scaling_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'scaling')
    align_table.attach(scaling_x, 0, 1, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    scaling_factor=gtk.Entry()
    scaling_factor.set_width_chars(10)
    scaling_factor.set_text(str(self.active_file_data.fit_object.scaling_factor))
    # activating the input will apply the settings, too
    scaling_factor.connect('activate', self.dialog_activate, dialog)
    align_table.attach(scaling_factor, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('Theta_max (°): ')
    align_table.attach(text_filed, 2, 3, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    theta_max=gtk.Entry()
    theta_max.set_width_chars(10)
    theta_max.set_text(str(self.active_file_data.fit_object.theta_max))
    # activating the input will apply the settings, too
    theta_max.connect('activate', self.dialog_activate, dialog)
    align_table.attach(theta_max, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    # fit-settings
    fit_x=gtk.CheckButton(label='Fit selected', use_underline=True)
    fit_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'actually')
    align_table.attach(fit_x, 0, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    max_iter=gtk.Entry()
    max_iter.set_width_chars(4)
    max_iter.set_text(str(self.max_iter))
    # activating the input will apply the settings, too
    max_iter.connect('activate', self.dialog_activate, dialog)
    align_table.attach(max_iter, 2, 3, 3, 4, 0, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('max. iterations')
    align_table.attach(text_filed, 3, 4, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    if self.active_file_data.fit_object_history!=[]:
      history_back=gtk.Button(label='Undo (%i)' % len(self.active_file_data.fit_object_history), use_underline=True)
      history_back.connect('clicked', self.fit_history, True, dialog, window)
      align_table.attach(history_back, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    if self.active_file_data.fit_object_future!=[]:
      history_forward=gtk.Button(label='Redo (%i)' % len(self.active_file_data.fit_object_future), use_underline=True)
      history_forward.connect('clicked', self.fit_history, False, dialog, window)
      align_table.attach(history_forward, 2, 3, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    frame = gtk.Frame()
    frame.set_shadow_type(gtk.SHADOW_IN)
    frame.add(align_table)
    table.attach(frame, 0, 1, layer_index+3, layer_index+4, gtk.FILL,  gtk.FILL, 0, 0)
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(table) # add textbuffer view widget
  #----------------- Adding input fields -----------------
    dialog.vbox.add(sw) # add table to dialog box
    dialog.set_default_size(size[0],size[1])
    dialog.add_button('Custom Constraints',7) # button custom constrain has handler_id 7
    dialog.add_button('New Layer',3) # button new layer has handler_id 3
    dialog.add_button('New Multilayer',4) # button new multilayer has handler_id 4
    dialog.add_button('Fit/Simulate and Replot',5) # button replot has handler_id 5
    dialog.connect("response", self.dialog_response, dialog, window, \
                   [energy, background, resolution, scaling_factor, theta_max, x_from, x_to], \
                   [layer_params, fit_params, max_iter])
    # befor the widget gets destroyed the textbuffer view widget is removed
    #dialog.connect("destroy",self.close_plot_options_window,sw) 
    dialog.show_all()
    # connect dialog to main window
    window.open_windows.append(dialog)
    dialog.connect("destroy", lambda *w: window.open_windows.remove(dialog))

  def stop_scroll_emission(self, SL_selector, action):
    SL_selector.stop_emission('scroll-event')

  def create_layer_options(self, layer, layer_index, layer_params, dialog, window, substrate=False):
    '''
      Create dialog inputs for every layer.
      Checkboxes are connected to toggle_fit_option,
      entries get passed to dialog_get_params when dialog response is triggered
      and 'DEL' buttons are connected to delete_layer
    '''
    if not layer.multilayer:
      #++++++++++++++++++ singlelayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]=[]
      align_table=gtk.Table(6, 3, False)
      # labels
      layer_title=gtk.Label()
      if not substrate:
        layer_title.set_markup(str(layer_index + 1) + ' - ' + layer.name)
        align_table.attach(layer_title, 0, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
        thickness_x=gtk.CheckButton(label='thickness', use_underline=True)
        thickness_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 0)
        align_table.attach(thickness_x, 0, 1, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      else:
        layer_title.set_markup('Substrate - ' + layer.name)
        align_table.attach(layer_title, 0, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
        spacer=gtk.Label()
        spacer.set_markup('  ')
        spacer.set_width_chars(11)
        align_table.attach(spacer, 0, 1, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      delta_x=gtk.CheckButton(label='delta', use_underline=True)
      delta_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 1)
      align_table.attach(delta_x, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      d_over_b_x=gtk.CheckButton(label='delta over beta', use_underline=True)
      d_over_b_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 2)
      align_table.attach(d_over_b_x, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      roughness_x=gtk.CheckButton(label='roughness', use_underline=True)
      roughness_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 3)
      align_table.attach(roughness_x, 4, 5, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      # entries
      thickness=gtk.Entry()
      thickness.set_width_chars(10)
      thickness.set_text(str(layer.thickness))
      # activating the input will apply the settings, too
      thickness.connect('activate', self.dialog_activate, dialog)
      if not substrate:
        align_table.attach(thickness, 0, 1, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
        delete=gtk.Button(label='DEL', use_underline=True)
        delete.connect('clicked', self.delete_layer, layer, dialog, window)
        align_table.attach(delete, 5, 6, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
        delete=gtk.Button(label='UP', use_underline=True)
        delete.connect('clicked', self.up_layer, layer, dialog, window)
        align_table.attach(delete, 6, 7, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      delta=gtk.Entry()
      delta.set_width_chars(10)
      delta.set_text(str(layer.delta))
      # activating the input will apply the settings, too
      delta.connect('activate', self.dialog_activate, dialog)
      align_table.attach(delta, 1, 2, 2, 3, gtk.FILL,  gtk.FILL, 0, 0)
      d_over_b=gtk.Entry()
      d_over_b.set_width_chars(12)
      d_over_b.set_text(str(layer.d_over_b))
      # activating the input will apply the settings, too
      d_over_b.connect('activate', self.dialog_activate, dialog)
      align_table.attach(d_over_b, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      # selection dialog for material
      SL_selector=gtk.combo_box_new_text()
      SL_selector.append_text('SL')
      SL_selector.set_active(0)
      for i, SL in enumerate(self.active_file_data.fit_object.SCATTERING_LENGTH_DENSITIES.items()):
        SL_selector.append_text(SL[0])
        if layer.delta==SL[1][0] and layer.d_over_b==SL[1][1]:
          SL_selector.set_active(i+1)
      SL_selector.connect('scroll-event', self.stop_scroll_emission)
      SL_selector.connect('changed', self.change_scattering_length, \
                          SL_selector, layer, delta, d_over_b, \
                          layer_title, layer_index, substrate)
      layer.SL_selector=SL_selector
      align_table.attach(SL_selector, 2, 3, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      roughness=gtk.Entry()
      roughness.set_width_chars(10)
      roughness.set_text(str(layer.roughness))
      # activating the input will apply the settings, too
      roughness.connect('activate', self.dialog_activate, dialog)
      align_table.attach(roughness, 4, 5, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      # when apply button is pressed or field gets activated, send data
      dialog.connect('response', layer.dialog_get_params, thickness, delta, d_over_b, roughness) # when apply button is pressed, send data
    else:
      #++++++++++++++++++ multilayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]={}
      align_table=gtk.Table(5, 1 + len(layer.layers), False)
      align_table.set_row_spacings(5)
      text_filed=gtk.Label()
      text_filed.set_markup('Multilayer')
      align_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      text_filed=gtk.Label()
      text_filed.set_markup(str(layer_index + 1) + ' - ' + layer.name)
      align_table.attach(text_filed, 1, 2,  0, 1, gtk.FILL, gtk.FILL, 0, 0)
      small_table=gtk.Table(2, 1, False)
      repititions=gtk.Entry()
      repititions.set_width_chars(3)
      repititions.set_text(str(layer.repititions))
      # activating the input will apply the settings, too
      repititions.connect('activate', self.dialog_activate, dialog)
      small_table.attach(repititions, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      add=gtk.Button(label='Add Layer', use_underline=True)
      add.connect('clicked', self.add_multilayer, layer, dialog, window)
      small_table.attach(add, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      align_table.attach(small_table, 2, 3, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      small_table=gtk.Table(4, 1, False)
      # entry for a gradient in roughness
      text_filed=gtk.Label()
      text_filed.set_markup('Roughness Gradient:')
      small_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      roughness_gradient=gtk.Entry()
      roughness_gradient.set_width_chars(3)
      roughness_gradient.set_text(str(layer.roughness_gradient))
      # activating the input will apply the settings, too
      roughness_gradient.connect('activate', self.dialog_activate, dialog)
      small_table.attach(roughness_gradient, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      delete=gtk.Button(label='DEL', use_underline=True)
      delete.connect('clicked', self.delete_multilayer, layer, dialog, window)
      small_table.attach(delete, 2, 3, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      delete=gtk.Button(label='UP', use_underline=True)
      delete.connect('clicked', self.up_layer, layer, dialog, window)
      small_table.attach(delete, 3, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      dialog.connect('response', layer.dialog_get_params, repititions, roughness_gradient) # when apply button is pressed, send data
      align_table.attach(small_table, 3, 6, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      # sublayers are appended to the align_table via recursion
      for i, sub_layer in enumerate(layer.layers):
        sub_table=self.create_layer_options(sub_layer, i, layer_params[layer_index], dialog, window)
        align_table.attach(sub_table, 1, 5, i+1, i+2, gtk.FILL, gtk.FILL, 0, 0)
      frame = gtk.Frame()
      frame.set_shadow_type(gtk.SHADOW_IN)
      frame.add(align_table)
      align_table=frame
    return align_table
  
  
  def dialog_response(self, action, response, dialog, window, parameters_list, fit_list):
    '''
      handle fit dialog response
    '''
    if response>=5:
      try:
        self.active_file_data.fit_object.radiation[0]=float(parameters_list[0].get_text())
        self.active_file_data.fit_object.background=float(parameters_list[1].get_text())
        self.active_file_data.fit_object.resolution=float(parameters_list[2].get_text())
        self.active_file_data.fit_object.scaling_factor=float(parameters_list[3].get_text())
        self.active_file_data.fit_object.theta_max=float(parameters_list[4].get_text())
      except ValueError:
        None
      try:
        self.x_from=float(parameters_list[5].get_text())
      except ValueError:
        self.x_from=None
      try:
        self.x_to=float(parameters_list[6].get_text())
      except ValueError:
        self.x_to=None
      self.active_file_data.fit_object.set_fit_parameters(layer_params=fit_list[0], substrate_params=map(lambda x: x-1, fit_list[1][0]), \
                                         background=fit_list[1]['background'], \
                                         resolution=fit_list[1]['resolution'], \
                                         scaling=fit_list[1]['scaling'])
      try:
        self.max_iter=int(fit_list[2].get_text())
      except ValueError:
        self.max_iter=50
      if fit_list[1]['actually'] and response==5:
        self.active_file_data.fit_object.fit=1
      if response==7:
        self.user_constraint_dialog(dialog, window)
        return None
      self.dialog_fit(action, window)
      # read fit parameters from file and create new object, if process is killed ignore
      if fit_list[1]['actually'] and response==5 and self.active_file_data.fit_object.fit==1: 
        parameters, errors=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref', self.active_file_data.fit_object)
        new_fit=self.active_file_data.fit_object.copy()
        new_fit.get_parameters(parameters)
        sorted_errors=new_fit.get_errors(errors)
        self.show_result_window(dialog, window, new_fit, sorted_errors)
      os.remove(self.TEMP_DIR+'fit_temp.ref')
      self.active_file_data.fit_object.fit=0
    elif response==3: # new layer
      new_layer=RefLayerParam()
      self.active_file_data.fit_object.layers.append(new_layer)
      self.rebuild_dialog(dialog, window)
    elif response==4: # new multilayer
      multilayer=RefMultilayerParam()
      multilayer.layers.append(RefLayerParam())
      self.active_file_data.fit_object.layers.append(multilayer)
      self.rebuild_dialog(dialog, window)

  def show_result_window(self, dialog, window, new_fit, sorted_errors):
    '''
      show the result of a fit and ask to retrieve the result
    '''
    old_fit=self.active_file_data.fit_object
    results=gtk.Dialog(title='Fit results:')
    text_string='These are the parameters retrieved by the last fit\n'
    #+++++++++++ get_layer_text responde function ++++++++++++++++
    def get_layer_text(new_layer, old_layer, index, index_add=''):
      text_string=''
      if len(new_layer)==1: # single layer
        text_string+=str(index)+' - Layer:\n'
        if new_layer.thickness!=old_layer.thickness:
          text_string+='\tthickness:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.thickness, new_layer.thickness, sorted_errors[index_add+str(index)+','+str(0)])
        if new_layer.delta!=old_layer.delta:
          text_string+='\tdelta:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.delta, new_layer.delta, sorted_errors[index_add+str(index)+','+str(1)])
        if new_layer.d_over_b!=old_layer.d_over_b:
          text_string+='\tdelta/beta:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.d_over_b, new_layer.d_over_b, sorted_errors[index_add+str(index)+','+str(2)])
        if new_layer.roughness!=old_layer.roughness:
          text_string+='\troughness:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.roughness, new_layer.roughness, sorted_errors[index_add+str(index)+','+str(3)])
        return text_string+'\n'
      else:
        text_string+='\n'+str(index)+' - Multilayer:\n'
        for i,  layer in enumerate(new_layer.layers):
          text_string+='\t'+get_layer_text(layer, old_layer.layers[i], i, index_add=str(index)+',')
        return text_string
    #----------- get_layer_text responde function ----------------
    for i, new_layer in enumerate(new_fit.layers):
      text_string+=get_layer_text(new_layer, old_fit.layers[i], i)
    # substrate parameters
    text_string+='\nSubstrat:\n'
    if old_fit.substrate.delta!=new_fit.substrate.delta:
      text_string+='\tdelta:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.delta, new_fit.substrate.delta, sorted_errors['substrate0'])
    if old_fit.substrate.d_over_b!=new_fit.substrate.d_over_b:
      text_string+='\tdelta/beta:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
          (old_fit.substrate.d_over_b, new_fit.substrate.d_over_b, sorted_errors['substrate1'])
    if old_fit.substrate.roughness!=new_fit.substrate.roughness:
      text_string+='\troughness:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
          (old_fit.substrate.roughness, new_fit.substrate.roughness, sorted_errors['substrate2'])
    # global parameters
    text_string+='\n'
    if old_fit.background!=new_fit.background:
      text_string+='Background:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.background, new_fit.background, sorted_errors['background'])
    if old_fit.resolution!=new_fit.resolution:
      text_string+='Resolution:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.resolution, new_fit.resolution, sorted_errors['resolution'])
    if old_fit.scaling_factor!=new_fit.scaling_factor:
      text_string+='Scaling Factor:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
          (old_fit.scaling_factor, new_fit.scaling_factor, sorted_errors['scaling'])
    text_string+='\n\nDo you want to use these new parameters?'
    text=gtk.TextView()
    # Retrieving a reference to a textbuffer from a textview. 
    buffer = text.get_buffer()
    buffer.set_text(text_string)
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(text) # add textbuffer view widget
    sw.show_all()
    results.vbox.add(sw) # add table to dialog box
    results.set_default_size(500,450)
    results.add_button('OK',1) # button replot has handler_id 1
    results.add_button('Cancel',2) # button replot has handler_id 2
    #dialog.connect("response", self.result_window_response, dialog, window, new_fit)
    # connect dialog to main window
    window.open_windows.append(dialog)
    results.connect("destroy", lambda *w: window.open_windows.remove(dialog))
    response=results.run()
    self.result_window_response(response, dialog, window, new_fit)
    results.destroy()
    
  def add_multilayer(self, action, multilayer, dialog, window):
    '''
      add a layer to the multilayer after button is pressed
    '''
    new_layer=RefLayerParam()
    multilayer.layers.append(new_layer)
    self.rebuild_dialog(dialog, window)
  
  def dialog_fit(self, action, window):
    '''
      function invoked when apply button is pressed
      fits with the new parameters
    '''
    dataset=window.measurement[window.index_mess]
      # convert x values from angle to q
    dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])    
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', False, ' ', xfrom=self.x_from, xto=self.x_to)
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    #open a background process for the fit function
    reflectometer_fit.functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',self.max_iter)
    print "fit.f90 program started."
    if self.active_file_data.fit_object.fit!=1: # if this is not a fit just wait till finished
      exec_time, stderr_value = reflectometer_fit.functions.proc.communicate()
      print "fit.f90 program finished in %.2g seconds." % float(exec_time.splitlines()[-1])
    else:
      self.open_status_dialog(window)
    simu=read_data.reflectometer.read_simulation(self.TEMP_DIR+'fit_temp.sim')
    simu.number='sim_'+dataset.number
    simu.short_info='simulation'
    simu.sample_name=dataset.sample_name
    dataset.plot_together=[dataset, simu]
    window.replot()

  def change_scattering_length(self, action, SL_selector, layer, delta, d_over_b, layer_title, layer_index, substrate):
    '''
      function to change a layers scattering length parameters
      when a material is selected
    '''
    name=layer.SL_selector.get_active_text()
    try:
      SL=self.active_file_data.fit_object.SCATTERING_LENGTH_DENSITIES[name]
      layer.name=name
      delta.set_text(str(SL[0]))
      d_over_b.set_text(str(SL[1]))
      if substrate:
        layer_title.set_markup('Substrate - ' + layer.name)
      else:
        layer_title.set_markup(str(layer_index + 1) + ' - ' + layer.name)
    except KeyError:
      delta.set_text("1")
      d_over_b.set_text("1")
  
  def import_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter import from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new datafile...', 
                                      action=gtk.FILE_CHOOSER_ACTION_OPEN, 
                                      buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    filter = gtk.FileFilter()
    filter.set_name('Entry file')
    filter.add_pattern('*.ent')
    file_dialog.add_filter(filter)
    filter = gtk.FileFilter()
    filter.set_name('All')
    filter.add_pattern('*.*')
    file_dialog.add_filter(filter)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      file_name=file_dialog.get_filename()
    else:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    self.active_file_data.fit_object=RefFitParameters()
    self.active_file_data.fit_object.read_params_from_file(file_name)
    self.dialog_fit(action, window)
    return True
  
  
  def export_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter export from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new datafile...', action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    file_dialog.set_current_name(self.active_file_name+'.ent')
    filter = gtk.FileFilter()
    filter.set_name('Entry file')
    filter.add_pattern('*.ent')
    file_dialog.add_filter(filter)
    filter = gtk.FileFilter()
    filter.set_name('All')
    filter.add_pattern('*.*')
    file_dialog.add_filter(filter)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      file_name=file_dialog.get_filename()
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    file_prefix=file_name.rsplit('.ent', 1)[0]
    dataset=self.active_file_data[window.index_mess]
    data_lines=dataset.export(file_prefix+'.res', False, ' ', xfrom=self.x_from, xto=self.x_to)
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(file_prefix+'.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str(use_roughness_gradient=False)+'\n')
    ent_file.close()
    self.call_fit_program(file_prefix+'.ent', file_prefix+'.res', file_prefix, 50, exe=file_prefix+'.o')
    script_file=open(file_prefix+'_run.sh', 'w')
    script_file.write("""#!/bin/sh
    echo "Runnig fit for %s"
    %s %s %s %s %s 50&
    tail -f %s\n""" % (file_prefix, 
           file_prefix+'.o', 
           file_prefix+'.ent', 
           file_prefix+'.res', 
           file_prefix+'.ref', 
           file_prefix+'.sim', 
           file_prefix+'.ref')
    )
    script_file.close()
    os.chmod(file_prefix+'_run.sh', 0777)
    return True
  
  def replot_present(self, session, window):
    dataset=window.measurement[window.index_mess]        
    simu=read_data.reflectometer.read_simulation(self.TEMP_DIR+'fit_temp.sim')
    simu.number='sim_'+dataset.number
    simu.short_info='simulation'
    simu.sample_name=dataset.sample_name
    dataset.plot_together=[dataset, simu]
    window.replot()  

  #----------------------- GUI functions -----------------------

  def call_fit_program(self, file_ent, file_res, file_out, max_iter, exe=None):
    '''
      This function calls the fit.f90 program and if it is not compiled with 
      those settings, will compile it with the number of layres present in 
      the current simulation. For this the maxint parameter in the fit.f90 
      code is replaced by the real number of layers. It does not wait for the 
      program to finish, it only startes the sub process, which is returned.
    '''
    code_file=os.path.join(self.SCRIPT_PATH, config.reflectometer.FIT_PROGRAM_CODE_FILE)
    if not exe:
      exe=os.path.join(self.TEMP_DIR, 'fit.o')
    try:
      code_tmp=open(os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), 'r').read()
    except IOError:
      code_tmp=' '
    # has the program been changed or does it not exist
    if (not os.path.exists(exe)) or \
      ((os.stat(code_file)[8]-os.stat(exe)[8]) > 0) or \
      (not 'maxint='+str(self.active_file_data.fit_object.number_of_layers()+1) in code_tmp):
      code=open(code_file, 'r').read()
      # compile the program with constants suitable for this dataset
      code_tmp=code.replace('maxint=25', 'maxint='+str(self.active_file_data.fit_object.number_of_layers()+1))
      code_tmp=code_tmp.replace('.and.alamda.le.1.0d10', '.and.alamda.le.1.0d'+str(self.max_alambda))
      code_tmp=code_tmp.replace('.or.alamda.gt.1.0d10', '.or.alamda.gt.1.0d'+str(self.max_alambda))
      tmp_file=open(os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), 'w')
      tmp_file.write(code_tmp)
      tmp_file.close()
      print 'Compiling fit program!'
      call_params=[config.reflectometer.FORTRAN_COMPILER, os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), '-o', exe]
      if  config.reflectometer.FORTRAN_COMPILER_OPTIONS!=None:
        call_params.append(config.reflectometer.FORTRAN_COMPILER_OPTIONS)
      if  config.reflectometer.FORTRAN_COMPILER_MARCH!=None:
        call_params.append(config.reflectometer.FORTRAN_COMPILER_MARCH)
      subprocess.call(call_params, shell=False)
      print 'Compiled'
    process = subprocess.Popen([exe, file_ent, file_res, file_out+'.ref', file_out+'.sim', str(max_iter)], 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        cwd=self.TEMP_DIR, 
                        )
    return process
    
  def find_total_reflection(self, dataset):
    '''
      try to find the angle of total reflection by
      searching for a decrease of intensity to 1/3
    '''
    position=0
    max_value=0
    for point in dataset:
      position=point[0]
      if point[0]>0.05:
        if max_value<point[1]:
          max_value=point[1]
        elif max_value>(point[1]*3):
          dataset.index=0
          return position
    return position

  def refine_scaling(self, dataset):
    '''
      try to fit the scaling factor before the total reflection angle
    '''
    self.active_file_data.fit_object.fit=1
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', False, ' ', xfrom=0.005,xto=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(scaling=True) # fit only scaling factor
    self.active_file_data.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    reflectometer_fit.functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',20)
    retcode = reflectometer_fit.functions.proc.communicate()
    parameters, errors=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref', self.active_file_data.fit_object)
    self.active_file_data.fit_object.scaling_factor=parameters[self.active_file_data.fit_object.fit_params[0]]
    self.active_file_data.fit_object.fit=0
    return retcode

  def refine_roughnesses(self, dataset):
    '''
      try to fit the layer roughnesses
    '''
    self.active_file_data.fit_object.fit=1
    layer_dict={}
    # create parameter dictionary for every (multi)layer, 3 is the roughness
    for i, layer in enumerate(self.active_file_data.fit_object.layers):
      if not layer.multilayer:
        layer_dict[i]=[3]
      else:
        layer_dict[i]=[[3] for j in range(len(layer.layers))]
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', False, ' ', xfrom=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(layer_params=layer_dict, substrate_params=[2]) # set all roughnesses to be fit
    self.active_file_data.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    reflectometer_fit.functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',20)
    sec=0.
    while reflectometer_fit.functions.proc.poll()==None:
      time.sleep(0.1)
      sec+=0.1
      sys.stdout.write( '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                        'Script running for % 6dsec' % sec)
      sys.stdout.flush()
    retcode = reflectometer_fit.functions.proc.communicate()
    parameters, errors=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref',self.active_file_data.fit_object)
    self.active_file_data.fit_object.get_parameters(parameters)
    self.active_file_data.fit_object.fit=0
    return retcode

  def export_fit(self, dataset, input_file_name, export_file_prefix=None):
    '''
      Function to export data for fitting with fit.f90 program.
    '''
    if not export_file_prefix:
      export_file_prefix=self.TEMP_DIR+'fit_temp'
    if self.active_file_data.fit_object.layers==[]:
      #+++++++++++++++++++ create fit parameters object +++++++++++++++++++
      fit_thick=self.fit_thicknesses
      first_split=self.fit_layers.split('-')
      for compound in first_split:
        if compound[-1]==']': # is there a multilayer
          count=int(compound.split('[')[0])
          second_split=compound.split('[')[1].rstrip(']').split('_')
          second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
          self.active_file_data.fit_object.append_multilayer(second_split, map(float, second_thick), [self.fit_est_roughness for i in second_thick], count)
        else: # no multilayer
            if len(fit_thick)>0:
                self.active_file_data.fit_object.append_layer(compound, float(fit_thick.split('-')[0]), self.fit_est_roughness)
            else:
                self.active_file_data.fit_object.append_substrate(compound, self.fit_est_roughness)
        if len(fit_thick.split('-'))>1: # remove first thickness
            fit_thick=fit_thick.split('-',1)[1]
        else:
            fit_thick=''
      #------------------- create fit parameters object -------------------
    self.active_file_data.fit_object.set_fit_constrains() # set constrained parameters for multilayer
      # convert x values from angle to q
    dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])
      # first guess for scaling factor is the maximum intensity
    self.active_file_data.fit_object.scaling_factor=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    self.active_file_data.fit_object.background=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine: 
      print "Try to refine scaling"
      dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])    
      self.refine_scaling(dataset)
      print "Try to refine roughnesses"
      self.refine_roughnesses(dataset)
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
      # write data into files with sequence numbers in format ok for fit.f90    
    data_lines=dataset.export(export_file_prefix+'.res',False,' ') 
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.set_fit_parameters(background=True)
    ent_file=open(export_file_prefix+'.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    print "Simulate the measurement"
    reflectometer_fit.functions.proc = self.call_fit_program(export_file_prefix+'.ent', 
                                                             export_file_prefix+'.res', 
                                                             export_file_prefix,20)
    retcode = reflectometer_fit.functions.proc.communicate()
    #------- create final input file and make a simulation -------

  #---- functions for fitting with fortran program by E. Kentzinger ----

class RefFitParameters(FitParameters):
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  radiation=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
  number_of_points=10 # number of simulated points
  resolution=3.5 # resolution in q in 1e-3 A^-1
  theta_max= 2.3 # angle of total coverage for recalibration
  from config.scattering_length_table import SCATTERING_LENGTH_DENSITIES
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
      parameters=[thickness] + SL + [roughness]
    except (KeyError, TypeError):
      parameters=[thickness] + [1. for i in range(self.PARAMETER_LENGTH-2)] + [roughness]
      material='Unknown'
      result=False
    layer=RefLayerParam(material, parameters)
    self.layers.append(layer)
    return result

  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.SCATTERING_LENGTH_DENSITIES[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(RefLayerParam(materials[i], [thicknesses[i]] + SL + [roughnesses[i]]))
    multilayer=RefMultilayerParam(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1. for i in range(self.PARAMETER_LENGTH - 2)]
      result=False
    layer=RefLayerParam(material, [0.] + SL + [roughness])
    self.substrate=layer
    return result

  def get_ent_str(self, use_roughness_gradient=True):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.number_of_layers() + 1) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string_layer, layer_index, para_index = self.__get_ent_str_layers__(use_roughness_gradient)
    ent_string+=ent_string_layer
    # more global parameters
    ent_string+=str(round(self.background, 4)) + '\tbackground\t\t\t\tparametar ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.resolution) + '\tresolution in q (sigma, in 1e-3 A^-1)\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(round(self.scaling_factor, 4)) + '\tscaling factor *1e6\t\t\tparameter ' + str(para_index) + '\n'
    ent_string+='\n' + str(self.theta_max) + '\ttheta_max (in deg) for recalibration\n'
    # fit specific parameters
    ent_string+='#### fit specific parameters:\n'
    ent_string+=str(self.fit) + '\t1: fit; 0: simulation\n'
    ent_string+='\n' + str(len(self.fit_params)) + '\t\tNumber of parameters to be fitted\n'
    ent_string+=' '.join([str(param) for param in self.fit_params]) + '\t\tindices of parameters\n'
    ent_string+=str(len(self.constrains)) + '\t\tnumber of constrains\n'
    for constrain in self.constrains:
      ent_string+=str(len(constrain)) + '\t\tnumber of parameters to be kept equal\n'
      ent_string+=' '.join([str(param) for param in constrain]) + '\t\tindices of those parameters\n'
    return ent_string

  
  def set_fit_parameters(self, layer_params={}, substrate_params=[], background=False, resolution=False, scaling=False):
    '''
      set fit parameters depending on (multi)layers
      layer_params is a dictionary with the layer number as index
    '''
    fit_params=[]
    para_index=1
    for i, layer in enumerate(self.layers):
      if i in layer_params:
        new_paras, para_index=layer.get_fit_params(layer_params[i], para_index)
        fit_params+=new_paras
      else:
        para_index+=len(layer)*4
    for param in substrate_params:
      fit_params.append(para_index + param)
    para_index+=3
    if background:
      fit_params.append(para_index)
    para_index+=1
    if resolution:
      fit_params.append(para_index)
    para_index+=1
    if scaling:
      fit_params.append(para_index)
    para_index+=1
    fit_params.sort()
    self.fit_params=fit_params
    
  def get_parameters(self, parameters):
    '''
      set layer parameters from existing fit
    '''
    para_index=1
    for i, layer in enumerate(self.layers):
      for j in range(4): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            layer.set_param(j, parameters[para_index + j])
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*4) in self.fit_params:
              layer.layers[k].set_param(j, parameters[para_index + j + k*4])
      para_index+=len(layer)*4
    for j in range(3):
      if para_index in self.fit_params:
        self.substrate.set_param(j+1, parameters[para_index])
      para_index+=1
    if para_index in self.fit_params:
      self.background=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.resolution=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.scaling_factor=parameters[para_index]
    para_index+=1
  
  def get_errors(self, errors):
    '''
      convert errors dictionary from parameter indices to layer indices
    '''
    para_index=1
    errors_out={}
    for i, layer in enumerate(self.layers):
      for j in range(4): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            errors_out[str(i) + ',' + str(j)]=errors[para_index + j]
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*4) in self.fit_params:
              errors_out[str(i) + ',' + str(k) + ',' + str(j)]=errors[para_index + j + k*4]
      para_index+=len(layer)*4
    for j in range(3):
      if para_index in self.fit_params:
        errors_out['substrate'+str(j)]=errors[para_index]
      para_index+=1
    if para_index in self.fit_params:
      errors_out['background']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['resolution']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['scaling']=errors[para_index]
    para_index+=1
    return errors_out
  
  def set_fit_constrains(self):
    '''
      Set fit constrains depending on (multi)layers.
      layer_params is a dictionary with the layer number as index
      Merge custom constrins with multilayer constrains.
    '''
    fit_cons=[]
    con_index=1
    for layer in self.layers:
      if layer.multilayer: # for every multilayer add constrains
        new_con, con_index=layer.get_fit_cons(con_index)
        fit_cons+=new_con
      else:
        con_index+=4
    fit_cons+=self.user_constraints
    fit_cons2=[]
    # remove constrains not importent for the fitted parameters
    for constrain in fit_cons:
      if constrain[0] in self.fit_params:
        fit_cons2.append(constrain)
    # write actual constraints and combine constraints with same indices
    fit_cons3=[]
    for constrain in fit_cons2:
      # go through the list in both directions and collect any lists which contain at
      # least one element with the same value, this way every constrains will be
      # merged without missing any crosscorrelations.
      for constrain2 in fit_cons2:
        if len(set(constrain+constrain2))!=len(set(constrain))+len(set(constrain2)):
          constrain=sorted(list(set(constrain+constrain2)))
      for constrain2 in reversed(fit_cons2):
        if len(set(constrain+constrain2))!=len(set(constrain))+len(set(constrain2)):
          constrain=sorted(list(set(constrain+constrain2)))
      if not constrain in fit_cons3:
        fit_cons3.append(constrain)
    self.constrains=fit_cons3

  def copy(self):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit=FitParameters.copy(self, RefFitParameters())
    new_fit.radiation=copy(self.radiation)
    new_fit.number_of_points=self.number_of_points
    new_fit.resolution=self.resolution
    new_fit.theta_max=self.theta_max
    return new_fit

  def read_params_from_file(self, file):
    '''
      read data from .ent file
    '''
    lines=open(file, 'r').readlines()
    lines.reverse()
    self.radiation[0]=float(lines.pop().split()[0])
    lines.pop()
    lines.pop()
    number_of_layers=int(lines.pop().split()[0])
    # read layer data
    self.layers=[]
    for i in range(number_of_layers-1):
      comment=lines.pop()
      if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
        name=comment.split(':', 1)[1].strip('\n').lstrip()
      else:
        name='NoName'
      parameters=[]
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      layer=RefLayerParam(name=name, parameters_list=parameters)
      self.layers.append(layer)
    # read substrate data
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      name='NoName'
    parameters=[]
    parameters.append(0)
    parameters.append(float(lines.pop().split()[0]))
    parameters.append(float(lines.pop().split()[0]))
    parameters.append(float(lines.pop().split()[0]))
    self.substrate=RefLayerParam(name=name, parameters_list=parameters)
    # read last parameters
    lines.pop()
    self.background=float(lines.pop().split()[0])
    self.resolution=float(lines.pop().split()[0])
    self.scaling_factor=float(lines.pop().split()[0])
    lines.pop()
    self.theta_max=float(lines.pop().split()[0])
    self.combine_layers(RefMultilayerParam)

class RefLayerParam(LayerParam):
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  delta=1
  d_over_b=1
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    LayerParam.__init__(self, name, parameters_list)
    if parameters_list!=None:
      self.delta=parameters_list[1]
      self.d_over_b=parameters_list[2]
    else:
      self.delta=1
      self.d_over_b=1
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return LayerParam.__eq__(self, other) and\
      self.delta==other.delta and\
      self.d_over_b==other.d_over_b
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return RefLayerParam(name=self.name, \
                     parameters_list=[\
                          self.thickness, \
                          self.delta, \
                          self.d_over_b, \
                          self.roughness])


  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params
    '''
    list=[]
    for i in params:
      list.append(param_index + i)
    return list, param_index + 4
  
  def dialog_get_params(self, action, response, thickness, delta, d_over_b, roughness):
    '''
      function to get parameters from the GUI dialog
    '''
    LayerParam.dialog_get_params(self, action, response, thickness, roughness)
    try:
      self.delta=float(delta.get_text())
      self.d_over_b=float(d_over_b.get_text())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==1: 
      self.delta=value
    elif index==2: 
      self.d_over_b=value
    else:
      LayerParam.set_param(self, index, 3, value)
  
  def dialog_get_SL_online(self):
    '''
      Open a dialog to retrieve delta and beta online via http://henke.lbl.gov.
    '''
    dialog=gtk.Dialog()
  
  def get_ent_text(self, layer_index, para_index, add_roughness=0., use_roughness_gradient=True):
    '''
      Function to get the text lines for the .ent file.
      Returns the text string and the parameter index increased
      by the number of parameters for the layer.
    '''
    if not use_roughness_gradient:
      add_roughness=0.
    text=LayerParam.__get_ent_text_start__(self, layer_index, para_index)
    para_index+=1
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=LayerParam.__get_ent_text_end__(self, layer_index, para_index, add_roughness)
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class RefMultilayerParam(MultilayerParam):
  '''
    class for multilayer data
  '''
  
  def copy(self):
    return MultilayerParam.copy(self, RefMultilayerParam())
  
  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params (list of param lists for multilayer)
    '''
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[j]:
        list+=[param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)]
    return list, param_index + len(self) * 4
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    if self.roughness_gradient==0:
      constrain_params=4
    else:
      constrain_params=3
    for j in range(layers): # iterate through layers
      for i in range(constrain_params): # iterate through parameters
        list.append([param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)])
    return list, param_index + len(self)
