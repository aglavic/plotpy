'''
  Configurations for the GUI frontend.
  Mostly used for the global parameter 'toolkit' which is a string
  defining the prefix for the gui package, e.g. 'gtk' for using the
  gtkgui package.
  
  At the moment the gtk version is much more mature and feature rich 
  so it is recommanded to use this if possible.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.5"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

#toolkit='wx'
#toolkit='gtk'
toolkit='auto'

DOWNLOAD_PAGE_URL='http://iffwww.iff.kfa-juelich.de/~glavic/plotupdate.py'

if toolkit=='auto':
  # try to automatically select the available toolkit (could be slower)
  try:
    import gtk
    toolkit='gtk'
  except ImportError:
    import wx
    toolkit='wx'
 
