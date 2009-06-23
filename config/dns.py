#!/usr/bin/env python
'''
  Configurations for the DNS file import.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

min_prefix_length=3

FIRST_DETECTOR_ANGLE=0.0
START_WITH_DETECTOR=4
NUMBER_OF_DETECTORS=24
DETECTOR_ANGULAR_INCREMENT=5.

get_info= (\
  # get detector bank position
  ('DeteRota','detector_bank_2T'),\
  # get sample rotation
  ('Huber','omega'),\
  # get polarizer positio
  ('Translation','polarizer_trans'),\
  # get flipper current
  ('Flipper_precession','flipper'),\
  # get temperature
  ('T1','temperature'),\
  # get counting time
  ('Timer','time'),\
  # get monitor counts
  ('Monitor','monitor')
  )

column_dimensions=(
                    )

name_replacements=(
                )
