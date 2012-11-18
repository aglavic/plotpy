'''
  Module for usefull decorators e.g. for logging function calls, input and output.
'''

import inspect
import logging


#
# Help functions adopted from Michele Simionato's decorator module
# http://www.phyast.pitt.edu/~micheles/python/decorator.zip
#

def getinfo(func):
    """
      Returns an info dictionary containing:
      - name (the name of the function : str)
      - argnames (the names of the arguments : list)
      - defaults (the values of the default arguments : tuple)
      - signature (the signature : str)
      - doc (the docstring : str)
      - module (the module name : str)
      - dict (the function __dict__ : str)
    """
    assert inspect.ismethod(func) or inspect.isfunction(func)
    regargs, varargs, varkwargs, defaults=inspect.getargspec(func)
    argnames=list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    signature=inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")[1:-1]
    output=dict(name=func.__name__, argnames=argnames, signature=signature,
                defaults=func.func_defaults, doc=func.__doc__,
                module=func.__module__, dict=func.__dict__,
                globals=func.func_globals, closure=func.func_closure)
    return output

def update_wrapper(wrapper, wrapped, create=False):
    """
      An improvement over functools.update_wrapper. By default it works the
      same, but if the 'create' flag is set, generates a copy of the wrapper
      with the right signature and update the copy, not the original.
      Moreovoer, 'wrapped' can be a dictionary with keys 'name', 'doc', 'module',
      'dict', 'defaults'.
    """
    if isinstance(wrapped, dict):
        infodict=wrapped
    else: # assume wrapped is a function
        infodict=getinfo(wrapped)
    assert not '_wrapper_' in infodict["argnames"], \
           '"_wrapper_" is a reserved argument name!'
    if create: # create a brand new wrapper with the right signature
        src="lambda %(signature)s: _wrapper_(%(signature)s)"%infodict
        # import sys; print >> sys.stderr, src # for debugging purposes
        wrapper=eval(src, dict(_wrapper_=wrapper))
    try:
        wrapper.__name__=infodict['name']
    except: # Python version < 2.4
        pass
    wrapper.__doc__=infodict['doc']
    wrapper.__module__=infodict['module']
    wrapper.__dict__.update(infodict['dict'])
    wrapper.func_defaults=infodict['defaults']
    return wrapper


# the real meat is here
def _decorator(caller, func):
    infodict=getinfo(func)
    argnames=infodict['argnames']
    assert not ('_call_' in argnames or '_func_' in argnames), \
           'You cannot use _call_ or _func_ as argument names!'
    src="lambda %(signature)s: _call_(_func_, %(signature)s)"%infodict
    dec_func=eval(src, dict(_func_=func, _call_=caller))
    return update_wrapper(dec_func, func)

def decorator(caller):
    """
    General purpose decorator factory: takes a caller function as
    input and returns a decorator with the same attributes.
    """
    return update_wrapper(lambda f : _decorator(caller, f), caller)


########################### Decorators for logging ##################################

logger=None
# if the logger is None only very small overhead is add to the function call
# for logging to the file the overhead is about 0.1ms per call

def start_log(log_file):
  global logger
  file_handle=logging.FileHandler(log_file, 'w')
  file_handle.setLevel(logging.DEBUG)
  formatter=logging.Formatter("%(asctime)26s %(levelname) 8s %(message)s")
  # add formatter to ch
  file_handle.setFormatter(formatter)
  logger=logging.getLogger()
  logger.setLevel(logging.DEBUG)
  logger.addHandler(file_handle)

def _nicetype(item):
  if 'array' in type(item).__name__:
    return type(item).__name__+("[%s]"%str(item.shape))
  elif type(item) in [list, tuple]:
    return type(item).__name__+('[%i]'%len(item))
  else:
    return type(item).__name__

@decorator
def log_call(func, *args, **kw):
  '''
    Decoratore to log a method call.
  '''
  if logger is None:
    return func(*args, **kw)
  infodict=getinfo(func)
  if len(infodict['argnames'])>0 and infodict['argnames'][0]=='self':
    logger.debug('call to %s.%s.%s'%(infodict['module'], args[0].__class__.__name__, infodict['name']))
  else:
    logger.debug('call to %s.%s'%(infodict['module'], infodict['name']))
  return func(*args, **kw)

