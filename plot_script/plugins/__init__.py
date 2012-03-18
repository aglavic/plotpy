# -*- coding: utf-8 -*-

'''
  Plot.py global plugins package. Scans the plugins folder for python files and imports them.
'''

import sys
import os
# Add this folder to python path
global_plugin_path=os.path.abspath(os.path.split(__file__)[0])
if not global_plugin_path in sys.path:
  sys.path.append(global_plugin_path)

global_plugins=[]
plugin_sources=os.listdir(global_plugin_path)
plugin_sources=filter(lambda file_name: file_name.endswith('.py'), plugin_sources)
for plugin_source in plugin_sources:
  plugin=__import__(plugin_source[:-3])
  global_plugins.append(plugin)