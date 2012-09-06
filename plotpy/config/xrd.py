# -*- encoding: utf-8 -*-
'''
 Some general settings for the 4circle session
'''

# Transformations for different units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[]

KNOWN_COLUMNS={
               u'H': (u'h', u''),
               u'K': (u'k', u''),
               u'L': (u'l', u''),
               u'Angle': (u'ξ', u'°'),
               u'Epoch': (u'Epoch', u's'),
               u'Seconds': (u'time', u's'),
               u'T-diode': (u'T_{sample}', u'K'),
               u'Temperature': (u'T_{sample}', u'K'),
               u'Field': (u'H', u'kG'),
               u'Det/Mon': (u'I_{norm}', u''),
               u'Drain': (u'I_{drain}', u'pA'),
               u'Detector_pA': (u'I', u'pA'),
               u'PhotEner': (u'E', u'eV'),
               u'Mon/Ring': (u'monitor_{ring}', u'signal'),
               u'Pressure': (u'P', u'mBar'),
               u'Two Theta': (u'2Θ', u'°'),
               u'Theta': (u'Θ', u'°'),
               u'twtht': (u'2Θ', u'°'),
               u'twtth': (u'2Θ', u'°'),
               u'twotheta': (u'2Θ', u'°'),
               u'theta': (u'Θ', u'°'),
               u'thetasample': (u'Θ', u'°'),
               u'Phi': (u'φ', u'°'),
               u'Chi': (u'χ', u'°'),
               u'Alpha': (u'α_i', u'°'),
               u'Beta': (u'α_f', u'°'),
               u'Azimuth': (u'Ψ', u'°'),
               u'Time': (u'Time', u's'),
               u'Ringcurr': (u'I_{ring}', u'mA'),
               u'Drain/Mon': (u'I_{drain_{norm}}', u''),
               u'norm': (u'I_{drain_{norm}}', u''),
               u'Monitor': (u'monitor', u'a.u.'),
               u'Detector': (u'I', u'counts'),
               u'Det/Atten': (u'I_{det/atten}', u'counts'),
               u'Integrated Intensity': (u'I_{int}', u'counts'),
               u'xsample': (u'x_{sample}', u'mm'),
               u'ysample': (u'y_{sample}', u'mm'),
               u'zsample': (u'z_{sample}', u'mm'),
               u'x': (u'x_{sample}', u'mm'),
               u'y': (u'y_{sample}', u'mm'),
               u'z': (u'z_{sample}', u'mm'),
               u'xs': (u'x_{sample}', u'mm'),
               u'ys': (u'y_{sample}', u'mm'),
               u'zs': (u'z_{sample}', u'mm'),
               u'Sample X': (u'x_{sample}', u'mm'),
               u'Sample Y': (u'y_{sample}', u'mm'),
               u'Sample Z': (u'z_{sample}', u'mm'),
               }

INTENSITY_COLUMNS=[
                   u'I_{norm}',
                   u'I',
                   u'I_{drain_{norm}}',
                   ]

P09_COLUMNS_MAPPING={
                     u'EXP_C01_POINT_DETECTOR': (u'I_{RAW}', u'counts'),
                     u'EXP_VFC01_BEAM_MONITOR_VERT.': (u'Monitor_{vert}', u'counts'),
                     u'EXP_VFC02_BM_MONITOR_HOR.': (u'Monitor_{hor}', u'counts'),
                     u'SECONDS_PER_POINT': (u'time', u's'),
                     u'ATTN_FACTOR': (u'Attenuation', u''),
                     u'ENERGY': (u'E', u'eV'),
                     u'TEMPERATURE_SAMPLE': (u'T_{Sample}', u'K'),
                     u'TEMPERATURE_CONTROL': (u'T_{Control}', u'K'),
                     u'H': (u'H', u'r.l.u'),
                     u'K': (u'K', u'r.l.u'),
                     u'L': (u'L', u'r.l.u'),
                     u'T2T': (u'Θ_{th2th}', u'°'),
                     u'DUMMY': (u'time-scan', u'steps'),
                     u'EXP_MOT05': (u'Θ', u'°'),
                     u'EXP_MOT07': (u'z', u'mm'),
                     u'EXP_MOT12': (u'Δ', u'°'),
                     #u'EXP_MOT07': (u'Δ', u'°'), 
                     #u'EXP_MOT06': (u'χ', u'°'), 
                     u'EXP_MOT17': (u'φ', u'°'),
                     }

ID4_SCANS={
           u'XMCD': ([(1, u'E', u'eV'),
                     (15, u'XMCD (TFY)', u''), (12, u'Total Fluorescense Yield', u''),
                     (11, u'Electron Yield', u''), (14, u'XMCD (EY)', u''),
                     (13, u'Fluorescense Yield 2nd window', u'counts'), (16, u'XMCD (FY2)', u''),
                     (17, u'Reference Foil', u''),
                     (5, u'Raw TFY (1)', u'counts'), (9, u'Raw TFY (2)', u'counts'),
                     (3, u'Monitor (1)', u'counts'), (7, u'Monitor (2)', u'counts'),
                     (6, u'Raw FY2 (1)', u'counts'), (10, u'Raw FY2 (2)', u'counts'),
                     ]),
           u'e-scan': ([(1, None, None),
                      (12, u'Total Fluorescense Yield', u''),
                      (11, u'Electron Yield', u''),
                      (10, u'Fluorescense Yield 2nd window', u'counts'),
                      (6, u'Raw TFY', u'counts'),
                     (4, u'Monitor', u'counts'), ]),
           u'mirror-align': ([(1, None, None),
                      (3, u'I_0', u'counts'),
                      (8, u'Electron Yield', u''),
                      (9, u'Total Fluorescense Yield', u''),
                      (10, u'Fluorescense Yield 2nd window', u'counts')]),
           u'other': ([(1, None, None),
                      (9, u'Total Fluorescense Yield', u''),
                      (8, u'Electron Yield', u''),
                      (10, u'Fluorescense Yield 2nd window', u'counts')])
           }

ID4_MAPPING={
             u'7T Sample Z': u'Z',
             u'Magnet X': u'X',
             u'Magnet Y': u'Y',
             u'SGM1:Energy': u'E',
             u'M3C DS Y': u'Mirror Y_{M3C DS Y}',
             }
