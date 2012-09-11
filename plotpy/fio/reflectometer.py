# -*- encoding: utf-8 -*-
'''
  Functions to read from reflectometer UXD data file. Mostly just string processing.
  MeasurementData Object from 'mds' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.
import numpy
from baseread import TextReader, BinReader
from plotpy.mds import MeasurementData, PhysicalProperty
from plotpy.config.reflectometer import DATA_COLUMNS

class D8Text(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"D8"
  description=u"Files recored with the Bruker D8 reflectometer"
  glob_patterns=[u'*.uxd']
  session='xrr'
  encoding="ISO 8859-15"

  def read(self):
    '''
      Read the datafile.
      
      :param input_file: Name of the file to import
      :param DATA_COLUMNS: List of columns to be imported
      
      :return: List of MeasurementData objects with the file data
    '''
    input_file_lines=self.text_data.splitlines()
    output=[]
    while len(input_file_lines)>0:
      measurement_info=self.read_header(input_file_lines)
      if measurement_info is None:
        self.error('No valid header found')
        return None
      sequence=self.read_data_lines(input_file_lines, measurement_info, DATA_COLUMNS)
      if sequence is not None:
        # filter 0 intensity points
        sequence.filters=[(1, 0.0, 0.0, False)]
        # for Θ or 2Θ scans add q-column
        if u"DRIVE='THETA'" in sequence.info:
          two_theta_start=float(sequence.info.split(u'2THETA=')[1].split(u"\n")[0])
          # omega/2-theta scan
          th=(sequence.x-sequence.x[0])+two_theta_start*0.5
          sequence.data.append((4.*numpy.pi/1.54*numpy.sin(th))//(u'Q_z', u'Å^{-1}'))
          # rocking scan
          ai=sequence.x
          af=two_theta_start-ai
          sequence.data.append((2.*numpy.pi/1.54*(numpy.cos(af)-numpy.cos(ai)))//
                               (u'Q_x', u'Å^{-1}'))
        elif u"DRIVE='2THETA'" in sequence.info or u"DRIVE='COUPLED'" in sequence.info:
          th=sequence.x*0.5
          sequence.data.append((4.*numpy.pi/1.54*numpy.sin(th))//(u'Q_z', u'Å^{-1}'))
        output.append(sequence)
      else:
        return None
    return output

  def read_header(self, input_file_lines):
    '''
      Read header of datafile.
      
      :param input_file_lines: List of lines from the input file
      
      :return: Header information 
    '''
    output=''
    for ignore in input_file_lines:
      line=input_file_lines.pop(0)
      if (u'COUNTS' in line):
        scantype=line[1:-1].rstrip('\r\n')
        # remove comment lines
        while u";" in input_file_lines[0]:
          line=input_file_lines.pop(0)
        return [output, scantype]
      elif u'CPS' in line:
        scantype=line[1:].rstrip(u'\r\n')
        return [output, scantype]
      else:
        output=output+line.rstrip(u'\n').rstrip(u'\r').lstrip(u'_').lstrip(u';')+u'\n'
    return None

  def read_data_lines(self, input_file_lines, info, DATA_COLUMNS):
    '''
      Read data points line by line.
      
      :return: One MeasurementData object for a scan sequence
    '''
    global sample_name
    if info[1].endswith(u'CPS'):
      cps=True
    else:
      cps=False
    data_info=u''
    scantype=None
    _count_time=1.
    for line in info[0].splitlines():
      setting=line.split(u'=')
      if setting[0]==u'SAMPLE':
        sample_name=setting[1].rstrip(u'\n').strip(u"'")
      elif setting[0].strip()==u'DRIVE':
        scantype=setting[1].strip(u"'").strip()
      elif setting[0].strip()==u'STEPTIME':
        _count_time=float(setting[1])
      # Definitions for locked-coupled scans
      elif setting[0].strip()==u'START':
        i=0
        start_angle=float(setting[1])
      elif setting[0].strip()==u'STEPSIZE':
        increment_angle=float(setting[1])
      data_info=data_info+line+u'\n'
    if scantype==None:
      self.error("Wrong file type, no 'DRIVE' defined in header!")
      return None
    data=MeasurementData([DATA_COLUMNS[scantype], DATA_COLUMNS[u'COUNTS']],
                         [], 0, 1,-1)
    data.info=data_info
    data.sample_name=sample_name
    raw_data=[]
    while len(input_file_lines)>0: # append data from one sequence to the object or create new object for the next sequence
      line=input_file_lines.pop(0)
      next_data=self.read_data_line(line, cps, _count_time)
      if next_data is not None and len(next_data)==2:
        raw_data.append((start_angle+i*increment_angle, next_data[0], next_data[1]))
        i+=1
      elif next_data is not None:
        raw_data.append(next_data)
      else:
        break
    x, y, ddy=numpy.array(raw_data).transpose()
    x=PhysicalProperty(DATA_COLUMNS[scantype][0],
                        DATA_COLUMNS[scantype][1],
                        x)
    y=PhysicalProperty(DATA_COLUMNS[u'COUNTS'][0],
                      DATA_COLUMNS[u'COUNTS'][1],
                      y, numpy.sqrt(numpy.abs(ddy)))
    data.data=[x, y]
    return data

  def read_data_line(self, input_file_line, cps, ctime):
    '''
      Read one line and output data as list of floats.
    '''
    if input_file_line[0]==u';':
      return None
    else:
      line=input_file_line.strip().split()
      if len(line)==0:
        return None
      elif len(line)==1:
        if cps:
          return [float(line[0])*ctime, float(line[0])*ctime]
        else:
          return [float(line[0]), float(line[0])]
      if cps:
        return [float(line[0]), float(line[1])*ctime, float(line[1])*ctime]
      else:
        return [float(line[0]), float(line[1]), float(line[1])]


class D8Bin(BinReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"D8raw"
  description=u"Files recored with the Bruker D8 reflectometer"
  glob_patterns=[u'*.raw']
  session='xrr'
  priority=6 # increase priority as the type check is very fast 

  def read(self):
    '''
      Read a raw dataset from Bruker D8
    '''
    data=self.raw_data
    pi, sin, cos, sqrt=(numpy.pi, numpy.sin, numpy.cos, numpy.sqrt)
    if data[:7]!='RAW1.01':
      self.error("Wrong file format")
      return None
    header_info=self.read_header(data[:712])
    scans=self.read_data(data[712:], header_info['SCANS'])
    output=[]
    for i, scan in enumerate(scans):
      dataset=MeasurementData()
      if scan[0]['SCAN_ANGLE']=='2THETA':
        dataset.data.append(PhysicalProperty('2Θ', '°', scan[1]))
        dataset.data.append(PhysicalProperty('I', 'counts', scan[2], sqrt(scan[2])))
        dataset.data.append((4.*pi/1.54*sin(dataset.data[0]/2.))//('Q_z', u'Å^{-1}'))
      else:
        dataset.data.append(PhysicalProperty('Θ', '°', scan[1]))
        dataset.data.append(PhysicalProperty('I', 'counts', scan[2], sqrt(scan[2])))
        # th2th
        dataset.data.append((4.*pi/1.54*sin(dataset.data[0]))//('Q_z', u'Å^{-1}'))
        # rocking
        tth=scan[0]['START_2THETA']
        ai=dataset.data[0]
        af=tth-ai
        dataset.data.append((2.*pi/1.54*(cos(af)-cos(ai)))//('Q_x', u'Å^{-1}'))
      dataset.data[1]/=PhysicalProperty('', 's', [scan[0]['TIME_PER_STEP']])

      dataset.sample_name=header_info['SAMPLE_ID']
      if len(scans)!=1:
        dataset.short_info='#%i'%(i+1)
      dataset.info=''
      for key, value in sorted(header_info.items()+scan[0].items()):
        dataset.info+='%20s: %s\n'%(key, value)
      output.append(dataset)
    return output

  def read_header(self, data):
    head_info={}
    file_status=self.uint32_(data[8:12])
    if file_status==1:
      head_info["file status"]="done"
    elif (file_status==2):
      head_info["file status"]="active"
    elif (file_status==3):
      head_info["file status"]="aborted"
    elif (file_status==4):
      head_info["file status"]="interrupted"
    head_info['SCANS']=self.uint32_(data[12:16])
    head_info["MEASURE_DATE"]=data[16:26].replace('\x00', '')
    head_info["MEASURE_TIME"]=data[26:36].replace('\x00', '')
    #head_info["USER"]=data[36:108].replace('\x00', '')
    #head_info["SITE"]=data[108:326].replace('\x00', '')
    head_info["SAMPLE_ID"]=data[326:386].replace('\x00', '')
    head_info["COMMENT"]=data[386:446].replace('\x00', '')
    head_info["ANODE_MATERIAL"]=data[608:612].replace('\x00', '')
    head_info["ALPHA_AVERAGE"]=self.double_(data[616:624])
    head_info["ALPHA1"]=self.double_(data[624:632])
    head_info["ALPHA2"]=self.double_(data[632:640])
    head_info["BETA"]=self.double_(data[640:648])
    head_info["ALPHA_RATIO"]=self.double_(data[648:656])
    head_info["measurement time"]=self.float_(data[664:668])

    head_info["detector code"]=self.uint32_(data[96:100])
    return head_info

  def read_data(self, data, scans):
    i=0
    scan_data=[]
    for ignore in range(scans):
      range_info=self.read_range_header(data[i:])
      start=i+304+range_info['supplementary_headers_size']
      i=start+4*range_info['STEPS']
      I=numpy.fromstring(data[start:i], dtype=numpy.float32)
      x=numpy.linspace(range_info['START_%s'%range_info['SCAN_ANGLE']],
                      range_info['START_%s'%range_info['SCAN_ANGLE']]+\
                      range_info['STEP_SIZE']*range_info['STEPS'],
                      range_info['STEPS'])
      scan_data.append([range_info, x, I])
    return scan_data

  def read_range_header(self, data):
    range_info={}
    #head_length=uint32_(data[:4])
    range_info['STEPS']=self.uint32_(data[4:8])
    range_info['START_THETA']=self.double_(data[8:16])
    range_info['START_2THETA']=self.double_(data[16:24])
    range_info['START_CHI']=self.double_(data[24:32])
    range_info['START_PHI']=self.double_(data[32:40])
    range_info['START_Z']=self.double_(data[56:64])
    range_info['STEP_SIZE']=self.double_(data[176:184])

    range_info['STEP_MODE']=self.uint32_(data[196:200])

    range_info['TIME_PER_STEP']=self.float_(data[192:196])
    range_info['supplementary_headers_size']=self.uint32_(data[256:260])
    if range_info['STEP_MODE'] in [0, 1]:
      range_info['SCAN_ANGLE']='2THETA'
    else:
      range_info['SCAN_ANGLE']='THETA'
    return range_info

  def double_(self, string):
    '''
      Return a double float from a binary string.
    '''
    data=numpy.fromstring(string, numpy.float64)
    return data[0]

  def float_(self, string):
    '''
      Return a double float from a binary string.
    '''
    data=numpy.fromstring(string, numpy.float32)
    return data[0]

  def uint32_(self, string):
    '''
      Return a double float from a binary string.
    '''
    data=numpy.fromstring(string, numpy.uint32)
    return data[0]



#def read_simulation(file_name):
#  '''
#    Read a fit.f90 output file as MeasurementData object.
#    
#    :return: MeasurementData with the fitted dataset
#  '''
#  sim_file=open(file_name, 'r')
#  sim_lines=sim_file.readlines()
#  sim_file.close()
#  data=MeasurementData([['Q', 'Å^{-1}'], ['Intensity', 'counts/s'], ['error', 'counts']], [], 0, 1, 2)
#  data.info='Simulation'
#  for line in sim_lines:
#    if len(line.split())>1:
#      point=map(float, line.split())
#      point.append(0.0)
#      data.append(point)
#  return data
#
class PhilipsXpert(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"Philips XPert"
  description=u"Files recored with the Philips XPert reflectometer"
  glob_patterns=[u'*.']
  session='xrr'
  encoding="ISO 8859-15"

  def read(self):
    '''
      Read the data of a philips X'Pert diffractometer file, exported as text files.
    '''
    # change german numbers to point notation
    input_file_lines=self.text_data.replace(',', '.').splitlines()
    input_file_lines=map(unicode.strip, input_file_lines)
    input_file_lines=filter(lambda line: line!="", input_file_lines)
    header_info, data_lines, header_lines=self.read_header(input_file_lines)
    # convert data
    data_array=self.lines2data(data_lines, '\t').transpose()
    dataset=MeasurementData()
    angles=[]
    I=[]
    for i, col_i in enumerate(header_info['I-columns']):
      angles.append(data_array[:, 0]+float(col_i.strip('°')))
      I.append(data_array[:, i+1])
    angles=numpy.array(angles).flatten()
    I=numpy.array(I).flatten()
    sorting=numpy.argsort(angles)
    angles=angles[sorting]
    I=I[sorting]
    if header_info['Scan axis'].strip()=='Omega-2Theta':
      col=PhysicalProperty(u'Θ', u'°', angles)
    else:
      col=PhysicalProperty(header_info['Scan axis'].strip(), u'°', angles)
    dataset.data.append(col)
    count_time=float(header_info['Time per step (s)'])
    col=PhysicalProperty('I', 'counts/s', I/count_time,
                         numpy.sqrt(I)/count_time)
    dataset.data.append(col)
    dataset.sample_name=header_info['Diffraction measurement']
    dataset.info=u"\n".join(header_lines)
    return [dataset]

  def read_header(self, input_file_lines):
    header_info={}
    for i, line in enumerate(input_file_lines):
      if line.startswith('Angle\t'):
        header_info['I-columns']=line.split('\t')[1:]
        return header_info, input_file_lines[i+1:], input_file_lines[:i]
      if u':' in line:
        key, value=line.split(u':', 1)
        header_info[key.strip()]=value.strip()
    return header_info, [], []

class XRDML(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"XRDML"
  description=u"XRDML files"
  glob_patterns=[u'*.xrdml']
  session='xrr'
  encoding="ISO 8859-15"

  def read(self):
    from xml.dom.minidom import parseString
    xml_data=parseString(self.text_data).firstChild

    # retrieve data
    try:
      sample_name=xml_data.getElementsByTagName('sample')[0].getElementsByTagName('name')[0].firstChild.nodeValue
    except AttributeError:
      sample_name=self.origin[1].rsplit('.', 1)[0]
    scan=xml_data.getElementsByTagName('xrdMeasurement')[0].getElementsByTagName('scan')[0].getElementsByTagName('dataPoints')[0]
    header=xml_data.getElementsByTagName('xrdMeasurement')[0].getElementsByTagName('scan')[0].getElementsByTagName('header')[0]
    start_time=header.getElementsByTagName('startTimeStamp')[0].firstChild.nodeValue
    try:
      user=header.getElementsByTagName('author')[0].getElementsByTagName('name')[0].firstChild.nodeValue
    except AttributeError:
      user=u''


    fixed_positions={}
    moving_positions={}
    for motor in scan.getElementsByTagName('positions'):
      axis=motor.attributes['axis'].value
      if axis=='2Theta':
        axis=u'2Θ'
      if axis=='Omega':
        axis=u'Θ'
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
    I=numpy.array(data)
    atten=numpy.array(atten_factors)
    dI=numpy.sqrt(I*atten)
    I/=time
    dI/=time
    cols=[PhysicalProperty('Intensity', 'counts/s', I, dI)]
    if u'Θ' in moving_positions:
      angles=numpy.linspace(moving_positions[u'Θ'][1], moving_positions[u'Θ'][2], len(data))
      cols.append(PhysicalProperty(u'Θ', moving_positions[u'Θ'][0], angles))
      del(moving_positions[u'Θ'])
    for key, value in sorted(moving_positions.items()):
      angles=numpy.linspace(value[1], value[2], len(data))
      cols.append(PhysicalProperty(key, value[0], angles))
    dataset=MeasurementData(x=1, y=0)
    dataset.data=cols
    dataset.number='0'
    dataset.sample_name=sample_name
    dataset.info=u'User: %s\nStart Time: %s\n\nMotor Positions:\n'%(user, start_time)
    for key, value in sorted(moving_positions.items()):
      dataset.info+=u'% 10s = %g-%g %s\n'%(key, value[1], value[2], value[0])
    for key, value in sorted(fixed_positions.items()):
      dataset.info+=u'% 10s = %g %s\n'%(key, value[1], value[0])

    return [dataset]

