# -*- encoding: utf-8 -*-
'''
  class for KWS2 data sessions
'''
#################################################################################################
#                        Script to plot KWS2-measurements with gnuplot                          #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

import os
from glob import glob
from configobj import ConfigObj
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
import config.kws2
# importing data readout
import read_data.kws2
# import gui functions for active toolkit
from config.gui import toolkit
try:
  GUI=__import__( toolkit+'gui.kws2', fromlist=['KWS2GUI']).KWS2GUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.7beta1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class KWS2Session(GenericSession, GUI):
  '''
    Class to handle in12 data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tKWS2-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('KWS2', '*.DAT'), ('KWS2 gziped', '*.DAT.gz'), ('All','*'))
  mds_create=False
  read_directly=True

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
    folder, rel_file=os.path.split(os.path.realpath(file_name))
    setups=ConfigObj(os.path.join(folder, 'kws2_setup.ini'), unrepr=True)
    setups.indent_type='\t'
    found=False
    for key, value in setups.items():
      if os.path.join(folder, rel_file) in glob(os.path.join(folder, key)):
        found=True
    if not found:
      self.new_configuration(setups, rel_file, folder)
    return read_data.kws2.read_data(file_name)

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
