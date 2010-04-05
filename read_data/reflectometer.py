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
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


def read_data(input_file,DATA_COLUMNS): 
  '''
    Read the datafile.
    
    @param input_file Name of the file to import
    @param DATA_COLUMNS List of columns to be importedd
    
    @return List of MeasurementData objects with the file data
  '''
  measurement_data=[]
  if os.path.exists(input_file):
    global sample_name
    sample_name=''
    input_file_lines=open(input_file,'r').readlines()
    while len(input_file_lines)>0:
      measurement_info=read_header(input_file_lines)
      if measurement_info=='NULL':
        break
      sequence=read_data_lines(input_file_lines,measurement_info,DATA_COLUMNS)
      if sequence!='NULL':
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
  for line in info[0].splitlines():
    setting=line.split('=')
    if setting[0]=='SAMPLE':
      sample_name=setting[1].rstrip('\n')
    if setting[0]=='DRIVE':
      scantype=setting[1].strip("'")
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
    if next_data!='NULL':
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
    if len(line)<2:
      return 'NULL'
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