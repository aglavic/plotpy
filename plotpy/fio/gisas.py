# -*- encoding: utf-8 -*-
'''
  Collection of different GISAS file formats (2D detector images).
  The default xy-axes are Qy and Qz.
'''

# Pleas do not make any changes here unless you know what you are doing.
import numpy
from baseread import BinReader, TextReader
from plotpy.mds import HugeMD, PhysicalProperty, MeasurementData

# planck times speed of light
h_c=1.239842e4 #eV⋅Å

class GISASBase(object):
  '''
    Base class for GISAS readers to provide general purpose methods.
  '''
  object_creator=HugeMD
  # store background and sensitivity data for faster reuse
  _background_cache={}
  _sensitivity_cache={}

  def create_dataobj(self, start_progess=30, end_progress=100):
    '''
      Creat a HugeMD object for the data
    '''
    self.info('Processing Data', start_progess)
    steps=4.
    if self.background_file!='':
      steps+=1
    if self.detector_sensitivity!='':
      steps+=1
    delta_progress=(end_progress-start_progess)/steps
    step=1
    # if no error was read, take sqrt of data as error
    if getattr(self, 'error_array', None) is None:
      self.error_array=numpy.minimum(1., numpy.sqrt(self.data_array))
    # make corrections to data
    if self.background_file!='':
      self.info(u'Background Subtraction')
      self.correct_background()
      self.info(progress=start_progess+step*delta_progress)
      step+=1
    if self.detector_sensitivity!='':
      self.info(u'Sensitivity Correction')
      self.correct_sensitivity()
      self.info(progress=start_progess+step*delta_progress)
    # create object and collect data
    dataobj=self.object_creator([], [], 3, 4,-1, 2)
    data=self.data_array
    error=self.error_array
    if hasattr(self, 'exposure_time'):
      corrected_data=data/self.exposure_time
      corrected_error=error/self.exposure_time
      Iunit=u'counts/s'
    else:
      corrected_data=data
      corrected_error=error
      Iunit=u'counts'
    self.info(progress=start_progess+(steps-3)*delta_progress)
    tth=0.
    # calculate Q positions
    k2=4.*numpy.pi/self.lambda_rays
    x_array=numpy.linspace(0, self.x_dim*self.y_dim-1, self.x_dim*self.y_dim)%self.x_dim
    y_array=numpy.linspace(0, self.x_dim*self.y_dim-1, self.x_dim*self.y_dim)//self.x_dim
    qy_array=k2*numpy.sin((numpy.arctan2((x_array-self.center_x)*self.size_x,
                               self.sample_detector_distance)+tth)/2.)
    self.info(progress=start_progess+(steps-2)*delta_progress)
    qz_array=-k2*numpy.sin(numpy.arctan2((y_array-self.center_y)*self.size_y,
                               self.sample_detector_distance)/2.)
    self.info(progress=start_progess+(steps-1)*delta_progress)
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

  def correct_background(self):
    '''
      General background correction function.
      For this to work the read_raw_data method has to be
      defined in a subclass.
    '''
    bgfile=self.background_file
    if bgfile in self._background_cache:
      bg, bgerror=self._background_cache[bgfile]
    else:
      bg, bgerror=self.read_raw_data(bgfile)
      self._background_cache[bgfile]=(bg, bgerror)
    if not bg.shape==self.data_array.shape:
      self.warn('Could not subtract background, shape mismatch')
      return
    self.data_array-=bg*self.exposure_time
    self.error_array=numpy.sqrt(self.error_array**2+(bgerror*self.exposure_time)**2)

  def read_raw_data(self, filename):
    '''
      Default implementation of read_raw_data stores information
      needed later for object creation and than calls read_header
      and read_data.
      The raw data is than returned and saved settings restored.
    '''
    data, error=self.data_array, self.error_array
    pos_params=(self.x_dim, self.y_dim,
                self.size_x, self.size_y,
                self.center_x, self.center_y,
                self.sample_detector_distance)
    misc_params=self.exposure_time, self.swap_xy, self.sample_name, self.short_info
    # read file
    self.data_array=None
    self.error_array=None
    self._read_file(filename)
    self.read_header()
    self.read_data()
    if getattr(self, 'error_array', None) is None:
      self.error_array=numpy.minimum(1., numpy.sqrt(self.data_array))
    raw_data=self.data_array/self.exposure_time
    raw_error=self.error_array/self.exposure_time
    # restor params
    self.data_array, self.error_array=data, error
    (self.x_dim, self.y_dim,
      self.size_x, self.size_y,
      self.center_x, self.center_y,
      self.sample_detector_distance)=pos_params
    self.exposure_time, self.swap_xy, self.sample_name, self.short_info=misc_params
    return raw_data, raw_error

  def read_header(self):
    '''
      If filetype has no header to read.
    '''
    return True

  def correct_sensitivity(self):
    '''
      General background correction function.
      For this to work the read_background method has to be
      defined in a subclass.
    '''
    sfile=self.detector_sensitivity
    if sfile in self._sensitivity_cache:
      s, serror=self._sensitivity_cache[sfile]
    else:
      s, serror=self.read_raw_data(sfile)
      smean=s.mean()
      s, serror=s/smean, serror/smean
      self._sensitivity_cache[sfile]=(s, serror)
    if not s.shape==self.data_array.shape:
      self.warn('Could not correct sensitivity, shape mismatch')
      return
    #self.error_array=numpy.sqrt(self.error_array**2+serror**2)
    self.data_array/=s

