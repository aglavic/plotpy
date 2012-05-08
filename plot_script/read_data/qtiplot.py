#-*- coding: utf8 -*-
'''
  Import for qtiplot project files. Reads the data of all tables.
'''

import os
import numpy
from plot_script.measurement_data_structure import MeasurementData, PhysicalProperty

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

def read_data(input_file):
  '''
    Read the datafile from QtiPlot.
  '''
  if os.path.exists(input_file):
    return read_qti_file(input_file)
  else:
    print 'File '+input_file+' does not exist.'
    return []

def read_qti_file(input_file):
  '''
    Read data from one input file if the header is correct.
  '''
  file_text=open(input_file, 'r').read()
  if not file_text.startswith('QtiPlot'):
    print "Wrong file type, header does not start with QtiPlot"
    return []
  # extract all tables
  tables=file_text.split('<table>')[1:]
  tables=[table.split('</table>')[0] for table in tables]
  output=[]
  for index, table in enumerate(tables):
    output.append(process_tables(input_file.rsplit('.qti', 1)[0], table, index))
  return output

def process_tables(name, table, index):
  '''
    Read the data of one table using the header to define column names.
  '''
  header, data=table.split('<data>')
  data=data.strip().split('</data>')[0]
  header_info=process_header(header)
  # split data by lines and columns
  data_lines=data.splitlines()
  data_items=map(lambda line: line.split('\t'), data_lines)
  # convert to numbers
  data=[map(float_convert, line) for line in data_items]
  data=numpy.array(data).transpose()
  column_names=header_info['columns']
  cols=[PhysicalProperty(column_names[i], '', data[i+1]) for i in range(len(data)-1)]
  output=MeasurementData()
  output.data=cols
  output.ydata=header_info['y-index']
  output.zdata=header_info['z-index']
  output.sample_name=name
  output.short_info=header_info['name']
  output.number=str(index)
  return output

def process_header(header):
  '''
    Read column and name information from the header of one table.
  '''
  output={}
  header_lines=header.strip().splitlines()
  output['name']=header_lines[0].split()[0]
  for line in header_lines:
    if line.startswith('header'):
      cols=line.split('\t')[1:]
      col_names=[col.split('[')[0] for col in cols]
      col_types=[col.split('[')[1][0] for col in cols]
      output['columns']=col_names
      output['col-types']=col_types
      output['y-index']=col_types.index('Y')
      if 'Z' in col_types:
        output['z-index']=col_types.index('Z')
      else:
        output['z-index']=-1
  return output

def float_convert(item):
  '''
    Convert a string to float if possible, otherwise return 0.
  '''
  try:
    return float(item)
  except ValueError:
    if ':' in item:
      try:
        h, m, s=item.split(':')
        return 3600.*float(h)+60.*float(m)+float(s)
      except:
        return 0.
    else:
      return 0.

