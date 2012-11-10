# -*- encoding: utf-8 -*-
'''
  Transformations for physical units.
'''

from numpy import pi as _pi

config_file='units'

# common prefixes for units
unit_prefixes={
               u'G': 1e9,
               u'M': 1e6,
               u'k': 1e3,
               u'd': 1e-1,
               u'c': 1e-2,
               u'm': 1e-3,
               u'µ': 1e-6,
               u'n': 1e-9,
               u'p': 1e-12,
               u'f': 1e-15,
               }
# base SI units where these prfixes apply to
SI_base_units=[u'm', u'g', u'K', u'T', u'A', u's', u'eV', u'rad', u"C"]

# define transformations that can be used to convert units
#                            u'from->to': (factor, offset, [name_from, name_to]),
unit_transformations={
                            # angle
                            u'rad->mrad': (1.e3, 0.),
                            u'rad->°': (180./_pi, 0.),
                            # length
                            u'Å->nm': (0.1, 0.),
                            # temperature
                            u'K->°C': (1.,-273.15),
                            # time
                            u'd->h': (24., 0.),
                            u'h->min': (60., 0.),
                            u'min->s': (60., 0.),
                            # magnetism
                            u'emu->A·m²': (1.e-3, 0.),
                            u'eV->g·m²/s²': (1.602177e-16, 0.),
                            u'Oe->T': (1.e-4, 0., u'H', u'μ_0·H')
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
                      [u'°', _pi/180, 0, u'rad'],
                      [u'rad', 1000., 0, u'mrad'],
                      [u'2Θ', u'°', 0.5 , 0, u'Θ', u'°'],
                      [u'2Θ', u'rad', 0.5 , 0, u'Θ', u'rad'],
                      [u'2Θ', u'mrad', 0.5 , 0, u'Θ', u'mrad'],
                      # temperature
                      [u'K', 1,-273.15, u'°C']
                      ]
