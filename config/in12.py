#!/usr/bin/env python
'''
  Configurations for the IN12 file import.
'''

column_dimensions=(
                   (('A1', 'A2', 'A3', 'A4', 'A5', 'A6'), 'grad'), 
                   (('I1', 'I2', 'I3', 'I4', 'I5', 'I6'), 'A'), 
                   (('CNTS', 'M1', 'M2'), 'counts'), 
                   (('QH', 'QK', 'QL'), 'r.l.u.'), 
                   (('TIME'), 's'), 
                   (('PNT'), ''), 
                   (('TT', 'TRT'), 'K'), 
                   (('KI', 'KF'), 'A^{-1}'), 
                   (('F1', 'F2'), 'ON-OFF'), 
                    )

name_replacements=(
                ('A3', 'omega'), 
                ('A4', '2Theta'), 
                ('CNTS', 'Intensity'), 
                ('QH', 'h'), 
                ('QK', 'k'), 
                ('QL', 'l'), 
                ('TT', 'Sample Temperature'), 
                ('TRT', 'Controled Temperature'), 
                ('KI', 'K_i'), 
                ('KF', 'K_f'), 
                ('F1', 'Flipper1'), 
                ('F2', 'Flipper2'), 
                )
