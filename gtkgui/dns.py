# -*- encoding: utf-8 -*-
'''
  DNS GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

from dialogs import SimpleEntryDialog
from diverse_classes import MultiplotList
import gtk

import config.dns

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.5"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


 
class DNSGUI:
  '''
    DNS GUI functions for the GTK Toolkit.
  '''
  def create_menu(self):
    '''
      Create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='DNS'>
        <menuitem action='SetOmegaOffset' />
        <menuitem action='SetIncrement' />
        <menuitem action='SetMultipleScattering' />
        <menuitem action='SetDSpacing' />
        <separator name='dns0' />
        <menuitem action='OmegaSlice' />
        <menuitem action='SeperateScattering' />
        <menuitem action='SeperatePreset' />
        <separator name='dns1' />
        <menuitem action='ReloadActive' />
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "DNS", None,                             # name, stock id
                "DNS", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SetOmegaOffset", None,                             # name, stock id
                "Omega Offset...", None,                    # label, accelerator
                None,                                   # tooltip
                self.change_omega_offset ),
            ( "SetDSpacing", None,                             # name, stock id
                "d-spacing...", None,                    # label, accelerator
                None,                                   # tooltip
                self.change_d_spacing ),
            ( "SetIncrement", None,                             # name, stock id
                "Change Increment", None,                    # label, accelerator
                "Change Increment between files with same Polarization",                                   # tooltip
                self.change_increment ),
            ( "SetMultipleScattering", None,                             # name, stock id
                "Change Multiple Scattering Propability", None,                    # label, accelerator
                None,                                   # tooltip
                self.change_multiple_scattering_propability ),
            ( "CorrectFlipping", None,                             # name, stock id
                "Correct for flipping-ratio", None,                    # label, accelerator
                "Correct scattering for the finite flipping-ratio.",                                   # tooltip
                self.correct_flipping_dialog ),
            ( "OmegaSlice", None,                             # name, stock id
                "Extract ω-scan", None,                    # label, accelerator
                "Extract a scan with fixed 2Θ value and changing ω.",                                   # tooltip
                self.extract_omega_slice ),
            ( "SeperateScattering", None,                             # name, stock id
                "Seperate Scattering", None,                    # label, accelerator
                "Calculate seperated scattering parts from polarization directions.",                                   # tooltip
                self.seperate_scattering ),
            ( "SeperatePreset", None,                             # name, stock id
                "Seperate from Preset", None,                    # label, accelerator
                "Calculate seperated scattering parts from polarization directions from presets.",               # tooltip
                self.seperate_scattering_preset ),
            ( "ReloadActive", None,                             # name, stock id
                "Reload Active Measurement", 'F5',                    # label, accelerator
                None,               # tooltip
                self.reload_active_measurement ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  def correct_flipping_dialog(self, action, window):
    '''
      In future this will set up a dialog to change the flipping ratio correction
    '''
    scattering_propability=0.1
    self.correct_flipping_ratio(scattering_propability)
    for dataset in self.active_file_data:
      dataset.make_corrections()
    window.replot()
  
  def change_omega_offset(self, action, window):
    '''
      A dialog to change the omega offset of the active map.
      If no map is active at the moment it does nothing.
    '''
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for ooff input +++++
    ooff_dialog=gtk.Dialog(title='Change omega offset:')
    ooff_dialog.set_default_size(100,50)
    ooff_dialog.add_button('OK', 1)
    ooff_dialog.add_button('Apply', 2)
    ooff_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,1,False)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text(str(self.file_options[self.active_file_name][1]))
    input_filed.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    up_button=gtk.Button("+")
    down_button=gtk.Button("-")
    table.attach(up_button,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                         0,
                0,                         0);
    table.attach(down_button,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                0,                         0,
                0,                         0);
    def toggle_up(*ignore):
      input_filed.set_text(str((float(input_filed.get_text())+10)%360))
      ooff_dialog.response(2)
    def toggle_down(*ignore):
      input_filed.set_text(str((float(input_filed.get_text())-10)%360))
      ooff_dialog.response(2)
    up_button.connect('clicked', toggle_up)
    down_button.connect('clicked', toggle_down)
    ooff_dialog.vbox.add(table)
    ooff_dialog.show_all()
    #----- Create a dialog window for ooff input -----
    # wait for user response
    result=ooff_dialog.run()
    while result > 1:
      # response is Apply
      ooff=float(input_filed.get_text())
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      if self.TRANSFORM_Q:
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
      window.replot()
      result=ooff_dialog.run()
    if result==1:
      # response is OK
      ooff=float(input_filed.get_text())
      self.file_options[self.active_file_name][1]=ooff
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      window.replot()
    ooff_dialog.destroy()

  def change_d_spacing(self, action, window):
    '''
      A dialog to change the d-spacing of the plots to calculate reciprocal lattice units.
    '''
    #+++++ Create a dialog window for ooff input +++++
    ds_dialog=gtk.Dialog(title='Set d-spacing for x and y directions:')
    ds_dialog.set_default_size(100,100)
    ds_dialog.add_button('OK', 1)
    ds_dialog.add_button('Apply', 2)
    ds_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,3,False)
    label=gtk.Label()
    label.set_text('Direction')
    table.attach(label, 0,1, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('label')
    table.attach(label, 1,2, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('d-spacing')
    table.attach(label, 2,3, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('x')
    table.attach(label, 0,1, 1,2,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('y')
    table.attach(label, 0,1, 2,3,  gtk.EXPAND|gtk.FILL,0, 0,0);
    input_filed_nx=gtk.Entry()
    input_filed_nx.set_width_chars(4)
    input_filed_nx.set_text(self.D_NAME_X)
    input_filed_nx.connect('activate', lambda *ignore: ds_dialog.response(2))
    table.attach(input_filed_nx,
                # X direction #          # Y direction
                1, 2,                      1, 2,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_ny=gtk.Entry()
    input_filed_ny.set_width_chars(4)
    input_filed_ny.set_text(self.D_NAME_Y)
    input_filed_ny.connect('activate', lambda *ignore: ds_dialog.response(2))
    table.attach(input_filed_ny,
                # X direction #          # Y direction
                1, 2,                      2, 3,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_dx=gtk.Entry()
    input_filed_dx.set_width_chars(4)
    input_filed_dx.set_text(str(self.D_SPACING_X))
    input_filed_dx.connect('activate', lambda *ignore: ds_dialog.response(2))
    table.attach(input_filed_dx,
                # X direction #          # Y direction
                2, 3,                      1, 2,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_dy=gtk.Entry()
    input_filed_dy.set_width_chars(4)
    input_filed_dy.set_text(str(self.D_SPACING_Y))
    input_filed_dy.connect('activate', lambda *ignore: ds_dialog.response(2))
    table.attach(input_filed_dy,
                # X direction #          # Y direction
                2, 3,                      2, 3,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    ds_dialog.vbox.add(table)
    ds_dialog.show_all()
    #----- Create a dialog window for ooff input -----
    # wait for user response
    result=ds_dialog.run()
    while result > 0:
      try:
        # response is Apply
        self.D_NAME_X=input_filed_nx.get_text()
        self.D_NAME_Y=input_filed_ny.get_text()
        self.D_SPACING_X=float(input_filed_dx.get_text())
        self.D_SPACING_Y=float(input_filed_dy.get_text())
        self.set_transformations()
        self.active_file_data[window.index_mess].calculate_wavevectors()
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
        window.replot()
        if result==1:
          break
        result=ds_dialog.run()
      except ValueError:
        result=ds_dialog.run()
        if result==1:
          break
    ds_dialog.destroy()

  def change_increment(self, action, window):
    '''
      Change the increments between files of the same polarization
      chanel. New maps are created after this change.
    '''
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for increment input +++++
    inc_dialog=gtk.Dialog(title='Change increment for same polarization:')
    inc_dialog.set_default_size(100,50)
    inc_dialog.add_button('OK', 1)
    inc_dialog.add_button('Cancle', 0)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text(str(self.file_options[self.active_file_name][2]))
    input_filed.show()
    input_filed.connect('activate', lambda *ignore: inc_dialog.response(1))
    inc_dialog.vbox.add(input_filed)
    #----- Create a dialog window for increment input -----
    result=inc_dialog.run()
    if result==1:
      # Answer is OK
      try:
        inc=int(input_filed.get_text())
        self.file_options[self.active_file_name][2]=inc
        self.create_maps(self.active_file_name)
        object=self.file_data[self.active_file_name]
        window.change_active_file_object((self.active_file_name, object))
      except ValueError:
        pass
    inc_dialog.destroy()
  
  def change_multiple_scattering_propability(self, action, window):
    '''
      Change the value for multiple scattering propability and 
      reacalculate the corrected dataset.
    '''
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for increment input +++++
    inc_dialog=gtk.Dialog(title='Change scattering propability for the flipping-ratio correction:')
    inc_dialog.set_default_size(100,50)
    inc_dialog.add_button('OK', 1)
    inc_dialog.add_button('Apply', 2)
    inc_dialog.add_button('Cancle', 0)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text(str(self.SCATTERING_PROPABILITY))
    input_filed.show()
    input_filed.connect('activate', lambda *ignore: inc_dialog.response(1))
    inc_dialog.vbox.add(input_filed)
    #----- Create a dialog window for increment input -----
    result=inc_dialog.run()
    while result>0:
      # Answer is OK or Apply
      try:
        new_sp=float(input_filed.get_text())
        self.SCATTERING_PROPABILITY=new_sp
        self.create_maps(self.active_file_name)
        object=self.file_data[self.active_file_name]
        window.change_active_file_object((self.active_file_name, object))
      except ValueError:
        pass
      if result==1:
        # leave the dialog on OK
        break
      else:
        result=inc_dialog.run()
    inc_dialog.destroy()

  def extract_omega_slice(self, action, window):
    '''
      Extract ω-scans with constant 2θ from all datasets. 
    '''
    params, result=SimpleEntryDialog('Defint 2θ-value for the slice...', [
                                    ('2θ-center', 90., float, gtk.Label('°')), 
                                    ('2θ-width', 2.6, float, gtk.Label('°'))
                                                                          ]).run()
    if not result:
      return None
    slices=[]
    for i, dataset in enumerate(self.active_file_data):
      if dataset.zdata<0:
        continue
      saved_x=dataset.xdata
      saved_y=dataset.ydata
      dataset.xdata=1
      dataset.ydata=3
      window.index_mess=i
      slice=window.file_actions.create_cross_section(
                        1, 0, 0, params['2θ-center'], params['2θ-width'], 
                        0.1, bin_distance=0.1
                                               )
      if slice is None:
        continue
      slice.ydata-=1
      slice.yerror-=1
      slice.data.pop(0)
      slice.short_info=dataset.short_info + ' 2θ='+str(params['2θ-center'])
      slice.sample_name=dataset.sample_name
      slice.number=str(i)
      slices.append(slice)
      dataset.xdata=saved_x
      dataset.ydata=saved_y
    if len(slices)==0:
      return None
    self.active_file_data=slices
    self.active_file_name=self.active_file_name+'-2Θ='+str(params['2θ-center'])
    self.file_data[self.active_file_name]=self.active_file_data
    window.index_mess=0
    window.measurement=self.active_file_data
    window.rebuild_menus()
    slices_names=[(slice, self.active_file_name) for slice in slices]
    window.multiplot.append(MultiplotList(slices_names))
    window.active_multiplot=True
    window.replot()

  def seperate_scattering_preset(self, action, window):
    '''
      A selection dialog to choose a preset for seperate_scattering.
    '''
    keys=sorted(config.dns.SEPERATION_PRESETS.keys())
    preset_box=gtk.combo_box_new_text()
    preset_box.append_text(keys[0])
    for key in keys[1:]:
      preset_box.append_text(key)
    preset_dialog=gtk.Dialog(title='Add polarization:')
    preset_dialog.set_default_size(100,50)
    preset_dialog.add_button('OK', 1)
    preset_dialog.add_button('Cancle', 0)
    preset_dialog.vbox.add(preset_box)
    preset_dialog.show_all()
    result=preset_dialog.run()
    key=keys[preset_box.get_active()]
    preset_dialog.destroy()
    if result==1:
      self.seperate_scattering(action, window, config.dns.SEPERATION_PRESETS[key])
  
  def seperate_scattering(self, action, window, preset=None):
    '''
      Add or substract measured polarizations from each other
      to calculate e.g. coherent magnetic scattering.
    '''
    # TODO: Review the dialog layout.
    if not self.active_file_name in self.file_options:
      return None
    # build a list of DNSMeasurementData objects in active_file_data for the polarizations
    polarization_list=[(object, self.active_file_name) for object in self.active_file_data if "dns_info" in dir(object)]
    for name, file_data_tmp in sorted(self.file_data.items()):
      polarization_list+=[(object, name) for object in file_data_tmp if (("dns_info" in dir(object)) and not (('|raw_data' in name)or (self.active_file_name is name)))]
    combine_list=[]
    def add_object():
      '''Subdialog to add one chanel to the separation.'''
      add_dialog=gtk.Dialog(title='Add polarization:')
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
      object_box.append_text('0-('+polarization_list[0][0].short_info+')')
      for i, object in enumerate(polarization_list[1:]):
        object_box.append_text(str(i+1)+'-('+object[0].short_info+','+object[1]+')')
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
    combine_dialog=gtk.Dialog(title='Combination of polarizations:')
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
          label=gtk.Label(item[1]+str(item[2])+'*{'+str(i)+'-('+polarization_list[item[0]][0].short_info+')}')
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
      self.calculate_combination(combine_list, polarization_list, input_filed.get_text())
    combine_dialog.destroy()
  
  def calculate_combination(self, combine_list, polarization_list, title):
    '''
      Calculate a combination of polarization directions as
      set in the combine_list.
      
      @param combine_layers List of how the chanels should be combined
      @param polarization_list The chanels which will be combined
      @param title Name of the new created chanel
    '''
    if combine_list[0][1] != '-':
      result=combine_list[0][2]*polarization_list[combine_list[0][0]][0]
    else:
      result=-1.*combine_list[0][2]*polarization_list[combine_list[0][0]][0]
    for object, sign, multiplier in combine_list[1:]:
      if sign == '+':
        result=result+multiplier*polarization_list[object][0]
      elif sign == '*':
        result=result*(multiplier*polarization_list[object][0])
      elif sign == '/':
        result=result/(multiplier*polarization_list[object][0])
      else:
        result=result-multiplier*polarization_list[object][0]
      if result is None:
        message=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='You can only combine polarizations with the same number of measured points!')
        message.run()
        message.destroy()
        return None
    result.short_info=title
    result.number=str(len(polarization_list))
    self.active_file_data.append(result)

  def reload_active_measurement(self, action, window):
    '''
      Reload the measurement active in the GUI.
    '''
    self.read_files(self.active_file_name.rsplit('|raw_data')[0])
    window.change_active_file_object((self.active_file_name, self.file_data[self.active_file_name]))
