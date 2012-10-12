#-*- coding: utf-8 -*-
'''
  Collection of physical constants.
'''

from numpy import pi as _pi
from mds import PhysicalConstant as _C

h=_C(6.6260693e-31, u'g·m²/s', 'h', 'Planck') # 
hbar=_C(1.0545717e-31, u'g·m²/s', 'h-bar', u'Planck over 2π')

c=_C(2.9979246e8, u'm/s', 'c', 'speed of light') # 
e=_C(1.6021765e-19, 'A·s', 'e', 'elemental charge') # 

N_a=_C(6.0221415e23, 'mol^-1', 'N_a', 'Avogadro')
u=_C(1.66054e-24, 'g', 'u', 'atomic mass unit')
k_B=_C(1.3806505e-20, u'g·m²/(K·s²)', 'k_B', 'Boltzmann constant')
R=_C(8.314472e3, r'g·m²/(K·mol·s²)', 'R', 'ideal gas constant')

m_e=_C(9.1094e-28, 'g', 'm_e', 'electron mass')
m_n=_C(1.67493e-24, 'g', 'm_n', 'neutron mass')

r_e=_C(2.81794e-15, 'm', 'r_e', 'classical electron radius')
r_0=_C(5.291772e-11, 'm', 'r_0', 'Bohr radius')

mu_0=_C(_pi*4e-7, u'V·s/(A·m)', u'µ_0', 'permeability of the free space')
epsilon_0=_C((1./(mu_0*c**2))%u'A·s/(V·m)', u'A·s/(V·m)',
             u'ε_0', 'permittivity of the free space')

mu_B=_C(9.2740095e-24, u'A·m²', u'µ_B', 'Bohr magneton')
mu_n=_C(-9.6623641e-27, u'A·m²', u'µ_n', 'neutron magnetic moment')
mu_nuc=_C(5.0507834e-27, u'A·m²', u'µ_nuc', 'nuclear magneton')

Phi_0=_C(2.0678337e-12, u'g·m²/(A·s²)', u'Φ_0', 'magnetic flux quant')
