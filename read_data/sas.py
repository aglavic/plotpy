# -*- encoding: utf-8 -*-
'''
  Functions to read from in12 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import numpy
from measurement_data_structure import MeasurementData, PhysicalProperty

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.6.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

def read_data(file_name):
  '''
    Read the data of a small angle scattering data file.
    
    @param file_name The name of the file to import
    
    @return MeasurementData object with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  data_array=numpy.loadtxt(file_name)
  data_cols=data_array.transpose()
  dataset=MeasurementData(x=0, y=1, yerror=-1)
  output=[dataset]
  q=PhysicalProperty('q', '', data_cols[0])
  I=PhysicalProperty('I', 'a.u.', data_cols[1])
  filter_indices=numpy.where(I>0.)
  q=q[filter_indices]
  I=I[filter_indices]
  dataset.data.append(q)
  dataset.data.append(I)
  dataset.sample_name=file_name
  dataset.logy=True
  if len(data_cols)>2:
    I.error=data_cols[2][filter_indices]
  if len(data_cols)>3:
    dataset.short_info=" - Intensity column %i" % 1
    for i in range(1, ((len(data_cols)-1)/2)):
      Ii=PhysicalProperty('I' , 'a.u.', data_cols[1+2*i][filter_indices])
      if len(data_cols)>(1+2*i):
        Ii.error=data_cols[2+2*i][filter_indices]
      dataset=MeasurementData(x=0, y=1, yerror=-1)
      dataset.data.append(q)
      dataset.data.append(Ii)
      dataset.sample_name=file_name
      dataset.short_info=" - Intensity column %i" % (i+1)
      dataset.logy=True 
      output.append(dataset)
      i+=1
  return output
