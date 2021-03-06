'''
  Facility to auto-generate entry dialogs from function inspection.
'''

import gtk
from dialogs import VListEntry
import inspect

registered_functions=[]

class AutoDialog(gtk.Dialog):
  '''
    Dialog automatically generated from the inspection of an input function.
    Supplies text, number and list inputs dependent on the function arguments.
    
    The function should be defined as 
    def func(dataset, arg1=..., arg2=..., arg3=[...]):
       """
         :param arg1: Arg1 name - Arg1 description
         :param arg2: Arg2 name - Arg2 description
         :param arg3: [min:max] - Arg3 name - Arg3 description
       """
  '''
  parameters=None
  _active_buttons=False

  def __init__(self, function, description_text=None, *args, **opts):
    if not 'buttons' in opts:
      # when using the default buttons, connect each entry with the OK action
      opts['buttons']=('OK', 1, 'Cancel', 0)
      self._active_buttons=True
    gtk.Dialog.__init__(self, *args, **opts)
    self._build_dialog(function, description_text)

  def _build_dialog(self, function, description_text):
    '''
      Create entries in a list widget together with names and
      tooltips.
    '''
    self._analyze_function(function)
    table=gtk.Table(2, len(self.parameters)+1)
    table.show()
    if description_text is not None:
      text=gtk.Label(description_text+'\n')
      text.show()
      table.attach(text, 0, 2, 0, 1)
    self.vbox.add(table)
    self.entries=[]
    for i, item in enumerate(self.parameters):
      text=gtk.Label(item['name'])
      text.show()
      entry=self.get_entry(item)
      entry.show()
      if self._active_buttons:
        entry.connect('activate', lambda *ignore: self.response(1))
      self.entries.append(entry)
      if item['type'] is not list:
        table.attach(text, 0, 1, i+1, i+2)
        table.attach(entry, 1, 2, i+1, i+2)
      else:
        table.attach(entry, 0, 2, i+1, i+2)

  def _analyze_function(self, function):
    '''
      Inspect the function to get the parameter names, description,
      defaults and types.
    '''
    argspec=inspect.getargspec(function)
    skip_items=len(argspec.args)-len(argspec.defaults)
    if skip_items==0:
      raise ValueError, "function does not have the right form"
    parameters=[]
    doc_lines=function.__doc__.splitlines()
    doc_lines=map(str.strip, doc_lines)
    for arg, default in zip(argspec.args[skip_items:], argspec.defaults):
      item={'arg':arg, 'name': arg, 'description': '',
            'type': type(default), 'default': default,
            'numrange': (-1e30, 1e30)}
      arg_doc=':param %s:'%arg
      for line in doc_lines:
        if arg_doc in line:
          line=line.split(arg_doc, 1)[1].strip()
          if '[' in line and ']' in line:
            data, rline=line.split(']', 1)
            data=[data]+rline.split('-', 1)
          else:
            data=line.split('-', 1)
          if len(data)==1:
            item['description']=data[0]
          elif len(data)==2:
            item['name']=data[0].strip()
            item['description']=data[1].strip()
          elif len(data)==3:
            item['numrange']=map(float, data[0].lstrip('[ ').rstrip().split(':'))
            item['name']=data[1].strip()
            item['description']=data[2].strip()
          break
      parameters.append(item)
    self.parameters=parameters

  def get_entry(self, item):
    '''
      Return an entry widget dependent on the datatype of item. 
    '''
    if item['type']==int:
      entry=gtk.SpinButton(adjustment=gtk.Adjustment(value=item['default'],
                                                     lower=item['numrange'][0],
                                                     upper=item['numrange'][1],
                                                     step_incr=1, page_incr=10),
                           climb_rate=1, digits=0)
    elif item['type'] is float:
      entry=gtk.SpinButton(adjustment=gtk.Adjustment(value=item['default'],
                                                     lower=item['numrange'][0],
                                                     upper=item['numrange'][1],
                                                     step_incr=0.01, page_incr=1),
                           climb_rate=0.01, digits=6)
    elif item['type'] is str:
      entry=gtk.Entry()
      entry.set_text(item['default'])
    elif item['type'] is list:
      entry=VListEntry(list(item['default']), title=item['name'],
                             entry_type=type(item['default'][0]))
    else:
      raise ValueError, "only basic types are supported"
    entry.set_tooltip_text(item['description'])
    return entry

  def get_result(self):
    '''
      Return all parameters in a dictionary.
    '''
    result={}
    for item, entry in zip(self.parameters, self.entries):
      if item['type']==int:
        result[item['arg']]=entry.get_value_as_int()
      elif item['type'] is float:
        result[item['arg']]=entry.get_value()
      elif item['type'] is str:
        result[item['arg']]=entry.get_text()
      elif item['type'] is list:
        result[item['arg']]=entry.list_link
    return result

