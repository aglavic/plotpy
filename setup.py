#!/usr/bin/env python
'''
  Script used for setup and installation perpose. 
  If all works the right way this should test the system environment for all dependencies.
'''

from sys import argv, prefix
from distutils.core import setup
from os import listdir
from os.path import join as join_path

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__license__ = "None"
__version__ = "0.6"
__email__ = "a.glavic@fz-juelich.de"

__py_modules__=['plot', 'plotting_gui', 'measurement_data_structure', 'measurement_data_plotting', 'fit_data']
__packages__=['config', 'read_data', 'sessions']

if 'sdist' in argv:
  versions_fit=True
  # Test if every file has the right version for distributing.
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
    modules=filter(lambda file: file[-3:]=='.py',listdir(package))
    modules.remove('__init__.py')
    for module in modules:
      mod=__import__(package + '.' + module[:-3], globals(), locals(), ['__version__'], -1)
      try:
        if mod.__version__!=__version__:
          print "File %s/%s.py has version %s not equal to distribution version %s." % (package, module, mod.__version__, __version__)
          versions_fit=False
      except AttributeError:
          print "File %s/%s.py has no version number." % (package, module)
          versions_fit=False
  if not versions_fit:
    answer=raw_input('Do you still want to distribute? (y/n): ')
    if answer!='y':
      exit()

__py_modules__.append('configobj')

# as the requires keyword from distutils is not working, we test for the dependencies ourselves.
if 'install' in argv:
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

setup(name='Plot',
      version=__version__,
      description='Program to plot measured data with Gnuplot.',
      author=__author__,
      author_email=__email__,
      url='http://www.fz-juelich.de',
      scripts=['plot.py'], 
      py_modules=__py_modules__, 
      packages=__packages__, 
      package_data={'config': ['squid_calibration', '*.dat', 'fit/fit.f90', 'fonts/*.ttf'], 
                    },
      requires=['pygtk', 'gobject', 'numpy', 'scipy'], #does not do anything
     )

