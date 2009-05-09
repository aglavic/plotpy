#!/usr/bin/env python
'''
 Some general settings for the treff plotting mode from plot.py
'''

from math import pi

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

DETECTOR_ROWS_MAP=[[j+i*256 for i in range(256)] for j in range(256)]
PIXEL_WIDTH=0.014645
LAMBDA_TREFF=4.8

PI_4_OVER_LAMBDA=4*pi/LAMBDA_TREFF
GRAD_TO_MRAD=pi/180*1000
GRAD_TO_RAD=pi/180
