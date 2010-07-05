# -*- encoding: utf-8 -*-
'''
  Script used for setup and installation purpose. 
  If all works the right way this should test the system environment for all dependencies and create source and binary distributions.
'''

import sys, os
exit=sys.exit
from distutils.core import setup
from glob import glob
import subprocess

if "py2exe" in sys.argv:
  import py2exe

__name__='Plot-script'
__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__license__ = "None"
__version__ = "0.7beta2"
__email__ = "a.glavic@fz-juelich.de"
__author_email__ = __email__
__url__ = "http://atzes.homeip.net/plotwiki"
__description__='''Program to plot measured data with Gnuplot. Provides a GUI interface, fitting and some other useful functionalities. Supported file types are 4circle (.spec)/MPMS,PPMS (.dat/.raw)/reflectometer (.UXD)/TREFF/IN12/DNS and can be widened with plugins.'''

__scripts__=['plot.py']
__py_modules__=[]
__package_dir__={'plot_script': ''}
__packages__=['plot_script', 'plot_script.config', 'plot_script.read_data', 'plot_script.sessions', 
            'plot_script.sessions.reflectometer_fit', 'plot_script.wxgui', 'plot_script.gtkgui']
__package_data__={'plot_script.config': ['plot_script.squid_calibration', '*.dat', 'fit/fit.f90', 
                            'fit/pnr_multi/*.f90', 'fonts/*.ttf', 'logo.png'], 
                    }
__requires__=['pygtk', 'gobject', 'numpy', 'scipy']

__options__={ "py2exe": {"includes": "numpy,scipy,gtk,pango,cairo,pangocairo,atk,gobject",
                             }}

script_files=['scripts/prd', 'scripts/psd', 'scripts/p4d', 'scripts/dnsplot', 'scripts/treffplot', 'scripts/pin12', 
              'scripts/plot_SQUID_data', 'scripts/plot_4circle_data', 'scripts/plot_reflectometer_data']
# creat windows batches for the script_files
win_batches=[script+'.bat' for script in script_files]
for script in script_files:
  line=open(script, 'r').readlines()[1]
  open(script+'.bat', 'w').write(line.replace('$', '%'))
__scripts__+=script_files+win_batches

if '-test' in sys.argv:
  sys.argv.remove('-test')
  py2exe_test=True
else:
  py2exe_test=False

if 'install' not in sys.argv:
  # Remove MANIFEST befor distributing to be sure no file is missed
  if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

if 'sdist' in sys.argv:
  # Test if every file has the right version for distributing.
  # This is only to remind the developer to check all files before every new version.
  # If the versions do not match a alpha/beta can be added to the version name of the distribution.
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
  for package in __packages__[1:]:
    package=package.split('.', 1)[1]
    modules=filter(lambda file: file[-3:]=='.py',os.listdir(package.replace(".", "/")))
    modules.remove('__init__.py')
    for module in modules:
      mod=__import__(package + '.' + module[:-3], globals(), locals(), ['__version__'], -1)
      try:
        if mod.__version__!=__version__:
          print "File %s/%s has version %s not equal to distribution version %s." % (
                                        package, module, mod.__version__, __version__)
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

#__py_modules__.append('configobj')

# as the requires keyword from distutils is not working, we test for the dependencies ourselves.
if 'install' in sys.argv:
  dependencies_ok=True
  print "Testing dependencies."
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
    print "PyGTK with gobject has to be installed to use GTK GUI."
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

# Run the setup command with the selected parameters
setup(name=__name__,
      version=__version__,
      description=__description__,
      author=__author__,
      author_email=__email__,
      url=__url__,
      scripts=__scripts__, 
      py_modules=__py_modules__, 
      packages=__packages__, 
      package_dir=__package_dir__, 
      package_data=__package_data__,
      requires=__requires__, #does not do anything
      console = [ "__init__.py","py2exe_imports.py" ],
      #windows = [ "plot.py" ],
      options = __options__, 
     )

