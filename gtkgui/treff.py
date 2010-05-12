 # -*- encoding: utf-8 -*-
'''
  Treff GTK gui class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class TreffGUI:
  '''
    Treff GUI functions for the GTK toolkit.
  '''
  
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
                "Fit...", "<control><shift>F",                    # label, accelerator
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

  def extract_specular_reflectivity(self, action, window):
    '''
      Open a dialog for the extraction of the specular line from a 3d image.
      The user can select the width for the cross-section,
      after this the data is extracted and appendet to the fileobject.
      The true specular reflectivity is calculated using two parallel
      lines next to the specular line.
    '''
    data=window.measurement[window.index_mess]
    cs_dialog=gtk.Dialog(title='Create a cross-section:')
    cs_dialog.set_default_size(300, 150)
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
    line_width.set_text('0.08')
    table.attach(line_width,
                # X direction #          # Y direction
                1, 3,                      5, 6,
                0,                       gtk.FILL,
                0,                         0);
    label=gtk.Label()
    label.set_markup('Stepwidth:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      6, 7,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    binning=gtk.Entry()
    binning.set_width_chars(4)
    binning.set_text('0.08')
    table.attach(binning,
                # X direction #          # Y direction
                1, 3,                      6, 7,
                0,                       gtk.FILL,
                0,                         0);
    weight=gtk.CheckButton(label='Gauss weighting, Sigma:', use_underline=True)
    weight.set_active(True)
    table.attach(weight,
                # X direction #          # Y direction
                0, 1,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    sigma=gtk.Entry()
    sigma.set_width_chars(4)
    sigma.set_text('0.04')
    table.attach(sigma,
                # X direction #          # Y direction
                1, 3,                      7, 8,
                0,                       gtk.FILL,
                0,                         0);
    ext_all=gtk.CheckButton(label='Extract for all maps', use_underline=True)
    ext_all.set_active(True)
    table.attach(ext_all,
                # X direction #          # Y direction
                0, 1,                      8, 9,
                0,                       gtk.FILL,
                0,                         0);
                
    label=gtk.Label()
    label.set_markup('0-position offset:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1,                      9, 10,
                gtk.EXPAND | gtk.FILL,     gtk.FILL,
                0,                         0);
    offset_x=gtk.Entry()
    offset_x.set_width_chars(4)
    offset_x.set_text('0.0')
    table.attach(offset_x,
                # X direction #          # Y direction
                1, 2,                      9, 10,
                0,                       gtk.FILL,
                0,                         0);
    offset_y=gtk.Entry()
    offset_y.set_width_chars(4)
    offset_y.set_text('0.0')
    table.attach(offset_y,
                # X direction #          # Y direction
                2, 3,                      9, 10,
                0,                       gtk.FILL,
                0,                         0);
    table.show_all()
    # Enty activation triggers calculation, too
    line_width.connect('activate', lambda *ign: cs_dialog.response(1))
    offset_x.connect('activate', lambda *ign: cs_dialog.response(1))
    offset_y.connect('activate', lambda *ign: cs_dialog.response(1))
    binning.connect('activate', lambda *ign: cs_dialog.response(1))
    sigma.connect('activate', lambda *ign: cs_dialog.response(1))
    cs_dialog.vbox.add(table)
    cs_dialog.add_button('OK', 1)
    cs_dialog.add_button('Cancel', 0)
    result=cs_dialog.run()
    if result==1:
      # If not canceled the data is extracted
      if not ext_all.get_active():
        if data.zdata==-1:
          cs_dialog.destroy()
          return False
        else:
          extract_indices=[self.active_file_data.index(data)]
      else:
        extract_indices=[]
        for i, data in enumerate(self.active_file_data):
          if data.zdata>=0:
            extract_indices.append(i)
      try:
        args=('extract_specular_reflectivity',
              float(line_width.get_text()), 
              weight.get_active(), 
              float(sigma.get_text()), 
              float(binning.get_text()), 
              (float(offset_x.get_text()), float(offset_y.get_text()))
              )
      except ValueError:
        gotit=False
      gotit=True
      for i in extract_indices:
        window.index_mess=i
        gotit=gotit and window.file_actions.activate_action(*args)        
      if not gotit:
        message=gtk.MessageDialog(parent=self, 
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='Wrong parameter type.')
        message.run()
        message.destroy()
    else:
      gotit=False
    cs_dialog.destroy()
    if gotit:
      window.rebuild_menus()
      window.replot()      
    return gotit
  
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
    if any(self.active_file_data.fit_datasets):
      indices=[]
      for item in self.active_file_data.fit_datasets:
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
      self.active_file_data.fit_datasets=[set_list[object_box_1.get_active()], 
                        set_list[object_box_2.get_active()], 
                        set_list[object_box_3.get_active()], 
                        set_list[object_box_4.get_active()]]
      for object in self.active_file_data.fit_datasets:
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
    if not any(self.active_file_data.fit_datasets):
      if not self.select_fittable_sequences(action, window):
        return False
    if self.active_file_data.fit_object.layers==[]:
      self.active_file_data.fit_object.append_layer('Unknown', 10., 5.)
      self.active_file_data.fit_object.append_substrate('Unknown', 5.)
      # for first run autoset to multiplot
      window.active_multiplot=True
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
    for layer in self.active_file_data.fit_object.layers:
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
    first_slit.set_text(str(self.active_file_data.fit_object.slits[0]))
    # activating the input will apply the settings, too
    first_slit.connect('activate', self.dialog_activate, dialog)
    align_table.attach(first_slit, 0, 1,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('2nd slit:')
    align_table.attach(text_filed, 1, 2, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    second_slit=gtk.Entry()
    second_slit.set_width_chars(10)
    second_slit.set_text(str(self.active_file_data.fit_object.slits[1]))
    # activating the input will apply the settings, too
    second_slit.connect('activate', self.dialog_activate, dialog)
    align_table.attach(second_slit, 1, 2,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Smpl length:')
    align_table.attach(text_filed, 2, 3, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    length=gtk.Entry()
    length.set_width_chars(10)
    length.set_text(str(self.active_file_data.fit_object.sample_length))
    # activating the input will apply the settings, too
    length.connect('activate', self.dialog_activate, dialog)
    align_table.attach(length, 2, 3,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Dist. to 1st:')
    align_table.attach(text_filed, 3, 4, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    first_distance=gtk.Entry()
    first_distance.set_width_chars(10)
    first_distance.set_text(str(self.active_file_data.fit_object.distances[0]))
    # activating the input will apply the settings, too
    first_distance.connect('activate', self.dialog_activate, dialog)
    align_table.attach(first_distance, 3, 4,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('Dist. to 2nd:')
    align_table.attach(text_filed, 4, 5, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    second_distance=gtk.Entry()
    second_distance.set_width_chars(10)
    second_distance.set_text(str(self.active_file_data.fit_object.distances[1]))
    # activating the input will apply the settings, too
    second_distance.connect('activate', self.dialog_activate, dialog)
    align_table.attach(second_distance, 4, 5,  1, 2, gtk.FILL, gtk.FILL, 0, 3)
    
    wavelength_table=gtk.Table(4, 1, False)
    text_filed=gtk.Label()
    text_filed.set_markup('Wavelength:')
    wavelength_table.attach(text_filed, 0, 1, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    wavelength=gtk.Entry()
    wavelength.set_width_chars(5)
    wavelength.set_text(str(self.active_file_data.fit_object.wavelength[0]))
    # activating the input will apply the settings, too
    wavelength.connect('activate', self.dialog_activate, dialog)
    wavelength_table.attach(wavelength, 1, 2,  0, 1, gtk.FILL, gtk.FILL, 0, 3)
    text_filed=gtk.Label()
    text_filed.set_markup('+/-')
    wavelength_table.attach(text_filed, 2, 3, 0, 1, gtk.FILL,  gtk.FILL, 10, 0)
    delta_wavelength=gtk.Entry()
    delta_wavelength.set_width_chars(5)
    delta_wavelength.set_text(str(self.active_file_data.fit_object.wavelength[1]))
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
    substrat_options=self.create_layer_options(self.active_file_data.fit_object.substrate, 0, fit_params, dialog, window, substrate=True)
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
    background.set_text(str(self.active_file_data.fit_object.background))
    # activating the input will apply the settings, too
    background.connect('activate', self.dialog_activate, dialog)
    align_table.attach(background, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)   
    scaling_x=gtk.CheckButton(label='Scaling: ', use_underline=True)
    scaling_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'scaling')
    align_table.attach(scaling_x, 0, 1, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    scaling_factor=gtk.Entry()
    scaling_factor.set_width_chars(10)
    scaling_factor.set_text(str(self.active_file_data.fit_object.scaling_factor))
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
    polarizer_efficiancy.set_text(str(self.active_file_data.fit_object.polarization_parameters[0]))
    # activating the input will apply the settings, too
    polarizer_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(polarizer_efficiancy, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
    analyzer_efficiancy_x=gtk.CheckButton(label='Analyzer: ', use_underline=True)
    analyzer_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'analyzer_efficiancy')
    align_table.attach(analyzer_efficiancy_x, 2, 3, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    analyzer_efficiancy=gtk.Entry()
    analyzer_efficiancy.set_width_chars(10)
    analyzer_efficiancy.set_text(str(self.active_file_data.fit_object.polarization_parameters[1]))
    # activating the input will apply the settings, too
    analyzer_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(analyzer_efficiancy, 3, 4, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
    flipper0_efficiancy_x=gtk.CheckButton(label='1st Flipper: ', use_underline=True)
    flipper0_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'flipper0_efficiancy')
    align_table.attach(flipper0_efficiancy_x, 2, 3, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    flipper0_efficiancy=gtk.Entry()
    flipper0_efficiancy.set_width_chars(10)
    flipper0_efficiancy.set_text(str(self.active_file_data.fit_object.polarization_parameters[2]))
    # activating the input will apply the settings, too
    flipper0_efficiancy.connect('activate', self.dialog_activate, dialog)
    align_table.attach(flipper0_efficiancy, 3, 4, 4, 5, gtk.FILL, gtk.FILL, 0, 0)
    flipper1_efficiancy_x=gtk.CheckButton(label='2nd Flipper: ', use_underline=True)
    flipper1_efficiancy_x.connect('toggled', self.toggle_fit_bool_option, fit_params, 'flipper1_efficiancy')
    align_table.attach(flipper1_efficiancy_x, 2, 3, 5, 6, gtk.FILL, gtk.FILL, 0, 0)
    flipper1_efficiancy=gtk.Entry()
    flipper1_efficiancy.set_width_chars(10)
    flipper1_efficiancy.set_text(str(self.active_file_data.fit_object.polarization_parameters[3]))
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
    alambda_first.set_text(str(self.active_file_data.fit_object.alambda_first))
    # activating the input will apply the settings, too
    alambda_first.connect('activate', self.dialog_activate, dialog)
    align_table.attach(alambda_first, 1, 2, 6, 7, 0, gtk.FILL, 0, 0)   
    text_filed=gtk.Label()
    text_filed.set_markup('nTest')
    align_table.attach(text_filed, 0, 1, 7, 8, gtk.FILL, gtk.FILL, 0, 0)
    ntest=gtk.Entry()
    ntest.set_width_chars(2)
    ntest.set_text(str(self.active_file_data.fit_object.ntest))
    # activating the input will apply the settings, too
    ntest.connect('activate', self.dialog_activate, dialog)
    align_table.attach(ntest, 1, 2, 7, 8, 0, gtk.FILL, 0, 0)   
    
    text_filed=gtk.Label()
    text_filed.set_markup('max_hr')
    align_table.attach(text_filed, 0, 1, 8, 9, gtk.FILL, gtk.FILL, 0, 0)
    max_hr=gtk.Entry()
    max_hr.set_width_chars(4)
    max_hr.set_text(str(self.max_hr))
    move_channels_button=gtk.CheckButton(label='move chanels in plot', use_underline=True)
    move_channels_button.set_active(True)
    align_table.attach(move_channels_button, 3, 4, 8, 9, gtk.FILL, gtk.FILL, 0, 0)
    show_all_button=gtk.CheckButton(label='all channels', use_underline=True)
    show_all_button.set_active(self.active_file_data.fit_object.simulate_all_channels)
    align_table.attach(show_all_button, 2, 3, 8, 9, gtk.FILL, gtk.FILL, 0, 0)
    # activating the input will apply the settings, too
    ntest.connect('activate', self.dialog_activate, dialog)
    align_table.attach(max_hr, 1, 2, 8, 9, 0, gtk.FILL, 0, 0)   
    if self.active_file_data.fit_object_history!=[]:
      history_back=gtk.Button(label='Undo (%i)' % len(self.active_file_data.fit_object_history), use_underline=True)
      history_back.connect('clicked', self.fit_history, True, dialog, window)
      align_table.attach(history_back, 2, 3, 7, 8, gtk.FILL, gtk.FILL, 0, 0)
    if self.active_file_data.fit_object_future!=[]:
      history_forward=gtk.Button(label='Redo (%i)' % len(self.active_file_data.fit_object_future), use_underline=True)
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
                   alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
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
      theta_x=gtk.CheckButton(label='Θ', use_underline=True)
      theta_x.connect('toggled', self.toggle_fit_option, layer_params[layer_index], 4)
      align_table.attach(theta_x, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)
      phi_x=gtk.CheckButton(label='φ', use_underline=True)
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
      for i, SL in enumerate(sorted(self.active_file_data.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES.items())):
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
      SL=self.active_file_data.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES[name]
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
        self.active_file_data.fit_object.wavelength[0]=float(parameters_list[0].get_text())
        self.active_file_data.fit_object.background=float(parameters_list[1].get_text())
        self.active_file_data.fit_object.slits=map(float, map(lambda item: item.get_text(), parameters_list[2]))
        self.active_file_data.fit_object.scaling_factor=float(parameters_list[3].get_text())
        self.active_file_data.fit_object.polarization_parameters=map(float, map(lambda item: item.get_text(), parameters_list[4]))
        self.active_file_data.fit_object.alambda_first=float(parameters_list[5].get_text())
        self.active_file_data.fit_object.ntest=int(parameters_list[6].get_text())
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
      self.active_file_data.fit_object.simulate_all_channels=parameters_list[11].get_active()
      try:
        self.x_from=float(parameters_list[7].get_text())
      except ValueError:
        self.x_from=None
      try:
        self.x_to=float(parameters_list[8].get_text())
      except ValueError:
        self.x_to=None
      self.active_file_data.fit_object.set_fit_parameters(layer_params=fit_list[0], substrate_params=map(lambda x: x-1, fit_list[1][0]),
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
        self.active_file_data.fit_object.fit=1
      if response==7:
        self.user_constraint_dialog(dialog, window)
        return None
      self.dialog_fit(action, window, move_channels=parameters_list[10].get_active(), new_max_hr=new_max_hr)
      # read fit parameters from file and create new object, if process is killed ignore
      if fit_list[1]['actually'] and response==5 and self.active_file_data.fit_object.fit==1: 
        parameters, errors=self.read_fit_file(self.TEMP_DIR+'result', self.active_file_data.fit_object)
        new_fit=self.active_file_data.fit_object.copy()
        new_fit.get_parameters(parameters)
        sorted_errors=new_fit.get_errors(errors)
        self.show_result_window(dialog, window, new_fit, sorted_errors)
      #os.remove(self.TEMP_DIR+'fit_temp.ref')
      self.active_file_data.fit_object.fit=0
    elif response==3: # new layer
      new_layer=TreffLayerParam()
      self.active_file_data.fit_object.layers.append(new_layer)
      self.rebuild_dialog(dialog, window)
    elif response==4: # new multilayer
      multilayer=TreffMultilayerParam()
      multilayer.layers.append(TreffLayerParam())
      self.active_file_data.fit_object.layers.append(multilayer)
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
    if self.active_file_data.fit_object.fit!=1 and any(self.active_file_data.fit_datasets): # if this is not a fit just wait till finished
      exec_time, stderr_value = reflectometer_fit.functions.proc.communicate()
      print "PNR program finished in %.2g seconds." % float(exec_time.splitlines()[-1])
    else:
      self.open_status_dialog(window)
    first=True
    free_sims=[]
    for i, dataset in enumerate(self.active_file_data.fit_datasets):
      if dataset:
        # if data for the channel was selected combine data and fit together
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
      elif self.active_file_data.fit_object.simulate_all_channels:
        simu=read_data.treff.read_simulation(self.TEMP_DIR + output_names[i])
        simu.number='%i' % i
        simu.short_info='simulation '+names[i]
        simu.plot_options+='''
          set style line 1 lc %i
          set style increment user
          ''' % (i+1)
        simu.logy=True
        free_sims.append(simu)
    # create a multiplot with all datasets
    window.multiplot=[[(dataset, dataset.short_info) for dataset in self.active_file_data.fit_datasets if dataset]]
    window.multi_list.set_markup(' Multiplot List: \n' + '\n'.join(map(lambda item: item[1], window.multiplot[0])))
    if not window.index_mess in [self.active_file_data.index(item[0]) for item in window.multiplot[0]]:
      try:
        window.index_mess=self.active_file_data.index(window.multiplot[0][0][0])
      except:
        self.file_data['Simulations']=free_sims
        self.active_file_data=self.file_data['Simulations']
        self.active_file_name='Simulations'
        window.index_mess=0
        window.measurement=self.active_file_data
        window.input_file_name='Simulations'
        free_sims[0].plot_options+='''
          set style line 2 lc 1
          set style line 3 lc 2
          set style line 4 lc 2
          set style line 5 lc 3
          set style line 6 lc 3
          set style line 7 lc 4
          set style line 8 lc 4
          set style increment user
          '''
    for sim in free_sims:
      # add simulations without dataset to the multiplot
      window.multiplot[0].append((sim, sim.short_info))
      window.multiplot[0].append((sim, sim.short_info))
    free_sims.reverse()
    if move_channels:
      # move the polarization channels agains eachother to make it easier for the eye
      if not self.replot:
        self.replot=window.replot
        window.replot=lambda *ignore: self.move_channels_replot(window)
        def reset_replot(index):
          window.replot=self.replot
          self.replot=None
          window.do_add_multiplot=self.do_add_multiplot
          return window.do_add_multiplot(index)
        self.do_add_multiplot=window.do_add_multiplot
        window.do_add_multiplot=reset_replot
    elif self.replot:
      window.replot=self.replot
      window.do_add_multiplot=self.do_add_multiplot
      self.replot=None
    window.replot()

  def move_channels_replot(self, window):
    '''
      function to replace window.replot if the 
      channels should be moved to show the fits.
    '''
    if window.active_multiplot:
      for i, tupel in enumerate(reversed(window.multiplot[0])):
        dataset=tupel[0]
        if len(dataset.plot_together)>1:
          dataset.data[dataset.ydata].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.ydata].values)
          dataset.data[dataset.yerror].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.yerror].values)
          dataset.plot_together[1].data[dataset.plot_together[1].ydata].values=\
            map(lambda number: number*10.**(i*1), dataset.plot_together[1].data[dataset.plot_together[1].ydata].values)
        else:
          dataset.data[dataset.ydata].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.ydata].values)
          dataset.data[dataset.yerror].values=map(lambda number: number*10.**(i*1), dataset.data[dataset.yerror].values)
      self.replot()
      for i, tupel in enumerate(reversed(window.multiplot[0])):
        dataset=tupel[0]
        if len(dataset.plot_together)>1:
          dataset.data[dataset.ydata].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.ydata].values)
          dataset.data[dataset.yerror].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.yerror].values)
          dataset.plot_together[1].data[dataset.plot_together[1].ydata].values=\
            map(lambda number: number/10.**(i*1), dataset.plot_together[1].data[dataset.plot_together[1].ydata].values)
        else:
          dataset.data[dataset.ydata].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.ydata].values)
          dataset.data[dataset.yerror].values=map(lambda number: number/10.**(i*1), dataset.data[dataset.yerror].values)
    else:
      self.replot()

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
    self.active_file_data.fit_object=TreffFitParameters()
    if x_ray_import.get_active():
      self.active_file_data.fit_object.read_params_from_X_file(file_name)
    else:
      self.active_file_data.fit_object.read_params_from_file(file_name)
    if not any(self.active_file_data.fit_datasets):
      if not self.select_fittable_sequences(action, window):
        return False
    self.dialog_fit(action, window)
    return True
  
  #----------------------- GUI functions -----------------------

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
    
