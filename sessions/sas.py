# -*- encoding: utf-8 -*-
'''
  class for small angle scattering data sessions
'''
#################################################################################################
#                        Script to plot SAS-measurements with gnuplot                          #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.
import sys
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
import read_data.sas
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.sas', fromlist=['SASGUI']).SASGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.6.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SASSession(GUI, GenericSession):
  '''
    Class to handle small angle scattering data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tSAS-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('Filtered', '*.dat', '*.txt', '*.gz'),]
  mds_create=False

  #------------------ local variables -----------------

  
  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.sas.read_data(file_name)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
