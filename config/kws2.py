# -*- encoding: utf-8 -*-
'''
  Configurations for the kws2 file import.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7RC1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

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
              'DETECTOR_SENSITIVITY' : None, 
              'LAMBDA_N': LAMBDA_N, 
              }