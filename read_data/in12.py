#!/usr/bin/env python
'''
  Functions to read from in12 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from math import sqrt
from measurement_data_structure import MeasurementData
from config.in12 import column_dimensions, name_replacements

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

def read_data(file_name):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  header_lines=lines[:get_first_data_line(lines)]
  data_lines=lines[get_first_data_line(lines):]
  file_handler.close()
  valid,  header, columns= read_header(header_lines)
  if not valid:
    print 'Not a valid datafile, skipped.'
    return 'NULL'
  output = read_data_lines(data_lines, columns[1:], header)
  return output
  
def read_header(lines):
  '''
    Function to read IN12 file header information and check if the file is in the right format.
  '''
  try:
    if  (lines.pop(6)!='VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV\n') or\
        (lines.pop(3)!='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n') or\
        (lines.pop(0)!='RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR\n'):
      return False, [],  []
  except IndexError:
    return False, [],  []
  lines.pop(0)
  lines.pop(0)
  lines.pop(0)
  lines.pop(0)
  columns=lines.pop(-1).split()
  if not 'CNTS' in columns:
    return False, [],  []
  variables={}
  parameters={}
  user=''
  time=''
  command='unknown'
  for line in lines:
    item, value=line.split(':', 1)
    if item=='PARAM':
      for param in value.split(','):
        split_param=param.split('=')
        try:
          parameters[replace_names(split_param[0])]=float(split_param[1])
        except ValueError:
          parameters[replace_names(split_param[0])]=None
    elif item=='VARIA' or item=='POSQE':
      for var in value.split(','):
        var_param=var.split('=')
        try:
          variables[replace_names(var_param[0])]=float(var_param[1])
        except ValueError:
          variables[replace_names(var_param[0])]=None
    elif item=='USER_':
      user=value
    elif item=='DATE_':
      time=value
    elif item=='COMND':
      command=value
    elif item=='TITLE':
      title=value
  return True, (time, user, title, command, variables, parameters), columns
  
def string_or_float(string_line):
  '''
    Short function to test if first column of a line is a float number or string.
    Used to devide Header/Comment from Data lines.
  '''
  if len(string_line)==0:
    return False
  try:
    float(string_line[0])
    return True
  except ValueError:
    return False

def get_first_data_line(lines):
  '''
    Short function to find the first line containing data.
    Used to devide Header/Comment from Data lines.
  '''
  for i, line in enumerate(reversed(lines)):
    if not string_or_float(line.split()):
      return len(lines)-i

def read_data_lines(lines, columns, header):
  '''
    Function to creat a MeasurementData object from the columns of the file.
  '''
  time, user, title, command, variables, parameters=header
  md_columns=[(replace_names(column), get_dimensions(column)) for column in columns]
  md_columns.append(('error', 'counts'))
  y_column=columns.index('CNTS')
  error_column=len(columns)
  if columns[0]=='PAL':
    x_column=1
  else:
    x_column=0
  split=str.split
  def process_line(line):
    spl=split(line)
    float_list=map(float, spl)[1:]
    float_list.append(sqrt(float_list[y_column]))
    return float_list
  processed_lines=map(process_line, lines)
  # is this a polarized measurement
  if x_column==1:
    error_column-=1
    y_column-=1
    number_of_channels=max([line[0] for line in processed_lines])
    data_objects=[MeasurementData(md_columns[1:], 
                                [], 0, y_column, error_column)
                  for i in range(number_of_channels)]
    for i in range(number_of_channels):
      lines_i=[line[1:] for line in processed_lines if line[0] == i + 1]
      map(data_objects[i].append, lines_i)
      data_objects[i].sample_name=title.replace('\n', '')
      scan_type=replace_names(columns[x_column])
      data_objects[i].short_info= scan_type + '-scan started at (%2g %2g %2g) with pol. %i' % (variables['h'], variables['k'], variables['l'], i)
    return data_objects
  else:
    data_object=MeasurementData(md_columns, 
                                [], 0, y_column, error_column)
    map(data_object.append, processed_lines)
    data_object.sample_name=title.replace('\n', '')
    scan_type=replace_names(columns[x_column])
    data_object.short_info= scan_type + '-scan started at (%2g %2g %2g)' % (variables['h'], variables['k'], variables['l'])
    return [ data_object ]
  
def get_dimensions(item):
  '''
    Lookup the dimension of the values in the datafile.
  '''
  for seq in column_dimensions:
    if item in seq[0]:
      return seq[1]
  return ''

def replace_names(item):
  '''
    Replace variable names from datafile by custom names.
  '''
  for replacement in name_replacements:
    if replacement[0] == item.strip():
      return replacement[1]
  return item

if __name__ == '__main__':    #code to execute if called from command-line for testing
  import sys
  read_data(sys.argv[1])
  