@decorator
def log_input(func, *args, **kw):
  '''
    Decoratore to log a method call with input.
  '''
  if logger is None:
    return func(*args, **kw)
  infodict=getinfo(func)
  if len(infodict['argnames'])>0 and infodict['argnames'][0]=='self':
    logstr='call to %s.%s.%s('%(infodict['module'], args[0].__class__.__name__, infodict['name'])
    method=True
  else:
    logstr='call to %s.%s('%(infodict['module'], infodict['name'])
    method=False
  for i, arg in enumerate(args):
    if i==0 and method:
      continue
    value=repr(arg)
    value_split=value.splitlines()
    if len(value_split)>5:
      value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
    logstr+='\n'+'% 10s=%15s (%s)'%(infodict['argnames'][i], value, _nicetype(arg))
  for key, arg in sorted(kw.items()):
    value=repr(arg)
    value_split=value.splitlines()
    if len(value_split)>5:
      value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
    logstr+='\n'+'% 10s=%15s (%s)'%(key, repr(value), _nicetype(arg))
  logstr+='\n)'
  logstr=logstr.replace('\n', '\n'+' '*44)
  logger.debug(logstr)
  return func(*args, **kw)

@decorator
def log_output(func, *args, **kw):
  '''
    Decoratore to log a method call with output. If combined with log_input
    the input is logged at the time before the call and the output after.
  '''
  if logger is None:
    return func(*args, **kw)
  output=func(*args, **kw)
  infodict=getinfo(func)
  if len(infodict['argnames'])>0 and infodict['argnames'][0]=='self':
    logstr='return from %s.%s.%s'%(infodict['module'], args[0].__class__.__name__, infodict['name'])
  else:
    logstr='return from %s.%s'%(infodict['module'], infodict['name'])
  value=repr(output)
  value_split=value.splitlines()
  if len(value_split)>5:
    value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
  logstr+='\n-> %15s (%s)'%(value, _nicetype(output))
  logstr=logstr.replace('\n', '\n'+' '*44)
  logger.debug(logstr)
  return output

@decorator
def log_both(func, *args, **kw):
  '''
    Decoratore to log a method call with input and output.
  '''
  if logger is None:
    return func(*args, **kw)
  infodict=getinfo(func)
  if len(infodict['argnames'])>0 and infodict['argnames'][0]=='self':
    logstr='call to %s.%s.%s('%(infodict['module'], args[0].__class__.__name__, infodict['name'])
    method=True
  else:
    logstr='call to %s.%s('%(infodict['module'], infodict['name'])
    method=False
  for i, arg in enumerate(args):
    if i==0 and method:
      continue
    value=repr(arg)
    value_split=value.splitlines()
    if len(value_split)>5:
      value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
    logstr+='\n'+'% 10s=%15s (%s)'%(infodict['argnames'][i], value, _nicetype(arg))
  for key, arg in sorted(kw.items()):
    value=repr(arg)
    value_split=value.splitlines()
    if len(value_split)>5:
      value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
    logstr+='\n'+'% 10s=%15s (%s)'%(key, repr(value), _nicetype(arg))
  logstr+='\n)'
  logstr=logstr.replace('\n', '\n'+' '*44)
  logger.debug(logstr)
  # call the function
  output=func(*args, **kw)
  infodict=getinfo(func)
  if len(infodict['argnames'])>0 and infodict['argnames'][0]=='self':
    logstr='return from %s.%s.%s'%(infodict['module'], args[0].__class__.__name__, infodict['name'])
  else:
    logstr='return from %s.%s'%(infodict['module'], infodict['name'])
  value=repr(output)
  value_split=value.splitlines()
  if len(value_split)>5:
    value="\n".join(value_split[:2]+[' '*(len(value_split[1])/2)+'...']+value_split[-2:])
  logstr+='\n-> %15s (%s)'%(value, _nicetype(output))
  logstr=logstr.replace('\n', '\n'+' '*44)
  logger.debug(logstr)
  return output

######################## User function handling #############################

class user_menu(object):
  '''
    Class to store and process functions to be used with AutoDialog creation.
    The class is not instantiated, calling it will add a function to it as
    the user_menu.add_function method does. This makes it possible
    to use the class as decorator to functions in e.g. plugins, therfore
    the normal naminc convention of classes is not applied here.
    
    Functions are added using:
      user_menu.add_function(function, menu_entry=None,
                                   description=None, shortcut=None)
  '''
  # for easier reading of the code, the convention using cls for class
  # is replaced by using self instead
  registered_functions=[]
  main_gui=None

  def __new__(self, function, menu_entry=None, description=None, shortcut=None):
    # calling FunctionHandler returns the function itself
    # this makes it possible to use it as a decorator
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
    return function

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
    # import only on call to make this decorator work in plugins even
    # when GTK is not used
    from plotpy.gtkgui.autodialogs import AutoDialog
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

