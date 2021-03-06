# -*- encoding: utf-8 -*-
'''
  Configurations for the IN12 file import.
'''

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

column_dimensions=(
                   (('A1', 'A2', 'A3', 'A4', 'A5', 'A6'), '°'),
                   (('I1', 'I2', 'I3', 'I4', 'I5', 'I6'), 'A'),
                   (('CNTS', 'M1', 'M2'), 'counts'),
                   (('QH', 'QK', 'QL'), 'r.l.u.'),
                   (('TIME'), 's'),
                   (('PNT'), ''),
                   (('TT', 'TRT'), 'K'),
                   (('KI', 'KF'), 'Å^{-1}'),
                   (('F1', 'F2'), 'ON-OFF'),
                   (('EN'), 'meV'),
                    )

name_replacements=(
                ('A1', 'mono. tilt'),
                ('A2', 'mono. 2Θ'),
                ('A3', 'ω'),
                ('A4', '2Θ'),
                ('A5', 'ana. tilt'),
                ('A6', 'ana. 2Θ'),
                ('CNTS', 'Intensity'),
                ('QH', 'h'),
                ('QK', 'k'),
                ('QL', 'l'),
                ('EN', 'energy transfer'),
                ('TT', 'Smpl Temp.'),
                ('TRT', 'Cntrl Temp.'),
                ('KI', 'K_i'),
                ('KF', 'K_f'),
                ('F1', 'Flipper1'),
                ('F2', 'Flipper2'),
                ('MN', 'Monitor'),
                ('AS', 'a'),
                ('BS', 'b'),
                ('CS', 'c'),
                ('AX', 'x_a'),
                ('BX', 'x_b'),
                ('CX', 'x_c'),
                ('AY', 'y_a'),
                ('BY', 'y_b'),
                ('CY', 'y_c'),
                ('RA', 'ana. curve'),
                ('RM', 'mono. curve'),
                )