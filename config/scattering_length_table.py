#!/usr/bin/env python
''' 
  A table of compounds and their scattering length density for x-ray K_alpha.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# {'name': [sl_density,delta/beta]}
#
# 
SCATTERING_LENGTH_DENSITIES={\
    'GaAs': [14.5511,33.391],
    'Ag': [29.4355,11.058],
    'Fe': [22.4640,7.744],
    'FeO': [23.118,10.145],
    'Fe2O3': [23.3472,11.327],
    'Fe3O4': [23.2762,10.934],
    'Cr': [21.1332,9.771],
    'TbMnO3': [19.194,8.9],
    'SrTiO3': [7.457,22.02],
    'LaCoO3': [16.794,7.775],
    'YAlO3': [13.4114,30.8]
}

#
# {'name': [Nb', Nb'', Np]}
#
# 
NEUTRON_SCATTERING_LENGTH_DENSITIES={\
    'Au': [2.17, 0.0075, 0.],
    'Fe': [4.70, 0.000698, 5.12],
    'Ag': [2.4, 0.00760, 0.],
}

