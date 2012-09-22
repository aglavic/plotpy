'''
  Used to gather masked imports for PyInstaller script.
'''

#import os
#import sys
#import pkgutil

#plotpydir=os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
#guihooks=[name for _, name, _ in pkgutil.iter_modules([os.path.join(plotpydir, 'plotpy', 'gtkgui')],
#                                                      prefix='plotpy.gtkgui.')]
hiddenimports=[]#guihooks
