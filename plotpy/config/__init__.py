# -*- encoding: utf-8 -*-
'''
  Package containing configuration modules.
  This folder contains all files which define constants and parameters
  for the plot and diverse import modes of plotpy.
  
  The config package facilitates a special ConfigProxy interface that
  acts like a dictionary, which is automatically generated from the
  submodules. Constants (variables using only capital letters) are
  directly taken from the module, others are first taken from the
  module and than stored in a user config file defined by the
  "config_file" variable in the module and read from there on the
  next import. To get access to the configuration other modules
  only need to import the module name, which can be either
  used as dictionary or by accessing the objects attributes.
  
  For example the module "user1" could look like this::
    
    # module docstring
    config_file="user"
    CONST1=12.3
    CONST2=431.2
    opt1=12
    opt2=1
  
  The module that wants to use these information will be similar to::
  
    from plotpy.config import user1config
    
    print user1.CONS1 # directly read from module
    print user1['opt1'] # first time read from module than from user.ini file
    
  If the module does not define the 'config_file' variable it is treated as
  a normal module, if it is None the storage is just temporary and if it
  is the empty string it will use the default config file.
'''

import os as _os
import pkgutil as _pkgutil
from baseconfig import ConfigProxy as _ConfigProxy
from plotpy.message import warn as _warn

user_config={} # remove when fixed

_package_dir=_os.path.split(_os.path.abspath(__file__))[0]

# prepare user config, if it does not exist
_config_path=_os.path.expanduser('~/.plotting_gui')
if not _os.path.exists(_config_path):
  _os.mkdir(_config_path)
# define ipython config path to seperate it from normal ipython configuration
_os.environ['IPYTHONDIR']=_os.path.join(_config_path, 'ipython')

proxy=None
__all__=[]

def _create_proxy():
  global proxy, __all__
  proxy=_ConfigProxy(_config_path)
  for ignore, name, ispackage in _pkgutil.iter_modules([_package_dir]):
    if ispackage or name=='baseconfig':
      continue
    try:
      modi=__import__('plotpy.config.'+name, fromlist=[name])
    except Exception, error:
      _warn("Could not import module %s,\n %s: %s"%(name, error.__class__.__name__, error))
      continue
    if 'config_file' in modi.__dict__:
      moddict={}
      for key, value in modi.__dict__.items():
        if key.startswith('_') or key=='config_file' or\
           hasattr(value, '__file__') or hasattr(value, '__module__'):
          continue
        moddict[key]=value
      config_holder=proxy.add_config(name, moddict, storage=modi.config_file) #@UnusedVariable
    else:
      # if config_file is not defined in the module, just use the module itself
      config_holder=modi #@UnusedVariable
    # add item to the package
    __all__.append(name)
    exec "global %s;%s=config_holder"%(name, name)

if proxy is None:
  _create_proxy()
