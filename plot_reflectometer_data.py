#!/usr/bin/env python
'''
  classes for reflectometer sessions and fits with fit.f90
'''
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                       last changes:                                           #
#                                        06.04.2009                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert uxd files to .out space(and other)seperated text files, splitted by sequences        #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -GUI control over all fit parameters                                                          #
# -send all files to printer after processing (linux commandline printing)                      #
# -complete gui control over the fit program                                                    #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
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
import threading
# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import reflectometer_read_data
import reflectometer_preferences

fortran_compiler='gfortran'
# compiler optimization options as can be found in the manual,
# add your cpu flag here to increase performance of the fit
# stdandart cpu flags are:
# i686 / pentium4 / athlon / k8 / amdfam10 (athlon64) / nocona (p4-64bit)
fortran_compiler_options='-O3'
fortran_compiler_march=None#'-march=nocona'
fit_program_code='fit/fit.f90'
fit_program_executible='fit/fit.o'


class reflectometer_session(generic_session):
  '''
    Class to handle reflectometer data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\tReflectometer-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
\t-fit [layers] [thicknesses] [est._roughness]
\t\t\t\tExport measurements for use with fit programm by Emmanuel Kentzinger and create .ent file for it.
\t\t\t\tlayers is a list of layers with format L1-L2-L3-S or 5[L1_L2]-S, where L,S are the names
\t\t\t\tof the compounds of the layers and substrate as provided in scattering_length_table.py
\t\t\t\tthicknesses is a list of layer thicknesses with format LT1-LT2-LT3 or [LT1_LT2] in A
\t\t\t\test._roughness is the estimated overall roughness to begin with
\t-ref\t\tTry to refine the scaling factor, background and roughnesses.
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_wildcards=(('reflectometer data','*.UXD'), )  
  options=generic_session.options+['fit', 'ref']
  #options:
  show_counts=False
  export_for_fit=False
  try_refine=False
  fit_object=None
  x_from=0.005 # fit only x regions between x_from and x_to
  x_to=''
  max_iter=50 # maximal iterations in fit
  max_alambda=10
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the generic_session constructor
    '''
    self.fit_object=fit_parameter()
    self.data_columns=reflectometer_preferences.data_columns
    self.transformations=reflectometer_preferences.transformations
    generic_session.__init__(self, arguments)
    # initialize the GTK thread engine used in show_result_window
    #gtk.gdk.threads_init()    
    
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
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
    return reflectometer_read_data.read_data(file_name,self.data_columns)
  
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
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "ReflectometerMenu", None,                             # name, stock id
                "Reflectometer", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "ReflectometerFit", None,                             # name, stock id
                "Fit...", None,                    # label, accelerator
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
             )
    return string,  actions
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to generic_session counts per secong
      corrections and fiting are performed here, too.  
    '''
    datasets=generic_session.add_file(self, filename, append)
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
        dataset.process_funcion(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      dataset.short_info=' started at Th='+str(round(th,4))+' 2Th='+str(round(twoth,4))+' Phi='+str(round(phi,4))
      dataset.logx=self.logx
      dataset.logy=self.logy
      if self.export_for_fit: # export fit files
        self.export_fit(dataset,  filename)
        simu=reflectometer_read_data.read_simulation(self.temp_dir+'fit_temp.sim')
        simu.number='sim_'+dataset.number
        simu.short_info='simulation'
        simu.sample_name=dataset.sample_name
        #refinements.append(simu)
        dataset.plot_together=[dataset, simu]
    #if self.export_for_fit: # export fit files
     # self.add_data(refinements, filename+"_simulation")



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
      output_data[counts]=output_data[counts]/self.time_col # calculate the linear correction
    return output_data
  
  #++++ functions for fitting with fortran program by E. Kentzinger ++++

  #+++++++++++++++++++++++ GUI functions +++++++++++++++++++++++

  def fit_window(self, action, window, position=None, size=[500, 400]):
    '''
      create a dialog window for the fit options
    '''
    if self.fit_object.layers==[]:
      self.fit_object.append_layer('Unknown', 10., 5.)
      self.fit_object.append_substrate('Unknown', 5.)
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
    for layer in self.fit_object.layers:
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
    energy.set_text(str(self.fit_object.radiation[0]))
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
    substrat_options=self.create_layer_options(self.fit_object.substrate, 0, fit_params, dialog, window, substrate=True)
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
    background.set_text(str(self.fit_object.background))
    # activating the input will apply the settings, too
    background.connect('activate', self.dialog_activate, dialog)
    align_table.attach(background, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)   
    resolution_x=gtk.CheckButton(label='Resolution: ', use_underline=True)
    resolution_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'resolution')
    align_table.attach(resolution_x, 2, 3, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    resolution=gtk.Entry()
    resolution.set_width_chars(10)
    resolution.set_text(str(self.fit_object.resolution))
    # activating the input will apply the settings, too
    resolution.connect('activate', self.dialog_activate, dialog)
    align_table.attach(resolution, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)   
    scaling_x=gtk.CheckButton(label='Scaling: ', use_underline=True)
    scaling_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'scaling')
    align_table.attach(scaling_x, 0, 1, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    scaling_factor=gtk.Entry()
    scaling_factor.set_width_chars(10)
    scaling_factor.set_text(str(self.fit_object.scaling_factor))
    # activating the input will apply the settings, too
    scaling_factor.connect('activate', self.dialog_activate, dialog)
    align_table.attach(scaling_factor, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('Theta_max (\302\260): ')
    align_table.attach(text_filed, 2, 3, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    theta_max=gtk.Entry()
    theta_max.set_width_chars(10)
    theta_max.set_text(str(self.fit_object.theta_max))
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

  def dialog_activate(self, action, dialog):
    ''' just responde the right signal, when input gets activated '''
    dialog.response(6)

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
      for i, SL in enumerate(self.fit_object.scattering_length_densities.items()):
        SL_selector.append_text(SL[0])
        if layer.delta==SL[1][0] and layer.d_over_b==SL[1][1]:
          SL_selector.set_active(i+1)
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
      repititions=gtk.Entry()
      repititions.set_width_chars(3)
      repititions.set_text(str(layer.repititions))
      # activating the input will apply the settings, too
      repititions.connect('activate', self.dialog_activate, dialog)
      align_table.attach(repititions, 2, 3, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      add=gtk.Button(label='Add Layer', use_underline=True)
      add.connect('clicked', self.add_multilayer, layer, dialog, window)
      align_table.attach(add, 3, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      delete=gtk.Button(label='DEL', use_underline=True)
      delete.connect('clicked', self.delete_multilayer, layer, dialog, window)
      align_table.attach(delete, 4, 5, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      dialog.connect('response', layer.dialog_get_params, repititions) # when apply button is pressed, send data
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
        self.fit_object.radiation[0]=float(parameters_list[0].get_text())
        self.fit_object.background=float(parameters_list[1].get_text())
        self.fit_object.resolution=float(parameters_list[2].get_text())
        self.fit_object.scaling_factor=float(parameters_list[3].get_text())
        self.fit_object.theta_max=float(parameters_list[4].get_text())
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
      self.fit_object.set_fit_parameters(layer_params=fit_list[0], substrate_params=map(lambda x: x-1, fit_list[1][0]), \
                                         background=fit_list[1]['background'], \
                                         resolution=fit_list[1]['resolution'], \
                                         scaling=fit_list[1]['scaling'])
      try:
        self.max_iter=int(fit_list[2].get_text())
      except ValueError:
        self.max_iter=50
      if fit_list[1]['actually'] and response==5:
        self.fit_object.fit=1
      self.dialog_fit(action, window)
      # read fit parameters from file and create new object, if process is killed ignore
      if fit_list[1]['actually'] and response==5 and self.fit_object.fit==1: 
        parameters, errors=self.read_fit_file(self.temp_dir+'fit_temp.ref', self.fit_object)
        new_fit=self.fit_object.copy()
        new_fit.get_parameters(parameters)
        sorted_errors=new_fit.get_errors(errors)
        self.show_result_window(dialog, window, new_fit, sorted_errors)
      os.remove(self.temp_dir+'fit_temp.ref')
      self.fit_object.fit=0
    elif response==3: # new layer
      new_layer=fit_layer()
      self.fit_object.layers.append(new_layer)
      self.rebuild_dialog(dialog, window)
    elif response==4: # new multilayer
      multilayer=fit_multilayer()
      multilayer.layers.append(fit_layer())
      self.fit_object.layers.append(multilayer)
      self.rebuild_dialog(dialog, window)

  def show_result_window(self, dialog, window, new_fit, sorted_errors):
    '''
      show the result of a fit and ask to retrieve the result
    '''
    old_fit=self.fit_object
    results=gtk.Dialog(title='Fit results:')
    text_string='These are the parameters retrieved by the last fit\n'
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
    results.add_button('Cancle',2) # button replot has handler_id 2
    #dialog.connect("response", self.result_window_response, dialog, window, new_fit)
    # connect dialog to main window
    window.open_windows.append(dialog)
    results.connect("destroy", lambda *w: window.open_windows.remove(dialog))
    response=results.run()
    self.result_window_response(response, dialog, window, new_fit)
    results.destroy()
    
  def result_window_response(self, response, dialog, window, new_fit):
    '''
      depending of response to result window use new fit parameters
      or old ones.
    '''
    if response==1:
      self.fit_object=new_fit
      self.rebuild_dialog(dialog, window)
    else:
      self.fit_object.fit=0
      self.dialog_fit(None, window)

  def rebuild_dialog(self, dialog, window):
    '''
      reopen the fit dialog window to redraw all buttons with a
      new fit_parameters object
    '''
    position=dialog.get_position()
    size=dialog.get_size()
    dialog.destroy()
    self.fit_window(None, window, position=position, size=size)

  def delete_layer(self, action, layer, dialog, window):
    '''
      remove a layer after button is pressed
    '''
    self.fit_object.remove_layer(layer)
    self.rebuild_dialog(dialog, window)
  
  def add_multilayer(self, action, multilayer, dialog, window):
    '''
      add a layer to the multilayer after button is pressed
    '''
    new_layer=fit_layer()
    multilayer.layers.append(new_layer)
    self.rebuild_dialog(dialog, window)
  
  def delete_multilayer(self, action, multilayer, dialog, window):
    '''
      remove a multilayer after button is pressed
    '''
    self.fit_object.layers.remove(multilayer)
    self.rebuild_dialog(dialog, window)

  def dialog_fit(self, action, window):
    '''
      function invoked when apply button is pressed
      fits with the new parameters
    '''
    dataset=window.measurement[window.index_mess]
      # convert x values from angle to q
    dataset.unit_trans([['Theta', '\\302\\260', 4*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}'], \
                      ['2 Theta', '\\302\\260', 2*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}']])    
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=self.x_from, xto=self.x_to)
    self.fit_object.number_of_points=data_lines
    self.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(self.fit_object.get_ent_str()+'\n')
    ent_file.close()
    #open a background process for the fit function
    global proc
    proc = self.call_fit_program(self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp',self.max_iter)
    if self.fit_object.fit!=1: # if this is not a fit just wait till finished
      stderr_value = proc.communicate()[1]
    else:
      self.open_status_dialog(window)
    simu=reflectometer_read_data.read_simulation(self.temp_dir+'fit_temp.sim')
    simu.number='sim_'+dataset.number
    simu.short_info='simulation'
    simu.sample_name=dataset.sample_name
    dataset.plot_together=[dataset, simu]
    window.replot()

  def open_status_dialog(self, window):
    '''
      when fit process is started, create a window with
      status informations and a kill button
    '''
    def status_response(action, response, session, window):
      if response==1: # if the process is abborted, plot without fit
        proc.kill()
        session.fit_object.fit=0
        session.dialog_fit(action, window)
      elif response==2:
        replot_present(session, window)
      
    def replot_present(session, window):
      dataset=window.measurement[window.index_mess]        
      simu=reflectometer_read_data.read_simulation(self.temp_dir+'fit_temp.sim')
      simu.number='sim_'+dataset.number
      simu.short_info='simulation'
      simu.sample_name=dataset.sample_name
      dataset.plot_together=[dataset, simu]
      window.replot()      
    status=gtk.Dialog(title='Fit status after 0 seconds')
    text_view=gtk.TextView()
    # Retrieving a reference to a textbuffer from a textview. 
    buffer = text_view.get_buffer()
    buffer.set_text('')
    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(text_view) # add textbuffer view widget
    status.vbox.add(sw) # add table to dialog box
    status.set_default_size(500,450)
    status.add_button('Plot present simulation',2) # button kill has handler_id 2
    status.add_button('Kill Process',1) # button kill has handler_id 1
    status.connect("response", status_response, self, window)
    status.show_all()
    status.set_modal(True)
    sec=0.2
    start=time.time()
    main_iteration=gtk.main_iteration
    file_name=self.temp_dir+'fit_temp.ref'
    i=0
    # while the process is running ceep reading the .ref output file
    try:
      file=open(file_name, 'r')
    except:
      file=None
      text='Empty .ref file.'
    while proc.poll()==None:
      if i%10==0: # every 10th loop the file is read
        if file==None:
          try:
            file=open(file_name, 'r')
          except:
            file=None
            text='Empty .ref file.'
        else:
          file.seek(0)
          text=file.read()
          if text=='':
            text='Empty .ref file.'
        status.set_title('Fit status after ' + str(round(time.time()-start, 1)) + ' seconds')
        if buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())!=text:
          buffer.set_text(text)
          text_view.scroll_to_iter(buffer.get_end_iter(), 0)
        sec+=0.2
        main_iteration(False)
      else: # the other loops just go to the GTK main loop to paint the dialog
        main_iteration(False)
      i+=1
    file.close()
    # threading does not work in windows!
    #loop=ProcessLoop()
    #loop.active_session=self
    #loop.start()
    #response=status.run()
    status.set_modal(False)
    status.destroy()
  

  def change_scattering_length(self, action, SL_selector, layer, delta, d_over_b, layer_title, layer_index, substrate):
    '''
      function to change a layers scattering length parameters
      when a material is selected
    '''
    name=layer.SL_selector.get_active_text()
    try:
      SL=self.fit_object.scattering_length_densities[name]
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
  
  def toggle_fit_option(self, action, list, number):
    '''
      add or remove parameter from list
    '''
    if number in list:
      list.remove(number)
    else:
      list.append(number)
    list.sort()

  def toggle_fit_bool_option(self, action, dict, value):
    '''
      add or remove parameter from list
    '''
    dict[value]=not dict[value]

  def import_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter import from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new datafile...', action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
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
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    self.fit_object=fit_parameter()
    self.fit_object.read_params_from_file(file_name)
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
    file_handler=open(file_name, 'w')
    file_handler.write(self.fit_object.get_ent_str())
    file_handler.close
    return True
  
  #----------------------- GUI functions -----------------------

  def call_fit_program(self, file_ent, file_res, file_out, max_iter):
    '''
      This function calls the fit.f90 program and if it is not compiled with 
      those settings, will compile it with the number of layres present in 
      the current simulation. For this the maxint parameter in the fit.f90 
      code is replaced by the real number of layers. It does not wait for the 
      program to finish, it only startes the sub process, which is returned.
    '''
    code_file=self.script_path + fit_program_code
    exe=self.script_path + fit_program_executible
    try:
      code_tmp=open(code_file.split('.f90')[0] + '_tmp.f90', 'r').read()
    except IOError:
      code_tmp=' '
    # has the program been changed or does it not exist
    if (not os.path.exists(exe)) or \
      ((os.stat(code_file)[8]-os.stat(exe)[8]) > 0) or \
      (not 'maxint='+str(self.fit_object.number_of_layers()+1) in code_tmp):
      code=open(code_file, 'r').read()
      # compile the program with constants suitable for this dataset
      code_tmp=code.replace('maxint=25', 'maxint='+str(self.fit_object.number_of_layers()+1))
      code_tmp=code_tmp.replace('.and.alamda.le.1.0d10', '.and.alamda.le.1.0d'+str(self.max_alambda))
      code_tmp=code_tmp.replace('.or.alamda.gt.1.0d10', '.or.alamda.gt.1.0d'+str(self.max_alambda))
      tmp_file=open(code_file.split('.f90')[0] + '_tmp.f90', 'w')
      tmp_file.write(code_tmp)
      tmp_file.close()
      print 'Compiling fit program!'
      call_params=[fortran_compiler, code_file.split('.f90')[0] + '_tmp.f90', '-o', exe]
      if  fortran_compiler_options!=None:
        call_params.append(fortran_compiler_options)
      if  fortran_compiler_march!=None:
        call_params.append(fortran_compiler_march)
      subprocess.call(call_params)
      print 'Compiled'
    process = subprocess.Popen([exe, file_ent, file_res, file_out+'.ref', file_out+'.sim', str(max_iter)], 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
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

  def read_fit_file(self, file_name, fit_object):
    '''
      get fit-parameters back from the file
    '''
    parameters=map(str, fit_object.fit_params)
    result={}
    errors={}
    fit_file=open(file_name,'r')
    test_fit=fit_file.readlines()
    fit_file.close()
    for i,line in enumerate(reversed(test_fit)):
      split=line.split()
      if len(split)>0:
        if split[0] in parameters:
          result[int(split[0])]=float(split[1])
          try:
            errors[int(split[0])]=float(split[3])
          except ValueError:
            None
      if len(parameters)==len(result):
          return result, errors
    return None

  def refine_scaling(self, dataset):
    '''
      try to fit the scaling factor before the total reflection angle
    '''
    self.fit_object.fit=1
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=0.005,xto=self.find_total_reflection(dataset))
    self.fit_object.set_fit_parameters(scaling=True) # fit only scaling factor
    self.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(self.fit_object.get_ent_str()+'\n')
    ent_file.close()
    proc = self.call_fit_program(self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp',20)
    retcode = proc.communicate()
    parameters, errors=self.read_fit_file(self.temp_dir+'fit_temp.ref', self.fit_object)
    self.fit_object.scaling_factor=parameters[self.fit_object.fit_params[0]]
    self.fit_object.fit=0
    return retcode

  def refine_roughnesses(self, dataset):
    '''
      try to fit the layer roughnesses
    '''
    self.fit_object.fit=1
    layer_dict={}
    # create parameter dictionary for every (multi)layer, 3 is the roughness
    for i, layer in enumerate(self.fit_object.layers):
      if not layer.multilayer:
        layer_dict[i]=[3]
      else:
        layer_dict[i]=[[3] for j in range(len(layer.layers))]
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=self.find_total_reflection(dataset))
    self.fit_object.set_fit_parameters(layer_params=layer_dict, substrate_params=[2]) # set all roughnesses to be fit
    self.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(self.fit_object.get_ent_str()+'\n')
    ent_file.close()
    proc = self.call_fit_program(self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp',20)
    sec=0.
    while proc.poll()==None:
      time.sleep(0.1)
      sec+=0.1
      sys.stdout.write( '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                        'Script running for % 6dsec' % sec)
      sys.stdout.flush()
    retcode = proc.communicate()
    parameters, errors=self.read_fit_file(self.temp_dir+'fit_temp.ref',self.fit_object)
    self.fit_object.get_parameters(parameters)
    self.fit_object.fit=0
    return retcode

  def export_fit(self, dataset, input_file_name):
    '''
      Function to export data for fitting with fit.f90 program.
    '''
    if self.fit_object.layers==[]:
      #+++++++++++++++++++ create fit parameters object +++++++++++++++++++
      fit_thick=self.fit_thicknesses
      first_split=self.fit_layers.split('-')
      for compound in first_split:
        if compound[-1]==']': # is there a multilayer
          count=int(compound.split('[')[0])
          second_split=compound.split('[')[1].rstrip(']').split('_')
          second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
          self.fit_object.append_multilayer(second_split, map(float, second_thick), [self.fit_est_roughness for i in second_thick], count)
        else: # no multilayer
            if len(fit_thick)>0:
                self.fit_object.append_layer(compound, float(fit_thick.split('-')[0]), self.fit_est_roughness)
            else:
                self.fit_object.append_substrate(compound, self.fit_est_roughness)
        if len(fit_thick.split('-'))>1: # remove first thickness
            fit_thick=fit_thick.split('-',1)[1]
        else:
            fit_thick=''
      #------------------- create fit parameters object -------------------
    self.fit_object.set_fit_constrains() # set constrained parameters for multilayer
      # convert x values from angle to q
    dataset.unit_trans([['Theta', '\\302\\260', 4*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}'], \
                      ['2 Theta', '\\302\\260', 2*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}']])
      # first guess for scaling factor is the maximum intensity
    self.fit_object.scaling_factor=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    self.fit_object.background=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine: 
      print "Try to refine scaling"
      self.refine_scaling(dataset)
      print "Try to refine roughnesses"
      self.refine_roughnesses(dataset)
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
      # write data into files with sequence numbers in format ok for fit.f90    
    data_lines=dataset.export(self.temp_dir+'fit_temp.res',False,' ') 
    self.fit_object.number_of_points=data_lines
    self.fit_object.set_fit_parameters(background=True)
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(self.fit_object.get_ent_str()+'\n')
    ent_file.close()
    print "Simulate the measurement"
    proc = self.call_fit_program(self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp',20)
    retcode = proc.communicate()
    #------- create final input file and make a simulation -------

  #---- functions for fitting with fortran program by E. Kentzinger ----

class fit_parameter:
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  radiation=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
  number_of_points=10 # number of simulated points
  background=0 # constant background intensity
  resolution=3.5 # resolution in q in 1e-3 A^-1
  scaling_factor=1 # intensity of total reflection in 1e6
  theta_max= 2.3 # angle of total coverage for recalibration
  layers=[] # a list storing all layers/multilayers
  substrate=None # data for the substrate
  # fit specifc parameters
  fit=0
  fit_params=[]
  constrains=[]
  
  def __init__(self):
    '''
      class constructor
    '''
    # lookup the scattering length density table
    from scattering_length_table import scattering_length_densities
    self.scattering_length_densities=scattering_length_densities
    self.layers=[]
    self.substrate=None
    self.fit_params=[]
    self.constrains=[]
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.scattering_length_densities[material]
      result=True
    except KeyError:
      SL=[1., 1.]
      material='Unknown'
      result=False
    layer=fit_layer(material, [thickness, SL[0], SL[1], roughness])
    self.layers.append(layer)
    return result

  def remove_layer(self, layer):
    '''
      Remove a layer ither directly or from a multilayer
      inside. Strings of the object have to be compared,
      as __eq__ is defined in fit_layer only by the settings.
    '''
    if str(layer) in map(str, self.layers): # single layer can be removed directly
      self.layers.remove(layer)
    else: # multilayer layers have to be searched first
      for multilayer in [a_layer for a_layer in self.layers if a_layer.multilayer]:
        if str(layer) in map(str, multilayer.layers):
          multilayer.layers.remove(layer)
  
  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.scattering_length_densities[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(fit_layer(materials[i], [thicknesses[i], SL[0], SL[1], roughnesses[i]]))
    multilayer=fit_multilayer(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
    None
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.scattering_length_densities[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1., 1.]
      result=False
    layer=fit_layer(material, [0., SL[0], SL[1], roughness])
    self.substrate=layer
    return result
    
  def get_ent_str(self):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.number_of_layers() + 1) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string+='#### Begin of layers, first layer '
    # layers and parameters are numbered started with 1
    layer_index=1
    para_index=1
    # add text for every (multi)layer
    for layer in self.layers:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    # substrate data
    string,  layer_index, para_index=self.substrate.get_ent_text(layer_index, para_index-1)
    ent_string+='\n'.join([string.splitlines()[0]]+string.splitlines()[2:]) + '\n' # cut the thickness line
    ent_string+='### End of layers.\n'
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
      set fit constrains depending on (multi)layers
      layer_params is a dictionary with the layer number as index
    '''
    fit_cons=[]
    con_index=1
    for layer in self.layers:
      if layer.multilayer: # for every multilayer add constrains
        new_con, con_index=layer.get_fit_cons(con_index)
        fit_cons+=new_con
      else:
        con_index+=4
    self.constrains=[]
    # remove constrains not importent for the fitted parameters
    for constrain in fit_cons:
      if constrain[0] in self.fit_params:
        self.constrains.append(constrain)

  def copy(self):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit=fit_parameter()
    new_fit.radiation=copy(self.radiation)
    new_fit.number_of_points=self.number_of_points
    new_fit.background=self.background
    new_fit.resolution=self.resolution
    new_fit.scaling_factor=self.scaling_factor
    new_fit.theta_max=self.theta_max
    new_fit.layers=[layer.copy() for layer in self.layers]
    new_fit.substrate=self.substrate.copy()
    new_fit.fit=self.fit
    new_fit.fit_params=copy(self.fit_params)
    new_fit.constrains=copy(self.constrains)
    return new_fit

  def number_of_layers(self):
    '''
      calculate the number of layers in the file as the layer list can
      contain multilayer elements
    '''
    i=0
    for layer in self.layers:
      i+=len(layer)
    return i
  
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
      layer=fit_layer(name=name, parameters_list=parameters)
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
    self.substrate=fit_layer(name=name, parameters_list=parameters)
    # read last parameters
    lines.pop()
    self.background=float(lines.pop().split()[0])
    self.resolution=float(lines.pop().split()[0])
    self.scaling_factor=float(lines.pop().split()[0])
    lines.pop()
    self.theta_max=float(lines.pop().split()[0])
    self.combine_layers()

  def combine_layers(self):
    '''
      Function which tries to combine layers with the same parameters
      to a multilayer object. This needs a lot of list processing
      but essentially, it creates a list of periodically equal
      layers and changes these in the layers list to multilayers.
    '''
    candidates=[]
    for i, layer in enumerate(self.layers):
      for candidate in candidates:
        if i<candidate[1]:
          if i-candidate[0]+candidate[1]<len(self.layers) and\
            i-candidate[0]-candidate[1]>=0:
            if layer!=self.layers[i-candidate[0]+candidate[1]] and\
              layer!=self.layers[i-candidate[0]-candidate[1]]:
              candidates.remove(candidate)
      for j, layer2 in enumerate(self.layers[i+1:]):
        if layer==layer2:
          candidates.append([i, j+i+1])
    remove=[]
    # first delete all candidates, which have larger distances
    for i, candidate in enumerate(candidates):
      for candidate2 in candidates[i+1:]:
        if candidate2[0]==candidate[0] and not candidate2 in remove:
          remove.append(candidate2)
    for remover in remove:
      candidates.remove(remover)
    remove=[]
    # now combine followup repititions
    for i, candidate in enumerate(candidates):
      for candidate2 in candidates[i+1:]:
        if candidate2[0]==candidate[-1] and not candidate2 in remove:
          candidate.append(candidate2[1])
          remove.append(candidate2)
    for remover in remove:
      candidates.remove(remover)
    # now we have lists of layers with the same settings, 
    # we only have to create the multilayers and delete them
    multilayers=[]
    remove_layers=[]
    start_indices=[]
    while len(candidates)>0:
      from copy import deepcopy as copy
      first=copy(candidates[0])
      layers_in=[]
      for i in range(first[1]-first[0]):
        remove_layers+=[self.layers[j] for j in candidates[i]]
        layers_in.append(self.layers[first[0]+i])
      for i in range(first[1]-first[0]):
        candidates.pop(0)
      multilayers.append([len(first), layers_in]) # [repititions, layers]
      start_indices.append(first[0])
    new_layers=[]
    i=0
    while self.layers!=[]:
      if not self.layers[0] in remove_layers:
        new_layers.append(self.layers.pop(0))
      elif len(start_indices)>0 and i==start_indices[0]:
        start_indices.pop(0)
        new=multilayers.pop(0)
        new_multilayer=fit_multilayer(new[0], layer_list=new[1])
        new_layers.append(new_multilayer)
        self.layers.pop(0)
      else:
        self.layers.pop(0)
      i+=1
    self.layers=new_layers
    


