#!/usr/bin/env python
'''
 Some general settings for the treff sessions
'''

from math import pi

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

# map of line/column indices for the detector raw data files (256*256 points)
DETECTOR_ROWS_MAP=[[j+i*256 for i in range(256)] for j in range(256)]
PIXEL_WIDTH=0.014645
LAMBDA_TREFF=4.75

PI_4_OVER_LAMBDA=4*pi/LAMBDA_TREFF
GRAD_TO_MRAD=pi/180*1000
GRAD_TO_RAD=pi/180

# Files to combine for the pnr_multi.f90 program
PROGRAM_FILES=['fit_pnr_mult_newcons.f90', 'levenberg_rough_newcons.f90', 
'param_mult.f90', 'polref_sp_rough_noncoll.f90', 'read_mrad_sim_rough.f90', 
'refconv_illu.f90', 'calchi.f90']
REF_FILE_ENDINGS=['uu', 'dd', 'ud', 'du']
FIT_OUTPUT_FILES=['simulation_pp', 'simulation_mm', 'simulation_pm', 'simulation_mp']
RESULT_FILE='result'

# compiler settings for fortran
FORTRAN_COMPILER='gfortran'
# compiler optimization options as can be found in the manual,
# add your cpu flag here to increase performance of the fit
# stdandard cpu flags are:
# i686 / pentium4 / athlon / k8 / amdfam10 (athlon64) / nocona (p4-64bit)
FORTRAN_COMPILER_OPTIONS='-O3'
FORTRAN_COMPILER_MARCH=None #'-march=nocona'
