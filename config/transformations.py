# -*- encoding: utf-8 -*-
'''
  Transformations for physical units.
'''

from math import pi

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

# define transformations that can be used to convert units
known_unit_transformations={
                            # angle
                            ('rad', 'mrad'): (1.e3, 0.),
                            ('rad', '°'): (180./pi, 0.),
                            # length
                            ('Å', 'nm'): (1.e-1, 0.),
                            ('nm', 'µm'): (1.e-3, 0.),
                            ('µm', 'mm'): (1.e-3, 0.),
                            ('mm', 'm'): (1.e-3, 0.),
                            ('m', 'km'): (1.e-3, 0.),
                            ('cm', 'm'): (1.e-2, 0.),
                            ('dm', 'm'): (1.e-1, 0.),
                            # temperature
                            ('mK', 'K'): (1.e-3, 0.),
                            ('K', '°C'): (1.,-273.15),
                            # time
                            ('d', 'h'): (24., 0.),
                            ('min', 'h'): (1./60., 0.),
                            ('s', 'min'): (1./60., 0.),
                            ('s', 'ms'): (1.e3, 0.),
                            ('µs', 'ms'): (1.e-3, 0.),
                            # magnetism
                            ('emu', 'A·m^2'): (1.e-3, 0.),
                            ('mT', 'T'): (1.e-3, 0.),
                            ('Oe', 'T'): (1.e-4, 0., 'H', 'μ_0·H')
                            }

known_transformations=[
                      # magnetism
                      ['H', 'Oe', 1e-4, 0, 'µ_0·H', 'T'],
                      ['emu', 1e-3, 0, 'A·m^2'],
                      # time
                      ['h', 24, 0, 'd'],
                      ['min', 1./60, 0, 'h'],
                      ['s', 1./60, 0, 'min'],
                      ['s', 1./1000, 0, 'ms'],
                      # length
                      ['m', 1./1000, 0, 'km'],
                      ['mm', 1./1000, 0, 'm'],
                      ['cm', 1./100, 0, 'm'],
                      ['µm', 1./1000, 0, 'mm'],
                      ['nm', 1./1000, 0, 'µm'],
                      ['Å', 1./10, 0, 'nm'],
                      # angle
                      ['°', pi/180, 0, 'rad'],
                      ['rad', 1000., 0, 'mrad'],
                      ['2Θ', '°', 0.5 , 0, 'Θ', '°'],
                      ['2Θ', 'rad', 0.5 , 0, 'Θ', 'rad'],
                      ['2Θ', 'mrad', 0.5 , 0, 'Θ', 'mrad'],
                      # temperature
                      ['K', 1,-273.15, '°C']
                      ]
