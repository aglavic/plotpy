# -*- encoding: utf-8 -*-
'''
  Functions to read from reflectometer UXD data file. Mostly just string processing.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import math
from plot_script import  measurement_data_structure
from plot_script.measurement_data_structure import PhysicalProperty
import codecs
from copy import deepcopy
from numpy import array, sqrt, pi, sin, float32, argsort, linspace
from array import array as py_array

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"


def read_data(file_name, DATA_COLUMNS):
  '''
    Read the datafile.
    
    @param input_file Name of the file to import
    @param DATA_COLUMNS List of columns to be imported
    
    @return List of MeasurementData objects with the file data
  '''
  measurement_data=[]
  if os.path.exists(file_name):
    if file_name.endswith('.raw'):
      # Philips X'Pert data files
      return read_bruker_raw(file_name)
    elif file_name.endswith('.txt'):
      # Philips X'Pert data files
      return read_data_philips(file_name)
    if file_name.endswith('.xrdml'):
      return read_data_xrdml(file_name)
    global sample_name
    sample_name=''
    if file_name.endswith('.gz'):
      # use gziped data format
      import gzip
      file_handler=gzip.open(file_name, 'r')
    else:
      file_handler=open(file_name, 'r')
    file_string=file_handler.read()
    input_file_lines=codecs.decode(file_string, "ISO 8859-15", 'ignore').splitlines()
    file_handler.close()
    while len(input_file_lines)>0:
      measurement_info=read_header(input_file_lines)
      if measurement_info=='NULL':
        return 'NULL'
      sequence=read_data_lines(input_file_lines, measurement_info, DATA_COLUMNS)
      if sequence!='NULL':
        # filter 0 intensity points
        sequence.filters=[(1, 0.0, 0.0, False)]
        # for Θ or 2Θ scans add q-column
        if "DRIVE='THETA'" in sequence.info:
          two_theta_start=float(sequence.info.split('2THETA=')[1].split("\n")[0])
          th=(sequence.x-sequence.x[0])+two_theta_start*0.5
          sequence.data.append((4.*pi/1.54*sin(th))//('Q_z', 'Å^{-1}'))
        elif "DRIVE='2THETA'" in sequence.info or "DRIVE='COUPLED'" in sequence.info:
          th=sequence.x*0.5
          sequence.data.append((4.*pi/1.54*sin(th))//('Q_z', 'Å^{-1}'))
        measurement_data.append(sequence)
      else:
        return 'NULL'
    return measurement_data
  else:
    print 'File '+file_name+' does not exist.'
    return measurement_data

def read_header(input_file_lines):
  '''
    Read header of datafile.
    
    @param input_file_lines List of lines from the input file
    
    @return Header information 
  '''
  output=''
  for ignore in input_file_lines:
    line=input_file_lines.pop(0)
    if ('COUNTS' in line):
      scantype=line[1:-1].rstrip('\r\n')
      # remove comment lines
      while ";" in input_file_lines[0]:
        line=input_file_lines.pop(0)
      return [output, scantype]
    else:
      output=output+line.rstrip('\n').rstrip('\r').lstrip('_').lstrip(';')+'\n'
  return 'NULL'

def read_data_lines(input_file_lines, info, DATA_COLUMNS):
  '''
    Read data points line by line.
    
    @return One MeasurementData object for a scan sequence
  '''
  global sample_name
  data_info=''
  scantype=None
  _count_time=1.
  for line in info[0].splitlines():
    setting=line.split('=')
    if setting[0]=='SAMPLE':
      sample_name=setting[1].rstrip('\n').strip("'")
    elif setting[0].strip()=='DRIVE':
      scantype=setting[1].strip("'").strip()
    elif setting[0].strip()=='STEPTIME':
      _count_time=float(setting[1])
    # Definitions for locked-coupled scans
    elif setting[0].strip()=='START':
      i=0
      start_angle=float(setting[1])
    elif setting[0].strip()=='STEPSIZE':
      increment_angle=float(setting[1])
    data_info=data_info+line+'\n'
  if scantype==None:
    print "Wrong file type, no 'DRIVE' defined in header!"
    return 'NULL'
  data=MeasurementData([DATA_COLUMNS[scantype], DATA_COLUMNS['COUNTS']],
                       [], 0, 1,-1)
  data.info=data_info
  data.sample_name=sample_name
  raw_data=[]
  while len(input_file_lines)>0: # append data from one sequence to the object or create new object for the next sequence
    line=input_file_lines.pop(0)
    next_data=read_data_line(line)
    if len(next_data)==2 and next_data!='NULL':
      raw_data.append((start_angle+i*increment_angle, next_data[0], next_data[1]))
      i+=1
    elif next_data!='NULL':
      raw_data.append(next_data)
    else:
      break
  x, y, dy=array(raw_data).transpose()
  x=measurement_data_structure.PhysicalProperty(DATA_COLUMNS[scantype][0],
                                                DATA_COLUMNS[scantype][1],
                                                x)
  y=measurement_data_structure.PhysicalProperty(DATA_COLUMNS['COUNTS'][0],
                                                DATA_COLUMNS['COUNTS'][1],
                                                y, dy)
  data.data=[x, y]
  return data

def read_data_line(input_file_line):
  '''
    Read one line and output data as list of floats.
  '''
  if input_file_line[0]==';':
    return 'NULL'
  else:
    line=input_file_line.strip().split()
    if len(line)==0:
      return 'NULL'
    elif len(line)==1:
      return [float(line[0]), math.sqrt(abs(float(line[0])))]
    return [float(line[0]), float(line[1]), math.sqrt(abs(float(line[1])))]

def read_simulation(file_name):
  '''
    Read a fit.f90 output file as MeasurementData object.
    
    @return MeasurementData with the fitted dataset
  '''
  sim_file=open(file_name, 'r')
  sim_lines=sim_file.readlines()
  sim_file.close()
  data=MeasurementData([['Q', 'Å^{-1}'], ['Intensity', 'counts/s'], ['error', 'counts']], [], 0, 1, 2)
  data.info='Simulation'
  for line in sim_lines:
    if len(line.split())>1:
      point=map(float, line.split())
      point.append(0.0)
      data.append(point)
  return data

def read_data_philips(file_name):
  '''
    Read the data of a philips X'Pert diffractometer file, exported as text files.
  '''
  file_handler=open(file_name, 'r')
  file_string=file_handler.read()
  # decode file text and change german numbers to point notation
  input_file_lines=codecs.decode(file_string, "ISO 8859-15", 'ignore').replace(',', '.').splitlines()
  file_handler.close()
  input_file_lines=map(unicode.strip, input_file_lines)
  input_file_lines=filter(lambda line: line!="", input_file_lines)
  header_info, data_lines, header_lines=read_philips_header(input_file_lines)
  # convert data
  data_lines=map(lambda line: line.split('\t'), data_lines)
  data_array=array(data_lines, dtype=float32)
  dataset=MeasurementData()
  angles=[]
  I=[]
  for i, col_i in enumerate(header_info['I-columns']):
    angles.append(data_array[:, 0]+float(col_i.strip('°')))
    I.append(data_array[:, i+1])
  angles=array(angles).flatten()
  I=array(I).flatten()
  sorting=argsort(angles)
  angles=angles[sorting]
  I=I[sorting]
  if header_info['Scan axis'].strip()=='Omega-2Theta':
    col=measurement_data_structure.PhysicalProperty('Θ', '°', angles)
  else:
    col=measurement_data_structure.PhysicalProperty(header_info['Scan axis'].strip(), '°', angles)
  dataset.data.append(col)
  count_time=float(header_info['Time per step (s)'])
  col=measurement_data_structure.PhysicalProperty('I', 'counts/s', I/count_time,
                                                  sqrt(I)/count_time)
  dataset.data.append(col)
  dataset.sample_name=header_info['Diffraction measurement']
  dataset.info="\n".join(header_lines)
  return [dataset]

def read_philips_header(input_file_lines):
  header_info={}
  for i, line in enumerate(input_file_lines):
    if line.startswith('Angle\t'):
      header_info['I-columns']=line.split('\t')[1:]
      return header_info, input_file_lines[i+1:], input_file_lines[:i]
    if ':' in line:
      key, value=line.split(':', 1)
      header_info[key.strip()]=value.strip()
  return header_info, [], []

def read_data_xrdml(input_file):
    PhysicalProperty=measurement_data_structure.PhysicalProperty
    from xml.dom.minidom import parse
    xml_data=parse(input_file).firstChild

    # retrieve data
    try:
      sample_name=xml_data.getElementsByTagName('sample')[0].getElementsByTagName('name')[0].firstChild.nodeValue
    except AttributeError:
      sample_name=os.path.split(input_file)[1].rsplit('.', 1)[0]
    scan=xml_data.getElementsByTagName('xrdMeasurement')[0].getElementsByTagName('scan')[0].getElementsByTagName('dataPoints')[0]
    header=xml_data.getElementsByTagName('xrdMeasurement')[0].getElementsByTagName('scan')[0].getElementsByTagName('header')[0]
    start_time=header.getElementsByTagName('startTimeStamp')[0].firstChild.nodeValue
    try:
      user=header.getElementsByTagName('author')[0].getElementsByTagName('name')[0].firstChild.nodeValue
    except AttributeError:
      user=''


    fixed_positions={}
    moving_positions={}
    for motor in scan.getElementsByTagName('positions'):
      axis=motor.attributes['axis'].value
      if axis=='2Theta':
        axis='2Θ'
      if axis=='Omega':
        axis='Θ'
      unit=motor.attributes['unit'].value
      if unit=='deg':
        unit='°'
      if len(motor.getElementsByTagName('commonPosition'))==0:
        start=float(motor.getElementsByTagName('startPosition')[0].firstChild.nodeValue)
        end=float(motor.getElementsByTagName('endPosition')[0].firstChild.nodeValue)
        moving_positions[axis]=(unit, start, end)
      else:
        pos=float(motor.getElementsByTagName('commonPosition')[0].firstChild.nodeValue)
        fixed_positions[axis]=(unit, pos)

    atten_factors=scan.getElementsByTagName('beamAttenuationFactors')[0].firstChild.nodeValue
    time=float(scan.getElementsByTagName('commonCountingTime')[0].firstChild.nodeValue)
    data=scan.getElementsByTagName('intensities')[0].firstChild.nodeValue
    atten_factors=map(float, atten_factors.split())
    data=map(float, data.split())
    I=array(data)
    atten=array(atten_factors)
    dI=sqrt(I*atten)
    I/=time
    dI/=time
    cols=[PhysicalProperty('Intensity', 'counts/s', I, dI)]
    if 'Θ' in moving_positions:
      angles=linspace(moving_positions['Θ'][1], moving_positions['Θ'][2], len(data))
      cols.append(PhysicalProperty('Θ', moving_positions['Θ'][0], angles))
      del(moving_positions['Θ'])
    for key, value in sorted(moving_positions.items()):
      angles=linspace(value[1], value[2], len(data))
      cols.append(PhysicalProperty(key, value[0], angles))
    dataset=measurement_data_structure.MeasurementData(x=1, y=0)
    dataset.data=cols
    dataset.number='0'
    dataset.sample_name=sample_name
    dataset.info='User: %s\nStart Time: %s\n\nMotor Positions:\n'%(user, start_time)
    for key, value in sorted(moving_positions.items()):
      dataset.info+='% 10s = %g-%g %s\n'%(key, value[1], value[2], value[0])
    for key, value in sorted(fixed_positions.items()):
      dataset.info+='% 10s = %g %s\n'%(key, value[1], value[0])

    return [dataset]

def read_bruker_raw(input_file):
  '''
    Read a raw dataset from Bruker D8
  '''
  data=open(input_file, 'rb').read()
  if data[:7]!='RAW1.01':
    print "Wrong file format"
    return "NULL"
  header_info=read_bruker_header(data[:712])
  scans=read_bruker_data(data[712:], header_info['SCANS'])
  output=[]
  for i, scan in enumerate(scans):
    dataset=MeasurementData()
    if scan[0]['SCAN_ANGLE']=='2THETA':
      dataset.data.append(PhysicalProperty('2Θ', '°', scan[1]))
      dataset.data.append(PhysicalProperty('I', 'counts', scan[2], sqrt(scan[2])))
      dataset.data.append((4.*pi/1.54*sin(dataset.data[0]/2.))//('Q_z', 'Å^{-1}'))
    else:
      dataset.data.append(PhysicalProperty('Θ', '°', scan[1]))
      dataset.data.append(PhysicalProperty('I', 'counts', scan[2], sqrt(scan[2])))
      dataset.data.append((4.*pi/1.54*sin(dataset.data[0]))//('Q_z', 'Å^{-1}'))
    dataset.data[1]/=PhysicalProperty('', 's', [scan[0]['TIME_PER_STEP']])

    dataset.sample_name=header_info['SAMPLE_ID']
    if len(scans)!=1:
      dataset.short_info='#%i'%(i+1)
    dataset.info=''
    for key, value in sorted(header_info.items()+scan[0].items()):
      dataset.info+='%20s: %s\n'%(key, value)
    output.append(dataset)
  return output

def read_bruker_header(data):
  head_info={}
  file_status=uint32_(data[8:12])
  if file_status==1:
    head_info["file status"]="done"
  elif (file_status==2):
    head_info["file status"]="active"
  elif (file_status==3):
    head_info["file status"]="aborted"
  elif (file_status==4):
    head_info["file status"]="interrupted"
  head_info['SCANS']=uint32_(data[12:16])
  head_info["MEASURE_DATE"]=data[16:26].replace('\x00', '')
  head_info["MEASURE_TIME"]=data[26:36].replace('\x00', '')
  #head_info["USER"]=data[36:108].replace('\x00', '')
  #head_info["SITE"]=data[108:326].replace('\x00', '')
  head_info["SAMPLE_ID"]=data[326:386].replace('\x00', '')
  head_info["COMMENT"]=data[386:446].replace('\x00', '')
  head_info["ANODE_MATERIAL"]=data[608:612].replace('\x00', '')
  head_info["ALPHA_AVERAGE"]=double_(data[616:624])
  head_info["ALPHA1"]=double_(data[624:632])
  head_info["ALPHA2"]=double_(data[632:640])
  head_info["BETA"]=double_(data[640:648])
  head_info["ALPHA_RATIO"]=double_(data[648:656])
  head_info["measurement time"]=float_(data[664:668])

  head_info["detector code"]=uint32_(data[96:100])
  return head_info

def read_bruker_data(data, scans):
  i=0
  scan_data=[]
  for j in range(scans):
    range_info=read_bruker_range_header(data[i:])
    start=i+304+range_info['supplementary_headers_size']
    i=start+4*range_info['STEPS']
    I=py_array('f')
    I.fromstring(data[start:i])
    I=array(I)
    x=linspace(range_info['START_%s'%range_info['SCAN_ANGLE']],
         range_info['START_%s'%range_info['SCAN_ANGLE']]+\
           range_info['STEP_SIZE']*range_info['STEPS'],
         range_info['STEPS'])
    scan_data.append([range_info, x, I])
  return scan_data

def read_bruker_range_header(data):
  range_info={}
  #head_length=uint32_(data[:4])
  range_info['STEPS']=uint32_(data[4:8])
  range_info['START_THETA']=double_(data[8:16])
  range_info['START_2THETA']=double_(data[16:24])
  range_info['START_CHI']=double_(data[24:32])
  range_info['START_PHI']=double_(data[32:40])
  range_info['START_Z']=double_(data[56:64])
  range_info['STEP_SIZE']=double_(data[176:184])

  range_info['STEP_MODE']=uint32_(data[196:200])

  range_info['TIME_PER_STEP']=float_(data[192:196])
  range_info['supplementary_headers_size']=uint32_(data[256:260])
  if range_info['STEP_MODE'] in [0, 1]:
    range_info['SCAN_ANGLE']='2THETA'
  else:
    range_info['SCAN_ANGLE']='THETA'
  return range_info

def double_(string):
  '''
    Return a double float from a binary string.
  '''
  a=py_array('d')
  a.fromstring(string)
  return a.pop()

def float_(string):
  '''
    Return a double float from a binary string.
  '''
  a=py_array('f')
  a.fromstring(string)
  return a.pop()

def uint32_(string):
  '''
    Return a double float from a binary string.
  '''
  a=py_array('I')
  a.fromstring(string)
  return int(a.pop())

class MeasurementData(measurement_data_structure.MeasurementData):
  '''
    Class implementing additions for Reflectometer data objects.
  '''
  def __add__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)+array(other.data[1].values)).tolist()
    out.data[2].values=(sqrt(array(self.data[2].values)**2+array(other.data[2].values)**2)).tolist()
    return out

  def __sub__(self, other):
    '''
      Subtract two measurements from another.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'-'+other.short_info
    out.data[1].values=(array(self.data[1].values)-array(other.data[1].values)).tolist()
    out.data[2].values=(sqrt(array(self.data[2].values)**2+array(other.data[2].values)**2)).tolist()
    return out

  def __rmul__(self, other):
    '''
      Multiply measurement with a scalar.
    '''
    out=deepcopy(self)
    out.data[1].values=(other*array(self.data[1].values)).tolist()
    out.data[2].values=(other*array(self.data[2].values)).tolist()
    return out

  def __mul__(self, other):
    '''
      Multiply two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)*array(other.data[1].values)).tolist()
    out.data[2].values=(sqrt(array(self.data[2].values)**2*array(other.data[1].values)**2+\
                             array(other.data[2].values)**2*array(self.data[1].values)**2)).tolist()
    return out

  def __div__(self, other):
    '''
      Divide two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(1./other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.data[1].values=(array(self.data[1].values)/array(other.data[1].values)).tolist()
    out.data[2].values=(sqrt(array(self.data[2].values)**2/array(other.data[1].values)**2+\
                             array(other.data[2].values)**2*array(self.data[1].values)**2\
                             /array(other.data[1].values)**4)).tolist()
    return out

