# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'mds' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import numpy
from baseread import BinReader
from plotpy.mds import HugeMD, PhysicalProperty
from plotpy.config import kws2 as config
from plotpy.message import in_encoding

# planck times speed of light
h_c=1.239842e4 #eV⋅Å

#class KWSReader(BinReader):
#  name=u"KWS"
#  description=u"Data measured at KWS1/KWS2 of FRM-II"
#  glob_patterns=[u'*.cmb']
#  session='gisas'

class GISASBase(object):
  '''
    Base class for GISAS readers to provide general purpose methods.
  '''

  def create_dataobj(self, start_progess=30, end_progress=100):
    delta_progress=(end_progress-start_progess)/6.
    dataobj=HugeMD([], [], 3, 4,-1, 2)
    data=self.data_array
    if hasattr(self, 'error_array'):
      error=self.error_array
    else:
      error=numpy.sqrt(data)
    if hasattr(self, 'exposure_time'):
      corrected_data=data/self.exposure_time
      corrected_error=error/self.exposure_time
      Iunit=u'counts/s'
    else:
      corrected_data=data
      corrected_error=error
      Iunit=u'counts'
    self.info(progress=start_progess+delta_progress)
    tth=0.
    k2=4.*numpy.pi/self.lambda_rays
    x_array=numpy.linspace(0, self.x_dim*self.y_dim-1, self.x_dim*self.y_dim)%self.x_dim
    self.info(progress=start_progess+2*delta_progress)
    y_array=numpy.linspace(0, self.x_dim*self.y_dim-1, self.x_dim*self.y_dim)//self.x_dim
    self.info(progress=start_progess+3*delta_progress)
    qy_array=k2*numpy.sin((numpy.arctan2((x_array-self.center_x)*self.size_x,
                               self.sample_detector_distance)+tth)/2.)
    self.info(progress=start_progess+4*delta_progress)
    qz_array=-k2*numpy.sin(numpy.arctan2((y_array-self.center_y)*self.size_y,
                               self.sample_detector_distance)/2.)
    self.info(progress=start_progess+5*delta_progress)
    if self.swap_xy:
      # swap the directions
      tmp=qz_array
      qz_array=qy_array
      qy_array=tmp
    # Insert columns
    dataobj.data.append(PhysicalProperty(u'pixel_x', u'pix', x_array).astype(numpy.int16))
    dataobj.data.append(PhysicalProperty(u'pixel_y', u'pix', y_array).astype(numpy.int16))
    dataobj.data.append(PhysicalProperty(u'intensity', Iunit, corrected_data, corrected_error))
    dataobj.data.append(PhysicalProperty(u'Q_y', u'Å^{-1}', qy_array))
    dataobj.data.append(PhysicalProperty(u'Q_z', u'Å^{-1}', qz_array))
    dataobj.sample_name=self.sample_name
    dataobj.short_info=self.short_info
    dataobj.info=u"\n".join([item[0]+': '+item[1].strip() for item in self.header_settings])
    dataobj.scan_line=1
    dataobj.scan_line_constant=0
    dataobj.logz=True
    self.info(progress=end_progress)
    return dataobj

