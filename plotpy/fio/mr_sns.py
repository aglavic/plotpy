# -*- coding: utf-8 -*-
'''
  Read reflectometry data from the SNS magnetism reflectometer.
'''

import numpy
from baseread import Reader, TextReader
from plotpy.mds import PhysicalConstant, PhysicalProperty, MeasurementData, MeasurementData4D
from plotpy.constants import m_n, h
from plotpy.config import mr_sns as config

class DatReader(TextReader):
  name=u"MR_SNS"
  description=u"Reduced data of magnetism reflectometer at SNS"
  glob_patterns=[u'*.dat']
  session='pnr'

  store_mds=False

  def read(self):
    output=[]
    header_info=self.read_header()
    data=self.read_data()
    dataset=MeasurementData()
    if header_info['type']=='Specular':
      dataset.data.append(PhysicalProperty('Q_z', u'Å^{-1}', data[0], data[3]))
      dataset.data.append(PhysicalProperty('R', u'', data[1], data[2]))
      dataset.logy=True
    elif header_info['type']=='OffSpecSmooth':
      dataset.zdata=2
      dataset.scan_line=0
      dataset.scan_line_constant=1
      dataset.data.append(PhysicalProperty('k_{i,z}-k_{f,z}', u'Å^{-1}', data[0]))
      dataset.data.append(PhysicalProperty('Q_z', u'Å^{-1}', data[1]))
      dataset.data.append(PhysicalProperty('I', u'a.u.', data[2]))
      dataset.logz=True
    elif header_info['type']=='OffSpec':
      dataset.xdata=4
      dataset.zdata=5
      dataset.scan_line=7
      dataset.scan_line_constant=6
      dataset.data.append(PhysicalProperty('Q_x', u'Å^{-1}', data[0]))
      dataset.data.append(PhysicalProperty('Q_z', u'Å^{-1}', data[1]))
      dataset.data.append(PhysicalProperty('k_{i,z}', u'Å^{-1}', data[2]))
      dataset.data.append(PhysicalProperty('k_{f,z}', u'Å^{-1}', data[3]))
      dataset.data.append(PhysicalProperty('k_{i,z}-k_{f,z}', u'Å^{-1}', data[4]))
      dataset.data.append(PhysicalProperty('I', u'a.u.', data[5], data[6]))
      dataset.data.append(PhysicalProperty('scan', u'', data[7]))
      dataset.data.append(PhysicalProperty('item', u'', data[8]))
      dataset.logz=True
    dataset.sample_name=''
    dataset.short_info=header_info['indices']+' ('+header_info['channel']+')'
    dataset.info=header_info['header']
    output.append(dataset)
    return output

  def read_header(self):
    input_file_lines=self.text_data.splitlines()
    input_file_lines=map(unicode.strip, input_file_lines)
    header_lines=filter(lambda line: line.startswith('#'), input_file_lines)
    output={'indices': '', 'channel': 'x', 'header': '\n'.join(header_lines)}
    for line in input_file_lines:
      if "Input file indices:" in line:
        output['indices']=line.split("Input file indices:")[1].strip()
      elif "Extracted states:" in line:
        output['channel']=line.split("Extracted states:")[1].strip()
      elif "Type:" in line:
        output['type']=line.split("Type:")[1].strip()
    return output

  def read_data(self):
    input_file_lines=self.text_data.splitlines()
    input_file_lines=map(unicode.strip, input_file_lines)
    data_lines=filter(lambda line: not (line.startswith('#') or line==''), input_file_lines)
    new_line_indices=[i for i in range(len(input_file_lines)) if input_file_lines[i]=='']
    output_data=numpy.array(map(unicode.split, data_lines), dtype=float).transpose()
    scan_index=numpy.zeros_like(output_data[0])
    scan_item=numpy.zeros_like(output_data[0])
    index_i=0
    for index in new_line_indices:
      scan_index[index-index_i:]+=1
      scan_item[index-index_i:]=numpy.arange(len(output_data[0])-index+index_i)
      index_i+=1
    return numpy.vstack([output_data, scan_index, scan_item])


