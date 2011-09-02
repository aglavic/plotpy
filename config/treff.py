# -*- encoding: utf-8 -*-
'''
 Some general settings for the treff sessions
'''

from math import pi
import numpy

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.10"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

# map of line/column indices for the detector raw data files (256*256 points)
DETECTOR_PIXELS=256
CENTER_PIXEL=130.8
CENTER_PIXEL_Y=128.5
DETECTOR_ROWS_MAP=[[j+i*DETECTOR_PIXELS for i in range(DETECTOR_PIXELS)] for j in range(DETECTOR_PIXELS)]
DETECTOR_REGION=(0, 256, 0, 256)
PIXEL_WIDTH=0.014645
LAMBDA_N=4.75

PI_4_OVER_LAMBDA=4*pi/LAMBDA_N
GRAD_TO_MRAD=pi/180.*1000.
GRAD_TO_RAD=pi/180.

# Files to combine for the pnr_multi.f90 program
PROGRAM_FILES=[ 'fit_pnr_mult_newcons.f90', 
                'levenberg_rough_newcons_treff.f90', 
                'param_mult.f90', 
                'polref_sp_rough.f90', 
                'read_mrad_sim_rough_treff.f90', 
                'refconv_illu.f90', 
                'calchi_treff.f90']
PROGRAM_PARAMETER_FILE='parameters_module.f90'
REF_FILE_ENDINGS=['uu', 'dd', 'ud', 'du']
FIT_OUTPUT_FILES=['simulation_pp', 'simulation_mm', 'simulation_pm', 'simulation_mp']
RESULT_FILE='result'

# D17 Instrument options
# Correction fiels
D17_CALIBRATION_FILES={'water': None,#"/home/glavic/tmp/d17/Water/016295",  
                       'transmission': None,#"/home/glavic/tmp/d17/transmission/025258"
                       }
# Lower and Upper Bounds of the detector to use
D17_MASK_BOUNDS_Y=(20, 51)
D17_MASK_BOUNDS_X=(28, 237)
# Define the integration mask of the detector, a 64x265 matrix of 0 and 1
D17_MASK=None #((numpy.zeros((64, 256))+1).transpose()*numpy.where((numpy.arange(0, 64)>=D17_MASK_BOUNDS_Y[0])*\
               #     (numpy.arange(0, 64)<=D17_MASK_BOUNDS_Y[1]), 1., 0.)).transpose()*\
               #     numpy.where((numpy.arange(0, 256)>=D17_MASK_BOUNDS_X[0])*\
               #     (numpy.arange(0, 256)<=D17_MASK_BOUNDS_X[1]), 1., 0.)
D17_PIXEL_SIZE=0.02225 # °
D17_CENTER_OFFSET=0.18846#0.225 # °
# compiler settings for fortran
FORTRAN_COMPILER='gfortran'
# compiler optimization options as can be found in the manual,
# add your cpu flag here to increase performance of the fit
# stdandard cpu flags are:
# i686 / pentium4 / athlon / k8 / amdfam10 (athlon64) / nocona (p4-64bit)
FORTRAN_COMPILER_OPTIONS='-O3'
# option to precompile every file
FORTRAN_PRECOMPILE_OPTION='-c'
FORTRAN_OUTPUT_OPTION='-o'
FORTRAN_COMPILER_MARCH=None #'-march=nocona'
