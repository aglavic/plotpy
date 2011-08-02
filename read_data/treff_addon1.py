# -*- encoding: utf-8 -*-
'''
  Functions to read data for the treff session, not collected by treff.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from glob import glob
import numpy as np
from measurement_data_structure import MeasurementData
from config.treff import GRAD_TO_MRAD, GRAD_TO_RAD

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Daniel Schumacher"]
__license__ = "GPL v3"
__version__ = "0.7.8"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

PI_4_OVER_LAMBDA=np.pi*4./4.73

def read_data(file_name, script_path, import_images, return_detector_images):
  '''
    Read the data and return the measurements.
  '''
  file_names=glob(file_name+'*.txt')
  output=[]
  for name in file_names:
    print "Reading %s" % name
    file_data=open(name, 'r').read()
    lines=file_data.splitlines()
    lines=filter(lambda line: not (line.startswith('#') or line.strip()==''), lines)
    lines=map(str.strip, lines)
    i=0
    continue_it=True
    while continue_it:
      try:
        block=lines[i:lines.index('')]
        i=lines.index('')
      except ValueError:
        block=lines[i:]
        continue_it=False
      try:
        floats=map(lambda line: map(float, line.split()),  block)
      except ValueError:
        print "\tNot numeric string in %s[%i], ignoreing block." % (name, i+1)
      floats=filter(lambda line: line[1]!=0., floats)
      dataset=MeasurementData([['q', 'Å^{-1}'], ['I', 'a.u.'], ['dI', 'a.u.']], [], 0, 1, 2)
      map(dataset.append, floats)
      dataset.sample_name=name
      dataset.logy=True
      dataset.short_info=''
      # (from dim, from unit, multiplier, offset, to dim, to unit)
      dataset.data.append(dataset.data[0]//'q2')
      dataset.unit_trans([['q2', 'Å^{-1}', 1000./PI_4_OVER_LAMBDA, 0., 'Θ{4.73Å}', 'mrad']])
      if len(dataset.data[0])>1:
        output.append(dataset)
      else:
        print "\tDataset %s[%i] has no intensities >0 in it!" % (name, i+1)
  return output
