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
from plotpy.mds import PhysicalProperty, PhysicalConstant, MeasurementData
from plotpy.config import pnr, maria

GRAD_TO_MRAD=numpy.pi/180.*1000.
GRAD_TO_RAD=numpy.pi/180.

class TreffMariaBase(object):
  '''
  Methods common to TREFF, old and new MARIA file formats.
  '''

  def get_file_data(self, filename):
    if filename.endswith('.gz'):
      filename=filename[:-3]
    jfile=os.path.join(self.origin[0], filename)
    if os.path.exists(jfile):
      return open(jfile, 'r').read()
    if os.path.exists(jfile+'.gz'):
      return gzip.open(jfile+'.gz', 'r').read()
    return None


class TreffMariaReader(TextReader):
  name=u"TREFF/MARIA"
  description=u"Polarized neutron reflectivity measured with TREFF or MARIA at FRM-II"
  glob_patterns=[u'*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]',
                 u'*.dat']
  session='pnr'

  allow_multiread=True

  def set_treff(self):
    # define parameters for TREFF readout
    self.detector_pixels=256
    self.detector_region=pnr.treff_detector_region
    self.center_x=pnr.treff_center_x # pix
    self.center_y=pnr.treff_center_y # pix
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
                u'H': 'Gauss',
                }
    # import calibration from file, need to get this as relative path
    calibration=numpy.array(pnr.TREFF_CALIBRATION, dtype=numpy.float32)
    calibration*=calibration[calibration!=0.].mean() # normalize to about 1
    calibration[calibration==0.]=1.
    self.calibration=calibration

  def set_maria(self):
    # define parameters for MARIA readout
    self.detector_pixels=maria.DETECTOR_PIXELS
    self.calibration=numpy.ones(self.detector_pixels)
    self.center_y=maria.center_x
    self.center_x=maria.center_y
    self.pixelsize=0.019
    self.detector_region=maria.detector_region
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
    self.sample_name=self.origin[1].replace('_', ' ')
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
             'full': 'I_{total}',
             'Mon1': 'I_{monitor}',
             'monitor1': 'I_{monitor}',
             'omega': u'ω',
             'detarm': u'2Θ',
             'Time[sec]': 'Time',
             'time': 'Time',
             'selector': u'λ_n',
             'wavelength': u'λ_n',
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
        # wavelength column
        k_n=2.*numpy.pi/dataobj[u'λ_n']
        Qz=(k_n*(numpy.sin(af)+numpy.sin(ai)))//'Q_z'
        Qx=(k_n*(numpy.cos(af)-numpy.cos(ai)))//'Q_x'
      else:
        # fixed wavelength
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
    dr=self.detector_region
    y_detector=numpy.arange(self.detector_pixels, dtype=numpy.float32)[dr[2]:dr[3]]
    tth_detector=(y_detector-self.center_y)*self.pixelsize
    fcount=0.
    fmax=len(self.file_names)
    factor=1./self.calibration[dr[2]:dr[3]]
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
        data=data[dr[0]:dr[1], dr[2]:dr[3]]# crop to detector region
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

      if len(imgobj)>100000:
        # speedup plotting for large datasets
        imgobj.is_matrix_data=True
      self.data[channel+'_map']=imgobj

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
      item.sample_name=self.sample_name
      item.info=info
    return output

