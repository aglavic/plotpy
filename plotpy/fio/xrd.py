# -*- encoding: utf-8 -*-
'''
'''

import numpy
from baseread import TextReader
from plotpy.mds import MeasurementData, PhysicalProperty, MeasurementData4D
from plotpy.config.xrd import KNOWN_COLUMNS, INTENSITY_COLUMNS, P09_COLUMNS_MAPPING, \
                               ID4_SCANS, ID4_MAPPING

class Spec(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"Spec"
  description=u"Files recored with the SPEC diffraction software"
  glob_patterns=[u'*.spec']
  session='xrd'

  def read(self):
    input_file_lines=self.text_data.splitlines()
    sample_name, last_comments=self.read_file_header(input_file_lines)
    if not sample_name:
      self.warn(u"Wrong file type, no spec header found (#F,#E,#D,#C)!")
      sample_name=u''
    measurement_data=self.read_data_lines(input_file_lines, sample_name, last_comments)
    if len(measurement_data)==0:
      self.error(u"No scan data found.")
      return None
    return measurement_data


  def read_file_header(self, input_file_lines):
    '''
      Read the header of the file.
      
      :param input_file_lines: List of lines to be evaluated
      
      :return: The sample name defined in the file or None if the wron filetype.
    '''
    if not (input_file_lines[0].startswith(u'#F') and
            input_file_lines[1].startswith(u'#E') and
            input_file_lines[2].startswith(u'#D')):
      return None, None
    try:
      line=input_file_lines[3]
      sample_name=line.split(u'User')[0].split(u' ', 1)[1]
      # remove characters from keyboard input
      if u'[D' in sample_name or u'\b' in sample_name:
        while u'[D' in sample_name:
          i=sample_name.index(u'[D')
          sample_name=sample_name[:i-1]+sample_name[i+3:]
        while u'\b' in sample_name:
          i=sample_name.index(u'\b')
          sample_name=sample_name[:i-1]+sample_name[i+1:]
      last_comments=u''
      for line in input_file_lines[4:]:
        if line.startswith(u'#C'):
          last_comments+=line
        elif line.startswith(u'#S'):
          return sample_name, last_comments
      return None, None
    except:
      return None, None

  def read_data_lines(self, input_file_lines, sample_name, last_comments):
    '''
      Read data points line by line.
      
      :param input_file_lines: List of lines from the input file
      :param sample_name: Sample Name from file header
      :param last_comments: comment lines from before the scan
      
      :return: MeasurementData objects
    '''
    scan_indices=[]
    for i, line in enumerate(input_file_lines):
      if line.startswith(u'#S'):
        scan_indices.append(i)
    output=[]
    for i, j in zip(scan_indices[:], scan_indices[1:]+[len(input_file_lines)]):
        self.info(None, progress=100*i/float(len(input_file_lines)))
        dataset, last_comments=self.read_scan(input_file_lines[i:j], last_comments)
        if dataset is not None:
          dataset.sample_name=sample_name
          output.append(dataset)
    return output

  def read_scan(self, scan_lines, last_comments):
    '''
      Read and evaluate the lines of one scan.
    '''
    scan_header, scan_data=self.get_scan_header(scan_lines)
    scan_header[u'last_comments']=last_comments
    if len(scan_data)<2:
      return None, None
    columns=[]
    for col in scan_header[u'columns']:
      if col in KNOWN_COLUMNS:
        columns.append(KNOWN_COLUMNS[col])
      else:
        columns.append((col, u''))
    xcol, ycol, errorcol, zcol=self.get_type_columns(scan_header[u'type'], [col[0] for col in columns])
    output=MeasurementData(x=xcol, y=ycol, zdata=zcol, yerror=errorcol)
    if scan_header[u'type'].split()[0]==u'mesh3d':
      output.scan_line_constant=0
      output.scan_line=1
      output.filters=[(9,-1.0, 0.5, False)]
      output=MeasurementData4D.from_md(output, y2=2)
    if scan_header[u'type'].split()[0]==u'circle_mesh':
      output.scan_line_constant=0
      output.scan_line=1
    data=self.lines2data(scan_data)
    for i, col in enumerate(columns):
      output.data.append(PhysicalProperty(col[0], col[1], data[i]))
      if col[1]==u'counts':
        output.data[-1].error=numpy.sqrt(data[i])
    output.short_info=u'#'+scan_header[u'index']+u' - '
    from string import Template
    output.info=Template(u'''    Scan: ${type}
      Index: ${index}            Date: ${date}
      
      Lattice Parameters: ${lp}
      Q at Start: ${q_start}
      Angles at Start: ${angles_start}
  
      Comments (before scan):
  ${last_comments}
      Comments (during scan):
  ${comments}
      ''').substitute(scan_header)
    if u'h' in output.dimensions():
      index=output.dimensions().index(u'h')
      output.data.append((output.data[index]*scan_header[u'rl'][0])//(u'Q_x', u'Å^{-1}'))
    if u'k' in output.dimensions():
      index=output.dimensions().index(u'k')
      output.data.append((output.data[index]*scan_header[u'rl'][1])//(u'Q_y', u'Å^{-1}'))
    if u'l' in output.dimensions():
      index=output.dimensions().index(u'l')
      output.data.append((output.data[index]*scan_header[u'rl'][2])//(u'Q_z', u'Å^{-1}'))
    if u'I_{det/atten}' in output.dimensions() and u'I' in output.dimensions():
      # calculate 4-circle monitor error
      index=output.dimensions().index(u'I_{det/atten}')
      count_idx=output.dimensions().index(u'I')
      atten_factor=output.data[index]/numpy.maximum(output.data[count_idx], 1.)
      atten_factor[atten_factor==0.]=1.
      output.data[index].error=atten_factor*output.data[count_idx].error
      max_factor=atten_factor[atten_factor.nonzero()].max()
      min_factor=atten_factor[atten_factor.nonzero()].min()
      if max_factor!=min_factor:
        if output.zdata<0:
          output.ydata=index
        else:
          output.zdata=index
    self.recheck_type(output, scan_header)
    return output, scan_header[u'comments']

  def get_type_columns(self, type_line, columns):
    '''
      Return the indices of columns to plot.
    '''
    type_, options=type_line.split(None, 1)
    intensity=len(columns)-1
    intensity_error=-1
    for col in INTENSITY_COLUMNS:
      if col in columns:
        intensity=columns.index(col)
        break
    if type_==u'hklscan':
      hklranges=map(float, options.strip().split())
      if abs(hklranges[1]-hklranges[0])>1e-5:
        return columns.index(u'h'), intensity, intensity_error,-1
      if abs(hklranges[3]-hklranges[2])>1e-5:
        return columns.index(u'k'), intensity, intensity_error,-1
      if abs(hklranges[5]-hklranges[4])>1e-5:
        return columns.index(u'l'), intensity, intensity_error,-1
    elif type_==u'hklmesh':
      items=options.strip().split()
      return columns.index(items[0].lower()), columns.index(items[4].lower()), intensity_error, intensity
    elif type_==u'mesh':
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
    elif type_==u'circle_mesh':
      items=options.strip().split()
      return (columns.index(items[0].lower()), columns.index(items[1].lower()),
              intensity_error, intensity)
    elif type_==u'mesh3d':
      items=options.strip().split()
      first_angle=u'Theta' #items[0]
      if first_angle in KNOWN_COLUMNS:
        first_angle=KNOWN_COLUMNS[first_angle][0]
      second_angle=u'Chi' #items[4]
      if second_angle in KNOWN_COLUMNS:
        second_angle=KNOWN_COLUMNS[second_angle][0]
      first_index=columns.index(first_angle)
      second_index=columns.index(second_angle)
      return first_index, second_index, intensity_error, intensity
    elif type_==u'timescan_cm' or type_==u'Escan' or type_==u'contmode':
      return columns.index(u'E'), intensity, intensity_error,-1
    elif type_==u'ascan' and options.split()[0]==u'lake':
      return columns.index(u'T_{sample}'), intensity, intensity_error,-1
    else:
      return 0, intensity, intensity_error,-1

  def recheck_type(self, dataset, scan_header):
    type_line=scan_header[u'type']
    type_, ignore=type_line.split(None, 1)
    if type_==u'timescan':
      if u'T_{sample}' in dataset.dimensions():
        t_index=dataset.dimensions().index(u'T_{sample}')
        T=dataset.data[t_index]
        # if the temperature of start and end value is differs by more the 5 times the temperature fluctuation
        # set T as x
        if abs(T[-1]-T[0])>(numpy.abs(T[:-1]-T[1:]).var()**2)*5:
          dataset.xdata=t_index

  def get_scan_header(self, scan_lines):
    '''
      Read header of scan and return the data lines and some information of the header.
      
      :param scan_lines: lines corresponding to one scan
      
      :return: dictionary with header informations and lines containing data
    '''
    scan_header={}
    for i, line in enumerate(scan_lines):
      if (line[0:2]==u'#L'):
        scan_header[u'columns']=line[3:].split(u'  ')
        break
      elif (line[0:2]==u'#S'):
        scan_header[u'index'], scan_header[u'type']=line[3:].strip().split(u'  ', 1)
      elif line[0:3] in [u'#N ', u'#G0', u'#G2', u'#G3', u'#G4']:
          continue
      elif line[0:2]==u'#D':
        scan_header[u'date']=line[3:].strip()
      elif line[0:2]==u'#T':
        scan_header[u'time']=line[3:].strip().split()[0]
      elif line[0:2]==u'#Q':
        scan_header[u'q_start']=line[3:].strip()
      elif line[0:3]==u'#P0':
        scan_header[u'angles_start']=line[3:].strip()
      elif line[0:3]==u'#G1':
        lp=line[3:].strip().split()
        scan_header[u'lp']=u"a=%s b=%s c=%s α=%s β=%s γ=%s"%(lp[0], lp[1], lp[2],
                                                             lp[3], lp[4], lp[5])
        scan_header[u'rl']=map(float, (lp[6], lp[7], lp[8], lp[9], lp[10], lp[11]))
      elif line[0:2]==u'#D':
        scan_header[u'date']=line[3:].strip()
    data_lines=scan_lines[i+1:]
    comment_lines=filter(lambda line: line.startswith(u'#'), data_lines)
    data_lines=filter(lambda line: not (line.startswith(u'#') or line.strip()==u''), data_lines)
    scan_header[u'comments']=u'\n'.join(comment_lines)
    return scan_header, data_lines

class Online(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"Online (DESY)"
  description=u"File format used at diffraction beamlines of PETRA 3 and DORIS"
  glob_patterns=[u'*.fio']
  session='xrd'

  def read(self):
    '''
      Read data aquired at P09 beamlime of PETRA III.
    '''
    text=self.text_data
    if not ((u'! Parameter' in text) and (u'! Data' in text)):
      self.error(u"No valid P09 header found.")
      return None
    name=text.split(u'Name: ', 1)[1].split(u' ', 1)[0].strip()
    scan_type=text.split(u'%c')[1].strip().split()[0]
    parameter_region=text.split(u'%p')[1].split(u'%d')[0].strip().splitlines()
    data_region=text.split(u'%d')[1].strip().splitlines()
    parameter_region=filter(lambda item: not item.startswith(u'!'), parameter_region)
    data_region=filter(lambda item: not item.startswith(u'!'), data_region)
    data_region=map(unicode.strip, data_region)
    parameter_region=map(lambda line: line.strip().split(u'=', 1), parameter_region)
    parameters={}
    for param, value in parameter_region:
      parameters[param]=value
    columns=[]
    for i, line in enumerate(data_region):
      if line.strip().startswith(u'Col'):
        try:
          columns.append(line.split(name.upper()+u'_')[1].split()[0])
        except IndexError:
          columns.append(scan_type)
      else:
        data_region=data_region[i:]
        break
    for i, col in enumerate(columns):
      if col in P09_COLUMNS_MAPPING:
        columns[i]=P09_COLUMNS_MAPPING[col]
      else:
        columns[i]=(col, u'°')
    columns[0]=columns[1]
    columns[1]=[u'None', u'']
    data_region=map(unicode.strip, data_region)
    data=self.lines2data(data_region)
    output=MeasurementData(x=0, y=2)
    for i, column in enumerate(columns):
      if column[1]==u'counts':
        output.append_column(PhysicalProperty(column[0], column[1], data[i], numpy.sqrt(data[i])))
      else:
        output.append_column(PhysicalProperty(column[0], column[1], data[i]))
    I=PhysicalProperty(u'I', u'counts', data[columns.index((u'I_{RAW}', u'counts'))],
                          numpy.sqrt(data[columns.index((u'I_{RAW}', u'counts'))]))
    I*=data[columns.index((u'Attenuation', u''))]
    output.append_column(I)
    output.ydata=len(output.data)-1
    output.info=u"\n".join([param[0]+u": "+param[1] for param in parameters.items()])
    output.sample_name=name.split(u'_')[-1]
    if output.x.dimension==u'hkl-Scan':
      output.x.dimension=u'-Scan'
      output.x.unit=u''
      hidx=output.dimensions().index(u'H')
      kidx=output.dimensions().index(u'K')
      lidx=output.dimensions().index(u'L')
      if (output.data[lidx].max()-output.data[lidx].min())>0.02:
        output.x.dimension=u'L'+output.x.dimension
      if (output.data[kidx].max()-output.data[kidx].min())>0.02:
        output.x.dimension=u'K'+output.x.dimension
      if (output.data[hidx].max()-output.data[hidx].min())>0.02:
        output.x.dimension=u'H'+output.x.dimension
    return [output]

class APS4ID(TextReader):
  '''
    Read ascii scan files created by spec (fourc).
  '''
  name=u"4ID"
  description=u"Data taken at the 4ID beamline of APS"
  glob_patterns=[u'*.[0-9][0-9][0-9][0-9]']
  session='xrd'

  def read(self):
    '''
      Read data from 4-ID-C station at APS.
    '''
    text=self.text_data
    if not text.startswith(u'## mda2ascii'):
      self.error(u"No valid 4-ID ascii header found.")
      return None
    header, data_with_head=text.split(u'# Column Descriptions:', 1)
    header_info=self.extract_headerinfo(header)
    type_, file_columns, data=self.extract_columns_and_data(data_with_head)
    if len(data)==0:
      self.error(u"No data in the file.")
      return None
    output=MeasurementData(x=0, y=1)
    used_columns=[0]
    for i, column, unit in ID4_SCANS[type_]:
      if column is None:
        column, unit=file_columns[i]
        if column in ID4_MAPPING:
          column=ID4_MAPPING[column]
      if unit==u'counts':
        output.append_column(PhysicalProperty(column, unit, data[i], numpy.sqrt(data[i])))
      else:
        output.append_column(PhysicalProperty(column, unit, data[i]))
      used_columns.append(i)
    for i in range(len(file_columns)):
      if i not in used_columns:
        column, unit=file_columns[i]
        column=u"% 2i: "%i+column
        if column in ID4_MAPPING:
          column=ID4_MAPPING[column]
        if unit==u'counts':
          output.append_column(PhysicalProperty(column, unit, data[i], numpy.sqrt(data[i])))
        else:
          output.append_column(PhysicalProperty(column, unit, data[i]))
    output.info=u"Started at: %s"%header_info[u'starting time']
    output.info+=u'\n'+u"\n".join(map(lambda item: u"%s: \t%s"%(item[0], item[1]), header_info[u'status info']))
    output.short_info=u"#%04i"%header_info[u'scan number']
    output.sample_name=u''
    return [output]

  def extract_headerinfo(self, header):
    '''
      Extract some infor from the file header.
    '''
    info={u'status info': []}
    for line in header.splitlines():
      if line.startswith(u'# Scan number'):
        info[u'scan number']=int(line.split(u'=')[1])
      elif line.startswith(u'# Scan time'):
        info[u'starting time']=line.split(u'=')[1].strip()
      elif u'scaler time preset' in line:
        info[u'time']=float(line.split(u',')[2].strip(u' "'))
      elif u'SGM Energy' in line:
        info[u'status info'].append((u'Energy (eV)', line.split(u',')[2].strip(u' "')))
      elif u'7T Z pos' in line:
        info[u'status info'].append((u'Z', line.split(u',')[2].strip(u' "')))
      elif u'7T rotation' in line:
        info[u'status info'].append((u'φ', line.split(u',')[2].strip(u' "')))
      elif u'7T T sample' in line:
        temperature=float(line.split(u',')[2].strip(u' "'))
        info[u'status info'].append((u'T', u"%.1f"%temperature))
      elif u'7T field' in line:
        field=float(line.split(u',')[2].strip(u' "'))*0.1
        info[u'status info'].append((u'H (T)', u"%.3g"%field))

    return info

  def extract_columns_and_data(self, data_with_head):
    '''
      Extract the data and columns of the file.
    '''
    type_=u'other'
    lines=data_with_head.splitlines()
    columns=[]
    data_lines=[]
    for i, line in enumerate(lines):
      if not (line.startswith(u'#') or line.strip()==u''):
        data_lines=lines[i:]
        break
      if u'Index' in line:
        columns.append((u'Point', u''))
      if u'Positioner' in line:
        items=line.split(u',')
        columns.append((
                        items[1].strip(),
                        items[3].strip()
                        ))
      if u'Detector' in line:
        items=line.split(u',')
        columns.append((
                        items[1].strip(),
                        items[2].strip()
                        ))
    if u'M3C DS Y' in data_with_head:
      type_=u'mirror-align'
    elif u'XMCD_2_Diff' in data_with_head:
      type_=u'XMCD'
    elif u'Positioner 2' in data_with_head:
      type_=u'e-scan'
    data_lines=map(unicode.strip, data_lines)
    data=self.lines2data(data_lines)
    return type_, columns, data
