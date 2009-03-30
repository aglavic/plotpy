#!/usr/bin/env python
#
# Functions to read from SQUID data file
# mostly just string processing.
# MeasurementData Object from 'measurement_data_structure' is used to store the data points.
# read_data is the main procedure, returning a list of MeasurementData objects

# Pleas do not make any changes here unless you know what you are doing.


import os
import sys
from measurement_data_structure import *
import SQUID_preferences
import globals

def read_data(input_file,columns_mapping,measurement_types): #read the datafile with diamagnetic correction
  if os.path.exists(input_file):
    input_file_lines=open(input_file,'r').readlines()
    if input_file_lines[0].find('[Header]')>=0:
      measurement_info=read_header(input_file_lines)
      while input_file_lines.pop(0).find('[Data]')==-1:
        continue
      measurement_data=read_data_lines(input_file_lines,measurement_info,columns_mapping,measurement_types)
    else:
      print "Wrong file type! Doesn't contain header information."
      return 'NULL'
    return measurement_data
  else:
    print 'File '+input_file+' does not exist.'
    return 'NULL'

def get_columns(input_file): # just return the columns present in file
  if os.path.exists(input_file):
    input_file_handler=open(input_file,'r')
    if input_file_handler.readline().find('[Header]')>=0:
      lines=[input_file_handler.readline() for i in range(50)]
      measurement_info=read_header(lines)
      while lines.pop(0).find('[Data]')==-1:
        continue
    else:
      print "Wrong file type! Doesn't contain header information."
      return 'NULL'
    out=lines.pop(0).split(',')
    input_file_handler.close()
    return out
  else:
    print 'File '+input_file+' does not exist.'
    return 'NULL'
  

def read_header(input_file_lines): #read header of datafile
  output=['','']
  for i in range(len(input_file_lines)):
    line=input_file_lines[i].split(', ', 2)
    if (line[0]=='INFO') & (len(line)>2):
      output[0]=output[0]+'\n'+line[1]+': '+line[2].rstrip('\r\n')
      if line[1]=='NAME':
        output[1]=line[2].rstrip('\r\n')
    if line[0].find('[Data]')>=0:
      break
  return output

def check_type(data_1,data_2,type_i):
  output=True
  for ty in type_i[0]:
    if (abs(data_1[ty[0]]-data_2[ty[0]])<ty[1])&output:
      output=True
    else:
      output=False
  return output
  
def read_data_lines(input_file_lines,info,columns_mapping,measurement_types): #read data points line by line
  output=[] #initialise data array containing data objects
  line=input_file_lines.pop(0).split(',')
  count=1
  columns=[]
# define which columns contain the relevant data
  for item in line:
    count=count+1
    for mapping in columns_mapping:
      if item==mapping[0]:
        columns.append([count-2,mapping[1],mapping[2]])
    columns.sort(key=lambda x:x[1])
  #read 2 lines to determine the type of the first sequence
  data_1=read_data_line(input_file_lines.pop(0),columns)
  data_2=read_data_line(input_file_lines.pop(0),columns)
  not_found=True
  if (data_1!='NULL')&(data_2!='NULL'):
    for type_i in measurement_types:
      if check_type(data_1,data_2,type_i)&not_found:
        data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],type_i[3])
        data.append(data_1)
        data.append(data_2)
        data.plot_options=type_i[4]
        data.filters=SQUID_preferences.filters
        not_found=False
  else:
    return 'NULL'
  try: # if no sequence of set types is found return null
    data.info=info[0]
  except:
    print 'No sequence with right type found!'
    return 'Null'
  data.sample_name=info[1]
  count_lines=len(input_file_lines)
  if count_lines>10000:
    sys.stdout.write('Reading progress [%]:   0')
    sys.stdout.flush()
  for i,line in enumerate(input_file_lines): # append data from one sequence to the object or create new object for the next sequence
    if (i+1)%10000==0:
      procent=float(i)/count_lines*100.
      sys.stdout.write('\b\b\b'.replace('\b','',3-len('%d' % procent))+'%d' % procent)
      sys.stdout.flush()
    next_data=read_data_line(line,columns)
    if next_data!='NULL':
      if data.is_type(next_data):
        data.append(next_data)
      else:
        output.append(data)
      next_data_2=read_data_line(input_file_lines[i+1],columns)
      if next_data_2!='NULL':
        not_found=True
        for type_i in measurement_types:
          if check_type(next_data,next_data_2,type_i)&not_found:
            data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],type_i[3])
            data.plot_options=type_i[4]
            not_found=False
            data.info=info[0]
            data.sample_name=info[1]
            data.filters=SQUID_preferences.filters
            data.append(next_data)
            data.append(next_data_2)
      else:
        return output
    else:
      output.append(data)
      return output
  output.append(data)
  return output

def read_data_line(input_file_line,columns): #read one line and output data as list
    line=input_file_line.split(',')
    values=[]
    if len(line)>=len(columns):
      for column in columns:
        val=line[column[0]]
      if not val=='':
        values.append(float(val))
      else:
        values.append(0.)
      return values
    else:
      return 'NULL'
  
