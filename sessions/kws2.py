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
import sys
from glob import glob
from configobj import ConfigObj
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
import config.kws2
# importing data readout
import read_data.kws2
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.kws2', fromlist=['KWS2GUI']).KWS2GUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Ulrich Ruecker"]
__license__ = "GPL v3"
__version__ = "0.7.6.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class KWS2Session(GUI, GenericSession):
  '''
    Class to handle in12 data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tGISAS-Data treatment:
\t\t-bg fraction\tPerform automatic background substraction with the minimal fraction 1./{fraction}
\t\t\t\tof pixels to be treated as background
\t\t-all-frames
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('GISAS', '*.DAT', '*.DAT.gz', '*.cmb', '*.cmb.gz', '*.edf', '*.edf.gz', '*.tif', '*.bin', '*.bin.gz'),]
  mds_create=False
  read_directly=True

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['-all-frames', 'bg']  
  auto_background=None
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    GenericSession.__init__(self, arguments)
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='bg':
          self.auto_background=float(argument)
          last_argument_option=[False,'']          
        else:
          found=False
      elif argument=='-all-frames':
        read_data.kws2.import_subframes=True
        found=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    folder, rel_file=os.path.split(os.path.realpath(file_name ))
    setups=ConfigObj(os.path.join(folder, 'gisas_setup.ini'), unrepr=True)
    setups.indent_type='\t'
    found=False
    for key, value in setups.items():
      if os.path.join(folder, rel_file) in glob(os.path.join(folder, key)):
        found=True
    if not found:
      self.new_configuration(setups, rel_file, folder)
    if self.auto_background is not None:
      datasets=read_data.kws2.read_data(file_name )
      print "\tAutosubtracting background"
      for dataset in datasets:
        self.autosubtract_background(dataset, self.auto_background)
      return datasets
    else:
      return read_data.kws2.read_data(file_name )

  def autosubtract_background(self, dataset, fraction=5.):
    '''
      Try to estimate the background and subtract it. This is done using a
      threashhold, which is logarithmic increased until a cirtain amount of 
      points lies below it. After this the threashold is linearly increased within
      the power of 10 evaluated by the logarithmic method.
    '''
    z=dataset.data[dataset.zdata]
    zarray=z[:]
    length=len(zarray)
    # get maximal power of 10 for the background
    max_index=map(lambda i: ((zarray<10**i).sum()>length/fraction), range(1,10)).index(True)
    rough_background=10**(max_index)*(map(lambda i: ((zarray<(10**(max_index)*i)).sum())>length/fraction, 
                                          range(2,11)).index(True)+1)
    fine_background=rough_background+10**(max_index-1)*(map(lambda i: (zarray<(rough_background+10**(max_index-1)*i)).sum()>length/fraction, 
                                                        range(1,11)).index(True)+1)
    z.values=zarray-fine_background
    dataset.plot_options.zrange=(1.,None)
    return fine_background

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
