# -*- encoding: utf-8 -*-
''' 
 A table of elements, their diamagnetic moment per mol and elemental weight.
'''

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# ['name',mol mass,mol dia(10^-6emu/Oe/mol)]
#
# Values from Kalzium elemental table and G.A.Bain and J.F.Berry J.Chem.Edu. Vol.85 No.4 (2008)
ELEMENT_DIA=[\
# Anions
['O',15.9994,12]\
,['F',18.9984032,9.1]\
,['S',32.065,30]\
# Cations
,['Al',26.9815386,2]\
# Alkalines
,['Be',9.012182,0.4]\
,['Mg',24.305,5]\
,['Ca',40.078,10.4]\
,['Sr',87.62,19]\
,['Ba',137.327,26.5]\
# transition metals
,['Cr',51.9961,15]\
,['Cr2+',51.9961,15]\
,['Cr3+',51.9961,11]\
,['Cr4+',51.9961,8]\
,['Cr5+',51.9961,5]\
,['Cr6+',51.9961,3]\
,['Mn',54.938045,10]\
,['Mn2+',54.938045,14]\
,['Mn3+',54.938045,10]\
,['Mn4+',54.938045,8]\
,['Mn6+',54.938045,4]\
,['Mn7+',54.938045,3]\
,['Fe',55.845,13]\
,['Fe2+',55.845,13]\
,['Fe3+',55.845,10]\
,['Co',58.933195,12]\
,['Co2+',58.933195,12]\
,['Co3+',58.933195,10]\
,['Ni',58.6934,12]\
,['Cu',63.546,12]\
,['Cu+',63.546,12]\
,['Cu2+',63.546,11]\
,['Y',88.90585,12]\
# Lantanides
,['La',138.90547,20]\
,['Ce',140.116,20]\
,['Ce3+',140.116,20]\
,['Ce4+',140.116,17]\
,['Pr',140.90765,27]\
,['Pr3+',140.90765,27]\
,['Pr4+',140.90765,20]\
,['Nd',144.242,20]\
,['Pm',145,18]\
,['Sm',150.36,23]\
,['Sm2+',150.36,23]\
,['Sm3+',150.36,20]\
,['Eu',151.964,22]\
,['Eu2+',151.964,22]\
,['Eu3+',151.964,20]\
,['Gd',157.25,20]\
,['Tb',158.92535,19]\
,['Tb3+',158.92535,19]\
,['Tb4+',158.92535,17]\
,['Dy',162.5,19]\
,['Ho',164.93032,19]\
,['Er',167.259,18]\
,['Tm',168.93421,18]\
,['Yb',173.04,20]\
,['Yb2+',173.04,20]\
,['Yb3+',173.04,18]\
,['Lu',174.967,17]\
]