class EDFReader(BinReader, GISASBase):
  name=u"EDF"
  description=u"Data with ESRF .edf format from ID01 and SWING in Soleil"
  glob_patterns=[u'*.edf']
  session='gisas'

  parameters=[('background_file', ''), ('swap_xy', False),
              ('center_x', 512.), ('center_y', 512.)]
  parameter_units={
                   'background_file': 'file',
                   'center_x': 'pix',
                   'center_y': 'pix',
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction (ignored for ID01)',
                         'center_y': 'Direct beam center in y direction (ignored for ID01)',
                         } # hover text for description

  store_mds=False

  cached_background={}

  SWING_DETECTOR_SIZE_X=170.96704#mm
  SWING_DETECTOR_SIZE_Y=170.96704#mm

  def read(self):
    '''
      Read the binary .edf (european data format) file including header.
      The data is taken from many pictures and summed up. To prevent double
      import the file names already used are stored in a global list.
    '''
    if not self.read_header():
      self.warn('Wrong Header')
      return None

    self.info('Reading Data', 5)
    if not self.read_data():
      return None

    if self.background_file!='':
      self.read_background()
    else:
      self.background=None

    # subtract background
    if self.background is not None:
      self.info('Subtracting Background', 15)
      self.data_array-=self.background*self.exposure_time
    self.info('Processing Data', 20)

    return [self.create_dataobj()]


  def read_background(self):
    '''
      Read the binary .edf (european data format) file including header.
      The data is taken from many pictures and summed up. To prevent double
      import the file names already used are stored in a global list.
    '''
    if self.background_file in self.cached_background:
      self.background=self.cached_background[self.background_file]
      return
    try:
      # read the data for background
      self._read_file(self.background_file)
    except:
      self.background=None
      self.warn(u'Could not read background file %s'%self.background_file)
      return

    if not self.read_header(do_eval=False):
      self.background=None
      self.warn(u'Could not read background file %s'%self.background_file)
      return
    settings=dict(self.header_settings)
    datatype=settings['DataType']
    if 'ExposureTime' in settings:
      exposure_time=float(settings['ExposureTime'].rstrip('s (Seconds)'))
    else:
      exposure_time=float(settings['Exposure_time'].rstrip('ms'))*0.001
    bg_array=self._read_data(datatype, self.raw_data[self.head_sep+1:])
    if bg_array is not None:
      self.background=bg_array/exposure_time
      self.cached_background[self.background_file]=self.background

  def read_header(self, do_eval=True):
    '''
      Read the header of an edf file from an open file object.
    '''
    head_sep=self.raw_data.find('}')
    if head_sep<0:
      return False
    self.head_sep=head_sep+1
    header=self.raw_data[:head_sep+1]
    header_lines=header.splitlines()[1:-1]
    header_lines=map(str.strip, header_lines)
    header_lines=filter(lambda line: line!='' and "=" in line, header_lines)
    header_items=map(lambda line: line.rstrip(' ;').split('=', 1), header_lines)
    self.header_settings=map(lambda item: (item[0].strip(), item[1].strip()), header_items)
    if do_eval:
      return self.eval_header()
    return True

  def eval_header(self):
    # Read some settings
    settings=dict(self.header_settings)
    if 'ESRF_ID01_PSIC_HAI' in settings:
      self.info('Found ID01 Header')
      self.eval_header_id01(settings)
      return True
    elif 'Intensity(I11-C-C07__DT__MI_DIODE.5)' in settings:
      self.info('Found SWING Header')
      self.eval_header_swing(settings)
      return True
    else:
      return False

  def eval_header_id01(self, settings):
    self.x_dim=int(settings['Dim_1'])
    self.y_dim=int(settings['Dim_2'])
    self.sample_detector_distance=float(settings['SampleDistance'].rstrip('m'))*1000.#mm
    self.lambda_rays=float(settings['WaveLength'].rstrip('m'))*1e10# angstrom
    self.sample_name=unicode(settings['Title'].split('( hai')[0], encoding=in_encoding)
    self.exposure_time=float(settings['ExposureTime'].rstrip('s (Seconds)'))
    self.center_x=float(settings['Center_1'].rstrip('pixel'))
    self.center_y=float(settings['Center_2'].rstrip('pixel'))
    self.size_x=float(settings['PSize_1'].rstrip('m'))*1000. # mm
    self.size_y=float(settings['PSize_2'].rstrip('m'))*1000. # mm
    self.alpha_i=float(settings['ESRF_ID01_PSIC_HAI'])
    self.datatype=settings['DataType']
    self.short_info=''
    return True

  def eval_header_swing(self, settings):
    self.x_dim=int(settings['Dim_1'])
    self.y_dim=int(settings['Dim_2'])
    self.sample_detector_distance=float(settings['Distance_sample-detector'].rstrip('mm'))
    energy=float(settings['Monochromator_energy'].rstrip('keV'))*1000. # eV
    self.lambda_rays=h_c/energy
    self.sample_name=unicode(settings['Title'].split('_im_')[0], encoding=in_encoding)
    self.short_info=unicode(settings['Sample_comments'], encoding=in_encoding)
    self.exposure_time=float(settings['Exposure_time'].rstrip('ms'))*0.001
    self.size_x=self.SWING_DETECTOR_SIZE_X/float(self.x_dim)
    self.size_y=self.SWING_DETECTOR_SIZE_Y/float(self.y_dim)
    self.datatype=settings['DataType']
    return True

  def read_data(self):
    '''
      Read the header and data from one edf file.
      
      :return: array of the data and the header string.
    '''
    self.data_array=self._read_data(self.datatype, self.raw_data[self.head_sep+1:])
    if self.data_array is None:
      self.warning('Unknown data format in header: %s'%self.datatype)
      return False
    return True

  def _read_data(self, datatype, raw_data):
    #  check if file is in gzip format
    if datatype=='UnsignedShort':
      # load data as binary integer values
      data_array=numpy.fromstring(raw_data, dtype=numpy.uint16).astype(numpy.float32)
      data_array-=200.
    elif datatype=='SignedInteger':
      # load data as binary integer values
      data_array=numpy.fromstring(raw_data, dtype=numpy.int32).astype(numpy.float32)
    elif self.datatype=='FloatValue':
      # load data as binary integer values
      data_array=numpy.fromstring(raw_data, dtype=numpy.float32)
    else:
      return None
    return data_array

