# -*- encoding: utf-8 -*-
'''
  class for SHG data sessions
'''
#################################################################################################
#                        Script to plot IN12-measurements with gnuplot                          #
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
import read_data.shg
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.shg', fromlist=['SHGGUI']).SHGGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Ulrich Ruecker"]
__license__ = "GPL v3"
__version__ = "0.7.6.7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SHGSession(GUI, GenericSession):
  '''
    Class to handle SHG data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tSHG-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('SHG Parameters (.par)', '*.par'),]
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
    return read_data.shg.read_data(file_name )


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++