# -*- encoding: utf-8 -*-
''' 
  A table of compounds and their scattering length density for x-ray K_alpha and Neutrons.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Esther Pfuhl", "Paul Zakalek"]
__license__ = "GPL v3"
__version__ = "0.7.9"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# {'name': [sl_density,delta/beta]}
#
# 
SCATTERING_LENGTH_DENSITIES={
  #     All values given here are calculated using crystal structures from
  #     the ICSD database and the index of Refraction calculator at 
  #     http://henke.lbl.gov/ .
  # semiconductors:
    'GaAs': [14.543, 33.4117], 
    'Si': [7.57547, 43.83831], 
  # metals:
    'Ag': [29.43313, 11.06523],
    'Cr': [20.905, 9.77735],
    'Er': [20.43544, 14.27319],
    'Fe': [22.452, 7.7493],
    'Nb': [24.34427, 16.33058],
    'Tb': [18.57305, 6.06786],
    'Y': [12.47608, 18.36523],
  # oxides:
    'FeO': [17.117, 10.15169],
    'Fe2O3': [15.57389, 11.3341],
    'Fe3O4': [15.36298, 10.94133],
    'Y2O3':[14.50101, 23.52424],
    'Al2O3': [12.63875, 86.33993],
    'DyMnO3': [19.59296, 8.15930],
    'TbMnO3': [19.339, 8.6],
    'LaCoO3': [21.801, 7.7804],
    'YAlO3': [15.923, 31.0272],
    'BaTiO3': [16.78458, 9.22838],
    'EuTiO3': [17.71187, 7.31787],
    'SrTiO3': [15.01150, 22.03151],
    'DyScO3': [17.53474, 8.75332],
    'GdScO3': [17.02964, 6.70421],
    'LSMO 0.1':[16.27891, 15.80883],
    'LSMO 0.5':[17.62232, 10.90424],
    'LSMO 0.6':[17.74971, 10.18752],
    'LSMO 0.7.1':[18.03254, 9.58077],
    'LSMO 0.8':[18.26688, 9.06048],
    'LSMO 0.9':[18.48490, 8.60941],
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