class P08Reader(BinReader, GISASBase):
  name=u"P08"
  description=u"Data measured at P08 of PETRA-III with CCD camera"
  glob_patterns=[u'*.bin']
  session='gisas'

  parameters=[('background_file', ''), ('swap_xy', False),
              ('center_x', 2048.), ('center_y', 2048.),
              ('sample_detector_distance', 1000.),
              ('join_pixels', 4), ('lambda_rays', 1.54),
              ]
  parameter_units={
                   'background_file': 'file',
                   'center_x': 'pix',
                   'center_y': 'pix',
                   'sample_detector_distance': 'mm',
                   'join_pixels': 'pix',
                   'lambda_rays': u'Å',
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction',
                         'center_y': 'Direct beam center in y direction',
                         } # hover text for description

  store_mds=False

  def read(self):
    while 4096%self.join_pixels!=0:
      self.join_pixels-=1
    self.size_x=0.015*self.join_pixels#mm
    self.size_y=0.015*self.join_pixels#mm
    self.sample_name=self.origin[0].rsplit(u'.bin', 1)[0]
    self.short_info=''
    self.center_x=self.center_x/self.join_pixels
    self.center_y=self.center_y/self.join_pixels
    self.x_dim=4096/self.join_pixels
    self.y_dim=4096/self.join_pixels
    # read the data
    self.info(u'Reading Data', 5)
    self.read_binary_data()
    if self.background_file!='':
      self.info(u'Subtracting Background', 15)
      pass
    # adding up pixels
    if self.join_pixels>1:
      self.info(u'Joining %ix%i pixels'%(self.join_pixels, self.join_pixels), 20)
      # fast rebinning by reshaping the 2D array to 4D and summing over two dimensions
      self.data_array=self.data_array.reshape(4096/self.join_pixels,
                                              self.join_pixels,
                                              4096/self.join_pixels,
                                              self.join_pixels)
      self.data_array=self.data_array.sum(axis=1).sum(axis=2).flatten()
      progress=40
    else:
      self.data_array=self.data_array.flatten()
      self.info(progress=20)
      progress=20

    dataobj=self.create_dataobj(start_progess=progress)
    dataobj.data[0]*=self.join_pixels
    dataobj.data[1]*=self.join_pixels
    return [dataobj]

  def read_binary_data(self):
    '''
      Read the raw data of p08 file.
    '''
    #header=self.raw_data[:216]
    data=numpy.fromstring(self.raw_data[216:], numpy.uint16).reshape(4096, 4096)
    self.data_array=data.astype(numpy.float32)
    self.header_settings=[]
    return True

