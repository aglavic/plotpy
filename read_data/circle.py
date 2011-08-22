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
import math, numpy
from measurement_data_structure import MeasurementData, PhysicalProperty
from config.circle import *

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.9"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

def read_data(input_file):
  '''
    Read the datafile from spec.
  '''
  if os.path.exists(input_file):
    if input_file.endswith('.fio') or input_file.endswith('.fio.gz'):
      return read_data_p09(input_file)
    elif input_file.rstrip('.gz').split('.')[-1].isdigit():
      return read_data_4id(input_file)
    elif input_file.endswith('.gz'):
      # use gziped format file
      import gzip
      file_handle=gzip.open(input_file, 'r')
    else:
      file_handle=open(input_file, 'r')
    input_file_lines=file_handle.readlines()
    file_handle.close()
    sample_name, last_comments=read_file_header(input_file_lines)
    if not sample_name:
      print "Wrong file type, no spec header found (#F,#E,#D,#C)!"
      sample_name=''
    measurement_data=read_data_lines(input_file_lines, sample_name, last_comments)
    if len(measurement_data)==0:
      print "No scan data found in file %s." % input_file
    return measurement_data
  else:
    print 'File '+input_file+' does not exist.'
    return []  

def read_file_header(input_file_lines):
  '''
    Read the header of the file.
    
    @param input_file_lines List of lines to be evaluated
    
    @return The sample name defined in the file or None if the wron filetype.
  '''
  if not (input_file_lines[0].startswith('#F') and 
          input_file_lines[1].startswith('#E') and 
          input_file_lines[2].startswith('#D')):
    return None, None
  try:
    line=input_file_lines[3]
    sample_name=line.split('User')[0].split(' ', 1)[1]
    # remove characters from keyboard input
    if '[D' in sample_name or '\b' in sample_name:
      while '[D' in sample_name:
        i=sample_name.index('[D')
        sample_name=sample_name[:i-1]+sample_name[i+3:]
      while '\b' in sample_name:
        i=sample_name.index('\b')
        sample_name=sample_name[:i-1]+sample_name[i+1:]
    last_comments=''
    for line in input_file_lines[4:]:
      if line.startswith('#C'):
        last_comments+=line
      elif line.startswith('#S'):
        return sample_name, last_comments
    return None, None
  except:
    return None, None

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

def read_data_lines(input_file_lines, sample_name, last_comments): 
  '''
    Read data points line by line.
    
    @param input_file_lines List of lines from the input file
    @param sample_name Sample Name from file header
    @param last_comments comment lines from before the scan
    
    @return MeasurementData objects
  '''
  scan_indices=[]
  for i, line in enumerate(input_file_lines):
    if line.startswith('#S'):
      scan_indices.append(i)
  output=[]
  for i, j in zip(scan_indices[:], scan_indices[1:]+[len(input_file_lines)]):
      dataset, last_comments=read_scan(input_file_lines[i:j], last_comments)
      if dataset is not None:
        dataset.sample_name=sample_name        
        output.append(dataset)
  return output

