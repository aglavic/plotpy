#!/usr/bin/env python
'''
  Functions to read from a 4circle data file (spec).
  Mostly just string processing.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import sys
import math
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def read_data(input_file,COLUMNS_MAPPING,MEASUREMENT_TYPES): 
  '''
    Read the datafile.
  '''
  if os.path.exists(input_file):
    measurement_data=[]
    input_file_lines=open(input_file,'r').readlines()
    first=True
    while len(input_file_lines)>0:
      measurement_info=read_header(input_file_lines)
      if measurement_info=='NULL':
        break
      first=False
      sequence=read_data_lines(input_file_lines,measurement_info,COLUMNS_MAPPING,MEASUREMENT_TYPES)
      if not sequence=='NULL':
        measurement_data.append(sequence)
    if first:
      print "Wrong file type, no columns defined in header (#L)!"
    return measurement_data
  else:
    print 'File '+input_file+' does not exist.'
    return measurement_data


def read_header(input_file_lines): 
  '''
    Read header of datafile and return the columns present.
  '''
  output=''
  for i in range(len(input_file_lines)):
    line=input_file_lines.pop(0)
    if (line[0:2]=='#L'):
      columns=line[3:-1].split('  ')
      return [output,columns]
    else:
      output=output+'\n'+line.rstrip('\n')
  return 'NULL'

def column_compare(col1,col2):
  '''
    Compare the second entry of two lists.
  '''
  return (col1[1]-col2[1])

def check_type(data_1,data_2,type_i):
  '''
    Compare the data of two lines to check 
    if they belong to the same sequence. 
  '''
  output=True
  for ty in type_i[0]:
    if len(data_1)>ty[0]+1:
      if (abs(data_1[ty[0]]-data_2[ty[0]])<ty[1])&output:
        output=True
      else:
        output=False
    else:
      return False
  return output
  
def read_data_lines(input_file_lines,info,COLUMNS_MAPPING,MEASUREMENT_TYPES): 
  '''
    Read data points line by line.
  '''
  output=[] #initialise data array containing data objects
  count=1
  columns=[]
  # define which columns contain the relevant data
  for item in info[1]:
    count=count+1
    for mapping in COLUMNS_MAPPING:
      if item==mapping[0]:
        columns.append([count-2,mapping[1],mapping[2]])
  columns.sort(column_compare)
  #read 2 lines to determine the type of the first sequence
  # if the scan was aborted this can lead to an IndexError
  # so this scan is considered not present.
  try:
    data_1=read_data_line(input_file_lines.pop(0),columns)
    data_2=read_data_last_line(input_file_lines,columns)
  except IndexError:
    return 'NULL'
  not_found=True
  if (data_1!='NULL')&(data_2!='NULL')&(data_1!='Comment')&(data_2!='Comment'):
    for type_i in MEASUREMENT_TYPES:
        if check_type(data_1,data_2,type_i)&not_found:
          columns.append([0,len(columns),['delta intensity','counts']])
          data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],type_i[3])
          data.append(data_1)
          data.plot_options=type_i[4]
          if len(type_i)>5:
            data.zdata=type_i[5]
          not_found=False
          columns.pop(-1)
  else:
    return 'NULL'
  try: # if no sequence of set types is found return null
    data.info=info[0]
  except:
    print 'No sequence with right type found!'
    return 'Null'
  data.sample_name=''
  while len(input_file_lines)>0: # append data from one sequence to the object or create new object for the next sequence
    line=input_file_lines.pop(0)
    next_data=read_data_line(line,columns)
    if next_data!='NULL':
      if next_data=='Comment':
        continue
      elif data.is_type(next_data):
        data.append(next_data)
      else:
        return data
    else:
      return data
  return data

def read_data_line(input_file_line,columns): 
  '''
    Read one line and output data as list.
  '''
  if input_file_line[0]=='#':
    if input_file_line[1]=='C':
      return 'Comment'
    else:
      return 'NULL'
  else:
    line=input_file_line.split()
    values=[]
    if len(line)>=len(columns):
      for column in columns:
        if line[column[0]]=='':
          values.append(0.)
        else:
          values.append(float(line[column[0]]))
      values.append(max(math.sqrt(float(line[-1])),1))
      return values
    else:
      return 'NULL'

def read_data_last_line(input_file_lines,columns): 
  '''
    Returns second last line of one sequence for type finding.
    Second last because of possibility of abborted scans.
  '''
  for i,line in enumerate(input_file_lines):
    if line[0]=='#':
      return read_data_line(input_file_lines[i-2],columns)
    elif len(line.split())<2:
      return read_data_line(input_file_lines[i-2],columns)
  try:
    return read_data_line(input_file_lines[-2],columns)
  except IndexError:
    raise IndexError
