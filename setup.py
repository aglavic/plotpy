#!/usr/bin/env python
'''
  Script used for setup and installation perpose. 
  If all works the right way this should test the system environment for all dependencies.
'''

import sys, os
from distutils.core import setup

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__license__ = "None"
__version__ = "0.6"
__email__ = "a.glavic@fz-juelich.de"


__name__='Plot-script'
__scripts__=['plot.py']
__py_modules__=['plot', 'plotting_gui', 'measurement_data_structure', 'measurement_data_plotting', 'fit_data', 'file_actions']
__packages__=['config', 'read_data', 'sessions']
__package_data__={'config': ['squid_calibration', '*.dat', 'fit/fit.f90', 'fonts/*.ttf'], 
                    }
__url__='http://www.fz-juelich.de'
__requires__=['pygtk', 'gobject', 'numpy', 'scipy']
__description__='''Program to plot measured data with Gnuplot. 
Provides a GUI interface, fitting and some other useful functionalities.

Supported file types are 4circle (.spec)/MPMS,PPMS (.dat/.raw)/reflectometer (.UXD)/TREFF/IN12 and can be widened with plugins.'''

if 'sdist' in sys.argv:
  # Test if every file has the right version for distributing.
  # This is only to remind the developer to check all files for every new version.
  # If the versions do not match a beta is added to the version name of the distribution.
  versions_fit=True
  for module in __py_modules__:
    mod=__import__(module, globals(), locals(), ['__version__'], -1)
    try:
      if mod.__version__!=__version__:
        print "File %s.py has version %s not equal to distribution version %s." % (module, mod.__version__, __version__)
        versions_fit=False
    except AttributeError:
        print "File %s.py has no version number." % (module)
        versions_fit=False
  # test modules in packages
  for package in __packages__:
    modules=filter(lambda file: file[-3:]=='.py',os.listdir(package))
    modules.remove('__init__.py')
    for module in modules:
      mod=__import__(package + '.' + module[:-3], globals(), locals(), ['__version__'], -1)
      try:
        if mod.__version__!=__version__:
          print "File %s/%s has version %s not equal to distribution version %s." % (package, module, mod.__version__, __version__)
          versions_fit=False
      except AttributeError:
          print "File %s/%s.py has no version number." % (package, module)
          versions_fit=False
  if not versions_fit:
    answer=raw_input('Not all file versions match the distribution version.\nDo you still want to distribute as alpha/beta/normal/cancel? (a/b/y/any): ')
    if answer=='a':
      __version__=__version__ + 'alpha'
    elif answer=='b':
      __version__=__version__ + 'beta'
    elif answer!='y':
      exit()

__py_modules__.append('configobj')

# as the requires keyword from distutils is not working, we test for the dependencies ourselves.
if 'install' in sys.argv:
  dependencies_ok=True
  print "Testing all dependencies."
  # call linux and windows gnuplot command with --help option to test if it can be called.
  import subprocess
  try:
    subprocess.Popen(['gnuplot','--help'], shell=False,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
    gnuplot=True
  except OSError:
    try:
      subprocess.Popen(['pgnuplot','--help'], shell=False,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
      gnuplot=True
    except OSError:
      print "Gnuplot must be installed to use this program."
      gnuplot=False
      dependencies_ok=False
  # GUI dependencies
  try:
    import gobject
    import gtk
  except ImportError:
    print "PyGTK with gobject has to be installes."
    dependencies_ok=False
  # fitting dependencies, not crucial
  try:
    import numpy
    import scipy
  except ImportError:
    print "For fitting to work, numpy and scipy have to be installed."
    dependencies_ok=False
  if not dependencies_ok:
    answer=raw_input('Do you still want to install? (y/n): ')
    if answer!='y':
      exit()


setup(name=__name__,
      version=__version__,
      description=__description__,
      author=__author__,
      author_email=__email__,
      url=__url__,
      scripts=__scripts__, 
      py_modules=__py_modules__, 
      packages=__packages__, 
      package_data=__package_data__,
      requires=__requires__, #does not do anything
     )

# In windows the scriptpath is not in the path by default
if ('install' in sys.argv) and ('win' in sys.platform):
  win_script_path=sys.prefix.lower() + '\\scripts'
  win_path=os.path.expandvars('$PATH').lower().split(';')
  if not win_script_path in win_path:
    print "Could not verify path!\nPlease be sure that '" + sys.prefix + "\scripts' is in your path."
  
