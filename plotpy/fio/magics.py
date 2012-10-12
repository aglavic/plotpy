#-*- coding: utf-8 -*-
'''
  Read reflectometry data from the SNS magnetism reflectometer.
'''

import numpy
from baseread import Reader
from plotpy.mds import PhysicalConstant, PhysicalProperty, MeasurementData
from plotpy.constants import m_n, h

class EDFReader(Reader):
  name=u"MR"
  description=u"Data of magnetism reflectometer at SNS"
  glob_patterns=[u'*.nxs']
  session='pnr'

  parameters=[]
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
                    'degree': u'°',

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

  def read(self):
    output=[]
    for key, block in self.nxs.items():
      print "\t%s"%key
      # get each dataset in the file
      self.block=block
      datasets=self.read_block()
      output+=datasets
    return output

  def collect_header_info(self):
    '''
    
    '''
    items=dict(
      title='collection_title', # measurement title
      sample='sample/name',
      gemoetry_file='instrument/SNSgeometry_file_name',
      monitor='proton_charge',
      time='start_time',
      alpha_i='sample/SANGLE',
      detector_angle='instrument/bank1/DANGLE/average_value',
      detector_angle2='instrument/bank1/DANGLE0',
      detector_sample_distance='instrument/bank1/SampleDetDis',
      sample_tof_distance='instrument/moderator/ModeratorSamDis',
                        )
    self.header_info=dict([(name, self.get_value(path)) for name, path in items.items()])

  def read_block(self):
    self.collect_header_info()
    full_dist=self.header_info['sample_tof_distance']+self.header_info['sample_tof_distance']
    ToF=self.get_value('bank1/time_of_flight')
    lambda_n=(((h/m_n)/ToF)%'Å')//'λ_n'
    #SDdistance=block['instrument']['bank1']['distance'] # distance of each pixel
    I=self.get_value('bank1/data')
    x=self.get_value('bank1/x_pixel_offset')
    y=self.get_value('bank1/y_pixel_offset')
    # create x,y grid indices
    X=numpy.tile(x, y.shape[0]).reshape(x.shape[0], y.shape[0])
    Y=numpy.repeat(y, x.shape[0]).reshape(x.shape[0], y.shape[0])


  def get_value(self, path, name=None):
    sub=self.block[path]
    if name is None:
      name=path
    if hasattr(sub, 'value'):
      item=sub
    elif hasattr(sub, 'average_value'):
      if 'average_value':
        item=sub['average_value']
    if 'units' in item.attrs.keys():
      unit=item.attrs['units']
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
        return item.values
