# -*- encoding: utf-8 -*-
'''
  Transformations for physical units.
'''

from math import pi

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

known_transformations=[
                      # magnetism
                      ['H','Oe',1e-4,0,'μ_0·H','T'],
                      ['2 Theta','°',2 , 0, 'Theta', '°'], 
                      ['2 Theta','rad',2 , 0, 'Theta', 'rad'], 
                      ['2 Theta','mrad',2 , 0, 'Theta', 'mrad'], 
                      ['emu',1e-3,0,'A·m²'],
                      # time
                      ['h', 24, 0, 'd'], 
                      ['min',1./60,0,'h'], 
                      ['s',1./60,0,'min'], 
                      ['s',1./1000,0,'ms'], 
                      # length
                      ['m',1./1000,0,'km'], 
                      ['mm',1./1000,0,'m'], 
                      ['cm',1./100,0,'m'], 
                      ['μm',1./1000,0,'mm'], 
                      ['nm',1./1000,0,'μm'], 
                      ['A',1./10,0,'nm'], 
                      # angle
                      ['°',pi/180,0,'rad'], 
                      ['rad',1000.,0,'mrad'], 
                      # temperature
                      ['K', 1, -273.15, '°C']
                      ]