class MariaReader(TextReader, TreffMariaBase):
  name=u"TREFF/MARIA"
  description=u"Polarized neutron reflectivity measured with MARIA at FRM-II"
  glob_patterns=[u'*.dat']
  session='pnr'

  mapping=[
           ('omega', (u'ω', u'°')),
           ('detarm', (u'2Θ', u'°')),
           ('full', ('I_{full}', 'counts')),
           ('roi1', ('I_1', 'counts')),
           ('roi2', ('I_2', 'counts')),
           ('roi3', ('I_3', 'counts')),
           ('roi4', ('I_4', 'counts')),
           ('roi5', ('I_5', 'counts')),
           ('roi6', ('I_6', 'counts')),
           ('monitor1', ('I_{monitor1}', 'counts')),
           ('monitor2', ('I_{monitor2}', 'counts')),
           ('time', (u'Time', u's')),
           ('wavelength', (u'λ_n', u'Å')),
           ('temperature', (u'T', u'K')),
          ]

  norm_by='Time'
  norm_items=[item[1][0] for item in mapping if item[1][0].startswith('I_')]

  allow_multiread=True
  images_present=False
  columns=None
  units=None
  detector_pixels=maria.DETECTOR_PIXELS
  calibration=numpy.ones(detector_pixels)
  center_y=maria.center_x
  center_x=maria.center_y
  pixelsize=0.019
  detector_region=maria.detector_region

  def read(self):
    if not self.check_valid():
      self.warn('No valid TREFF or MARIA format')
      return None
    self.info('Evaluate Header', 1)
    self.eval_header()
    self.data={}
    self.info('Reading Text', 10)
    if not self.read_textfile():
      self.warn('No valid data found')
      return None
    if self.images_present:
      self.info('Reading Images', 20)
      self.read_images()
    return self.collect_objects()

  def check_valid(self):
    '''
      Test if header is correct and needed files are present.
    '''
    if self.text_data.split('\n', 1)[0][:11]==u'#shutter__1':

      return True
    return False

  def eval_header(self):
    cols=self.text_data.split('\n', 1)[0][1:].split()
    self.columns=[col.rsplit('_', 2)[0] for col in cols]
    self.units=[col.rsplit('_', 2)[1] for col in cols]
    setfile=os.path.join(self.origin[0], self.origin[1][:-4])+'.set'
    if os.path.exists(setfile):
      self.set_info=self.read_metafile(setfile)

  def read_metafile(self, fname):
    txt=open(fname, 'r').read()
    txt=unicode(txt, self.encoding, 'ignore')
    sections=map(unicode.strip, txt.split('---'))
    head_section=sections[1]
    sections=[map(unicode.strip, sec.split(':', 1)) for sec in sections[2:] if ':' in sec]
    meta_data={}
    # evaluate head information
    meta_data['command']=' '.join(head_section.split('command:')[1].split('created:')[0]
                                  .strip().splitlines())

    # evaluate device information
    for key, data in sections:
      eval_data={}
      if 'position:' in data:
        null=None
        eval_data['position']=eval(data.split('position:')[1].split('\n')[0])
      if 'status:' in data:
        eval_data['status']={}

      if eval_data!={}:
        meta_data[key]=eval_data
    return meta_data

  def read_textfile(self):
    data=numpy.genfromtxt(self.text_file, missing_values=['None'], unpack=True)
    pol=data[self.columns.index('pflipper')]
    ana=data[self.columns.index('aflipper')]
    pp=numpy.where((pol==0)&(ana==0))[0]
    mm=numpy.where((pol==1)&(ana==1))[0]
    pm=numpy.where((pol==0)&(ana==1))[0]
    mp=numpy.where((pol==1)&(ana==0))[0]
    channels=[('++', pp), ('+-', pm), ('-+', mp), ('--', mm)]
    
    data_cols=[]
    for col, (dim, unit) in self.mapping:
      if col in self.columns:
        di=data[self.columns.index(col)]
        if unit=='counts':
          data_cols.append(PhysicalProperty(dim, unit, di, numpy.sqrt(di)))
        else:
          data_cols.append(PhysicalProperty(dim, unit, di))
    full_dataobj=MeasurementData(x=2, y=3)
    full_dataobj.data=data_cols