class EDFReader(BinReader, GISASBase):
  name=u"EDF"
  description=u"Data with ESRF .edf format from ID01 and SWING in Soleil"
  glob_patterns=[u'*.edf']
  session='gisas'

  parameters=[('background_file', ''), ('detector_sensitivity', ''),
              ('swap_xy', False),
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
  allow_multiread=True

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

    return [self.create_dataobj(start_progess=50.)]

  def read_header(self, do_eval=True, echo=True):
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
      return self.eval_header(echo=echo)
    return True

  def eval_header(self, echo):
    # Read some settings
    settings=dict(self.header_settings)
    if 'ESRF_ID01_PSIC_HAI' in settings:
      if echo:
        self.info('Found ID01 Header')
      self.eval_header_id01(settings)
      return True
    elif 'Intensity(I11-C-C07__DT__MI_DIODE.5)' in settings:
      if echo:
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
    self.sample_name=unicode(settings['Title'].split('( hai')[0], encoding='latin1')
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
    self.sample_name=unicode(settings['Title'].split('_im_')[0], encoding='latin1')
    self.short_info=unicode(settings['Sample_comments'], encoding='latin1')
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
    input_files=len(self.unread_files)+1

    offset=0
    if self.datatype=='UnsignedShort':
      dtype=numpy.uint16
      offset=200.
    elif self.datatype=='SignedInteger':
      dtype=numpy.uint32
    elif self.datatype=='FloatValue':
      dtype=numpy.float32
    else:
      self.warning('Unknown data format in header: %s'%self.datatype)
      return False
    data_array=numpy.fromstring(self.raw_data[self.head_sep+1:],
                                dtype=dtype).astype(numpy.float32)-offset
    exposure_time=self.exposure_time
    for i in range(input_files-1):
      self.info(progress=10+i*40./input_files)
      # add data from additional files
      self.next()
      self.read_header(self, echo=False)
      exposure_time+=self.exposure_time
      data_array+=numpy.fromstring(self.raw_data[self.head_sep+1:],
                                dtype=dtype).astype(numpy.float32)-offset
    self.data_array=data_array
    self.exposure_time=exposure_time
    return True

class P08Reader(BinReader, GISASBase):
  name=u"P08"
  description=u"Data measured at P08 of PETRA-III with CCD camera"
  glob_patterns=[u'*.bin']
  session='gisas'

  parameters=[('background_file', ''), ('detector_sensitivity', ''),
              ('swap_xy', False),
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
  allow_multiread=True

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
    self.read_data()

    dataobj=self.create_dataobj()
    dataobj.data[0]*=self.join_pixels
    dataobj.data[1]*=self.join_pixels
    return [dataobj]

  def read_data(self):
    '''
      Read the raw data of p08 file.
    '''
    self.header_settings=[]
    #header=self.raw_data[:216]
    data=numpy.fromstring(self.raw_data[216:], numpy.uint16).astype(numpy.float32)
    input_files=len(self.unread_files)
    for i in range(input_files):
      self.info(progress=10+i*20./input_files)
      # add more files
      self.next()
      data+=numpy.fromstring(self.raw_data[216:], numpy.uint16).astype(numpy.float32)
    self.data_array=data.reshape(4096, 4096)

    # adding up pixels
    if self.join_pixels>1:
      # fast rebinning by reshaping the 2D array to 4D and summing over two dimensions
      self.data_array=self.data_array.reshape(4096/self.join_pixels,
                                              self.join_pixels,
                                              4096/self.join_pixels,
                                              self.join_pixels)
      self.data_array=self.data_array.sum(axis=1).sum(axis=2).flatten()
    else:
      self.data_array=self.data_array.flatten()
    return True

class ImageReader(BinReader, GISASBase):
  name=u"GISAS Image"
  description=u"Read normal image formats as GISAS measurements"
  glob_patterns=[u'*.png', u'*.bmp', u'*.tif']
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
    if not self.read_data():
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

  def read_data(self):
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
    if not self.read_data():
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

  def read_data(self):
    file_data=loadmat(self.raw_file)
    if 'Intensity' in file_data and 'Error' in file_data:
      self.data_array=file_data['Intensity']
      self.error_array=file_data['Error']
      return True
    else:
      return False

class CMBReader(BinReader, GISASBase):
  name=u"CMB"
  description=u"Read cmb binary files"
  glob_patterns=[u'*.cmb']
  session='gisas'

  parameters=[('background_file', ''), ('detector_sensitivity', ''),
              ('swap_xy', True),
              ('center_x', 512.), ('center_y', 512.),
              ('sample_detector_distance', 1400.),
              ]
  parameter_units={
                   'background_file': 'file',
                   'detector_sensitivity': 'file',
                   'center_x': 'pix',
                   'center_y': 'pix',
                   'sample_detector_distance': 'mm',
                   }
  parameter_description={
                         'swap_xy': 'Switch x- and y-axes',
                         'center_x': 'Direct beam center in x direction (ignored for ID01)',
                         'center_y': 'Direct beam center in y direction (ignored for ID01)',

                         } # hover text for description

  store_mds=False

  def read(self):
    self.sample_name=self.origin[1].rsplit('.', 1)[0]
    self.short_info=''
    if not self.read_data(False):
      self.warn('No valid file for cmb')
      return None
    if self.background_file!='':
      pass
    if self.detector_sensitivity!='':
      pass

    self.info('Process Data', 33)
    self.size_x=0.2171 #mm
    self.size_y=0.2071 #mm

    self.header_settings=[]

    return [self.create_dataobj()]

  def read_data(self, silent=True):
    if not silent:
      self.info('Processing Header', 5)
    header=self.raw_data[:512]
    if not (header.startswith('HCI data file')
            and 'Channels X =' in header
            and 'Channels Y =' in header):
      self.warn('Wrong file header')
      return False
    if not silent:
      self.info('Reading Data', 10)
    # reading dimensions and raw data
    self.x_dim=int(header.split('Channels X =', 1)[1].split('\n', 1)[0])
    self.y_dim=int(header.split('Channels Y =', 1)[1].split('\n', 1)[0])
    self.data_array=numpy.fromstring(self.raw_data[512:512+4*self.x_dim*self.y_dim],
                                     dtype=numpy.int32).astype(numpy.float32)
    # read additional info from end of file
    if not silent:
      self.info('Processing Info', 20)
    info_lines=self.raw_data[512+4*self.x_dim*self.y_dim:].splitlines()
    start_time=0.
    end_time=1.
    for line in info_lines:
      if line.startswith('#sca'):
        self.exposure_time=float(line.split()[1])
      #elif line.startswith('#dst'):
      #  detector_distance=float(line.split()[1])
      elif line.startswith('#txt'):
        ls=line.split(None, 1)
        if len(ls)>1:
          self.short_info=unicode(ls[1].strip(), encoding='latin1')
      elif line.startswith('#lam'):
        self.lambda_rays=float(line.split()[1])
      elif line.startswith('#sdt') and 'Epoch time:' in line:
        start_time=float(line.split('Epoch time:')[1])
      elif line.startswith('#edt') and 'Epoch time:' in line:
        end_time=float(line.split('Epoch time:')[1])
    self.exposure_time=end_time-start_time
    return True

class KWSReader(TextReader, GISASBase):
  name=u"KWS"
  description=u"Data measured at KWS1/KWS2 of FRM-II"
  glob_patterns=[u'*.dat']
  session='gisas'

  parameters=[('background_file', ''), ('detector_sensitivity', ''),
              ('swap_xy', False),
              ('center_x', 64.), ('center_y', 64.),
              ('detector_size_x', 600.), ('detector_size_y', 600.),
              ('sample_detector_distance', 2000.),
              ('exposure_time', 1.), ('lambda_rays', 4.51),
              ]
  parameter_units={
                   'background_file': 'file(*.dat)',
                   'detector_sensitivity': 'file(*.dat)',
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
  object_creator=MeasurementData

  def read(self):
    '''
      Read the data of a kws2 data file.
      
      :param file_name: The name of the file to import
      
      :return: MeasurementData object with the file data
    '''
    if not self.read_header():
      self.warn('No valid KWS file format')
      return None

    self.read_data()
    self.sample_name=self.origin[1].rsplit('.', 1)[0]
    self.short_info=''
    self.size_x=self.detector_size_x/self.x_dim
    self.size_y=self.detector_size_y/self.y_dim

    return [self.create_dataobj()]

  def read_header(self):
    if not (self.text_data[:16]==u'KWS1_MEASUREMENT' or
            self.text_data[:16]==u'KWS2_MEASUREMENT'):
      self.warn('Wrong file header')
      return False
    self.head_sep=self.text_data.find('$')
    head=self.text_data[:self.head_sep]
    head_blocks=head.split('(*')
    block_info=[('fileinfo', head_blocks[0])]
    for block in head_blocks:
      block_split=block.split('*)')
      if len(block_split)>1:
        block_desc, block_bulk=block_split
      else:
        block_desc=block_split[0]
        block_bulk=''
      block_info.append((block_desc.strip(), block_bulk.strip()))
    self.header_settings=block_info
    settings=dict(block_info)
    if 'Real measurement time for detector data' in settings:
      self.exposure_time=float(settings['Real measurement time for detector data'].split()[0])
    return True

  def read_data(self):
    data_string=self.text_data[self.head_sep+1:]
    self.data_array=numpy.fromstring(data_string, sep=' ', dtype=numpy.float32)
    self.x_dim=numpy.sqrt(self.data_array.shape[0])
    self.y_dim=self.x_dim
