# -*- encoding: utf-8 -*-
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
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

def read_data(file_name):
  '''
    Read the data of a in12 data file.
    
    @param file_name The name of the file to import
    
    @return MeasurementData object with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
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
    
    @return If right format, sequence with some information and the data columns present in the file.
  '''
  # test for correct format with these lines:
  try:
    if  (lines.pop(6)!='VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV\n') or\
        (lines.pop(3)!='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n') or\
        (lines.pop(0)!='RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR\n'):
      return False, [],  []
  except IndexError:
    return False, [],  []
  # pop lines without information
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
    If the measurement is done using a .pol file the data points are splitted
    into seqences corresponding to the polarizations.
    
    @param lines List of lines in input file
    @param coluns List of data columns in that file
    @param header The header information to use for e.g. the plot title
    
    @return List of MeasurementData objects with the read data
  '''
  title=header[2]
  variables=header[4]
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
                  for i in range(int(number_of_channels))]
    for i in range(number_of_channels):
      lines_i=[line[1:] for line in processed_lines if line[0] == i + 1]
      map(data_objects[i].append, lines_i)
      data_objects[i].sample_name=title.replace('\n', '')
      scan_type=replace_names(columns[x_column])
      data_objects[i].short_info= scan_type + '-scan started at (%2g %2g %2g) with pol. %i' % (variables['h'], variables['k'], variables['l'], i)
      data_objects[i].info=create_info(header)
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
    Uses the mapping defined in config.in12.column_dimensions.
    
    @return String for the dimension
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
  
def create_info(header):
  '''
    Use the header list to create an information string which is easier readable.
    
    @return The information string
  '''
  time, user, title, command, variables, parameters=header
  info_text=['']
  info_text.append('data taken from IN12 file')
  info_text.append('User: %s' % user.strip())
  info_text.append('Time: %s' % time.strip())
  info_text.append('Title: %s' % title.strip())
  info_text.append('')
  info_text.append('Scaned with command: %s' % command)
  add_1=''
  add_2=''
  info_text.append('Variables:')
  for i, var in enumerate(sorted(variables.items())):
    if var[1] is not None:
      value='\t% -11g' % var[1]
      add_2+=value
    else:
      add_2+='\tN/A     '
    add_1+=('\t %-15s' % var[0].strip()[:15])[:len(value)]
    if (i % 8) == 7:
      info_text.append(add_1)
      info_text.append(add_2)
      add_1=''
      add_2=''
      info_text.append('')
  if (i % 8) != 7:
    info_text.append(add_1)
    info_text.append(add_2)
    info_text.append('')
  info_text.append('')
  add_1=''
  add_2=''
  info_text.append('Parameters:')
  for i, par in enumerate(sorted(parameters.items())):
    if par[1] is not None:
      value='\t% -11g' % par[1]
      add_2+=value
    else:
      add_2+='\tN/A     '
    add_1+=('\t %-15s' % par[0].strip()[:15])[:len(value)]
    if (i % 8) == 7:
      info_text.append(add_1)
      info_text.append(add_2)
      add_1=''
      add_2=''
      info_text.append('')
  if (i % 8) != 7:
    info_text.append(add_1)
    info_text.append(add_2)
    info_text.append('')
  info_text.append('')
  return '\n'.join(info_text)

if __name__ == '__main__':    #code to execute if called from command-line for testing
  import sys
  read_data(sys.argv[1])
  
