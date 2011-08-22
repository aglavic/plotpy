# -*- encoding: utf-8 -*-
'''
  KWS2 GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import os
import gtk
from glob import glob
# own modules
import config.kws2
from dialogs import SimpleEntryDialog

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.9"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class KWS2GUI:
  def new_configuration(self, setups, file_name, folder):
    '''
      Create a new intrumental setup.
    '''
    file_type=file_name.rsplit('.', 1)[-1]
    if file_type == 'cmb':
      # riso dataset
      setup=dict(config.kws2.setup_config_riso)
    else:
      setup=dict(config.kws2.setup_config)
    dialog=gtk.Dialog('Setup parameters:')
    table=gtk.Table(3, 7, False)
    # labels
    label_center_x=gtk.Label('Horizontal Beamcenter:')
    label_center_y=gtk.Label('Vertical Beamcenter:')
    label_detector_distance=gtk.Label('Detector distance:')
    if file_type in ['edf', 'cmb', 'bin']:
      label_lambda_n=gtk.Label('X-ray Wavelength λ:')
    else:
      label_lambda_n=gtk.Label('Neutron Wavelength λ:')
    label_detector_sensitivity=gtk.Label('Sensitivity measurement:')
    label_background=gtk.Label('Background measurement:')
    label_apply=gtk.Label('Apply this to files:')
    rl_center_x=gtk.Label('pix')
    rl_center_y=gtk.Label('pix')
    rl_detector_distance=gtk.Label('mm')
    rl_lambda_n=gtk.Label('Å')
    # entries
    entry_center_x=gtk.Entry()
    entry_center_x.set_text(str(setup['CENTER_X']))
    entry_center_y=gtk.Entry()
    entry_center_y.set_text(str(setup['CENTER_Y']))
    entry_detector_distance=gtk.Entry()
    entry_detector_distance.set_text(str(setup['DETECTOR_DISTANCE']))
    entry_lambda_n=gtk.Entry()
    entry_lambda_n.set_text(str(setup['LAMBDA_N']))
    entry_apply=gtk.Entry()
    entry_apply.set_text(file_name)
    toggle_button_swapyz=gtk.CheckButton('Swap z to horizontal ')
    entry_detector_sensitivity=gtk.Entry()
    entry_detector_sensitivity.set_text('None')
    button_detector_sensitivity=gtk.Button(None, gtk.STOCK_OPEN)
    button_detector_sensitivity.connect('clicked', self.select_file, folder, entry_detector_sensitivity)
    entry_background=gtk.Entry()
    entry_background.set_text('None')
    button_background=gtk.Button(None, gtk.STOCK_OPEN)
    button_background.connect('clicked', self.select_file, folder, entry_background)
    # add to table
    table.attach(label_center_x, 0,1, 0,1, gtk.FILL,0, 0,0);
    table.attach(label_center_y, 0,1, 1,2, gtk.FILL,0, 0,0);
    table.attach(label_detector_distance, 0,1, 2,3, gtk.FILL,0, 0,0);
    table.attach(label_lambda_n, 0,1, 3,4, gtk.FILL,0, 0,0);
    if not file_type in ['cmb']:
      table.attach(label_detector_sensitivity, 0,1, 5,6, gtk.FILL,0, 0,0);
      table.attach(label_background, 0,1, 6,7, gtk.FILL,0, 0,0);
      table.attach(toggle_button_swapyz, 1,3, 4,5, gtk.EXPAND|gtk.FILL,0, 0,0);
      table.attach(entry_detector_sensitivity, 1,2, 5,6, gtk.EXPAND|gtk.FILL,0, 0,0);
      table.attach(entry_background, 1,2, 6,7, gtk.EXPAND|gtk.FILL,0, 0,0);
      table.attach(button_detector_sensitivity, 2,3, 5,6, gtk.FILL,0, 0,0);  
      table.attach(button_background, 2,3, 6,7, gtk.FILL,0, 0,0);  
    table.attach(label_apply, 0,1, 7,8, gtk.FILL,0, 0,0);
    table.attach(entry_center_x, 1,2, 0,1, 0,0, 0,0);
    table.attach(entry_center_y, 1,2, 1,2, 0,0, 0,0);
    table.attach(entry_detector_distance, 1,2, 2,3, 0,0, 0,0);
    table.attach(entry_lambda_n, 1,2, 3,4, 0,0, 0,0);
    table.attach(entry_apply, 1,2, 7,8, gtk.EXPAND|gtk.FILL,0, 0,0);
    table.attach(rl_center_x, 2,3, 0,1, gtk.FILL,0, 0,0);
    table.attach(rl_center_y, 2,3, 1,2, gtk.FILL,0, 0,0);
    table.attach(rl_detector_distance, 2,3, 2,3, gtk.FILL,0, 0,0);  
    table.attach(rl_lambda_n, 2,3, 3,4, gtk.FILL,0, 0,0);  
    
    dialog.vbox.add(table)
    dialog.show_all()
    dialog.run()
    
    # read the configuration
    setup_name=entry_apply.get_text()
    if not os.path.join(folder, file_name) in glob(os.path.join(folder, setup_name)):
      setup_name=file_name
    detector_sensitivity=entry_detector_sensitivity.get_text()
    if not os.path.exists(os.path.join(folder, detector_sensitivity)):
      detector_sensitivity=None
    setup['DETECTOR_SENSITIVITY']=detector_sensitivity
    background=entry_background.get_text()
    if not os.path.exists(os.path.join(folder, background)):
      background=None
    setup['BACKGROUND']=background
    try:
      setup['CENTER_X']=float(entry_center_x.get_text())
    except:
      pass
    try:
      setup['CENTER_Y']=float(entry_center_y.get_text())
    except:
      pass
    try:
      setup['LAMBDA_N']=float(entry_lambda_n.get_text())
    except:
      pass
    try:
      setup['DETECTOR_DISTANCE']=float(entry_detector_distance.get_text())
    except:
      pass
    setup['SWAP_YZ']=toggle_button_swapyz.get_active()
    setups[setup_name]=setup
    setups.write()
    dialog.destroy()

  def select_file(self, action, folder, entry_detector_sensitivity):
    '''
      Select a file for the sensitivity measurement.
    '''
    dialog=gtk.FileChooserDialog(title='Select file...', action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=('OK', 1))
    dialog.set_current_folder(folder)
    result=dialog.run()
    if result==1:
      entry_detector_sensitivity.set_text(os.path.relpath(dialog.get_filename(), start=folder))
    dialog.destroy()

  def create_menu(self):
    '''
      Create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='GISAS'>
        <menuitem action='SeperateScattering' />
        <menuitem action='AutoBackground' />
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "GISAS", None,                             # name, stock id
                "GISAS", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SeperateScattering", None,                             # name, stock id
                "Seperate Scattering", None,                    # label, accelerator
                "Calculate seperated scattering parts from polarization directions.",                                   # tooltip
                self.seperate_scattering ),
            ( "AutoBackground", None,                             # name, stock id
                "Automatically Subtract Background", None,                    # label, accelerator
                "",                                   # tooltip
                self.do_autosubtract_background ),
                )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def seperate_scattering(self, action, window, preset=None):
    '''
      Add or substract measured polarizations from each other
      to calculate e.g. coherent magnetic scattering.
    '''
    # build a list of MeasurementData objects in active_file_data for the polarizations
    polarization_list=[(object[1][0],object[0]) for object in self.file_data.items()]
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
        object_box.append_text(str(i+1)+'-('+object[0].short_info+')')
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
      window.index_mess=len(self.active_file_data)-1
      window.replot()
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

  def do_autosubtract_background(self, action, window):
    fraction_entry=SimpleEntryDialog('Enter Minimal Background Fraction...', [('Fraction (1/x)', 5., float)])
    values, ok=fraction_entry.run()
    fraction_entry.destroy()
    if ok:
      bg_fraction=values['Fraction (1/x)']
      bg=self.autosubtract_background(self.active_file_data[window.index_mess], bg_fraction)
      window.replot()
      print "%i background subtracted" % bg
