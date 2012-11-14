#-*- coding: utf-8 -*-
'''
  Peakfinder configuration
'''

config_file='user'

presets={}
# fill default presets
for i in range(5):
  presets[str(i+1)]={
                'PeakWidth': (2., 0.5),
                'SNR': 5.,
                'RidgeLength': 20.,
                'DoublePeaks': False,
                'DoublePeakRidgeLength': 5.,
                                                 }
del(i)
