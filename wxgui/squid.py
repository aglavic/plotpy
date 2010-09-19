# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in squid session.
'''

import wx

from dialogs import PreviewDialog

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SquidGUI:
  def create_menu(self, home):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    print 'squid.py: Entry create_menu: self = ', self

#     SQUID Menu

    menu_list = []    
    
    title        = 'SQUID'
    menuSquid    = wx.Menu()
 
    id = menuSquid.Append( wx.ID_ANY, 'Dia-/Paramagnetic Correction...',
                           'Dia-/Paramagnetic Correction...').GetId()
    act = 'SquidDiaPara'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda evt, arg1=act, arg2=home, arg3=self.dia_para_dialog: arg3(  arg1, arg2) )
  
    id = menuSquid.Append( wx.ID_ANY, 'Substract another dataset ...',
                           'Substract anaother dataset').GetId()
    act = 'SubstractDataset'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda evt, arg1=act, arg2=home, arg3=self.substract_dataset: arg3( evt, arg1, arg2) )
 
    id = menuSquid.Append( wx.ID_ANY, 'Extract magnetic moment',
                           'Extract magnetic moment').GetId()
    act = 'SquidExtractRaw'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda evt, arg1=act, arg2=home, arg3=self.calc_moment_from_rawdata: arg3( evt, arg1, arg2) )

    menu = [menuSquid, title]
    print 'menu = ', menu
    menu_list.append(menu) 
    return menu_list



   #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  
  def dia_para_dialog(self, action, window):
    '''
      A dialog to enter the diamagnetic and paramagnetic correction.
      Diamagnetic correction can be calculated from a fit to the
      asymptotic behaviour of a MvsH measurement.
    '''


    print 'squid.py: Entry  dia_para_dialog'

    units=window.measurement[window.index_mess].units()
    dia=self.dia_mag_correct
    para=self.para[0]
    if 'T' in units:
      dia*=1e4
      para*=1e4
    if 'A·m²' in units:
      dia/=1e3
      para/=1e3

    dialog = wx.Dialog(window, wx.ID_ANY, title="Enter diamagnetic and paramagnetic correction factors:",
                               size=wx.Size(600,280),
                               style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )
    vbox        = wx.BoxSizer( wx.VERTICAL )
    table       = wx.GridBagSizer(  )
    butBox      = wx.StaticBox( dialog, wx.ID_ANY, style=wx.BORDER_DOUBLE|wx.BORDER_RAISED )
    butBoxSizer = wx.StaticBoxSizer(butBox, wx.HORIZONTAL )
    dialog.SetSizer( vbox )

      
    top_label = wx.StaticText(dialog, wx.ID_ANY, label="\nYou can enter a diamgnetic and paramagnetic Correction Factor here,\n"+\
                        "the data will then be correct as: NEWDATA=DATA - PARA * 1/T + DIA.\n\n")
    table.Add(top_label, wx.GBPosition(0,0), span=wx.GBSpan(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)
 
    label = wx.StaticText( dialog, wx.ID_ANY, label= "Diamagnetic Correction: ", style=wx.ALIGN_CENTRE )
    table.Add(label, wx.GBPosition(1,0), span=wx.GBSpan(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)

    dia_entry = wx.TextCtrl( dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    dia_entry.SetValue(str(dia))
    table.Add(dia_entry, wx.GBPosition(1,3), span=wx.GBSpan(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)
    
    fit_button = wx.Button(dialog, wx.ID_ANY, label="Fit asymptotes")
    table.Add(fit_button, wx.GBPosition(2,0),  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)
 
    label = wx.StaticText(dialog, wx.ID_ANY, label='of MvsH measurement, excluding ±')
    table.Add(label, wx.GBPosition(2,1),  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)

    fit_exclude_regtion = wx.TextCtrl(dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    fit_exclude_regtion.SetMaxLength(4)
    fit_exclude_regtion.SetValue("1")
    table.Add(fit_exclude_regtion, wx.GBPosition(2,2),  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)

    ignore_errors = wx.CheckBox(dialog, wx.ID_ANY, label="ignore errors")
    table.Add( ignore_errors, wx.GBPosition(2,3),  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)
    
    label = wx.StaticText(dialog, wx.ID_ANY, label='Paramagnetic Correction: ', style=wx.ALIGN_CENTRE)
    table.Add(label, wx.GBPosition(3,0), span=wx.GBSpan(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)

    para_entry = wx.TextCtrl( dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    para_entry.SetValue(str(para))
    table.Add(para_entry, wx.GBPosition(3,2), span=wx.GBSpan(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3)

    # insert the table and buttons to the dialog
    vbox.Add(table)
    butOk     = wx.Button( dialog, wx.ID_ANY, label='OK')            # returns 2
    butApply  = wx.Button( dialog, wx.ID_ANY, label='Apply')         # returns 1
    butCancel = wx.Button( dialog, wx.ID_ANY, label='Cancel')        # returns 0
    butOk.Bind( event=wx.EVT_BUTTON, handler=lambda  evt, arg1=dialog, arg2=2, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func(evt, arg1, arg2, arg3, arg4) )
    butApply.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=dialog, arg2=1, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )
    butCancel.Bind( event=wx.EVT_BUTTON, handler=lambda  evt, arg1=dialog, arg2=0, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )

    butBoxSizer.Add(butOk,     0, wx.EXPAND|wx.ALL, border=3)
    butBoxSizer.Add(butApply,  0, wx.EXPAND|wx.ALL, border=3)
    butBoxSizer.Add(butCancel, 0, wx.EXPAND|wx.ALL, border=3)

    vbox.Add(butBoxSizer, 0, wx.EXPAND|wx.ALL, border=3)                            

    fit_button.Bind(event = wx.EVT_BUTTON,  handler=lambda  evt, arg1=dialog, arg2=3, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )
    fit_exclude_regtion.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda  evt, arg1=dialog, arg2=3, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )
    dia_entry.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda  evt, arg1=dialog, arg2=2, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )
    para_entry.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda  evt, arg1=dialog, arg2=2, arg3=window,
                                     arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors],
                                     func=self.dia_para_response:
                                     func( evt, arg1, arg2, arg3, arg4) )
    
    dialog.Bind( event=wx.EVT_CLOSE, handler=lambda evt, func=self.dia_para_response, 
                                                    arg1=dialog, arg2=0, arg3=window,
                                                    arg4=[dia_entry, para_entry, fit_exclude_regtion, ignore_errors]:
                                                    func(evt, arg1, arg2, arg3, arg4) )
    dialog.ShowModal()
  

  def dia_para_response(self, evt, dialog, response, window, entries):
    '''
    Evaluate the response of the dialog from dia_para_dialog.
    '''
    print 'squid.py: entry dia_para_response response = ', response
    print 'entries=',entries
    if response==0:
      units=window.measurement[window.index_mess].units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia*=1e4
        para*=1e4
      if 'A·m²' in units:
        dia/=1e3
        para/=1e3
      self.dia_para_correction(window.measurement[window.index_mess], 
                               dia, para)
      window.replot()      
      dialog.Destroy()
      return None
    try:
      dia=float(entries[0].GetValue())
    except ValueError:
      dia=0.
      entries[0].set_text("0")
    try:
      para=float(entries[1].GetValue())
    except ValueError:
      para=0.
      entries[1].SetValue("0")
    try:
      split=float(entries[2].GetValue())
    except ValueError:
      split=1.
      entries[2].SetValue("1")
    if response==3:
      dataset=window.measurement[window.index_mess]
      if dataset.xdata==1:
        from fit_data import FitDiamagnetism
        # fit after paramagnetic correction
        self.dia_para_correction(dataset, 0. , para)
        fit=FitDiamagnetism(([0, 0, 0, split]))
        
        if not entries[3].IsChecked():
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values, 
                     dataset.data[dataset.yerror].values)
        else:
          fit.refine(dataset.data[1].values, 
                     dataset.data[-1].values)
        entries[0].SetValue(str(-fit.parameters[0]))
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
      if 'A·m²' in units:
        dia*=1e3
        para*=1e3      
      self.dia_mag_correct=dia
      self.para[0]=para
      dialog.Destroy()
    

  
  def substract_dataset(self, event, action, window):
    '''
      Subtract one dataset from another using interpolated values.
    '''
    print 'squid.py: Entry  substract_dataset'
    print 'action = ',action
    print 'window = ', window
    if window.measurement[window.index_mess].zdata>=0:
      return None
    import gtk
    selection_dialog=PreviewDialog(window, self.file_data, 
                                show_previews=False, 
                                buttons=('OK', 1, 'Cancel', 0), 
                                single_selection=True,
                                title='Select Dataset for Subtraction...',
                                style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP
                              )
    selection_dialog.SetSize( wx.Size(800, 600) )
    selection_dialog.set_preview_parameters(window.plot, self, self.TEMP_DIR+'plot_temp.png')
    result = selection_dialog.run()
    if result==1:
      object = selection_dialog.get_active_objects()[0]
      dataset=window.measurement[window.index_mess]
      newdata=self.do_subtract_dataset(dataset, object)
      window.measurement.insert(window.index_mess+1, newdata)
      window.index_mess+=1
      window.replot()
    print 'squid.py: vor selection_dialog.Destroy'  
    selection_dialog.Destroy()


  
  def calc_moment_from_rawdata(self, event, action, window):
    '''
      Try to fit the SQUID signal to retrieve the magnetic moment of a sample,
      in the future this will be extendet to use different sample shape functions.
    '''
    print 'squid.py: Entry calc_moment_from_rawdata'

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
      extracted_data.append((i, data.get_data(0)[field_index],
                             data.get_data(0)[temp_index],
                             fit_data[0], fit_data[0], fit_data[1], fit_data[2]))
      self.active_file_data.append(extracted_data)
      
    print 'squid.py: return from  calc_moment_from_rawdata'