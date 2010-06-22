# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from copy import deepcopy
from numpy import sqrt, array, pi, sin, arctan, maximum, linspace, savetxt, resize, where
from configobj import ConfigObj
from glob import glob
from measurement_data_structure import MeasurementData
import config.kws2
import config.gnuplot_preferences

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

detector_sensitivities={}
background_data={}

def read_data(file_name):
  '''
    Read the data of a kws2 data file.
    
    @param file_name The name of the file to import
    
    @return MeasurementData object with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  if file_name.endswith('.cmb'):
    #config.gnuplot_preferences.plotting_parameters_3d='w points palette pt 5'
    config.gnuplot_preferences.settings_3dmap=config.gnuplot_preferences.settings_3dmap.replace('interpolate 5,5', '')
    return read_cmb_file(file_name)
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'kws2_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
    read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  if setup['BACKGROUND'] and not setup['BACKGROUND'] in detector_sensitivities:
    read_background(folder, setup['BACKGROUND'])
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
  output.short_info=os.path.split(file_name)[1]
  
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
  if setup['BACKGROUND']:
    print "\tcorrecting for background"
    corrected_data-=background_data[setup['BACKGROUND']][0]
    corrected_error=sqrt(corrected_error**2+background_data[setup['BACKGROUND']][1]**2)
    if setup['BACKGROUND']:
      print "\tcorrecting for detector sensitivity"
      ds=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]-\
                        background_data[setup['BACKGROUND']][0]
      ds/=ds.mean()
      corrected_data/=ds
      corrected_error/=ds
  elif setup['DETECTOR_SENSITIVITY']:
    print "\tcorrecting for detector sensitivity"
    ds=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]
    ds/=ds.mean()
    corrected_data/=ds
    corrected_error/=ds
  if 'LAMBDA_N' in setup:
    lambda_n=setup['LAMBDA_N']
  else:
    lambda_n=config.kws2.LAMBDA_N
  qy_array=4.*pi/lambda_n*\
           sin(arctan((y_array-setup['CENTER_X'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  qz_array=4.*pi/lambda_n*\
           sin(arctan((z_array-setup['CENTER_Y'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  if setup['SWAP_YZ']:
    # swap the directions
    tmp=qz_array
    qz_array=qy_array
    qy_array=tmp
  for i in range(config.kws2.PIXEL_X**2):
    dataobj.append((y_array[i], z_array[i], corrected_data[i], corrected_error[i], 
                    qy_array[i], qz_array[i], data_array[i], error_array[i]))
  return dataobj
  
def read_sensitivities(folder, name):
  '''
    Read data from the sensitivity file.
  '''
  global detector_sensitivities
  print "\treading detector sesitivity from %s" % name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.kws2.HEADER])
  data_lines=lines[config.kws2.HEADER:]
  file_handler.close()
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  # take at minimum 0.5 counts for the sensitivity
  data_array=maximum(0.5, data_array)
  detector_sensitivities[name]=data_array/countingtime
  
def read_background(folder, name):
  '''
    Read data from the background file.
  '''
  global background_data
  print "\treading background data from %s" % name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.kws2.HEADER])
  data_lines=lines[config.kws2.HEADER:]
  file_handler.close()
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  # normalize to get about the same cps values
  error_array=sqrt(data_array)
  background_data[name]=(data_array/countingtime, error_array/countingtime)
  
def read_cmb_file(file_name):
  '''
    Read the binary .cmb file format.
  '''
  background=2.
  countingtime=1.
  detector_distance=1.
  sample_name=''
  center_x=384.
  center_y=498.5
  q_window=[-0.1, 0.1, -0.02, 0.1]
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  file_handler=open(file_name, 'rb')
  header=file_handler.read(256)
  file_handler.read(256)
  import array as array_module
  data_array=array_module.array('i')
  data_array.fromfile(file_handler, 1024**2)
  # read additional info from end of file
  lines=file_handler.readlines()
  for line in lines:
    if line.startswith('#sca'):
      countingtime=float(line.split()[1])
    elif line.startswith('#dst'):
      detector_distance=float(line.split()[1])
    elif line.startswith('#txt'):
      sample_name+=" ".join(line.split()[1:])
  data_array=array(data_array)
  z_array=linspace(0, 1024**2-1, 1024**2)%1024
  y_array=linspace(0, 1024**2-1, 1024**2)//1024
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  lambda_x=1.54
  qy_array=4.*pi/lambda_x*\
           sin(arctan((y_array-center_y)*0.0001/detector_distance/2.))
  qz_array=4.*pi/lambda_x*\
           sin(arctan((z_array-center_x)*0.0001/detector_distance/2.))
  data=array([y_array, z_array, corrected_data, corrected_error, qy_array, qz_array, 
              data_array, error_array, \
              (qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3])]).transpose()
  data_lines=[data_line[:8] for data_line in data if not data_line[8]]
  #dataobj.number_of_points=1024**2
  #dataobj.data[0].values=y_array.tolist()
  #dataobj.data[1].values=z_array.tolist()
  #dataobj.data[2].values=corrected_data.tolist()
  #dataobj.data[3].values=corrected_error.tolist()
  #dataobj.data[4].values=qy_array.tolist()
  #dataobj.data[5].values=qz_array.tolist()
  #dataobj.data[6].values=data_array.tolist()
  #dataobj.data[7].values=error_array.tolist()
  for data_line in data_lines:
    dataobj.append(data_line)
  dataobj.sample_name=sample_name
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  return [dataobj]
  

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

