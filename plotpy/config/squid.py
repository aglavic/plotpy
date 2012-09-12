# -*- encoding: utf-8 -*-
'''
 Some general settings for the SQUID sessions
'''

# Diamagnetic correction applied to every measurement (for example the used sample holder)
dia_mag_correct=0

# Options for the squid raw data fit function
squid_coil_distance=1.5 # distance of squid coils from center in cm
squid_factor=0.00057486103 # scalation factor to calculate the mag. moment

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
[u'H', u'Oe', 1e-4, 0, u'µ_0·H', u'T'], \
[u'emu', 1e-3, 0, u'A·m^2'], \
[u's', 1./60, 0, u'min']\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[\
[u'T', 1000, 0, u'mT']\
]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ u'Name in file' , u'column to map to' , [ u'dimension' , u'unit' ]]
COLUMNS_MAPPING=[\
[u'Time', 0, [u'Time', u's']]\
, [u'Time Stamp (sec)', 0, [u'Time', u's']]\
, [u'Magnetic Field (Oe)', 1, [u'H', u'Oe']]\
, [u'Field (Oe)', 1, [u'H', u'Oe']]\
, [u'Temperature (K)', 2, [u'T', u'K']]\
# RSO dat file
, [u'Long Moment (emu)', 3, [u'M_{rso}', u'emu'], u'Long Scan Std Dev']\
#,[u'Long Scan Std Dev',4,[u'delta_M',u'emu']]\
# AC dat file
, [u"m' (emu)", 3, [u'M_{ac}', u'emu'], u"m' Scan Std Dev"]\
#,[u"m' Scan Std Dev",4,[u'delta_M',u'emu']]\
# Torque magnetometer
, [u'Torque (Nm)', 3, [u'Torque', u'Nm'], u'Torque Std. Dev. (Nm)']\
#,[u'Torque Std. Dev. (Nm)',4,[u'δTorque',u'Nm']]\
, [u"Sample Position (deg)", 5, [u'φ', u'°']]\
# AC PPMS dat file
, [u"M' (emu)", 7, [u"M\\047{ac}", u'emu', u"M-Std.Dev. (emu)"]]\
, [u"M'' (emu)", 8, [u"M\\047\\047_{ac}", u'emu']]\
#,[u"M-Std.Dev. (emu)",4,[u'delta_M',u'emu']]\
# VSM PPMS dat file
, [u"Moment (emu)", 3, [u"M", u'emu'], u'M. Std. Err. (emu)']\
#,[u'M. Std. Err. (emu)',4,[u'delta_M',u'emu']]\
# for RSO raw data files
, [u'Start Temperature (K)', 2, [u'T', u'K']]\
, [u'Position (cm)', 3, [u'pos', u'cm']]\
, [u'Long Voltage', 10, [u'V_{long}', u'V']]\
, [u'Long Regression Fit', 5, [u'V_{Fit}', u'V']]\
, [u'Long Reg Fit', 5, [u'V_{Fit}', u'V']]\
, [u'Long Average Voltage', 6, [u'V_{avrg}', u'V']]\
, [u'End Temperature (K)', 7, [u'T_{End}', u'V']]\
, [u"M'' (emu)", 8, [u"M2_{ac}", u'emu']]\
, [u"Frequency (Hz)", 6, [u"Frequency", u'Hz']]\
, [u'Long Detrended Voltage', 8, [u'V_{det}', u'V']]\
, [u'Long Demeaned Voltage', 9, [u'V_{dem}', u'V']]\
, [u'Long Scaled Response', 4, [u'V_{SC-long}', u'V']]\
, [u'Long Avg. Scaled Response', 11, [u'V_{SC-avrg}', u'V']]\
, [u'Long Voltmeter Gain', 11, [u'Range', u'']]
]
# Measurement types where some parameters are fix and x,y and yerror columns are set.
# [ u'list of constant parameters [ column , max_div , {same direction} ]' , x-col, y-col, div_y-col , plot options]
# The first measurement fitting is used (so you should put stricter rules before others).
# If no type fits the data collected nothing will be plotted. 
# Diviations are only compared with last datapoint, so slow increases won't trigger a new sequence.
MEASUREMENT_TYPES=[\
# raw data, sequence have same time stamp, temperature should be shown for every sequence (div=300K always true)
[[[u'T', 300.], [u'Time', 1.]], 3, 4, 4, u''], \
# phi scan of e.g. torque magnetometer
[[[u'T', 300.]], 2, u'Torque', u'δTorque', u''], \
# MvsT, H is constant
[[[u'H', 1.]], 2, 3, 4, u''], \
# MvsH T is constant
[[[u'T', 0.25]], 1, 3, 4, u'']\
]

# Split sequences after readout [list_for_scantype, split_by, split_sensitivity]
SPLIT_AFTER=[
             [u"M\\047{ac}", u'Frequency', 5.],
             [u"T", u'DIRECTION', 0.25],
             [u"T", u'φ', 2.],
             ]

# permanent datafilters applied, a list of
# ( column , from , to , include )
filters=[\
#(4,0,5e-10,True)\
]
