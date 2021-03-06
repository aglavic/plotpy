# -*- encoding: utf-8 -*-
'''
  Some general settings for the reflectometer sessions
'''

# import modules
import os

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ 'Name in file' , 'column to map to' , [ 'dimension' , 'unit' ]]
DATA_COLUMNS={
            'THETA':        ['Θ', '°']
            , '2THETA':      ['2Θ', '°']
            , 'PHI':         ['φ', '°']
            , 'COUPLED':     ['2Θ', '°']
            , 'COUNTS':      ['Intensity', 'counts']
            , 'STEPTIME':    ['Time per Step', 's']
            , 'AUX1':        ['z', 'mm']
            , 'AUX3':        ['KEC', 'mm']
            }

# how to call the fit-script
FIT_SCRIPT_COMMAND='fit-script'

# compiler settings for fortran
FORTRAN_COMPILER='gfortran'
# compiler optimization options as can be found in the manual,
# add your cpu flag here to increase performance of the fit
# stdandard cpu flags are:
# i686 / pentium4 / athlon / k8 / amdfam10 (athlon64) / nocona (p4-64bit)
FORTRAN_COMPILER_OPTIONS='-O3'
FORTRAN_COMPILER_MARCH=None #'-march=nocona' #
FIT_PROGRAM_CODE_FILE=os.path.join('config', 'fit', 'fit.f90')
RESULT_FILE='fit_temp.ref'