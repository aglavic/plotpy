# -*- encoding: utf-8 -*-
'''
  Package containing configuration moduls.
  This folder containes all files which define constants and parameters
  for the plot and diverse import modes of plot.py.
'''

from plotpy.info import __copyright__, __license__, __version__, \
                                    __maintainer__, __email__

# as the configuration files could be in a folder without user write access,
# we test if it is possible to write to the configuration folder and otherwise
# copy the files to our home directory and relink the module. This makes
# user specific config files possible as well.
import os

config_path=os.path.expanduser('~/.plotting_gui')
os.environ['IPYTHONDIR']=os.path.join(config_path, 'ipython')
if not os.path.exists(config_path):
  os.mkdir(config_path)
#if not os.access(__path__[0], os.W_OK):
#  user_path=os.path.join(config_path, 'config')
#  if not os.path.exists(user_path):
#    os.mkdir(user_path)
#  # create new config files if the script version is newer
#  try:
#    if not os.path.exists(os.path.join(user_path, "gnuplot_preferences.py")) or \
#        os.path.getmtime(os.path.join(user_path, "gnuplot_preferences.py"))<os.path.getmtime(os.path.abspath(__file__)):
#        # copy all files to the users directory
#        files=filter(lambda file_: file_.endswith('.py'), os.listdir(__path__[0]))
#        for file_ in files:
#          from_name=os.path.join(__path__[0], file_)
#          to_name=os.path.join(user_path, file_)
#          open(to_name, 'wb').write(open(from_name, 'rb').read())
#  except Exception, error:
#    raise error
#    # if the files are not present or accessible, use the variables to create them
#    def typecheck():
#      pass
#    subpackage_items=[
#                       'circle',
#                       'diamagnetism_table',
#                       'dns',
#                       'gnuplot_preferences',
#                       'gui',
#                       'in12',
#                       'kws2',
#                       'maria',
#                       'reflectometer',
#                       'scattering_length_table',
#                       'squid',
#                       'templates',
#                       'transformations',
#                       'treff',
#                       ]
#    for package in subpackage_items:
#      active_config=__import__('plotpy.config.'+package, fromlist=[package])
#      export_file=open(os.path.join(user_path, package+'.py'), 'w')
#      variables=filter(lambda item: '__' not in item, dir(active_config))
#      for name in variables:
#        if type(getattr(active_config, name)) is type(typecheck) or \
#          type(getattr(active_config, name)) is type(os):
#          continue
#        export_file.write('%s = %s\n'%(name, getattr(active_config, name).__repr__()))
#      # for code executed when importing the modules we would loose information
#      # so this code is doubled in the __configadd__ variable.
#      if '__configadd__' in dir(active_config):
#        export_file.write(active_config.__configadd__)
#      export_file.close()
#  # reassociate this module to use the user files
#  __path__=[user_path] #@ReservedAssignment


# load user config, it will be saved automatically on exit
from configobj import ConfigObj
import atexit

user_config=ConfigObj(os.path.join(config_path, 'user_config.ini'),
                        unrepr=True, indent_type='    ')
user_config['last_access_version']=__version__
atexit.register(user_config.write)
