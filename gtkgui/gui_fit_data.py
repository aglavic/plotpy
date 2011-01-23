# -*- encoding: utf-8 -*-
'''
  GTK GUI functions for data fitting.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

# for dialog window import gtk
import gtk
import numpy

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class FitFunctionGUI:
  def history_back(self, action, dialog, window):
    '''
      Set old parameters from the history of parameters and
      set the active parameters as history.
    '''
    active_params=self.parameters
    self.parameters=self.parameters_history
    self.parameters_history=active_params
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)


class FitSessionGUI:
  def get_dialog(self, window, dialog, fit_button_press_event=None):
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
      function[index]=not function[index]
    def toggle_logarithmic(action, function):
      function[0].fit_logarithmic=not function[0].fit_logarithmic
    entries=[]
    align_table=gtk.Table(5,len(self.functions)*2+2,False)
    for i, function in enumerate(self.functions):
      #+++++++ create a row for every function in the list +++++++
      text=gtk.Label(function[0].name + ': ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  0, 2,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      if function[0].parameters_history is not None:
        back_button=gtk.Button(label='Undo')
        align_table.attach(back_button,
                    # X direction #          # Y direction
                    0, 2,                      i*2+1, i*2+2,
                    gtk.EXPAND,     gtk.EXPAND,
                    0,                         0);
        back_button.connect('clicked', function[0].history_back, dialog, window)
      text=gtk.Entry()
      text.set_text(function[0].fit_function_text)
      text.set_width_chars(40)
      align_table.attach(text,
                  # X direction #          # Y direction
                  4, 5,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_errors=gtk.CheckButton(label="ignore errors")
      toggle_errors.set_active(function[3])
      toggle_errors.connect('toggled', set_function_param, function, 3)
      align_table.attach(toggle_errors,
                  # X direction #          # Y direction
                  5, 6,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_log=gtk.CheckButton(label="logarithmic")
      toggle_log.set_active(function[0].fit_logarithmic)
      toggle_log.connect('toggled', toggle_logarithmic, function)
      align_table.attach(toggle_log,
                  # X direction #          # Y direction
                  6, 7,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      new_line, entry=self.function_line(function[0], dialog, window)
      entries.append(entry+[text, toggle_errors])
      align_table.attach(new_line,
                  # X direction #          # Y direction
                  4, 6,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label(' fit ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  2, 3,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_fit=gtk.CheckButton()
      toggle_fit.set_active(function[1])
      toggle_fit.connect('toggled', set_function_param, function, 1)
      align_table.attach(toggle_fit,
                  # X direction #          # Y direction
                  2, 3,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label(' show ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  3, 4,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_show=gtk.CheckButton()
      toggle_show.set_active(function[2])
      toggle_show.connect('toggled', set_function_param, function, 2)
      align_table.attach(toggle_show,
                  # X direction #          # Y direction
                  3, 4,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      #------- create a row for every function in the list -------
    # Options for new functions
    new_function=gtk.combo_box_new_text()
    add_button=gtk.Button(label='Add Function')
    map(new_function.append_text, self.get_functions())
    sum_button=gtk.Button(label='Combine')
    fit_button=gtk.Button(label='Fit and Replot')
    # connect the window signals to the handling methods
    add_button.connect('clicked', self.add_function_dialog, new_function, dialog, window)
    sum_button.connect('clicked', self.combine_dialog, dialog, window)
    fit_button.connect('clicked', self.fit_from_dialog, entries, dialog, window)
    align=gtk.Alignment(0.5, 0.5, 0, 0) # the table is centered in the dialog window
    align.add(align_table)
    def toggle_show_covariance(action, self):
      self.show_covariance=not self.show_covariance
    toggle_covariance=gtk.CheckButton(label='show errors')
    toggle_covariance.set_active(self.show_covariance)
    toggle_covariance.connect('toggled', toggle_show_covariance, self)
    return align, [toggle_covariance, new_function, add_button, sum_button, fit_button]
  
  def function_line(self, function, dialog, window):
    '''
      Create the widgets for one function and return a table of those.
      The entry widgets are returned in a list to be able to read them.
      
      @param function The FitFunction object for this line
      @param dialog The dialog widget this line will be added to
      @param window The parent window for the dialog
      
      @return A table widget for this function line and a list of entry widgets.
    '''
    table=gtk.Table(15, (len(function.parameters)*3+3)//12+1, False)
    entries=[]
    for i, parameter in enumerate(function.parameters):
      # Test,Toggle and Entry for every parameter of the funciton
      text=gtk.Label(function.parameter_names[i])
      toggle=gtk.CheckButton()
      toggle.set_active(i in function.refine_parameters)
      toggle.connect('toggled', function.toggle_refine_parameter, i)
      entries.append(gtk.Entry())
      entries[i].set_width_chars(8)
      entries[i].set_text("%.6g" % parameter)
      table.attach(toggle, i*3%12, (i*3%12)+1, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(text, (i*3%12)+1, (i*3%12)+2, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(entries[i], (i*3%12)+2, (i*3%12)+3, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    # Button to delete the function
    del_button=gtk.Button(label='DEL')
    table.attach(del_button, 12, 13, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    del_button.connect('clicked', self.del_function_dialog, function, dialog, window)
    # entries for the x range this function is fitted in
    entries.append(gtk.Entry())
    entries[len(function.parameters)].set_width_chars(8)
    if function.x_from is not None:
      entries[len(function.parameters)].set_text("%.6g" % function.x_from)
    else:
      entries[len(function.parameters)].set_text("{x-from}")      
    table.attach(entries[len(function.parameters)], 13, 14, 0, 1, 
                             gtk.EXPAND, gtk.EXPAND, 0, 0)
    entries.append(gtk.Entry())
    entries[len(function.parameters)+1].set_width_chars(8)
    if function.x_to is not None:
      entries[len(function.parameters)+1].set_text("%.6g" % function.x_to)
    else:
      entries[len(function.parameters)+1].set_text("{x-to}")
    table.attach(entries[len(function.parameters)+1], 14,15, 0, 1, 
                             gtk.EXPAND, gtk.EXPAND, 0, 0)
    if function.is_3d:
      # entries for the y range this function is fitted in
      entries.append(gtk.Entry())
      entries[len(function.parameters)+2].set_width_chars(8)
      if function.y_from is not None:
        entries[len(function.parameters)+2].set_text("%.6g" % function.y_from)
      else:
        entries[len(function.parameters)+2].set_text("{y-from}")      
      table.attach(entries[len(function.parameters)+2], 13, 14, 1, 2, 
                               gtk.EXPAND, gtk.EXPAND, 0, 0)
      entries.append(gtk.Entry())
      entries[len(function.parameters)+3].set_width_chars(8)
      if function.y_to is not None:
        entries[len(function.parameters)+3].set_text("%.6g" % function.y_to)
      else:
        entries[len(function.parameters)+3].set_text("{y-to}")
      table.attach(entries[len(function.parameters)+3], 14,15, 1, 2, 
                               gtk.EXPAND, gtk.EXPAND, 0, 0)
    return table, entries

  def add_function_dialog(self, action, name, dialog, window):
    '''
      Add a function via dialog access.
      Standart parameters are used.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    window.file_actions.activate_action('add_function', name.get_active_text())
    #self.add_function(name.get_active_text())
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def del_function_dialog(self, action, function, dialog, window):
    '''
      Delete a function via dialog access.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    self.del_function(function)
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def set_function_parameters(self, func_index, values):
    '''
      Set the parameters of one functio object in the list.
    
      @param func_index List index of the function to be altered
      @param values List of values for the parameters to be set
    '''
    function=self.functions[func_index][0]
    if function.is_3d:
      for j, value in enumerate(values[0:-5]):
        function.parameters[j]=value
      function.x_from=values[-5]
      function.x_to=values[-4]
      function.y_from=values[-3]
      function.y_to=values[-2]
      function.fit_function_text=values[-1]
    else:
      for j, value in enumerate(values[0:-3]):
        function.parameters[j]=value
      function.x_from=values[-3]
      function.x_to=values[-2]
      function.fit_function_text=values[-1]
  
  def fit_from_dialog(self, action, entries, dialog, window):
    '''
      Trigger the fit, simulation and replot functions.
      
      @param entries Entry widgets from the dialog to get the function parameters from
      @param dialog Fit dialog widget
      @param window Parent window of the dialog.destroy
    '''
    def get_entry_values(entry, if_not=0):
      '''
        Help function to evaluate the entry boxes. Skippes entries with no numbers
        and converts ',' to '.'.
      '''
      try: 
        return float(entry.get_text().replace(',', '.'))
      except ValueError:
        return if_not
    for i, function in enumerate(self.functions):
      # Set all function parameters according to the entries
      values=[]
      if function[0].is_3d:
        for entry in entries[i][:-6]:
          values.append(get_entry_values(entry))
        values.append(get_entry_values(entries[i][-6], if_not=None))
        values.append(get_entry_values(entries[i][-5], if_not=None))
        values.append(get_entry_values(entries[i][-4], if_not=None))
        values.append(get_entry_values(entries[i][-3], if_not=None))
        values.append(entries[i][-2].get_text())        
      else:
        for entry in entries[i][:-4]:
          values.append(get_entry_values(entry))
        values.append(get_entry_values(entries[i][-4], if_not=None))
        values.append(get_entry_values(entries[i][-3], if_not=None))
        values.append(entries[i][-2].get_text())
      window.file_actions.activate_action('set_function_parameters', i, values)
    covariance_matices=window.file_actions.activate_action('fit_functions')
    window.file_actions.activate_action('simmulate_functions')
    # save the geometry of the fit dialog and replot the data+fit
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.rebuild_menus()
    window.replot()
    if self.show_covariance:
      # Show the estimated errors of the fit parameters
      text='Esitmated errors from covariance matrices:'
      for i, function in enumerate(self.functions):
        if function[1]:
          text+='\n\n%s:' % function[0].name
          for j, pj in enumerate(function[0].parameter_names):
            text+='\n%s = %g +/- %g' % (pj, function[0].parameters[j], numpy.sqrt(covariance_matices[i][j][j]))
      info_dialog=gtk.MessageDialog(parent=window, flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                    type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, message_format=text)
      info_dialog.run()
      info_dialog.destroy()
    # recreate the fit dialog with the new parameters 
    window.fit_dialog(None, size, position)

  def combine_dialog(self, action, dialog, window):
    '''
      A dialog window to combine two fit functions e.g. sum them up.
    '''
    # TODO: Make a(b) working.
    if len(self.functions)<2:
      return False
    function_1=gtk.combo_box_new_text()
    for i, function in enumerate(self.functions):
      function_1.append_text(str(i)+': '+function[0].name)
    function_2=gtk.combo_box_new_text()
    for i, function in enumerate(self.functions):
      function_2.append_text(str(i)+': '+function[0].name)
    combine_dialog=gtk.Dialog(title='Fit...')
    combine_dialog.set_default_size(400,150)
    combine_dialog.vbox.add(function_1)
    combine_dialog.vbox.add(function_2)
    combine_dialog.add_button('Add: a + b',2)
    #combine_dialog.add_button('Add: a(b)',3)
    combine_dialog.add_button('Cancel',1)
    combine_dialog.show_all()
    result=combine_dialog.run()
    selected=[int(function_1.get_active_text().split(':')[0]), int(function_2.get_active_text().split(':')[0])]
    if result in [2, 3]:
      if result==2:
        window.file_actions.activate_action('sum_up_functions', selected[0], selected[1])
        size=dialog.get_size()
        position=dialog.get_position()
        dialog.destroy()
        window.fit_dialog(None, size, position)
    combine_dialog.destroy()