class ImageReader(BinReader, GISASBase):
  name=u"GISAS Image"
  description=u"Read normal image formats as GISAS measurements"
  glob_patterns=[u'*.png', u'*.bmp', u'*.tif']
  session='gisas'

  parameters=[('background_file', ''), ('swap_xy', False),
              ('center_x', 512.), ('center_y', 512.),
              ('detector_size_x', 100.), ('detector_size_y', 100.),
              ('sample_detector_distance', 1000.),
              ('exposure_time', 1.), ('lambda_rays', 1.54),
              ]
  parameter_units={
                   'background_file': 'file',
                   'center_x': 'pix',
                   'center_y': 'pix',
                   'detector_size_x': 'mm',
                   'detector_size_y': 'mm',
                   'sample_detector_distance': 'mm',
                   'exposure_time': 's',
                   'lambda_rays': u'Å',
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction (ignored for ID01)',
                         'center_y': 'Direct beam center in y direction (ignored for ID01)',

                         } # hover text for description

  store_mds=False

  def __init__(self):
    global Image
    # use PIL image readout
    import Image
    # py2exe hack
    import PngImagePlugin, TiffImagePlugin, BmpImagePlugin #@UnusedImport
    Image._initialized=2

  def read(self):
    '''
      Read a tif datafile.
    '''

    self.info('Read Image Data', 5)
    # read the data
    if not self.read_image_data():
      return None
    self.info('Process Data', 33)

    if self.data_array[0]==255:
      self.data_array=255-self.data_array
    self.size_x=self.detector_size_x/self.x_dim
    self.size_y=self.detector_size_y/self.y_dim
    self.header_settings=[]
    self.sample_name=''
    self.short_info=''

    if self.background_file!='':
      pass

    return [self.create_dataobj()]

  def read_image_data(self):
    img=Image.open(self.raw_file)
    if img.mode in ['P', 'L', 'RGB', 'RGBA']:
      dtype=numpy.uint8
    elif img.mode=='I':
      dtype=numpy.int32
    elif img.mode=='F':
      dtype=numpy.float32
    else:
      self.warn(u'Unknown color format %s'%img.mode)
      return False
    data_array=numpy.fromstring(img.tostring(), dtype=dtype)
    data_array=data_array.reshape(img.size[0], img.size[1],-1)
    data_array=data_array.astype(numpy.float32).sum(axis=2)
    self.x_dim, self.y_dim=data_array.shape
    self.data_array=data_array.flatten()
    return True

class MatReader(BinReader, GISASBase):
  name=u"Matlab 2D Image"
  description=u"Read matlab files used at B1 from HASYlab"
  glob_patterns=[u'*.mat']
  session='gisas'

  parameters=[('background_file', ''), ('detector_sensitivity', ''),
              ('swap_xy', False),
              ('center_x', 512.), ('center_y', 512.),
              ('detector_size_x', 100.), ('detector_size_y', 100.),
              ('sample_detector_distance', 1000.),
              ('exposure_time', 1.), ('lambda_rays', 1.54),
              ]
  parameter_units={
                   'background_file': 'file',
                   'detector_sensitivity': 'file',
                   'center_x': 'pix',
                   'center_y': 'pix',
                   'detector_size_x': 'mm',
                   'detector_size_y': 'mm',
                   'sample_detector_distance': 'mm',
                   'exposure_time': 's',
                   'lambda_rays': u'Å',
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction (ignored for ID01)',
                         'center_y': 'Direct beam center in y direction (ignored for ID01)',

                         } # hover text for description

  store_mds=False

  def __init__(self):
    global loadmat
    from scipy.io import loadmat #@UnusedImport

  def read(self):
    self.info('Reading Data', 5)
    if not self.read_raw_data():
      self.warn('No valid file for B1')
      return None
    if self.background_file!='':
      pass
    if self.detector_sensitivity!='':
      pass
    self.y_dim, self.x_dim=self.data_array.shape
    self.data_array=self.data_array.flatten()
    self.error_array=self.error_array.flatten()

    self.size_x=self.detector_size_x/self.x_dim
    self.size_y=self.detector_size_y/self.y_dim
    self.header_settings=[]
    self.sample_name=''
    self.short_info=''

    return [self.create_dataobj()]

  def read_raw_data(self):
    file_data=loadmat(self.raw_file)
    if 'Intensity' in file_data and 'Error' in file_data:
      self.data_array=file_data['Intensity']
      self.error_array=file_data['Error']
      return True
    else:
      return False

