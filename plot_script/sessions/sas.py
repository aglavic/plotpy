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

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
from plot_script.read_data import sas as read_data
# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.sas', fromlist=['SASGUI']).SASGUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

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
  FILE_WILDCARDS=[('Filtered', '*.dat', '*.txt', '*.gz'), ]
  mds_create=False

  #------------------ local variables -----------------


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.read_data(file_name)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++