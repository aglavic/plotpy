# -*- encoding: utf-8 -*-
'''
  Functions to read data for the treff session, not collected by treff.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import numpy as np
from measurement_data_structure import MeasurementData
from config.treff import GRAD_TO_MRAD, GRAD_TO_RAD

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = ["Daniel Schumacher"]
__license__ = "None"
__version__ = "0.7beta2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

PI_4_OVER_LAMBDA=np.pi*4./1.5

def read_data(file_name, script_path, import_images):
  '''
    Read the data and return the measurements.
  '''
  output=[]
  dataset1=MeasurementData([['q', 'Å^{-1}'], ['I', 'counts'], ['dI', 'counts']], [], 0, 1, 2)
  dataset1.append([0.5, 2000, np.sqrt(2000)])
  dataset1.append([1, 200, np.sqrt(200)])
  dataset1.append([1.5, 20, np.sqrt(20)])
  dataset1.sample_name='Test'
  dataset1.logy=True
  dataset1.short_info='not set'
  dataset1.unit_trans([['q', 'Å^{-1}', 1000/PI_4_OVER_LAMBDA, 0, 'Θ', 'mrad']])
  output.append(dataset1)
  return output