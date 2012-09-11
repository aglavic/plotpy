# -*- encoding: utf-8 -*-
'''
  Transformations for physical units.
'''

from math import pi

__author__=u"Artur Glavic"
__credits__=[]
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__=u"Production"

# define transformations that can be used to convert units
known_unit_transformations={
                            # angle
                            (u'rad', u'mrad'): (1.e3, 0.),
                            (u'rad', u'°'): (180./pi, 0.),
                            # length
                            (u'Å', u'nm'): (1.e-1, 0.),
                            (u'nm', u'µm'): (1.e-3, 0.),
                            (u'µm', u'mm'): (1.e-3, 0.),
                            (u'mm', u'm'): (1.e-3, 0.),
                            (u'm', u'km'): (1.e-3, 0.),
                            (u'cm', u'm'): (1.e-2, 0.),
                            (u'dm', u'm'): (1.e-1, 0.),
                            # reciprocal length
                            (u'Å^{-1}', u'nm^{-1}'): (10., 0.),
                            # temperature
                            (u'mK', u'K'): (1.e-3, 0.),
                            (u'K', u'°C'): (1.,-273.15),
                            # time
                            (u'd', u'h'): (24., 0.),
                            (u'h', u'min'): (60., 0.),
                            (u'min', u's'): (60., 0.),
                            (u's', u'ms'): (1.e3, 0.),
                            (u'ms', u'µs'): (1.e3, 0.),
                            # magnetism
                            (u'emu', u'A·m^2'): (1.e-3, 0.),
                            (u'mT', u'T'): (1.e-3, 0.),
                            (u'Oe', u'T'): (1.e-4, 0., u'H', u'μ_0·H')
                            }

known_transformations=[
                      # magnetism
                      [u'H', u'Oe', 1e-4, 0, u'µ_0·H', u'T'],
                      [u'emu', 1e-3, 0, u'A·m^2'],
                      # time
                      [u'h', 24, 0, u'd'],
                      [u'h', 60., 0, u'min'],
                      [u'min', 60., 0, u's'],
                      [u's', 1000., 0, u'ms'],
                      [u'ms', 1000., 0, u'µs'],
                      # length
                      [u'm', 1./1000, 0, u'km'],
                      [u'mm', 1./1000, 0, u'm'],
                      [u'cm', 1./100, 0, u'm'],
                      [u'µm', 1./1000, 0, u'mm'],
                      [u'nm', 1./1000, 0, u'µm'],
                      [u'Å', 1./10, 0, u'nm'],
                      # angle
                      [u'°', pi/180, 0, u'rad'],
                      [u'rad', 1000., 0, u'mrad'],
                      [u'2Θ', u'°', 0.5 , 0, u'Θ', u'°'],
                      [u'2Θ', u'rad', 0.5 , 0, u'Θ', u'rad'],
                      [u'2Θ', u'mrad', 0.5 , 0, u'Θ', u'mrad'],
                      # temperature
                      [u'K', 1,-273.15, u'°C']
                      ]
