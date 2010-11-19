# -*- encoding: utf-8 -*-
'''
 Some general settings for the SQUID sessions
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# Diamagnetic correction applied to every measurement (for example the used sample holder)
dia_mag_correct=0

# Options for the squid raw data fit function
squid_coil_distance=1.5 # distance of squid coils from center in cm
squid_factor=0.00057486103 # scalation factor to calculate the mag. moment

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
['H','Oe',1e-4,0,'µ_0·H','T'],\
['emu',1e-3,0,'A·m^2'],\
['s',1./60,0,'min']\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[\
['T',1000,0,'mT']\
]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ 'Name in file' , 'column to map to' , [ 'dimension' , 'unit' ]]
COLUMNS_MAPPING=[\
['Time',0,['time','s']]\
,['Time Stamp (sec)',0,['time','s']]\
,['Magnetic Field (Oe)',1,['H','Oe']]\
,['Field (Oe)',1,['H','Oe']]\
,['Temperature (K)',2,['T','K']]\
# RSO dat file
,['Long Moment (emu)',3,['M_{rso}','emu'], 'Long Scan Std Dev']\
#,['Long Scan Std Dev',4,['delta_M','emu']]\
# AC dat file
,["m' (emu)",3,['M_{ac}','emu']]\
,["m' Scan Std Dev",4,['delta_M','emu']]\
# Torque magnetometer
,['Torque (Nm)',3,['Torque','Nm']]\
,['Torque Std. Dev. (Nm)',4,['δTorque','Nm']]\
,["Sample Position (deg)", 5, ['φ', '°']]\
# AC PPMS dat file
,["M' (emu)",7,["M\\047{ac}",'emu']]\
,["M'' (emu)",8,["M\\047\\047_{ac}",'emu']]\
,["M-Std.Dev. (emu)",4,['delta_M','emu']]\
# VSM PPMS dat file
,["Moment (emu)",3,["M",'emu']]\
,['M. Std. Err. (emu)',4,['delta_M','emu']]\
# for RSO raw data files
,['Start Temperature (K)',2,['T','K']]\
,['Position (cm)',3,['pos','cm']]\
,['Long Voltage',10,['V_{long}','V']]\
,['Long Regression Fit',5,['V_{Fit}','V']]\
,['Long Reg Fit',5,['V_{Fit}','V']]\
,['Long Average Voltage', 6, ['V_{avrg}', 'V']]\
,['End Temperature (K)',7,['T_{End}','V']]\
,["M'' (emu)",8,["M2_{ac}",'emu']]\
,["Frequency (Hz)",6,["Frequency",'Hz']]\
,['Long Detrended Voltage',8,['V_{det}','V']]\
,['Long Demeaned Voltage', 9, ['V_{dem}', 'V']]\
,['Long Scaled Response',4,['V_{SC-long}','V']]\
,['Long Avg. Scaled Response', 11, ['V_{SC-avrg}', 'V']]\
,['Long Voltmeter Gain', 11, ['Range', '']]
]
# Measurement types where some parameters are fix and x,y and yerror columns are set.
# [ 'list of constant parameters [ column , max_div , {same direction} ]' , x-col, y-col, div_y-col , plot options]
# The first measurement fitting is used (so you should put stricter rules before others).
# If no type fits the data collected nothing will be plotted. 
# Diviations are only compared with last datapoint, so slow increases won't trigger a new sequence.
MEASUREMENT_TYPES=[\
# raw data, sequence have same time stamp, temperature should be shown for every sequence (div=300K always true)
[[['T',300.],['time',1.]], 3, 4, 4,''],\
# phi scan of e.g. torque magnetometer
[[['T', 300.]], 2, 'Torque', 'δTorque',''],\
# MvsT, H is constant
[[['H',1.]],2,3,4,''],\
# MvsH T is constant
[[['T',0.25]],1,3,4,'']\
]

# Split sequences after readout [list_for_scantype, split_by, split_sensitivity]
SPLIT_AFTER=[
             ["M\\047{ac}",'Frequency', 5.], 
             ["T",'DIRECTION', 0.25], 
             ["T",'φ', 2.], 
             ]

# permanent datafilters applied, a list of
# ( column , from , to , include )
filters=[\
#(4,0,5e-10,True)\
]
