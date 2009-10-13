#!/usr/bin/env python
''' 
  A table of compounds and their scattering length density for x-ray K_alpha and Neutrons.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Esther Pfuhl"]
__license__ = "None"
__version__ = "0.6b1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# {'name': [sl_density,delta/beta]}
#
# 
SCATTERING_LENGTH_DENSITIES={
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
    'YAlO3': [13.4114,30.8],
    'Tb': [18.543,6.0665],
    'Er': [20.288,14.2753],
    'Nb': [24.187,16.3271],
    'Y': [12.443,1.8362],
    'Al2O3': [12.624,86.4658],
    'Y2O3':[0.9287,23.51]
}

#
# {'name': [Nb', Nb'', Np]}
#
# 
NEUTRON_SCATTERING_LENGTH_DENSITIES={
    'Au': [2.17, 0.0075, 0.],
    'Fe': [4.70, 0.000698, 5.12],
    'Ag': [2.4, 0.00760, 0.],
    'Er':[2.57, 1.83e-2, 0.],
    'Tb':[2.33, 3.8e-3, 0.],
    'Y':[1.37, 6.77e-5, 0.],
    'Nb':[3.91, 1.62e-4, 0.],
    'Al2O3':[5.7, 2.81e-5, 0.],
}

