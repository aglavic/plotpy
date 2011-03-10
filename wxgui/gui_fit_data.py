# -*- encoding: utf-8 -*-
'''
  wx dialog extensions for the fit_data module. Creating a dialog to select
  functions and their parameters to be fitted.
'''

import wx
from math import sqrt

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.7.2.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class FitFunctionGUI: pass

class FitSessionGUI:
  '''
    GUI Methods for the FitSession class .
  '''

  #+++++++++++++++++++++++++ methods for GUI dialog ++++++++++++++++++++
  def get_dialog(self, window, dialog, sw):
    '''
      Create a aligned table widget for the interaction with this class.
      
      @param window The parent Window for the dialog
      @param dialog The dialog the table will be appendet to
      
      @return A widget object for the Dialog and a list of action widgets inside the table
    '''
    def set_function_param(action, function, index):
      '''
        Toggle a setting in the functions list. 
        Called when check button is pressed.
      '''
      print 'Entry set_function_param: function = ',function
      print 'Entry set_function_param: index    = ',index
      function[index]=not function[index]


    print 'fit_data.py: Entry get_dialog window = ', window
    print 'fit_data.py: Entry get_dialog dialog = ', dialog
    print 'fit_data.py: self.functions = ', self.functions
    print 'fit_data.py: len self.functions = ', len(self.functions)
    entries=[]
    align_table = wx.GridBagSizer(30,10)

    for i, function in enumerate(self.functions):
      #+++++++ create a row for every function in the list +++++++
      print 'i = ',i,' function = ',function
      text = wx.StaticText( sw, wx.ID_ANY, label=function[0].name + ': ')
      align_table.Add( text, wx.GBPosition(i*2, 0), span=wx.GBSpan(1,2), flag=wx.EXPAND  )

      if function[0].parameters_history is not None:
        back_button = wx.Button( sw, wx.ID_ANY, label='Undo')
        align_table.Add( back_button, wx.GBPosition(i*2+1,0), flag=wx.EXPAND )
        back_button.Bind( wx.EVT_BUTTON, handler=lambda evt, arg1=dialog, arg2=window:
                          function[0].history_back(evt, arg1, arg2) )

      text = wx.StaticText(sw, wx.ID_ANY, label=' fit ')
      align_table.Add( text, wx.GBPosition(i*2, 2), flag=wx.EXPAND  )
      text = wx.StaticText(sw, wx.ID_ANY, label=' show ')
      align_table.Add( text, wx.GBPosition(i*2, 3), flag=wx.EXPAND  )
