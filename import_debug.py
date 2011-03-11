# -*- encoding: utf-8 -*-
'''
  Script to import debug.log information to investigate the error messages.
'''

import sys
from cPickle import loads

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.2.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def import_from_log(name):
  '''
    Open the log file and import the message and the pickled datasets.
  '''
  log_file_data=open(name, 'r').read()
  message, pickle_str=log_file_data.split('#-----------------------------start of pickled datasets-----------------------\n')
  pickle_str=pickle_str.split('#-----------------------------end of pickled datasets-----------------------')[0]
  datasets=loads(pickle_str)
  return message, datasets
  
if __name__=='__main__':
  m, d=import_from_log(sys.argv[1])
  print m
  import sessions.generic
  active_session=sessions.generic.GenericSession(None)
  active_session.file_data={'import from log': d}
  active_session.active_file_data=d
  active_session.active_file_name='import from log'
  # Start GUI
  import plotting_gui
  import gtk
  plotting_session=plotting_gui.ApplicationMainWindow(active_session)
  gtk.main() # start GTK engine
  
