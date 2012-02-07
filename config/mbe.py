# -*- encoding: utf-8 -*-
'''
  Configurations for the kws2 file import.
'''

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

from config import user_config

#Å^{-1}·eV^{1/2} - electron wavelength factor for 1/sqrt(energy in eV)
H_over_2m=12.26426

if not 'LEED' in user_config:
  user_config['LEED']=dict(
                SCREEN_SIZE=350.,
                SCREEN_X=220.,
                SCREEN_Y=380.,
                DISTANCE=300.,
                PIXEL_SIZE=650.,
                           )

if not 'RHEED' in user_config:
  user_config['RHEED']=dict(
                SCREEN_SIZE=200.,
                SCREEN_PIXELS=620.,
                DISTANCE=350.,
                CENTER_X=-50.,
                CENTER_Y=255.,
                ENERGY=15000.,
                           )

O_ENERGY=503.
