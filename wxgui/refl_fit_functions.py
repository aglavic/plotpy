'''
  Functions for reflectometer and treff sessions to work with fortran fit program. 
  They only work if imported inside a plotting session and are expanded with specific functions in the
  session source code. This is for the GTK toolkit.
'''

# import buildin modules
import os
import sys
import math
import subprocess
#import gtk
import wx
import time

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

#TODO: Generalize other functions to be moved here

#+++++++++++++++++++++++ GUI functions +++++++++++++++++++++++

def dialog_activate(self, action, dialog):
  ''' just responde the right signal, when input gets activated '''
  print 'refl_fit_functions: Entry dialog_activate action = ', action
  print 'refl_fit_functions: Entry dialog_activate dialog = ', dialog
  dialog.SetReturnCode(6)

def result_window_response(self, response, dialog, window, new_fit):
  '''
    depending of response to the result window use new fit parameters
    or old ones.
  '''
  self.fit_object.fit=0
  if response==1:
    self.fit_object_history.append(self.fit_object)
    self.fit_object_future=[]
    self.fit_object=new_fit
    self.rebuild_dialog(dialog, window)
  else:
    self.dialog_fit(None, window)

def fit_history(self, action, back, dialog, window):
  '''
    Change fit options to older parameters and back.
  '''
  if back:
    self.fit_object_future=[self.fit_object] + self.fit_object_future
    self.fit_object=self.fit_object_history.pop(-1)
  else:
    self.fit_object_history.append(self.fit_object)
    self.fit_object=self.fit_object_future.pop(0)
  self.rebuild_dialog(dialog, window)

def rebuild_dialog(self, dialog, window):
  '''
    reopen the fit dialog window to redraw all buttons with a
    new fit_parameters object
  '''
  position = dialog.GetPosition()
  size     = dialog.GetSize()
  dialog.Destroy()
  print 'refl_fit_functions.py: entry rebuild_dialog position = ', position
  print 'refl_fit_functions.py: entry rebuild_dialog size     = ', size
  self.fit_window(None, window, position=position, size=size)

def delete_layer(self, action, layer, dialog, window):
  '''
    remove a layer after button is pressed
  '''
  print 'refl_fit_functions.py: Entry deleteLayer: action =', action
  print 'refl_fit_functions.py: Entry deleteLayer: layer  =', layer
  print 'refl_fit_functions.py: Entry deleteLayer: dialog =', dialog
  print 'refl_fit_functions.py: Entry deleteLayer: window =', window
  self.fit_object.remove_layer(layer)
  self.rebuild_dialog(dialog, window)

def up_layer(self, action, layer, dialog, window):
  '''
    remove a layer after button is pressed
  '''
  print 'refl_fit_functions: Entry up_layer action = ',action
  print 'refl_fit_functions: Entry up_layer layer  = ',layer
  print 'refl_fit_functions: Entry up_layer dialog = ',dialog
  print 'refl_fit_functions: Entry up_layer window = ',window
  # is the layer not part of a multilayer?
  if layer in self.fit_object.layers:
    self.fit_object.layers=self.move_layer_up_in_list(layer, self.fit_object.layers)
    self.rebuild_dialog(dialog, window)
  else: # it is a part of a multilayer, try to find it
    for layer_in in self.fit_object.layers:
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
  self.fit_object.layers.remove(multilayer)
  self.rebuild_dialog(dialog, window)

