#!/usr/bin/env python
'''
  Transformations for physical units.
'''

from math import pi

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6.1beta"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

known_transformations=[
                      # magnetism
                      ['H','Oe',1e-4,0,'\316\274_0\302\267H','T'],
                      ['2 Theta','\302\260',2 , 0, 'Theta', '\302\260'], 
                      ['2 Theta','rad',2 , 0, 'Theta', 'rad'], 
                      ['2 Theta','mrad',2 , 0, 'Theta', 'mrad'], 
                      ['emu',1e-3,0,'A\302\267m\302\262'],
                      # time
                      ['h', 24, 0, 'd'], 
                      ['min',1./60,0,'h'], 
                      ['s',1./60,0,'min'], 
                      ['s',1./1000,0,'ms'], 
                      # length
                      ['m',1./1000,0,'km'], 
                      ['mm',1./1000,0,'m'], 
                      ['cm',1./100,0,'m'], 
                      ['\\316\\274m',1./1000,0,'mm'], 
                      ['nm',1./1000,0,'\\316\\274m'], 
                      ['A',1./10,0,'nm'], 
                      # angle
                      ['\302\260',pi/180,0,'rad'], 
                      ['rad',1000.,0,'mrad'], 
                      # temperature
                      ['K', 1, -273.15, '\302\260C']
                      ]
