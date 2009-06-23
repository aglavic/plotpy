#!/usr/bin/env python
'''
  class for DNS data sessions
'''
#################################################################################################
#                        Script to plot DNS-measurements with gnuplot                           #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing data readout
import read_data.dns

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Werner Schweika"]
__license__ = "None"
__version__ = "0.6a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class DNSSession(GenericSession):
  '''
    Class to handle dns data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tDNS-Data treatment:
\t\t-inc\tinc\tThe default increment between files of the same polarization.
\t\t-ooff\tooff\tOffset of omega angle for the sample to calculate the right q_x,q_y
\t\t-vana\tfile\tUse different Vanadium file for evaluation.
\t\t-files\tprefix ooff inc from to
\t\t\t\t\t\tExplicidly give the file name prefix, omega offset, increment and numbers for the files to be used.
\t\t\t\t\t\tCan be given multiple times for diefferent prefixes.
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('All','*'), ('DNS (.d_dat)', '*.d_dat'))

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['inc', 'ooff', 'bg', 'vana', 'files'] 
  file_options={'default': [0, 1, [0, -1]],  # (omega_offset, increment, range)
                } # Dictionary storing specific options for files with the same prefix
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    GenericSession.__init__(self, arguments)
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      additional command line arguments for dns sessions
    '''
    #found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='inc':
          self.file_options['default'][1]=int(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='ooff':
          self.file_options['default'][0]=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='vana':
          self.vanadium_file=argument
          last_argument_option=[False,'']
        else:
          found=False
#      elif argument=='-no-img':
#        self.import_images=False
#        found=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.dns.read_data(file_name)


  def create_menu(self):
    '''
      create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='DNS'>
        <menuitem action='SetOmegaOffset' />
        <menuitem action='SetIncrement' />
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "DNS", None,                             # name, stock id
                "DNS", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SetOmegaOffset", None,                             # name, stock id
                "Omega Offset...", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SetIncrement", None,                             # name, stock id
                "Change Increment", None,                    # label, accelerator
                "Change Increment between files with same Polarization",                                   # tooltip
                None ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
