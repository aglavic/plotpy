# -*- encoding: utf-8 -*-
'''
  Configurations for the DNS file import.
'''

import os, sys

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.5.9"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

min_prefix_length=3

FIRST_DETECTOR_ANGLE=0.0
START_WITH_DETECTOR=4
NUMBER_OF_DETECTORS=24
DETECTOR_ANGULAR_INCREMENT=5.
# Mapping the detector numbers of D7 to their angular offset from the bank center
D7_DETECTOR_MAP=[
                 # Relative detector positions for first Bank (Bank 4)
                 [(i%2)*(-0.9886*(i+1)+26.452)+((i+1)%2)*(-0.99863*(i+1)+26.511) for i in range(44)], 
                 # Relative detector positions for second Bank (Bank 3)
                 [(i%2)*(-0.99234*(i+1)+22.728)+((i+1)%2)*(-0.9939*(i+1)+22.397) for i in range(44)], 
                 # Relative detector positions for third Bank (Bank 2)
                 [(i%2)*(-1.0068*(i+1)+21.762)+((i+1)%2)*(-0.99642*(i+1)+21.326) for i in range(44)], 
                 # trying old one
                 #[(i%2)*(-1.0204*(i+1)+23.905)+((i+1)%2)*(-0.9955*(i+1)+23.377) for i in range(44)], 
                 #[(i%2)*(-0.99762*(i+1)+20.566)+((i+1)%2)*(-0.99237*(i+1)+20.7.1a5) for i in range(44)], 
                 #[(i%2)*(-0.99383*(i+1)+19.192)+((i+1)%2)*(-1.0035*(i+1)+19.827) for i in range(44)], 
                 ]
LAMBDA_NEUTRON=None
VANADIUM_FILE=None
SETUP_DIRECTORYS=['.'] # directories to look for the calibration files
NICR_FILE_WILDCARDS=[('', 'nicr.d_dat'), ('', 'NiCr.d_dat'), ('', 'nicr.d_dat.gz'), ('', 'NiCr.d_dat.gz'), 
                     ('','_silica.d7')] # nicr files start, end string
BACKGROUND_WILDCARDS=[('', 'leer.d_dat'), ('', 'back.d_dat'), ('', 'leer.d_dat.gz'), ('', 'back.d_dat.gz'), 
                      ('','_back.d7')]  # background file start, end string
VANADIUM_WILDCARDS=[('', 'vana.d_dat'), ('', 'Vana.d_dat'), ('', 'vana.d_dat.gz'), ('', 'Vana.d_dat.gz'), 
                    ('vanadium_', '.dat'), ('', '_vana.d7')] # vanadium file start, end string

ALWAYS_FULLAUTO=False
FULLAUTO_TEMP_SENSITIVITY=5.

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


if 'dns_config.py' in os.listdir('.'):
  # if a configfile is inside the directory use it's settings.
  sys.path.append('.')
  from dns_config import *

# This is a variable to write the above code to config files created by the binary program
# see config.__init__ for more information
__configadd__="""
import os, sys

if 'dns_config.py' in os.listdir('.'):
  # if a configfile is inside the directory use it's settings.
  sys.path.append('.')
  from dns_config import *
"""