class MRReader(Reader):
  name=u"MR_SNS_RAW"
  description=u"Data of magnetism reflectometer at SNS"
  glob_patterns=[u'*.nxs']
  session='none'

  parameters=[('tth_offset', 0.), ('phi_offset', 0.),
              ("alpha_i_offset", 0.),
              ('tth_window', 0.1), ('phi_window', 0.5),
              ('show_4D', False),
              ('show_tth_phi', False), ('show_tth_lambda', False),
              ('background_method', ("Top/Bottom of Window", "Right of Window")),
              ('intensity_file', 'None')]
  parameter_units={
                   'tth_offset': u'°',
                   'phi_offset': u'°',
                   'alpha_i_offset': u'°',
                   'tth_window': u'°',
                   'phi_window': u'°',
                   'intensity_file': 'file',
                   }
  parameter_description={
                         'tth_window': u'Region used for specular extraction',
                         'phi_window': u'Region used for specular extraction in y direction',
                         'show_4D': u'Creat a full 4D dataset containing all information',
                         'show_tth_phi': u'Creat a map of 2Θ-φ vs. I',
                         'show_tth_lambda': u'Creat a map of 2Θ-λ vs. I',
                         }  # hover text for description

  store_mds=False
  allow_multiread=True

  unit_conversions={
                    'second': u's',
                    'millisecond': u'ms',
                    'microsecond': u'µs',
                    'degree': u'°',
                    'metre': u'm',
                    'millimetre': u'mm',
                    'picoCoulomb': u'pC',
                    }

  def __init__(self):
    global h5py
    import h5py  # @UnusedImport

  def _read_file(self, filename):
    '''
      Read the raw data from the file.
    '''
    if hasattr(filename, 'read'):
      self.error('Can only open nexus files from filename, not file object.')
      return
    elif filename.lower().endswith(".gz"):
      self.error('Can only open nexus files from filename, not gzip file.')
    else:
      self.nxs=h5py.File(filename, 'r')
      self.raw_data=filename

  def read(self):
    output=[]
    self.tth_offset=PhysicalConstant(self.tth_offset, u'°')
    self.phi_offset=PhysicalConstant(self.phi_offset, u'°')
    for key, block in self.nxs.items():
      self.info(key+u'-block')
      # get each dataset in the file
      self.block=block
      self.block_key=key
      datasets=self.read_block()
      if datasets is None:
        continue
      output+=datasets
    return output

  def collect_header_info(self):
    '''
    
    '''
    items=dict(
      title=u'collection_title',  # measurement title
      sample=u'sample/name',
      gemoetry_file=u'instrument/SNSgeometry_file_name',
      monitor=u'proton_charge',
      time=u'start_time',
      alpha_i=u'sample/SANGLE',
      tth=u'instrument/bank1/DANGLE/average_value',
      # detector_angle2=u'instrument/bank1/DANGLE0',
      sample_detector_distance=u'instrument/bank1/SampleDetDis',
      sample_tof_distance=u'instrument/moderator/ModeratorSamDis',
                        )
    self.header_info=dict([(name, self.get_value(path)) for name, path in items.items()])

  def read_block(self):
    self.collect_header_info()
    if self.header_info['monitor']==0:
      return None
    output=[]
    full_dist=(self.header_info['sample_tof_distance']
               +self.header_info['sample_detector_distance'])
    tof=self.get_value('bank1/time_of_flight')%'s'
    tof=(tof[:-1]+tof[1:])/2.
    lambda_n=(((h/m_n)*(tof/full_dist))%u'Å')//u'λ_n'  # h/(m·v)=λ
    # SDdistance=block['instrument']['bank1']['distance'] # distance of each pixel
    I=self.get_value('bank1/data')
    x=self.get_value('bank1/x_pixel_offset', 'pix_x')
    y=self.get_value('bank1/y_pixel_offset', 'pix_y')
    xpix=PhysicalProperty('x', 'pix', numpy.arange(x.shape[0]))
    ypix=PhysicalProperty('y', 'pix', numpy.arange(y.shape[0]))
    # filter detector sensitive area
    reg=config.detector_sensitive_area
    I=I[reg[0]:reg[1], reg[2]:reg[3], :]
    monitor=PhysicalProperty(self.header_info['monitor'])%'C'
    I=PhysicalProperty('I', 'counts', I, numpy.sqrt(I))/monitor
    x=x[reg[0]:reg[1]]
    y=y[reg[2]:reg[3]]
    xpix=xpix[reg[0]:reg[1]]
    ypix=ypix[reg[2]:reg[3]]

    tth=(-numpy.arctan(x%'m'/(self.header_info['sample_detector_distance']%'m'))
         +self.header_info['tth']-self.tth_offset)//u'2Θ'
    phi=(numpy.arctan(y%'m'/(self.header_info['sample_detector_distance']%'m'))
         -self.phi_offset)//u'φ'
    alpha_i=self.header_info['alpha_i']-self.alpha_i_offset
    k=(2.*numpy.pi/lambda_n)//u'k'

    if self.show_tth_phi:
      # create phi, tth, I grid data
      TTH=numpy.repeat(tth, phi.shape[0]).reshape(tth.shape[0], phi.shape[0])
      PHI=numpy.tile(phi, tth.shape[0]).reshape(tth.shape[0], phi.shape[0])
      X=numpy.repeat(xpix, phi.shape[0]).reshape(tth.shape[0], phi.shape[0])
      Y=numpy.tile(ypix, tth.shape[0]).reshape(tth.shape[0], phi.shape[0])
      ds=MeasurementData(zdata=4)
      ds.scan_line=0
      ds.scan_line_constant=1
      ds.data.append(TTH.flatten()%u'°')
      ds.data.append(PHI.flatten()%u'°')
      ds.data.append(X.flatten())
      ds.data.append(Y.flatten())
      Is=I.sum(axis=2).flatten()//"I"
      ds.data.append(Is)
      ds.sample_name=self.header_info['sample']
      ds.short_info=self.block_key
      ds.is_matrix_data=True
      ds.plot_options.rectangles.append([
                                         [[2*float(alpha_i%u'°')-self.tth_window,
                                           -self.phi_window, 1.],
                                         [2*float(alpha_i%u'°')+self.tth_window,
                                          self.phi_window, 1.]],
                                         True, True, 0.5, '#ffffff', True, '#000000', '',
                                         ])
      if self.background_method=="Top/Bottom of Window":
        ds.plot_options.rectangles.append([
                                           [[2*float(alpha_i%u'°')-self.tth_window,
                                             self.phi_window, 1.],
                                           [2*float(alpha_i%u'°')+self.tth_window,
                                            2*self.phi_window, 1.]],
                                           True, True, 0.5, '#ff0000', True, '#000000', '',
                                           ])
        ds.plot_options.rectangles.append([
                                           [[2*float(alpha_i%u'°')-self.tth_window,
                                             -2*self.phi_window, 1.],
                                           [2*float(alpha_i%u'°')+self.tth_window,
                                            -self.phi_window, 1.]],
                                           True, True, 0.5, '#ff0000', True, '#000000', '',
                                           ])
      else:
        ds.plot_options.rectangles.append([
                                           [[2*float(alpha_i%u'°')+self.tth_window,
                                             -self.phi_window, 1.],
                                           [2*float(alpha_i%u'°')+3*self.tth_window,
                                            self.phi_window, 1.]],
                                           True, True, 0.5, '#ff0000', True, '#000000', '',
                                           ])

      output.append(ds)
    if self.show_tth_lambda:
      # create lambda, tth, I grid data
      TTH=numpy.repeat(tth, lambda_n.shape[0]).reshape(tth.shape[0], lambda_n.shape[0])
      LAMBDA_N=numpy.tile(lambda_n, tth.shape[0]).reshape(tth.shape[0], lambda_n.shape[0])
      ds=MeasurementData(zdata=2)
      ds.scan_line=1
      ds.scan_line_constant=0
      ds.data.append(LAMBDA_N.flatten())
      ds.data.append(TTH.flatten()%u'°')
      Is=I.sum(axis=1).flatten()//"I"
      ds.data.append(Is)
      ds.sample_name=self.header_info['sample']
      ds.short_info=self.block_key
      output.append(ds)
    if self.show_4D:
      # create lambda, tth, I grid data
      TTH=numpy.repeat(tth, k.shape[0]*phi.shape[0]).reshape(tth.shape[0], phi.shape[0],
                                                             k.shape[0])
      PHI=numpy.repeat(numpy.tile(phi, tth.shape[0]), k.shape[0]).reshape(tth.shape[0],
                                                              phi.shape[0], k.shape[0])
      LAMBDA_N=numpy.tile(lambda_n, tth.shape[0]*phi.shape[0]).reshape(tth.shape[0], phi.shape[0], k.shape[0])
      K=numpy.tile(k, tth.shape[0]*phi.shape[0]).reshape(tth.shape[0], phi.shape[0], k.shape[0])
      alpha_f=TTH-alpha_i
      Qx=(K*(numpy.cos(alpha_f)*numpy.cos(PHI)-numpy.cos(alpha_i)))//u"Q_x"
      Qy=(K*(numpy.cos(alpha_f)*numpy.sin(PHI)))//u"Q_y"
      Qz=(K*(numpy.sin(alpha_f)+numpy.sin(alpha_i)))//u"Q_z"
      Pi=(K*(numpy.sin(alpha_i)))//u"p_i"
      Pf=(K*(numpy.sin(alpha_f)))//u"p_f"
      PiPf=(Pi-Pf)//"p_i-p_f"

      ds=MeasurementData4D(x=3, y=5, y2=4, z=10)
      ds.data.append(TTH.flatten()%u'°')
      ds.data.append(PHI.flatten()%u'°')
      ds.data.append(K.flatten())
      ds.data.append(Qx.flatten())
      ds.data.append(Qy.flatten())
      ds.data.append(Qz.flatten())
      ds.data.append(Pi.flatten())
      ds.data.append(Pf.flatten())
      ds.data.append(PiPf.flatten())
      ds.data.append(LAMBDA_N.flatten())

      ds.data.append(I.flatten())
      ds.sample_name=self.header_info['sample']
      ds.short_info=self.block_key
      output.append(ds)
    # create reflectivity data
    Qz=(2.*k*numpy.sin(alpha_i))//u'Q_z'
    x_reg=numpy.where((numpy.abs(tth-alpha_i*2)%u'°')<self.tth_window)[0]
    y_reg=numpy.where((numpy.abs(phi)%u'°')<=self.phi_window)[0]
    if self.background_method=="Top/Bottom of Window":
      x_bg=numpy.where((numpy.abs(tth-alpha_i*2)%u'°')<self.tth_window)[0]
      y_bg=numpy.where(((numpy.abs(phi)%u'°')>self.phi_window)
                     &((numpy.abs(phi)%u'°')<=2*self.phi_window))[0]
    else:
      x_bg=numpy.where((numpy.abs((tth-alpha_i*2)%u'°'-2*self.tth_window))<self.tth_window)[0]
      y_bg=numpy.where((numpy.abs(phi)%u'°')<=self.phi_window)[0]

    ds=MeasurementData()
    ds.scan_line=1
    ds.scan_line_constant=0
    ds.data.append(Qz)
    Is=I[x_reg][:, y_reg].sum(axis=0).sum(axis=0)
    Ib=I[x_bg][:, y_bg].sum(axis=0).sum(axis=0)
    Ib*=float(len(Is))/len(Ib)
    ds.data.append((Is-Ib)//'I_{corr}')
    ds.data.append(Is//'I_{raw}')
    ds.data.append(Ib//'I_{BG}')
    ds.sample_name=self.header_info['sample']
    ds.short_info=self.block_key
    output.append(ds)

    return  output


  def get_value(self, path, name=None):
    sub=self.block[path]
    if name is None:
      name=unicode(path)
    if hasattr(sub, 'value'):
      item=sub
    elif 'average_value' in sub:
      item=sub['average_value']
    if 'units' in item.attrs.keys():
      unit=str(item.attrs['units'])
      if unit in self.unit_conversions:
        unit=self.unit_conversions[unit]
      if item.shape==(1,):
        return PhysicalConstant(item[0], unit, name)
      else:
        return PhysicalProperty(name, unit, item.value)
    else:
      if item.shape==(1,):
        return item[0]
      else:
        return item.value
