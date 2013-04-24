#-*- coding: utf-8 -*-
'''
  Macro facility to log function calls for later use in script like macros. 
  The MacroProxy object handles all the magic and supplies several methods
  usable as decorators in other modules to easily allow definition of new macros.
  
  Example:
    from plotpy.macros import macro
    
    @macro.gui
    def my_function(gui, a, b, c='12'):
       .... do your stuff ....
    
    This will result in a function with signature "my_function(a, b, c='12')"
    while the gui object will be availble from within the function as if
    it was supplied during the call.
'''
from .decorators import update_wrapper, getinfo
from inspect import getmembers

class MacroProxy(object):
  '''
    Handles macro storage and function calls and supplies different methods
    to be used as decorators to functions that should be logged and call
    these functions with different arguments, depending on the selected method.
    
    The instance of MacroProxy can already been used from other modules
    before the session and gui parameters are set, actual calls to the
    wrapped functions before this initialization will yeald function
    calls with None instead of the expected parameters.
    
    MacroProxy.macro   - just logs the call with the given parameters
    MacroProxy.data    - calls the function with the currently active 
                         dataset as additional first argument
    MacroProxy.gui     - calls the function with the main window object
                         as additional first argument
    MacroProxy.session - adds the current active session as first argument
    MacroProxy.all     - adds three additional arguments to the call as 
                         data, gui and session combined.
  '''
  _session=None
  _gui=None
  # parameters overwritten on each call
  _next_name=None
  _next_gui=False
  _next_session=False
  _next_data=False
  _next_returns_dataset=False

  def __init__(self):
    self._wrapped_functions={} # all functions before wrapping
    self._wrapped_methods={} # all methods before wrapping
    self._wrapper_functions={} # all functions after wrapping
    self._wrapper_methods={} # all methods after wrapping
    self._wrapper_options={}
    self._known_macros={} # functions and methods activated as macros
    self._call_history=[] # each macro call will be added to this list

  def set_session(self, session):
    self._session=session
    self._known_macros=dict(self._wrapper_functions)
    # activate all macros based on the current session methods
    for ignore, member in getmembers(session):
      for key, wrapper in self._wrapper_methods.items():
        if hasattr(member, '__func__') and member.__func__ is wrapper:
          self._known_macros[key]=wrapper

  def set_gui(self, gui):
    self._gui=gui

  def clear(self):
    '''
      Empty the call history of the object.
    '''
    self._call_history=[]

  # The decorator methods do a lot of black magic not very easy to
  # follow. Basically this is to allow the resulting functions to
  # have a better signature and correct docstring.

  def _register(self, function, is_method=False):
    if self._next_name:
      key=self._next_name
      self._next_name=None
    else:
      key=function.__name__
    if key in self._wrapped_methods or key in self._wrapped_functions:
      raise ValueError, "There is already a macro with the name %s"%key
    if is_method:
      self._wrapped_methods[key]=function
    else:
      self._wrapped_functions[key]=function
    self._wrapper_options[key]=(self._next_gui, self._next_session, self._next_data,
                                self._next_returns_dataset)
    return key

  def _call_wrapper(self, key, args, opts):
    '''
      Gets called each time a macro is used and stores the call parameters as well
      as adding optional gui, session and data objects to them.
    '''
    options=self._wrapper_options[key]
    argadd=[]
    if options[0]: argadd.append(self._gui)
    if options[1]: argadd.append(self._session)
    if options[2]: argadd.append(self._gui.active_dataset)
    if key in self._wrapped_methods:
      self._call_history.append((key, args[1:], opts))
      # check if first call argument is the session instance, otherwise through error
      if args[0] is not self._session:
        raise ValueError, "Only methods of the current session are supported as macros"
      else:
        args=(args[0],)+tuple(argadd)+args[1:]
    else:
      self._call_history.append((key, args, opts))
      args=tuple(argadd)+args
    return args, opts

  def _handle_result(self, key, result):
    '''
      Perform specific actions for special methods results.
    '''
    if self._wrapper_options[key][3]:
      self._session.active_file_data.append(result)

  def _decorate(self, function):
    '''
      Wrap the function using the options set in the last call.
      To be able to use them as macros, only methods of a GenericSession
      derived class are supported, every other macros need to be
      defined as functions.
    '''
    # collect information about the function
    info=getinfo(function)
    if info['argnames'][0]=='self':
      # There is no way finding out which class the method will
      # belong to, so we store all methods until the session
      # instance is set and activate them afterwards.
      is_method=True
    else:
      is_method=False

    key=self._register(function, is_method)

    def wrapper(*args, **opts):
      args, opts=self._call_wrapper(key, args, opts)
      result=function(*args, **opts)
      self._handle_result(key, result)
      return result

    if is_method: remove_items=1
    else: remove_items=0
    for item in [self._next_gui, self._next_session, self._next_data]:
      if item: remove_items+=1

    # remove the first items from the function arguments of the wrapper
    # as they will automatically be supplied by tha macro object on call
    try:
      if is_method:
        info['signature']='self, '+info['signature'].split(',', remove_items)[remove_items]
      elif remove_items:
        info['signature']=info['signature'].split(',', remove_items)[remove_items]
    except IndexError:
      info['signature']=''

    src="lambda %(signature)s: _wrapper_(%(signature)s)"%info
    # import sys; print >> sys.stderr, src # for debugging purposes
    wrapper=update_wrapper(eval(src, dict(_wrapper_=wrapper)), function, create=False)
    if not is_method:
      self._known_macros[key]=wrapper
      self._wrapper_functions[key]=wrapper
    else:
      self._wrapper_methods[key]=wrapper
    return wrapper

  def __call__(self, function=None, name=None, gui=False, session=False, data=False,
               returns_data=False):
    '''
      Allows the object to be used as decorator, ither as is or by calling
      it with additional optoins:
      
      @macro
      def your_function(a,b):
        return a+b
      
      @macro(name='new_name', data=True)
      def old_name(data, a, b):
        return a+b
    '''
    self._next_name=name
    self._next_gui=gui
    self._next_session=session
    self._next_data=data
    self._next_returns_dataset=returns_data
    if function is not None:
      # if just used as decorator, scan the argument names to select options
      argnames=list(getinfo(function)['argnames'])
      if argnames[0]=='self': argnames.pop(0)
      if argnames[0]=='gui':
        self._next_gui=True
        argnames.pop(0)
      if argnames[0]=='session':
        self._next_session=True
        argnames.pop(0)
      if argnames[0]=='data':
        self._next_data=True
        self._next_returns_dataset=True
        argnames.pop(0)
      return self._decorate(function)
    else:
      return self._decorate


macro=MacroProxy()
