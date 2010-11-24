# -*- encoding: utf-8 -*-
'''
  SQUID GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
from gtkgui.dialogs import PreviewDialog

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7rc1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class SquidGUI:
  '''
    Squid GUI functions for the GTK toolkit.
  '''
  
  def create_menu(self):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    string='''
      <menu action='SquidMenu'>
        <menuitem action='SquidDiaPara'/>
        <menuitem action='SubtractDataset'/>
        <menuitem action='SquidExtractRaw'/>
      </menu>
    '''
    # Create actions for the menu, functions are invoked with the window as
    # third parameter to make interactivity with the GUI possible
    actions=(
            ( "SquidMenu", None,                             # name, stock id
                "SQUID", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SquidDiaPara", None,                             # name, stock id
                "_Dia-/Paramagnetic Correction...", "<control>d",                    # label, accelerator
                None,                                   # tooltip
                self.dia_para_dialog ),
            ( "SquidExtractRaw", None,                             # name, stock id
                "Extract magnetic moment", None,                    # label, accelerator
                None,                                   # tooltip
                self.calc_moment_from_rawdata ),
            ( "SubtractDataset", None,                             # name, stock id
                "Subtract another dataset...", None,                    # label, accelerator
                None,                                   # tooltip
                self.subtract_dataset ),
             )
    return string,  actions
  
   #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  
  def dia_para_dialog(self, action, window):
    '''
      A dialog to enter the diamagnetic and paramagnetic correction.
      Diamagnetic correction can be calculated from a fit to the
      asymptotic behaviour of a MvsH measurement.
    '''
    import gtk
    units=window.measurement[window.index_mess].units()
    dia=self.dia_mag_correct
    para=self.para[0]
    if 'T' in units:
      dia*=1e4
      para*=1e4
    if 'A·m^2' in units:
      dia/=1e3
      para/=1e3
    dialog=gtk.Dialog(title="Enter diamagnetic and paramagnetic correction factors:", 
                      parent=window, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
    # create a table with the entries
    table=gtk.Table(4, 4, False)
    top_label=gtk.Label("\nYou can enter a diamgnetic and paramagnetic Correction Factor here,\n"+\
                        "the data will then be correct as: NEWDATA=DATA - PARA * 1/T + DIA.\n\n")
    table.attach(top_label,
                # X direction #          # Y direction
                0, 3,                      0, 1,
                0,                       gtk.FILL|gtk.EXPAND,
                0,                         0)
    label=gtk.Label("Diamagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    dia_entry=gtk.Entry()
    dia_entry.set_text(str(dia))
    table.attach(dia_entry,
                # X direction #          # Y direction
                2, 4,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    
    fit_button=gtk.Button("Fit asymptotes")
    table.attach(fit_button,
                # X direction #          # Y direction
                0, 1,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    label=gtk.Label("of MvsH measurement, excluding ±")
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      2, 3,
                gtk.FILL,                       gtk.FILL,
                0,                         0)
    fit_exclude_regtion=gtk.Entry()
    fit_exclude_regtion.set_width_chars(4)
    fit_exclude_regtion.set_text("1")
    table.attach(fit_exclude_regtion,
                # X direction #          # Y direction
                2, 3,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    ignore_errors=gtk.CheckButton("ignore errors")
    table.attach(ignore_errors,
                # X direction #          # Y direction
                3, 4,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    
    label=gtk.Label("Paramagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    para_entry=gtk.Entry()
    para_entry.set_text(str(para))
    table.attach(para_entry,
                # X direction #          # Y direction
                2, 4,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    # insert the table and buttons to the dialog
    dialog.vbox.add(table)
    dialog.add_button("OK", 2)
    dialog.add_button("Apply", 1)
    dialog.add_button("Cancel", 0)
    fit_button.connect("clicked", lambda *ignore: dialog.response(3))
    fit_exclude_regtion.connect("activate", lambda *ignore: dialog.response(3))
    dia_entry.connect("activate", lambda *ignore: dialog.response(2))
    para_entry.connect("activate", lambda *ignore: dialog.response(2))
    dialog.show_all()
    dialog.connect("response", self.dia_para_response, window, [dia_entry, para_entry, fit_exclude_regtion, ignore_errors])
  
  def dia_para_response(self, dialog, response, window, entries):
    '''
      Evaluate the response of the dialog from dia_para_dialog.
    '''
    if response==0:
      units=window.measurement[window.index_mess].units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia*=1e4
        para*=1e4
      if 'A·m^2' in units:
        dia/=1e3
        para/=1e3
      self.dia_para_correction(window.measurement[window.index_mess], 
                               dia, para)
      window.replot()      
      dialog.destroy()
      return None
    try:
      dia=float(entries[0].get_text())
    except ValueError:
      dia=0.
      entries[0].set_text("0")
    try:
      para=float(entries[1].get_text())
    except ValueError:
      para=0.
      entries[1].set_text("0")
    try:
      split=float(entries[2].get_text())
    except ValueError:
      split=1.
      entries[2].set_text("1")
    if response==3:
      dataset=window.measurement[window.index_mess]
      if dataset.xdata==1:
        from fit_data import FitDiamagnetism
        # fit after paramagnetic correction
        self.dia_para_correction(dataset, 0. , para)
        fit=FitDiamagnetism(([0, 0, 0, split]))
        if not entries[3].get_active():
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values, 
                     dataset.data[dataset.yerror].values)
        else:
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values)
        entries[0].set_text(str(-fit.parameters[0]))
      return None
    if response>0:
      self.dia_para_correction(window.measurement[window.index_mess], dia, para)
      window.replot()
    if response==2:
      # if OK is pressed, apply the corrections and save as global.
      units=window.measurement[window.index_mess].units()
      if 'T' in units:
        dia/=1e4
        para/=1e4
      if 'A·m^2' in units:
        dia*=1e3
        para*=1e3      
      self.dia_mag_correct=dia
      self.para[0]=para
      dialog.destroy()
    
  
  def dia_para_dialog(self, action, window):
    '''
      A dialog to enter the diamagnetic and paramagnetic correction.
      Diamagnetic correction can be calculated from a fit to the
      asymptotic behaviour of a MvsH measurement.
    '''
    import gtk
    units=window.measurement[window.index_mess].units()
    dia=self.dia_mag_correct
    para=self.para[0]
    if 'T' in units:
      dia*=1e4
      para*=1e4
    if 'A·m^2' in units:
      dia/=1e3
      para/=1e3
    dialog=gtk.Dialog(title="Enter diamagnetic and paramagnetic correction factors:", 
                      parent=window, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
    # create a table with the entries
    table=gtk.Table(4, 4, False)
    top_label=gtk.Label("\nYou can enter a diamgnetic and paramagnetic Correction Factor here,\n"+\
                        "the data will then be correct as: NEWDATA=DATA - PARA * 1/T + DIA.\n\n")
    table.attach(top_label,
                # X direction #          # Y direction
                0, 3,                      0, 1,
                0,                       gtk.FILL|gtk.EXPAND,
                0,                         0)
    label=gtk.Label("Diamagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    dia_entry=gtk.Entry()
    dia_entry.set_text(str(dia))
    table.attach(dia_entry,
                # X direction #          # Y direction
                2, 4,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    
    fit_button=gtk.Button("Fit asymptotes")
    table.attach(fit_button,
                # X direction #          # Y direction
                0, 1,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    label=gtk.Label("of MvsH measurement, excluding ±")
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      2, 3,
                gtk.FILL,                       gtk.FILL,
                0,                         0)
    fit_exclude_regtion=gtk.Entry()
    fit_exclude_regtion.set_width_chars(4)
    fit_exclude_regtion.set_text("1")
    table.attach(fit_exclude_regtion,
                # X direction #          # Y direction
                2, 3,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    ignore_errors=gtk.CheckButton("ignore errors")
    table.attach(ignore_errors,
                # X direction #          # Y direction
                3, 4,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    
    label=gtk.Label("Paramagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    para_entry=gtk.Entry()
    para_entry.set_text(str(para))
    table.attach(para_entry,
                # X direction #          # Y direction
                2, 4,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    # insert the table and buttons to the dialog
    dialog.vbox.add(table)
    dialog.add_button("OK", 2)
    dialog.add_button("Apply", 1)
    dialog.add_button("Cancel", 0)
    fit_button.connect("clicked", lambda *ignore: dialog.response(3))
    fit_exclude_regtion.connect("activate", lambda *ignore: dialog.response(3))
    dia_entry.connect("activate", lambda *ignore: dialog.response(2))
    para_entry.connect("activate", lambda *ignore: dialog.response(2))
    dialog.show_all()
    dialog.connect("response", self.dia_para_response, window, [dia_entry, para_entry, fit_exclude_regtion, ignore_errors])
  
  def dia_para_response(self, dialog, response, window, entries):
    '''
      Evaluate the response of the dialog from dia_para_dialog.
    '''
    if response==0:
      units=window.measurement[window.index_mess].units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia*=1e4
        para*=1e4
      if 'A·m^2' in units:
        dia/=1e3
        para/=1e3
      self.dia_para_correction(window.measurement[window.index_mess], 
                               dia, para)
      window.replot()      
      dialog.destroy()
      return None
    try:
      dia=float(entries[0].get_text())
    except ValueError:
      dia=0.
      entries[0].set_text("0")
    try:
      para=float(entries[1].get_text())
    except ValueError:
      para=0.
      entries[1].set_text("0")
    try:
      split=float(entries[2].get_text())
    except ValueError:
      split=1.
      entries[2].set_text("1")
    if response==3:
      dataset=window.measurement[window.index_mess]
      if dataset.xdata==1:
        from fit_data import FitDiamagnetism
        # fit after paramagnetic correction
        self.dia_para_correction(dataset, 0. , para)
        fit=FitDiamagnetism(([0, 0, 0, split]))
        if not entries[3].get_active():
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values, 
                     dataset.data[dataset.yerror].values)
        else:
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values)
        entries[0].set_text(str(-fit.parameters[0]))
      return None
    if response>0:
      self.dia_para_correction(window.measurement[window.index_mess], dia, para)
      window.replot()
    if response==2:
      # if OK is pressed, apply the corrections and save as global.
      units=window.measurement[window.index_mess].units()
      if 'T' in units:
        dia/=1e4
        para/=1e4
      if 'A·m^2' in units:
        dia*=1e3
        para*=1e3      
      self.dia_mag_correct=dia
      self.para[0]=para
      dialog.destroy()
    
  #-------------------------- GUI functions --------------------------------

  def toggle_correction(self, action, window):
    '''
      do or undo dia-/paramagnetic correction
    '''
    name=action.get_name()
    for dataset in self.active_file_data:
      units=dataset.units()
      if 'T' in units:
        self.dia_mag_correct*=1e4
        self.para[0]*=1e4
      if 'A·m^2' in units:
        self.dia_mag_correct/=1e3
        self.para[0]/=1e3
      if name=='SquidDia':
        if dataset.dia_corrected:
          dataset.process_function(self.diamagnetic_correction_undo)
          dataset.dia_corrected=False
        else:
          dataset.process_function(self.diamagnetic_correction)
          dataset.dia_corrected=True
      if name=='SquidPara':
        if dataset.para_corrected:
          dataset.process_function(self.paramagnetic_correction_undo)
          dataset.para_corrected=False
        else:
          dataset.process_function(self.paramagnetic_correction)
          dataset.para_corrected=True
      units=dataset.units()
      if 'T' in units:
        self.dia_mag_correct/=1e4
        self.para[0]/=1e4
      if 'A·m^2' in units:
        self.dia_mag_correct*=1e3
        self.para[0]*=1e3
    window.replot()
  
  def calc_moment_from_rawdata(self, action, window, start_point=None, end_point=None):
    '''
      Try to fit the SQUID signal to retrieve the magnetic moment of a sample,
      in the future this will be extendet to use different sample shape functions.
    '''
    # check if this is a squid raw data file
    dims=self.active_file_data[0].dimensions()
    units=self.active_file_data[0].units()
    if not 'V_{SC-long}' in dims or\
        not ('H' in dims or '\xce\xbc_0\xc2\xb7H' in dims) or\
        not 'T' in dims or\
        not self.ALLOW_FIT:
      return False
    from fit_data import FitSession
    try:
      field_index=dims.index('\xce\xbc_0\xc2\xb7H')
    except ValueError:
      field_index=dims.index('H')
    field_unit=units[field_index]
    temp_index=dims.index('T')
    temp_unit=units[temp_index]
    v_index=dims.index('V_{SC-long}')
    from measurement_data_structure import MeasurementData      
    # select a data subset
    raw_data=self.active_file_data[start_point:end_point]
    # create object for extracted data
    extracted_data=MeasurementData([['Point', 'No.'], 
                                    [dims[field_index], field_unit], 
                                    ['T', temp_unit], 
                                    ['M_{fit}', 'emu'], 
                                    ['dM_{fit}', 'emu'], 
                                    ['Sample Pos._{fit}', 'cm'], 
                                    ['sigma_{fit}', 'cm'], 
                                    ],[],2,3,4)
    extracted_data.short_info='Magnetization data extracted via fitting'
    for i, data in enumerate(raw_data):
      if i%50 == 0:
        print "Extracting datapoint No: %i" %i
      data.ydata=v_index
      data.dydata=v_index
      fit_object=FitSession(data)
      data.fit_object=fit_object
      fit_object.add_function('SQUID RAW-data')
      fit_object.fit()
      fit_object.simulate()
      fit_data=fit_object.functions[0][0].parameters
      extracted_data.append((i, data.get_data(0)[field_index], data.get_data(0)[temp_index], fit_data[0], fit_data[0], fit_data[1], fit_data[2]))
      self.active_file_data.append(extracted_data) 

  def subtract_dataset(self, action, window):
    '''
      Subtract one dataset from another using interpolated values.
    '''
    if window.measurement[window.index_mess].zdata>=0:
      return None
    selection_dialog=PreviewDialog(self.file_data, 
                                title='Select Dataset for Subtraction...', 
                                show_previews=False, 
                                buttons=('OK', 1, 'Cancel', 0), 
                                parent=window, 
                                flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                single_selection=True
                                )
    selection_dialog.set_default_size(800, 600)
    selection_dialog.set_preview_parameters(window.plot, self, self.TEMP_DIR+'plot_temp.png')
    result=selection_dialog.run()
    if result==1:
      object=selection_dialog.get_active_objects()[0]
      dataset=window.measurement[window.index_mess]
      newdata=self.do_subtract_dataset(dataset, object)
      window.measurement.insert(window.index_mess+1, newdata)
      window.index_mess+=1
      window.replot()
    selection_dialog.destroy()