def read_data(file_name):
  '''
    Read the data of a kws2 data file.
    
    :param file_name: The name of the file to import
    
    :return: MeasurementData object with the file data
  '''
  if file_name.endswith('.cmb') or file_name.endswith('.cmb.gz'):
    #gnuplot_preferences.plotting_parameters_3d='w points palette pt 5'
    return read_cmb_file(file_name)
  elif file_name.endswith('.mat'):
    return read_mat_data(file_name)
  if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
    read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  if setup['BACKGROUND'] and not setup['BACKGROUND'] in detector_sensitivities:
    read_background(folder, setup['BACKGROUND'])
  lines=file_handler.readlines()
  header_lines=lines[:config.HEADER]
  countingtime=read_countingtime(header_lines)
  data_lines=lines[config.HEADER:]
  file_handler.close()
  output=create_dataobj(data_lines, header_lines, countingtime, setup)
  output.short_info=os.path.split(file_name)[1]

  return [output]

def read_countingtime(lines):
  '''
    Extract the countingtime from the file header.
  '''
  for i, line in enumerate(lines):
    if 'Real measurement time for detector data' in line:
      return float(lines[i+1].split()[0])

def create_dataobj(data_lines, header_lines, countingtime, setup):
  '''
    Create a MeasurementData object form the input datalines.
  '''
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'],
                           ['Q_y', 'Å^{-1}'], ['Q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']],
                            [], 4, 5, 3, 2)
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  y_array=array([i%config.PIXEL_X for i in range(config.PIXEL_X**2)])
  z_array=array([i/config.PIXEL_X for i in range(config.PIXEL_X**2)])
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  if setup['BACKGROUND']:
    print "\tcorrecting for background"
    corrected_data-=background_data[setup['BACKGROUND']][0]
    corrected_error=sqrt(corrected_error**2+background_data[setup['BACKGROUND']][1]**2)
    if setup['BACKGROUND']:
      print "\tcorrecting for detector sensitivity"
      ds=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]-\
                        background_data[setup['BACKGROUND']][0]
      ds/=ds.mean()
      corrected_data/=ds
      corrected_error/=ds
  elif setup['DETECTOR_SENSITIVITY']:
    print "\tcorrecting for detector sensitivity"
    ds=detector_sensitivities[setup['DETECTOR_SENSITIVITY']]
    ds/=ds.mean()
    corrected_data/=ds
    corrected_error/=ds
  if 'LAMBDA_N' in setup:
    lambda_n=setup['LAMBDA_N']
  else:
    lambda_n=config.LAMBDA_N
  qy_array=4.*pi/lambda_n*\
           sin(arctan((y_array-setup['CENTER_X'])*config.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  qz_array=4.*pi/lambda_n*\
           sin(arctan((z_array-setup['CENTER_Y'])*config.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  if setup['SWAP_YZ']:
    # swap the directions
    tmp=qz_array
    qz_array=qy_array
    qy_array=tmp
  for i in range(config.PIXEL_X**2):
    dataobj.append((y_array[i], z_array[i], corrected_data[i], corrected_error[i],
                    qy_array[i], qz_array[i], data_array[i], error_array[i]))
  return dataobj

def read_sensitivities(folder, name):
  '''
    Read data from the sensitivity file.
  '''
  global detector_sensitivities
  print "\treading detector sesitivity from %s"%name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.HEADER])
  data_lines=lines[config.HEADER:]
  file_handler.close()
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  # take at minimum 0.5 counts for the sensitivity
  data_array=maximum(0.5, data_array)
  detector_sensitivities[name]=data_array/countingtime

def read_background(folder, name):
  '''
    Read data from the background file.
  '''
  global background_data
  print "\treading background data from %s"%name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.HEADER])
  data_lines=lines[config.HEADER:]
  file_handler.close()
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  # normalize to get about the same cps values
  error_array=sqrt(data_array)
  background_data[name]=(data_array/countingtime, error_array/countingtime)

