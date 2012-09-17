# -*- coding: utf-8 -*-
'''
  Plot.py global plugins package. Scans the global and user plugins folder 
  for python files and imports them.
  
  To import all plugin modules directly use:
    from plotpy.plugins import * # import to namespace
     or
    from plotpy.plugins import all_plugins # import list of modules
'''

import sys
import os
import pkgutil
import imp
from plotpy.message import warn

__all__=[]

global_plugin_path=os.path.abspath(os.path.split(__file__)[0])
user_folder=os.path.join(os.path.expanduser('~'), '.plotting_gui', 'plugins')

# plugins from the program folder (also works if program package is in zip file)
global_plugins=[]
for ignore, name, ispackage in pkgutil.iter_modules([global_plugin_path]):
  try:
    plugin=__import__('plotpy.plugins.'+name, fromlist=[name])
  except ImportError, error:
    warn("Error importing plugin %s, skipped. Error message: %s"%(name, error))
  else:
    global_plugins.append(plugin)
    exec '%s=plugin'%name
    __all__.append(name)

# plugins from the user folder
user_plugins=[]
for loader, name, ispackage in pkgutil.iter_modules([user_folder]):
  try:
    # make sure user plugins are imported as submodules of 
    # the plotpy.plugins package
    moduleloader=loader.find_module(name)
    plugin=imp.load_source('plotpy.plugins.'+name, moduleloader.filename)
    plugin=__import__('plotpy.plugins.'+name, fromlist=[name])
  except ImportError, error:
    warn("Error importing plugin %s, skipped. Error message: %s"%(name, error))
  else:
    global_plugins.append(plugin)
    exec '%s=plugin'%name
    __all__.append(name)


all_plugins=global_plugins+user_plugins
