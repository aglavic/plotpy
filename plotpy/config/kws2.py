# -*- encoding: utf-8 -*-
'''
  Configurations for the kws2 file import.
'''

__author__="Artur Glavic"
__credits__=[]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

# how many header lines
HEADER=70

# sqrt(pixels)
PIXEL_X=128
PIXEL_SIZE=5.25

# for calculating q
LAMBDA_N=4.51

# setup specific settings
setup_config={'CENTER_X' :65.,
              'CENTER_Y' :64.3,
              'DETECTOR_DISTANCE' :5285.,
              'SWAP_YZ' : False,
              'BACKGROUND': None,
              'DETECTOR_SENSITIVITY' : None,
              'LAMBDA_N': 4.51,
              }

# setup specific settings
setup_config_riso={'CENTER_X' :345.,
              'CENTER_Y' :498.5,
              'DETECTOR_DISTANCE' : 1435.,
              #'BACKGROUND': None, 
              #'DETECTOR_SENSITIVITY' : None, 
              'LAMBDA_N': 1.54,
              }

# Setup parameters and defaults
#setup_parameter_config={
#              'edf': [
#                      ('CENTER_X', )
#                      ]
#              }