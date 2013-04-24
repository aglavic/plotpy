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
  _name_overwrite=None
  
  def __init__(self):
    self._wrapped_functions={}
    self._wrappers={}
    self._call_history=[]
    
  def set_params(self, session, gui):
    self._session=session
    self._gui=gui
  
  def clear(self):
    '''
      Empty the call history of the object.
    '''
    self._call_history=[]
  
  # The decorator methods do a lot of black magic not very easy to
  # follow. Basically this is to allow the resulting functions to
  # have a better signature and correct docstring.
  
  def _register(self, item, function):
    if self._name_overwrite:
      key=self._name_overwrite
      self._name_overwrite=None
    else:
      key=function.__name__
    if key in self._wrapped_functions:
      raise ValueError, "There is already a macro with the name %s"%key
    self._wrapped_functions[key]=('macro', function)
    return key
  
  def macro(self, function):
    '''
    Create a macro function, which is just loged upon calling.
    '''
    key=self._register('macro', function)
    def wrapper(*args, **opts):
      self._register_call(key, args, opts)
      return function(*args, **opts)
    self._wrappers[key]=wrapper
    return update_wrapper(wrapper, function, create=True)
  
  def data(self, function):
    '''
    Create a macro function, which loggs the input and adds the gui object as
    first argument to the call. The returned function is reduced in it's signature
    by it's first argument.
    '''
    key=self._register('data', function)
    infodict=getinfo(function)
    if infodict['signature'].startswith('self'):
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(args[0], self._gui.measurement, *args[1:], **opts)
      infodict['signature']='self, '+infodict['signature'].split(',', 2)[2]
    else:
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(self._gui.measurement, *args, **opts)
      infodict['signature']=infodict['signature'].split(',', 1)[1]
    self._wrappers[key]=wrapper
    src="lambda %(signature)s: _wrapper_(%(signature)s)"%infodict
    # import sys; print >> sys.stderr, src # for debugging purposes
    wrapper=eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(wrapper, function, create=False)
  
  def gui(self, function):
    '''
    Create a macro function, which loggs the input and adds the gui object as
    first argument to the call. The returned function is reduced in it's signature
    by it's first argument.
    '''
    key=self._register('gui', function)
    infodict=getinfo(function)
    if infodict['signature'].startswith('self'):
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(args[0], self._gui, *args[1:], **opts)
      infodict['signature']='self, '+infodict['signature'].split(',', 2)[2]
    else:
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(self._gui, *args, **opts)
      infodict['signature']=infodict['signature'].split(',', 1)[1]
    self._wrappers[key]=wrapper
    src="lambda %(signature)s: _wrapper_(%(signature)s)"%infodict
    # import sys; print >> sys.stderr, src # for debugging purposes
    wrapper=eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(wrapper, function, create=False)
  
  def session(self, function):
    '''
    Create a macro function, which loggs the input and adds the gui object as
    first argument to the call. The returned function is reduced in it's signature
    by it's first argument.
    '''
    key=self._register('session', function)
    infodict=getinfo(function)
    if infodict['signature'].startswith('self'):
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(args[0], self._session, *args[1:], **opts)
      infodict['signature']='self, '+infodict['signature'].split(',', 2)[2]
    else:
      def wrapper(*args, **opts):
        self._register_call(key, args, opts)
        return function(self._session, *args, **opts)
      infodict['signature']=infodict['signature'].split(',', 1)[1]
    self._wrappers[key]=wrapper
    src="lambda %(signature)s: _wrapper_(%(signature)s)"%infodict
    # import sys; print >> sys.stderr, src # for debugging purposes
    wrapper=eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(wrapper, function, create=False)
  
  def all(self, function):
    return function
  
  def _register_call(self, key, args, opts):
    self._call_history.append((key, args, opts))
  
  def __call__(self, type_, name=None):
    '''
      Allows a convenient way to overwrite default macro creation.
      Alters options for the next decorator method call and returns self
      so the object can be used e.g.:
      @macro('macro', name='new_name')
      def old_name(a,b):
        return a+b
    '''
    self._name_overwrite=name
    return getattr(self, type_)
    

macro=MacroProxy()