class fit_layer:
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  multilayer=False
  name=''
  thickness=1
  delta=1
  d_over_b=1
  roughness=1
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    self.name=name
    if parameters_list!=None:
      self.thickness=parameters_list[0]
      self.delta=parameters_list[1]
      self.d_over_b=parameters_list[2]
      self.roughness=parameters_list[3]
    else:
      self.multilayer=False
      self.name=''
      self.thickness=1
      self.delta=1
      self.d_over_b=1
      self.roughness=1
  
  def __len__(self):
    '''
      length is just one layer, see multilayers
    '''
    return 1
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    if self.multilayer==other.multilayer and\
          self.thickness==other.thickness and\
          self.delta==other.delta and\
          self.d_over_b==other.d_over_b and\
          self.roughness==other.roughness:
      return True
    else:
      return False
  
  def __ne__(self, other):
    return not self.__eq__(other)
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return fit_layer(name=self.name, \
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
    try:
      self.thickness=float(thickness.get_text())
      self.delta=float(delta.get_text())
      self.d_over_b=float(d_over_b.get_text())
      self.roughness=float(roughness.get_text())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==0: 
      self.thickness=value
    elif index==1: 
      self.delta=value
    elif index==2: 
      self.d_over_b=value
    elif index==3: 
      self.roughness=value
  
  def get_ent_text(self, layer_index, para_index):
    '''
      Function to get the text lines for the .ent file.
      Returns the text string and the parameter index increased
      by the number of parameters for the layer.
    '''
    text='# ' + str(layer_index) + ': ' + self.name + '\n' # Name comment
    text+=str(self.thickness) + '\tlayer thickness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.roughness) + '\tlayer roughness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class fit_multilayer:
  '''
    class for multilayer data
  '''
  name=''
  repititions=1 # number of times these layers will be repeated
  multilayer=True
  
  def __init__(self, repititions=1, name='NoName', layer_list=None):
    '''
      class constructor
    '''
    self.repititions=repititions
    self.name=name
    if layer_list!=None:
      self.layers=layer_list
    else:
      self.layers=[]
  
  def __len__(self):
    '''
      length of the object is length of the layers list * repititions
    '''
    return len(self.layers) * self.repititions

  def copy(self):
    '''
      create a copy of this object
    '''
    new_multilayer=fit_multilayer(name=self.name)
    new_multilayer.repititions=self.repititions
    new_multilayer.layers=[layer.copy() for layer in self.layers]
    return new_multilayer

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
  
  def dialog_get_params(self, action, response, repititions):
    '''
      function to get parameters from the GUI dialog
    '''
    try:
      self.repititions=int(repititions.get_text())
    except ValueError:
      None
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    for j in range(layers): # iterate through layers
      for i in range(4): # iterate through parameters
        list.append([param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)])
    return list, param_index + len(self)
  

  def get_ent_text(self, layer_index, para_index):
    '''
      Function to get the text lines for the .ent file.
      Returns the text string and the parameter index increased
      by the number of parameters for the layers.
    '''
    text='# Begin of multilay ' + self.name
    for i in range(self.repititions): # repead all layers
      for layer in self.layers: # add text for every layer
        string, layer_index, para_index = layer.get_ent_text(layer_index, para_index)
        text+=string
    return text,  layer_index,  para_index
  

class ProcessLoop(threading.Thread):
  '''
    to make it possible to kill the fit process while GTK outputs
    the data, we have to create a looping thread
  '''
  active_session=None

  def run(self):
    '''
      Standart function called from Thread.start().
      While the fit program is running, the .ref file
      is regularly read and shown in the status dialog.
    '''
    global status, text_view
    sec=0    
    buffer=text_view.get_buffer()
    while proc.poll()==None:
      try:
        file=open(self.active_session.temp_dir+'fit_temp.ref', 'r')
        text=file.read()
        file.close()
        if text=='':
          text='Empty .ref file.'
      except:
        text='Empty .ref file.'
      gtk.gdk.threads_enter()
      status.set_title('Fit status after ' + str(sec/5) + ' seconds')
      buffer.set_text(text)
      position=buffer.get_end_iter()
      text_view.scroll_to_iter(position, 0)
      gtk.gdk.threads_leave()
      time.sleep(0.2)
      sec+=1
    gtk.gdk.threads_enter()
    status.destroy()
    gtk.gdk.threads_leave()