def read_cmb_file(file_name):
  '''
    Read the binary .cmb file format.
  '''
  if '.cmb-' in file_name or '.cmb.gz-' in file_name:
    folder, combname=os.path.split(file_name)
    if '.cmb-' in file_name:
      first_name, last_name=combname.split('.cmb-')
      first_name=first_name+'.cmb'
    else:
      first_name, last_name=combname.split('.cmb.gz-')
      first_name=first_name+'.cmb.gz'
    first_name=os.path.join(folder, first_name)
    last_name=os.path.join(folder, last_name)
    files=glob(os.path.join(folder, '*.cmb'))+\
          glob(os.path.join(folder, '*.cmb.gz'))
    files.sort()
    if not (first_name in files and last_name in files):
      print '\t%s and/or %s not found'
      return 'NULL'
    first_idx=files.index(first_name)
    last_idx=files.index(last_name)
    file_names=files[first_idx:last_idx+1]
  else:
    if not os.path.exists(file_name):
      print 'File '+file_name+' does not exist.'
      return 'NULL'
    file_names=[file_name]
  return read_cmb_files(file_names)

def read_cmb_files(file_names):
  '''
    Read a list of .cmb files and sum them up in one dataset.
  '''
  # Read configurations
  folder, rel_file_name=os.path.split(os.path.realpath(file_names[0]))
  setups=ConfigObj(os.path.join(folder, 'gisas_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  sys.stdout.write("\tReading...\n")
  sys.stdout.flush()
  detector_distance=setup['DETECTOR_DISTANCE']#1435. #mm
  pixelsize_x=0.2171 #mm
  pixelsize_y=0.2071 #mm
  center_x=setup['CENTER_X'] #345. pix
  center_y=setup['CENTER_Y'] #498.5 pix
  lambda_x=setup['LAMBDA_N'] #1.54
  q_window=[-10., 10.,-10., 10.]
  dataobj=HugeMD([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'],
                           ['Q_y', 'Å^{-1}'], ['Q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']],
                            [], 4, 5, 3, 2)
  data_array=None
  countingtime=0.
  for i, file_name in enumerate(file_names):
    if len(file_names)>1:
      sys.stdout.write("\b\b\b% 3i"%i)
      sys.stdout.flush()
    sample_name=''
    if file_name.endswith('.gz'):
      file_handler=gzip.open(file_name, 'rb')
    else:
      file_handler=open(file_name, 'rb')
    header=file_handler.read(256) #@UnusedVariable
    file_handler.read(256)
    raw_array=array_module.array('i')
    raw_array.fromfile(file_handler, 1024**2)
    # read additional info from end of file
    lines=file_handler.readlines()
    for line in lines:
      if line.startswith('#sca'):
        countingtime+=float(line.split()[1])
      #elif line.startswith('#dst'):
      #  detector_distance=float(line.split()[1])
      elif line.startswith('#txt'):
        sample_name+=" ".join(line.split()[1:])
      elif line.startswith('#lam'):
        lambda_x=float(line.split()[1])
    data_arrayi=array(raw_array)
    if data_array is None:
      data_array=data_arrayi
    else:
      data_array+=data_arrayi
  sys.stdout.write("\b\b\b done!\n\tProcessing...")
  sys.stdout.flush()
  z_array=linspace(0, 1024**2-1, 1024**2)%1024
  y_array=linspace(0, 1024**2-1, 1024**2)//1024
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  qy_array=4.*pi/lambda_x*\
           sin(arctan((y_array-center_y)*pixelsize_y/detector_distance)/2.)
  qz_array=4.*pi/lambda_x*\
           sin(arctan((z_array-center_x)*pixelsize_x/detector_distance)/2.)
  if setup['SWAP_YZ']:
    # swap the directions
    tmp=qz_array
    qz_array=qy_array
    qy_array=tmp

  use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
  dataobj.data[0].values=z_array[use_indices].tolist()
  dataobj.data[1].values=y_array[use_indices].tolist()
  dataobj.data[2].values=corrected_data[use_indices].tolist()
  dataobj.data[3].values=corrected_error[use_indices].tolist()
  dataobj.data[4].values=qy_array[use_indices].tolist()
  dataobj.data[5].values=qz_array[use_indices].tolist()
  dataobj.data[6].values=data_array[use_indices].tolist()
  dataobj.data[7].values=error_array[use_indices].tolist()

  dataobj.sample_name=sample_name
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  dataobj.logz=True
  sys.stdout.write("\b\b\b done!\n")
  sys.stdout.flush()
  return [dataobj]