class FunctionHandler(object):
  '''
    Class to store and process functions to be used with AutoDialog creation.
    The class is not instantiated, calling it will add a function to as
    the FunctionHandler.add_function method does.
    
    Functions are added using:
      FunctionHandler.add_function(function, menu_entry=None,
                                   description=None, shortcut=None)
  '''
  # for easier reading of the code, the convention using cls for classmethods
  # is replaced by using self instead
  registered_functions=[]
  main_gui=None

  def __new__(self, function, menu_entry=None, description=None, shortcut=None):
    return self.add_function(function, menu_entry, description, shortcut)

  @classmethod
  def add_function(self, function, menu_entry=None, description=None, shortcut=None):
    '''
      Add a function to the list of available objects.
    '''
    if menu_entry is None:
      # if no menu entry is supplied, use the functions name
      # replacing underscores with spaces and using the first letter
      # in upper case
      fname=function.__name__
      menu_entry=fname[0].upper()+fname[1:].replace('_', ' ')+'...'
    if not self.check_function(function):
      raise ValueError, 'function does not have the right format'
    if function.__doc__ is None:
      function.__doc__=''
    # remove the former registered function if it was already registered
    known_funcs=[item[0].__name__ for item in self.registered_functions]
    if function.__name__ in known_funcs:
      self.registered_functions.pop(known_funcs.index(function.__name__))
    self.registered_functions.append((function, menu_entry, description, shortcut))

  @classmethod
  def check_function(self, function):
    '''
      Check the validity of the function argument specifications.
    '''
    argspec=inspect.getargspec(function)
    args=argspec.args
    if args[0]=='dataset':
      if argspec.defaults is not None and len(args)!=(1+len(argspec.defaults)):
        return False
      return True
    elif args[0]=='datasets':
      if args[1]!='d_index' or (argspec.defaults is not None and
                                len(args)!=(2+len(argspec.defaults))):
        return False
      return True
    else:
      return False

  @classmethod
  def get_menu_string(self):
    if len(self.registered_functions)==0:
      return ''
    else:
      output='''        </menu>
        <menu action='UserAddedMenu'>
    '''
      for function, ignore, ignore, ignore in self.registered_functions:
        output+='''          <menuitem action='%s'/>
        '''%function.__name__.replace('_', '')
      return output


  @classmethod
  def get_menu_actions(self):
    if len(self.registered_functions)==0:
      return ()
    else:
      output=[("UserAddedMenu", None, "User-Func.", None, None, None), ]
      for function, menu_entry, ignore, shortcut in self.registered_functions:
        output.append(
                      (function.__name__.replace('_', ''), None,
                       menu_entry, shortcut,
                       None, self.call_function)
                      )
      return tuple(output)

  @classmethod
  def call_function(self, action, main_window):
    '''
      Open AutoDialog and run the function with the given parameters.
    '''
    action_name=action.get_name()
    action_names=[item[0].__name__.replace('_', '') for item in self.registered_functions]
    action_index=action_names.index(action_name)
    function, menu_entry, description, ignore=self.registered_functions[action_index]
    argspec=inspect.getargspec(function)
    if argspec.defaults is None:
      args={}
      result=True
    else:
      dialog=AutoDialog(function, description_text=description, title=menu_entry)
      result=dialog.run()
      args=dialog.get_result()
      dialog.destroy()
    if result:
      datasets=main_window.active_session.active_file_data
      d_index=main_window.index_mess
      if argspec.args[0]=='dataset':
        result=function(datasets[d_index], **args)
      else:
        result=function(datasets, d_index, **args)
      if result is None:
        main_window.rebuild_menus()
        main_window.replot()
      else:
        datasets.append(result)
        main_window.index_mess=len(datasets)-1
        main_window.rebuild_menus()
        main_window.replot()