#    if self.norm_by in full_dataobj.dimensions():
#      for col in self.norm_items:
#        if col in full_dataobj.dimensions():
#          full_dataobj[col]/=full_dataobj[self.norm_by]
    full_dataobj.logy=True
    Qz=4.*numpy.pi/full_dataobj[u'λ_n']*numpy.sin(full_dataobj[u'ω'])
    full_dataobj.data.insert(2, Qz//'Q_z')
    
    self.data['channels']=[]
    for c, f in channels:
      if f.any():
        self.data['channels'].append(c)
        self.data[c]=full_dataobj[f]

    self.images_present=True
    self.image_files={}
    for c, f in channels:
      if not c in self.data['channels']:
        continue
      self.image_files[c]=[]
      for i in f:
        ifile=os.path.join(self.origin[0], self.origin[1][:-4])+'_%i.gz'%i
        if not os.path.exists(ifile):
          self.images_present=False
        else:
          self.image_files[c].append(ifile)
    return True

  def read_images(self):
    dr=self.detector_region
    y_detector=numpy.arange(self.detector_pixels, dtype=numpy.float32)[dr[2]:dr[3]]
    tth_detector=(y_detector-self.center_y)*self.pixelsize
    fcount=0.
    fmax=0
    for channel in self.data['channels']:
      fmax+=len(self.data[channel])
    factor=1./self.calibration[dr[2]:dr[3]]
    for channel in self.data['channels']:
      files=self.image_files[channel]
      self.info('Channel %s - %i/%i files'%(channel, len(files), fmax),
                progress=20+70.*fcount/fmax)
      scan=self.data[channel]
      sdata=scan.data
      scan_lines=[]
      for i, filename in enumerate(files):
        fcount+=1.
        data=self.get_file_data(filename[:-3])
        if i%25==0:
          # update progress every 25 files
          self.info(progress=20+70.*fcount/fmax)
        if data is None:
          continue
        data=numpy.fromstring(data, sep=' ', dtype=int).astype(numpy.float32)
        data=data.reshape(numpy.sqrt(data.shape[0]),-1) # create matrix
        data=data[dr[0]:dr[1], dr[2]:dr[3]]# crop to detector region
        I=data.sum(axis=0)
        dI=numpy.sqrt(I)
        scan_lines.append((scan[i], I*factor, dI*factor))
      if len(scan_lines)==0:
        continue
      out_data=[]
      om_col=scan.dimensions().index(u'ω')
      tth_col=scan.dimensions().index(u'2Θ')
      monitor_col=scan.dimensions().index(u'I_{monitor2}')
      lambda_col=scan.dimensions().index(u'λ_n')
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
      imgobj=MeasurementData(x=5, y=6, zdata=11)
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
      Qxz=Qx/Qz//'Q_x/Q_z'
      imgobj.data.append(ai)
      imgobj.data.append(af)
      imgobj.data.append(afmai)
      imgobj.data.append(Qz)
      imgobj.data.append(Qx)
      imgobj.data.append(Qxz)
      imgobj.xdata=imgobj.dimensions().index('α_i')
      imgobj.ydata=imgobj.dimensions().index('α_f')
      Inorm=(imgobj['I']/imgobj['I_{monitor}'])//'I_{norm}'
      imgobj.data.append(Inorm)

      imgobj.logz=True
      imgobj.plot_options.xrange=[0., float("%.2g"%ai.max())]
      imgobj.plot_options.yrange=[0., float("%.2g"%ai.max())]
      imgobj.plot_options.zrange=[float("%.2g"%(1./sdata[monitor_col].mean())), None]

      if len(imgobj)>100000:
        # speedup plotting for large datasets
        imgobj.is_matrix_data=True
      self.data[channel+'_map']=imgobj


  def collect_objects(self):
    output=[]
    for channel in self.data['channels']:
      item=self.data[channel]
      item.short_info=channel
      output.append(item)
    for channel in self.data['channels']:
      if channel+'_map' in self.data:
        item=self.data[channel+'_map']
        item.short_info=channel+u' α_i-α_f map'
        output.append(item)
    #for item in output:
    #  item.sample_name=self.sample_name
    #  item.info=info
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

class GisansMariaReader(TreffMariaReader):
  name=u"TREFF/MARIA"
  description=u"Polarized GISANS measured with MARIA at FRM-II"
  glob_patterns=[u'*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]']
  session='gisas'

  store_mds=False
  allow_multiread=True

  def read_images(self):
    if self.image_col is None:
      return
    dr=self.detector_region
    x_detector=numpy.arange(self.detector_pixels, dtype=numpy.float32)[dr[0]:dr[1]]
    y_detector=numpy.arange(self.detector_pixels, dtype=numpy.float32)[dr[2]:dr[3]]
    phi_detector=(x_detector-self.center_x)*self.pixelsize
    tth_detector=(y_detector-self.center_y)*self.pixelsize
    Y, X=numpy.meshgrid(y_detector, x_detector)
    X=X.flatten();Y=Y.flatten()
    Tth, Phi=numpy.meshgrid(tth_detector, phi_detector)
    Phi=PhysicalProperty('φ', '°', Phi.flatten()); Tth=PhysicalProperty('φ', '°', Tth.flatten())
    fcount=0.
    fmax=len(self.file_names)
    #factor=1./self.calibration[dr[2]:dr[3]]
    for channel in self.data['channels']:
      self.data[channel+'_map']=[]
      files=self.file_names[self.data[channel+'_indices']]
      self.info('Channel %s - %i/%i files'%(channel, len(files), fmax),
                progress=20+70.*fcount/fmax)
      scan=self.data[channel]
      sdata=scan.data
      om_col=scan.dimensions().index(u'ω')
      tth_col=scan.dimensions().index(u'2Θ')
      monitor_col=scan.dimensions().index(u'I_{monitor}')
      if u'λ_n' in scan.dimensions():
        lambda_col=scan.dimensions().index(u'λ_n')
      else:
        lambda_col=None
      for i, filename in enumerate(files):
        if filename.endswith('.gz'):
          filename=filename[:-3]
        fcount+=1.
        data=self.get_file_data(filename)
        # update progress
        self.info(progress=20+70.*fcount/fmax)
        if data is None:
          continue
        data=numpy.fromstring(data, sep=' ', dtype=int).astype(numpy.float32)
        data=data.reshape(numpy.sqrt(data.shape[0]),-1) # create matrix
        data=data[dr[0]:dr[1], dr[2]:dr[3]]# crop to detector region
        I=data.flatten()
        dI=numpy.sqrt(I)
        tth=Tth+sdata[tth_col][i]
        monitor=sdata[monitor_col][i]
        if lambda_col is None:
          k_n=self.k_n
        else:
          k_n=PhysicalConstant(2.*numpy.pi/sdata[lambda_col][i], 'Å^{-1}')
        imgobj=MeasurementData(x=6, y=7, zdata=5)
        imgobj.scan_line=0
        imgobj.scan_line_constant=1
        imgobj.data.append(PhysicalProperty(u'x', 'pix', X))
        imgobj.data.append(PhysicalProperty(u'y', 'pix', Y))
        imgobj.data.append(PhysicalProperty(u'φ', sdata[om_col].unit, Phi))
        imgobj.data.append(PhysicalProperty(u'2Θ', sdata[tth_col].unit, tth))
        imgobj.data.append(PhysicalProperty('I', 'counts', I, dI))
        imgobj.data.append(PhysicalProperty('I_{norm}', '', I/monitor, dI/monitor))
        #ai=imgobj[u'ω'][i]
        #af=(imgobj[u'2Θ'][i]-ai)
        Qz=(2.*k_n*(numpy.sin(tth/2.)))//'Q_z'
        Qy=(2.*k_n*(numpy.sin(Phi/2.)))//'Q_x'
        imgobj.data.append(Qy)
        imgobj.data.append(Qz)

        imgobj.logz=True
        imgobj.is_matrix_data=True
        #imgobj.plot_options.xrange=[0., float("%.2g"%ai.max())]
        #imgobj.plot_options.yrange=[0., float("%.2g"%ai.max())]
        imgobj.plot_options.zrange=[float("%.2g"%(1./monitor)), None]

        self.data[channel+'_map'].append(imgobj)

  def collect_objects(self):
    output=[]
    for channel in self.data['channels']:
      if channel+'_map' in self.data:
        items=self.data[channel+'_map']
        for i, item in enumerate(items):
          item.short_info=self.polarization_mapping[channel]+u'#%02i'%i
          output.append(item)
    info=u"\n".join(['---Header---']+self.lines_data[:self.head_sep]+
                    ['', '---Footer---']+self.lines_data[self.foot_sep:])
    for item in output:
      item.sample_name=self.sample_name
      item.info=info
    return output

class ZippedGisansMariaReader(ZippedTreffMaria, GisansMariaReader):
  name=u"zip(TREFF/MARIA)"
  description=u"Polarized GISANS measured with MARIA at FRM-II"
  glob_patterns=[u'*.zip']
  session='gisas'

  store_mds=False
  allow_multiread=True

  collect_objects=GisansMariaReader.collect_objects
  read_images=GisansMariaReader.read_images
