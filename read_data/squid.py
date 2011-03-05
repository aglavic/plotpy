# -*- encoding: utf-8 -*-
'''
  Functions to read from a SQUID data file.
  Mostly just string processing.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import sys
from measurement_data_structure import MeasurementData
import config.squid

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def read_data(file_name,COLUMNS_MAPPING,MEASUREMENT_TYPES): 
  '''
    Read the ppms/mpms datafile.
    
    @param input_file Name of the file to read
    @param COLUMNS_MAPPING A list of column names with the associated column in the MeasurementData object
    @param MEASUREMENT_TYPES List of measurements with at least one constant data column (e.g. T=const)
    
    @return List of MeasurementData objects for all measured sequences of 'NULL'
  '''
  if os.path.exists(file_name):
    if file_name.endswith('.gz'):
      # use gziped data format
      import gzip
      file_handler=gzip.open(file_name, 'r')
    else:
      file_handler=open(file_name, 'r')
    input_file_lines=file_handler.readlines()
    file_handler.close()
    if input_file_lines[0].find('[Header]')>=0:
      measurement_info=read_header(input_file_lines)
      while input_file_lines.pop(0).find('[Data]')==-1:
        continue
      measurement_data=read_data_lines(input_file_lines,measurement_info,COLUMNS_MAPPING,MEASUREMENT_TYPES)
      if measurement_data=='NULL':
        print "No valid data found!"
        return 'NULL'
      for split in config.squid.SPLIT_AFTER:
        new_measurement_data=[]
        for i, dataset in enumerate(measurement_data):
          if split[0] in dataset.dimensions():
            new_measurement_data+=split_after_read(dataset, split)
          else:
            new_measurement_data.append(dataset)
        measurement_data=new_measurement_data
      new_measurement_data=[]
      for dataset in measurement_data:
        if len(set(dataset.data[dataset.ydata].values)) <= 1:
          continue
        else:
          new_measurement_data.append(dataset)
      measurement_data=new_measurement_data
    else:
      print "Wrong file type! Doesn't contain header information."
      return 'NULL'
    return measurement_data
  else:
    print 'File '+file_name+' does not exist.'
    return 'NULL'

def get_columns(input_file): 
  '''
    Just return the columns present in the file.
    
    @return List of measured columns or 'NULL'
  '''
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
  

def read_header(input_file_lines): 
  '''
    Read header of the datafile.
    
    @return Measurement information and Name of the sample
  '''
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
  '''
    Check if the data from two lines belong to the same sequence.
  '''
  output=True
  for ty in type_i[0]:
    if (abs(data_1[ty[0]]-data_2[ty[0]])<ty[1])&output:
      output=True
    else:
      output=False
  return output
  
def read_data_lines(input_file_lines,info,COLUMNS_MAPPING,MEASUREMENT_TYPES): 
  '''
    Read data points line by line.
    
    @return List of MeasurementData objects
  '''
  output=[] #initialise data array containing data objects
  try:
    line=input_file_lines.pop(0).split(',')
  except IndexError:
    return "NULL"
  count=1
  columns=[]
  # define which columns contain the relevant data
  for item in line:
    count=count+1
    for mapping in COLUMNS_MAPPING:
      if item==mapping[0]:
        if len(mapping)==3 or mapping[3] not in line:
          columns.append([count-2,mapping[1],mapping[2]])
        else:
          columns.append([count-2,mapping[1],mapping[2], line.index(mapping[3])])
    columns.sort(key=lambda x:x[1])
  # Find the columns of the types which can be used with this measurement.
  # The columns can be given by index or name, if the name is not present
  # the type is ignored.
  applicable_types=[]
  column_names=[col[2][0] for col in columns]
  for type_i in MEASUREMENT_TYPES:
    if (type_i[1] in column_names or type(type_i[1]) is int) and \
       (type_i[2] in column_names or type(type_i[2]) is int) and \
       (type_i[3] in column_names or type(type_i[3]) is int):
      use_indices=[]
      for col in type_i[1:4]:
        if type(col) is int:
          use_indices.append(col)
        else:
          use_indices.append(column_names.index(col))
      useable=True
      const_col_indices=[]
      for const_col in type_i[0]:
        if const_col[0] in column_names:
          const_col_indices.append((column_names.index(const_col[0]), const_col[1]))
        elif type(const_col[0]) is int:
          const_col_indices.append(const_col)
        else:
          useable=False
          break
      if not useable:
        continue
      applicable_types.append([
                               const_col_indices, 
                               use_indices[0], 
                               use_indices[1], 
                               use_indices[2], 
                               type_i[4], 
                               ])
  not_found=True
  while not_found:
    try:
      #read 2 lines to determine the type of the first sequence
      data_1=read_data_line(input_file_lines.pop(0),columns)
      data_2=read_data_line(input_file_lines.pop(0),columns)
    except IndexError:
      print "No valid data in file."
      return 'NULL'
    if (data_1!='NULL')&(data_2!='NULL'):
      for type_i in applicable_types:
        if not_found and check_type(data_1,data_2,type_i):
          data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],-1)
          data.append(data_1)
          data.append(data_2)
          data.plot_options=type_i[4]
          data.filters=config.squid.filters
          not_found=False
    else:
      return 'NULL'
  try: # if no sequence of set types is found return null
    data.info=info[0]
  except:
    print 'No sequence with right type found!'
    return 'NULL'
  data.sample_name=info[1]
  # trying to speed up function lookup
  data_is_type=data.is_type
  data_append=data.append
  count_lines=len(input_file_lines)
  if count_lines>10000:
    sys.stdout.write('Reading progress [%]:   0')
    sys.stdout.flush()
  for i,line in enumerate(input_file_lines): # append data from one sequence to the object or create new object for the next sequence
    if (i+1)%10000==0:
      procent=float(i)/count_lines*100.
      sys.stdout.write('\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                        'Reading progress [%%]: %3d' % procent)
      sys.stdout.flush()
    next_data=read_data_line(line, columns)
    if next_data != 'NULL':
      if data_is_type(next_data):
        data_append(next_data)
      else:
        output.append(data)
        next_data_2=read_data_line(input_file_lines[i+1],columns)
        if next_data_2 != 'NULL':
          not_found=True
          for type_i in applicable_types:
            if check_type(next_data,next_data_2,type_i)&not_found:
              data=MeasurementData([column[2] for column in columns],type_i[0],type_i[1],type_i[2],-1)
              data.plot_options=type_i[4]
              not_found=False
              data.info=info[0]
              data.sample_name=info[1]
              data.filters=config.squid.filters
              data.append(next_data)
              data.append(next_data_2)
              data_is_type=data.is_type
              data_append=data.append
              # trying to speed up function lookup
        else:
          return output
    else:
      output.append(data)
      return output
  if count_lines>10000:
    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                    'Done!                                              \n')
    sys.stdout.flush()
  output.append(data)
  return output

def read_data_line(input_file_line, columns): 
  '''
    Read one line of data and output the data as a list of floats.
    
    @return List of floats or 'NULL'
  '''
  line=input_file_line.split(',')
  values=[]
  if len(line)>=len(columns):
    for column in columns:
      val=line[column[0]]
      if len(column)==4:
        err=line[column[3]]
        if val != '' and err!='':
          values.append((float(val), float(err)))
        else:
          values.append((0., 1.))        
      else:
        if val != '':
          values.append(float(val))
        else:
          values.append(0.)
    return values
  else:
    return 'NULL'
  
def split_after_read(dataset, split):
  '''
    Split a dataset by a specific column after the file has been read.
    
    @param dataset A MeasurementData object
    @param split A list of 'dimension name', 'sensitivity'
    
    @return list of MeasurementData objects
  '''
  from copy import deepcopy
  output=[]
  dims=dataset.dimensions()
  dims.append('DIRECTION')
  # only split if the right measurement is presen (e.g. frequency only for AC)
  if split[0] not in dims or split[1] not in dims:
      return [dataset]
  if split[1]!='DIRECTION':
    split_col=dims.index(split[1])
    found_entries=[]
    for point in dataset:
      key=round(point[split_col]/split[2])
      if key in found_entries:
        output[found_entries.index(key)].append(point)
      else:
        found_entries.append(key)
        output.append(deepcopy(dataset))
        for physprop in output[-1].data:
          physprop.values=[]
        output[-1].append(point)
        output[-1].short_info='at %d %s' % (key*split[2], dataset.units()[split_col])
  else:
    xcol=dataset.xdata
    if dims[xcol]!=split[0]:
      return [dataset]
    direction = dataset[0][xcol]<dataset[4][xcol]
    lastpoint=dataset[0]
    active_data=deepcopy(dataset)
    for col in active_data.data:
      col.values=[]
    active_data.append(lastpoint)
    for point in dataset[1:]:
      if (direction and (lastpoint[xcol]<=point[xcol]+split[2])) or\
         (not direction and (lastpoint[xcol]>=point[xcol]-split[2])):
        active_data.append(point)
        lastpoint=point
      else:
        direction=not direction
        lastpoint=point
        output.append(active_data)
        active_data=deepcopy(dataset)
        for col in active_data.data:
          col.values=[]
        active_data.append(point)
    output.append(active_data)
  return output
  
