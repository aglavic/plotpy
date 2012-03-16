#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Script to import debug.log information to investigate the error messages.
'''

import sys
from cPickle import loads

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

def import_from_log(name):
  '''
    Open the log file and import the message and the pickled datasets.
  '''
  if name.endswith('.gz'):
    import gzip
    log_file_data=gzip.open(name, 'r').read()
  else:
    log_file_data=open(name, 'r').read()
  message, pickle_str=log_file_data.split('#-----------------------------start of pickled datasets-----------------------\n')
  pickle_str, tempfiles=pickle_str.split('#-----------------------------end of pickled datasets-----------------------')
  datasets=loads(pickle_str)
  return message, datasets, tempfiles

if __name__=='__main__':
  m, d, t=import_from_log(sys.argv[1])
  from plot_script.gtkgui.dialogs import StatusDialog
  sd=StatusDialog(title='Error Text', initial_text=m)
  sd.set_default_size(800, 800)
  if t.strip()!='':
    sd2=StatusDialog(title='Tempfile Contents', initial_text=t)
    sd2.set_default_size(800, 800)
    sd2.show()
  sd.show()
  import plot_script.sessions.generic
  active_session=plot_script.sessions.generic.GenericSession(None)
  active_session.file_data={'import from log': d}
  active_session.active_file_data=d
  active_session.active_file_name='import from log'
  # Start GUI
  import plot_script.gtkgui.main_window
  import gtk
  plotting_session=plot_script.gtkgui.main_window.ApplicationMainWindow(active_session)
  gtk.main() # start GTK engine