#
      text = wx.TextCtrl( sw, wx.ID_ANY, size=(400,20) )
      text.SetValue(function[0].fit_function_text)
      text.SetMaxLength(40)
      align_table.Add( text, wx.GBPosition(i*2, 4) )

      toggle_errors = wx.CheckBox( sw, wx.ID_ANY, label="ignore errors")
      toggle_errors.SetValue(function[3])
      toggle_errors.Bind( wx.EVT_CHECKBOX, handler=lambda evt, arg1=function, arg2=3:
                                          set_function_param(evt, arg1, arg2) )
      align_table.Add(toggle_errors, wx.GBPosition(i*2, 5), flag=wx.EXPAND )

      new_line, entry = self.function_line(function[0], dialog, window, sw)
      entries.append(entry+[text, toggle_errors])
      align_table.Add(new_line, wx.GBPosition(i*2+1, 4), span=wx.GBSpan(1,2)  )

      toggle_fit = wx.CheckBox( sw, wx.ID_ANY )
      toggle_fit.SetValue(function[1])
      align_table.Add(toggle_fit, wx.GBPosition(i*2+1, 2), flag=wx.EXPAND )
      toggle_fit.Bind( wx.EVT_CHECKBOX,  handler=lambda evt, arg1=function, arg2=1:
                      set_function_param(evt, arg1, arg2) )

      toggle_show = wx.CheckBox( sw, wx.ID_ANY )
      toggle_show.SetValue(function[2])
      align_table.Add(toggle_show, wx.GBPosition(i*2+1, 3), flag=wx.EXPAND )
      toggle_show.Bind( wx.EVT_CHECKBOX,  handler=lambda evt, arg1=function, arg2=2:
                      set_function_param(evt, arg1, arg2) )

      #------- create a row for every function in the list -------
    # Options for new functions

    new_function = wx.ComboBox( dialog )
    new_function.SetMinSize( wx.Size(200,25) )
   

    map(new_function.Append, self.get_functions())  # trage funktionen in combo box ein

    add_button = wx.Button(dialog, wx.ID_ANY, label='Add Function')
    sum_button = wx.Button(dialog, wx.ID_ANY, label='Combine')
    fit_button = wx.Button(dialog, wx.ID_ANY, label='Fit and Replot')

    # connect the window signals to the handling methods

    add_button.Bind( wx.EVT_BUTTON, 
                     handler=lambda evt, arg1=new_function, arg2=dialog, arg3=window:
                             self.add_function_dialog(evt, arg1, arg2, arg3) )
    sum_button.Bind( wx.EVT_BUTTON, 
                     handler=lambda evt, arg1=dialog, arg2=window:
                     self.combine_dialog(evt, arg1, arg2) )
    fit_button.Bind( wx.EVT_BUTTON, 
                     handler=lambda evt, arg1=entries, arg2=dialog, arg3=window:
                     self.fit_from_dialog(evt, arg1, arg2, arg3) )


    def toggle_show_covariance( event ):
      print 'self.show_covariance = ', self.show_covariance
      self.show_covariance=not self.show_covariance

    toggle_covariance = wx.CheckBox( dialog, wx.ID_ANY, label='show errors')
    toggle_covariance.SetValue(self.show_covariance)
    toggle_covariance.Bind( wx.EVT_CHECKBOX, handler=toggle_show_covariance )

    return  align_table, [toggle_covariance, new_function, add_button, sum_button, fit_button]
  
  def function_line(self, function, dialog, window, sw):
    '''
      Create the widgets for one function and return a table of those.
      The entry widgets are returned in a list to be able to read them.
      
      @param function The FitFunction object for this line
      @param dialog The dialog widget this line will be added to
      @param window The parent window for the dialog
      
      @return A table widget for this function line and a list of entry widgets.
    '''
    print 'fit_data.py: Entry function_line'
    table = wx.GridBagSizer( )
    entries=[]
    for i, parameter in enumerate(function.parameters):
      # Test,Toggle and Entry for every parameter of the funciton
      text   = wx.StaticText( sw, wx.ID_ANY, label=function.parameter_names[i])
      toggle = wx.CheckBox( sw, wx.ID_ANY)
      toggle.SetValue(i in function.refine_parameters)
      toggle.Bind( wx.EVT_CHECKBOX, handler=lambda evt, arg1=i: 
                   function.toggle_refine_parameter( evt, arg1) ) 
      entries.append( wx.TextCtrl( sw, wx.ID_ANY ))
      entries[i].SetMaxLength(8)
      entries[i].SetValue("%.6g" % parameter)
      table.Add( toggle,     wx.GBPosition(i*3//12, i*3%12),     flag=wx.ALIGN_CENTER_VERTICAL )
      table.Add( text,       wx.GBPosition(i*3//12, (i*3%12)+1), flag=wx.ALIGN_CENTER_VERTICAL)
      table.Add( entries[i], wx.GBPosition(i*3//12, (i*3%12)+2), flag=wx.ALIGN_CENTER_VERTICAL)

    # Button to delete the function
    del_button = wx.Button(sw, wx.ID_ANY, label='DEL' )
    table.Add( del_button, wx.GBPosition(0,12), flag=wx.ALIGN_CENTER_VERTICAL)
    del_button.Bind( wx.EVT_BUTTON, handler=lambda evt, arg1=function, arg2=dialog, arg3=window:
                     self.del_function_dialog(evt, arg1, arg2, arg3))
    entries.append( wx.TextCtrl( sw, wx.ID_ANY ) )
    entries[len(function.parameters)].SetMaxLength(8)
    # entries for the x range this function is fitted in
    if function.x_from is not None:
      entries[len(function.parameters)].SetValue("%.6g" % function.x_from)
    else:
      entries[len(function.parameters)].SetValue("{from}")  
    
    table.Add( entries[len(function.parameters)] , wx.GBPosition(0,13), flag=wx.ALIGN_CENTER_VERTICAL )
    entries.append( wx.TextCtrl( sw, wx.ID_ANY ))
    entries[len(function.parameters)+1].SetMaxLength(8)
    if function.x_to is not None:
      entries[len(function.parameters)+1].SetValue("%.6g" % function.x_to)
    else:
      entries[len(function.parameters)+1].SetValue("{to}")

    table.Add( entries[len(function.parameters)+1] ,wx.GBPosition(0,14), flag=wx.ALIGN_CENTER_VERTICAL )

    return table, entries

  def add_function_dialog(self, action, name, dialog, window):

    '''
      Add a function via dialog access.
      Standart parameters are used.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    print 'fit_data.py: Entry add_function_dialog'
    print 'name   = ', name
    print 'dialog = ', dialog
    print 'window = ', window
    window.file_actions.activate_action('add_function', name.GetValue())
    print 'sel value = ', name.GetValue()
    size     = dialog.GetSize()
    position = dialog.GetPosition()
    dialog.Destroy()
    window.fit_dialog(None, size, position)
  
  def del_function_dialog(self, action, function, dialog, window):
    '''
      Delete a function via dialog access.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    print 'fit_data.py: Entry del_function_dialog'
    self.del_function(function)
    size     = dialog.GetSize()
    position = dialog.GetPosition()
    dialog.Destroy()
    window.fit_dialog(None, size, position)
  
  def set_function_parameters(self, func_index, values):
    '''
      Set the parameters of one functio object in the list.
    
      @param func_index List index of the function to be altered
      @param values List of values for the parameters to be set
    '''
    for j, value in enumerate(values[0:-3]):
      self.functions[func_index][0].parameters[j]=value

    self.functions[func_index][0].x_from=values[-3]
    self.functions[func_index][0].x_to=values[-2]
    self.functions[func_index][0].fit_function_text=values[-1]
  
  def fit_from_dialog(self, action, entries, dialog, window):
    '''
      Trigger the fit, simulation and replot functions.
      
      @param entries Entry widgets from the dialog to get the function parameters from
      @param dialog Fit dialog widget
      @param window Parent window of the dialog.destroy
    '''
    print 'fit_data.py: Entry fit_from_dialog'
    def get_entry_values(entry, if_not=0):
      '''
        Help function to evaluate the entry boxes. Skippes entries with no numbers
        and converts ',' to '.'.
      '''
      try: 
        return float(entry.GetValue().replace(',', '.'))
      except ValueError:
        return if_not


    for i, function in enumerate(self.functions):
      # Set all function parameters according to the entries
      values=[]
      for entry in entries[i][:-4]:
        values.append(get_entry_values(entry))
      values.append(get_entry_values(entries[i][-4], if_not=None))
      values.append(get_entry_values(entries[i][-3], if_not=None))
      values.append(entries[i][-2].GetValue())
      window.file_actions.activate_action('set_function_parameters', i, values)
    covariance_matices=window.file_actions.activate_action('fit_functions')
    window.file_actions.activate_action('simmulate_functions')
    # save the geometry of the fit dialog and replot the data+fit
    size     = dialog.GetSize()
    position = dialog.GetPosition()
    dialog.Destroy()
    window.replot()
    print 'fit_data.py: return from fit_from_dialog'


    if self.show_covariance:
      # Show the estimated errors of the fit parameters
      text='Esitmated errors from covariance matrices:'
      for i, function in enumerate(self.functions):
        if function[1]:
          text+='\n\n%s:' % function[0].name
          for j, pj in enumerate(function[0].parameter_names):
            text+='\n%s = %g +/- %g' % (pj, function[0].parameters[j], sqrt(covariance_matices[i][j][j]))

      info_dialog = wx.MessageDialog( window, 
                                text,
                                'Covariance matrix',
                                wx.OK|wx.ICON_INFORMATION|wx.STAY_ON_TOP )
      info_dialog.ShowModal()
      info_dialog.Destroy()



    # recreate the fit dialog with the new parameters 
    window.fit_dialog(None, size, position)

  def combine_dialog(self, action, dialog, window):
    '''
      A dialog window to combine two fit functions e.g. sum them up.
    '''

    def butClicked(  event ):
         print 'fit_data.py: Entry combine_dialog butClicked'
         id = event.GetId()
         ret = 0
         if id == idBut1:
           ret = 2
         elif id == idBut2:
           ret = 1
         combine_dialog.EndModal( ret )


    # TODO: Make a(b) working.
    print 'fit_data.py: Entry combine_dialog'
    if len(self.functions)<2:
      return False

    combine_dialog = wx.Dialog(dialog, wx.ID_ANY, title='Fit ...', size=(400,150), 
                         style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)

    vbox = wx.BoxSizer( wx.VERTICAL ) 
    combine_dialog.SetSizer(vbox)


    function_1 = wx.ComboBox( combine_dialog )
    for i, function in enumerate(self.functions):
      function_1.Append(str(i)+': '+function[0].name)

    function_2 = wx.ComboBox( combine_dialog )
    for i, function in enumerate(self.functions):
      function_2.Append(str(i)+': '+function[0].name)

    vbox.Add(function_1, 0, wx.ALL|wx.EXPAND, 3)
    vbox.Add(function_2, 0, wx.ALL|wx.EXPAND, 3)

    hbox       = wx.BoxSizer( wx.HORIZONTAL ) 
    but_add    = wx.Button( combine_dialog, wx.ID_ANY, label='Add: a + b')   # returns 2
    idBut1 = but_add.GetId()
    but_add.Bind( wx.EVT_BUTTON, handler=butClicked )
    but_cancel = wx.Button( combine_dialog, wx.ID_ANY, label='Cancel' )      # returns 1
    idBut2 = but_cancel.GetId()
    but_cancel.Bind( wx.EVT_BUTTON, handler=butClicked )
    hbox.Add( but_add,    0, wx.ALL|wx.EXPAND, 3 )
    hbox.Add( but_cancel, 0, wx.ALL|wx.EXPAND, 3 )
    vbox.Add( hbox,       0, wx.ALL|wx.EXPAND, 3 )

    result = combine_dialog.ShowModal()
    print 'result = ',result 
    print 'function_1 = ',function_1
    print 'function_2 = ',function_2

    selected=[int(function_1.GetValue().split(':')[0]), int(function_2.GetValue().split(':')[0])]
    if result in [2, 3]:
      if result==2:
        print 'selected = ',selected
        window.file_actions.activate_action('sum_up_functions', selected[0], selected[1])
        size     = dialog.GetSize()
        position = dialog.GetPosition()
        dialog.Destroy()
        window.fit_dialog(None, size, position)

    combine_dialog.Destroy()

  #------------------------- methods for GUI dialog ---------------------
