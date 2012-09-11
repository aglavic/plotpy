# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'mds' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''


import numpy
from baseread import TextReader, BinReader
from plotpy.mds import HugeMD, PhysicalProperty, MeasurementData

class DCAlog(TextReader):
  '''
    DCA MBE log files.
  '''
  name=u"DCA log"
  description=u"Files saved by DCA MBE as logfiles"
  glob_patterns=[u'*.log']
  session='mbe'

  def read(self):
    ''' 
      Read DCA log files
    '''
    data_lines=self.text_data.splitlines()
    i=0
    while i<len(data_lines):
      try:
        float(data_lines[i].split()[0])
      except:
        i+=1
      else:
        break
    header=data_lines[:i]
    if len(header)>0:
      cols=header[-1].strip().split('\t')
      cols=map(lambda col: col.replace('_', '-') , cols)
      sample_name=header[0].strip()
    else:
      cols=[u"Col-%i"%i for i in range(len(data_lines[0].split('\t')))]
      sample_name=''
    data_lines=data_lines[i:]
    data=self.lines2data(data_lines, '\t', numpy.float64)
    output=MeasurementData()
    output.short_info=self.origin[1].rsplit('.', 1)[0]
    output.sample_name=sample_name
    for i, col in enumerate(cols):
      try:
        output.data.append(PhysicalProperty(col, '', data[i], dtype=numpy.float64))
      except IndexError:
        return None
    return [output]

class AESdat(TextReader):
  '''
    AES dat files.
  '''
  name=u"AES dat"
  description=u""
  glob_patterns=[u'*.dat']
  session='mbe'
  priority=4 # dat is an ofter used filetype and the check here is slow

  def read(self):
    ''' 
      Read AES dat file
    '''
    data_lines=self.text_data.splitlines()
    i=0
    while 'Basis' not in data_lines[i]:
      i+=1
      if i==len(data_lines):
        self.warn('Not a valid AES .dat file')
        return None
    ignore=data_lines[:i+1]
    data_lines=data_lines[i+1:]
    cols=self.lines2data(data_lines)
    output=MeasurementData()
    output.data.append(PhysicalProperty('E', 'eV', cols[0]/1000.))
    output.data.append(PhysicalProperty('I', 'a.u.', cols[1]))
    output.short_info=self.origin[1].rsplit('.', 1)[0]
    for i, col in enumerate(cols[2:]):
      output.data.append(PhysicalProperty('I_%i'%(i+2), 'a.u.', col))
    return [output]

class RHEEDpng(BinReader):
  '''
    PNG files for RHEED.
  '''
  name=u"RHEED PNG"
  description=u""
  glob_patterns=[u'*.png']
  session='mbe'

  def __init__(self):
    global Image
    # use PIL image readout
    import Image
    # py2exe hack
    import PngImagePlugin #@UnusedImport
    Image._initialized=2


  def read(self):
    '''
      Read a png datafile.
    '''

    data_array=self.read_raw_data()
    pixels_x, pixels_y=data_array.shape
    if data_array[0][0]==255:
      data_array=255-data_array
    #detector_distance=setup['DETECTOR_DISTANCE'] #mm
    #pixelsize=setup['DETECTOR_DIAMETER']/setup['DETECTOR_PIXELS']
    #center_x=setup['CENTER_X']
    #center_y=setup['CENTER_Y']
    sample_name=''
    dataobj=HugeMD([], [], 0, 1,-1, 2)
    data_array=data_array.flatten()
    #sys.stdout.write("\b\b\b, calculating q-positions and joining data...")
    #sys.stdout.flush()
    # read additional info from end of file
    y_array=numpy.linspace(0, (pixels_x)*(pixels_y)-1,
                     (pixels_x)*(pixels_y))//(pixels_y)
    x_array=numpy.linspace(0, (pixels_x)*(pixels_y)-1,
                     (pixels_x)*(pixels_y))%(pixels_y)

    #th_x=arctan((x_array-center_x)*pixelsize/detector_distance)#/2.
    #th_y=arctan((y_array-center_y)*pixelsize/detector_distance)#/2.

    #lamda=H_over_2m/sqrt(setup['ENERGY'])
    #tilt=-setup['TILT']/180.*pi
    #qx_array=2.*pi/lamda*(sin(th_x)*cos(tilt)+sin(th_y)*sin(tilt))
    #qy_array=2.*pi/lamda*(sin(th_y)*cos(tilt)-sin(th_x)*sin(tilt))
    #if setup['SWAP_YZ']:
      # swap the directions
    #  tmp=qy_array
    #  qy_array=qx_array
    #  qx_array=tmp

    #use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
    #            (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
    dataobj.data.append(PhysicalProperty('pixel_x', 'pix', x_array))
    dataobj.data.append(PhysicalProperty('pixel_y', 'pix', y_array))
    #dataobj.data.append(PhysicalProperty('Q_x', 'Å^{-1}', qx_array))
    #dataobj.data.append(PhysicalProperty('Q_y', 'Å^{-1}', qy_array))
    dataobj.data.append(PhysicalProperty('intensity', 'a.u.', data_array))
    #dataobj.data[-1].error=corrected_error
    #dataobj.data[3]=PhysicalProperty('raw_int', 'counts', data_array[use_indices])
    #dataobj.data[3].error=error_array[use_indices]

    dataobj.sample_name=sample_name
    dataobj.scan_line=0
    dataobj.scan_line_constant=1
    #dataobj.is_matrix_data=False
    dataobj.SPLIT_SENSITIVITY=0.000001
    #dataobj.setup=setup
    dataobj.short_info=self.origin[1].rsplit('.', 1)[0]
    #dataobj.logz=True
    return [dataobj]

  def read_raw_data(self):
    img=Image.open(self.raw_file)
    data_array=numpy.fromstring(img.tostring(), dtype=numpy.uint8)
    if img.mode=='RGB':
      data_array=data_array.reshape(img.size[1], img.size[0], 3).sum(axis=2)
    else:
      data_array=data_array.reshape(img.size[1], img.size[0])
    data_array=data_array.astype(numpy.float32)
    return data_array