# If binary distribution has been created rename it and create .deb package, too.
if ('bdist' in sys.argv):
  print "Moving distribution files..."
  from glob import glob
  os.chdir('archiv')
  os.rename(__name__+'-'+__version__+'-1.noarch.rpm', __name__+'-'+__version__+'.rpm')
  os.remove(__name__+'-'+__version__+'-1.src.rpm')
  os.rename(__name__+'-'+__version__+'.linux-x86_64.exe', __name__+'-'+__version__+'.exe')
  print "Creating debian folder..."
  subprocess.Popen(['fakeroot', 'alien', '-k', '-g', __name__+'-'+__version__+'.rpm'], shell=False, 
                   stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
  # creating menu entries
  os.mkdir(__name__+'-'+__version__+'/usr/share/applications/')
  os.mkdir(__name__+'-'+__version__+'.orig/usr/share/applications/')
  subprocess.Popen(['cp']+ glob('../menu_entries/*.desktop')+[__name__+'-'+__version__+'/usr/share/applications/'], 
                   shell=False, stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['cp']+glob('../menu_entries/*.desktop')+[__name__+'-'+__version__+'.orig/usr/share/applications/'], 
                   shell=False, stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()
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
  print "Removing build folder..."
  os.chdir('..')
  os.popen('rm build -r')

if ('install' in sys.argv) and len(sys.argv)==2:
  if ('win' in sys.platform):
    # In windows the scriptpath is not in the path by default
    win_script_path=os.path.join(sys.prefix.lower(), 'scripts')
    win_path=os.path.expandvars('$PATH').lower().split(';')
    if not win_script_path in win_path:
      print "Could not verify path!\nPlease be sure that '" + win_script_path + "' is in your path."
  else:
    # Linux/OS-X installation
    pass

  # If not installing to python default path change a line in the script to add the program location
  # to pythons module search path when executing.
  # TODO: Try to make this work with all setup parameters not only --install-scripts + --prefix
if ('--install-scripts' in sys.argv) and ('--prefix' in sys.argv):
  print "Adding module directory to python path in plot.py script."
  script=open(os.path.join(sys.argv[sys.argv.index('--install-scripts')+1], 'plot.py'), 'r')
  text=script.read().replace('##---add_python_path_here---##','sys.path.append("'+\
                    glob(os.path.join(sys.argv[sys.argv.index('--prefix')+1], 'lib/python2.?/site-packages'))[-1]\
                    +'")')
  script.close()
  script=open(os.path.join(sys.argv[sys.argv.index('--install-scripts')+1], 'plot.py'), 'w')
  script.write(text)
  script.close()
  
# py2exe specific stuff to make it work:
if "py2exe" in sys.argv and not py2exe_test:
  print "\nRenaming executable"
  os.popen('copy archiv\\__init__.exe archiv\\plot.exe')
  os.popen('del archiv\\__init__.exe')
  print "\n*** Copying gtk stuff ***"
  from glob import glob
  try:
    os.mkdir('archiv\\etc')
    os.mkdir('archiv\\share')
    os.mkdir('archiv\\lib')
    os.mkdir('archiv\\gnuplot')
    os.mkdir('archiv\\config')
  except:
    print "Directories already exist."
  try:
    handle=os.popen('xcopy c:\\gtk\\etc archiv\\etc /y /e')
    print handle.read()
    handle=os.popen('xcopy c:\\gtk\\share archiv\\share /y /e')
    print handle.read()
    handle=os.popen('xcopy c:\\gtk\\lib archiv\\lib /y /e')
    print handle.read()
    handle=os.popen('xcopy c:\\gnuplot archiv\\gnuplot /y /e')
    print handle.read()
    handle=os.popen('xcopy config archiv\\config /y /e')
    print handle.read()
  except:
    print "Problem with copy"
  for script_file in glob('scripts\\*.bat'):
    sf=open(script_file, 'r').read()
    open(os.path.join('archiv', os.path.split(script_file)[1]), 'w').write(sf.replace('plot.py', 'plot'))
  
