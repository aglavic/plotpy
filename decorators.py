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
    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)
    argnames = list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")[1:-1]
    return dict(name=func.__name__, argnames=argnames, signature=signature,
                defaults = func.func_defaults, doc=func.__doc__,
                module=func.__module__, dict=func.__dict__,
                globals=func.func_globals, closure=func.func_closure)

def update_wrapper(wrapper, wrapped, create=False):
    """
      An improvement over functools.update_wrapper. By default it works the
      same, but if the 'create' flag is set, generates a copy of the wrapper
      with the right signature and update the copy, not the original.
      Moreovoer, 'wrapped' can be a dictionary with keys 'name', 'doc', 'module',
      'dict', 'defaults'.
    """
    if isinstance(wrapped, dict):
        infodict = wrapped
    else: # assume wrapped is a function
        infodict = getinfo(wrapped)
    assert not '_wrapper_' in infodict["argnames"], \
           '"_wrapper_" is a reserved argument name!'
    if create: # create a brand new wrapper with the right signature
        src = "lambda %(signature)s: _wrapper_(%(signature)s)" % infodict
        # import sys; print >> sys.stderr, src # for debugging purposes
        wrapper = eval(src, dict(_wrapper_=wrapper))        
    try:
        wrapper.__name__ = infodict['name']
    except: # Python version < 2.4
        pass
    wrapper.__doc__ = infodict['doc']
    wrapper.__module__ = infodict['module']
    wrapper.__dict__.update(infodict['dict'])
    wrapper.func_defaults = infodict['defaults']
    return wrapper

# the real meat is here
def _decorator(caller, func):
    infodict = getinfo(func)
    argnames = infodict['argnames']
    assert not ('_call_' in argnames or '_func_' in argnames), \
           'You cannot use _call_ or _func_ as argument names!'
    src = "lambda %(signature)s: _call_(_func_, %(signature)s)" % infodict
    dec_func = eval(src, dict(_func_=func, _call_=caller))
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
  formatter = logging.Formatter("%(asctime)26s %(levelname) 8s %(message)s")
  # add formatter to ch
  file_handle.setFormatter(formatter)  
  logger=logging.getLogger()
  logger.setLevel(logging.DEBUG)
  logger.addHandler(file_handle)

@decorator
def log_call(func, *args, **kw):
  '''
    Decoratore to log a method call.
  '''
  if logger is None:
    return func(*args, **kw)
  infodict=getinfo(func)
  if inspect.ismethod(func):
    infodict['name']=func.im_class.__name__+'.'+infodict['name']
  logger.debug('call to %s.%s' % (infodict['module'], infodict['name']))
  return func(*args, **kw)

@decorator
def log_input(func, *args, **kw):
  '''
    Decoratore to log a method call with input.
  '''
  if logger is None:
    return func(*args, **kw)
  infodict=getinfo(func)
  if inspect.ismethod(func):
    infodict['name']=func.im_class.__name__+'.'+infodict['name']
  logstr='call to %s.%s(' % (infodict['module'], infodict['name'])
  for i, arg in enumerate(args):
    logstr+='\n'+' '*36+'% 10s=%15s (%s)' % (infodict['argnames'][i], str(arg), type(arg).__name__)
  for key, value in sorted(kw.items()):
    logstr+='\n'+' '*36+'% 10s=%15s (%s)' % (key, str(value), type(value).__name__)
  logstr+='\n'+' '*36+')'
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
  logstr='return from %s.%s' % (infodict['module'], infodict['name'])
  logstr+='\n'+' '*44+'-> %15s (%s)' % (str(output), type(output).__name__)
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
  if inspect.ismethod(func):
    infodict['name']=func.im_class.__name__+'.'+infodict['name']
  logstr='call to %s.%s(' % (infodict['module'], infodict['name'])
  for i, arg in enumerate(args):
    logstr+='\n'+' '*36+'% 10s=%15s (%s)' % (infodict['argnames'][i], str(arg), type(arg).__name__)
  for key, value in sorted(kw.items()):
    logstr+='\n'+' '*36+'% 10s=%15s (%s)' % (key, str(value), type(value).__name__)
  logstr+='\n'+' '*36+')'
  logger.debug(logstr)
  # call the function
  output=func(*args, **kw)
  infodict=getinfo(func)
  logstr='return from %s.%s' % (infodict['module'], infodict['name'])
  logstr+='\n'+' '*44+'-> %15s (%s)' % (str(output), type(output).__name__)
  logger.debug(logstr)
  return output

########################## General decorators ###############################

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
    src="def dec_func(%(signature)s):" % infodict
    for i, typei in enumerate(self.types):
      src+='\n  if type(%s).__name__!="%s":' % (argnames[i], typei.__name__)
      if self.try_convert:
        src+='\n    try:'
        src+='\n      %s=%s(%s)' % (argnames[i], typei.__name__, argnames[i])
        src+='\n    except:'
        src+='\n      raise ValueError, "type of %s is not %s"' % (argnames[i], typei.__name__)
      else:
        src+='\n    raise ValueError, "type of %s is not %s"' % (argnames[i], typei.__name__)
    src+='\n  return _func_(%(signature)s)' % infodict
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
  src = "lambda %(signature)s: _%(name)s(None, %(signature)s)" % infodict
  dec_func = eval(src, infodict['globals'])
  dec_func.__name__ = infodict['name']
  if infodict['doc'] is  None:
    infodict['doc']=''
  dec_func.__doc__ = infodict['doc'] + '''
  This is a wrappter to the function _%s.''' % infodict['name']
  dec_func.__module__ = infodict['module']
  dec_func.__dict__.update(infodict['dict'])
  dec_func.func_defaults = infodict['defaults']
  return dec_func

testdict={}
def test1(func):
  '''
    Register function call inputs.
  '''
  infodict=getinfo(func)
  testdict[infodict['name']]=[]
  infodict['arglist']='['+', '.join(infodict['argnames'])+']'
  src = '''
def dec_func(%(signature)s):
  calldict['%(name)s'].append(%(arglist)s)
  return _func_(%(signature)s)
  ''' % infodict
  exec_dict=dict(_func_=func, calldict=testdict)
  exec(src, exec_dict)
  return update_wrapper(exec_dict['dec_func'], func)
