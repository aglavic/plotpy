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

# Add this folder to python path
global_plugin_path=os.path.abspath(os.path.split(__file__)[0])
if not global_plugin_path in sys.path:
  sys.path.append(global_plugin_path)

__all__=[]

# plugins from the program folder
global_plugins=[]
plugin_sources=os.listdir(global_plugin_path)
plugin_sources=filter(lambda file_name: file_name.endswith('.py'), plugin_sources)
for plugin_source in plugin_sources:
  if plugin_source.startswith('_'):
    continue
  try:
    plugin=__import__('plotpy.plugins.'+plugin_source[:-3], fromlist=[plugin_source[:-3]])
  except ImportError, error:
    print "Error importing plugin %s, skipped. Error message: %s"%(plugin_source, error)
  else:
    global_plugins.append(plugin)
    exec '%s=plugin'%plugin_source[:-3]
    __all__.append(plugin_source[:-3])

# plugins from the user folder
user_plugins=[]
user_folder=os.path.join(os.path.expanduser('~'), '.plotting_gui')
if os.path.exists(user_folder) and os.path.exists(os.path.join(user_folder, 'plugins')):
  if not os.path.join(user_folder, 'plugins') in sys.path:
    sys.path.append(os.path.join(user_folder, 'plugins'))
  plugin_sources=os.listdir(os.path.join(user_folder, 'plugins'))
  plugin_sources=filter(lambda file_: file_.endswith('.py'), plugin_sources)
  for plugin_source in plugin_sources:
    if plugin_source.startswith('_'):
      continue
    try:
      plugin=__import__(plugin_source[:-3])
    except ImportError, error:
      print "Error importing plugin %s, skipped. Error message: %s"%(plugin_source, error)
    else:
      user_plugins.append(plugin)
      exec '%s=plugin'%plugin_source[:-3]
      __all__.append(plugin_source[:-3])


all_plugins=global_plugins+user_plugins
