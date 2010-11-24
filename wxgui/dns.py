# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in DNS session.
'''

import wx
if __name__ == '__main__':
 import sys
 sys.path.append('..')
else:
 import config.dns

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7rc1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class DNSGUI:
  '''
    wx functions for the dns sessions.
  '''
  
  def create_menu(self, home):
    '''
      Create a specifig menu for the DNS session
    '''

    print 'dns.py: Entry create_menu'
    menu_list = []    
    
    title       = 'DNS'
    menuDNS    = wx.Menu()
 
    id = menuDNS.Append( wx.ID_ANY, 'Omega Offset',
                           'Set Omega Offset').GetId()
    act = 'SetOmegaOffset'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.change_omega_offset: function(  arg1, arg2) )

    id = menuDNS.Append( wx.ID_ANY, 'Change Increment',
                           'Change Increment between files with same Polarization').GetId()
    act = 'SetIncrement'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.change_increment: function(  arg1, arg2) )

    id = menuDNS.Append( wx.ID_ANY, 'Change Multiple Scattering Propability',
                           'Change Multiple Scatttering Propability').GetId()
    act = 'SetMultipleScattering'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.change_multiple_scattering_propability: function(  arg1, arg2) )

    id = menuDNS.Append( wx.ID_ANY, 'd-spacing ...',
                           'd-spacing ...').GetId()
    act = 'SetDSpacing '
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.change_d_spacing: function(  arg1, arg2) )
  
#    id = menuDNS.Append( wx.ID_ANY, 'Correct for flipping-ratio',
#                           'Correct scattering for the finite flipping ratio').GetId()
#    act = 'CorrectFlipping'
#    home.Bind( wx.EVT_MENU, id= id,
#               handler=lambda  arg1=act, arg2=home, function=self.correct_flipping_dialog: function(  arg1, arg2) )

    id = menuDNS.Append( wx.ID_ANY, 'Separate Scattering',
                           'Calculate separated scattering parts from polarization directions').GetId()
    act = 'SeperateScattering'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.seperate_scattering: function(  arg1, arg2) )

    id = menuDNS.Append( wx.ID_ANY, 'Separate from Preset',
                           'Calculate separated scattering parts from polarization directions from presets').GetId()
    act = 'SeperatePreset'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda arg1=act, arg2=home, function=self.separate_scattering_preset: function( arg1, arg2) )

    menuDNS.AppendSeparator()

    id = menuDNS.Append( wx.ID_ANY, 'Reload Active Measurement',
                           'Reload Active Measurement').GetId()
    act = 'ReloadActive'
    home.Bind( wx.EVT_MENU, id= id,
               handler=lambda  arg1=act, arg2=home, function=self.reload_active_measurement: function(  arg1, arg2) )


    menu = [menuDNS, title]
    print 'menu = ', menu
    menu_list.append(menu) 
    return menu_list



  #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  def correct_flipping_dialog(self, action, window):
    '''
      In future this will set up a dialog to change the flipping ratio correction
    '''
    print 'dns.py: Entry correct_flipping_dialog'
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
    print 'dns.py: Entry change_omega_offset: action = ', action
    if not self.active_file_name in self.file_options:
      return None

    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        elif id == idButApply:
           ret = 2
        ooff_dialog.EndModal( ret )

    print 'dns.py: entry correct_flipping_dialog'
    #+++++ Create a dialog window for ooff input +++++
    ooff_dialog = wx.Dialog(window, wx.ID_ANY, title='Change omega offset:', size=(500,200),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    ooff_dialog.SetSizer( vbox )

    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butOk      = wx.Button( ooff_dialog, wx.ID_ANY, label='OK' )
    butApply   = wx.Button( ooff_dialog, wx.ID_ANY, label='Apply' )
    butCancel  = wx.Button( ooff_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    idButApply = butApply.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butApply, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butApply.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)

    input_filed = wx.TextCtrl(ooff_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER  )
    input_filed.SetMaxLength(50)
    input_filed.SetValue( str(self.file_options[self.active_file_name][1]) )

    input_filed.Bind(event=wx.EVT_TEXT_ENTER, handler = lambda *ignore: ooff_dialog.EndModal(2) )

    table = wx.BoxSizer( wx.HORIZONTAL )
    up_button   = wx.Button(ooff_dialog, wx.ID_ANY, label="+", style=wx.BU_EXACTFIT )
    down_button = wx.Button(ooff_dialog, wx.ID_ANY, label="-", style=wx.BU_EXACTFIT )
    table.Add( input_filed, 1, wx.ALL|wx.EXPAND, 3)
    table.Add( up_button,   0, wx.ALL, 3)
    table.Add( down_button, 0, wx.ALL, 3)

    def toggle_up(*ignore):
      input_filed.SetValue(str((float(input_filed.GetValue())+10)%360))
      ooff_dialog.EndModal(2)
    def toggle_down(*ignore):
      input_filed.SetValue(str((float(input_filed.GetValue())-10)%360))
      ooff_dialog.EndModal(2)

    up_button.Bind(event=wx.EVT_BUTTON, handler=toggle_up)
    down_button.Bind(event=wx.EVT_BUTTON, handler=toggle_down)

    vbox.Add(table, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)

    #----- Create a dialog window for ooff input -----
    # wait for user response
    ooff_dialog.Fit()
    result = ooff_dialog.ShowModal()
    while result > 1:
      # response is Apply
      ooff=float(input_filed.GetValue())
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      if self.TRANSFORM_Q:
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
      window.replot()
      result = ooff_dialog.ShowModal()
    if result==1:
      # response is OK
      ooff = float(input_filed.GetValue())
      self.file_options[self.active_file_name][1]=ooff
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      window.replot()

    ooff_dialog.Destroy()

  def change_d_spacing(self, action, window):
    '''
      A dialog to change the d-spacing of the plots to calculate reciprocal lattice units.
    '''
    print 'dns.py: Entry change_d_spacing'

    #+++++ Create a dialog window for ooff input +++++

    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        elif id == idButApply:
           ret = 2
        ds_dialog.EndModal( ret )

    #+++++ Create a dialog window for ooff input +++++
    ds_dialog = wx.Dialog(window, wx.ID_ANY, title='Set d-spacing for x and y directions:', size=(500,200),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    ds_dialog.SetSizer( vbox )

    table   = wx.GridBagSizer()

    label = wx.StaticText(ds_dialog, label='Direction')
    table.Add( label, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    label = wx.StaticText(ds_dialog, label='label', style=wx.ALIGN_CENTRE)
    table.Add( label, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    label = wx.StaticText(ds_dialog, label='d-spacing', style=wx.ALIGN_CENTRE)
    table.Add( label, wx.GBPosition(0,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    label = wx.StaticText(ds_dialog, label='x', style=wx.ALIGN_CENTRE)
    table.Add( label, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    label = wx.StaticText(ds_dialog, label='y', style=wx.ALIGN_CENTRE)
    table.Add( label, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    input_filed_nx  = wx.TextCtrl( ds_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    input_filed_nx.SetMaxLength(20)
    input_filed_nx.SetValue(self.D_NAME_X)
    input_filed_nx.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda *ignore: ds_dialog.EndModal(2) )  
    table.Add( input_filed_nx, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND )

    input_filed_ny  = wx.TextCtrl( ds_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    input_filed_ny.SetMaxLength(20)
    input_filed_ny.SetValue(self.D_NAME_Y)
    input_filed_ny.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda *ignore: ds_dialog.EndModal(2) )  
    table.Add( input_filed_ny, wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND )

    input_filed_dx  = wx.TextCtrl( ds_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    input_filed_dx.SetMaxLength(20)
    print 'self.D_SPACING_X = ',self.D_SPACING_X,', ',type(self.D_SPACING_X)
    input_filed_dx.SetValue(str(self.D_SPACING_X))
    input_filed_dx.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda *ignore: ds_dialog.EndModal(2) )  
    table.Add( input_filed_dx, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND )

    input_filed_dy  = wx.TextCtrl( ds_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    input_filed_dy.SetMaxLength(20)
    input_filed_dy.SetValue(str(self.D_SPACING_Y))
    input_filed_dy.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda *ignore: ds_dialog.EndModal(2) )  
    table.Add( input_filed_dy, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND )

    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butOk      = wx.Button( ds_dialog, wx.ID_ANY, label='OK' )
    butApply   = wx.Button( ds_dialog, wx.ID_ANY, label='Apply' )
    butCancel  = wx.Button( ds_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    idButApply = butApply.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butApply, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butApply.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)

    vbox.Add( table, 0, wx.CENTER|wx.EXPAND, 10)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)

    #----- Create a dialog window for d-spacing input -----
    # wait for user response
    ds_dialog.Fit()
    result = ds_dialog.ShowModal()
    print 'result = ', result

    while result > 0:

      try:
        # response is Apply
        self.D_NAME_X    = input_filed_nx.GetValue()
        self.D_NAME_Y    = input_filed_ny.GetValue()
        self.D_SPACING_X = float(input_filed_dx.GetValue())
        self.D_SPACING_Y = float(input_filed_dy.GetValue())
        self.set_transformations()
        self.active_file_data[window.index_mess].calculate_wavevectors()
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
        window.replot()
        if result==1:
          break
        result = ds_dialog.ShowModal()

      except ValueError:
        result = ds_dialog.ShowModal()
        if result==1:
          break

    ds_dialog.Destroy()

  def change_increment(self, action, window):
    '''
      Change the increments between files of the same polarization
      chanel. New maps are created after this change.
    '''
    print 'dns.py: Entry change_increment'
    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        inc_dialog.EndModal( ret )

    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for increment input +++++
    inc_dialog = wx.Dialog(window, wx.ID_ANY, title='Change increment for same polarization:', size=(100,50),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    inc_dialog.SetSizer( vbox )

    butBox    = wx.BoxSizer( wx.HORIZONTAL )
    butOk     = wx.Button( inc_dialog, wx.ID_ANY, label='OK' )
    butCancel = wx.Button( inc_dialog, wx.ID_ANY, label='Cancel' )
    idButOk   = butOk.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)


    input_filed = wx.TextCtrl(inc_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER  )
    input_filed.SetMaxLength(20)
    input_filed.SetValue(str(self.file_options[self.active_file_name][2]))

    input_filed.Bind(event=wx.EVT_TEXT_ENTER, handler = lambda *ignore: inc_dialog.EndModal(1) )

    vbox.Add(input_filed, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)
    #----- Create a dialog window for increment input -----

    inc_dialog.Fit()
    result = inc_dialog.ShowModal()
    print 'result = ', result
    if result==1:
      # Answer is OK
      try:
        inc = int(input_filed.GetValue())
        self.file_options[self.active_file_name][2]=inc
        self.create_maps(self.active_file_name)
        object=self.file_data[self.active_file_name]
        window.change_active_file_object((self.active_file_name, object))
      except ValueError:
        pass
    inc_dialog.Destroy()
  


  def change_multiple_scattering_propability(self, action, window):
    '''
      Change the value for multiple scattering propability and 
      reacalculate the corrected dataset.
    '''
    print 'dns.py: Entry change_multiple_scattering_propability'
    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        elif id == idButApply:
           ret = 2
        inc_dialog.EndModal( ret )

    print 'dns.py: entry change_multiple_scattering_propability'
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for increment input +++++

    inc_dialog = wx.Dialog(window, wx.ID_ANY, title='Change scattering propability for the flipping-ratio correction:',
                              size=(250,100),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    inc_dialog.SetSizer( vbox )

    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butOk      = wx.Button( inc_dialog, wx.ID_ANY, label='OK' )
    butApply   = wx.Button( inc_dialog, wx.ID_ANY, label='Apply' )
    butCancel  = wx.Button( inc_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    idButApply = butApply.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butApply, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butApply.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)

    input_filed = wx.TextCtrl(inc_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER  )
    input_filed.SetMaxLength(20)
    input_filed.SetValue( str(self.SCATTERING_PROPABILITY) )

    input_filed.Bind(event=wx.EVT_TEXT_ENTER, handler = lambda *ignore: inc_dialog.EndModal(1) )

    vbox.Add(input_filed, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)
 

    #----- Create a dialog window for increment input -----
    inc_dialog.Fit()
    result = inc_dialog.ShowModal()
    print 'result = ', result
    while result>0:
      # Answer is OK or Apply
      try:
        new_sp=float(input_filed.GetValue())
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
        result=inc_dialog.ShowModal()

    inc_dialog.Destroy()
  
  def separate_scattering_preset(self, action, window):
    '''
      A selection dialog to choose a preset for separate_scattering.
    '''
    print 'dns.py: Entry separate_scattering_preset'
    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        preset_dialog.EndModal( ret )



    preset_dialog = wx.Dialog(window, wx.ID_ANY, title='Add polarization:', size=(500,200),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    preset_dialog.SetSizer( vbox )

    preset_box = wx.ComboBox( preset_dialog )
    keys=sorted(config.dns.SEPERATION_PRESETS.keys())
    print 'dns.py: keys =', keys
    preset_box.Append(keys[0])
    for key in keys[1:]:
      preset_box.Append(key)
    vbox.Add( preset_box, 0, wx.ALL|wx.CENTER|wx.EXPAND, 3 )

    butBox    = wx.BoxSizer( wx.HORIZONTAL )
    butOk     = wx.Button( preset_dialog, wx.ID_ANY, label='OK' )
    butCancel = wx.Button( preset_dialog, wx.ID_ANY, label='Cancel' )
    idButOk   = butOk.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)

    preset_dialog.Fit()
    result = preset_dialog.ShowModal()
    print 'result = ',result
    key=keys[preset_box.GetCurrentSelection()]
    preset_dialog.Destroy()

    if result==1:
      self.seperate_scattering(action, window, config.dns.SEPERATION_PRESETS[key])
  
  def seperate_scattering(self, action, window, preset=None):
    '''
      Add or substract measured polarizations from each other
      to calculate e.g. coherent magnetic scattering.
    '''
    print 'dns.py: Entry seperate_scattering'

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
      print 'dns.py:   Entry add_object: len combine_list = ', len(combine_list)
      def butClicked( event ):
          id = event.GetId()
          ret = 0
          if id == idButOk:
            ret = 1
          add_dialog.EndModal( ret )

      add_dialog = wx.Dialog(window, wx.ID_ANY, title='Add polarization:', size=(500,100),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
      vbox = wx.BoxSizer( wx.VERTICAL )
      add_dialog.SetSizer( vbox )

      align_table = wx.BoxSizer( wx.HORIZONTAL )
      label = wx.StaticText( add_dialog, wx.ID_ANY, 'sign:' )
      align_table.Add( label, 0, wx.ALL|wx.CENTER, 3 )
      sign = wx.TextCtrl( add_dialog, wx.ID_ANY )
      sign.SetValue('+')
      align_table.Add( sign, 0, wx.ALL|wx.CENTER, 3 )
      multiplier = wx.TextCtrl( add_dialog, wx.ID_ANY )
      multiplier.SetValue('1')
      align_table.Add( multiplier, 0, wx.ALL|wx.CENTER, 3 )
      object_box = wx.ComboBox( add_dialog )
      object_box.Append('0-('+polarization_list[0][0].short_info+')')
      for i, object in enumerate(polarization_list[1:]):
        object_box.Append(str(i+1)+'-('+object[0].short_info+','+object[1]+')')
      object_box.SetSelection(0)
      align_table.Add( object_box, 0, wx.ALL|wx.EXPAND, 3)
      vbox.Add( align_table, 0, wx.CENTER|wx.EXPAND, 10 )

      butBox    = wx.BoxSizer( wx.HORIZONTAL )
      butOk     = wx.Button( add_dialog, wx.ID_ANY, label='OK' )
      butCancel = wx.Button( add_dialog, wx.ID_ANY, label='Cancel' )
      idButOk   = butOk.GetId()
      butBox.Add( butOk, wx.CENTER|wx.EXPAND )
      butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
      butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
      butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)
      vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)

      result = add_dialog.ShowModal()
      print 'add_dialog: result = ', result
      if result==1:
        if sign.GetValue() in ['+','-', '*', '/']:
          sign = sign.GetValue()
        else:
          sign='+'
        print 'object_box.GetSelection() = ',object_box.GetSelection()
        print 'object_box.GetValue()     = ',object_box.GetValue()
        combine_list.append( (object_box.GetSelection(), sign, float(multiplier.GetValue())) )
        print 'len combine_list = ', len(combine_list)
        labelfunc =  wx.StaticText(combine_dialog, wx.ID_ANY, sign+multiplier.GetValue()+'*{'+object_box.GetValue()+'}') 
        function_table.Add(labelfunc, wx.GBPosition(len(combine_list)-1, 0), flag=wx.CENTER|wx.EXPAND )

      add_dialog.Destroy()

    def butClicked( event ):
          id = event.GetId()
          ret = 0
          if id == idButOk:
            ret = 1
          elif id == idButAdd:
            ret = 2
          combine_dialog.EndModal( ret )

    combine_dialog = wx.Dialog(window, wx.ID_ANY, title='Combination of polarizations:', size=(500,100),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    combine_dialog.SetSizer( vbox )

    table = wx.BoxSizer( wx.HORIZONTAL )
    input_filed = wx.TextCtrl( combine_dialog, wx.ID_ANY )
    input_filed.SetMaxLength(20)
    input_filed.SetValue( 'Result')
    table.Add( input_filed, 0, wx.ALL|wx.EXPAND, 3)
    label = wx.StaticText( combine_dialog, wx.ID_ANY, label=' = ' )
    table.Add( label, 0, wx.ALL|wx.EXPAND, 3)
    
    function_table = wx.GridBagSizer(  )

    table.Add( function_table, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add( table, 0, wx.ALL|wx.EXPAND,3 )


    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butAdd     = wx.Button( combine_dialog, wx.ID_ANY, label='Add' )
    butOk      = wx.Button( combine_dialog, wx.ID_ANY, label='OK' )
    butCancel  = wx.Button( combine_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    idButAdd   = butAdd.GetId()
    butBox.Add( butAdd, wx.CENTER|wx.EXPAND )
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butAdd.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)


    # if a preset is used create the right list and show the function
    if preset is None:
      add_object()
    else:
      combine_list=preset
      for i, item in enumerate(combine_list):
        try:
            labelfunc = wx.StaticText( combine_dialog, wx.ID_ANY, 
                              label=item[1]+str(item[2])+'*{'+str(i)+'-('+polarization_list[item[0]][0].short_info+')}') 
            function_table.Add(labelfunc, wx.GBPosition(i,0) )
        except IndexError:
          combine_dialog.Destroy()
          return None

    combine_dialog.Fit()
    result = combine_dialog.ShowModal()
    print 'result= ',result
    while result>1:
      add_object()
      combine_dialog.Fit()
      result = combine_dialog.ShowModal()
    if result==1:
      self.calculate_combination(combine_list, polarization_list, input_filed.GetValue())
    combine_dialog.Destroy()
  
  def calculate_combination(self, combine_list, polarization_list, title):
    '''
      Calculate a combination of polarization directions as
      set in the combine_list.
      
      @param combine_layers List of how the chanels should be combined
      @param polarization_list The chanels which will be combined
      @param title Name of the new created chanel
    '''
    print 'dns.py: Entry calculate_combination'

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
        message = wx.MessageDialog(self, 
                                  'You can only combine polarizations with the same number of measured points!',
                                  'Information',
                                  wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP)
        message.ShowModal()
        message.Destroy()
        return None

    result.short_info=title
    result.number=str(len(polarization_list))
    self.active_file_data.append(result)

  def reload_active_measurement(self, action, window):
    '''
      Reload the measurement active in the GUI.
    '''
    print 'dns.py: Entry reload_active_measurement'

    self.read_files(self.active_file_name.rsplit('|raw_data')[0])
    window.change_active_file_object((self.active_file_name, self.file_data[self.active_file_name]))


if __name__ == '__main__':
   print 'name ist main'
   app   = wx.PySimpleApp()
   frame = wx.Frame(None)
   dd    = DNSGUI()
   mb    = wx.MenuBar()
   frame.SetMenuBar( mb )
   menulist = dd.create_menu(frame)

   print 'menulist = ', menulist 
   for j, item in enumerate(menulist):
          print 'j = ',j,' append item = ', item
          mb.Append(item[0], item[1] )

   frame.Show(True)
   app.MainLoop()