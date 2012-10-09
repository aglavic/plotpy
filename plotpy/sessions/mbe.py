# -*- encoding: utf-8 -*-
'''
  Class for Oxide MBE data (logfiles, RHEED, LEED) sessions
'''

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession

try:
  from plotpy.gtkgui.mbe import MBEGUI as GUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=["Ulrich Ruecker"]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class MBESession(GUI, GenericSession):
  '''
    Class to handle mbe leed/rheed and other data
  '''
  name='mbe'
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
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

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
