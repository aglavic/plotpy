# -*- encoding: utf-8 -*-
'''
  Class for IN12 data sessions
'''

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
from plotpy.read_data import in12 as read_data
# import gui functions for active config.gui.toolkit
from plotpy.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.in12', fromlist=['IN12GUI']).IN12GUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=["Ulrich Ruecker"]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class IN12Session(GUI, GenericSession):
  '''
    Class to handle in12 data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tIN12-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('Filtered', '*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]', '*.gz'), ]
  mds_create=False

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
#  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+[]  
  #------------------ local variables -----------------


  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    GenericSession.__init__(self, arguments)

#  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
#    '''
#      additional command line arguments for squid sessions
#    '''
#    found=True
#    if (argument[0]=='-') or last_argument_option[0]:
#      # Cases of arguments:
#      if last_argument_option[0]:
#        found=False
#      elif argument=='-no-img':
#        self.import_images=False
#        found=True
#      else:
#        found=False
#    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.read_data(file_name)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
