#!/usr/bin/env python
'''
  class for IN12 data sessions
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

# import GenericSession, which is the parent class for the squid_session
from plot_generic_data import GenericSession
# importing data readout
import read_data.in12

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class IN12Session(GenericSession):
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
  FILE_WILDCARDS=(('All','*'), ('Filtered', '*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]'))
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
  
#  def read_argument_add(self, argument, last_argument_option=[False, '']):
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
    return read_data.in12.read_data(file_name)


  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string=''#'
      #<menu action='TREFF'>
      #
      #</menu>
    #'''
    # Create actions for the menu
    actions=(
            ( "IN12", None,                             # name, stock id
                "IN12", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
