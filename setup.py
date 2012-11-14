# -*- encoding: utf-8 -*-
'''
  Script used for setup and installation purpose. 
  If all works the right way this should test the system environment for all dependencies and create source and binary distributions.
  
  The script can create exe stand alone programs under windows, but py2app doesn't word until now.
'''

import sys, os

try:
  # Use easy setup to ensure dependencies
  import ez_setup
  ez_setup.use_setuptools()
except ImportError:
  pass
try:
  from setuptools import setup
  __options__={
               'zip_safe': True,
               'install_requires': '''numpy
                                      PyGTK''',
               'license': 'GPLv3',
               'classifiers': [
                            "Intended Audience :: Science/Research",
                            "License :: OSI Approved :: GNU General Public License (GPLv3)",
                            "Operating System :: Windows,Linux",
                            ],
               }
except ImportError:
  from distutils.core import setup
  __options__={}

import subprocess
from glob import glob

__name__='plotpy' #@ReservedAssignment
__author__="Artur Glavic"
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__author_email__=__email__
__url__="http://plotpy.sourceforge.net/plotwiki"
__description__='''Program to plot measured data with Gnuplot. Provides a GUI interface, fitting and some other useful functionalities. Supported file types are 4circle (.spec)/MPMS,PPMS (.dat/.raw)/reflectometer (.UXD)/TREFF/IN12/DNS and can be widened with plugins.'''

__scripts__=['scripts/plotpy']
__py_modules__=[]
__package_dir__={}
__packages__=['plotpy', 'plotpy.config', 'plotpy.config.default_templates',
            'plotpy.fio', 'plotpy.sessions',
            'plotpy.sessions.reflectometer_fit', 'plotpy.gtkgui', 'plotpy.plugins'] #'plotpy.wxgui', 
__package_data__={'plotpy.config': ['plotpy.squid_calibration', '*.dat', 'fit/fit.f90',
                            'fit/pnr_multi/*.f90'],
                  'plotpy': ['doc/*.*', 'doc/_modules/*.*',
                                  'doc/_static/*.*', 'doc/_sources/*.*',
                                  'gpl.pdf', 'gpl.txt'],
                  'plotpy.gtkgui': ['icons/*.png'],
                    }
__data_files__=[('plotpy/doc', glob('plotpy/doc/*.*'))]

if "py2app" in sys.argv:
  import py2app #@UnusedImport @UnresolvedImport
  #__data_files__+=[('../Frameworks', glob('/usr/lib/libwx_mac*'))]
  __options__.update({
              "app": ['plot.py'],
              "options": { "py2app": {
                           "includes": "numpy, pango, cairo, pangocairo, atk, gobject, gio",
                           "optimize": 1, # Keep docstrings
                           "packages": "encodings, gtk, IPython, plotpy",
                           "resources": glob("plotpy/doc/*.html"),
                           "iconfile": "plotpy/config/logo.png",
                           #"argv_emulation": True,
                           },
                          }
              })
elif "py2exe" in sys.argv:
  import py2exe #@UnusedImport @UnresolvedImport
  __options__.update({
                #"setup_requires": ['py2exe'], 
                #"console": [ "__init__.py"], # set the executable for py2exe
                "windows": [ "scripts/plotpy" ], # executable for py2exe is windows application
                "options": {  "py2exe": {
                              "includes": "numpy, pango, cairo, pangocairo, atk, gobject, gio, Image, TiffImagePlugin, PngImagePlugin",
                              "optimize": 1, # Keep docstring (e.g. IPython console usage)
                              "skip_archive": True, # setting not to move compiled code into library.zip file
                              'packages':'encodings, gtk, IPython, PIL, plotpy',
                              "dll_excludes": ["MSVCP90.dll", 'libglade-2.0-0.dll'],
                              "excludes": "matplotlib, pylab, PyQt4, wx, wxPython, idlelib",
                             },
                           }
              })

__requires__=['pygtk', 'numpy']

# extensions modules written in C
__extensions_modules__=[]

script_files=['scripts/prd', 'scripts/psd', 'scripts/p4d', 'scripts/dnsplot',
              'scripts/treffplot', 'scripts/pin12',
              'scripts/plot_SQUID_data', 'scripts/plot_4circle_data',
              'scripts/plot_reflectometer_data']
## creat windows batches for the script_files
#win_batches=[script+'.bat' for script in script_files]
#for script in script_files:
#  line=open(script, 'r').readlines()[1]
#  open(script+'.bat', 'w').write(line.replace('$', '%'))
#__scripts__+=script_files+win_batches

if '-test' in sys.argv:
  sys.argv.remove('-test')
  py2exe_test=True
else:
  py2exe_test=False

if 'install' not in sys.argv:
  # Remove MANIFEST befor distributing to be sure no file is missed
  if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

#__py_modules__.append('configobj')