def read_scan(scan_lines, last_comments):
  '''
    Read and evaluate the lines of one scan.
  '''
  scan_header, scan_data=get_scan_header(scan_lines)
  scan_header['last_comments']=last_comments
  if len(scan_data)<2:
    return None, None
  columns=[]
  for col in scan_header['columns']:
    if col in KNOWN_COLUMNS:
      columns.append(KNOWN_COLUMNS[col])
    else:
      columns.append((col, ''))
  xcol, ycol, errorcol, zcol= get_type_columns(scan_header['type'], [col[0] for col in columns])
  output=MeasurementData(x=xcol, y=ycol, zdata=zcol, yerror=errorcol)
  data=numpy.array(map(lambda line: numpy.fromstring(line, sep=" "), scan_data)).transpose()
  for i, col in enumerate(columns):
    output.data.append(PhysicalProperty(col[0], col[1], data[i]))
    if col[1]=='counts':
      output.data[-1].error=numpy.sqrt(data[i])
  output.short_info='#'+scan_header['index']+' - '
  from string import Template
  output.info=Template('''    Scan: ${type}
    Index: ${index}            Date: ${date}
    
    Lattice Parameters: ${lp}
    Q at Start: ${q_start}
    Angles at Start: ${angles_start}

    Comments (before scan):
${last_comments}
    Comments (during scan):
${comments}
    ''').substitute(scan_header)
  if 'h' in output.dimensions():
    index=output.dimensions().index('h')
    output.data.append( (output.data[index]*scan_header['rl'][0])//('q_x', 'Å^{-1}') )
  if 'k' in output.dimensions():
    index=output.dimensions().index('k')
    output.data.append( (output.data[index]*scan_header['rl'][1])//('q_y', 'Å^{-1}') )
  if 'l' in output.dimensions():
    index=output.dimensions().index('l')
    output.data.append( (output.data[index]*scan_header['rl'][2])//('q_z', 'Å^{-1}') )
  recheck_type(output, scan_header)
  return output, scan_header['comments']

def get_type_columns(type_line, columns):
  '''
    Return the indices of columns to plot.
  '''
  type, options=type_line.split(None, 1)
  intensity=len(columns)-1
  intensity_error=-1
  for col in INTENSITY_COLUMNS:
    if col in columns:
      intensity=columns.index(col)
      break
  if type=='hklscan':
    hklranges=map(float, options.strip().split())
    if abs(hklranges[1]-hklranges[0])>1e-5:
      return columns.index('h'), intensity, intensity_error, -1
    if abs(hklranges[3]-hklranges[2])>1e-5:
      return columns.index('k'), intensity, intensity_error, -1
    if abs(hklranges[5]-hklranges[4])>1e-5:
      return columns.index('l'), intensity, intensity_error, -1
  elif type=='hklmesh':
    items=options.strip().split()
    return columns.index(items[0].lower()), columns.index(items[4].lower()), intensity_error, intensity
  elif type=='mesh':
    items=options.strip().split()
    first_angle=items[0]
    if first_angle in KNOWN_COLUMNS:
      first_angle=KNOWN_COLUMNS[first_angle][0]
    second_angle=items[4]
    if second_angle in KNOWN_COLUMNS:
      second_angle=KNOWN_COLUMNS[second_angle][0]
    first_index=columns.index(first_angle)
    second_index=columns.index(second_angle)
    return first_index, second_index, intensity_error, intensity
  elif type=='timescan_cm' or type=='Escan':
    return columns.index('E'), intensity, intensity_error, -1
  elif type=='ascan' and options.split()[0]=='lake':
    return columns.index('T_{sample}'), intensity, intensity_error, -1
  else:
    return 0, intensity, intensity_error, -1

def recheck_type(dataset, scan_header):
  type_line=scan_header['type']
  type_line=scan_header['type']
  type, options=type_line.split(None, 1)
  if type=='timescan':
    if 'T_{sample}' in dataset.dimensions():
      t_index=dataset.dimensions().index('T_{sample}')
      T=dataset.data[t_index]
      # if the temperature of start and end value is differs by more the 5 times the temperature fluctuation
      # set T as x
      if abs(T[-1]-T[0])>(numpy.abs(T[:-1]-T[1:]).var()**2)*5:
        dataset.xdata=t_index

def get_scan_header(scan_lines):
  '''
    Read header of scan and return the data lines and some information of the header.
    
    @param scan_lines lines corresponding to one scan
    
    @return dictionary with header informations and lines containing data
  '''
  scan_header={}
  for i, line in enumerate(scan_lines):
    if (line[0:2]=='#L'):
      scan_header['columns']=line[3:-1].split('  ')
      break
    elif (line[0:2]=='#S'):
      scan_header['index'], scan_header['type']=line[3:].strip().split('  ', 1)
    elif line[0:3] in ['#N ','#G0', '#G2','#G3','#G4']:
        continue
    elif line[0:2]=='#D':
      scan_header['date']=line[3:].strip()
    elif line[0:2]=='#T':
      scan_header['time']=line[3:].strip().split()[0]
    elif line[0:2]=='#Q':
      scan_header['q_start']=line[3:].strip()
    elif line[0:3]=='#P0':
      scan_header['angles_start']=line[3:].strip()
    elif line[0:3]=='#G1':
      lp=line[3:].strip().split()
      scan_header['lp']="a=%s b=%s c=%s α=%s β=%s γ=%s" % (lp[0], lp[1], lp[2], 
                                                           lp[3], lp[4], lp[5])
      scan_header['rl']=map(float, (lp[6], lp[7], lp[8], lp[9], lp[10], lp[11]))
    elif line[0:2]=='#D':
      scan_header['date']=line[3:].strip()
  data_lines=scan_lines[i+1:]
  comment_lines=filter(lambda line: line.startswith('#'), data_lines)
  data_lines=filter(lambda line: not (line.startswith('#') or line.strip()==''), data_lines)
  scan_header['comments']=''.join(comment_lines)
  return scan_header, data_lines
  
def read_data_p09(input_file):
  '''
    Read data aquired at P09 beamlime of PETRA III.
  '''
  if input_file.endswith('.gz'):
    import gzip    
    file_handle=gzip.open(input_file, 'r')
  else:
    file_handle=open(input_file, 'r')
  text=file_handle.read()
  if not (('! Parameter' in text) and ('! Data' in text)):
    print "No valid P09 header found."
    return 'NULL'
  name=text.split('Name: ', 1)[1].split(' ', 1)[0].strip()
  scan_type=text.split('%c')[1].strip().split()[0]
  parameter_region=text.split('%p')[1].split('%d')[0].strip().splitlines()
  data_region=text.split('%d')[1].strip().splitlines()
  parameter_region=filter(lambda item: not item.startswith('!'), parameter_region)
  data_region=filter(lambda item: not item.startswith('!'), data_region)
  data_region=map(str.strip, data_region)
  parameter_region=map(lambda line: line.strip().split('=', 1), parameter_region)
  parameters={}
  for param, value in parameter_region:
    parameters[param]=value
  columns=[]
  for i, line in enumerate(data_region):
    if line.strip().startswith('Col'):
      try:
        columns.append(line.split(name.upper()+'_')[1].split()[0])
      except IndexError:
        columns.append(scan_type)
    else:
      data_region=data_region[i:]
      break
  for i, col in enumerate(columns):
    if col in P09_COLUMNS_MAPPING:
      columns[i]=P09_COLUMNS_MAPPING[col]
    else:
      columns[i]=(col, '°')
  columns[0]=columns[1]
  columns[1]=['None', '']
  data_region=map(str.strip, data_region)
  data=map(str.split, data_region)
  data=numpy.array(data, dtype=numpy.float32)
  data=data.transpose()
  output=MeasurementData(x=0, y=2)
  for i, column in enumerate(columns):
    if column[1]=='counts':
      output.append_column( PhysicalProperty(column[0], column[1], data[i], numpy.sqrt(data[i])))
    else:
      output.append_column( PhysicalProperty(column[0], column[1], data[i]))
  I=PhysicalProperty('I', 'counts', data[columns.index(('I_{RAW}', 'counts'))], 
                        numpy.sqrt(data[columns.index(('I_{RAW}', 'counts'))]))
  I*=data[columns.index(('Attenuation', ''))]
  output.append_column(I)
  output.ydata=len(output.data)-1
  output.info="\n".join([param[0]+": "+param[1] for param in parameters.items()])
  output.sample_name=name.split('_')[-1]
  if output.x.dimension=='hkl-Scan':
    output.x.dimension='-Scan'
    output.x.unit=''
    hidx=output.dimensions().index('H')
    kidx=output.dimensions().index('K')
    lidx=output.dimensions().index('L')
    if (output.data[lidx].max()-output.data[lidx].min())>0.02:
      output.x.dimension='L'+output.x.dimension
    if (output.data[kidx].max()-output.data[kidx].min())>0.02:
      output.x.dimension='K'+output.x.dimension
    if (output.data[hidx].max()-output.data[hidx].min())>0.02:
      output.x.dimension='H'+output.x.dimension
  return [output]

def read_data_4id(input_file):
  '''
    Read data from 4-ID-C station at APS.
  '''
  if input_file.endswith('.gz'):
    import gzip
    file_handle=gzip.open(input_file, 'r')
  else:
    file_handle=open(input_file, 'r')
  text=file_handle.read()
  if not text.startswith('## mda2ascii'):
    print "No valid 4-ID ascii header found."
    return 'NULL'
  header, data_with_head=text.split('# Column Descriptions:',1)
  header_info=extract_4id_headerinfo(header)
  type, file_columns, data=extract_4id_columns_and_data(data_with_head)
  if len(data)==0:
    print "No data in the file."
    return 'NULL'
  output=MeasurementData(x=0, y=1)
  used_columns=[0]
  for i, column, unit in ID4_SCANS[type]:
    if column is None:
      column, unit=file_columns[i]
      if column in ID4_MAPPING:
        column=ID4_MAPPING[column]
    if unit=='counts':
      output.append_column( PhysicalProperty(column, unit, data[i], numpy.sqrt(data[i])))
    else:
      output.append_column( PhysicalProperty(column, unit, data[i]))
    used_columns.append(i)
  for i in range(len(file_columns)):
    if i not in used_columns:
      column, unit=file_columns[i]
      column="% 2i: " % i +column
      if column in ID4_MAPPING:
        column=ID4_MAPPING[column]
      if unit=='counts':
        output.append_column( PhysicalProperty(column, unit, data[i], numpy.sqrt(data[i])))
      else:
        output.append_column( PhysicalProperty(column, unit, data[i]))
  output.info="Started at: %s" % header_info['starting time']
  output.info+='\n'+"\n".join(map(lambda item: "%s: \t%s" % (item[0], item[1]), header_info['status info']))
  output.short_info="#%04i" % header_info['scan number']
  output.sample_name=''
  return [output]

def extract_4id_headerinfo(header):
  '''
    Extract some infor from the file header.
  '''
  info={'status info': []}
  for line in header.splitlines():
    if line.startswith('# Scan number'):
      info['scan number']=int(line.split('=')[1])
    elif line.startswith('# Scan time'):
      info['starting time']=line.split('=')[1].strip()
    elif 'scaler time preset' in line:
      info['time']=float(line.split(',')[2].strip(' "'))
    elif 'SGM Energy' in line:
      info['status info'].append(('Energy (eV)', line.split(',')[2].strip(' "')))
    elif '7T Z pos' in line:
      info['status info'].append(('Z', line.split(',')[2].strip(' "')))
    elif '7T rotation' in line:
      info['status info'].append(('φ', line.split(',')[2].strip(' "')))
    elif '7T T sample' in line:
      temperature=float(line.split(',')[2].strip(' "'))
      info['status info'].append(('T', "%.1f" % temperature))
    elif '7T field' in line:
      field=float(line.split(',')[2].strip(' "'))*0.1
      info['status info'].append(('H (T)', "%.3g" % field))
      
  return info

def extract_4id_columns_and_data(data_with_head):
  '''
    Extract the data and columns of the file.
  '''
  type='other'
  lines=data_with_head.splitlines()
  columns=[]
  data_lines=[]
  for i,  line in enumerate(lines):
    if not (line.startswith('#') or line.strip()==''):
      data_lines=lines[i:]
      break
    if 'Index' in line:
      columns.append(('Point', ''))
    if 'Positioner' in line:
      items=line.split(',')
      columns.append((
                      items[1].strip(), 
                      items[3].strip()
                      ))
    if 'Detector' in line:
      items=line.split(',')
      columns.append((
                      items[1].strip(), 
                      items[2].strip()
                      ))
  if 'M3C DS Y' in data_with_head:
    type='mirror-align'
  elif 'XMCD_2_Diff' in data_with_head:
    type='XMCD'
  elif 'Positioner 2' in data_with_head:
    type='e-scan'
  data_lines=map(str.strip, data_lines)
  data=map(str.split, data_lines)
  data=numpy.array(data, dtype=numpy.float32)
  data=data.transpose()  
  return type, columns, data
