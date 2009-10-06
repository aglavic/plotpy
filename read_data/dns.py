#!/usr/bin/env python
'''
  Functions to read from dns data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from math import sqrt
from measurement_data_structure import MeasurementData
from config.dns import *

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

def read_data(file_name, print_comments=True):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
  '''
  if not os.path.exists(file_name): # Test if the file exists
    if print_comments:
      print "File does not exist."
    return 'NULL'
  file_handler=open(file_name, 'r')
  add_info={}
  # read header to test if this is a dns data file
  if (file_handler.readline().split()[0:3]==['#','DNS','Data']): 
    file_handler.readline() # skip empty line
    add_info['header']=read_header(file_handler) # read header information
    add_info['lambda_n']=read_lambda(file_handler) # find wavelength
    # get the information defined in config.dns.GET_INFO function
    for info in GET_INFO: 
      add_info[info[1]]=read_info(file_handler,info[0]) 
    while (file_handler.readline().find('DATA')==-1): # read until data line
      continue
    # dimensions are given at the line above the data
    line=file_handler.readline().split()
    detectors=min(float(line[1]),NUMBER_OF_DETECTORS)
    time_channels=float(line[2])
    # collect the data
    data_array=read_detector_data(file_handler,detectors,time_channels)
    #measurement_data=evaluate_data(data_array,add_info['detector_bank_2T'])
    columns=[['Detector', '']]
    error_columns=[]
    for i in range(len(data_array[0][1])):
      columns.append(['Channel_%i' % i, 'counts/'+SCALE_BY[1]])
      error_columns.append(['Error_Ch_%i' % i, 'counts/'+SCALE_BY[1]])
    columns+=error_columns
    measurement_data=MeasurementData(columns, [],0,1,len(data_array[0][1])*2,zdata=-1)
    scaling=add_info[SCALE_BY[0]]
    scale=lambda intensity: intensity/scaling
    error_scale=lambda intensity: sqrt(intensity)/scaling
    for point in data_array:
      measurement_data.append([point[0]]+map(scale, point[1])+map(error_scale, point[1]))
    measurement_data.dns_info=add_info
    measurement_data.info="\n".join(map(lambda item: item[0]+': '+str(item[1]),
                                    sorted(add_info.items())))
    measurement_data.sample_name=file_name
    return measurement_data
  else: # not dns data
    if print_comments:
      print "Wrong file type! Doesn't contain dns header information."
    return 'NULL'
  

def read_header(file_handler): # read file header information
  file_handler.readline()
  line=file_handler.readline()
  output=''
  while (not line[0:6]=='#-----'): # while header section is not over
    output=output+line.lstrip('#')
    line=file_handler.readline()
  return output
    
def read_lambda(file_handler): # read wavelength when after comment section
  file_handler.readline()
  return abs(float(file_handler.readline().split()[4]))*10
  
def read_info(file_handler,info_name): # read until specified line
  line=file_handler.readline()
  while (line.find(info_name)==-1):
    line=file_handler.readline()
  return float(line.split()[2])

# reads data and stores it in an array
def read_detector_data(file_handler,detectors,time_channels): 
  data=[]
  data_point=[]
  i=-1
  j=0
  line=file_handler.readline()
  while(not line==''): # read until EOF
    for value in line.split():
      if (i==-1):
        j=j+1
      else:
        if (i<time_channels):
          data_point.append(float(value))
      i=i+1
    if(not i<time_channels):
      # only save data form detectors after start_with
      if (START_WITH_DETECTOR<=j): 
        data.append([j-1,data_point])
      data_point=[]
      i=-1
      if (j>=detectors):
        break
    line=file_handler.readline()
  return data
