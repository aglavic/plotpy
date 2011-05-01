# -*- encoding: utf-8 -*-
'''
  Functions for reflectometer and treff sessions to work with fortran fit program. 
  They only work if imported inside a plotting session and are expanded with specific functions in the
  session source code.
'''

# import buildin modules
import os
import sys
import math
import subprocess
import gtk
import time

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.5.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class ReflectometerFitGUI:
  def dialog_activate(self, action, dialog):
    ''' just responde the right signal, when input gets activated '''
    dialog.response(6)

  def result_window_response(self, response, dialog, window, new_fit):
    '''
      depending of response to the result window use new fit parameters
      or old ones.
    '''
    self.active_file_data.fit_object.fit=0
    if response==1:
      self.active_file_data.fit_object_history.append(self.active_file_data.fit_object)
      self.active_file_data.fit_object_future=[]
      self.active_file_data.fit_object=new_fit
      self.rebuild_dialog(dialog, window)
    else:
      self.dialog_fit(None, window)

  def fit_history(self, action, back, dialog, window):
    '''
      Change fit options to older parameters and back.
    '''
    if back:
      self.active_file_data.fit_object_future=[self.active_file_data.fit_object] + self.active_file_data.fit_object_future
      self.active_file_data.fit_object=self.active_file_data.fit_object_history.pop(-1)
    else:
      self.active_file_data.fit_object_history.append(self.active_file_data.fit_object)
      self.active_file_data.fit_object=self.active_file_data.fit_object_future.pop(0)
    self.rebuild_dialog(dialog, window)

  def rebuild_dialog(self, dialog, window):
    '''
      reopen the fit dialog window to redraw all buttons with a
      new fit_parameters object
    '''
    position=dialog.get_position()
    size=dialog.get_size()
    dialog.destroy()
    self.fit_window(None, window, position=position, size=size)

  def delete_layer(self, action, layer, dialog, window):
    '''
      remove a layer after button is pressed
    '''
    self.active_file_data.fit_object.remove_layer(layer)
    self.rebuild_dialog(dialog, window)

  def up_layer(self, action, layer, dialog, window):
    '''
      remove a layer after button is pressed
    '''
    # is the layer not part of a multilayer?
    if layer in self.active_file_data.fit_object.layers:
      self.active_file_data.fit_object.layers=self.move_layer_up_in_list(layer, self.active_file_data.fit_object.layers)
      self.rebuild_dialog(dialog, window)
    else: # it is a part of a multilayer, try to find it
      for layer_in in self.active_file_data.fit_object.layers:
        if layer_in.multilayer:
          if layer in layer_in.layers:
            layer_in.layers=self.move_layer_up_in_list(layer, layer_in.layers)
            self.rebuild_dialog(dialog, window)

  def move_layer_up_in_list(self, layer, old_layer_list):
      index_layer=old_layer_list.index(layer)
      new_layer_list=[]
      if index_layer > 1:
        new_layer_list=old_layer_list[:index_layer-1] 
      new_layer_list.append(layer)
      if index_layer > 0:
        new_layer_list.append(old_layer_list[index_layer-1])
      if index_layer <= len(old_layer_list):
        new_layer_list+=old_layer_list[index_layer+1:]
      return new_layer_list

  def delete_multilayer(self, action, multilayer, dialog, window):
    '''
      remove a multilayer after button is pressed
    '''
    self.active_file_data.fit_object.layers.remove(multilayer)
    self.rebuild_dialog(dialog, window)

  def open_status_dialog(self, window):
    '''
      when fit process is started, create a window with
      status informations and a kill button
    '''
    def status_response(action, response, session, window):
      if response==1: # if the process is abborted, plot without fit
        self.proc.kill()
        session.active_file_data.fit_object.fit=0
        session.dialog_fit(action, window)
      elif response==2:
        replot_present(session, window)
      
    replot_present=self.replot_present
    from gtkgui.dialogs import StatusDialog
    status=StatusDialog(title='Fit status after 0 s')
    status.set_default_size(500,450)
    status.add_button('Plot present simulation',2) # button kill has handler_id 2
    status.add_button('Kill Process',1) # button kill has handler_id 1
    status.connect("response", status_response, self, window)
    status.show_all()
    status.set_modal(True)
    start=time.time()
    time_get=time.time
    main_iteration=gtk.main_iteration
    events_pending=gtk.events_pending
    file_name=self.TEMP_DIR+self.RESULT_FILE
    # while the process is running ceep reading the .ref output file
    while self.proc.poll()==None and not os.path.exists(file_name):
      continue
    file=open(file_name, 'r')
    text=file.read()
    while self.proc.poll()==None:
      try:
        line=open(self.TEMP_DIR+'status').read()
        iteration=int(line.split('-')[0].split(':')[1])
        chi=float(line.split('-')[1].split(':')[1])
        improvements=int(line.split('-')[2].split(':')[1])
        s_text='Status after ' + str(round(time_get()-start, 1)) + \
                ' s: iteration %i, chi %.6g' % (iteration, chi)
        if improvements>0:
          s_text+='(%i)' % improvements
      except:
        iteration=1
        chi=0
        improvements=0
        s_text='No status available at...'
      text=file.read()
      status.set_title(s_text)
      status.write(text)
      time.sleep(0.1)
    try:
      file.close()
    except AttributeError:
      pass
    status.destroy()


  def toggle_fit_option(self, action, list, number):
    '''
      add or remove parameter from list
    '''
    if number in list:
      list.remove(number)
    else:
      list.append(number)
    list.sort()

  def toggle_fit_bool_option(self, action, dict, value):
    '''
      add or remove parameter from list
    '''
    dict[value]=not dict[value]

  def user_constraint_dialog(self, fit_dialog, window):
    '''
      Open a dialog that shows the constraints for the active fit
      with the possiblilty to add custom constraints by the user.
      A second window shows the .ent file for the parameter list.
    '''
    from pango import FontDescription
    # create the constraints list
    self.active_file_data.fit_object.set_fit_constrains()
    constraint_dialog=gtk.Dialog(title='Add constraints:', parent=fit_dialog, 
                                 flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                 buttons=('Add constraint', 2, 'OK', 1, 'Cancel', 0))
    parameter_dilog=gtk.Dialog(title='Fit parameters:', parent=constraint_dialog, 
                               flags=gtk.DIALOG_DESTROY_WITH_PARENT)
    # move to better usable positions
    parameter_dilog.set_default_size(600, 400)
    parameter_dilog.move(0, 0)
    constraint_dialog.set_default_size(400, 50)
    constraint_dialog.move(600, 0)
    parameter_text=gtk.TextView()
    parameter_text.get_buffer().set_text(self.active_file_data.fit_object.get_ent_str())
    # set monospace fonts for better readability
    parameter_text.modify_font(FontDescription("mono"))
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(parameter_text)
    parameter_dilog.vbox.add(sw)
    parameter_dilog.show_all()
    # remove User Constrints from the list
    for cons in self.active_file_data.fit_object.user_constraints:
      try:
        self.active_file_data.fit_object.constrains.remove(cons)
      except ValueError:
        continue
    for constraint in self.active_file_data.fit_object.constrains:
      text=gtk.Label()
      text.set_markup(str(constraint))
      constraint_dialog.vbox.pack_start(text, expand=False)
    for user_con in self.active_file_data.fit_object.user_constraints:
      table=gtk.Table(4, 1, False)
      text=gtk.Label()
      text.set_markup('[')
      table.attach(text, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      entry=gtk.Entry()
      entry.set_width_chars(30)
      entry.set_text(str(user_con)[1:-1])
      table.attach(entry, 1, 2, 0, 1, gtk.FILL|gtk.EXPAND, gtk.FILL, 0, 0)
      text=gtk.Label()
      text.set_markup(']')
      table.attach(text, 2, 3, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      del_button=gtk.Button(label='del')
      del_button.connect('clicked', lambda act, tab, box: box.remove(tab), 
                         table, constraint_dialog.vbox)
      table.attach(del_button, 3, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      table.show_all()
      constraint_dialog.vbox.pack_end(table)    
    constraint_dialog.show_all()
    constraint_dialog.connect("response", self.user_constraint_response, constraint_dialog, fit_dialog)

  def user_constraint_response(self, action, response, dialog, fit_dialog):
    '''
      Response to the user_constraint_dialog actions.
    '''
    if response==2:
      table=gtk.Table(4, 1, False)
      text=gtk.Label()
      text.set_markup('[')
      table.attach(text, 0, 1, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      entry=gtk.Entry()
      entry.set_width_chars(30)
      table.attach(entry, 1, 2, 0, 1, gtk.FILL|gtk.EXPAND, gtk.FILL, 0, 0)
      text=gtk.Label()
      text.set_markup(']')
      table.attach(text, 2, 3, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      del_button=gtk.Button(label='del')
      del_button.connect('clicked', lambda act, tab, box: box.remove(tab), table, dialog.vbox)
      table.attach(del_button, 3, 4, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
      table.show_all()
      dialog.vbox.pack_end(table)
    if response==1:
      self.active_file_data.fit_object.user_constraints=[]
      objects=dialog.vbox.get_children()
      for object in objects:
        if type(object) is gtk.Table:
          for widget in object.get_children():
            if type(widget) is gtk.Entry:
              try:
                self.active_file_data.fit_object.user_constraints.append(map(int, widget.get_text().split(',')))
              except ValueError:
                continue
      fit_dialog.response(5)
    if response!=2:
      dialog.destroy()
    
  def read_fit_file(self, file_name, fit_object):
    '''
      get fit-parameters back from the file
    '''
    parameters=map(str, fit_object.fit_params)
    result={}
    errors={}
    fit_file=open(file_name,'r')
    test_fit=fit_file.readlines()
    fit_file.close()
    for i,line in enumerate(reversed(test_fit)):
      split=line.split()
      if len(split)>1:
        if split[0] in parameters:
          try:
            result[int(split[0])]=float(split[1])
          except ValueError:
            pass
          try:
            errors[int(split[0])]=float(split[3])
          except ValueError:
            pass
          except IndexError:
            errors[int(split[0])]=0.
      if len(parameters)==len(result):
          return result, errors
    return None
