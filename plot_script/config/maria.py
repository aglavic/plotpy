# -*- encoding: utf-8 -*-
'''
 Some general settings for the treff sessions using the maria reflectometer
'''

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

# map of line/column indices for the detector raw data files (1024*1024 points)
DETECTOR_PIXELS=1024
CENTER_PIXEL=512.5
CENTER_PIXEL_Y=512.5
DETECTOR_ROWS_MAP=[[j+i*DETECTOR_PIXELS for i in range(DETECTOR_PIXELS)] for j in range(DETECTOR_PIXELS)]
DETECTOR_REGION=(207, 836, 197, 826)
PIXEL_WIDTH=-0.019

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
                 'selector[Angstr.]': 'Wavelength',
                 'pflipper[]': 'PolarizerFlipped',
                 'aflipper[]': 'AnalyzerFlipped',
                      # New Names
                 'Monitor1[counts]': 'Monitor',
                 'ROI1[counts]': '2DWindow',
                 'omega[deg]': 'omega',
                 'detarm[deg]':'detector',
                 'Coinc[counts]':'DetectorTotal',
                 'image_file[]': 'Image',
                 'tx[mm]': 'Position_x',
    # only new format:
                 'roi1': '2DWindow',
                 'roi2': '2DWindow2',
                 'roi3': '2DWindow3',
                 'roi4': '2DWindow4',
                 'roi5': '2DWindow5',
                 'roi6': '2DWindow6',
                 'roi7': '2DWindow7',
                 'roi8': 'DetectorTotal',
                 'wavelength': 'Wavelength',
                 'monitor1': 'Monitor',
                 'full': 'DetectorTotal',
                 'time': 'Time',
                 'pflipper': 'PolarizerFlipped',
                 'aflipper': 'AnalyzerFlipped',


}