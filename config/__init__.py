#!/usr/bin/env python
'''
  Package containing configuration moduls.
  This folder containes all files which define constants and parameters
  for the plot and diverse import modes of plot.py.
'''

# as the configuration files could be in a folder without user write access,
# we test if it is possible to write to the configuration path and otherwise
# copy the files to out home directory and relink the module.
import os

if not os.access('config', os.W_OK):
  config_path=os.path.expanduser('~/.plotting_gui')
  user_path=os.path.join(config_path, 'config')
  if not os.path.exists(config_path):
    os.mkdir(config_path)
  if not os.path.exists(user_path):
    os.mkdir(user_path)
    # copy all files to the users directory
    files=filter(lambda file: file.endswith('.py'), os.listdir(__path__[0]))
    for file in files:
      from_name=os.path.join(__path__[0], file)
      to_name=os.path.join(user_path, file)
      open(to_name, 'wb').write(open(from_name, 'rb').read())
  # reassociate this module to use the user files
  __path__=[user_path]
