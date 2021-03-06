# -*- encoding: utf-8 -*-
'''
  Class for Oxide MBE data (logfiles, RHEED, LEED) sessions
'''

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
from plot_script.read_data import mbe as read_data
# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.mbe', fromlist=['MBEGUI']).MBEGUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=["Ulrich Ruecker"]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class MBESession(GUI, GenericSession):
  '''
    Class to handle mbe leed/rheed and other data
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('MBE', '*.png', '*.dat', '*.log'), ]
  mds_create=False
  read_directly=True

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+[]
  #------------------ local variables -----------------


  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    GenericSession.__init__(self, arguments)

  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    #folder, rel_file=os.path.split(os.path.realpath(file_name))
    #setups=ConfigObj(os.path.join(folder, 'leed_setup.ini'), unrepr=True)
    #setups.indent_type='\t'
    #found=False
    #for key, ignore in setups.items():
    #  if os.path.join(folder, rel_file) in glob(os.path.join(folder, key)):
    #    found=True
    #if not found:
    #  self.new_configuration(setups, rel_file, folder)
    return read_data.read_data(file_name)

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
