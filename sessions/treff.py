#!/usr/bin/env python
'''
  class for treff data sessions
'''
#################################################################################################
#                      Script to plot TREFF-measurements with gnuplot                           #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
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
# importing data readout
import read_data.treff
import config.treff

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Ulrich Ruecker", "Emmanuel Kentzinger", "Paul Zakalek"]
__license__ = "None"
__version__ = "0.6b2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class TreffSession(GenericSession):
  '''
    Class to handle treff data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tTREFF-Data treatment:
\t-no-img\tOnly import the detector window data, not the 2d-maps.
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('Filtered', '*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]'), ('All','*'))  
  TRANSFORMATIONS=[\
                  ['mrad',1/config.treff.GRAD_TO_MRAD,0,'\302\260'],
                  ['detector', 'mrad', 1., 0, '2Theta', 'mrad'], 
                  ['detector', 'rad', 1., 0, '2Theta', 'rad'], 
                  ['detector', '\302\260', 1., 0, '2Theta', '\302\260'], 
                  ]  
  import_images=True
  fit_object=None # used for storing the fit parameters
  fit_datasets=[None, None, None, None] # a list of datasets used for fit [++,--,+-,-+]
  fit_object_history=[]
  fit_object_future=[]
  x_from=5 # fit only x regions between x_from and x_to
  x_to=''
  max_iter=50 # maximal iterations in fit
  max_hr=5000 # Parameter in fit_pnr_multi
  max_alambda=10 # maximal power of 10 which alamda should reach in fit.f90
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['no-img']  
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.fit_object=TreffFitParameters() # create a new empty TreffFitParameters object
    self.RESULT_FILE=config.treff.RESULT_FILE
    GenericSession.__init__(self, arguments)
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        found=False
      elif argument=='-no-img':
        self.import_images=False
        found=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.treff.read_data(file_name, self.SCRIPT_PATH, self.import_images)


  def create_menu(self):
    '''
      create a specifig menu for the TREFF session
    '''
    # Create XML for squid menu
    string='''
      <menu action='TreffMenu'>
        <menuitem action='TreffFit'/>
        <menuitem action='TreffSelectPol'/>
        <menuitem action='TreffImportFit'/>
        <menuitem action='TreffExportFit'/>
        <menuitem action='TreffSpecRef'/>
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "TreffMenu", None,                             # name, stock id
                "TREFF", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "TreffFit", None,                             # name, stock id
                "Fit...", None,                    # label, accelerator
                None,                                   # tooltip
                self.fit_window ),
            ( "TreffSpecRef", None,                             # name, stock id
                "Extract specular reflectivity...", None,                    # label, accelerator
                None,                                   # tooltip
                self.extract_specular_reflectivity), 
            ( "TreffSelectPol", None,                             # name, stock id
                "Select polarization channels...", None,                    # label, accelerator
                None,                                   # tooltip
                self.select_fittable_sequences), 
            ( "TreffExportFit", None,                             # name, stock id
                "Export Fit...", None,                    # label, accelerator
                None,                                   # tooltip
                self.export_fit_dialog), 
            ( "TreffImportFit", None,                             # name, stock id
                "Import Fit...", None,                    # label, accelerator
                None,                                   # tooltip
                self.import_fit_dialog), 
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def extract_specular_reflectivity(self, action, window):
    '''
      Open a dialog for the extraction of the specular line from a 3d image.
      The user can select the width for the cross-section,
      after this the data is extracted and appendet to the fileobject.
    '''
    data=window.measurement[window.index_mess]
    dimension_names=[]
    dims=data.dimensions()
    dimension_names.append(dims[data.xdata])
    dimension_names.append(dims[data.ydata])
    del(dims)
    cs_dialog=gtk.Dialog(title='Create a cross-section:')
    table=gtk.Table(3,7,False)
    label=gtk.Label()
    label.set_markup('Width:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      5, 6,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    line_width=gtk.Entry()
    line_width.set_width_chars(6)
    line_width.set_text('0.1')
    table.attach(line_width,
                # X direction #          # Y direction
                1, 3,                      5, 6,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Binning:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      6, 7,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    binning=gtk.Entry()
    binning.set_width_chars(4)
    binning.set_text('10')
    table.attach(binning,
                # X direction #          # Y direction
                1, 3,                      6, 7,
                0,                       gtk.FILL,
                0,                         0);
    weight=gtk.CheckButton(label='Gauss weighting, Sigma:', use_underline=True)
    weight.set_active(True)
    table.attach(weight,
                # X direction #          # Y direction
                0, 2,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    sigma=gtk.Entry()
    sigma.set_width_chars(4)
    sigma.set_text('0.04')
    table.attach(sigma,
                # X direction #          # Y direction
                2, 3,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    table.show_all()
    # Enty activation triggers calculation, too
    line_width.connect('activate', lambda *ign: cs_dialog.response(1))
    binning.connect('activate', lambda *ign: cs_dialog.response(1))
    sigma.connect('activate', lambda *ign: cs_dialog.response(1))
    cs_dialog.vbox.add(table)
    cs_dialog.add_button('OK', 1)
    cs_dialog.add_button('Cancel', 0)
    result=cs_dialog.run()
    if result==1:
      gotit=window.file_actions.activate_action('cross-section', 
                                        1.0, 
                                        0.0, 
                                        1.0, 
                                        0.0, 
                                        float(line_width.get_text()), 
                                        int(binning.get_text()), 
                                        weight.get_active(), 
                                        float(sigma.get_text()), 
                                        True
                                        )
      if not gotit:
        message=gtk.MessageDialog(parent=self, 
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
    else:
      gotit=False
    cs_dialog.destroy()
    if gotit:
      window.file_actions.activate_action('unit_transformations', 
                                          [['1 \316\261_i + 1 \316\261_f', '\302\260', math.pi/180.*1000, 0, '2Theta', 'mrad'], 
                                          ['1 \316\261_i + 1 \316\261_f', 'mrad', 1., 0, '2Theta', 'mrad'], 
                                          ['1 \316\261_i + 1 \316\261_f', 'rad', 1., 0, '2Theta', 'rad']])
      window.rebuild_menus()
      window.replot()      
    return gotit

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

  def select_fittable_sequences(self, action, window):
    '''
      A dialog to select the sequences for the 4 polarization chanels.
      Not selected items will be ignored during fit process.
    '''
    align_table=gtk.Table(2, 4, False)
    selection_dialog=gtk.Dialog(title="Select polarization channels...")
    object_box_1=gtk.combo_box_new_text()
    object_box_1.append_text('None')
    object_box_2=gtk.combo_box_new_text()
    object_box_2.append_text('None')
    object_box_3=gtk.combo_box_new_text()
    object_box_3.append_text('None')
    object_box_4=gtk.combo_box_new_text()
    object_box_4.append_text('None')
    for i, object in enumerate(self.active_file_data):
      object_box_1.append_text(str(i)+'-('+object.short_info+')')
      object_box_2.append_text(str(i)+'-('+object.short_info+')')
      object_box_3.append_text(str(i)+'-('+object.short_info+')')
      object_box_4.append_text(str(i)+'-('+object.short_info+')')
    text_filed=gtk.Label()
    text_filed.set_markup('Up-Up-Channel: ')      
    align_table.attach(text_filed, 0, 1,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    align_table.attach(object_box_1, 1, 2,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Down-Down-Channel: ')      
    align_table.attach(text_filed, 0, 1,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    align_table.attach(object_box_2, 1, 2,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Up-Down-Channel: ')      
    align_table.attach(text_filed, 0, 1,  2, 3, gtk.FILL, gtk.FILL, 0, 3)
    align_table.attach(object_box_3, 1, 2,  2, 3, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Down-Up-Channel: ')      
    align_table.attach(text_filed, 0, 1,  3, 4, gtk.FILL, gtk.FILL, 0, 3)
    align_table.attach(object_box_4, 1, 2,  3, 4, gtk.FILL, gtk.FILL, 0, 3)
    if any(self.fit_datasets):
      indices=[]
      for item in self.fit_datasets:
        if item:
          indices.append(self.active_file_data.index(item)+1)
        else:
          indices.append(0)
      object_box_1.set_active(indices[0])
      object_box_2.set_active(indices[1])
      object_box_3.set_active(indices[2])
      object_box_4.set_active(indices[3])
    else:
      if len(self.active_file_data)==8:
        object_box_1.set_active(5)
        object_box_2.set_active(6)
        object_box_3.set_active(7)
        object_box_4.set_active(8)
      else:
        object_box_1.set_active(0)
        object_box_2.set_active(0)
        object_box_3.set_active(0)
        object_box_4.set_active(0)
    selection_dialog.add_button('OK', 1)
    selection_dialog.add_button('Cancel', 0)
    selection_dialog.vbox.add(align_table)
    selection_dialog.set_default_size(200, 60)
    selection_dialog.show_all()
    if selection_dialog.run() == 1:
      set_list=[None] + self.active_file_data
      self.fit_datasets=[set_list[object_box_1.get_active()], 
                        set_list[object_box_2.get_active()], 
                        set_list[object_box_3.get_active()], 
                        set_list[object_box_4.get_active()]]
      for object in self.fit_datasets:
        if object:
          object.logy=True
      selection_dialog.destroy()
      return True
    else:
      selection_dialog.destroy()
      return False


  def fit_window(self, action, window, position=None, size=[650, 600]):
    '''
      create a dialog window for the fit options
    '''
    # if no dataset is selected open the selection dialog
    if not any(self.fit_datasets):
      if not self.select_fittable_sequences(action, window):
        return False
    if self.fit_object.layers==[]:
      self.fit_object.append_layer('Unknown', 10., 5.)
      self.fit_object.append_substrate('Unknown', 5.)
    layer_options={}
    layer_index=0
    layer_params={}
    fit_params={
              'wavelength':False, 
              'polarizer_efficiancy': False, 
              'analyzer_efficiancy': False, 
              'flipper0_efficiancy': False, 
              'flipper1_efficiancy': False, 
              'scaling':False, 
              'background':False, 
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
    align_table=gtk.Table(5, 3, False)
    align_table.set_col_spacings(5)
    text_filed=gtk.Label()
    text_filed.set_markup('1st slit:')
    align_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    first_slit=gtk.Entry()
    first_slit.set_width_chars(10)
    first_slit.set_text(str(self.fit_object.slits[0]))
    # activating the input will apply the settings, too
    first_slit.connect('activate', self.dialog_activate, dialog)
    align_table.attach(first_slit, 0, 1,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('2nd slit:')
    align_table.attach(text_filed, 1, 2, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    second_slit=gtk.Entry()
    second_slit.set_width_chars(10)
    second_slit.set_text(str(self.fit_object.slits[1]))
    # activating the input will apply the settings, too
    second_slit.connect('activate', self.dialog_activate, dialog)
    align_table.attach(second_slit, 1, 2,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Smpl length:')
    align_table.attach(text_filed, 2, 3, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    length=gtk.Entry()
    length.set_width_chars(10)
    length.set_text(str(self.fit_object.sample_length))
    # activating the input will apply the settings, too
    length.connect('activate', self.dialog_activate, dialog)
    align_table.attach(length, 2, 3,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Dist. to 1st:')
    align_table.attach(text_filed, 3, 4, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    first_distance=gtk.Entry()
    first_distance.set_width_chars(10)
    first_distance.set_text(str(self.fit_object.distances[0]))
    # activating the input will apply the settings, too
    first_distance.connect('activate', self.dialog_activate, dialog)
    align_table.attach(first_distance, 3, 4,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Dist. to 2nd:')
    align_table.attach(text_filed, 4, 5, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    second_distance=gtk.Entry()
    second_distance.set_width_chars(10)
    second_distance.set_text(str(self.fit_object.distances[1]))
    # activating the input will apply the settings, too
    second_distance.connect('activate', self.dialog_activate, dialog)
    align_table.attach(second_distance, 4, 5,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    
    wavelength_table=gtk.Table(4, 1, False)
    text_filed=gtk.Label()
    text_filed.set_markup('Wavelength:')
    wavelength_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    wavelength=gtk.Entry()
    wavelength.set_width_chars(5)
    wavelength.set_text(str(self.fit_object.wavelength[0]))
    # activating the input will apply the settings, too
    wavelength.connect('activate', self.dialog_activate, dialog)
    wavelength_table.attach(wavelength, 1, 2,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('+/-')
    wavelength_table.attach(text_filed, 2, 3, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    delta_wavelength=gtk.Entry()
    delta_wavelength.set_width_chars(5)
    delta_wavelength.set_text(str(self.fit_object.wavelength[1]))
    # activating the input will apply the settings, too
    wavelength.connect('activate', self.dialog_activate, dialog)
    wavelength_table.attach(delta_wavelength, 3, 4,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    align_table.attach(wavelength_table, 0, 2,  2, 3, gtk.FILL, gtk.FILL, 0, 0)
    text_filed=gtk.Label()
    text_filed.set_markup('x-region')
    align_table.attach(text_filed, 2, 3,  2, 3, gtk.FILL, gtk.FILL, 0, 0)
    x_from=gtk.Entry()
    x_from.set_width_chars(10)
    x_from.set_text(str(self.x_from))
    # activating the input will apply the settings, too
    x_from.connect('activate', self.dialog_activate, dialog)
    align_table.attach(x_from, 3, 4,  2, 3, gtk.FILL, gtk.FILL, 0, 0)
    x_to=gtk.Entry()
    x_to.set_width_chars(10)
    x_to.set_text(str(self.x_to))
    # activating the input will apply the settings, too
    x_to.connect('activate', self.dialog_activate, dialog)
    align_table.attach(x_to, 4, 5, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
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
    align_table=gtk.Table(4, 8, False)
    align_table.set_col_spacings(10)
    text_filed=gtk.Label()
    text_filed.set_markup('Additional global parameters: ')
    align_table.attach(text_filed, 0, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 5)
    background_x=gtk.CheckButton(label='Background: ', use_underline=True)
    background_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'background')
    align_table.attach(background_x, 0, 1, 2, 3, gtk.FILL,  gtk.FILL, 0, 0)
    background=gtk.Entry()
    background.set_width_chars(10)
    background.set_text(str(self.fit_object.background))
    # activating the input will apply the settings, too
    background.connect('activate', self.dialog_activate, dialog)
    align_table.attach(background, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)   
    scaling_x=gtk.CheckButton(label='Scaling: ', use_underline=True)
    scaling_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'scaling')
    align_table.attach(scaling_x, 0, 1, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    scaling_factor=gtk.Entry()
    scaling_factor.set_width_chars(10)
    scaling_factor.set_text(str(self.fit_object.scaling_factor))
    # activating the input will apply the settings, too
    scaling_factor.connect('activate', self.dialog_activate, dialog)
    align_table.attach(scaling_factor, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)   
    
    text_filed=gtk.Label()
    text_filed.set_markup('Efficiencies: ')
    align_table.attach(text_filed, 2, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
    polarizer_efficiancy_x=gtk.CheckButton(label='Polarizer: ', use_underline=True)
    polarizer_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'polarizer_efficiancy')
    align_table.attach(polarizer_efficiancy_x, 2, 3, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    polarizer_efficiancy=gtk.Entry()
    polarizer_efficiancy.set_width_chars(10)
    polarizer_efficiancy.set_text(str(self.fit_object.polarization_parameters[0]))
    # activating the input will apply the settings, too
    polarizer_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(polarizer_efficiancy, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    analyzer_efficiancy_x=gtk.CheckButton(label='Analyzer: ', use_underline=True)
    analyzer_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'analyzer_efficiancy')
    align_table.attach(analyzer_efficiancy_x, 2, 3, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    analyzer_efficiancy=gtk.Entry()
    analyzer_efficiancy.set_width_chars(10)
    analyzer_efficiancy.set_text(str(self.fit_object.polarization_parameters[1]))
    # activating the input will apply the settings, too
    analyzer_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(analyzer_efficiancy, 3, 4, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    flipper0_efficiancy_x=gtk.CheckButton(label='1st Flipper: ', use_underline=True)
    flipper0_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'flipper0_efficiancy')
    align_table.attach(flipper0_efficiancy_x, 2, 3, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    flipper0_efficiancy=gtk.Entry()
    flipper0_efficiancy.set_width_chars(10)
    flipper0_efficiancy.set_text(str(self.fit_object.polarization_parameters[2]))
    # activating the input will apply the settings, too
    flipper0_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(flipper0_efficiancy, 3, 4, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    flipper1_efficiancy_x=gtk.CheckButton(label='2nd Flipper: ', use_underline=True)
    flipper1_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'flipper1_efficiancy')
    align_table.attach(flipper1_efficiancy_x, 2, 3, 5, 6, gtk.FILL, gtk.FILL, 0, 0)
    flipper1_efficiancy=gtk.Entry()
    flipper1_efficiancy.set_width_chars(10)
    flipper1_efficiancy.set_text(str(self.fit_object.polarization_parameters[3]))
    # activating the input will apply the settings, too
    flipper1_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(flipper1_efficiancy, 3, 4, 5, 6, gtk.FILL, gtk.FILL, 0, 0)
    
    # fit-settings
    fit_x=gtk.CheckButton(label='Fit selected', use_underline=True)
    fit_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'actually')
    align_table.attach(fit_x, 0, 2, 5, 6, gtk.FILL, gtk.FILL, 0, 0)
    max_iter=gtk.Entry()
    max_iter.set_width_chars(4)
    max_iter.set_text(str(self.max_iter))
    # activating the input will apply the settings, too
    max_iter.connect('activate', self.dialog_activate, dialog)
    align_table.attach(max_iter, 0, 1, 4, 5, 0, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('max. iterations')
    align_table.attach(text_filed, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    text_filed=gtk.Label()
    text_filed.set_markup('Alambda 1st:')
    align_table.attach(text_filed, 0, 1, 6, 7, gtk.FILL, gtk.FILL, 0, 0)
    alambda_first=gtk.Entry()
    alambda_first.set_width_chars(10)
    alambda_first.set_text(str(self.fit_object.alambda_first))
    # activating the input will apply the settings, too
    alambda_first.connect('activate', self.dialog_activate, dialog)
    align_table.attach(alambda_first, 1, 2, 6, 7, 0, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('nTest')
    align_table.attach(text_filed, 0, 1, 7, 8, gtk.FILL, gtk.FILL, 0, 0)
    ntest=gtk.Entry()
    ntest.set_width_chars(2)
    ntest.set_text(str(self.fit_object.ntest))
    # activating the input will apply the settings, too
    ntest.connect('activate', self.dialog_activate, dialog)
    align_table.attach(ntest, 1, 2, 7, 8, 0, gtk.FILL, 0, 0)   
    
    text_filed=gtk.Label()
    text_filed.set_markup('max_hr')
    align_table.attach(text_filed, 0, 1, 8, 9, gtk.FILL, gtk.FILL, 0, 0)
    max_hr=gtk.Entry()
    max_hr.set_width_chars(4)
    max_hr.set_text(str(self.max_hr))
    # activating the input will apply the settings, too
    ntest.connect('activate', self.dialog_activate, dialog)
    align_table.attach(max_hr, 1, 2, 8, 9, 0, gtk.FILL, 0, 0)   
    if self.fit_object_history!=[]:
      history_back=gtk.Button(label='Undo (%i)' % len(self.fit_object_history), use_underline=True)
      history_back.connect('clicked', self.fit_history, True, dialog, window)
      align_table.attach(history_back, 2, 3, 7, 8, gtk.FILL, gtk.FILL, 0, 0)
    if self.fit_object_future!=[]:
      history_forward=gtk.Button(label='Redo (%i)' % len(self.fit_object_future), use_underline=True)
      history_forward.connect('clicked', self.fit_history, False, dialog, window)
      align_table.attach(history_forward, 3, 4, 7, 8, gtk.FILL, gtk.FILL, 0, 0)
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
    dialog.connect("response", self.dialog_response, dialog, window,
                   [wavelength, background, 
                   [first_slit, second_slit], 
                   scaling_factor, 
                   [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy], 
                   alambda_first, ntest, x_from, x_to, max_hr],
                   [layer_params, fit_params, max_iter])
    # befor the widget gets destroyed the textbuffer view widget is removed
    #dialog.connect("destroy",self.close_plot_options_window,sw) 
    dialog.show_all()
    # connect dialog to main window
    window.open_windows.append(dialog)
    dialog.connect("destroy", lambda *w: window.open_windows.remove(dialog))

  def stop_scroll_emission(self, SL_selector, action):
    '''Stop scrolling event when ontop of seleciton dialog.'''
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
      align_table=gtk.Table(5, 5, False)
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
      scatter_density_Nb_x=gtk.CheckButton(label='Nb\'', use_underline=True)
      scatter_density_Nb_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 1)
      align_table.attach(scatter_density_Nb_x, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      scatter_density_Nb2_x=gtk.CheckButton(label='Nb\'\'', use_underline=True)
      scatter_density_Nb2_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 2)
      align_table.attach(scatter_density_Nb2_x, 2, 3, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      scatter_density_Np_x=gtk.CheckButton(label='Np', use_underline=True)
      scatter_density_Np_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 3)
      align_table.attach(scatter_density_Np_x, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      theta_x=gtk.CheckButton(label='theta', use_underline=True)
      theta_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 4)
      align_table.attach(theta_x, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
      phi_x=gtk.CheckButton(label='phi', use_underline=True)
      phi_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 5)
      align_table.attach(phi_x, 2, 3, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
      roughness_x=gtk.CheckButton(label='roughness', use_underline=True)
      roughness_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 6)
      align_table.attach(roughness_x, 3, 4, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
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
        align_table.attach(delete, 4, 5, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
        delete=gtk.Button(label='UP', use_underline=True)
        delete.connect('clicked', self.up_layer, layer, dialog, window)
        align_table.attach(delete, 4, 5, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
      scatter_density_Nb=gtk.Entry()
      scatter_density_Nb.set_width_chars(10)
      scatter_density_Nb.set_text(str(layer.scatter_density_Nb))
      # activating the input will apply the settings, too
      scatter_density_Nb.connect('activate', self.dialog_activate, dialog)
      align_table.attach(scatter_density_Nb, 1, 2, 2, 3, gtk.FILL,  gtk.FILL, 0, 0)
      scatter_density_Nb2=gtk.Entry()
      scatter_density_Nb2.set_width_chars(10)
      scatter_density_Nb2.set_text(str(layer.scatter_density_Nb2))
      # activating the input will apply the settings, too
      scatter_density_Nb2.connect('activate', self.dialog_activate, dialog)
      align_table.attach(scatter_density_Nb2, 2, 3, 2, 3, gtk.FILL,  gtk.FILL, 0, 0)
      scatter_density_Np=gtk.Entry()
      scatter_density_Np.set_width_chars(12)
      scatter_density_Np.set_text(str(layer.scatter_density_Np))
      # activating the input will apply the settings, too
      scatter_density_Np.connect('activate', self.dialog_activate, dialog)
      align_table.attach(scatter_density_Np, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      # selection dialog for material
      SL_selector=gtk.combo_box_new_text()
      SL_selector.append_text('SL')
      SL_selector.set_active(0)
      for i, SL in enumerate(sorted(self.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES.items())):
        SL_selector.append_text(SL[0])
        if layer.scatter_density_Nb==SL[1][0] and layer.scatter_density_Nb2==SL[1][1] and layer.scatter_density_Np==SL[1][2]:
          SL_selector.set_active(i+1)
      SL_selector.allowed=False
      SL_selector.connect('scroll-event', self.stop_scroll_emission)
      SL_selector.connect('changed', self.change_scattering_length, \
                          SL_selector, layer,scatter_density_Nb, scatter_density_Nb2, scatter_density_Np, \
                          layer_title, layer_index, substrate)
      layer.SL_selector=SL_selector
      align_table.attach(SL_selector, 4, 5, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
      theta=gtk.Entry()
      theta.set_width_chars(12)
      theta.set_text(str(layer.theta))
      # activating the input will apply the settings, too
      theta.connect('activate', self.dialog_activate, dialog)
      align_table.attach(theta, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
      phi=gtk.Entry()
      phi.set_width_chars(12)
      phi.set_text(str(layer.phi))
      # activating the input will apply the settings, too
      phi.connect('activate', self.dialog_activate, dialog)
      align_table.attach(phi, 2, 3, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
      roughness=gtk.Entry()
      roughness.set_width_chars(10)
      roughness.set_text(str(layer.roughness))
      # activating the input will apply the settings, too
      roughness.connect('activate', self.dialog_activate, dialog)
      align_table.attach(roughness, 3, 4, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
      # when apply button is pressed or field gets activated, send data
      dialog.connect('response', layer.dialog_get_params, thickness, scatter_density_Nb, scatter_density_Nb2, scatter_density_Np, theta, phi, roughness) # when apply button is pressed, send data
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
  
  def change_scattering_length(self, action, SL_selector, layer, scatter_density_Nb, scatter_density_Nb2, scatter_density_Np, layer_title, layer_index, substrate):
    '''
      function to change a layers scattering length parameters
      when a material is selected
    '''
    name=layer.SL_selector.get_active_text()
    try:
      SL=self.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES[name]
      layer.name=name
      scatter_density_Nb.set_text(str(SL[0]))
      scatter_density_Nb2.set_text(str(SL[1]))
      scatter_density_Np.set_text(str(SL[2]))
      if substrate:
        layer_title.set_markup('Substrate - ' + layer.name)
      else:
        layer_title.set_markup(str(layer_index + 1) + ' - ' + layer.name)
    except KeyError:
      scatter_density_Nb.set_text("1")
      scatter_density_Nb2.set_text("1")
      scatter_density_Np.set_text("1")
  
  def dialog_response(self, action, response, dialog, window, parameters_list, fit_list):
    '''
      Handle fit dialog response.
    '''
    if response>=5:
      try:
        self.fit_object.wavelength[0]=float(parameters_list[0].get_text())
        self.fit_object.background=float(parameters_list[1].get_text())
        self.fit_object.slits=map(float, map(lambda item: item.get_text(), parameters_list[2]))
        self.fit_object.scaling_factor=float(parameters_list[3].get_text())
        self.fit_object.polarization_parameters=map(float, map(lambda item: item.get_text(), parameters_list[4]))
        self.fit_object.alambda_first=float(parameters_list[5].get_text())
        self.fit_object.ntest=int(parameters_list[6].get_text())
      except ValueError:
        None
      try:
        max_hr_new=int(parameters_list[9].get_text())
        if max_hr_new!=self.max_hr:
          self.max_hr=max_hr_new
          new_max_hr=True
        else:
          new_max_hr=False
      except ValueError:
        new_max_hr=False
      try:
        self.x_from=float(parameters_list[7].get_text())
      except ValueError:
        self.x_from=None
      try:
        self.x_to=float(parameters_list[8].get_text())
      except ValueError:
        self.x_to=None
      self.fit_object.set_fit_parameters(layer_params=fit_list[0], substrate_params=map(lambda x: x-1, fit_list[1][0]),
                                         background=fit_list[1]['background'],
                                         polarizer_efficiancy=fit_list[1]['polarizer_efficiancy'],
                                         analyzer_efficiancy=fit_list[1]['analyzer_efficiancy'],
                                         flipper0_efficiancy=fit_list[1]['flipper0_efficiancy'],
                                         flipper1_efficiancy=fit_list[1]['flipper1_efficiancy'],
                                         scaling=fit_list[1]['scaling'])
      try:
        self.max_iter=int(fit_list[2].get_text())
      except ValueError:
        self.max_iter=50
      if fit_list[1]['actually'] and response==5:
        self.fit_object.fit=1
      if response==7:
        self.user_constraint_dialog(dialog, window)
        return None
      self.dialog_fit(action, window, new_max_hr=new_max_hr)
      # read fit parameters from file and create new object, if process is killed ignore
      if fit_list[1]['actually'] and response==5 and self.fit_object.fit==1: 
        parameters, errors=self.read_fit_file(self.TEMP_DIR+'result', self.fit_object)
        new_fit=self.fit_object.copy()
        new_fit.get_parameters(parameters)
        sorted_errors=new_fit.get_errors(errors)
        self.show_result_window(dialog, window, new_fit, sorted_errors)
      #os.remove(self.TEMP_DIR+'fit_temp.ref')
      self.fit_object.fit=0
    elif response==3: # new layer
      new_layer=TreffLayerParam()
      self.fit_object.layers.append(new_layer)
      self.rebuild_dialog(dialog, window)
    elif response==4: # new multilayer
      multilayer=TreffMultilayerParam()
      multilayer.layers.append(TreffLayerParam())
      self.fit_object.layers.append(multilayer)
      self.rebuild_dialog(dialog, window)

  def dialog_fit(self, action, window, move_channels=True, new_max_hr=False):
    '''
      function invoked when apply button is pressed
      at fit dialog. Fits with the new parameters.
    '''
    names=config.treff.REF_FILE_ENDINGS
    output_names=config.treff.FIT_OUTPUT_FILES
    self.export_data_and_entfile(self.TEMP_DIR, 'fit_temp.ent')
    #open a background process for the fit function
    reflectometer_fit.functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', new_max_hr)
    print "PNR program started."
    if self.fit_object.fit!=1: # if this is not a fit just wait till finished
      exec_time, stderr_value = reflectometer_fit.functions.proc.communicate()
      print "PNR program finished in %.2g seconds." % float(exec_time.splitlines()[-1])
    else:
      self.open_status_dialog(window)
    first=True
    for i, dataset in enumerate(self.fit_datasets):
      if dataset:
        simu=read_data.treff.read_simulation(self.TEMP_DIR + output_names[i])
        simu.number='sim_'+dataset.number
        simu.short_info='simulation '+names[i]
        simu.sample_name=dataset.sample_name
        dataset.plot_together=[dataset, simu]
        if first:
          dataset.plot_options+='''
          set style line 2 lc 1
          set style line 3 lc 2
          set style line 4 lc 2
          set style line 5 lc 3
          set style line 6 lc 3
          set style line 7 lc 4
          set style line 8 lc 4
          set style increment user
          '''
          first=False
        else:
          dataset.plot_options+='''
          set style line 1 lc %i
          set style line 2 lc %i
          set style increment user
          ''' % (i+1, i+1)
    window.multiplot=[[(dataset, dataset.short_info) for dataset in self.fit_datasets if dataset]]
    window.multi_list.set_markup(' Multiplot List: \n' + '\n'.join(map(lambda item: item[1], window.multiplot[0])))
    if not window.index_mess in [self.active_file_data.index(item[0]) for item in window.multiplot[0]]:
      window.index_mess=self.active_file_data.index(window.multiplot[0][0][0])
    if move_channels:
      window.active_multiplot=True
      for i, dataset in enumerate(reversed([item for item in self.fit_datasets if item])):
        dataset.data[dataset.ydata].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.ydata].values)
        dataset.data[dataset.yerror].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.yerror].values)
        dataset.plot_together[1].data[dataset.plot_together[1].ydata].values=\
          map(lambda number: number*10.**(i*1), dataset.plot_together[1].data[dataset.plot_together[1].ydata].values)
    window.replot()
    if move_channels:
       for i, dataset in enumerate(reversed([item for item in self.fit_datasets if item])):
         dataset.data[dataset.ydata].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.ydata].values)
         dataset.data[dataset.yerror].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.yerror].values)
         dataset.plot_together[1].data[dataset.plot_together[1].ydata].values=\
            map(lambda number: number/10.**(i*1), dataset.plot_together[1].data[dataset.plot_together[1].ydata].values)

  def export_data_and_entfile(self, folder, file_name, datafile_prefix='fit_temp_', 
                              use_multilayer=False, use_roughness_gradient=True):
    '''
      Export measured data for fit program and the corresponding .ent file.
    '''
    names=config.treff.REF_FILE_ENDINGS
    output_names=config.treff.FIT_OUTPUT_FILES
    # convert x values from grad to mrad and 2Theta to Theta
    data_lines=[]
    for i, dataset in enumerate(self.fit_datasets):
      # if the channel dataset is None use 0 points.
      if dataset:
        dataset.unit_trans([['\302\260', math.pi/180.*1000., 0, 'mrad'], 
                            ['rad', 1000., 0, 'mrad']])    
        dataset.unit_trans([['2Theta', 'mrad', 0.5, 0, 'Theta', 'mrad']])    
        data_lines.append(dataset.export(os.path.join(folder, datafile_prefix+names[i]+'.ref'), 
                                         False, ' ', 
                                         xfrom=self.x_from, xto=self.x_to, 
                                         only_fitted_columns=True))
      else:
        data_lines.append(0)
    self.fit_object.number_of_points=data_lines
    self.fit_object.input_file_names=[os.path.join(folder, datafile_prefix+names[i]+'.ref') for i in range(4)]
    self.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(os.path.join(folder, file_name), 'w')
    ent_file.write(self.fit_object.get_ent_str(use_multilayer=use_multilayer, use_roughness_gradient=use_roughness_gradient)+'\n')
    ent_file.close()

  def show_result_window(self, dialog, window, new_fit, sorted_errors):
    '''
      show the result of a fit and ask to retrieve the result
    '''
    old_fit=self.fit_object
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
        if new_layer.scatter_density_Nb!=old_layer.scatter_density_Nb:
          text_string+='\tNb\':\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.scatter_density_Nb, new_layer.scatter_density_Nb, sorted_errors[index_add+str(index)+','+str(1)])
        if new_layer.scatter_density_Nb2!=old_layer.scatter_density_Nb2:
          text_string+='\tNb\'\':\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.scatter_density_Nb2, new_layer.scatter_density_Nb2, sorted_errors[index_add+str(index)+','+str(2)])
        if new_layer.scatter_density_Np!=old_layer.scatter_density_Np:
          text_string+='\tNp:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.scatter_density_Np, new_layer.scatter_density_Np, sorted_errors[index_add+str(index)+','+str(3)])
        if new_layer.theta!=old_layer.theta:
          text_string+='\Theta:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.theta, new_layer.theta, sorted_errors[index_add+str(index)+','+str(4)])
        if new_layer.phi!=old_layer.phi:
          text_string+='\tPhi:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.phi, new_layer.phi, sorted_errors[index_add+str(index)+','+str(5)])
        if new_layer.roughness!=old_layer.roughness:
          text_string+='\troughness:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
              (old_layer.roughness, new_layer.roughness, sorted_errors[index_add+str(index)+','+str(6)])
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
    if old_fit.substrate.scatter_density_Nb!=new_fit.substrate.scatter_density_Nb:
      text_string+='\tNb\':\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.scatter_density_Nb, new_fit.substrate.scatter_density_Nb, sorted_errors[index_add+str(index)+','+str(1)])
    if old_fit.substrate.scatter_density_Nb2!=new_fit.substrate.scatter_density_Nb2:
      text_string+='\tNb\'\':\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.scatter_density_Nb2, new_fit.substrate.scatter_density_Nb2, sorted_errors[index_add+str(index)+','+str(2)])
    if old_fit.substrate.scatter_density_Np!=new_fit.substrate.scatter_density_Np:
      text_string+='\tNp:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.scatter_density_Np, new_fit.substrate.scatter_density_Np, sorted_errors[index_add+str(index)+','+str(3)])
    if old_fit.substrate.theta!=new_fit.substrate.theta:
      text_string+='\Theta:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.theta, new_fit.substrate.theta, sorted_errors[index_add+str(index)+','+str(4)])
    if old_fit.substrate.phi!=new_fit.substrate.phi:
      text_string+='\tPhi:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' % \
          (old_fit.substrate.phi, new_fit.substrate.phi, sorted_errors[index_add+str(index)+','+str(5)])
    if old_fit.substrate.roughness!=new_fit.substrate.roughness:
      text_string+='\troughness:\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
          (old_fit.substrate.roughness, new_fit.substrate.roughness, sorted_errors['substrate5'])
    # global parameters
    text_string+='\n'
    if old_fit.scaling_factor!=new_fit.scaling_factor:
      text_string+='Scaling Factor:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
          (old_fit.scaling_factor, new_fit.scaling_factor, sorted_errors['scaling'])
    if old_fit.background!=new_fit.background:
      text_string+='Background:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.background, new_fit.background, sorted_errors['background'])
    if old_fit.polarization_parameters[0]!=new_fit.polarization_parameters[0]:
      text_string+='Polarizer efficiency:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.polarization_parameters[0], new_fit.polarization_parameters[0], sorted_errors['polarizer_efficiancy'])
    if old_fit.polarization_parameters[1]!=new_fit.polarization_parameters[1]:
      text_string+='Analyzer efficiency:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.polarization_parameters[1], new_fit.polarization_parameters[1], sorted_errors['analyzer_efficiancy'])
    if old_fit.polarization_parameters[2]!=new_fit.polarization_parameters[2]:
      text_string+='1st Flipper efficiency:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.polarization_parameters[2], new_fit.polarization_parameters[2], sorted_errors['flipper0_efficiancy'])
    if old_fit.polarization_parameters[3]!=new_fit.polarization_parameters[3]:
      text_string+='2nd Flipper efficiency:\t\t%# .6g  \t->   %# .6g    +/- %# .6g\n' %  \
        (old_fit.polarization_parameters[3], new_fit.polarization_parameters[3], sorted_errors['flipper1_efficiancy'])
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

  def export_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter export to .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Export to...', action=gtk.FILE_CHOOSER_ACTION_SAVE, 
                                      buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, 
                                               gtk.RESPONSE_CANCEL))
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
    use_multilayer=gtk.CheckButton(label='Combine 1st multiplot (don\'t export every single layer)', use_underline=True)
    use_multilayer.show()
    file_dialog.vbox.pack_end(use_multilayer, expand=False)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      file_name=file_dialog.get_filename()
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    file_prefix=file_name.rsplit('.ent', 1)[0]
    self.export_data_and_entfile(os.path.dirname(file_prefix), 
                                 os.path.basename(file_prefix)+'.ent', 
                                 datafile_prefix=os.path.basename(file_prefix), 
                                 use_multilayer=use_multilayer.get_active(), use_roughness_gradient=False)
    return True
  
  def import_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter import from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog=gtk.FileChooserDialog(title='Open new entfile...', 
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
    # Add a check box for importing x-ray .ent files.
    x_ray_import=gtk.CheckButton('Convert from x-ray .ent File')
    align=gtk.Alignment(xalign=1.0, yalign=0.0, xscale=0.0, yscale=0.0)
    align.add(x_ray_import)
    align.show_all()
    file_dialog.vbox.pack_end(align, expand=False, fill=True, padding=0)
    response = file_dialog.run()
    if response == gtk.RESPONSE_OK:
      file_name=file_dialog.get_filename()
    elif response == gtk.RESPONSE_CANCEL:
      file_dialog.destroy()
      return False
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    self.fit_object=TreffFitParameters()
    if x_ray_import.get_active():
      self.fit_object.read_params_from_X_file(file_name)
    else:
      self.fit_object.read_params_from_file(file_name)
    if not any(self.fit_datasets):
      if not self.select_fittable_sequences(action, window):
        return False
    self.dialog_fit(action, window)
    return True
  
  #----------------------- GUI functions -----------------------

  def call_fit_program(self, file_ent, force_compile=False):
    '''
      This function calls the fit_pnr program and if it is not compiled with 
      those settings, will compile it. It does not wait for the 
      program to finish, it only startes the sub process, which is returned.
    '''
    code_path=os.path.join(self.SCRIPT_PATH, 'config', 'fit', 'pnr_multi')
    code_file=os.path.join(self.TEMP_DIR, 'pnr.f90')
    exe=os.path.join(self.TEMP_DIR, 'pnr.o')
    subcode_files=map(lambda name: os.path.join(code_path, name), config.treff.PROGRAM_FILES)
    # has the program been changed or does it not exist
    if force_compile or (not os.path.exists(exe)) or \
      any(map(lambda name: (os.stat(name)[8]-os.stat(exe)[8]) > 0, subcode_files)):
      code=''
      for subcode_file in subcode_files:
        code+=open(subcode_file, 'r').read()
      code=code.replace("parameter(maxlay=400,map=7*maxlay+12,ndatap=1000,max_hr=5000,np_conv=500,pdq=0.02d0)", 
                   "parameter(maxlay=400,map=7*maxlay+12,ndatap=1000,max_hr=%i,np_conv=500,pdq=0.02d0)" % \
                   self.max_hr
                   )
      open(code_file, 'w').write(code)
      print 'Compiling fit program!'
      call_params=[config.treff.FORTRAN_COMPILER, code_file, '-o', exe]
      if  config.treff.FORTRAN_COMPILER_OPTIONS!=None:
        call_params.append(config.treff.FORTRAN_COMPILER_OPTIONS)
      if  config.treff.FORTRAN_COMPILER_MARCH!=None:
        call_params.append(config.treff.FORTRAN_COMPILER_MARCH)
      subprocess.call(call_params)
      print 'Compiled'
    process = subprocess.Popen([exe, file_ent, str(self.max_iter)], 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        cwd=self.TEMP_DIR
                        )
    return process

  def add_multilayer(self, action, multilayer, dialog, window):
    '''
      add a layer to the multilayer after button is pressed
    '''
    new_layer=TreffLayerParam()
    multilayer.layers.append(new_layer)
    self.rebuild_dialog(dialog, window)

  def replot_present(self, session, window):
    '''
      Replot the simulated and measured data.
    '''
    dataset=window.measurement[window.index_mess]        
    simu=read_data.treff.read_simulation(self.TEMP_DIR+'simulation_pp')
    simu.number='sim_'+dataset.number
    simu.short_info='simulation'
    simu.sample_name=dataset.sample_name
    dataset.plot_together=[dataset, simu]
    window.replot()  
    
class TreffFitParameters(FitParameters):
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  wavelength=[4.73, 0.03] # wavelength and delta-wavelength of neutrons
  input_file_names=['', '', '', '']
  number_of_points=[10, 0, 0, 0] # number of simulated points from the 4 polarization chanels
  slits=[4.0, 4.0] # first and second slit opening before sample
  sample_length=10.0 # length of sample in the beam
  distances=[2270.0, 450.0] # distance between sample and first,last slit.
  polarization_parameters=[0.973, 0.951, 1.0, 1.0] # polarizer-/analyzer efficiency/first-/second flipper efficiency
  alambda_first=0.0001 # alambda parameter for first fit step
  ntest=1 # number of times chi has to be not improvable before the fit stops (I think)
  PARAMETER_LENGTH=7
  from config.scattering_length_table import NEUTRON_SCATTERING_LENGTH_DENSITIES
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.NEUTRON_SCATTERING_LENGTH_DENSITIES[material]
      result=True
      parameters=[thickness] + SL + [90., 90, roughness]
    except (KeyError, TypeError):
      parameters=[thickness] + [1. for i in range(self.PARAMETER_LENGTH-4)] + [90., 90., roughness]
      material='Unknown'
      result=False
    layer=TreffLayerParam(material, parameters)
    self.layers.append(layer)
    return result

  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.NEUTRON_SCATTERING_LENGTH_DENSITIES[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(TreffLayerParam(materials[i], [thicknesses[i]] + SL + [90., 90., roughnesses[i]]))
    multilayer=TreffMultilayerParam(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.NEUTRON_SCATTERING_LENGTH_DENSITIES[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1. for i in range(self.PARAMETER_LENGTH - 4)]
      result=False
    layer=TreffLayerParam(material, [0.] + SL + [90., 90., roughness])
    self.substrate=layer
    return result

  def get_ent_str(self, use_multilayer=False, use_roughness_gradient=True):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.slits[0]) + '\tfirst slit opening (mm)\n'
    ent_string+=str(self.slits[1]) + '\tsecond slit opening (mm)\n'
    ent_string+=str(self.sample_length) + '\tsample length (mm)\n'
    ent_string+=str(self.distances[0]) + '\tdistance from first slit to sample (mm)\n'
    ent_string+=str(self.distances[1]) + '\tdistance from second slit to sample (mm)\n'
    
    ent_string+='#+++ File names for the 4 polarization directions (++,--,+-,-+) +++\n'
    for i, name in enumerate(self.input_file_names):
      ent_string+=name + '\n' + str(self.number_of_points[i]) + '\t number of points used from this file\n'
    
    ent_string+='#------ \n'
    ent_string+=str(self.wavelength[0]) + '\twavelength of the neutrons (Angstrom)\n'
    ent_string+=str(self.wavelength[1]) + '\twidth of the wavelength (Angstrom)\n'
    
    ent_string+='#+++++  Begin of layer parameters +++++\n'
    if use_multilayer and any(map(lambda item: item.multilayer, self.layers)):
      string, layer_index, para_index=self.__get_ent_str_with_multilayer__()
      ent_string+=string
    else:      
      ent_string+='0\tnumber of layers on top of the (unused) multilayer\n'
      ent_string+='# blank\n'
      ent_string+='0\tnumber of layers in the unicell of the multilayer\n'
      ent_string+='# blank\n'
      ent_string+='0\tnumber of repititions of those unicells in the multilayer\n'
      ent_string+='# blank\n'
      
      ent_string+=str(self.number_of_layers()) + '\tnumber of layers below the (unused) multilayer\n'
      ent_string_layer, layer_index, para_index = self.__get_ent_str_layers__(use_roughness_gradient)
      ent_string+=ent_string_layer
    
    # more global parameters
    ent_string+=str(round(self.scaling_factor, 4)) + '\tscaling factor \t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(round(self.background, 4)) + '\tbackground\t\t\t\tparametar ' + str(para_index) + '\n'
    para_index+=1
    ent_string+='#### Polarization parameters\n'
    ent_string+=str(self.polarization_parameters[0]) + '\tpolarizer efficiency\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[1]) + '\tanalyzer efficiency\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[2]) + '\tfirst flipper efficiency\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[3]) + '\tsecond flipper efficiency\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    
    # create constrains as needed for pnr_multi ( degrees of freedom etc. )
    fit_parameters=list(self.fit_params)
    constrains_list=map(list, self.constrains)
    constrain_to_list=[]
    for constrain in constrains_list:
      constrain.sort()
      constrain_to_list.append(constrain.pop(0))
      for con in constrain:
        try:
          fit_parameters.remove(con)
        except ValueError:
          continue
    # fit specific parameters
    ent_string+='#### fit specific parameters:\n'
    ent_string+=str(self.fit) + '\t1: fit; 0: simulation\n'
    ent_string+='\n' + str(len(fit_parameters)) + '\t\tNumber of parameters to be fitted\n'
    ent_string+=' '.join([str(param) for param in fit_parameters]) + '\t\tindices of parameters\n'
    ent_string+='\n' + str(len(self.constrains)) + '\t\tnumber of constraints\n'
    for i, constrain in enumerate(constrains_list):
      ent_string+='1\ttype of contraint; 1: of type b=c=...=a  2: of type b+a=cste\n'
      ent_string+=str(constrain_to_list[i]) + '\tparameter with respect to which the equality relation has to be set\n'
      ent_string+=str(len(constrain)) + '\t\tnumber of parameters to be kept equal\n'
      ent_string+=' '.join([str(param) for param in constrain]) + '\t\tindices of those parameters\n'
    ent_string+='### Parameters for the fit algorithm:\n'
    ent_string+=str(self.alambda_first) + '\talambda_first, correspons to first step size in fit algorithm\n'
    ent_string+=str(self.ntest) + '\tntest, the number of times chi could not be improved before fit stops\n'
    return ent_string

  def __get_ent_str_with_multilayer__(self):
    '''
      Create string for layer part of .ent file for the fit script from given parameters.
      This function uses the multilayer functionality of pnr_multi.
    '''
    layer_list=[]
    for layer in self.layers:
      if layer.multilayer:
        layer_top=layer_list
        layer_list=[]
        multilayer=layer
      else:
        layer_list.append(layer)
    layer_bottom=layer_list
    
    # layers and parameters are numbered started with 1
    layer_index=1
    para_index=1
    ent_string=''
    ent_string+='%i\tnumber of layers on top of the (unused) multilayer\n' % len(layer_top)
    ent_string+='#### Begin of layers above, first layer '
    # add text for every top_layer
    for layer in layer_top:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    ent_string+='## End of layers above\n'
    ent_string+='%i\tnumber of layers in the unicell of the multilayer\n' % len(multilayer.layers)
    ent_string+='#### Begin of layers in multilayer '
    for layer in multilayer.layers:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    ent_string+='## End of layers in multilayer\n'
    ent_string+='%i\tnumber of repititions of those unicells in the multilayer\n' % multilayer.repititions
    ent_string+='\n'
    ent_string+='%i\tnumber of layers below the (unused) multilayer\n' % len(layer_bottom)
    ent_string+='#### Begin of layers below, first layer '
    # add text for every top_layer
    for layer in layer_bottom:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string    
    # substrate data
    string,  layer_index, para_index=self.substrate.get_ent_text(layer_index, para_index-1)
    ent_string+='\n'.join([string.splitlines()[0]]+string.splitlines()[2:]) + '\n' # cut the thickness line
    ent_string+='### End of layers.\n'
    return ent_string, layer_index, para_index
  
  def set_fit_parameters(self, layer_params={}, substrate_params=[], background=False, 
                         polarizer_efficiancy=False, analyzer_efficiancy=False, 
                         flipper0_efficiancy=False, flipper1_efficiancy=False, 
                         scaling=False):
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
        para_index+=len(layer)*7
    for param in substrate_params:
      fit_params.append(para_index + param)
    para_index+=6
    if scaling:
      fit_params.append(para_index)
    para_index+=1
    if background:
      fit_params.append(para_index)
    para_index+=1
    if polarizer_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if analyzer_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if flipper0_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if flipper1_efficiancy:
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
      for j in range(7): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            layer.set_param(j, parameters[para_index + j])
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*7) in self.fit_params:
              layer.layers[k].set_param(j, parameters[para_index + j + k*7])
      para_index+=len(layer)*7
    for j in range(6):
      if para_index in self.fit_params:
        self.substrate.set_param(j+1, parameters[para_index])
      para_index+=1
    if para_index in self.fit_params:
      self.scaling_factor=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.background=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[0]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[1]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[2]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[3]=parameters[para_index]
    para_index+=1
  
  def get_errors(self, errors):
    '''
      convert errors dictionary from parameter indices to layer indices
    '''
    para_index=1
    errors_out={}
    for i, layer in enumerate(self.layers):
      for j in range(7): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            errors_out[str(i) + ',' + str(j)]=errors[para_index + j]
        else:
          for k in range(len(layer.layers)): # go through sub layers
            if (para_index + j + k*7) in self.fit_params:
              errors_out[str(i) + ',' + str(k) + ',' + str(j)]=errors[para_index + j + k*7]
      para_index+=len(layer)*7
    for j in range(6):
      if para_index in self.fit_params:
        errors_out['substrate'+str(j)]=errors[para_index]
      para_index+=1
    if para_index in self.fit_params:
      errors_out['scaling']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['background']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['polarizer_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['analyzer_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['flipper0_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['flipper1_efficiancy']=errors[para_index]
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
        con_index+=7
    fit_cons+=self.user_constraints
    self.constrains=[]
    # remove constrains not importent for the fitted parameters
    for constrain in fit_cons:
      if constrain[0] in self.fit_params:
        self.constrains.append(constrain)
    # combine constraints which overlap
    fit_cons=self.constrains
    remove=[]
    for constrain in fit_cons:
      if constrain in remove:
        continue
      for constrain_2 in [cons for cons in fit_cons if not cons is constrain]:
        if any(map(lambda con: con in constrain, constrain_2)) and not constrain_2 in remove:
          cmb=constrain+constrain_2
          cmb=dict.fromkeys(cmb).keys()
          cmb.sort()
          self.constrains.append(cmb)
          remove.append(constrain)
          remove.append(constrain_2)
    for rmv in remove:
      self.constrains.remove(rmv)

  def copy(self):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit=FitParameters.copy(self, TreffFitParameters())
    new_fit.wavelength=copy(self.wavelength)
    new_fit.input_file_names=copy(self.input_file_names)
    new_fit.number_of_points=copy(self.number_of_points)
    new_fit.slits=copy(self.slits)
    new_fit.sample_length=self.sample_length
    new_fit.distances=copy(self.distances)
    new_fit.polarization_parameters=copy(self.polarization_parameters)
    new_fit.alambda_first=self.alambda_first
    new_fit.ntest=self.ntest
    return new_fit

  def read_params_from_file(self, file):
    '''
      read data from .ent file
    '''
    lines=open(file, 'r').readlines()
    lines.reverse()
    for i, line in enumerate(lines):
      if line[0]!='#':
        lines[i]=line.replace('d', 'e') # replace power of ten in fortran 'd' by float 'e'
    # Geometry parameters
    self.slits[0]=float(lines.pop().split()[0])
    self.slits[1]=float(lines.pop().split()[0])
    self.sample_length=float(lines.pop().split()[0])
    self.distances[0]=float(lines.pop().split()[0])
    self.distances[1]=float(lines.pop().split()[0])
    # skip file names
    for i in range(10):
      lines.pop()
    self.wavelength[0]=float(lines.pop().split()[0])
    self.wavelength[1]=float(lines.pop().split()[0])
    lines.pop()
    # read top layers data
    number_of_layers_top=int(lines.pop().split()[0])
    self.layers=[]
    for i in range(number_of_layers_top):
      layer = self.read_layer_params_from_file(lines)
      self.layers.append(layer)
    # read multi layers data
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      multi_name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      multi_name='NoName'
    number_of_layers_multi=int(lines.pop().split()[0])
    if number_of_layers_multi>0:
      layers_in_multi=[]
      for i in range(number_of_layers_multi):
        layer = self.read_layer_params_from_file(lines)
        layers_in_multi.append(layer)
      lines.pop()
      repititions_of_multi=int(lines.pop().split()[0])
      self.layers.append(TreffMultilayerParam(repititions=repititions_of_multi, 
                                              name=multi_name, 
                                              layer_list=layers_in_multi))
    else:
      lines.pop()
      lines.pop()
    lines.pop()
    # read bottom layers data
    number_of_layers_bottom=int(lines.pop().split()[0])
    for i in range(number_of_layers_bottom):
      layer = self.read_layer_params_from_file(lines)
      self.layers.append(layer)
    # read substrate data
    self.substrate=self.read_layer_params_from_file(lines, substrate=True)
    # read last parameters
    lines.pop()
    self.scaling_factor=float(lines.pop().split()[0])
    self.background=float(lines.pop().split()[0])
    lines.pop()
    self.polarization_parameters[0]=float(lines.pop().split()[0])
    self.polarization_parameters[1]=float(lines.pop().split()[0])
    self.polarization_parameters[2]=float(lines.pop().split()[0])
    self.polarization_parameters[3]=float(lines.pop().split()[0])
    self.combine_layers(TreffMultilayerParam)

  def read_layer_params_from_file(self, lines, substrate=False):
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      name='NoName'
    parameters=[]
    for i in range(7):
      if i==0 and substrate:
        parameters.append(0.)
      else:
        parameters.append(float(lines.pop().split()[0]))
    layer=TreffLayerParam(name=name, parameters_list=parameters)
    return layer

  def read_params_from_X_file(self,name):
    '''
      Convert Parameters from x-ray .ent file to neutrons and import it
      for usage with this fit.
    '''
    import sessions.reflectometer

    ### reading X-ray data
    x_ray_fitdata=sessions.reflectometer.RefFitParameters()
    x_ray_fitdata.read_params_from_file(name)

    ### instument settings
    self.slits[0]=4.
    self.slits[1]=2.
    self.sample_length=10.
    self.distances[0]=2270.
    self.distances[1]=450.
    self.wavelength[0]=4.73
    self.wavelength[1]=0.03
    self.layers=[]
  
    ### null multilayer above
    #layers_in_multi=[]
    #repititions_of_multi = 0
    #self.layers.append(sessions.treff.TreffMultilayerParam(0, name="NoName", layer_list=layers_in_multi))
    
    def get_layer_parameter(layer):
        name=layer.name
        parameters=[]
        parameters.append(layer.thickness)
        if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
        else:
          parameters.append(1)
          parameters.append(1)
          parameters.append(1)
        parameters.append(90)
        parameters.append(90)
        parameters.append(layer.roughness)
        return TreffLayerParam(name, parameters_list=parameters)
    
    for i, layer in enumerate(x_ray_fitdata.layers):
      ### multilayer
      if layer.multilayer:
        multilayer=TreffMultilayerParam(layer.repititions, layer.name, )
        for sub_layer in layer.layers:
          multilayer.layers.append(get_layer_parameter(sub_layer))
        self.layers.append(multilayer)
#          for k in range(len(x_ray_fitdata.layers[1].layers)):
#            name=x_ray_fitdata.layers[i].layers[k].name
#            parameters=[]
#            parameters.append(x_ray_fitdata.layers[i].layers[k].thickness)
#            if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
#            else:
#              parameters.append(1)
#              parameters.append(1)
#              parameters.append(1)
#            parameters.append(90)
#            parameters.append(90)
#            parameters.append(x_ray_fitdata.layers[i].layers[k].roughness)
#            layer=sessions.treff.TreffLayerParam(name, parameters_list=parameters)
#            self.layers.append(layer)
      else:
        ### single layer
        self.layers.append(get_layer_parameter(layer))
  
    ### substrate
    name=x_ray_fitdata.substrate.name
    parameters=[]
    parameters.append(0)
    if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
    else:
      parameters.append(1)
      parameters.append(1)
      parameters.append(1)
    parameters.append(90)
    parameters.append(90)
    parameters.append(x_ray_fitdata.substrate.roughness)
    self.substrate=TreffLayerParam(name=x_ray_fitdata.substrate.name, parameters_list=parameters)
  
   
    ### global parameters
    self.scaling_factor=0.4
    self.background=2
    self.polarization_parameters[0]=0.973
    self.polarization_parameters[1]=0.951
    self.polarization_parameters[2]=1.0
    self.polarization_parameters[3]=1.0

class TreffLayerParam(LayerParam):
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  scatter_density_Nb=1.
  scatter_density_Nb2=0.
  scatter_density_Np=0.
  theta=90.
  phi=90.
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    LayerParam.__init__(self, name, parameters_list)
    if parameters_list!=None:
      self.scatter_density_Nb=parameters_list[1]
      self.scatter_density_Nb2=parameters_list[2]
      self.scatter_density_Np=parameters_list[3]
      self.theta=parameters_list[4]
      self.phi=parameters_list[5]
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return LayerParam.__eq__(self, other) and\
      self.scatter_density_Nb==other.scatter_density_Nb and\
      self.scatter_density_Nb2==other.scatter_density_Nb2 and\
      self.scatter_density_Np==other.scatter_density_Np and\
      self.theta==other.theta and\
      self.phi==other.phi
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return TreffLayerParam(name=self.name, \
                     parameters_list=[\
                          self.thickness, \
                          self.scatter_density_Nb, \
                          self.scatter_density_Nb2, \
                          self.scatter_density_Np, \
                          self.theta, \
                          self.phi, \
                          self.roughness])

  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params
    '''
    list=[]
    for i in params:
      list.append(param_index + i)
    return list, param_index + 7
  
  def dialog_get_params(self, action, response, thickness, scatter_density_Nb, 
                        scatter_density_Nb2, scatter_density_Np, theta, phi, roughness):
    '''
      function to get parameters from the GUI dialog
    '''
    LayerParam.dialog_get_params(self, action, response, thickness, roughness)
    try:
      self.scatter_density_Nb=float(scatter_density_Nb.get_text())
      self.scatter_density_Nb2=float(scatter_density_Nb2.get_text())
      self.scatter_density_Np=float(scatter_density_Np.get_text())
      self.theta=float(theta.get_text())
      self.phi=float(phi.get_text())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==1: 
      self.scatter_density_Nb=value
    elif index==2: 
      self.scatter_density_Nb2=value
    elif index==3: 
      self.scatter_density_Np=value
    elif index==4: 
      self.theta=value
    elif index==5: 
      self.phi=value
    else:
      LayerParam.set_param(self, index, 6, value)
  
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
    text+=str(self.scatter_density_Nb) + '\treal part Nb\', - (A**-2)*1e6\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.scatter_density_Nb2) + ' imaginary part Nb\'\' of nuclear and\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.scatter_density_Np) + '\tmagnetic scat. len. dens. Np \t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.theta) + '\ttheta [deg.] (0 on z, 90 on x-y plane)\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.phi) + '\tphi [deg.]  (0 on x, 90 on y)\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=LayerParam.__get_ent_text_end__(self, layer_index, para_index, add_roughness)
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class TreffMultilayerParam(MultilayerParam):
  '''
    class for multilayer data
  '''
  
  def copy(self):
    return MultilayerParam.copy(self, TreffMultilayerParam())
  
  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params (list of param lists for multilayer)
    '''
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[j]:
        list+=[param_index + i + j * 7 + k * layers * 7 for k in range(self.repititions)]
    return list, param_index + len(self) * 7
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    if self.roughness_gradient==0:
      constrain_params=7
    else:
      constrain_params=6
    for j in range(layers): # iterate through layers
      for i in range(constrain_params): # iterate through parameters
        list.append([param_index + i + j * 7 + k * layers * 7 for k in range(self.repititions)])
    return list, param_index + len(self)
