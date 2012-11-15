# -*- encoding: utf-8 -*-
'''
  Class for small angle scattering data sessions.
'''

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession

try:
  from plotpy.gtkgui.sas import SASGUI as GUI
except ImportError:
  class GUI: pass

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


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
