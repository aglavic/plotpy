# -*- encoding: utf-8 -*-
'''
 Some general settings for the treff sessions
'''

from numpy import pi

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
D17_CALIBRATION_FILES={'water': None, #"/home/glavic/tmp/d17/Water/016295",  
                       'transmission': None, #"/home/glavic/tmp/d17/transmission/025258"
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

# detector calibration file measured for TREFF
DETECTOR_CALIBRATION=[ 0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.00519771, 0.12980382, 0.25440993,
        0.37901604, 0.46092573, 0.52698769, 0.57942404, 0.61757601,
        0.65419695, 0.68783214, 0.71649243, 0.72959829, 0.74821644,
        0.77008311, 0.79454877, 0.79822969, 0.80196493, 0.81704896,
        0.83243988, 0.84432779, 0.84587484, 0.84861623, 0.85306536,
        0.86766828, 0.87505847, 0.87643147, 0.87400821, 0.87612933,
        0.88859031, 0.88974808, 0.88564601, 0.89940434, 0.9121687 ,
        0.92307362, 0.91645687, 0.90569918, 0.90684795, 0.91207634,
        0.92315074, 0.91643291, 0.9078226 , 0.91777371, 0.92557986,
        0.93100837, 0.92301722, 0.91574606, 0.91920269, 0.92228262,
        0.92501667, 0.91504773, 0.90303779, 0.89688882, 0.89214565,
        0.88891484, 0.88313054, 0.86974972, 0.86020682, 0.85633217,
        0.85536051, 0.85740566, 0.85214447, 0.84212973, 0.83827359,
        0.83682164, 0.84540166, 0.8568684 , 0.85755056, 0.85716968,
        0.8605902 , 0.86566301, 0.87749627, 0.88913994, 0.8883501 ,
        0.88756026, 0.88677042, 0.89571641, 0.9111177 , 0.91193119,
        0.91014625, 0.90609756, 0.91392047, 0.93539514, 0.94181765,
        0.9437831 , 0.94653063, 0.95207424, 0.96160944, 0.96487344,
        0.96676572, 0.97579204, 0.98581963, 0.99728758, 0.99953665,
        0.99750653, 0.98709397, 0.98623272, 0.99571509, 0.99851634,
        0.99713522, 0.98533305, 0.97660705, 0.96994913, 0.9608312 ,
        0.95050333, 0.93791225, 0.92970865, 0.92327037, 0.91185209,
        0.90029798, 0.88856694, 0.87737586, 0.86582898, 0.85141641,
        0.83829833, 0.8265209 , 0.81186342, 0.79655206, 0.7829297 ,
        0.77375539, 0.77641145, 0.77485073, 0.76863282, 0.76658976,
        0.76697847, 0.76876855, 0.77096946, 0.76583649, 0.7605838 ,
        0.76063147, 0.76228121, 0.77099862, 0.77833196, 0.7831567 ,
        0.78467742, 0.78374623, 0.79030454, 0.79791561, 0.79471005,
        0.79298365, 0.79381587, 0.80492711, 0.82206709, 0.81465193,
        0.81047168, 0.81311728, 0.81658718, 0.82021365, 0.81242642,
        0.80788582, 0.80825766, 0.80743701, 0.80536874, 0.79890372,
        0.79837249, 0.8022989 , 0.80586848, 0.80409883, 0.79246284,
        0.7879309 , 0.78791126, 0.79806883, 0.79504058, 0.7841025 ,
        0.76906511, 0.76330734, 0.76223683, 0.75670502, 0.75263213,
        0.74394544, 0.70990952, 0.34335612, 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        ,
        0.        , 0.        , 0.        , 0.        , 0.        , 0.        ]
