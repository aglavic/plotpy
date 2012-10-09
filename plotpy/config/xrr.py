# -*- encoding: utf-8 -*-
'''
  Some general settings for the reflectometer sessions
'''

# import modules
import os

__author__=u"Artur Glavic"
__credits__=[]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__=u"Production"

# Transformations for differnt units to be made ( [(from_dim,)from_unit,a,b,(to_dim,)to_unit] to=a*from+b)
TRANSFORMATIONS=[\
]
# Transformations for constants (see MEASUREMENT_TYPES)
TRANSFORMATIONS_CONST=[]
# Select the read parameters and mapping to columns as well as dimensions and units 
#  (every measurement file the positions have to start with 0 and have no holes in between
# [ u'Name in file' , u'column to map to' , [ u'dimension' , u'unit' ]]
DATA_COLUMNS={
            u'THETA':        [u'Θ', u'°']
            , u'2THETA':      [u'2Θ', u'°']
            , u'PHI':         [u'φ', u'°']
            , u'COUPLED':     [u'2Θ', u'°']
            , u'COUNTS':      [u'Intensity', u'counts']
            , u'STEPTIME':    [u'Time per Step', u's']
            , u'AUX1':        [u'z', u'mm']
            , u'AUX3':        [u'KEC', u'mm']
            }

# how to call the fit-script
FIT_SCRIPT_COMMAND=u'fit-script'

# compiler settings for fortran
FORTRAN_COMPILER=u'gfortran'
# compiler optimization options as can be found in the manual,
# add your cpu flag here to increase performance of the fit
# stdandard cpu flags are:
# i686 / pentium4 / athlon / k8 / amdfam10 (athlon64) / nocona (p4-64bit)
FORTRAN_COMPILER_OPTIONS=u'-O3'
FORTRAN_COMPILER_MARCH=None #u'-march=nocona' #
FIT_PROGRAM_CODE_FILE=os.path.join(u'config', u'fit', u'fit.f90')
RESULT_FILE=u'fit_temp.ref'