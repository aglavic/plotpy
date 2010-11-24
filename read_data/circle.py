# -*- encoding: utf-8 -*-
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
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7rc1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def read_data(input_file,COLUMNS_MAPPING,MEASUREMENT_TYPES): 
  '''
    Read the datafile.
    
    @param COLUMNS_MAPPING List of predefined columns
    @param MEASUREMENT_TYPES List of predefined settings for the measured columns
  '''
  measurement_data=[]
  if os.path.exists(input_file):
    if input_file.endswith('.gz'):
      # use gziped format file
      import gzip
      file_handle=gzip.open(input_file, 'r')
    else:
      file_handle=open(input_file, 'r')
    input_file_lines=file_handle.readlines()
    file_handle.close()
    sample_name=read_file_header(input_file_lines)
    if not sample_name:
      print "Wrong file type, no spec header found (#F,#E,#D,#C)!"
      sample_name=''
    while len(input_file_lines)>0:
      measurement_info=read_scan_header(input_file_lines)
      if not measurement_info:
        break
      sequence=read_data_lines(input_file_lines,measurement_info,COLUMNS_MAPPING,MEASUREMENT_TYPES)
      if not sequence=='NULL':
        sequence.sample_name=sample_name
        measurement_data.append(sequence)
    if len(measurement_data)==0:
      print "No scan data found in file %s." % input_file
    return measurement_data
  else:
    print 'File '+input_file+' does not exist.'
    return measurement_data

def read_file_header(input_file_lines):
  '''
    Read the header of the file.
    
    @param input_file_lines List of lines to be evaluated
    
    @return The sample name defined in the file or None if the wron filetype.
  '''
  if not (input_file_lines[0].startswith('#F') and 
          input_file_lines[1].startswith('#E') and 
          input_file_lines[2].startswith('#D')):
    return None
  try:
    line=input_file_lines[3]
    sample_name=line.split('User')[0].split(' ', 1)[1]
    return sample_name
  except:
    return None
  

def read_scan_header(input_file_lines): 
  '''
    Read header of datafile and return the columns present.
    
    @param input_file_lines List of lines read from the input file
    
    @return List of header information and data column names or 'NULL' if not the right format
  '''
  output=None
  for i in range(len(input_file_lines)):
    line=input_file_lines.pop(0)
    if (line[0:2]=='#L'):
      columns=line[3:-1].split('  ')
      return [output,columns]
    elif (line[0:2]=='#S'):
      output=line.replace('#S', 'Scan: ').rstrip('\n')
    elif output:
      if line[0:3] in ['#N ','#G0', '#G2','#G3','#G4']:
        continue
      else:
        info=line.rstrip('\n').replace('#D', 'Date: ')
        info=info.replace('#T', 'Counting time: ')
        info=info.replace('#Q', 'Q at start: ')
        info=info.replace('#P0', 'Angles at start: ')
        info=info.replace('#G1', 'Lattice parameters at start: ')
        output+='\n'+info
  return None

def column_compare(col1,col2):
  '''
    Compare the second entry of two lists.
  '''
  return (col1[1]-col2[1])

def check_type(data_1,data_2,type_i):
  '''
    Compare the data of two lines to check 
    if they belong to the same sequence. 
    
    @return If the data fits to the sequence
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
    
    @param input_file_lines List of lines from the input file
    @param info Header information of that file
    @param COLUMNS_MAPPING List of predefined columns
    @param MEASUREMENT_TYPES List of predefined settings for the measured columns
    
    @return MeasurementData object with the read points or 'NULL' if error
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
  data_1=read_data_line(input_file_lines,columns)
  data_2=read_data_last_line(input_file_lines,columns)
  not_found=True
  if data_1 and data_2:
    for type_i in MEASUREMENT_TYPES:
        if check_type(data_1,data_2,type_i)&not_found:
          data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],-1)
          data.append(data_1)
          data.plot_options=type_i[4]
          if len(type_i)>5:
            data.zdata=len(columns)-1
          else:
            data.ydata=len(columns)-1
          not_found=False
  else:
    return 'NULL'
  try: # if no sequence of set types is found return null
    data.info=info[0]
  except:
    print 'No sequence with right type found!'
    return 'Null'
  next_data=read_data_line(input_file_lines, columns)
  while next_data: # append data from one sequence to the object or create new object for the next sequence
    data.append(next_data)
    next_data=read_data_line(input_file_lines,columns)
  return data

def read_data_line(input_file_lines,columns): 
  '''
    Read one line and output data as list.
    
    @param input_file_line Line to read data from
    
    @return List of floating point numbers of 'NULL' if error
  '''
  if len(input_file_lines)==0:
    return None
  line=input_file_lines[0]
  if line[0:2]=='#S':
    return None
  elif input_file_lines[0][0]=='#':
    input_file_lines.pop(0)
    return read_data_line(input_file_lines, columns)
  else:
    line=input_file_lines.pop(0).split()
    values=[]
    if len(line)>=len(columns):
      for column in columns[:-1]:
        if line[column[0]]=='':
          values.append(0.)
        else:
          values.append(float(line[column[0]]))
      values.append((float(line[-1]), max(math.sqrt(float(line[-1])),1)))
      return values
    else:
      return None

def read_data_last_line(input_file_lines,columns): 
  '''
    Returns second last line of one sequence for type finding.
    Second last because of possibility of abborted scans.
  '''
  if len(input_file_lines)<2:
    return None
  for i, line in enumerate(input_file_lines[2:]):
    if line[0:2]=='#S' or i==(len(input_file_lines)-3):
      while input_file_lines[i][0]=='#':
        if i==1:
          return None
        i-=1
      line=input_file_lines[i].split()
      values=[]
      if len(line)>=len(columns):
        for column in columns[:-1]:
          if line[column[0]]=='':
            values.append(0.)
          else:
            values.append(float(line[column[0]]))
        values.append((float(line[-1]), max(math.sqrt(float(line[-1])),1)))
        return values
      else:
        return None