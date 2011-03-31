# -*- encoding: utf-8 -*-
'''
  Functions to read from reflectometer UXD data file. Mostly just string processing.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import sys
import math
import measurement_data_structure
import codecs
from copy import deepcopy
from numpy import array, sqrt, pi, sin

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


def read_data(file_name, DATA_COLUMNS): 
  '''
    Read the datafile.
    
    @param input_file Name of the file to import
    @param DATA_COLUMNS List of columns to be importedd
    
    @return List of MeasurementData objects with the file data
  '''
  measurement_data=[]
  if os.path.exists(file_name):
    global sample_name
    sample_name=''
    if file_name.endswith('.gz'):
      # use gziped data format
      import gzip
      file_handler=gzip.open(file_name, 'r')
    else:
      file_handler=open(file_name, 'r')
    file_string=file_handler.read()
    input_file_lines=codecs.decode(file_string, "ISO 8859-15", 'ignore').splitlines()
    file_handler.close()
    while len(input_file_lines)>0:
      measurement_info=read_header(input_file_lines)
      if measurement_info=='NULL':
        return 'NULL'
      sequence=read_data_lines(input_file_lines,measurement_info,DATA_COLUMNS)
      if sequence!='NULL':
        # filter 0 intensity points
        sequence.filters=[(1, 0.0, 0.0, False)]
        # for Θ or 2Θ scans add q-column
        if "DRIVE='THETA'" in sequence.info:
          two_theta_start=float(sequence.info.split('2THETA=')[1].split("\n")[0])
          th=(sequence.x-sequence.x[0])+two_theta_start*0.5
          sequence.data.append( (4.*pi/1.54*sin(th))//('q_z', 'Å^{-1}') )
        elif "DRIVE='2THETA'" in sequence.info:
          th=sequence.x*0.5
          sequence.data.append( (4.*pi/1.54*sin(th))//('q_z', 'Å^{-1}') )
        measurement_data.append(sequence)
      else:
        return 'NULL'
    return measurement_data
  else:
    print 'File '+input_file+' does not exist.'
    return measurement_data

def read_header(input_file_lines): 
  '''
    Read header of datafile.
    
    @param input_file_lines List of lines from the input file
    
    @return Header information 
  '''
  output=''
  for i in range(len(input_file_lines)):
    line=input_file_lines.pop(0)
    if ('COUNTS' in line):
      scantype=line[1:-1].rstrip('\r\n')
      # remove comment lines
      while ";" in input_file_lines[0]:
        line=input_file_lines.pop(0)
      return [output,scantype]
    else:
      output=output+line.rstrip('\n').rstrip('\r').lstrip('_').lstrip(';')+'\n'
  return 'NULL'

def read_data_lines(input_file_lines,info,DATA_COLUMNS): 
  '''
    Read data points line by line.
    
    @return One MeasurementData object for a scan sequence
  '''
  global sample_name
  output=[] #initialise data array containing data objects
  data_info=''
  scantype=None
  count_time=1.
  for line in info[0].splitlines():
    setting=line.split('=')
    if setting[0]=='SAMPLE':
      sample_name=setting[1].rstrip('\n').strip("'")
    elif setting[0].strip()=='DRIVE':
      scantype=setting[1].strip("'").strip()
    elif setting[0].strip()=='STEPTIME':
      count_time=float(setting[1])
    # Definitions for locked-coupled scans
    elif setting[0].strip()=='START':
      i=0
      start_angle=float(setting[1])
    elif setting[0].strip()=='STEPSIZE':
      increment_angle=float(setting[1])
    data_info=data_info+line+'\n'
  if scantype==None:
    print "Wrong file type, no 'DRIVE' defined in header!"
    return 'NULL'
  data=MeasurementData([DATA_COLUMNS[scantype],DATA_COLUMNS['COUNTS'],['error','counts']],[],0,1,2)
  data.info=data_info
  data.sample_name=sample_name
  while len(input_file_lines)>0: # append data from one sequence to the object or create new object for the next sequence
    line=input_file_lines.pop(0)
    next_data=read_data_line(line)
    if len(next_data)==2 and next_data!='NULL':
      data.append((start_angle+i*increment_angle, next_data[0], next_data[1]))
      i+=1
    elif next_data!='NULL':
      data.append(next_data)
    else:
      return data
  return data

def read_data_line(input_file_line): 
  '''
    Read one line and output data as list of floats.
  '''
  if input_file_line[0]==';':
    return 'NULL'
  else:
    line=input_file_line.strip().split()
    if len(line)==0:
      return 'NULL'
    elif len(line)==1:
      return [float(line[0]), math.sqrt(abs(float(line[0])))]
    return [float(line[0]),float(line[1]),math.sqrt(abs(float(line[1])))]

def read_simulation(file_name):
  '''
    Read a fit.f90 output file as MeasurementData object.
    
    @return MeasurementData with the fitted dataset
  '''
  sim_file=open(file_name,'r')
  sim_lines=sim_file.readlines()
  sim_file.close()
  data=MeasurementData([['q','Å^{-1}'],['Intensity','counts/s'],['error','counts']],[],0,1,2)
  data.info='Simulation'
  for line in sim_lines:
    if len(line.split())>1:
      point=map(float,line.split())
      point.append(0.0)
      data.append(point)
  return data

class MeasurementData(measurement_data_structure.MeasurementData):
  '''
    Class implementing additions for Reflectometer data objects.
  '''
  def __add__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)+array(other.data[1].values)).tolist()    
    out.data[2].values=(sqrt(array(self.data[2].values)**2+array(other.data[2].values)**2)).tolist()
    return out
  
  def __sub__(self, other):
    '''
      Subtract two measurements from another.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'-'+other.short_info
    out.data[1].values=(array(self.data[1].values)-array(other.data[1].values)).tolist()    
    out.data[2].values=(sqrt(array(self.data[2].values)**2+array(other.data[2].values)**2)).tolist()
    return out
  
  def __rmul__(self, other):
    '''
      Multiply measurement with a scalar.
    '''
    out=deepcopy(self)
    out.data[1].values=(other*array(self.data[1].values)).tolist()    
    out.data[2].values=(other*array(self.data[2].values)).tolist()    
    return out
  
  def __mul__(self, other):
    '''
      Multiply two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)*array(other.data[1].values)).tolist()    
    out.data[2].values=(sqrt(array(self.data[2].values)**2*array(other.data[1].values)**2+\
                             array(other.data[2].values)**2*array(self.data[1].values)**2)).tolist()
    return out
  
  def __div__(self, other):
    '''
      Divide two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(1./other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)/array(other.data[1].values)).tolist()    
    out.data[2].values=(sqrt(array(self.data[2].values)**2/array(other.data[1].values)**2+\
                             array(other.data[2].values)**2*array(self.data[1].values)**2\
                             /array(other.data[1].values)**4)).tolist()
    return out
  