def open_status_dialog(self, window):
  '''
    when fit process is started, create a window with
    status informations and a kill button
  '''
  global proc
  def status_response(action, response, session, window):
    if response==1: # if the process is abborted, plot without fit
      proc.kill()
      session.fit_object.fit=0
      session.dialog_fit(action, window)
    elif response==2:
      replot_present(session, window)
    
  replot_present=self.replot_present
    
  status=gtk.Dialog(title='Fit status after 0 s')
  text_view=gtk.TextView()
  # Retrieving a reference to a textbuffer from a textview. 
  buffer = text_view.get_buffer()
  buffer.set_text('')
  sw = gtk.ScrolledWindow()
  # Set the adjustments for horizontal and vertical scroll bars.
  # POLICY_AUTOMATIC will automatically decide whether you need
  # scrollbars.
  sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  sw.add(text_view) # add textbuffer view widget
  status.vbox.add(sw) # add table to dialog box
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
  try:
    file=open(file_name, 'r')
    text='Empty .ref file.'
  except:
    file=None
    text='Empty .ref file.'
  old_text=text
  while proc.poll()==None:
    try:
      line=open(self.TEMP_DIR+'status').read()
      iteration=int(line.split('-')[0].split(':')[1])
      chi=float(line.split('-')[1].split(':')[1])
    except:
      iteration=1
      chi=0
    if file==None:
      try:
        file=open(file_name, 'r')
      except:
        file=None
        text='Empty .ref file.'
    else:
      file.seek(0)
      text=file.read()
      if text=='':
        text='Empty .ref file.'
    s_text='Status after ' + str(round(time_get()-start, 1)) + ' s: iteration %i, chi %.6g' % (iteration, chi)
    status.set_title(s_text)
    if old_text!=text:
      buffer.set_text(text)
      old_text=text
    while events_pending():
      main_iteration(False)
    while events_pending():
      main_iteration(False)
    time.sleep(0.1)
  try:
    file.close()
  except AttributeError:
    pass
  status.set_modal(False)
  status.destroy()


