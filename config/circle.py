# -*- encoding: utf-8 -*-
'''
 Some general settings for the 4circle session
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ 'Name in file' , 'column to map to' , [ 'dimension' , 'unit' ]]
COLUMNS_MAPPING=[\
['Two Theta',6,['2Θ','°']]\
,['Theta',6,['Θ','°']]\
,['Chi',6,['χ','°']]\
,['Phi',6,['φ','°']]\
,["Phi'",6,["φ_{calc}",'°']]\
,['xsample', 6, ['x_{Sample}', 'mm']]\
,['ysample', 6, ['y_{Sample}', 'mm']]\
,['zsample', 6, ['z_{Sample}', 'mm']]\
,['Time', 6, ['time', 's']]\
,['Lakeshore', 6, ['T_{set}', 'K']]\
,['H',0,['h','']]\
,['K',1,['k','']]\
,['L',2,['l','']]\
,['Epoch',3,['Epoch','']]\
,["Seconds",4,['counting time','s']]\
,["Monitor",5,['monitor intensity','counts']]\
,['Detector',7,['intensity','counts']]\
,['T-diode',8,['T_{sample}','K']]\
,['Det/Mon',13,['I','signal/monitor']]\
,['PhotEner',9,['energy','eV']]\
,['twotheta',10,['2Θ','°']]\
,['theta',11,['Θ','°']]\
, ['Drain/Mon', 12, ['drain/monitor', 'a.u.']]\
]
# Measurement types where some parameters are fix and x,y and yerror columns are set.
# [ 'list of constant parameters [ column , max_div ]' , x-col, y-col, div_y-col , plot options]
# The first measurement fitting is used (so you should put stricter rules before others).
# If no type fits the data collected nothing will be plotted. 
# Diviations are only compared with last datapoint, so slow increases won't trigger a new sequence.
MEASUREMENT_TYPES=[\
# Theta/2Theta/chi/phi scans
[[[6,500]],6,7,8,'']\
# h scan
,[[[1,0.005],[2,0.005]],0,8,7,'']\
# k scan
,[[[0,0.005],[2,0.005]],1,8,7,'']\
# l scan
,[[[0,0.005],[1,0.005]],2,8,7,'']\
# hk mesh
,[[[2,0.005]],0,1,8,'',7]\
# kl mesh
,[[[0,0.005]],1,2,8,'',7]\
# hl mesh
,[[[1,0.005]],0,2,8,'',7]\
,[[],0,3,6,'set title "Unknown Scan"\n']\
] # raw data measureing with temperature shown, MvsT with constand H,MvsH with constand T

KNOWN_COLUMNS={
               'H': ('h', ''), 
               'K': ('k', ''), 
               'L': ('l', ''), 
               'Epoch': ('Epoch', 's'), 
               'Seconds': ('time', 's'), 
               'T-diode': ('T_{sample}', 'K'), 
               'Det/Mon': ('I_{norm}', 'signal/monitor'), 
               'Drain': ('I_{drain}', 'mA'), 
               'PhotEner': ('E', 'eV'), 
               'Mon/Ring': ('monitor_{ring}', 'signal'), 
               'Pressure': ('P', 'mBar'), 
               'Two Theta': ('2Θ', '°'), 
               'Theta': ('Θ', '°'), 
               'twotheta': ('2Θ', '°'), 
               'theta': ('Θ', '°'), 
               'Phi': ('φ', '°'), 
               'Chi': ('χ', '°'), 
               'Alpha': ('α_i', '°'), 
               'Beta': ('α_f', '°'), 
               'Azimuth': ('Ψ', '°'), 
               'Time': ('Time', 's'), 
               'Ringcurr': ('I_{ring}', 'mA'), 
               'Drain/Mon': ('I_{drain_{norm}}', 'mA/monitor'), 
               'Monitor': ('monitor', 'a.u.'), 
               'Detector': ('I', 'counts'), 
               'Integrated Intensity': ('I_{int}', 'counts'), 
               'xsample': ('x_{sample}', 'mm'), 
               'ysample': ('y_{sample}', 'mm'), 
               'zsample': ('z_{sample}', 'mm'), 
               }

INTENSITY_COLUMNS=[
                   'I_{norm}',
                   'I', 
                   'I_{drain_{norm}}',
                   ]

P09_COLUMNS_MAPPING={
                     'EXP_C01_POINT_DETECTOR': ('I_{RAW}', 'counts'), 
                     'EXP_VFC01_BEAM_MONITOR_VERT.': ('Monitor_{vert}', 'counts'), 
                     'EXP_VFC02_BM_MONITOR_HOR.': ('Monitor_{hor}', 'counts'), 
                     'SECONDS_PER_POINT': ('time', 's'), 
                     'ATTN_FACTOR': ('Attenuation', ''), 
                     'ENERGY': ('E', 'eV'), 
                     'TEMPERATURE_SAMPLE': ('T_{Sample}', 'K'), 
                     'TEMPERATURE_CONTROL': ('T_{Control}', 'K'), 
                     'H': ('H', 'r.l.u'), 
                     'K': ('K', 'r.l.u'), 
                     'L': ('L', 'r.l.u'), 
                     'T2T': ('Θ_{th2th}', '°'), 
                     'DUMMY': ('time-scan', 'steps'), 
                     'EXP_MOT05': ('Θ', '°'), 
                     'EXP_MOT07': ('z', 'mm'), 
                     'EXP_MOT12': ('Δ', '°'), 
                     #'EXP_MOT07': ('Δ', '°'), 
                     #'EXP_MOT06': ('χ', '°'), 
                     'EXP_MOT17': ('φ', '°'),                      
                     }

ID4_SCANS={
           'XMCD': ([(1, 'E', 'eV'), 
                     (15, 'XMCD (TFY)', ''), (12, 'Total Fluorescense Yield', ''), 
                     (11, 'Electron Yield', ''), (14, 'XMCD (EY)', ''),
                     (13,  'Fluorescense Yield 2nd window', 'counts'), (16,  'XMCD (FY2)', ''), 
                     (17,  'Reference Foil', ''), 
                     (5, 'Raw TFY (1)', 'counts'), (9, 'Raw TFY (2)', 'counts'), 
                     (3, 'Monitor (1)', 'counts'), (7, 'Monitor (2)', 'counts'), 
                     (6, 'Raw FY2 (1)', 'counts'), (10, 'Raw FY2 (2)', 'counts'), 
                     ]), 
           'e-scan': ([(1, None, None), 
                      (12, 'Total Fluorescense Yield', ''), 
                      (11, 'Electron Yield', ''), 
                      (10,  'Fluorescense Yield 2nd window', 'counts'), 
                      (6, 'Raw TFY', 'counts'), 
                     (4, 'Monitor', 'counts'),]), 
           'mirror-align': ([(1, None, None), 
                      (3, 'I_0', 'counts'), 
                      (8, 'Electron Yield', ''), 
                      (9, 'Total Fluorescense Yield', ''), 
                      (10,  'Fluorescense Yield 2nd window', 'counts')]),
           'other': ([(1, None, None), 
                      (9, 'Total Fluorescense Yield', ''), 
                      (8, 'Electron Yield', ''), 
                      (10,  'Fluorescense Yield 2nd window', 'counts')])
           }

ID4_MAPPING={
             '7T Sample Z': 'Z', 
             'Magnet X': 'X', 
             'Magnet Y': 'Y', 
             'SGM1:Energy': 'E', 
             'M3C DS Y': 'Mirror Y_{M3C DS Y}', 
             }
