#-*- coding: utf-8 -*-
'''
  Read reflectometry data from the SNS magnetism reflectometer.
'''

import numpy
from baseread import Reader
from plotpy.mds import PhysicalConstant, PhysicalProperty, MeasurementData
from plotpy.constants import m_n, h

class MagicsReader(Reader):
  name=u"MAGICS"
  description=u"Data of magnetism reflectometer at SNS"
  glob_patterns=[u'*.nxs']
  session='pnr'

  parameters=[('tth_offset', 0.), ('phi_offset', 0.),
              ('show_tth_phi', False), ('show_tth_lambda', False)]
  parameter_units={
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction (ignored for ID01)',
                         'center_y': 'Direct beam center in y direction (ignored for ID01)',
                         } # hover text for description

  store_mds=False
  allow_multiread=True

  unit_conversions={
                    'second': u's',
                    'millisecond': u'ms',
                    'microsecond': u'µs',
                    'degree': u'°',
                    'metre': u'm',
                    'millimetre': u'mm',

                    }

  def __init__(self):
    global h5py
    import h5py #@UnusedImport

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
      title=u'collection_title', # measurement title
      sample=u'sample/name',
      gemoetry_file=u'instrument/SNSgeometry_file_name',
      monitor=u'proton_charge',
      time=u'start_time',
      alpha_i=u'sample/SANGLE',
      tth=u'instrument/bank1/DANGLE/average_value',
      #detector_angle2=u'instrument/bank1/DANGLE0',
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
    lambda_n=(((h/m_n)*(tof/full_dist))%u'Å')//u'λ_n' # h/(m·v)=λ
    #SDdistance=block['instrument']['bank1']['distance'] # distance of each pixel
    I=self.get_value('bank1/data')
    x=self.get_value('bank1/x_pixel_offset', 'pix_x')
    y=self.get_value('bank1/y_pixel_offset', 'pix_y')
    tth=(-numpy.arctan(x%'m'/(self.header_info['sample_detector_distance']%'m'))
         +self.header_info['tth']-self.tth_offset)//u'2Θ'
    phi=(numpy.arctan(y%'m'/(self.header_info['sample_detector_distance']%'m'))
         -self.phi_offset)//u'φ'
    tth_2=self.header_info['alpha_i']

    if self.show_tth_phi:
      # create phi, tth, I grid data
      TTH=numpy.repeat(tth, phi.shape[0]).reshape(tth.shape[0], phi.shape[0])
      PHI=numpy.tile(phi, tth.shape[0]).reshape(tth.shape[0], phi.shape[0])
      ds=MeasurementData(zdata=2)
      ds.scan_line=0
      ds.scan_line_constant=1
      ds.data.append(TTH.flatten()%u'°')
      ds.data.append(PHI.flatten()%u'°')
      Is=I.sum(axis=2).flatten()
      ds.data.append(PhysicalProperty('I', 'counts', Is, numpy.sqrt(Is)))
      ds.sample_name=self.header_info['sample']
      ds.short_info=self.block_key
      ds.is_matrix_data=True
      ds.plot_options.rectangles.append([
                                         [[2*float(tth_2%u'°')-0.1,-0.5, 1.],
                                         [2*float(tth_2%u'°')+0.1, 0.5, 1.]],
                                         True, True, 0.5, '#ffffff', True, '#000000', '',
                                         ])
      ds.plot_options.rectangles.append([
                                         [[2*float(tth_2%u'°')-0.1, 0.5, 1.],
                                         [2*float(tth_2%u'°')+0.1, 1., 1.]],
                                         True, True, 0.5, '#ff0000', True, '#000000', '',
                                         ])
      ds.plot_options.rectangles.append([
                                         [[2*float(tth_2%u'°')-0.1,-1., 1.],
                                         [2*float(tth_2%u'°')+0.1,-0.5, 1.]],
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
      Is=I.sum(axis=1).flatten()
      ds.data.append(PhysicalProperty('I', 'counts', Is, numpy.sqrt(Is)))
      ds.sample_name=self.header_info['sample']
      ds.short_info=self.block_key
      ds.is_matrix_data=True
      output.append(ds)
    # create reflectivity data
    Qz=(4.*numpy.pi/lambda_n*numpy.sin(tth_2))//u'Q_z'
    x_reg=numpy.where((numpy.abs(tth-tth_2*2)%u'°')<0.1)[0]
    y_reg=numpy.where((numpy.abs(phi)%u'°')<=0.5)[0]
    y_bg=numpy.where(((numpy.abs(phi)%u'°')>0.5)&((numpy.abs(phi)%u'°')<=1.))[0]

    ds=MeasurementData()
    ds.scan_line=1
    ds.scan_line_constant=0
    ds.data.append(Qz)
    Is=I[x_reg, :, :][:, y_reg, :].sum(axis=0).sum(axis=0)
    Ib=I[x_reg, :, :][:, y_bg, :].sum(axis=0).sum(axis=0)
    Ib*=float(len(Is))/len(Ib)
    ds.data.append(PhysicalProperty('I_{corr}', 'counts', Is-Ib, numpy.sqrt(Is)))
    ds.data.append(PhysicalProperty('I_{raw}', 'counts', Is, numpy.sqrt(Is)))
    ds.data.append(PhysicalProperty('I_{BG}', 'counts', Ib, numpy.sqrt(Ib)))
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
