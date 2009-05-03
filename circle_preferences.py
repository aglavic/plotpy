#!/usr/bin/env python
'''
 Some general settings for the 4circle plotting script 'plot_circle_data.py' 
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
transformations=[\
]
# Transformations for constants (see measurement_types)
transformations_const=[]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ 'Name in file' , 'column to map to' , [ 'dimension' , 'unit' ]]
columns_mapping=[\
['Two Theta',7,['2Theta','\\302\\260']]\
,['Theta',7,['Theta','\\302\\260']]\
,['Chi',7,['Chi','\\302\\260']]\
,['Phi',7,['Phi','\\302\\260']]\
,['H',0,['h','']]\
,['K',1,['k','']]\
,['L',2,['l','']]\
,['Epoch',3,['Epoch','']]\
,["Seconds",4,['time','s']]\
,["Monitor",5,['monitor intensity','counts']]\
,['Detector',6,['intensity','counts']]\
]
# Measurement types where some parameters are fix and x,y and yerror columns are set.
# [ 'list of constant parameters [ column , max_div ]' , x-col, y-col, div_y-col , plot options]
# The first measurement fitting is used (so you should put stricter rules before others).
# If no type fits the data collected nothing will be plotted. 
# Diviations are only compared with last datapoint, so slow increases won't trigger a new sequence.
measurement_types=[\
# Theta/2Theta/chi/phi scans
[[[7,500]],7,6,8,'']\
# h scan
,[[[1,0.005],[2,0.005]],0,6,7,'']\
# k scan
,[[[0,0.005],[2,0.005]],1,6,7,'']\
# l scan
,[[[0,0.005],[1,0.005]],2,6,7,'']\
# hk mesh
,[[[2,0.05]],0,1,7,'',6]\
# kl mesh
,[[[0,0.05]],1,2,7,'',6]\
# hl mesh
,[[[1,0.05]],0,2,7,'',6]\
,[[],0,6,7,'set title "Unknown Scan"\n']\
] # raw data measureing with temperature shown, MvsT with constand H,MvsH with constand T
