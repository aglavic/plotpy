# -*- encoding: utf-8 -*-
'''
  Functions to read from treff data and .img. files.
  MeasurementData Object from 'mds' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
  Image files can be gziped or plain.
'''

import os
import gzip
import numpy
from baseread import TextReader, BinReader
from plotpy.mds import HugeMD, PhysicalProperty, PhysicalConstant, MeasurementData
from plotpy.config.treff import DETECTOR_CALIBRATION as TREFF_CALIBRATION

MARIA_REDUCE_RESOLUTION=False
GRAD_TO_MRAD=numpy.pi/180.*1000.
GRAD_TO_RAD=numpy.pi/180.

class TreffMariaReader(TextReader):
  name=u"TREFF/MARIA"
  description=u"Polarized neutron reflectivity measured with TREFF or MARIA at FRM-II"
  glob_patterns=[u'*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]']
  session='pnr'

  store_mds=False
  allow_multiread=True

  def set_treff(self):
    # define parameters for TREFF readout
    self.detector_pixels=256
    #self.detector_region=(0, 256, 0, 256) # usable area of detector
    self.center_x=130.8 # pix
    self.center_y=128.5 # pix
    #DETECTOR_ROWS_MAP=[[j+i*DETECTOR_PIXELS for i in range(DETECTOR_PIXELS)]
    #                   for j in range(DETECTOR_PIXELS)]
    self.pixelsize=-0.014645 # mrad
    self.lambda_n=PhysicalConstant(4.75, 'Å', symbol=u'λ_n',
                                   discription=u'TREFF neutron wavelength')
    self.k_n=PhysicalConstant(2.*numpy.pi/4.75, 'Å^{-1}', symbol=u'k_n',
                                   discription=u'TREFF neutron wavevector')
    self.is_maria=False
    self.units={
                u'I_{window}': 'counts',
                u'I_{monitor}': 'counts',
                u'I_{total}': 'counts',
                u'Time': 's',
                u'2Θ': u'°',
                u'ω': u'°',
                }
    # import calibration from file, need to get this as relative path
    calibration=numpy.array(TREFF_CALIBRATION, dtype=numpy.float32)
    calibration*=calibration[calibration!=0.].mean() # normalize to about 1
    calibration[calibration==0.]=1.
    self.calibration=calibration

  def set_maria(self):
    # define parameters for MARIA readout
    self.detector_pixels=1024.
    self.calibration=1.
    self.center_y=512.
    self.center_x=512.
    self.pixelsize=0.01
    self.is_maria=True
    self.constants={}
    self.lambda_n=None
    self.k_n=None
    self.units={
                u'I_{window}': 'counts',
                 'I_2': 'counts',
                 'I_3': 'counts',
                 'I_4': 'counts',
                 'I_5': 'counts',
                 'I_6': 'counts',
                 'I_7': 'counts',
                 'I_8': 'counts',
                 'I_9': 'counts',
                 'I_{total}': 'counts',
                 'I_{monitor}': 'counts',
                u'Time': 's',
                u'2Θ': u'°',
                u'ω': u'°',
                u'λ_n': u'Å',
                }

  polarization_mapping={
                        'xx': '',
                        'uu': '(++)',
                        'dd': '(--)',
                        'ud': '(+-)',
                        'du': '(-+)',
                        }

  def read(self):
    if not self.check_head():
      self.warn('No valid TREFF or MARIA format')
      return None
    self.info('Evaluate Header')
    self.find_head_tail()
    self.eval_header()
    self.data={}
    self.info('Reading Text', 10)
    if not self.read_textfile():
      self.warn('No valid data found')
      return None
    if self.image_col is not None:
      self.info('Reading Images', 20)
      self.read_images()
    return self.collect_objects()

  def check_head(self):
    if self.text_data.split('\n', 2)[1][:13]==u'#Scan started':
      self.set_maria()
      return True
    if self.text_data[:6]==u'/home/':
      self.set_treff()
      return True
    return False

  def find_head_tail(self):
    # find the first and last dataline
    self.lines_data=self.text_data.splitlines()
    for i, line in enumerate(self.lines_data):
      try:
        float(line.split()[0])
        break
      except (ValueError, IndexError):
        continue
    self.head_sep=i
    for i, line in enumerate(reversed(self.lines_data)):
      try:
        float(line.split()[0])
        break
      except (ValueError, IndexError):
        continue
    self.foot_sep=len(self.lines_data)-i

  def eval_header(self):
    if self.is_maria:
      return self.eval_head_maria()
    return self.eval_head_treff()

  def eval_head_treff(self):
    self.negative_omega=False
    header=self.lines_data[:self.head_sep]
    foot=self.lines_data[self.foot_sep:]
    mapping={
             'Position': 'Step',
             '2DWind.': 'I_{window}',
             '2DTotal': 'I_{total}',
             'Monitor': 'I_{monitor}',
             'omega': u'ω',
             'detector': u'2Θ',
            }
    columns_line=header[2].replace(u'MF [G]', 'H')
    columns=columns_line.split()
    # get the columns of interest
    try:
      self.image_col=columns.index('Image')
    except ValueError:
      self.image_col=None
    self.polarization_col=[columns.index('Pol.')]
    for item, newname in mapping.items():
      if item in columns:
        iindex=columns.index(item)
        columns.pop(iindex)
        columns.insert(iindex, newname)
    # if file was stopped there is no footer, so make sure these values are defined
    constants=[(u'ω', 0.), (u'2Θ', 0.)]
    for line in header+foot:
      line=line.split()
      if len(line)==0:
        continue
      if line[0]=='Scan':
        self.scantype=line[-1]
        old_column=columns.pop(0)
        if line[-1]=='omega':
          columns.insert(0, u'ω')
        elif line[-1]=='detector' or line[-1]=='scatteringarm':
          columns.insert(0, u'2Θ')
        elif line[-1]=='sampletable':
          columns.insert(0, u'ω')
          self.negative_omega=True
        else:
          columns.insert(0, old_column)
      elif line[0]=='2nd':
        columns.pop(1)
        if line[-1]=='omega':
          columns.insert(1, u'ω')
        elif line[-1]=='detector':
          columns.insert(1, u'2Θ')
        elif line[-1]=='sampletable':
          columns.insert(1, u'ω')
          self.negative_omega=True
      else:
        try:
          constants.append((line[0], float(line[1])))
        except (ValueError, IndexError):
          continue
    self.columns=columns
    self.constants=[]
    for constant in constants:
      if constant[0] in mapping:
        self.constants.append((mapping[constant[0]], constant[1]))
      else:
        self.constants.append(constant)
    self.constants=dict(self.constants)
    self.x_col=0

  def eval_head_maria(self):
    self.polarization_col=None
    header=self.lines_data[:self.head_sep]
    columns=header[-1].strip('# ').split()
    mapping={
             'ROI1': 'I_{window}',
             'ROI2': 'I_2',
             'ROI3': 'I_3',
             'ROI4': 'I_4',
             'ROI5': 'I_5',
             'ROI6': 'I_6',
             'ROI7': 'I_7',
             'ROI9': 'I_8',
             'ROI8': 'I_9',
             'Coinc.': 'I_{total}',
             'Mon1': 'I_{monitor}',
             'omega': u'ω',
             'detarm': u'2Θ',
             'Time[sec]': 'Time',
             'selector': u'λ_n',
            }
    columns=[column.rsplit('[', 1)[0] for column in columns]
    for item, newname in mapping.items():
      if item in columns:
        iindex=columns.index(item)
        columns.pop(iindex)
        columns.insert(iindex, newname)
    self.columns=columns
    self.image_col=self.columns.index('image_file')
    self.x_col=columns.index(u'ω')


  def read_textfile(self):
    data=self.lines_data[self.head_sep:self.foot_sep]
    if len(data)==0:
      return False
    datasplit=map(unicode.split, data)
    datasplit=filter(lambda line: len(line)==len(self.columns), datasplit)
    # data as string array of columns
    str_array=numpy.array(datasplit, dtype=str).transpose()
    remove_cols=[]
    if self.image_col is not None:
      self.file_names=str_array[self.image_col]
      remove_cols.append(self.image_col)
    # get polarizations
    if self.polarization_col is None:
      channels=['xx']
      polarization=numpy.array(channels*str_array.shape[1])
    else:
      polarization=str_array[self.polarization_col]
      remove_cols+=self.polarization_col
      if self.is_maria:
        polarization=numpy.array(map(lambda item: item[0]+item[1], polarization.transpose()))
      else:
        polarization=polarization[0]
      channels=set(polarization.tolist()) # get available polarization channels
      if (str_array.shape[1]/len(channels))<2:
        return False
    for col in reversed(sorted(remove_cols)):
      self.columns.pop(col)
      keep_cols=numpy.where(numpy.arange(str_array.shape[0])!=col)
      str_array=str_array[keep_cols]
    self.data['channels']=channels
    # convert to floats
    data_array=str_array.astype(numpy.float32)
    # create datasets for each polarization channel
    for channel in channels:
      # lines with this polarization
      idx=numpy.where(polarization==channel)[0]
      cdata=data_array[:, idx]
      dataobj=MeasurementData(x=self.x_col)
      for i, column in enumerate(self.columns):
        if column in self.units:
          unit=self.units[column]
        else:
          unit=''
        if unit is not 'counts':
          col=PhysicalProperty(column, unit, cdata[i])
        else:
          col=PhysicalProperty(column, unit, cdata[i], numpy.sqrt(cdata[i]))
        dataobj.data.append(col)
      if not u'ω' in self.columns:
        dataobj.data.append(PhysicalProperty(u'ω', self.units[u'ω'],
                                    numpy.ones(len(data))+self.constants[u'ω']))
      if not u'2Θ' in self.columns:
        dataobj.data.append(PhysicalProperty(u'2Θ', self.units[u'2Θ'],
                                    numpy.ones(len(data))+self.constants[u'2Θ']))
      ai=dataobj[u'ω']
      af=dataobj[u'2Θ']-ai
      if self.k_n is None:
        k_n=2.*numpy.pi/dataobj[u'λ_n']
        Qz=(k_n*(numpy.sin(af)+numpy.sin(ai)))//'Q_z'
        Qx=(k_n*(numpy.cos(af)-numpy.cos(ai)))//'Q_x'
      else:
        Qz=(self.k_n*(numpy.sin(af)+numpy.sin(ai)))//'Q_z'
        Qx=(self.k_n*(numpy.cos(af)-numpy.cos(ai)))//'Q_x'
      dataobj.data.append(Qz)
      dataobj.data.append(Qx)
      dataobj.data.append((dataobj['I_{window}']/dataobj['Time'])//'I_{norm(t)}')
      dataobj.data.append((dataobj['I_{window}']/dataobj['I_{monitor}'])//'I_{norm}')
      dataobj.ydata=dataobj.dimensions().index('I_{norm}')
      if not dataobj.x.unit=='Time':
        dataobj.logy=True
      self.data[channel]=dataobj
      self.data[channel+'_indices']=idx
    return True

  def read_images(self):
    if self.image_col is None:
      return
    y_detector=numpy.arange(self.detector_pixels, dtype=numpy.float32)
    tth_detector=(y_detector-self.center_y)*self.pixelsize
    fcount=0.
    fmax=len(self.file_names)
    factor=1./self.calibration
    for channel in self.data['channels']:
      files=self.file_names[self.data[channel+'_indices']]
      self.info('Channel %s - %i/%i files'%(channel, len(files), fmax),
                progress=20+70.*fcount/fmax)
      scan=self.data[channel]
      sdata=scan.data
      scan_lines=[]
      for i, filename in enumerate(files):
        if filename.endswith('.gz'):
          filename=filename[:-3]
        fcount+=1.
        data=self.get_file_data(filename)
        if i%25==0:
          # update progress every 25 files
          self.info(progress=20+70.*fcount/fmax)
        if data is None:
          continue
        data=numpy.fromstring(data, sep=' ', dtype=int).astype(numpy.float32)
        data=data.reshape(numpy.sqrt(data.shape[0]),-1) # create matrix
        I=data.sum(axis=0)
        dI=numpy.sqrt(I)
        scan_lines.append((scan[i], I*factor, dI*factor))
      if len(scan_lines)==0:
        continue
      out_data=[]
      om_col=scan.dimensions().index(u'ω')
      tth_col=scan.dimensions().index(u'2Θ')
      monitor_col=scan.dimensions().index(u'I_{monitor}')
      if u'λ_n' in scan.dimensions():
        lambda_col=scan.dimensions().index(u'λ_n')
      else:
        lambda_col=None
      for scan_line in scan_lines:
        omega=numpy.ones(scan_line[1].shape)*scan_line[0][om_col]
        y=y_detector
        tth=tth_detector+scan_line[0][tth_col]
        monitor=numpy.ones(scan_line[1].shape)*scan_line[0][monitor_col]
        if lambda_col is None:
          out_data.append([y, omega, tth, monitor, scan_line[1], scan_line[2]])
        else:
          lambda_n=numpy.ones(scan_line[1].shape)*scan_line[0][lambda_col]
          out_data.append([y, omega, tth, monitor, lambda_n, scan_line[1], scan_line[2]])
      out_cols=numpy.hstack(out_data)
      imgobj=MeasurementData(x=5, y=6, zdata=10)
      imgobj.scan_line=0
      imgobj.scan_line_constant=1
      imgobj.data.append(PhysicalProperty('pix_y', '', out_cols[0]))
      imgobj.data.append(PhysicalProperty(u'ω', sdata[om_col].unit, out_cols[1]))
      imgobj.data.append(PhysicalProperty(u'2Θ', sdata[tth_col].unit, out_cols[2]))
      imgobj.data.append(PhysicalProperty(u'I_{monitor}', 'counts', out_cols[3]))
      if lambda_col is None:
        imgobj.data.append(PhysicalProperty('I', 'counts', out_cols[4], out_cols[5]))
        k_n=self.k_n
      else:
        k_n=PhysicalProperty('k_n', 'Å^{-1}', 2.*numpy.pi/out_cols[4])
        imgobj.data.append(PhysicalProperty('I', 'counts', out_cols[5], out_cols[6]))
      ai=imgobj[u'ω']//'α_i'
      af=(imgobj[u'2Θ']-ai)//'α_f'
      afmai=(af-ai)//'α_f-α_i'
      Qz=(k_n*(numpy.sin(af)+numpy.sin(ai)))//'Q_z'
      Qx=(k_n*(numpy.cos(af)-numpy.cos(ai)))//'Q_x'
      imgobj.data.append(ai)
      imgobj.data.append(af)
      imgobj.data.append(afmai)
      imgobj.data.append(Qz)
      imgobj.data.append(Qx)
      imgobj.xdata=imgobj.dimensions().index('α_i')
      imgobj.ydata=imgobj.dimensions().index('α_f')
      Inorm=(imgobj['I']/imgobj['I_{monitor}'])//'I_{norm}'
      imgobj.data.append(Inorm)

      imgobj.logz=True
      imgobj.plot_options.xrange=[0., float("%.2g"%ai.max())]
      imgobj.plot_options.yrange=[0., float("%.2g"%ai.max())]
      imgobj.plot_options.zrange=[float("%.2g"%(1./sdata[monitor_col].mean())), None]
      self.data[channel+'_map']=imgobj

  def get_file_data(self, filename):
    if filename.endswith('.gz'):
      filename=filename[:-3]
    jfile=os.path.join(self.origin[0], filename)
    if os.path.exists(jfile):
      return open(jfile, 'r').read()
    if os.path.exists(jfile+'.gz'):
      return gzip.open(jfile+'.gz', 'r').read()
    return None

  def collect_objects(self):
    output=[]
    for channel in self.data['channels']:
      item=self.data[channel]
      item.short_info=self.polarization_mapping[channel]
      output.append(item)
    for channel in self.data['channels']:
      if channel+'_map' in self.data:
        item=self.data[channel+'_map']
        item.short_info=self.polarization_mapping[channel]+u' α_i-α_f map'
        output.append(item)
    info=u"\n".join(['---Header---']+self.lines_data[:self.head_sep]+
                    ['', '---Footer---']+self.lines_data[self.foot_sep:])
    for item in output:
      item.sample_name=self.origin[1].replace('_', ' ')
      item.info=info
    return output

class ZippedTreffMaria(TreffMariaReader, BinReader):
  name=u'Zip(TEEFF/MARIA)'
  glob_patterns=[u'*.zip']

  def __init__(self):
    global ZipFile
    from zipfile import ZipFile #@UnusedImport

  _read_file=BinReader._read_file

  def read(self):
    self.zipfile=ZipFile(self.raw_file)
    files=[item.filename for item in self.zipfile.filelist]
    prefix=self.origin[1][:-4]
    if not prefix in files:
      self.warn(u'%s not found in zipfile'%prefix)
      return None
    TextReader._read_file(self, self.zipfile.open(prefix, 'r'))
    if not self.check_head():
      self.warn('No valid TREFF or MARIA format')
      return None
    self.info('Evaluate Header')
    self.find_head_tail()
    self.eval_header()
    self.data={}
    self.info('Reading Text', 10)
    if not self.read_textfile():
      self.warn('No valid data found')
      return None
    if self.image_col is not None:
      self.info('Reading Images', 20)
      self.read_images()
    return self.collect_objects()

  def get_file_data(self, filename):
    try:
      return self.zipfile.open(filename, 'r').read()
    except:
      return None