class plugin_menu(object):
  """
    Decorator class to easily define entries in the plugins menu.
    The function parameters determine which information is passed
    to it, when called. Any parameter of gui, dataset and session
    is allowed.
    
    The return value determines further actions, e.g. if a new
    dataset should be added. There are three different return
    values allowed for such a function:
      * None - no further action is performed
      * MeasurementData or derived type instance - the dataset is
        appended to the active file and plotted.
      * Tuple of ("name", [dataset1, ...]) - A new file_data entry
        is created and the first plot in it is shown.
    
    Usage example:
    
      @plugin_menu
      def do_replot(gui):
        gui.replot()
  """
  registered_items={}
  registered_main_items={}

  def __init__(self, entry_name, submenu=None):
    self.entry_name=entry_name
    self.submenu=submenu

  def __call__(self, function):
    '''
      Add menu entry for the function by altering
      the globals in the module there the function
      comes from. Therfoer this decorator only
      works inside a plugin module.
    '''
    return function

  @classmethod
  def menu(self, gui, session):
    '''
      Called by the gui to create the plugins menu.
    '''
    self._gui=gui
    self._session=session
    string=''
    # Create actions for the menu
    actions=[]
    for name, ignore in sorted(self.registered_main_items.items()):
      string+="       <menuitem action='%s' />\n"%name
      actions.append((name, None, name, None, None, self.call_function))
    for submenu, items in sorted(self.registered_items.items()):
      string+="    <menu action='%s'>\n"%submenu
      actions.append((submenu, None, submenu, None, None, None))
      for name, ignore in sorted(items.items()):
        string+="       <menuitem action='%s-%s' />\n"%(submenu, name)
        actions.append(("%s-%s"%(submenu, name), None, name, None, None, self.call_function))
      string+="    </menu>\n"
    return string, tuple(actions)

  def call_function(self, action, widget):
    action_name=action.get_name()

######################### General decorators ###############################

class check_input(object):
  '''
    Decorator checking the input to a function.
  '''
  try_convert=True
  types=[]

  def __init__(self, types, try_convert=True):
    self.types=types
    self.try_convert=try_convert

  def __call__(self, func):
    infodict=getinfo(func)
    argnames=infodict['argnames']
    assert not ('_call_' in argnames or '_func_' in argnames), \
           'You cannot use _call_ or _func_ as argument names!'
    src="def dec_func(%(signature)s):"%infodict
    for i, typei in enumerate(self.types):
      src+='\n  if type(%s).__name__!="%s":'%(argnames[i], typei.__name__)
      if self.try_convert:
        src+='\n    try:'
        src+='\n      %s=%s(%s)'%(argnames[i], typei.__name__, argnames[i])
        src+='\n    except:'
        src+='\n      raise ValueError, "type of %s is not %s"'%(argnames[i], typei.__name__)
      else:
        src+='\n    raise ValueError, "type of %s is not %s"'%(argnames[i], typei.__name__)
    src+='\n  return _func_(%(signature)s)'%infodict
    exec_dict=dict(_func_=func, _call_=self.__call__)
    exec(src, exec_dict)
    return update_wrapper(exec_dict['dec_func'], func)

# test decorators for future applications
def test(func):
  '''
    Put the function as private and call it with the returned function
    while adding an additional argument. The docstring is altered to
    point to the private function.
  '''
  infodict=getinfo(func)
  infodict['globals']['_'+infodict['name']]=func
  infodict['signature']=', '.join(infodict['signature'].split(', ')[1:])
  src="lambda %(signature)s: _%(name)s(None, %(signature)s)"%infodict
  dec_func=eval(src, infodict['globals'])
  dec_func.__name__=infodict['name']
  if infodict['doc'] is  None:
    infodict['doc']=''
  dec_func.__doc__=infodict['doc']+'''
  This is a wrappter to the function _%s.'''%infodict['name']
  dec_func.__module__=infodict['module']
  dec_func.__dict__.update(infodict['dict'])
  dec_func.func_defaults=infodict['defaults']
  return dec_func

testdict={}
def test1(func):
  '''
    Register function call inputs.
  '''
  infodict=getinfo(func)
  testdict[infodict['name']]=[]
  infodict['arglist']='['+', '.join(infodict['argnames'])+']'
  src='''
def dec_func(%(signature)s):
  calldict['%(name)s'].append(%(arglist)s)
  return _func_(%(signature)s)
  '''%infodict
  exec_dict=dict(_func_=func, calldict=testdict)
  exec(src, exec_dict)
  return update_wrapper(exec_dict['dec_func'], func)
