# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in treff session.
'''
import sys
import  math, os
import wx
# import parameter class for fits
if __name__ == '__main__':
 import sys
 sys.path.append('..')
else:
 import config.dns

from sessions.reflectometer_fit.parameters import FitParameters, LayerParam, MultilayerParam
import refl_fit_functions
import read_data.treff
import config.treff

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class TreffGUI:
  '''
    GTK2 functions for the treff sessions.
  '''
  def __init__(self):
    '''
      class constructor addition
    '''
    self.fit_object=TreffFitParameters() # create a new empty TreffFitParameters object

  def create_menu(self, home):
    '''
      create a specifig menu for the TREFF session
    '''
    print 'treff.py: Entry create_menu'
    menu_list = []

    title = 'TREFF'
    menuTreff = wx.Menu()

    id = menuTreff.Append( wx.ID_ANY, 'Fit ...',
                           'Fit ...').GetId()
    act = 'TreffFit'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.fit_window: function(arg1, arg2) )

    id = menuTreff.Append( wx.ID_ANY, 'Select polarization channels ...',
                           'Select polarization channels ...').GetId()
    act = 'TreffSelectPol'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.select_fittable_sequences: function(arg1, arg2) )

    id = menuTreff.Append( wx.ID_ANY, 'Import Fit ...',
                           'Import Fit ...').GetId()
    act = 'TreffImportFit'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.import_fit_dialog: function(arg1, arg2) )

    id = menuTreff.Append( wx.ID_ANY, 'Export Fit ...',
                           'Export Fit ...').GetId()
    act = 'TreffExportFit'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.export_fit_dialog: function(arg1, arg2) )

    id = menuTreff.Append( wx.ID_ANY, 'Extract specular reflectivity ...',
                           'Extract specular reflectivity ...').GetId()
    act = 'TreffSpecRef'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.extract_specular_reflectivity: function(arg1, arg2) )

    menu = [menuTreff, title]
    print 'menu = ', menu
    menu_list.append(menu) 
    return menu_list



  def extract_specular_reflectivity(self, action, window):
    '''
      Open a dialog for the extraction of the specular line from a 3d image.
      The user can select the width for the cross-section,
      after this the data is extracted and appendet to the fileobject.
      The true specular reflectivity is calculated using two parallel
      lines next to the specular line.
    '''
    print 'treff.py: entry extract_specular_reflectivity'
    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        cs_dialog.EndModal( ret )


    data=window.measurement[window.index_mess]

    cs_dialog = wx.Dialog(window, wx.ID_ANY, title='Create a cross-section:', size=(400,200),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    cs_dialog.SetSizer( vbox )

    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butOk      = wx.Button( cs_dialog, wx.ID_ANY, label='OK' )
    butCancel  = wx.Button( cs_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)

    table = wx.GridBagSizer()

    label      = wx.StaticText( cs_dialog, label='Width:', style=wx.ALIGN_CENTRE )
    line_width = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    line_width.SetMaxLength(5)
    line_width.SetValue('0.08')
    table.Add( label,      wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    table.Add( line_width, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    label   = wx.StaticText( cs_dialog, label='Stepwidth:', style=wx.ALIGN_CENTRE )
    binning = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    binning.SetMaxLength(5)
    binning.SetValue('0.08')
    table.Add( label,   wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    table.Add( binning, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    weight = wx.CheckBox(cs_dialog, wx.ID_ANY, 'Gauss weighting, Sigma:')
    weight.SetValue( True )
    sigma = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    sigma.SetMaxLength(5)
    sigma.SetValue('0.04')
    table.Add( weight, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    table.Add( sigma,  wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    ext_all = wx.CheckBox(cs_dialog, wx.ID_ANY, 'Extract for all maps')
    ext_all.SetValue( True )
    table.Add( ext_all, wx.GBPosition(3,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    label    = wx.StaticText( cs_dialog, label='0-position offset:', style=wx.ALIGN_CENTRE )
    offset_x = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    offset_y = wx.TextCtrl( cs_dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    offset_x.SetMaxLength(5)
    offset_y.SetMaxLength(5)
    offset_x.SetValue('0.0')
    offset_y.SetValue('0.0')
    table.Add( label,     wx.GBPosition(4,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    table.Add( offset_x, wx.GBPosition(4,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    table.Add( offset_y, wx.GBPosition(4,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )


    line_width.Bind(event=wx.EVT_TEXT_ENTER,  handler=lambda *ign: cs_dialog.EndModal(1))
    binning.Bind(   event=wx.EVT_TEXT_ENTER,  handler=lambda *ign: cs_dialog.EndModal(1))
    sigma.Bind(     event=wx.EVT_TEXT_ENTER,  handler=lambda *ign: cs_dialog.EndModal(1))
    offset_x.Bind(  event=wx.EVT_TEXT_ENTER,  handler=lambda *ign: cs_dialog.EndModal(1))
    offset_y.Bind(  event=wx.EVT_TEXT_ENTER,  handler=lambda *ign: cs_dialog.EndModal(1))
 

    vbox.Add( table,  0, wx.CENTER|wx.EXPAND, 10)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)


    result = cs_dialog.ShowModal()
    print 'result = ', result
    if result==1:
      # If not canceled the data is extracted
      if not ext_all.IsChecked():
        if data.zdata==-1:
          cs_dialog.Destroy()
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
              float(line_width.GetValue()), 
              weight.IsChecked(), 
              float(sigma.GetValue()), 
              float(binning.GetValue()), 
              (float(offset_x.GetValue()), float(offset_y.GetValue()))
              )
      except ValueError:
        gotit=False
      gotit=True
      for i in extract_indices:
        window.index_mess=i
        gotit=gotit and window.file_actions.activate_action(*args)        
      if not gotit:
 
         message = wx.MessageDialog(self, 
                                'Wrong parameter type.',
                                'Wrong parameter type',
                                wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP )
         message.ShowModal()
         message.Destroy()

    else:
      gotit=False
    cs_dialog.Destroy()
    if gotit:
      window.rebuild_menus()
      window.replot()      
    return gotit

  #++++ functions for fitting with fortran program by E. Kentzinger ++++
  
  from refl_fit_functions import \
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


  def select_fittable_sequences(self, action, window):
    '''
      A dialog to select the sequences for the 4 polarization chanels.
      Not selected items will be ignored during fit process.
    '''
    print 'treff.py Entry select_fittable_sequences'


    def butClicked( event ):
        id = event.GetId()
        ret = 0
        if id == idButOk:
           ret = 1
        selection_dialog.EndModal( ret )



    selection_dialog = wx.Dialog(window, wx.ID_ANY, title='Select polarization channels ...', size=(350,180),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL )
    selection_dialog.SetSizer( vbox )

    butBox     = wx.BoxSizer( wx.HORIZONTAL )
    butOk      = wx.Button( selection_dialog, wx.ID_ANY, label='OK' )
    butCancel  = wx.Button( selection_dialog, wx.ID_ANY, label='Cancel' )
    idButOk    = butOk.GetId()
    butBox.Add( butOk, wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind(event=wx.EVT_BUTTON, handler=butClicked)
    butCancel.Bind(event=wx.EVT_BUTTON, handler=butClicked)

    align_table = wx.GridBagSizer()

    object_box_1 = wx.ComboBox(selection_dialog)
    object_box_2 = wx.ComboBox(selection_dialog)
    object_box_3 = wx.ComboBox(selection_dialog)
    object_box_4 = wx.ComboBox(selection_dialog)
    object_box_1.Append( 'None' )
    object_box_2.Append( 'None' )
    object_box_3.Append( 'None' )
    object_box_4.Append( 'None' )
    align_table.Add( object_box_1, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    align_table.Add( object_box_2, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    align_table.Add( object_box_3, wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    align_table.Add( object_box_4, wx.GBPosition(3,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

    for i, object in enumerate(self.active_file_data):
      object_box_1.Append(str(i)+'-('+object.short_info+')')
      object_box_2.Append(str(i)+'-('+object.short_info+')')
      object_box_3.Append(str(i)+'-('+object.short_info+')')
      object_box_4.Append(str(i)+'-('+object.short_info+')')

    text_filed   = wx.StaticText( selection_dialog, label='Up-Up-Channel:', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    text_filed   = wx.StaticText( selection_dialog, label='Down-Down-Channel:', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    text_filed   = wx.StaticText( selection_dialog, label='Up-Down-Channel:', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
    text_filed   = wx.StaticText( selection_dialog, label='Down-Up-Channel:', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(3,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )


    vbox.Add( align_table,  0, wx.CENTER|wx.EXPAND, 10)
    vbox.Add( butBox, 0, wx.CENTER|wx.EXPAND, 10)

    if any(self.fit_datasets):
      indices=[]
      for item in self.fit_datasets:
        if item:
          indices.append(self.active_file_data.index(item)+1)
        else:
          indices.append(0)
      object_box_1.SetSelection(indices[0])
      object_box_2.SetSelection(indices[1])
      object_box_3.SetSelection(indices[2])
      object_box_4.SetSelection(indices[3])
    else:
      if len(self.active_file_data)==8:
        object_box_1.SetSelection(5)
        object_box_2.SetSelection(6)
        object_box_3.SetSelection(7)
        object_box_4.SetSelection(8)
      else:
        object_box_1.SetSelection(0)
        object_box_2.SetSelection(0)
        object_box_3.SetSelection(0)
        object_box_4.SetSelection(0)

    if selection_dialog.ShowModal() == 1:
      print 'result ist 1'
      set_list=[None] + self.active_file_data
      self.fit_datasets=[set_list[object_box_1.GetSelection()], 
                        set_list[object_box_2.GetSelection()], 
                        set_list[object_box_3.GetSelection()], 
                        set_list[object_box_4.GetSelection()]]
      for object in self.fit_datasets:
        if object:
          object.logy=True
      selection_dialog.Destroy()
      return True
    else:
      selection_dialog.Destroy()
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


    dialog = wx.Dialog(window, wx.ID_ANY, title='Fit parameters:', size=(size[0], 1.5*size[1]),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)

    if position!=None:
      dialog.Move( wx.Point(position[0], position[1]) )


    global_vbox = wx.BoxSizer( wx.VERTICAL )
    dialog.SetSizer(global_vbox)

    vbox = wx.BoxSizer( wx.VERTICAL )
    sw = wx.ScrolledWindow( dialog, wx.ID_ANY, style=wx.HSCROLL|wx.VSCROLL )
    sw.SetSizer( vbox )
    sw.SetScrollRate(10, 10 )

    #layer parameters
    for layer in self.fit_object.layers:
      layer_options[layer_index] =self.create_layer_options(layer, layer_index, layer_params, dialog, window, sw)
      layer_index+=1


    s_box = wx.StaticBox(sw, label='Instrumental parameters', size=(300,130) )
    s_boxsizer    = wx.StaticBoxSizer(s_box, wx.VERTICAL)


    # top parameter
    align_table = wx.GridBagSizer()                                                 # spacing 5
    s_boxsizer.Add(align_table)

    text_filed   = wx.StaticText( sw, label='1st slit: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    first_slit = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    first_slit.SetMaxLength(5)
    first_slit.SetValue(str(self.fit_object.slits[0]))
    align_table.Add( first_slit, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    first_slit.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed   = wx.StaticText( sw, label='2st slit: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    second_slit = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    second_slit.SetMaxLength(5)
    second_slit.SetValue(str(self.fit_object.slits[1]))
    align_table.Add( second_slit, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    second_slit.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed   = wx.StaticText( sw, label='Smpl length: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    length = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    length.SetMaxLength(10)
    length.SetValue(str(self.fit_object.sample_length))
    align_table.Add( length, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    length.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )
 
    text_filed   = wx.StaticText( sw, label='Dist. to 1st: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    first_distance = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    first_distance.SetMaxLength(10)
    first_distance.SetValue(str(self.fit_object.distances[0]))
    align_table.Add( first_distance, wx.GBPosition(1,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    first_distance.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed   = wx.StaticText( sw, label='Dist. to 2nd: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(0,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    second_distance = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    second_distance.SetMaxLength(10)
    second_distance.SetValue(str(self.fit_object.distances[1]))
    align_table.Add( second_distance, wx.GBPosition(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    second_distance.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    wavelength_table = wx.BoxSizer( wx.HORIZONTAL )

    text_filed = wx.StaticText( sw, label='Wavelength: ', style=wx.ALIGN_CENTRE )
    wavelength_table.Add(text_filed)
    wavelength = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    wavelength.SetMaxLength(5)
    wavelength.SetMaxSize( wx.Size(50,25) )
    wavelength.SetValue(str(self.fit_object.wavelength[0]))
    wavelength_table.Add( wavelength )

    # activating the input will apply the settings, too
    wavelength.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed = wx.StaticText( sw, label='+/- ', style=wx.ALIGN_CENTRE )
    text_filed.SetMaxSize( wx.Size(30,25) )
    wavelength_table.Add(text_filed)
    delta_wavelength = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    delta_wavelength.SetMaxLength(5)
    delta_wavelength.SetMaxSize( wx.Size(50,25) )
    delta_wavelength.SetValue(str(self.fit_object.wavelength[1]))
    wavelength_table.Add( delta_wavelength )

    # activating the input will apply the settings, too
    delta_wavelength.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    align_table.Add( wavelength_table, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, span = wx.GBSpan(1,2), border=5 )

    text_filed = wx.StaticText( sw, label='x-region', style=wx.ALIGN_CENTRE )
    align_table.Add(text_filed, wx.GBPosition(2,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.CENTER|wx.ALL|wx.EXPAND, border=3)

    x_from = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    x_from.SetMaxLength(10)
    x_from.SetValue( str(self.x_from)  )
    align_table.Add( x_from, wx.GBPosition(2,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    x_from.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    x_to = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    x_to.SetMaxLength(10)
    x_to.SetValue( str(self.x_to) )
    align_table.Add( x_to, wx.GBPosition(2,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    x_to.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )
   

    vbox.Add(s_boxsizer, 0, wx.ALL|wx.EXPAND, 10)



    
    #create table for widgets
    substrat_options = self.create_layer_options(self.fit_object.substrate, 0, fit_params, dialog, window, sw, substrate=True)
    # layer parameters in table
    table = wx.BoxSizer( wx.VERTICAL )                                                       # spacing 10


    for i in range(layer_index):
        table.Add(layer_options[i], flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5)
 
#      s_box = wx.StaticBox(sw, label='multilayer', size=(300,130) )
#      s_boxsizer = wx.StaticBoxSizer(s_box, wx.VERTICAL)
#      # layer parameters in table
#      for i in range(layer_index):
#        s_boxsizer.Add(layer_options[i], flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5)
#        vbox.Add(s_boxsizer, 0, wx.ALL|wx.EXPAND, 5 )


    table.Add(substrat_options, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    vbox.Add(table, 0, wx.ALL|wx.EXPAND, 5 )


    
    #bottom parameters
    s_box = wx.StaticBox(sw, label='Additional global parameters', size=(300,320) )
    s_boxsizer    = wx.StaticBoxSizer(s_box, wx.VERTICAL)
    
    align_table = wx.GridBagSizer()
    s_boxsizer.Add(align_table)
#
#    der folgende text ist jetzt Label der StaticBox
                                                 # spacing 10
#    text_filed = wx.StaticText( dialog, label='Additional global parameters', style=wx.ALIGN_CENTRE )
#    align_table.Add(text_filed, wx.GBPosition(0,0), flag=wx.CENTER|wx.ALL|wx.EXPAND, span=wx.GBSpan(1,4), border=3)

    background_x = wx.CheckBox( sw, wx.ID_ANY, 'Background:')
    align_table.Add( background_x, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    background_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='background',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    background = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    background.SetMaxLength(10)
    background.SetValue( str(self.fit_object.background) )
    align_table.Add( background, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    background.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )


    scaling_x = wx.CheckBox( sw, wx.ID_ANY, 'Scaling:')
    align_table.Add( scaling_x, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    scaling_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='background',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )
 
    scaling_factor = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    scaling_factor.SetMaxLength(10)
    scaling_factor.SetValue( str(self.fit_object.scaling_factor) )
    align_table.Add( scaling_factor, wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    scaling_factor.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed = wx.StaticText( sw, label='Efficiencies:', style=wx.ALIGN_CENTRE )
    align_table.Add(text_filed, wx.GBPosition(0,2), flag=wx.CENTER|wx.ALL|wx.EXPAND, span=wx.GBSpan(1,2), border=3)


    polarizer_efficiancy_x = wx.CheckBox( sw, wx.ID_ANY, 'Polarizer:')
    align_table.Add( polarizer_efficiancy_x, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    polarizer_efficiancy_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='polarizer_efficiancy',
                               func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )
    polarizer_efficiancy = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    polarizer_efficiancy.SetMaxLength(10)
    polarizer_efficiancy.SetValue( str(self.fit_object.polarization_parameters[0]) )
    align_table.Add( polarizer_efficiancy, wx.GBPosition(1,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    polarizer_efficiancy.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    analyzer_efficiancy_x = wx.CheckBox( sw, wx.ID_ANY, 'Analyzer:')
    align_table.Add( analyzer_efficiancy_x, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    analyzer_efficiancy_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='analyzer_efficiancy',
                               func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )
    analyzer_efficiancy = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    analyzer_efficiancy.SetMaxLength(10)
    analyzer_efficiancy.SetValue( str(self.fit_object.polarization_parameters[1]) )
    align_table.Add( analyzer_efficiancy, wx.GBPosition(2,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    analyzer_efficiancy.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    flipper0_efficiancy_x = wx.CheckBox( sw, wx.ID_ANY, '1st Flipper:')
    align_table.Add( flipper0_efficiancy_x, wx.GBPosition(3,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    flipper0_efficiancy_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='flipper0_efficiancy',
                               func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )
    flipper0_efficiancy = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    flipper0_efficiancy.SetMaxLength(10)
    flipper0_efficiancy.SetValue( str(self.fit_object.polarization_parameters[2]) )
    align_table.Add( flipper0_efficiancy, wx.GBPosition(3,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    flipper0_efficiancy.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    flipper1_efficiancy_x = wx.CheckBox( sw, wx.ID_ANY, '2nd Flipper:')
    align_table.Add( flipper1_efficiancy_x, wx.GBPosition(4,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    flipper1_efficiancy_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='flipper1_efficiancy',
                               func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )
    flipper1_efficiancy = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    flipper1_efficiancy.SetMaxLength(10)
    flipper1_efficiancy.SetValue( str(self.fit_object.polarization_parameters[2]) )
    align_table.Add( flipper1_efficiancy, wx.GBPosition(4,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    flipper1_efficiancy.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed =  wx.StaticText( sw, wx.ID_ANY, 'max. iterations:' )
    align_table.Add( text_filed, wx.GBPosition(3,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    max_iter   = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    max_iter.SetMaxLength(4)
    max_iter.SetValue(str(self.max_iter))
    align_table.Add( max_iter, wx.GBPosition(3,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    max_iter.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )
 
    # fit-settings

    fit_x = wx.CheckBox( sw, wx.ID_ANY, 'Fit selected')
    align_table.Add( fit_x, wx.GBPosition(4,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    fit_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='actually',
                               func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    text_filed =  wx.StaticText( sw, wx.ID_ANY, 'Alambda 1st:' )
    align_table.Add( text_filed, wx.GBPosition(5,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    alambda_first   = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    alambda_first.SetMaxLength(4)
    alambda_first.SetValue(str(self.fit_object.alambda_first))
    align_table.Add( alambda_first, wx.GBPosition(5,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    alambda_first.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )


    text_filed =  wx.StaticText( sw, wx.ID_ANY, 'nTest' )
    align_table.Add( text_filed, wx.GBPosition(6,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    ntest   = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    ntest.SetMaxLength(4)
    ntest.SetValue(str(self.fit_object.ntest))
    align_table.Add( ntest, wx.GBPosition(6,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    ntest.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    text_filed =  wx.StaticText( sw, wx.ID_ANY, 'max_hr' )
    align_table.Add( text_filed, wx.GBPosition(7,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    max_hr   = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    max_hr.SetMaxLength(4)
    max_hr.SetValue(str(self.max_hr))
    align_table.Add( max_hr, wx.GBPosition(7,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    max_hr.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    show_all_button = wx.CheckBox( sw, wx.ID_ANY, 'all channels')
    align_table.Add( show_all_button, wx.GBPosition(7,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    show_all_button.SetValue(self.fit_object.simulate_all_channels)

    move_channels_button = wx.CheckBox( sw, wx.ID_ANY, 'move channels in plot')
    align_table.Add( move_channels_button, wx.GBPosition(7,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    move_channels_button.SetValue(True)
  

#    frame = wx.Frame( dialog, wx.ID_ANY, style=wx.BORDER_RAISED )
#    sw_vbox.Add( frame, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )


 
    if self.fit_object_history!=[]:
      history_back = wx.Button(sw, wx.ID_ANY, label='Undo (%i)' % len(self.fit_object_history),style=wx.BU_EXACTFIT )
      history_back.Bind(event=EVT_BUTTON, handler=lambda evt, arg1=True, arg2=dialog, arg3=window, func=self.fit_history:
                                                  func( evt, ar1, arg2, arg3) )
      align_table.Add(history_back, wx.GBPosition(8,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    if self.fit_object_future!=[]:
      history_forward = wx.Button(sw, wx.ID_ANY, label='Redo (%i)' % len(self.fit_object_future), style=wx.BU_EXACTFIT)
      history_forward.Bind(event=EVT_BUTTON, handler=lambda evt, arg1=False, arg2=dialog, arg3=window, func=self.fit_history:
                                                  func( evt, ar1, arg2, arg3) )
      align_table.Addd(history_forward, wx.GBPosition(8,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    vbox.Add(s_boxsizer, 0, wx.ALL|wx.EXPAND, 10)

    global_vbox.Add(sw, 1, wx.EXPAND|wx.ALL, 10)


    #----------------- Adding input fields -----------------
    butBox         = wx.StaticBox(dialog, wx.ID_ANY, style=wx.BORDER_DOUBLE|wx.BORDER_RAISED)
    butBoxSizer    = wx.StaticBoxSizer(butBox, wx.HORIZONTAL)
    butCustom      = wx.Button(dialog, wx.ID_ANY, label='Custom Constraints' )            # 7
    butLayer       = wx.Button(dialog, wx.ID_ANY, label='New Layer' )                     # 3
    butMultiLayer  = wx.Button(dialog, wx.ID_ANY, label='New Multilayer' )                # 4
    butFit         = wx.Button(dialog, wx.ID_ANY, label='Fit/Simulate and Replot' )       # 5
    butBoxSizer.Add( butCustom,     1, wx.EXPAND|wx.ALL, 3)
    butBoxSizer.Add( butLayer,      1, wx.EXPAND|wx.ALL, 3)
    butBoxSizer.Add( butMultiLayer, 1, wx.EXPAND|wx.ALL, 3)
    butBoxSizer.Add( butFit,        1, wx.EXPAND|wx.ALL, 3)
    global_vbox.Add(butBoxSizer, 0, wx.EXPAND|wx.ALL, 10)
    butCustom.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=7, arg2=dialog, arg3=window,
                        arg4=[wavelength, background,[first_slit, second_slit], scaling_factor,
                             [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy],
                             alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )
    butLayer.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=3, arg2=dialog, arg3=window,
                        arg4=[wavelength, background,[first_slit, second_slit], scaling_factor,
                             [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy],
                             alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )
    butMultiLayer.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=4, arg2=dialog, arg3=window,
                        arg4=[wavelength, background,[first_slit, second_slit], scaling_factor,
                             [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy],
                             alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )

    butFit.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=5, arg2=dialog, arg3=window,
                        arg4=[wavelength, background,[first_slit, second_slit], scaling_factor,
                             [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy],
                             alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )
    
##    dialog.connect("response", self.dialog_response, dialog, window,
#                   [wavelength, background, 
#                   [first_slit, second_slit], 
#                   scaling_factor, 
#                   [polarizer_efficiancy, analyzer_efficiancy, flipper0_efficiancy, flipper1_efficiancy], 
#                   alambda_first, ntest, x_from, x_to, max_hr, move_channels_button, show_all_button],
#                   [layer_params, fit_params, max_iter])

    dialog.Show()
    window.open_windows.append(dialog)

    def myRemove(evt, arg1):
        print 'treff.py entry myRemove: arg1 = ', arg1 
        arg1.Destroy() 
        window.open_windows.remove(arg1)
        print 'window.open_windows = ', window.open_windows

    dialog.Bind(wx.EVT_CLOSE, lambda  evt, arg1=dialog, func=myRemove: func(evt, arg1))


  def stop_scroll_emission(self, SL_selector, action):
    '''Stop scrolling event when ontop of seleciton dialog.'''
    SL_selector.stop_emission('scroll-event')

  def create_layer_options(self, layer, layer_index, layer_params, dialog, window, home, substrate=False):
    '''
      Create dialog inputs for every layer.
      Checkboxes are connected to toggle_fit_option,
      entries get passed to dialog_get_params when dialog response is triggered
      and 'DEL' buttons are connected to delete_layer
    '''
    print 'treff.py Entry create_layer_options: layer.multilayer = ',layer.multilayer

    if not layer.multilayer:
      #++++++++++++++++++ singlelayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]=[]
      align_table = wx.GridBagSizer()

      # labels
      layer_title = wx.StaticText( home, wx.ID_ANY, style=wx.ALIGN_CENTRE )
      if not substrate:
        layer_title.SetLabel( str(layer_index + 1) + ' - ' + layer.name )
        align_table.Add(layer_title, wx.GBPosition(0,0), span=wx.GBSpan(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL,  border=5)
        thickness_x = wx.CheckBox(home, wx.ID_ANY, 'thickness')
        align_table.Add(thickness_x, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
        thickness_x.Bind(event=wx.EVT_CHECKBOX,
                         handler=lambda evt, arg1=layer_params[layer_index], arg2=0,
                         func=self.toggle_fit_option: func(evt, arg1, arg2) )
      else:
        layer_title.SetLabel('Substrate - ' + layer.name)
        align_table.Add(layer_title, wx.GBPosition(0, 0), flag=wx.CENTER|wx.EXPAND|wx.ALL, span=wx.GBSpan(1,4), border=5)
#        spacer = wx.StaticText( home, wx.ID_ANY )
#        spacer.SetLabel('  ')
#        align_table.Add(spacer, wx.GBPosition(0, 1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5)

      scatter_density_Nb_x = wx.CheckBox( home, wx.ID_ANY, label='Nb\'')
      align_table.Add(scatter_density_Nb_x, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      scatter_density_Nb_x.Bind( event=wx.EVT_CHECKBOX,
                                 handler=lambda evt, arg1=layer_params[layer_index], arg2=1,
                                 func=self.toggle_fit_option: func(evt, arg1,arg2) )
      scatter_density_Nb2_x = wx.CheckBox( home, wx.ID_ANY, label='Nb\'\'')
      align_table.Add(scatter_density_Nb2_x, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      scatter_density_Nb2_x.Bind( event=wx.EVT_CHECKBOX,
                                 handler=lambda evt, arg1=layer_params[layer_index], arg2=2,
                                 func=self.toggle_fit_option: func(evt, arg1,arg2) )
      scatter_density_Np_x = wx.CheckBox( home, wx.ID_ANY, label='Np')
      align_table.Add(scatter_density_Np_x, wx.GBPosition(1, 3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      scatter_density_Np_x.Bind( event=wx.EVT_CHECKBOX,
                                 handler=lambda evt, arg1=layer_params[layer_index], arg2=3,
                                 func=self.toggle_fit_option: func(evt, arg1, arg2) )

      theta_x = wx.CheckBox( home, wx.ID_ANY, label='theta')
      align_table.Add(theta_x, wx.GBPosition(3,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      theta_x.Bind( event=wx.EVT_CHECKBOX,
                    handler=lambda evt, arg1=layer_params[layer_index], arg2=4,
                    func=self.toggle_fit_option: func(evt, arg1, arg2) )
      phi_x = wx.CheckBox( home, wx.ID_ANY, label='phi')
      align_table.Add(phi_x, wx.GBPosition(3,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      phi_x.Bind( event=wx.EVT_CHECKBOX,
                    handler=lambda evt, arg1=layer_params[layer_index], arg2=5,
                    func=self.toggle_fit_option: func(evt, arg1, arg2) )
      roughness_x = wx.CheckBox( home, wx.ID_ANY, label='roughness')
      align_table.Add(roughness_x, wx.GBPosition(3,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      roughness_x.Bind( event=wx.EVT_CHECKBOX,
                    handler=lambda evt, arg1=layer_params[layer_index], arg2=6,
                    func=self.toggle_fit_option: func(evt, arg1, arg2) )


      # entries

#      thickness = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
#      thickness.SetMaxLength(10)
#      thickness.SetValue(str(layer.thickness))
#      thickness.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
#                      func=self.dialog_activate: func( evt, arg1)  )

      # activating the input will apply the settings, too
      if not substrate:
        thickness = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
        thickness.SetMaxLength(10)
        thickness.SetValue(str(layer.thickness))
        thickness.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                       func=self.dialog_activate: func( evt, arg1)  )
        align_table.Add(thickness, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
        delete = wx.Button( home, wx.ID_ANY, label='DEL' , style=wx.BU_EXACTFIT )
        delete.Bind( event=wx.EVT_BUTTON, 
                     handler=lambda evt, arg1=layer, arg2=dialog, arg3=window, 
                     func=self.delete_layer: func(evt, arg1, arg2, arg3) )
        align_table.Add(delete, wx.GBPosition(3,4), flag=wx.EXPAND|wx.ALL|wx.CENTER, border=3 )
        delete = wx.Button( home, wx.ID_ANY, label='UP', style=wx.BU_EXACTFIT )
        delete.Bind( event=wx.EVT_BUTTON,
                     handler=lambda evt, arg1=layer, arg2=dialog, arg3=window, 
                     func=self.up_layer: func(evt, arg1, arg2, arg3 ))
        align_table.Add(delete, wx.GBPosition(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 ) 

      scatter_density_Nb = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      scatter_density_Nb.SetMaxLength(10)
      scatter_density_Nb.SetValue(str(layer.scatter_density_Nb))
      # activating the input will apply the settings, too
      scatter_density_Nb.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(scatter_density_Nb, wx.GBPosition(2,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      scatter_density_Nb2 = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      scatter_density_Nb2.SetMaxLength(10)
      scatter_density_Nb2.SetValue(str(layer.scatter_density_Nb2))
      # activating the input will apply the settings, too
      scatter_density_Nb2.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(scatter_density_Nb2, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      scatter_density_Np = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      scatter_density_Np.SetMaxLength(10)
      scatter_density_Np.SetValue(str(layer.scatter_density_Np))
      # activating the input will apply the settings, too
      scatter_density_Np.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(scatter_density_Np, wx.GBPosition(2,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      # selection dialog for material
      SL_selector = wx.ComboBox(home, style=wx.CB_READONLY, size=wx.Size(75,30) )
      SL_selector.Append('SL')
      SL_selector.SetSelection(0)
      for i, SL in enumerate(sorted(self.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES.items())):
        SL_selector.Append(SL[0])
        if layer.scatter_density_Nb==SL[1][0] and layer.scatter_density_Nb2==SL[1][1] and layer.scatter_density_Np==SL[1][2]:
          SL_selector.SetSelection(i+1)
      SL_selector.Bind( event=wx.EVT_TEXT, handler=lambda evt, arg1=SL_selector, arg2=layer, arg3=scatter_density_Nb,
                                                               arg4=scatter_density_Nb2, arg5=scatter_density_Np,
                                                               arg6=layer_title, arg7=layer_index, arg8=substrate,
                         func=self.change_scattering_length: func(evt, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8) )
#      SL_selector.connect('scroll-event', self.stop_scroll_emission)

      layer.SL_selector = SL_selector
      align_table.Add(SL_selector, wx.GBPosition(2,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      theta = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      theta.SetMaxLength(12)
      theta.SetValue(str(layer.theta))
      theta.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(theta, wx.GBPosition(4,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      phi = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      phi.SetMaxLength(12)
      phi.SetValue(str(layer.phi))
      phi.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(phi, wx.GBPosition(4,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      roughness = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      roughness.SetMaxLength(12)
      roughness.SetValue(str(layer.roughness))
      roughness.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(roughness, wx.GBPosition(4,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

 

#########??????????????????????
      # when apply button is pressed or field gets activated, send data
#      dialog.connect('response', layer.dialog_get_params, thickness, scatter_density_Nb, scatter_density_Nb2, scatter_density_Np, theta, phi, roughness) # when apply button is pressed, send data
#########??????????????????????
    else:
      #++++++++++++++++++ multilayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]={}
      align_table = wx.GridBagSizer( )

      text_filed = wx.StaticText( home, wx.ID_ANY, label='Multilayer')
      align_table.Add(text_filed, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      text_filed =  wx.StaticText( home, wx.ID_ANY, label=str(layer_index + 1) + ' - ' + layer.name )
      align_table.Add( text_filed, wx.GBPosition(0,1), flag=wx.CENTER|wx.ALL|wx.EXPAND, border=3 )

      small_table = wx.BoxSizer( wx.HORIZONTAL)
      repititions = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      repititions.SetMaxLength(3)
      repititions.SetValue(str(layer.repititions))
      # activating the input will apply the settings, too
      repititions.Bind( event=wx.EVT_TEXT_ENTER, 
                        handler=lambda evt, arg1=dialog, func=self.dialog_activate: func(evt, arg1) )
      small_table.Add(repititions, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      add = wx.Button(home, wx.ID_ANY, label='Add Layer', style=wx.BU_EXACTFIT )
      add.Bind(event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window, 
               func=self.add_multilayer: func(evt, arg1, arg2, arg3) )
      small_table.Add(add, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      align_table.Add(small_table, wx.GBPosition(0,2), span=wx.GBSpan(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      small_table = wx.BoxSizer( wx.HORIZONTAL )
      # entry for a gradient in roughness
      text_filed = wx.StaticText(home, wx.ID_ANY )
      text_filed.SetLabel('Roughness Gradient:')
      small_table.Add(text_filed,  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      roughness_gradient = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      roughness_gradient.SetMaxLength(3)
      roughness_gradient.SetValue(str(layer.roughness_gradient))
      # activating the input will apply the settings, too
      roughness_gradient.Bind(event=wx.EVT_TEXT_ENTER,
                              handler=lambda evt, arg1=dialog, 
                              func=self.dialog_activate: func(evt, arg1) )
      small_table.Add(roughness_gradient,  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      delete = wx.Button(home, wx.ID_ANY, label='DEL', style=wx.BU_EXACTFIT)
      delete.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window,
                   func=self.delete_multilayer: func(evt, arg1, arg2, arg3) )
      small_table.Add(delete,  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      delete = wx.Button(home, wx.ID_ANY, label='UP', style=wx.BU_EXACTFIT)
      delete.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window,
                   func=self.up_layer: func(evt, arg1, arg2, arg3) )
      small_table.Add(delete, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )


######      dialog.connect('response', layer.dialog_get_params, repititions, roughness_gradient) # when apply button is pressed, send data
      align_table.Add(small_table, wx.GBPosition(0,4), span=wx.GBSpan(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      # sublayers are appended to the align_table via recursion
      for i, sub_layer in enumerate(layer.layers):
        print 'create subtable: i = ',i
        sub_table = self.create_layer_options(sub_layer, i, layer_params[layer_index], dialog, window, home)
        align_table.Add(sub_table, wx.GBPosition(i+1,1),  span=wx.GBSpan(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

#      frame = wx.Frame()
#      frame.set_shadow_type(gtk.SHADOW_IN)
#      frame.Add(align_table)
#      align_table=frame


    return align_table
  
  def change_scattering_length(self, action, SL_selector, layer, scatter_density_Nb, scatter_density_Nb2, scatter_density_Np, layer_title, layer_index, substrate):
    '''
      function to change a layers scattering length parameters
      when a material is selected
    '''
    print 'treff.py Entry change_scattering_length: layer_index = ',layer_index
    print 'treff.py Entry change_scattering_length: layer_title = ',layer_title
    name = layer.SL_selector.GetValue()
    print 'name = ',name
    try:
      SL=self.fit_object.NEUTRON_SCATTERING_LENGTH_DENSITIES[name]
      layer.name=name
      scatter_density_Nb.SetValue(str(SL[0]))
      scatter_density_Nb2.SetValue(str(SL[1]))
      scatter_density_Np.SetValue(str(SL[2]))
      if substrate:
        layer_title.SetLabel('Substrate - ' + layer.name)
      else:
        layer_title.SetLabel(str(layer_index + 1) + ' - ' + layer.name)
    except KeyError:
      scatter_density_Nb.SetValue("1")
      scatter_density_Nb2.SetValue("1")
      scatter_density_Np.SetValue("1")
  
  def dialog_response(self, action, response, dialog, window, parameters_list, fit_list):
    '''
      Handle fit dialog response.
    '''
    print 'treff.py: Entry dialog_response: response        = ',response
    print 'treff.py: Entry dialog_response: parrameter_list = ',parameters_list
    print 'parameters_list[10] = ',parameters_list[10]
    print 'parameters_list[11] = ',parameters_list[11]
    if response>=5:
      try:
        self.fit_object.wavelength[0]           = float(parameters_list[0].GetValue())
        self.fit_object.background              = float(parameters_list[1].GetValue())
        self.fit_object.slits                   = map(float, map(lambda item: item.GetValue(), parameters_list[2]))
        self.fit_object.scaling_factor          = float(parameters_list[3].GetValue())
        self.fit_object.polarization_parameters = map(float, map(lambda item: item.GetValue(), parameters_list[4]))
        self.fit_object.alambda_first           = float(parameters_list[5].GetValue())
        self.fit_object.ntest                   = int(parameters_list[6].GetValue())
        print 'response >=5: values ausgelesen'
      except ValueError:
        None
      try:
        max_hr_new=int(parameters_list[9].GetValue())
        if max_hr_new!=self.max_hr:
          self.max_hr=max_hr_new
          new_max_hr=True
        else:
          new_max_hr=False
      except ValueError:
        new_max_hr=False
      self.fit_object.simulate_all_channels=parameters_list[11].IsChecked()
      try:
        self.x_from=float(parameters_list[7].GetValue())
      except ValueError:
        self.x_from=None
      try:
        self.x_to=float(parameters_list[8].GetValue())
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
        self.max_iter=int(fit_list[2].GetValue())
      except ValueError:
        self.max_iter=50
      if fit_list[1]['actually'] and response==5:
        self.fit_object.fit=1
      if response==7:
        print 'response ist 7'
        self.user_constraint_dialog(dialog, window)
        return None

      self.dialog_fit(action, window, move_channels=parameters_list[10].IsChecked(), new_max_hr=new_max_hr)
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
      print 'response ist 3 --> new layer'
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
    print 'treff.py: Entry dialog_fit'
    names=config.treff.REF_FILE_ENDINGS
    output_names=config.treff.FIT_OUTPUT_FILES
    self.export_data_and_entfile(self.TEMP_DIR, 'fit_temp.ent')
    #open a background process for the fit function
    refl_fit_functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', new_max_hr)
    print "PNR program started."
    if self.fit_object.fit!=1 and any(self.fit_datasets): # if this is not a fit just wait till finished
      exec_time, stderr_value = refl_fit_functions.proc.communicate()
      print "PNR program finished in %.2g seconds." % float(exec_time.splitlines()[-1])
    else:
      self.open_status_dialog(window)
    first=True
    free_sims=[]
    for i, dataset in enumerate(self.fit_datasets):
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
      elif self.fit_object.simulate_all_channels:
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
    window.multiplot=[[(dataset, dataset.short_info) for dataset in self.fit_datasets if dataset]]
    window.multi_list.SetValue(' Multiplot List: \n' + '\n'.join(map(lambda item: item[1], window.multiplot[0])))
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
      elif not self.fit_object.simulate_all_channels and not i==0:
        data_lines.append(0)
      else:
        ref_file=open(os.path.join(folder, datafile_prefix+names[i]+'.ref'), 'w')
        ref_file.write('1 1 1\n150 1 1\n')
        ref_file.close()
        data_lines.append(2)
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
    def butClicked(event):
        id = event.GetId()
        print 'treff.py Entry butClicked: id = ', id
        ret = 0
        if id == idButOk:
           ret = 1
        elif id == idButCancel:
           ret = 2

        results.EndModal( ret )


    old_fit=self.fit_object

    results = wx.Dialog(dialog, wx.ID_ANY, title='Fit results:',  size=(500,450),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    vbox = wx.BoxSizer( wx.VERTICAL)
    results.SetSizer( vbox )

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

    text = wx.TextCtrl( results, wx.ID_ANY )
    text.SetValue( text )
    vbox.Add( text, 0, wx.EXPAND, 3 )
   
    butBox      = wx.BoxSizer( wx.HORIZONTAL )
    butOk       = wx.Button( results, wx.ID_ANY, label='OK' )  
    butCancel   = wx.Button( results, wx.ID_ANY, label='Cancel' )
    idButOk     = butOk.GetId()
    idButCancel = butCancel.GetId()
    butBox.Add( butOk,     wx.CENTER|wx.EXPAND )
    butBox.Add( butCancel, wx.CENTER|wx.EXPAND )
    butOk.Bind( event=wx.EVT_BUTTON, handler=butClicked )        # returns 1
    butCancel.Bind( event=wx.EVT_BUTTON, handler=butClicked )    # returns 2
    vbox.Add( butBox, 0, wx.EXPAND, 3 )

    #dialog.connect("response", self.result_window_response, dialog, window, new_fit)
    # connect dialog to main window
########## ??????????????  window.open_windows.append(results) ????????
########## ?????????????? remove(results) ???????????
    window.open_windows.append(dialog)
#    results.connect("destroy", lambda *w: window.open_windows.remove(dialog))
    results.Bind( event=wx.EVT_CLOSE, handler=lambda evt, arg1=results: window.open_windows.remove(evt, arg1) )

    response = results.ShowModal()

    self.result_window_response(response, dialog, window, new_fit)
    results.Destroy()

  def export_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter export to .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog = wx.FileDialog(None, message='Export to ...',
                                      style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT )

    filter = ''
    filter += 'Entry file (*.ent)|*.ent' 
    filter += '|All files |*.*' 
    file_dialog.SetWildcard( filter )
    print 'self.active_file_name = ',self.active_file_name 
    if sys.platform == 'darwin':
      file_dialog.SetPath(self.active_file_name+'.ent' )
    else:
     file_dialog.SetFilename(self.active_file_name+'.ent' )

##  fuer die naechsten n Zeilen muss noch eine Loesung gefunden werden ( SetExtraControlCreator ab 2.9)
##  Jetzt: Eigener Dialog mit checkBox
    hlp_dialog =  wx.Dialog(window, wx.ID_ANY, title='Combine', size=wx.Size(400,50),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
    hlp_vbox = wx.BoxSizer( wx.VERTICAL )
    hlp_dialog.SetSizer(hlp_vbox)

    use_multilayer = wx.CheckBox( hlp_dialog, wx.ID_ANY, label='Combine 1st multiplot (don\'t export every single layer)' )
    hlp_vbox.Add(use_multilayer)
    hlp_dialog.ShowModal()
##    use_multilayer.show()
##    file_dialog.vbox.pack_end(use_multilayer, expand=False)

    response = file_dialog.ShowModal()
    print 'treff.py: export_fit_dialog response file dialog = ', response
    if response == wx.ID_OK:
      file_name = file_dialog.GetFilename()
    elif response == wx.ID_CANCEL:
      file_dialog.Destroy()
      return False

    file_dialog.Destroy()
    #----------------File selection dialog-------------------#
    file_prefix=file_name.rsplit('.ent', 1)[0]
    print 'use_multilayer Checked = ', use_multilayer.IsChecked()
    self.export_data_and_entfile(os.path.dirname(file_prefix), 
                                 os.path.basename(file_prefix)+'.ent', 
                                 datafile_prefix=os.path.basename(file_prefix), 
                                 use_multilayer=use_multilayer.IsChecked(), use_roughness_gradient=False)
    return True
  
  def import_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter import from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog = wx.FileDialog(None, message='Open new entfile',
                                 style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST )
    filter = ''
    filter += 'Entry file (*.ent)|*.ent' 
    filter += '|All files |*.*' 
    file_dialog.SetWildcard( filter )

    # Add a check box for importing x-ray .ent files.
##  fuer die naechsten 5 Zeilen muss noch eine Loesung gefunden werden ( SetExtraControlCreator ab 2.9)
    x_ray_import = wx.CheckBox( window, wx.ID_ANY, label='Convert from x-ray to .ent file' )
##    align=gtk.Alignment(xalign=1.0, yalign=0.0, xscale=0.0, yscale=0.0)
##    align.add(x_ray_import)
##    align.show_all()
##    file_dialog.vbox.pack_end(align, expand=False, fill=True, padding=0)

    response = file_dialog.ShowModal()
    print 'treff.py: import_fit_dialog response file dialog = ', response
 
    if response == wx.ID_OK:
      file_name=file_dialog.GetFilename()
    elif response == wx.ID_CANCEL:
      file_dialog.Destroy()
      return False
    file_dialog.Destroy()
    #----------------File selection dialog-------------------#
    self.fit_object=TreffFitParameters()
    if x_ray_import.IsChecked():
      self.fit_object.read_params_from_X_file(file_name)
    else:
      self.fit_object.read_params_from_file(file_name)
    if not any(self.fit_datasets):
      if not self.select_fittable_sequences(action, window):
        return False
    self.dialog_fit(action, window)
    return True
  

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
  simulate_all_channels=False
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
    print 'treff.py: Entry __init__: parameters_list = ', parameters_list
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
      self.scatter_density_Nb  = float(scatter_density_Nb.GetValue())
      self.scatter_density_Nb2 = float(scatter_density_Nb2.GetValue())
      self.scatter_density_Np  = float(scatter_density_Np.GetValue())
      self.theta               = float(theta.GetValue())
      self.phi                 = float(phi.GetValue())
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





if __name__ == '__main__':
   print 'name ist main'
   app   = wx.PySimpleApp()
   frame = wx.Frame(None)
   dd    = TreffGUI()
   mb    = wx.MenuBar()
   frame.SetMenuBar( mb )
   menulist = dd.create_menu(frame)

   print 'menulist = ', menulist 
   for j, item in enumerate(menulist):
          print 'j = ',j,' append item = ', item
          mb.Append(item[0], item[1] )

   frame.Show(True)
   app.MainLoop()
