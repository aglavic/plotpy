# -*- encoding: utf-8 -*-
'''
  Functions to read from dns data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from math import sqrt
import numpy
from measurement_data_structure import MeasurementData
import config.dns
from config.dns import *

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def read_data(file_name, print_comments=True):
  '''
    Read the data of a dns data file.
    
    @return MeasurementData object with the data from file_name
  '''
  if not os.path.exists(file_name): # Test if the file exists
    if print_comments:
      print "File does not exist."
    return 'NULL'
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  add_info={}
  # read header to test if this is a dns data file
  if (file_handler.readline().split()[0:3]==['#','DNS','Data']): 
    file_handler.readline() # skip empty line
    add_info['header']=read_header(file_handler) # read header information
    if config.dns.LAMBDA_NEUTRON:
      add_info['lambda_n']=config.dns.LAMBDA_NEUTRON
      read_lambda(file_handler)
    else:
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
    file_handler.close()
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
  
def read_header(file_handler): 
  ''' 
    Read file header information.
    
    @return Header string without # characters
  '''
  file_handler.readline()
  line=file_handler.readline()
  output=''
  while (not line[0:6]=='#-----'): # while header section is not over
    output=output+line.lstrip('#')
    line=file_handler.readline()
  return output
    
def read_lambda(file_handler): 
  ''' 
    Read wavelength when after comment section.
    
    @return Float of wavelength
  '''
  file_handler.readline()
  return abs(float(file_handler.readline().split()[4]))*10
  
def read_info(file_handler,info_name): 
  ''' 
    Read until specified line.
    
    @param info_name String of the parameter to search for
  '''
  line=file_handler.readline()
  while (line.find(info_name)==-1):
    line=file_handler.readline()
  return float(line.split()[2])

def read_detector_data(file_handler,detectors,time_channels): 
  '''
    Reads data and stores it in an array.
    
    @param detectors Number of detectors installed
    @param time_channels number of channels to read from
    
    @return List of data points
  '''
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

def read_data_d7(file_name, print_comments=True):
  '''
    Read the data of a d7 data file.
    
    @return List of MeasurementData objects with the data from file_name
  '''
  if not os.path.exists(file_name): # Test if the file exists
    if print_comments:
      print "File does not exist."
    return 'NULL'
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  # read header to test if this is a d7 data file
  if file_handler.readline().strip()=='RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR': 
    comments, head_info, data_string=file_handler.read().split(
                            'IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
    # Read additional information from the header
    add_info=evaluate_header_d7(comments, head_info)
    # extract counts from datastring
    counts=map(float, data_string.split())
    counts=[counts[i*132:(i+1)*132] for i in range(len(counts)/132)]
    #counts=map(lambda count: numpy.array(list(reversed(count))), counts)
    counts=map(lambda count: numpy.array((count[88:132]+count[44:88]+count[0:44])), counts)
    detector_angles=(add_info['detector_bank_2T']-numpy.array(D7_DETECTOR_MAP[0])).tolist()+\
                    (add_info['detector_bank_2T[1]']-numpy.array(D7_DETECTOR_MAP[1])).tolist()+\
                    (add_info['detector_bank_2T[2]']-numpy.array(D7_DETECTOR_MAP[2])).tolist()
    # create objects
    datasets=[]
    for i, counts_array in enumerate(counts):
      measurement_data=MeasurementData([ ['Detector', ''], 
                                       ['Channel_0', 'counts/'+SCALE_BY[1]], 
                                       ['Error_Ch_0', 'counts/'+SCALE_BY[1]], 
                                       ['Detectorbank', '°'],
                                       ], [],0,1,2,zdata=-1)
      error_array=numpy.sqrt(counts_array)
      counts_array/=add_info[SCALE_BY[0]+'[%i]' % i]
      error_array/=add_info[SCALE_BY[0]+'[%i]' % i]
      measurement_data.data[3].values=list(detector_angles)
      measurement_data.data[1].values=counts_array.tolist()
      measurement_data.data[2].values=error_array.tolist()
      measurement_data.data[0].values=range(132)
      measurement_data.dns_info=dict(add_info)
      measurement_data.dns_info[SCALE_BY[0]]=add_info[SCALE_BY[0]+'[%i]' % i]
      measurement_data.dns_info.update({
                                    'flipper': add_info['currents[%i]' % i][0], 
                                    'flipper_compensation': add_info['currents[%i]' % i][1], 
                                    'C_a': add_info['currents[%i]' % i][2], 
                                    'C_b': add_info['currents[%i]' % i][3], 
                                    'C_c': add_info['currents[%i]' % i][4], 
                                    'C_z': add_info['currents[%i]' % i][5], 
                                  })
      measurement_data.sample_name=file_name+'[%i]' %i
      measurement_data.info="\n".join(map(lambda item: item[0]+': '+str(item[1]),
                                    sorted(add_info.items())))      
      datasets.append(measurement_data)
    return datasets
  else: # not dns data
    if print_comments:
      print "Wrong file type! Doesn't contain dns header information."
    return 'NULL'

def evaluate_header_d7(comments, head_info):
  '''
    Reads sample name and additional information as temperature and omega position 
    from d7 file header information.
    
    @return Dictionary of the read information.
  '''
  add_info={}
  header_blocks=head_info.split('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
  # extract the two data blocks
  header_blocks_data=[header_blocks[1].split('\n', 5)[5], 
          header_blocks[2].split(
            'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS')[0].split('\n', 5)[5]]
  header_blocks_data[0]=map(float, header_blocks_data[0].split())
  header_blocks_data[1]=map(float, header_blocks_data[1].split())
  # extract important information
  add_info['lambda_n']=header_blocks_data[0][0]
  add_info['detector_angles']=True
  add_info['detector_bank_2T']=header_blocks_data[0][164]
  add_info['detector_bank_2T[1]']=header_blocks_data[0][165]
  add_info['detector_bank_2T[2]']=header_blocks_data[0][166]
  #add_info['detector_bank_2T[3]']=header_blocks_data[0][167]
  add_info['omega']=-header_blocks_data[0][162]
  add_info['field']=header_blocks_data[1][6]
  add_info['temperature']=header_blocks_data[1][5]
  add_info['currents[0]']=header_blocks_data[1][8:14]
  add_info['currents[1]']=header_blocks_data[1][18:24]
  add_info['currents[2]']=header_blocks_data[1][28:34]
  add_info['currents[3]']=header_blocks_data[1][38:44]
  add_info['currents[4]']=header_blocks_data[1][48:54]
  add_info['currents[5]']=header_blocks_data[1][58:64]
  add_info['time[0]']=header_blocks_data[1][14]/100.
  add_info['time[1]']=header_blocks_data[1][24]/100.
  add_info['time[2]']=header_blocks_data[1][34]/100.
  add_info['time[3]']=header_blocks_data[1][44]/100.
  add_info['time[4]']=header_blocks_data[1][54]/100.
  add_info['time[5]']=header_blocks_data[1][64]/100.
  add_info['monitor[0]']=header_blocks_data[1][16]
  add_info['monitor[1]']=header_blocks_data[1][26]
  add_info['monitor[2]']=header_blocks_data[1][36]
  add_info['monitor[3]']=header_blocks_data[1][46]
  add_info['monitor[4]']=header_blocks_data[1][56]
  add_info['monitor[5]']=header_blocks_data[1][66]
  # evaluate comments
  true_comments=comments.split(
                 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')[2].split('\n', 2)[2]
  add_info['full comment']=true_comments
  add_info['sample_name']=true_comments.splitlines()[5].strip()
  return add_info

def read_vana_d7(file_name, print_comments=True):
  '''
    Readan already corrected vanadium data file from D7.
    
    @return List of MeasurementData objects with the data from file_name
  '''
  if not os.path.exists(file_name): # Test if the file exists
    if print_comments:
      print "File does not exist."
    return 'NULL'
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  # read header to test if this is a d7 data file
  text=file_handler.read()
  if text.startswith('Vanadium Intensities'):
    data=text.splitlines()[2:]
    data_items=map(str.split, data)
    def get_data(splitted_line):
      detector=int(splitted_line[0])-1
      intensity=float(splitted_line[2])
      dintensity=float(splitted_line[3])
      return [detector, intensity, dintensity]
    measurement_data=MeasurementData([ ['Detector', ''], 
                                       ['Channel_0', 'counts/'+SCALE_BY[1]], 
                                       ['Error_Ch_0', 'counts/'+SCALE_BY[1]], 
                                       ], [],0,1,2,zdata=-1)
    map(lambda splitted_line: measurement_data.append(get_data(splitted_line)), data_items[88:])
    map(lambda splitted_line: measurement_data.append(get_data(splitted_line)), data_items[44:88])
    map(lambda splitted_line: measurement_data.append(get_data(splitted_line)), data_items[:44])
    measurement_data.dns_info={
                    'detector_bank_2T': 0, 
                    'flipper': 0, 
                    'flipper_compensation': 99., 
                    'C_a': 0, 
                    'C_b': 0, 
                    'C_c': 0, 
                    'C_z': 0, 
                               }
    return measurement_data
  else:
    return 'NULL'
