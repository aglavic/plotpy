# -*- encoding: utf-8 -*-
'''
  Class for small angle scattering data sessions.
'''

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
from plotpy.read_data import sas as read_data

try:
  from plotpy.gtkgui.sas import SASGUI as GUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=[]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class SASSession(GUI, GenericSession):
  '''
    Class to handle small angle scattering data sessions
  '''
  name='sas'
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tSAS-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('Filtered', '*.dat', '*.txt', '*.gz'), ]
  mds_create=False

  #------------------ local variables -----------------


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.read_data(file_name)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
