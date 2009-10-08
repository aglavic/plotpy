#!/usr/bin/env python
'''
  Script used for setup and installation perpose. 
  If all works the right way this should test the system environment for all dependencies.
'''

import sys, os
from distutils.core import setup
import subprocess

# if python version < 2.5 set the sys.exit function as exit
if hex(sys.hexversion)<'0x2050000':
  exit=sys.exit

__name__='Plot-script'
__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__license__ = "None"
__version__ = "0.6b1"
__email__ = "a.glavic@fz-juelich.de"
__author_email__ = __email__
__url__ = "http://atzes.homeip.net/plotwiki"
__description__='''Program to plot measured data with Gnuplot. Provides a GUI interface, fitting and some other useful functionalities. Supported file types are 4circle (.spec)/MPMS,PPMS (.dat/.raw)/reflectometer (.UXD)/TREFF/IN12/DNS and can be widened with plugins.'''

__scripts__=['plot.py']
__py_modules__=['plot', 'plotting_gui', 'measurement_data_structure', 'measurement_data_plotting', 'fit_data', 'file_actions']
__packages__=['config', 'read_data', 'sessions', 'sessions.reflectometer_fit']
__package_data__={'config': ['squid_calibration', '*.dat', 'fit/fit.f90', 'fit/pnr_multi/*.f90', 'fonts/*.ttf'], 
                    }
__requires__=['pygtk', 'gobject', 'numpy', 'scipy']

script_files=['scripts/prd', 'scripts/psd', 'scripts/p4d', 'scripts/dnsplot', 'scripts/treffplot', 'scripts/pin12', 'scripts/plot_SQUID_data', 'scripts/plot_4circle_data', 'scripts/plot_reflectometer_data']
# creat windows batches for the script_files
win_batches=[script+'.bat' for script in script_files]
for script in script_files:
  line=open(script, 'r').readlines()[1]
  open(script+'.bat', 'w').write(line.replace('$', '%'))
__scripts__+=script_files+win_batches

# creat windows batches for the script_files

if ('install' in sys.argv) and (not 'win' in sys.platform) and len(sys.argv)==2:
  for lp in os.path.expandvars('$PATH').split(':'):
    for file in script_files:
      if os.path.exists(os.path.join(lp, file)) or\
        os.path.islink(os.path.join(lp, file)):
        if raw_input("%s exists, remove it first (Y/N)? " % os.path.join(lp, file)).lower() == 'y':
          os.remove(os.path.join(lp, file))
        else:
          continue

if 'install' not in sys.argv:
  if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

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
    modules=filter(lambda file: file[-3:]=='.py',os.listdir(package.replace(".", "/")))
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

# If binary distribution has been created rename it and create .deb package, too.
if ('bdist' in sys.argv):
  print "Moving distribution files..."
  os.chdir('archiv')
  os.rename(__name__+'-'+__version__+'-1.noarch.rpm', __name__+'-'+__version__+'.rpm')
  os.remove(__name__+'-'+__version__+'-1.src.rpm')
  os.rename(__name__+'-'+__version__+'.linux-x86_64.exe', __name__+'-'+__version__+'.exe')
  print "Creating debian folder..."
  subprocess.Popen(['fakeroot', 'alien', '-k', '-g', __name__+'-'+__version__+'.rpm'], shell=False, 
                   stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
  os.chdir(__name__+'-'+__version__)
  deb_con=open('debian/control', 'w')
  deb_con.write(open('../../deb_control', 'r').read())
  deb_con.close()
  print "Packaging for debian..."
  subprocess.Popen(['dpkg-buildpackage', '-i', '-I', '-rfakeroot'], shell=False, 
                   stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
  os.chdir('..')
  os.rename((__name__+'_'+__version__).lower()+'-1_all.deb', __name__+'-'+__version__+'.deb')
  print "Removing debian folder..."
  os.popen('rm '+__name__+'-'+__version__+' -r')
  os.popen('rm '+(__name__+'_'+__version__).lower()+'-1*')
  os.popen('rm '+(__name__+'_'+__version__).lower()+'.orig.tar.gz')

# In windows the scriptpath is not in the path by default
if ('install' in sys.argv) and len(sys.argv)==2:
  if ('win' in sys.platform):
    # Windows installation
    win_script_path=sys.prefix.lower() + '\\scripts'
    win_path=os.path.expandvars('$PATH').lower().split(';')
    if not win_script_path in win_path:
      print "Could not verify path!\nPlease be sure that '" + sys.prefix + "\scripts' is in your path."
  else:
    # Linux/OS-X installation
    py_sub_path=None
    for path_name in sys.path:
      if path_name != os.path.abspath(os.path.curdir) and \
          path_name != '' and \
          path_name !='.' and \
          os.path.exists(os.path.join(path_name, 'config', 'fit')):
        if py_sub_path:
          print "Second directory possible: %s , Skipping it!" % path_name
        py_sub_path=path_name
    try:
      # Make fit pathes writable for users to compile the fortran programs
      print "Setting mode 777 for %s/config/fit" % py_sub_path
      os.chmod(os.path.join(py_sub_path, 'config', 'fit'), 16895)
      print "Setting mode 777 for %s/config/fit/pnr_multi" % py_sub_path
      os.chmod(os.path.join(py_sub_path, 'config', 'fit', 'pnr_multi'), 16895)
    except OSError:
      pass
