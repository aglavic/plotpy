# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in reflectometer session.
'''
import sys
import wx
import math, os

# import parameter class for fits
if __name__ == '__main__':
 import sys
 sys.path.append('..')
else:
 import config.dns

# import parameter class for fits
from sessions.reflectometer_fit.parameters import FitParameters, LayerParam, MultilayerParam
# naechste Zeile wie in treff.py
import refl_fit_functions

import sessions.reflectometer_fit as reflectometer_fit
import read_data.reflectometer

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7rc1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class ReflectometerGUI:
  '''
    GTK2 functions for the reflectometer sessions.
  '''
  
  def __init__(self):
    self.active_file_data.fit_object=RefFitParameters() # create a new empty RefFitParameters object

  
  def create_menu(self, home):
    '''
      create a specifig menu for the Reflectometer session
    '''

    print 'reflectometer.py: Entry create_menu'
    menu_list = []

    title = 'Reflectometer'
    menuReflectometer = wx.Menu()

    id = menuReflectometer.Append( wx.ID_ANY, 'Fit...',
                                   'Fit ...').GetId()
    act = 'ReflectometerFit'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.fit_window:
                       function(arg1, arg2) )

    id = menuReflectometer.Append( wx.ID_ANY, 'Export Fit Parameters...',
                                   'Export Fit Parameters ...').GetId()
    act = 'ReflectometerExport'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.export_fit_dialog:
                       function(arg1, arg2) )

    id = menuReflectometer.Append( wx.ID_ANY, 'Import Fit Parameters...',
                                   'Export Fit Parameters ...').GetId()
    act = 'ReflectometerImport'
    home.Bind( wx.EVT_MENU, id = id,
               handler=lambda arg1=act, arg2=home, function=self.import_fit_dialog:
                       function(arg1, arg2) )

    menu = [menuReflectometer, title]
    menu_list.append(menu)
    
    return menu_list


  
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

  def fit_window(self, action, window, position=None, size=wx.Size(600, 800) ):
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

    dialog = wx.Dialog(window, wx.ID_ANY, title='Fit parameters:', size=size,
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)

    if position!=None:
#      dialog.Move( wx.Point(position[0], position[1]) )
      dialog.Move( position )


    global_vbox = wx.BoxSizer( wx.VERTICAL )
    dialog.SetSizer(global_vbox)

    vbox = wx.BoxSizer( wx.VERTICAL )
    sw = wx.ScrolledWindow( dialog, wx.ID_ANY, style=wx.HSCROLL|wx.VSCROLL )
    sw.SetSizer( vbox )
    sw.SetScrollRate(10, 10 )

    #layer parameters
    for layer in self.active_file_data.fit_object.layers:
      layer_options[layer_index]=self.create_layer_options(layer, layer_index, layer_params, dialog, window, sw)
      layer_index+=1


    #create table for widgets

    s_box = wx.StaticBox(sw, label='Instrumental parameters' )
    s_boxsizer    = wx.StaticBoxSizer(s_box, wx.VERTICAL)

    # top parameter
    align_table = wx.BoxSizer( wx.HORIZONTAL )  

    text_filed   = wx.StaticText( sw, label='Beam energy: ', style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    energy = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    energy.SetMaxLength( 10 )
    energy.SetValue( str(self.active_file_data.fit_object.radiation[0]) )
    align_table.Add( energy, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    energy.Bind( event=wx.EVT_TEXT_ENTER,
                 handler=lambda evt, arg1=dialog, 
                 func=self.dialog_activate: func( evt, arg1 ) )


    text_filed = wx.StaticText( sw, wx.ID_ANY, label='x-region' )
    align_table.Add( text_filed, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    x_from = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    x_from.SetMaxLength(10)
    x_from.SetValue( str(self.x_from)  )
    align_table.Add( x_from, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    x_from.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    x_to = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    x_to.SetMaxLength(10)
    x_to.SetValue( str(self.x_to) )
    align_table.Add( x_to, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    # activating the input will apply the settings, too
    x_to.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )
 
    s_boxsizer.Add(align_table, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add(s_boxsizer, 0, wx.ALL|wx.EXPAND, 10)
    vbox.Layout()


    # layer parameters in table
    table = wx.BoxSizer( wx.VERTICAL ) 
 
    for i in range(layer_index):
        table.Add(layer_options[i], flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5)

    # substrate parameters
    substrat_options=self.create_layer_options(self.active_file_data.fit_object.substrate, 0, fit_params, dialog, window, sw, substrate=True)
    table.Add(substrat_options, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    vbox.Add(table, 0, wx.ALL|wx.EXPAND, 5 )

    #bottom parameters
    s_box = wx.StaticBox(sw, label='Additional global parameters')
    s_boxsizer    = wx.StaticBoxSizer(s_box, wx.VERTICAL)
    
    align_table = wx.GridBagSizer()
    s_boxsizer.Add(align_table)

    background_x = wx.CheckBox( sw, wx.ID_ANY, 'Background:')
    align_table.Add( background_x, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    background_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='background',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    background = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    background.SetMaxLength(10)
    background.SetValue( str(self.active_file_data.fit_object.background) )
    align_table.Add( background, wx.GBPosition(0,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    background.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    resolution_x = wx.CheckBox( sw, wx.ID_ANY, 'Resolution:')
    align_table.Add( resolution_x, wx.GBPosition(0,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    resolution_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='resolution',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    resolution = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    resolution.SetMaxLength(10)
    resolution.SetValue( str(self.active_file_data.fit_object.resolution) )
    align_table.Add( resolution, wx.GBPosition(0,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    resolution.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )


    scaling_x = wx.CheckBox( sw, wx.ID_ANY, 'Scaling:')
    align_table.Add( scaling_x, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    scaling_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='scaling',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    scaling_factor = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    scaling_factor.SetMaxLength(10)
    scaling_factor.SetValue( str(self.active_file_data.fit_object.scaling_factor) )
    align_table.Add( scaling_factor, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    scaling_factor.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )

    # activating the input will apply the settings, too
#    text_filed   = wx.StaticText( sw, label='Theta_max (\302\260): ', style=wx.ALIGN_CENTRE )
    text_filed   = wx.StaticText( sw, label=unicode('Theta_max (\302\260): ','utf-8'), style=wx.ALIGN_CENTRE )
    align_table.Add( text_filed, wx.GBPosition(1,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )

    theta_max = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    theta_max.SetMaxLength(10)
    theta_max.SetValue( str(self.active_file_data.fit_object.theta_max) )
    align_table.Add( theta_max, wx.GBPosition(1,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    theta_max.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )


    # fit-settings

    fit_x = wx.CheckBox( sw, wx.ID_ANY, 'Fit selected:')
    align_table.Add( fit_x, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    fit_x.Bind( event=wx.EVT_CHECKBOX, 
                       handler=lambda evt,arg1=fit_params,arg2='actually',func=self.toggle_fit_bool_option: func(evt, arg1, arg2) )

    max_iter = wx.TextCtrl( sw, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    max_iter.SetMaxLength(10)
    max_iter.SetValue( str(self.max_iter) )
    align_table.Add( max_iter, wx.GBPosition(2,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )
    max_iter.Bind(event=wx.EVT_TEXT_ENTER, 
                   handler=lambda evt, arg1=dialog, 
                   func=self.dialog_activate: func( evt, arg1 ) )
    text_filed = wx.StaticText(sw, wx.ID_ANY, label='max. iterations:')
    align_table.Add( text_filed, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=5 )



    if self.active_file_data.fit_object_history!=[]:
      history_back = wx.Button(sw, wx.ID_ANY,label='Undo (%i)' % len(self.active_file_data.fit_object_history), style=wx.BU_EXACTFIT)
      history_back.Bind(event=wx.EVT_BUTTON, handler=lambda evt,arg1=True, arg2=dialog, arg3=window,
                                             func=self.fit_history: func(evt, arg1, arg2, arg30 ) )
      align_table.Add(history_back, wx.GBPosition(6,2), wx.EXPAND, 3)
    if self.active_file_data.fit_object_future!=[]:
      history_forward = wx.Button(sw, wx.ID_ANY, label='Redo (%i)' % len(self.active_file_data.fit_object_future), style=wx.BU_EXACTFIT)
      history_forward.Bind(event=wx.EVT_BUTTON, handler=lambda evt, arg1=False, arg2=dialog, arg3=window,
                                                func=self.fit_history: func( evt, arg1, arg2, arg3) )
      align_table.Add(history_forward, wx.GBPosition(6,3), wx.EXPAND, 3 )

    vbox.Add(s_boxsizer, 0, wx.ALL|wx.EXPAND, 10)

    global_vbox.Add(sw, 1, wx.EXPAND|wx.ALL, 10)

#    frame = gtk.Frame()
#    frame.set_shadow_type(gtk.SHADOW_IN)
#    frame.add(align_table)
#    table.attach(frame, 0, 1, layer_index+3, layer_index+4, gtk.FILL,  gtk.FILL, 0, 0)
#    sw = gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
#    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
#    sw.add_with_viewport(table) # add textbuffer view widget
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
                        arg4=[energy, background, resolution, scaling_factor, theta_max, x_from, x_to],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )
    butLayer.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=3, arg2=dialog, arg3=window,
                        arg4=[energy, background, resolution, scaling_factor, theta_max, x_from, x_to],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )
    butMultiLayer.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=4, arg2=dialog, arg3=window,
                        arg4=[energy, background, resolution, scaling_factor, theta_max, x_from, x_to],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )

    butFit.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=5, arg2=dialog, arg3=window,
                        arg4=[energy, background, resolution, scaling_factor, theta_max, x_from, x_to],
                        arg5=[layer_params, fit_params, max_iter],
                        func=self.dialog_response: func( evt, arg1, arg2, arg3, arg4, arg5 ) )




#    dialog.connect("response", self.dialog_response, dialog, window, \
#                   [energy, background, resolution, scaling_factor, theta_max, x_from, x_to], \
#                   [layer_params, fit_params, max_iter])
    # befor the widget gets destroyed the textbuffer view widget is removed
    #dialog.connect("destroy",self.close_plot_options_window,sw) 
    dialog.Show()
    # connect dialog to main window
    window.open_windows.append(dialog)

    def myRemove(evt, arg1):
        print 'reflectometer.py: entry myRemove: arg1 = ', arg1
        arg1.Destroy()
        window.open_windows.remove(arg1)
        print 'window.open_windows = ', window.open_windows 

    dialog.Bind(event=wx.EVT_CLOSE, handler=lambda evt, arg1=dialog, func=myRemove: func(evt,arg1) )

  def stop_scroll_emission(self, SL_selector, action):
    SL_selector.stop_emission('scroll-event')

  def create_layer_options(self, layer, layer_index, layer_params, dialog, window, home, substrate=False):
    '''
      Create dialog inputs for every layer.
      Checkboxes are connected to toggle_fit_option,
      entries get passed to dialog_get_params when dialog response is triggered
      and 'DEL' buttons are connected to delete_layer
    '''
    print 'reflectometer.py create_layer_options: layer.multilayer = ',layer.multilayer
    if not layer.multilayer:
      #++++++++++++++++++ singlelayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]=[]
      align_table = wx.GridBagSizer( )
      # labels
      layer_title = wx.StaticText( home, wx.ID_ANY, style=wx.ALIGN_CENTRE )
      if not substrate:
        layer_title.SetLabel(str(layer_index + 1) + ' - ' + layer.name)
        align_table.Add(layer_title, wx.GBPosition(0,0), span=wx.GBSpan(1,6), flag=wx.CENTER|wx.EXPAND|wx.ALL,  border=5)
        thickness_x = wx.CheckBox(home, wx.ID_ANY, 'thickness')
        align_table.Add(thickness_x, wx.GBPosition(1,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
        thickness_x.Bind(event=wx.EVT_CHECKBOX,
                         handler=lambda evt, arg1=layer_params[layer_index], arg2=0,
                         func=self.toggle_fit_option: func(evt, arg1, arg2) )
      else:
        layer_title.SetLabel('Substrate - ' + layer.name)
        align_table.Add(layer_title, wx.GBPosition(0, 0), flag=wx.CENTER|wx.EXPAND|wx.ALL, span=wx.GBSpan(1,6), border=5)


      delta_x = wx.CheckBox(home, wx.ID_ANY, label='delta')
      align_table.Add( delta_x, wx.GBPosition(1,1), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      delta_x.Bind(event=wx.EVT_CHECKBOX, handler=lambda evt, arg1=layer_params[layer_index], arg2=1,
                                        func=self.toggle_fit_option: func(evt,arg1,arg2) )

      d_over_b_x = wx.CheckBox(home, wx.ID_ANY, label='delta over beta')
      align_table.Add( d_over_b_x, wx.GBPosition(1,3), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      d_over_b_x.Bind(event=wx.EVT_CHECKBOX, handler=lambda evt, arg1=layer_params[layer_index], arg2=2,
                                        func=self.toggle_fit_option: func(evt,arg1,arg2) )


      roughness_x = wx.CheckBox(home, wx.ID_ANY, label='roughness')
      align_table.Add( roughness_x, wx.GBPosition(1,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      roughness_x.Bind(event=wx.EVT_CHECKBOX, handler=lambda evt, arg1=layer_params[layer_index], arg2=3,
                                        func=self.toggle_fit_option: func(evt,arg1,arg2) )


      # entries
      # activating the input will apply the settings, too


      if not substrate:
        thickness = wx.TextCtrl( home, wx.ID_ANY, style =wx.TE_PROCESS_ENTER )
        thickness.SetMaxLength(10)
        thickness.SetValue(str(layer.thickness))
        align_table.Add(thickness, wx.GBPosition(2,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 ) 
        thickness.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, func=self.dialog_activate: func(evt, arg1) )

        delete = wx.Button(home, wx.ID_ANY, label='DEL', style=wx.BU_EXACTFIT )
        delete.Bind(event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window,
                                         func=self.delete_layer: func(evt, arg1,arg2,arg3) )
        align_table.Add(delete, wx.GBPosition(2,5),  flag=wx.CENTER|wx.ALL, border=3 )
        delete = wx.Button(home, wx.ID_ANY, label='UP', style=wx.BU_EXACTFIT )
        delete.Bind(event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window, 
                                         func=self.up_layer: func(evt, arg1, arg2,arg3) )
        align_table.Add(delete, wx.GBPosition(2,6), flag=wx.CENTER|wx.ALL, border=3 )

      delta = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      delta.SetMaxLength(10)
      delta.SetValue(str(layer.delta))
      # activating the input will apply the settings, too
      delta.Bind(wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, func=self.dialog_activate: func(evt,arg1) )
      align_table.Add(delta, wx.GBPosition(2,1), flag=wx.CENTER|wx.ALL|wx.EXPAND, border=3 )
      d_over_b = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      d_over_b.SetMaxLength(12)
      d_over_b.SetValue(str(layer.d_over_b))
      # activating the input will apply the settings, too
      d_over_b.Bind(event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, func=self.dialog_activate: func(evt, arg1) )
      align_table.Add(d_over_b, wx.GBPosition(2,3),  flag=wx.CENTER|wx.ALL|wx.EXPAND, border=3 )
      # selection dialog for material
      SL_selector = wx.ComboBox( home, style=wx.CB_READONLY, size=wx.Size(75,30)  )
      SL_selector.Append('SL')
      SL_selector.SetSelection(0)
      for i, SL in enumerate(self.active_file_data.fit_object.SCATTERING_LENGTH_DENSITIES.items()):
        SL_selector.Append(SL[0])
        if layer.delta==SL[1][0] and layer.d_over_b==SL[1][1]:
          SL_selector.set_active(i+1)
#      SL_selector.connect('scroll-event', self.stop_scroll_emission)
      SL_selector.Bind(event=wx.EVT_TEXT, handler=lambda evt, 
                          arg1=SL_selector, arg2=layer, arg3=delta, arg4=d_over_b, 
                          arg5=layer_title, arg6=layer_index, arg7=substrate,
                          func=self.change_scattering_length: func(evt, arg1, arg2, arg3, arg4, arg5, arg6, arg7) )
      layer.SL_selector = SL_selector
      align_table.Add(SL_selector, wx.GBPosition(2,2), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      roughness = wx.TextCtrl( home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      roughness.SetMaxLength(10)
      roughness.SetValue(str(layer.roughness))
      roughness.Bind( event=wx.EVT_TEXT_ENTER, handler=lambda evt, arg1=dialog, 
                      func=self.dialog_activate: func( evt, arg1)  )
      align_table.Add(roughness, wx.GBPosition(2,4), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      # when apply button is pressed or field gets activated, send data
###      dialog.connect('response', layer.dialog_get_params, thickness, delta, d_over_b, roughness) # when apply button is pressed, send data
    else:
      #++++++++++++++++++ multilayer fileds +++++++++++++++++++++++++
      layer_params[layer_index]={}
      align_table = wx.BoxSizer(wx.HORIZONTAL)
#
#      text_filed = wx.StaticText( home, wx.ID_ANY, label='Multilayer')
#      align_table.Add(text_filed, wx.GBPosition(0,0), flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      text_filed =  wx.StaticText( home, wx.ID_ANY, label=str(layer_index + 1) + ' - ' + layer.name )
      align_table.Add( text_filed, 0, flag=wx.CENTER|wx.ALL|wx.EXPAND, border=3 )


      repititions = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      repititions.SetMaxLength(3)
      repititions.SetMaxSize(wx.Size(50,25))
      repititions.SetValue(str(layer.repititions))
      # activating the input will apply the settings, too
      repititions.Bind( event=wx.EVT_TEXT_ENTER, 
                        handler=lambda evt, arg1=dialog, func=self.dialog_activate: func(evt, arg1) )
      align_table.Add(repititions, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      add = wx.Button(home, wx.ID_ANY, label='Add Layer', style=wx.BU_EXACTFIT )
      add.Bind(event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window, 
               func=self.add_multilayer: func(evt, arg1, arg2, arg3) )
      align_table.Add(add, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
 

      # entry for a gradient in roughness
      text_filed = wx.StaticText(home, wx.ID_ANY )
      text_filed.SetLabel('Roughness Gradient:')
      align_table.Add(text_filed,  0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      roughness_gradient = wx.TextCtrl(home, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
      roughness_gradient.SetMaxLength(3)
      roughness_gradient.SetValue(str(layer.roughness_gradient))
      # activating the input will apply the settings, too
      roughness_gradient.Bind(event=wx.EVT_TEXT_ENTER,
                              handler=lambda evt, arg1=dialog, 
                              func=self.dialog_activate: func(evt, arg1) )
      align_table.Add(roughness_gradient, 0, flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )

      delete = wx.Button(home, wx.ID_ANY, label='DEL', style=wx.BU_EXACTFIT)
      delete.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window,
                   func=self.delete_multilayer: func(evt, arg1, arg2, arg3) )
      align_table.Add(delete,  flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )
      delete = wx.Button(home, wx.ID_ANY, label='UP', style=wx.BU_EXACTFIT)
      delete.Bind( event=wx.EVT_BUTTON, handler=lambda evt, arg1=layer, arg2=dialog, arg3=window,
                   func=self.up_layer: func(evt, arg1, arg2, arg3) )
      align_table.Add(delete, 0,flag=wx.CENTER|wx.EXPAND|wx.ALL, border=3 )


####      dialog.connect('response', layer.dialog_get_params, repititions, roughness_gradient) # when apply button is pressed, send data
      # sublayers are appended to the align_table via recursion
      s_box = wx.StaticBox(home, label='Multilayer', size=(300,130) )
      s_boxsizer = wx.StaticBoxSizer(s_box, wx.VERTICAL)
      s_boxsizer.Add( align_table )
      print 'layer.layers = ',layer.layers
      for i, sub_layer in enumerate(layer.layers):
        print 'i =', i, ' sub_layer = ',sub_layer
        sub_table=self.create_layer_options(sub_layer, i, layer_params[layer_index], dialog, window, home)
        s_boxsizer.Add(sub_table)

      return s_boxsizer
 

#      frame = gtk.Frame()
#      frame.set_shadow_type(gtk.SHADOW_IN)
#      frame.add(align_table)
#      align_table=frame

    return align_table
  
  
  def dialog_response(self, action, response, dialog, window, parameters_list, fit_list):
    '''
      handle fit dialog response
    '''
    if response>=5:
      try:
        self.active_file_data.fit_object.radiation[0]   = float(parameters_list[0].GetValue())
        self.active_file_data.fit_object.background     = float(parameters_list[1].GetValue())
        self.active_file_data.fit_object.resolution     = float(parameters_list[2].GetValue())
        self.active_file_data.fit_object.scaling_factor = float(parameters_list[3].GetValue())
        self.active_file_data.fit_object.theta_max      = float(parameters_list[4].GetValue())
      except ValueError:
        None
      try:
        self.x_from=float(parameters_list[5].GetValue())
      except ValueError:
        self.x_from=None
      try:
        self.x_to=float(parameters_list[6].GetValue())
      except ValueError:
        self.x_to=None
      self.active_file_data.fit_object.set_fit_parameters(layer_params=fit_list[0], substrate_params=map(lambda x: x-1, fit_list[1][0]), \
                                         background=fit_list[1]['background'], \
                                         resolution=fit_list[1]['resolution'], \
                                         scaling=fit_list[1]['scaling'])
      try:
        self.max_iter=int(fit_list[2].GetValue())
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
    def butClicked(event):
        id = event.GetId()
        print 'reflectometer.py Entry butClicked: id = ', id
        ret = 0
        if id == idButOk:
           ret = 1
        elif id == idButCancel:
           ret = 2

        results.EndModal( ret )

    old_fit=self.active_file_data.fit_object

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


    window.open_windows.append(dialog)
#    results.connect("destroy", lambda *w: window.open_windows.remove(dialog))
    results.Bind( event=wx.EVT_CLOSE, handler=lambda evt, arg1=results: window.open_windows.remove(evt, arg1) )

    #dialog.connect("response", self.result_window_response, dialog, window, new_fit)
    # connect dialog to main window
    response = results.Show_modal()

    self.result_window_response(response, dialog, window, new_fit)
    results.Destroy()
    
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
    dataset.unit_trans([['Theta', '\302\260', 4*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}'], \
                      ['2 Theta', '\302\260', 2*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}']])    
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', print_info=False, only_fitted_columns=True, xfrom=self.x_from, xto=self.x_to)
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    #open a background process for the fit function


########    reflectometer_fit.functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',self.max_iter)
#     8.Juni 2010
#     Name wie in treff.py: reflectometer_fit.functions ersetzt durch refl_fit_functions
#     refl_fit_functions.proc
    refl_fit_functions.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', 
                                                    self.TEMP_DIR+'fit_temp',self.max_iter)


    print "fit.f90 program started."
    if self.active_file_data.fit_object.fit!=1: # if this is not a fit just wait till finished
#######      exec_time, stderr_value = reflectometer_fit.functions.proc.communicate()
#     8.Juni 2010
#     Name wie in treff.py: reflectometer_fit.functions ersetzt durch refl_fit_functions
      exec_time, stderr_value = refl_fit_functions.proc.communicate()
      print "fit.f90 program finished in %.2g seconds." % float(exec_time.splitlines()[-1])
    else:
      self.open_status_dialog(window)
    simu=read_data.reflectometer.read_simulation(self.TEMP_DIR+'fit_temp.sim')
    simu.number='sim_'+dataset.number
    simu.short_info='simulation'
    simu.sample_name=dataset.sample_name
    dataset.plot_together=[dataset, simu]
    window.replot()

  def dialog_fit(self, action, window):
    '''
      function invoked when apply button is pressed
      fits with the new parameters
    '''
    dataset=window.measurement[window.index_mess]
      # convert x values from angle to q
    dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])    
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', print_info=False, only_fitted_columns=True, xfrom=self.x_from, xto=self.x_to)
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
        layer_title.set_markup('Substrate - ' + layer.name)
      else:
        layer_title.set_markup(str(layer_index + 1) + ' - ' + layer.name)
    except KeyError:
      delta.set_text("1")
      d_over_b.set_text("1")
  
  def import_fit_dialog(self, action, window):
    '''
      file selection dialog for parameter import from .ent file
    '''
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    file_dialog = wx.FileDialog(None, message='Open new datafile',
                                 style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST )
    filter = ''
    filter += 'Entry file (*.ent)|*.ent' 
    filter += '|All files |*.*' 
    file_dialog.SetWildcard( filter )

    response = file_dialog.ShowModal()
    print 'reflectometr.py: import_fit_dialog response file dialog = ', response
 
    if response == wx.ID_OK:
      file_name=file_dialog.GetFilename()
    elif response == wx.ID_CANCEL:
      file_dialog.Destroy()
      return False
    file_dialog.Destroy()
 

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
    file_dialog = wx.FileDialog(None, message='Open new datafile ...',
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

    response = file_dialog.ShowModal()
    print 'reflectometer.py: export_fit_dialog response file dialog = ', response
    if response == wx.ID_OK:
      file_name = file_dialog.GetFilename()
    elif response == wx.ID_CANCEL:
      file_dialog.Destroy()
      return False

    file_dialog.Destroy()

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

class RefFitParameters(FitParameters):
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  radiation=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
  number_of_points=10 # number of simulated points
  resolution=3.5 # resolution in q in 1e-3 A^-1
  theta_max= 2.3 # angle of total coverage for recalibration
  from config.scattering_length_table import SCATTERING_LENGTH_DENSITIES
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
      parameters=[thickness] + SL + [roughness]
    except (KeyError, TypeError):
      parameters=[thickness] + [1. for i in range(self.PARAMETER_LENGTH-2)] + [roughness]
      material='Unknown'
      result=False
    layer=RefLayerParam(material, parameters)
    self.layers.append(layer)
    return result

  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.SCATTERING_LENGTH_DENSITIES[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(RefLayerParam(materials[i], [thicknesses[i]] + SL + [roughnesses[i]]))
    multilayer=RefMultilayerParam(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1. for i in range(self.PARAMETER_LENGTH - 2)]
      result=False
    layer=RefLayerParam(material, [0.] + SL + [roughness])
    self.substrate=layer
    return result

  def get_ent_str(self, use_roughness_gradient=True):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.number_of_layers() + 1) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string_layer, layer_index, para_index = self.__get_ent_str_layers__(use_roughness_gradient)
    ent_string+=ent_string_layer
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
    fit_cons+=self.user_constraints
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
    new_fit=FitParameters.copy(self, RefFitParameters())
    new_fit.radiation=copy(self.radiation)
    new_fit.number_of_points=self.number_of_points
    new_fit.resolution=self.resolution
    new_fit.theta_max=self.theta_max
    return new_fit

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
      layer=RefLayerParam(name=name, parameters_list=parameters)
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
    self.substrate=RefLayerParam(name=name, parameters_list=parameters)
    # read last parameters
    lines.pop()
    self.background=float(lines.pop().split()[0])
    self.resolution=float(lines.pop().split()[0])
    self.scaling_factor=float(lines.pop().split()[0])
    lines.pop()
    self.theta_max=float(lines.pop().split()[0])
    self.combine_layers(RefMultilayerParam)

class RefLayerParam(LayerParam):
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  delta=1
  d_over_b=1
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    LayerParam.__init__(self, name, parameters_list)
    if parameters_list!=None:
      self.delta=parameters_list[1]
      self.d_over_b=parameters_list[2]
    else:
      self.delta=1
      self.d_over_b=1
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return LayerParam.__eq__(self, other) and\
      self.delta==other.delta and\
      self.d_over_b==other.d_over_b
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return RefLayerParam(name=self.name, \
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
    LayerParam.dialog_get_params(self, action, response, thickness, roughness)
    try:
      self.delta=float(delta.GetValue())
      self.d_over_b=float(d_over_b.GetValue())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==1: 
      self.delta=value
    elif index==2: 
      self.d_over_b=value
    else:
      LayerParam.set_param(self, index, 3, value)
  
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
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=LayerParam.__get_ent_text_end__(self, layer_index, para_index, add_roughness)
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class RefMultilayerParam(MultilayerParam):
  '''
    class for multilayer data
  '''
  
  def copy(self):
    return MultilayerParam.copy(self, RefMultilayerParam())
  
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
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    if self.roughness_gradient==0:
      constrain_params=4
    else:
      constrain_params=3
    for j in range(layers): # iterate through layers
      for i in range(constrain_params): # iterate through parameters
        list.append([param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)])
    return list, param_index + len(self)




if __name__ == '__main__':
   print 'name ist main'
   app   = wx.PySimpleApp()
   frame = wx.Frame(None)
   dd    = ReflectometerGUI()
   mb    = wx.MenuBar()
   frame.SetMenuBar( mb )
   menulist = dd.create_menu(frame)

   print 'menulist = ', menulist 
   for j, item in enumerate(menulist):
          print 'j = ',j,' append item = ', item
          mb.Append(item[0], item[1] )

   frame.Show(True)
   app.MainLoop()