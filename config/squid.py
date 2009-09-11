#!/usr/bin/env python
'''
 Some general settings for the SQUID plotting script 'plot_SQUID_data.py'
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# Diamagnetic correction applied to every measurement (for example the used sample holder)
dia_mag_correct=0


# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
['H','Oe',1e-4,0,'\316\274_0\302\267H','T'],\
['emu',1e-3,0,'A\302\267m\302\262'],\
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
,['Long Moment (emu)',3,['M_{rso}','emu']]\
,['Long Scan Std Dev',4,['delta_M','emu']]\
# AC dat file
,["m' (emu)",3,['M_{ac}','emu']]\
,["m' Scan Std Dev",4,['delta_M','emu']]\
# AC PPMS dat file
,["M' (emu)",3,["M_{ac}",'emu']]\
,["M-Std.Dev. (emu)",4,['delta_M','emu']]\
# VSM PPMS dat file
,["Moment (emu)",3,["M_{vsm}",'emu']]\
,['M. Std. Err. (emu)',4,['delta_M','emu']]\
# for RSO raw data files
,['Start Temperature (K)',2,['T','K']]\
,['Position (cm)',3,['pos','cm']]\
,['Long Voltage',4,['V_{long}','V']]\
,['Long Reg Fit',5,['Fit','V']]\
,['End Temperature (K)',6,['T_{End}','V']]\
,["M'' (emu)",7,["M2_{ac}",'emu']]\
,["Frequency (Hz)",7,["Frequency",'Hz']]\
]
# Measurement types where some parameters are fix and x,y and yerror columns are set.
# [ 'list of constant parameters [ column , max_div ]' , x-col, y-col, div_y-col , plot options]
# The first measurement fitting is used (so you should put stricter rules before others).
# If no type fits the data collected nothing will be plotted. 
# Diviations are only compared with last datapoint, so slow increases won't trigger a new sequence.
MEASUREMENT_TYPES=[\
# raw data, sequence have same time stamp, temperature should be shown for every sequence (div=300K always true)
[[[2,300],[0,1]],3,4,4,''],\
# MvsT, H is constant
[[[1,1]],2,3,4,''],\
# MvsH T is constant
[[[2,0.25]],1,3,4,'set key outside\n']\
]

# permanent datafilters applied, a list of
# ( column , from , to , include )
filters=[\
#(4,0,5e-10,True)\
]
