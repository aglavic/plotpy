# -*- encoding: utf-8 -*-
'''
  Reflectometer GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
import os
import math
# own modules
import read_data.reflectometer
from sessions.reflectometer_fit.reflectometer import *

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class ReflectometerGUI:
  '''
    Reflectometer GUI functions for GTK toolkit.
  '''
  
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
      layer_title=gtk.Entry()
      layer_title.connect('key-press-event', self.change_layer_name, layer)
      if not substrate:
        layer_title.set_text(str(layer_index + 1) + ' - ' + layer.name)
        align_table.attach(layer_title, 0, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
        thickness_x=gtk.CheckButton(label='thickness', use_underline=True)
        thickness_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 0)
        align_table.attach(thickness_x, 0, 1, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      else:
        layer_title.set_text('Substrate - ' + layer.name)
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
  
  def change_layer_name(self, widget, action, layer):
    '''
      Change the name of a layer, when anything is entered in the entryfield.
    '''
    text=widget.get_text()
    try:
      name=text.split('-', 1)[1].lstrip()
      layer.name=name
    except IndexError:
      layer.name=text
  
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
    self.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', 
                                      self.TEMP_DIR+'fit_temp',self.max_iter)
    print "fit.f90 program started."
    if self.active_file_data.fit_object.fit!=1: # if this is not a fit just wait till finished
      exec_time, stderr_value = self.proc.communicate()
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
        layer_title.set_text('Substrate - ' + layer.name)
      else:
        layer_title.set_text(str(layer_index + 1) + ' - ' + layer.name)
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

  def dialog_get_SL_online(self):
    '''
      Open a dialog to retrieve delta and beta online via http://henke.lbl.gov.
    '''
    dialog=gtk.Dialog()
  