# as the requires keyword from distutils is not working, we test for the dependencies ourselves.
if 'install' in sys.argv:
  dependencies_ok=True
  print "Testing dependencies."
  # call linux and windows gnuplot command with --help option to test if it can be called.
  try:
    subprocess.Popen(['gnuplot', '--help'], shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
    gnuplot=True
  except OSError:
    try:
      subprocess.Popen(['pgnuplot', '--help'], shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
      gnuplot=True
    except OSError:
      print "Gnuplot must be installed to use this program."
      gnuplot=False
      dependencies_ok=False
  # GUI dependencies
  try:
    import gobject #@UnusedImport
    import gtk #@UnusedImport
  except ImportError:
    print "PyGTK with gobject has to be installed to use GTK GUI."
    dependencies_ok=False
  # fitting dependencies, not crucial
  try:
    import numpy #@UnusedImport
  except ImportError:
    print "For fitting to work, numpy has to be installed."
    dependencies_ok=False
  if not dependencies_ok:
    answer=raw_input('Do you still want to install? (y/n): ')
    if answer!='y':
      exit()


#### Run the setup command with the selected parameters ####
setup(name=__name__,
      version=__version__,
      description=__description__,
      author=__author__,
      author_email=__email__,
      url=__url__,
      scripts=__scripts__,
      py_modules=__py_modules__,
      ext_modules=__extensions_modules__,
      packages=__packages__,
      package_dir=__package_dir__,
      package_data=__package_data__,
      data_files=__data_files__,
      requires=__requires__, #does not do anything
      **__options__
     )

# If binary distribution has been created rename it and create .deb package, too.
# The .deb only works on similar systems so we use python2.6 and python2.7 folders
# as these are the versions used in the latest ubuntu versions
if ('bdist' in sys.argv):
  print "Moving distribution files..."
  os.chdir('dist')
  os.rename(__name__+'-'+__version__+'-1.noarch.rpm', __name__+'-'+__version__+'.rpm')
  os.remove(__name__+'-'+__version__+'-1.src.rpm')
  print "Creating debian folder..."
  subprocess.Popen(['fakeroot', 'alien', '-k', '-g', __name__+'-'+__version__+'.rpm'], shell=False,
                   stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  # creating menu entries
  os.mkdir(__name__+'-'+__version__+'/usr/share/applications/')
  os.mkdir(__name__+'-'+__version__+'.orig/usr/share/applications/')
  subprocess.Popen(['cp']+glob('../menu_entries_27/*.desktop')+[__name__+'-'+__version__+'/usr/share/applications/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['cp']+glob('../menu_entries_27/*.desktop')+[__name__+'-'+__version__+'.orig/usr/share/applications/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  # creating mime types
  os.mkdir(__name__+'-'+__version__+'/usr/share/mime/')
  os.mkdir(__name__+'-'+__version__+'/usr/share/mime/packages/')
  os.mkdir(__name__+'-'+__version__+'.orig/usr/share/mime/')
  os.mkdir(__name__+'-'+__version__+'.orig/usr/share/mime/packages/')
  subprocess.Popen(['cp']+glob('../mime_types/*.xml')+[__name__+'-'+__version__+'/usr/share/mime/packages/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['cp']+glob('../mime_types/*.xml')+[__name__+'-'+__version__+'.orig/usr/share/mime/packages/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  os.mkdir(__name__+'-'+__version__+'/etc')
  os.mkdir(__name__+'-'+__version__+'/etc/bash_completion.d')
  os.mkdir(__name__+'-'+__version__+'.orig/etc')
  os.mkdir(__name__+'-'+__version__+'.orig/etc/bash_completion.d')
  os.chdir(__name__+'-'+__version__)
  complete=open('etc/bash_completion.d/plotpy', 'w')
  complete.write(open('../../bash_completion.d/plotpy', 'r').read())
  complete.close()
  # debian control file
  deb_con=open('debian/control', 'w')
  deb_con.write(open('../../deb_control', 'r').read())
  deb_con.close()
  # post install and remove scripts (e.g. adding mime types)
  deb_tmp=open('debian/postinst', 'w')
  deb_tmp.write(open('../../deb_postinst', 'r').read())
  deb_tmp.close()
  deb_tmp=open('debian/postrm', 'w')
  deb_tmp.write(open('../../deb_postrm', 'r').read())
  deb_tmp.close()
  # python 2.7
  print "Packaging for debian (python2.7)..."
  subprocess.Popen(['dpkg-buildpackage', '-i.*', '-I', '-rfakeroot', '-us', '-uc'], shell=False,
                   stderr=subprocess.STDOUT, stdout=open('../last_package.log', 'w')
                   ).communicate()
  os.chdir('..')
  os.rename((__name__+'_'+__version__).lower()+'-1_all.deb', __name__+'-'+__version__+'_natty.deb')
  # python 2.6
  subprocess.Popen(['cp']+glob('../menu_entries/*.desktop')+[__name__+'-'+__version__+'/usr/share/applications/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['cp']+glob('../menu_entries/*.desktop')+[__name__+'-'+__version__+'.orig/usr/share/applications/'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['mv', __name__+'-'+__version__+'/usr/local/lib/python2.7',
                    __name__+'-'+__version__+'/usr/local/lib/python2.6'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  subprocess.Popen(['mv', __name__+'-'+__version__+'.orig/usr/local/lib/python2.7',
                    __name__+'-'+__version__+'.orig/usr/local/lib/python2.6'],
                   shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
  os.chdir(__name__+'-'+__version__)
  print "Packaging for debian (python2.6)..."
  subprocess.Popen(['dpkg-buildpackage', '-i.*', '-I', '-rfakeroot', '-us', '-uc'], shell=False,
                   stderr=subprocess.STDOUT, stdout=open('../last_package_2.log', 'w')).communicate()
  os.chdir('..')
  os.rename((__name__+'_'+__version__).lower()+'-1_all.deb', __name__+'-'+__version__+'_maverick.deb')
  print "Removing debian folder..."
  os.popen('rm '+__name__+'-'+__version__+' -r')
  os.popen('rm '+(__name__+'_'+__version__).lower()+'-1*')
  os.popen('rm *.rpm')
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
      print "Could not verify path!\nPlease be sure that '"+win_script_path+"' is in your path."
  else:
    # Linux/OS-X installation
    pass

  # If not installing to python default path change a line in the script to add the program location
  # to pythons module search path when executing.
  # TODO: Try to make this work with all setup parameters not only --install-scripts + --prefix
if ('--install-scripts' in sys.argv) and ('--prefix' in sys.argv):
  print "Adding module directory to python path in plot.py script."
  script=open(os.path.join(sys.argv[sys.argv.index('--install-scripts')+1], 'plot.py'), 'r')
  text=script.read().replace('##---add_python_path_here---##', 'import sys\nsys.path.insert(1,"'+\
                    glob(os.path.join(sys.argv[sys.argv.index('--prefix')+1], 'lib/python2.?/site-packages'))[-1]\
                    +'")')
  script.close()
  script=open(os.path.join(sys.argv[sys.argv.index('--install-scripts')+1], 'plot.py'), 'w')
  script.write(text)
  script.close()

# py2exe specific stuff to make it work:
if "py2exe" in sys.argv and not py2exe_test:
  def xcopy_to_folder(from_folder, to_folder):
    dest=os.path.join('dist', to_folder)
    if getattr(from_folder, '__iter__', False):
      src=os.path.join(*from_folder)
    else:
      src=from_folder
    print "Copy %s to %s..."%(src, dest)
    try:
      os.mkdir(os.path.join('dist', to_folder))
    except OSError:
      print "\tDirectory %s already exists."%dest
    try:
      handle=os.popen('xcopy %s %s /y /e'%(src, dest))
      files=len(handle.read().splitlines())
      print "\t%i Files"%files
    except:
      print "\tSkipped because of errors!"%src
  print "\nRenaming executable"
  os.popen('copy dist\\__init__.exe archiv\\plot.exe')
  os.popen('del dist\\__init__.exe')
  print "\n*** Copying gtk stuff ***"
  # the package needs all gtk libraries to work stand alone 
  # (only works if the folders are set right on the building system)
  gtk_folder='C:\\gtk'
  #gtk_folder='C:\\Python27\\Lib\\site-packages\\gtk-2.0\\runtime'
  for src, dest in [
                    (gtk_folder+'\\etc', 'etc'),
                    (gtk_folder+'\\share\\*.none', 'share'),
                    (gtk_folder+'\\share\\locale', 'share\\locale'),
                    (gtk_folder+'\\share\\themes', 'share\\themes'),
                    (gtk_folder+'\\share\\icons', 'share\\icons'),
                    (gtk_folder+'\\bin', 'bin'),
                    (gtk_folder+'\\lib', 'lib'),
                    ('plotpy\\config', 'plotpy\\config'),
                    ('plotpy\\gtkgui\\icons', 'plotpy\\gtkgui\\icons'),
                    ]:
    xcopy_to_folder(src, dest)
  for script_file in glob('scripts\\*.bat'):
    sf=open(script_file, 'r').read()
    open(os.path.join('dist', os.path.split(script_file)[1]), 'w').write(sf.replace('plot.py', 'plot'))

# py2app specific stuff to make it work: 
#if "py2app" in sys.argv:
#  subprocess.call(['cp', '-r','config/*','archiv/plot-script.app/Contents/Resources/lib/python2.7/config'])

if 'clean' in sys.argv:
  print "Removing byte compiled files"
  # go through all directories and remove .pyo and .pyc files
  def rec_find_pyc(folder):
    output=glob(os.path.join(folder, '*.pyc'))
    output+=glob(os.path.join(folder, '*.pyo'))
    for item in glob(os.path.join(folder, '*')):
      if os.path.isdir(item):
        output+=rec_find_pyc(item)
    return output
  files=rec_find_pyc('plotpy')
  for filename in files:
    os.remove(filename)
