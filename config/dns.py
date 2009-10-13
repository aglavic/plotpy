#!/usr/bin/env python
'''
  Configurations for the DNS file import.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6b1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

min_prefix_length=3

FIRST_DETECTOR_ANGLE=0.0
START_WITH_DETECTOR=4
NUMBER_OF_DETECTORS=24
DETECTOR_ANGULAR_INCREMENT=5.
VANADIUM_FILE=None
SETUP_DIRECTORY='/home/glavic/Daten/DNS/setup/rc21' # directory to look for last reactore cycle calibrations
NICR_FILE_WILDCARD=('', 'nicr.d_dat') # nicr files start, end string
BACKGROUND_WILDCARD=('', 'leer.d_dat') # background file start, end string
VANADIUM_WILDCARD=('', 'vana.d_dat') # background file start, end string

# mapping of the parameter names in the DNS data files
GET_INFO= (\
  # get detector bank position
  ('DeteRota','detector_bank_2T'),\
  # get sample rotation
  ('Huber','omega'),\
  # get polarizer positio
  ('Translation','polarizer_trans'),\
  # get flipper current
  ('Flipper_precession','flipper'),\
  # get flipper current
  ('Flipper_z_compensation','flipper_compensation'),\
  # get helmholz current
  ('C_a','C_a'),\
  # get helmholz current
  ('C_b','C_b'),\
  # get helmholz current
  ('C_c','C_c'),\
  # get helmholz current
  ('C_z','C_z'),\
  # get temperature
  ('T1','temperature'),\
  # get counting time
  ('Timer','time'),\
  # get monitor counts
  ('Monitor','monitor')
  )

SCALE_BY=('time', 's') #('monitor','monitor') # scale data by measureing 'time' or 'monitor' counts

# This is a dictionary with predefined calculations on polarization channels.
# Each item is a list of the containing polarizations and their part of the equation,
# for each element this is ( {index of polarization chanel}, {sign}, {factor} ).
# For example to calculate polarization1 + polarization2 - 2*polarization3 use:
#  [ (1, '+', 1.) , (2, '+', 1.) , (3, '-' , 2.) ]
#
# Clearly this does only work if all polarizations have the same number 
# of measured points and if the direction of measureing is right.
SEPERATION_PRESETS={
                    'para' : [(0, '+', 2.), (2, '+', 2.), (4, '-', 4.)],
                    'spin incoherent' : [(4, '+', 4.5), (0, '-', 1.5), (2, '-', 1.5)],
                    'nuclear coherent' : [(5, '+', 1.), (6, '-', 0.5), (7, '-', 0.3333333)],
                    }
