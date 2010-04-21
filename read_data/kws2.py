# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from copy import deepcopy
from numpy import sqrt, array, pi, sin, arctan, maximum
from configobj import ConfigObj
from glob import glob
from measurement_data_structure import MeasurementData
import config.kws2

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

detector_sensitivities={}

def read_data(file_name):
  '''
    Read the data of a kws2 data file.
    
    @param file_name The name of the file to import
    
    @return MeasurementData object with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'kws2_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
    read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  header_lines=lines[:config.kws2.HEADER]
  countingtime=read_countingtime(header_lines)
  data_lines=lines[config.kws2.HEADER:]
  file_handler.close()
  output= create_dataobj(data_lines,  header_lines, countingtime, setup)
  output.short_info=file_name
  
  return [output]

def read_countingtime(lines):
  '''
    Extract the countingtime from the file header.
  '''
  for i, line in enumerate(lines):
    if 'Real measurement time for detector data' in line:
      return float(lines[i+1].split()[0])

def create_dataobj(data_lines, header_lines, countingtime, setup):
  '''
    Create a MeasurementData object form the input datalines.
  '''
  detector_sensitivities
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  y_array=array([i%config.kws2.PIXEL_X for i in range(config.kws2.PIXEL_X**2)])
  z_array=array([i/config.kws2.PIXEL_X for i in range(config.kws2.PIXEL_X**2)])
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  if setup['DETECTOR_SENSITIVITY']:
    corrected_data/=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]
    corrected_error/=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]
  qy_array=4.*pi/config.kws2.LAMBDA_N*\
           sin(arctan((y_array-setup['CENTER_X'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  qz_array=4.*pi/config.kws2.LAMBDA_N*\
           sin(arctan((z_array-setup['CENTER_Y'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  if setup['SWAP_YZ']:
    # swap the directions
    tmp=qz_array
    qz_array=qy_array
    qy_array=tmp
    tmp=z_array
    z_array=y_array
    y_array=tmp
  for i in range(config.kws2.PIXEL_X**2):
    dataobj.append((y_array[i], z_array[i], corrected_data[i], corrected_error[i], 
                    qy_array[i], qz_array[i], data_array[i], error_array[i]))
  return dataobj
  
def read_sensitivities(folder, name):
  '''
    Read data from the sensitivity file and normalize it.
  '''
  global detector_sensitivities
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  data_lines=file_handler.readlines()[config.kws2.HEADER:]
  file_handler.close()
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  # normalize to get about the same cps values
  data_array=maximum(1., data_array)
  data_array/=data_array.mean()
  detector_sensitivities[name]=data_array
  
class KWS2MeasurementData(MeasurementData):
  '''
    Class implementing additions for KWS2 data objects.
  '''
  def __add__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[2].values=(array(self.data[2].values)+array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2+array(other.data[3].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)+array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2+array(other.data[7].values)**2)).tolist()
    return out
  
  def __sub__(self, other):
    '''
      Subtract two measurements from another.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'-'+other.short_info
    out.data[2].values=(array(self.data[2].values)-array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2+array(other.data[3].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)-array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2+array(other.data[7].values)**2)).tolist()
    return out
  
  def __rmul__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.data[2].values=(other*array(self.data[2].values)).tolist()    
    out.data[3].values=(other*array(self.data[3].values)).tolist()    
    out.data[6].values=(other*array(self.data[6].values)).tolist()    
    out.data[7].values=(other*array(self.data[7].values)).tolist()    
    return out
  
  def __mul__(self, other):
    '''
      Multiply two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[2].values=(array(self.data[2].values)*array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2*array(other.data[2].values)**2+\
                             array(other.data[3].values)**2*array(self.data[2].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)*array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2*array(other.data[6].values)**2+\
                             array(other.data[7].values)**2*array(self.data[6].values)**2)).tolist()
    return out
  
  def __div__(self, other):
    '''
      Divide two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(1./other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[2].values=(array(self.data[2].values)/array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2/array(other.data[2].values)**2+\
                             array(other.data[3].values)**2*array(self.data[2].values)**2\
                             /array(other.data[2].values)**4)).tolist()
    out.data[6].values=(array(self.data[6].values)/array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2/array(other.data[6].values)**2+\
                             array(other.data[7].values)**2*array(self.data[6].values)**2\
                             /array(other.data[6].values)**4)).tolist()
    return out
  
