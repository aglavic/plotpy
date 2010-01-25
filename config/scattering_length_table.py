#!/usr/bin/env python
''' 
  A table of compounds and their scattering length density for x-ray K_alpha and Neutrons.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Esther Pfuhl", "Paul Zakalek"]
__license__ = "None"
__version__ = "0.6.1beta"
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
    'Al':[2.08, 3.63e-5, 0.],
    'Si':[2.15, 1.44e-5, 0.],
    'Ti':[-1.95, 9.17e-4, 0.],
    'Cr':[2.99, 6.85e-4, 0.],
    'Mn':[-2.95, 2.78e-3, 0.],
    'Fe': [8.09, 5.50e-4, 5.12],
    'Co':[2.3, 8.85e-3, 4.24],
    'Cu':[6.53, 8.61e-4, 0.],
    'Ge':[3.64, 2.68e-4, 0.],
    'Sr':[1.25, 5.79e-5, 0.],
    'Y':[1.37, 6.77e-5, 0.],
    'Nb':[3.91, 1.62e-4, 0.],
    'Mo':[4.45, 4.15e-4, 0.],
    'Pd': [4.01, 1.26e-3, 0.],
    'Ag': [3.5, 9.77e-3, 0.],
    'Cd':[2.32, 5.69e-1, 0.],
    'In':[1.56, 2.04e-2, 0.],
    'La':[2.21, 6.54e-4, 0.],
    'Gd':[2.89, 2.82, 0.],
    'Tb':[2.33, 3.8e-3, 0.],
    'Dy':[5.36, 8.52e-2, 0.],
    'Ho':[2.59, 7.41e-3, 0.],
    'Er':[2.65, 1.83e-2, 0.],
    'Yb':[3.03, 3.39e-3, 0.],
    'Lu':[2.44, 1.31e-2, 0.],
    'Pt':[6.29, 1.53e-3, 0.],
    'Au': [4.5, 1.56e-2, 0.],
    'Tl':[3.07, 3.23e-4, 0.],
    'Pb':[3.1, 1.53e-5, 0.],
    'Al2O3':[5.7, 2.81e-5, 0.],
}