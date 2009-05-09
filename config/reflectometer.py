#!/usr/bin/env python
'''
  Some general settings for the reflectometer plotting script 'plot_reflectometer_data.py' 
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
TRANSFORMATIONS=[\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ 'Name in file' , 'column to map to' , [ 'dimension' , 'unit' ]]
DATA_COLUMNS={\
'THETA':['Theta','\\302\\260']\
,'2THETA':['2 Theta','\\302\\260']\
,'PHI':['Phi','\\302\\260']\
,'COUPLED':['2 Theta','\\302\\260']\
,'COUNTS':['Intensity','counts']\
,'STEPTIME':['Time per Step','s']\
,'AUX1':['z','mm']
,'AUX3':['KEC','mm']
}

# how to call the fit-script
FIT_SCRIPT_COMMAND='fit-script'