def toggle_fit_option(self, action, list, number):
  '''
    add or remove parameter from list
  '''
  print 'refl_fit_functions.py: Entry toggle_fit_options: action = ',action
  print 'refl_fit_functions.py: Entry toggle_fit_options: list   = ',list
  print 'refl_fit_functions.py: Entry toggle_fit_options: number = ',number
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
#  from pango import FontDescription
  print 'refl_fit_functions.py: entry user_constraint_dialog'
  # create the constraints list
  self.fit_object.set_fit_constrains()

  constraint_dialog = wx.Dialog(fit_dialog, wx.ID_ANY, title='Add constraints:', size=(400,200),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
  parameter_dialog  = wx.Dialog(constraint_dialog, wx.ID_ANY, title='Fit parameters:',  size=(500,600),
                              style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
  parameter_dialog.Move( wx.Point(0, 0) )
  constraint_dialog.Move( wx.Point(600, 0) )
  constraint_dialog.vbox = wx.BoxSizer( wx.VERTICAL )
  constraint_dialog.SetSizer( constraint_dialog.vbox )

  butBox      = wx.StaticBox(constraint_dialog, wx.ID_ANY, style=wx.BORDER_DOUBLE|wx.BORDER_RAISED)
  butBoxSizer = wx.StaticBoxSizer(butBox, wx.HORIZONTAL)
  butAdd      = wx.Button(constraint_dialog, wx.ID_ANY, label='Add constraints' )            # 2
  butOk       = wx.Button(constraint_dialog, wx.ID_ANY, label='OK' )                         # 1
  butCancel   = wx.Button(constraint_dialog, wx.ID_ANY, label='Cancel' )                     # 0

  butBoxSizer.Add( butAdd,    1, wx.EXPAND|wx.ALL, 3)
  butBoxSizer.Add( butOk,     1, wx.EXPAND|wx.ALL, 3)
  butBoxSizer.Add( butCancel, 1, wx.EXPAND|wx.ALL, 3)

  butAdd.Bind(   event=wx.EVT_BUTTON, handler=lambda evt, arg1=2, arg2=constraint_dialog, arg3=fit_dialog,
                 func=self.user_constraint_response: func( evt, arg1, arg2, arg3 ) )
  butOk.Bind(    event=wx.EVT_BUTTON, handler=lambda evt, arg1=1, arg2=constraint_dialog, arg3=fit_dialog,
                 func=self.user_constraint_response: func( evt, arg1, arg2, arg3 ) )
  butCancel.Bind(    event=wx.EVT_BUTTON, handler=lambda evt, arg1=1, arg2=constraint_dialog, arg3=fit_dialog,
                 func=self.user_constraint_response: func( evt, arg1, arg2, arg3 ) )

  constraint_dialog.vbox.Add(butBoxSizer, 0, wx.EXPAND|wx.ALL, 10)
  print 'constraint_dialog = ',constraint_dialog
  print 'constraint_dialog.vbox = ',constraint_dialog.vbox


  parameter_text = wx.TextCtrl( parameter_dialog, wx.ID_ANY, style=wx.TE_MULTILINE)
  parameter_text.SetValue( self.fit_object.get_ent_str() )
  parameter_dialog.Show()

  constraint_dialog.Show()
  print ' GetSize   = ', constraint_dialog.vbox.GetSize()
#  print 'constraints_dialog returns ', self.ret_code

  # remove User Constraints from the list
  for cons in self.fit_object.user_constraints:
    try:
      self.fit_object.constrains.remove(cons)
    except ValueError:
      continue
  for constraint in self.fit_object.constrains:
    text = wx.StaticText(constraint_dialog, wx.ID_ANY, label=str(constraint) )
    constraint_dialog.vbox.Add( text, 0, wx.EXPAND|wxx.ALL, 3)
#    constraint_dialog.vbox.pack_start(text, expand=False)

  print 'self.fit_object.user_constraints: ',self.fit_object.user_constraints

  for user_con in self.fit_object.user_constraints:
    table = wx.BoxSizer( wx.HORIZONTAL )
    text  = wx.StaticText( constraint_dialog, wx.ID_ANY, label='[' )
    table.Add(text, 0, wx.CENTER|wx.EXPAND|wx.ALL, 1 )
    entry = wx.TextCtrl( constraint_dialog, wx.ID_ANY, label=str(user_con)[1:-1] )
    entry.SetMaxLength(30)
    table.Add(entry, 1, wx.CENTER|wx.EXPAND|wx.ALL, 1)
    text =  wx.StaticText( constraint_dialog, wx.ID_ANY, label=']' )
    table.Add(text, 0, wx.CENTER|wx.EXPAND|wx.ALL, 1 )
    del_button = wx.Button( constraint_dialog, wx.ID_ANY, label='del', flog=wx.BU_EXACTFIT )
    table.Add(del_button, 0, wx.ALL|wx.CENTER, 1 )

    constraint_dialog.vbox.Add( table, 0, wx.ALL|wx.EXPAND|wx.CENTER, 3 )

###    del_button.connect('clicked', lambda act, tab, box: box.remove(tab), 
###                       table, constraint_dialog.vbox)
#    table.show_all()
#    constraint_dialog.vbox.pack_end(table)    



def user_constraint_response(self, action, response, dialog, fit_dialog):
  '''
    Response to the user_constraint_dialog actions.
  '''
  print 'refl_fit_functions.py: entry user_constraint_response: response      = ',response
  def del_button_clicked( evt, box, tab):
    print 'Entry del Button clicked'
    print 'evt = ', evt
    print 'tab = ', tab
    print 'box = ', box

#   siehe manPage wxSizer::Remove  NB
#    for child in tab.GetChildren():
#        cw = child.GetWindow() 
#        rc = tab.Detach( cw )
#        cw.Destroy()  
#    oder einfacher:

    tab.Clear(True)

    rc = box.Remove(tab)
    box.Layout()



  if response==2:

    table = wx.BoxSizer( wx.HORIZONTAL )
    print 'table = ', table
    print 'table childs = ', table.GetChildren()
    text  = wx.StaticText( dialog, label='[' )
    table.Add( text, 0, wx.CENTER|wx.EXPAND, 3)
    entry = wx.TextCtrl( dialog, wx.ID_ANY, style=wx.TE_PROCESS_ENTER )
    entry.SetMaxLength( 30 )
    table.Add( entry, 1, wx.CENTER|wx.EXPAND, 3 )
    text  = wx.StaticText( dialog, label=']' )
    table.Add( text, 0, wx.CENTER|wx.EXPAND, 3)
    del_button = wx.Button( dialog, wx.ID_ANY, label='del', style=wx.BU_EXACTFIT )
    table.Add( del_button, 0, wx.CENTER|wx.EXPAND, 3)
    dialog.vbox.Prepend( table, 0, wx.CENTER|wx.EXPAND, 3 )
    dialog.vbox.Layout()

    del_button.Bind(event=wx.EVT_BUTTON, handler=lambda evt, tab=table, box=dialog.vbox: del_button_clicked(evt, box, tab) )
    


  if response==1:
    self.fit_object.user_constraints=[]
    objects = dialog.vbox.GetChildren()
    print 'objects = ', objects
    for object in objects:
      if type(object) is wx.BoxSizer:
        for widget in object.GetChildren():
          if type(widget) is wx.TextCtrl:
            try:
              self.fit_object.user_constraints.append(map(int, widget.GetValue().split(',')))
            except ValueError:
              continue
    fit_dialog.SetReturnCode(5)

  if response!=2:
    dialog.Destroy()
  
#----------------------- GUI functions -----------------------

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