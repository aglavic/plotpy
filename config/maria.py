# -*- encoding: utf-8 -*-
'''
 Some general settings for the treff sessions using the maria reflectometer
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

# map of line/column indices for the detector raw data files (1024*1024 points)
DETECTOR_PIXELS=1024
CENTER_PIXEL=512.5
CENTER_PIXEL_Y=512.5
DETECTOR_ROWS_MAP=[[j+i*DETECTOR_PIXELS for i in range(DETECTOR_PIXELS)] for j in range(DETECTOR_PIXELS)]
DETECTOR_REGION=(207, 836, 197, 820)
PIXEL_WIDTH=-0.02

COLUMNS_MAPPING={
                 'omega': 'omega', 
                 'detarm': 'detector', 
                 'ROI1': '2DWindow', 
                 #'Coinc.': 'DetectorTotal', 
                 'image_file': 'Image', 
                 'Mon2': 'Monitor', 
                 'ROI2': '2DWindow2', 
                 'ROI3': '2DWindow3', 
                 'ROI4': '2DWindow4', 
                 'ROI5': '2DWindow5', 
                 'ROI6': '2DWindow6', 
                 'ROI7': '2DWindow7', 
                 'ROI8': 'DetectorTotal', 
                 'tx': 'Position_x', 
                 'ty': 'Position_y', 
                 'tz': 'Position_z', 
                 'Time[sec]': 'Time',
                 'selector': 'Wavelength', 
                 }