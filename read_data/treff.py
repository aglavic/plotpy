# -*- encoding: utf-8 -*-
'''
  Functions to read from treff data and .img. files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
  Image files can be gziped or plain.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import math
import numpy
from copy import deepcopy
from measurement_data_structure import MeasurementData
from config.treff import GRAD_TO_MRAD, DETECTOR_ROWS_MAP, PI_4_OVER_LAMBDA, GRAD_TO_RAD, \
                          PIXEL_WIDTH, DETECTOR_PIXELS,CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION
from zipfile import ZipFile

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.7beta7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

MARIA_REDUCE_RESOLUTION=False

class MeasurementDataTREFF(MeasurementData):
  '''
    Treff measurement data class, defining functions
    to combine two sets of measurements.
  '''
  
  def __init__(self, *args, **opts):
    MeasurementData.__init__(self, *args, **opts)
  
  def join(self, other, join_type=0):
    '''
      Append the data of an other object to this object.
      
      @param join_type Tell function which objects parameters to use, if there is a conflict. 0=this, 1=other, -1=both
      
      @return Another MeasurementDataTREFF instance.
    '''
    if self.zdata!=other.zdata:
      return None
    if self.zdata>=0:
      return self.join3d(other, join_type)
    if join_type==1:
      new=deepcopy(other)
      add_obj=self
    else:
      new=deepcopy(self)
      add_obj=other
    xdata=new.data[0].values
    for point in add_obj:
      if point[0] in xdata and not join_type==-1:
        continue
      else:
        new.append(point)
    return new

  def join3d(self, other, join_type):
    '''
      Append the data of an other object to this object, called if self is a 3d dataset.
      
      @param join_type Tell function which objects parameters to use, if there is a conflict. 0=this, 1=other, -1=both
      
      @return Another MeasurementDataTREFF instance.
    '''
    if join_type==1:
      new=deepcopy(other)
      add_obj=self
    else:
      new=deepcopy(self)
      add_obj=other
    xydata=["%f,%f" % (new.data[0].values[i], new.data[1].values[i]) for i in range(len(new.data[0].values))]
    for point in add_obj:
      if "%f,%f" % (point[0], point[1]) in xydata:
        continue
      new.append(point)
    return new

def read_data(file_name, script_path, import_images, return_detector_images):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
    
    @param file_name Name of the file to import
    @param script_path Path of the plot scripts to get the treff calibration file
    @param import_images Boolian to select if only the datafile should be imported or the 2d-detector images, too
    
    @return List of MeasurementData objects for the 2d maps and scans splitted by polarization channels
  '''
  # reset parameters, if maria image was imported before
  global DETECTOR_ROWS_MAP, DETECTOR_PIXELS, PIXEL_WIDTH, CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION, PI_4_OVER_LAMBDA
  from config.treff import DETECTOR_ROWS_MAP, DETECTOR_PIXELS, PIXEL_WIDTH, CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION, PI_4_OVER_LAMBDA
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  if file_name.endswith('.zip'):
    # All data is stored in one zip file, open the files in the zip file
    treff_zip=ZipFile(file_name)
    realfile_name=file_name
    file_name=os.path.split(file_name[:-4])[1]
    file_handler=treff_zip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
    treff_zip=None
  lines=file_handler.readlines()
  file_handler.close()
  if len(lines)<5:
    print 'Not a valid datafile, skipped.'
    return 'NULL'
  # devide comment lines from data lines
  lines_columns=map(str.split, lines)
  comments=map(string_or_float, lines_columns)
  headers=filter(lambda i: not comments[lines_columns.index(i)], lines_columns)
  footers=headers[comments.index(True):]
  for hl in headers:
    if len(hl)>0 and hl[0]=='#Scan':
      print "\tdetected as MARIA file."
      if treff_zip is not None:
        file_name=realfile_name
      return read_data_maria(file_name, script_path, import_images, return_detector_images)
  data_lines=filter(lambda i: comments[lines_columns.index(i)], lines_columns)
  # define the data columns
  columns_line=headers[2]
  if 'MF' in columns_line:
    columns_line.insert(columns_line.index('MF'), 'MF [G]')
    columns_line.remove('MF')
    columns_line.remove('[G]')
  # get the columns of interest
  try:
    image_col=columns_line.index('Image')
  except ValueError:
    image_col=None
    import_images=False
  columns={ 'Image': image_col, 
           'Polarization': columns_line.index('Pol.'),
           'Monitor': columns_line.index('Monitor'), 
           '2DWindow': columns_line.index('2DWind.'), 
           'DetectorTotal': columns_line.index('2DTotal'), 
           'Time': columns_line.index('Time'), 
           'omega': -1, 
           'detector': -1
           }
  global negative_omega
  negative_omega=False
  const_information={}
  for line in headers:
    try:
      if line[0] == 'Scan':
        columns['Scantype']=line[-1]
        if line[-1] == 'omega':
          columns['omega']=0
        elif line[-1] == 'detector' or line[-1] == 'scatteringarm':
          columns['detector']=0
        elif line[-1] == 'sampletable':
          columns['omega']=0
          negative_omega=True
        else:
          columns[line[-1]]=0
      elif line[0] == '2nd':
        if line[-1] == 'omega':
          columns['omega']=1
        elif line[-1] == 'detector':
          columns['detector']=1
        elif line[-1] == 'sampletable':
          columns['omega']=1
          negative_omega=True
      else:
        const_information[line[0]]=float(line[1])
    except IndexError:
      None
    except ValueError:
      try:
        const_information[' '.join(line[0:2])]=float(line[2])
      except:
        None
        
  # devide polarization directions
  data_uu_lines=filter(lambda line: line[columns['Polarization']]=='uu', data_lines)
  data_dd_lines=filter(lambda line: line[columns['Polarization']]=='dd', data_lines)
  data_ud_lines=filter(lambda line: line[columns['Polarization']]=='ud', data_lines)
  data_du_lines=filter(lambda line: line[columns['Polarization']]=='du', data_lines)
  data_xx_lines=filter(lambda line: line[columns['Polarization']]=='xx', data_lines)
  del(data_lines)
  # import calibration from file, need to get this as relative path
  cali_file=script_path+'config/treff_calibration.dat'
  cali_open=open(cali_file, 'r')
  calibration=map(float, cali_open.readlines())
  cali_open.close()
  # get the path of the input file for the images
  path_name=os.path.dirname(file_name)
  if len(path_name)>0:
    path_name+='/'
  #++++++++++++ evaluating images and creating data objects ++++++++++++
  maps=[]
  scans=[]
  detector_images=[]
  if len(data_uu_lines)>0:
    print "\tEvaluating up-up images."
    data_uu, scan_uu, detector_image_uu=integrate_pictures(data_uu_lines, columns, const_information, 
                                        path_name, calibration, import_images, treff_zip, return_detector_images)
    if len(data_uu)>0:
      data_uu.short_info='++ map'
      maps.append(data_uu)
    scan_uu.short_info='++'
    # filter 0 intensity points
    scan_uu.filters=[(5, 0.0, 0.0, False)]    
    scans.append(scan_uu)
    detector_images.append(detector_image_uu)
  if len(data_dd_lines)>0:
    print "\tEvaluating down-down images."
    data_dd, scan_dd, detector_image_dd=integrate_pictures(data_dd_lines, columns, const_information, 
                                        path_name, calibration, import_images, treff_zip, return_detector_images)
    if len(data_dd)>0:
      data_dd.short_info='-- map'
      maps.append(data_dd)
    scan_dd.short_info='--'
    # filter 0 intensity points
    scan_dd.filters=[(5, 0.0, 0.0, False)]    
    scans.append(scan_dd)
    detector_images.append(detector_image_dd)
  if len(data_ud_lines)>0:
    print "\tEvaluating up-down images."
    data_ud, scan_ud, detector_image_ud=integrate_pictures(data_ud_lines, columns, const_information, 
                                        path_name, calibration, import_images, treff_zip, return_detector_images)
    if len(data_ud)>0:
      data_ud.short_info='+- map'
      maps.append(data_ud)
    scan_ud.short_info='+-'
    # filter 0 intensity points
    scan_ud.filters=[(5, 0.0, 0.0, False)]    
    scans.append(scan_ud)
    detector_images.append(detector_image_ud)
  if len(data_du_lines)>0:
    print "\tEvaluating down-up images."
    data_du, scan_du, detector_image_du=integrate_pictures(data_du_lines, columns, const_information, 
                                        path_name, calibration, import_images, treff_zip, return_detector_images)
    if len(data_du)>0:
      data_du.short_info='-+ map'
      maps.append(data_du)
    scan_du.short_info='-+'
    # filter 0 intensity points
    scan_du.filters=[(5, 0.0, 0.0, False)]    
    scans.append(scan_du)
    detector_images.append(detector_image_du)
  if len(data_xx_lines)>0:
    print "\tEvaluating unpolarized images."
    data_xx, scan_xx, detector_image_xx=integrate_pictures(data_xx_lines, columns, const_information, 
                                        path_name, calibration, import_images, treff_zip, return_detector_images)
    if len(data_xx)>0:
      data_xx.short_info='unpolarized'
      maps.append(data_xx)
    scan_xx.short_info='unpolarized'
    scans.append(scan_xx)
    detector_images.append(detector_image_xx)
  for mapi in maps:
    mapi.logz=True
    mapi.plot_options='set cbrange [1e-7:]\nset zrange [1e-7:]\n'
  for scan in scans:
    scan.logy=True
  if import_images:
    output=maps + scans
  else:
    output= scans
  if treff_zip:
    # this is very importent as the zip file could be damadged otherwise!
    treff_zip.close()
  info_list=filter(lambda item: item.strip()!='', map(" ".join, footers))
  info_string="\n".join(info_list)
  for dataset in output:
    dataset.info=info_string
  if return_detector_images:
    return output, detector_images
  else:
    return output

def string_or_float(string_line):
  '''
    Short function to test if first column of a line is a float number or string.
    Used to devide Header/Comment from Data lines.
  '''
  if len(string_line)==0:
    return False
  try:
    float(string_line[0])
    return True
  except ValueError:
    return False

def integrate_pictures(data_lines, columns, const_information, data_path, calibration, 
                       import_images, treff_zip=None, return_detector_images=False):
  '''
    Integrate detector rows of the image files corresponding to one polarization direction.
    This function is tuned quite much for fast readout, so some parts are a bit tricky.
    
    @param data_lines List of lines from the inputfile which are already split by columns
    @param columns Dictionary for the interesting columns
    @param const_information Dictionary of values which are constat for the whole scan e.g. mag. field
    @param data_path Path to the image files which should be integrated
    @param calibration Calibration data for the 2d detector as List of integers
    @param import_images Boolian to select if only the datafile should be imported or the 2d-detector images, too
    @param treff_zip ZipFile object which can be used insted of the local folder to get the image files
    
    @return MeasurementData objects for the map and the scan for this polarization channel
  '''
  detector_images=[]
  sqrt=math.sqrt
  # create the data object
  scan_data_object=MeasurementDataTREFF([[columns['Scantype'], 'mrad'], 
                               ['2DWindow', 'counts'], 
                               ['DetectorTotal', 'counts'], 
                               ['error','counts'], 
                               ['errorTotal','counts'], 
                               ['Intensity','counts/Monitor'], 
                               ['error(monitor)','counts/Monitor'], 
                               ['Intensity(time)', 'counts/s'], 
                               ['error(time)','counts/s']], 
                              [], 0, 5, 6)
  data_object=MeasurementDataTREFF([['α_i', 'mrad'], 
                               ['α_f', 'mrad'], 
                               ['α_i+α_f', 'mrad'], 
                               ['α_i-α_f', 'mrad'], 
                               ['q_x', 'Å^{-1}'], 
                               ['q_z', 'Å^{-1}'], 
                               ['Intensity', 'a.u.'], 
                               ['log_{10}(Intensity)', 'a.u.'], 
                               ['error','a.u.']], 
                              [], 0, 1, 8, 6)  
  # alpha_i is used as main column for the line splitteng used for pm3d
  data_object.scan_line_constant=0
  data_object.scan_line=1
  data_list=[]
  scan_data_list=[]
  for index, line in enumerate(data_lines):
    if float(line[columns['Monitor']]) == 0.:
      continue # measurement error, nothing to do
    scan_data_list.append(map(float, (line[columns[columns['Scantype']]], 
                                      line[columns['2DWindow']], 
                                      line[columns['DetectorTotal']], 
                                      line[columns['2DWindow']], 
                                      line[columns['DetectorTotal']],
                                      line[columns['Monitor']], 
                                      line[columns['Monitor']], 
                                      line[columns['Time']], 
                                      line[columns['Time']])))
    if not (import_images  or return_detector_images):
      continue
    if treff_zip and line[columns['Image']] in treff_zip.namelist():
      # use data inside ziped file
      img_file=treff_zip.open(line[columns['Image']], 'r')
    elif treff_zip and line[columns['Image']]+'.gz' in treff_zip.namelist():
      # use data inside ziped file
      print "gziped files not supported inside of .zip file."
      continue
    elif os.path.exists(data_path + line[columns['Image']] + '.gz'):
      # gziped images
      import gzip
      img_file=gzip.open(data_path + line[columns['Image']] + '.gz', 'rb')
    elif line[columns['Image']].endswith('.gz') and os.path.exists(data_path + line[columns['Image']]):
      # gziped images
      import gzip
      img_file=gzip.open(data_path + line[columns['Image']], 'rb')
    elif os.path.exists(data_path + line[columns['Image']]):
      # unziped images
      img_file=open(data_path + line[columns['Image']], 'r')
    else:
      # no image file
      print 'Image ' + data_path + line[columns['Image']] + '(.gz) does not exist, check your files.'
      continue
    # define alphai and alphaf (for the detector center)
    if columns['omega'] >= 0:
      alphai = float(line[columns['omega']])
    else:
      alphai = const_information['omega']
    if negative_omega:
      alphai *= -1
    if columns['detector'] >= 0:
      alphaf_center = float(line[columns['detector']]) - alphai
    else:
      alphaf_center = const_information['detector'] - alphai
    # integrate the image
    detector_data, detector_image=integrate_one_picture_neu(img_file, line, columns, alphai, alphaf_center, calibration, PIXEL_WIDTH)
    data_list+=detector_data
    if return_detector_images:
      # Create object for the detector image
      imgobj=create_img_object(detector_image, alphai, alphaf_center, float(line[columns['Time']]))
      imgobj.sample_name='Detector Image '+line[columns['Image']].rsplit('.', 1)[0]
      imgobj.short_info=line[columns['Image']].rsplit('.', 1)[1]
      imgobj.number=str(index)
      # write the data of the object to a file to save memory
      imgobj.store_data()
      del(detector_image)
      detector_images.append(imgobj)
    #data_list+=integrate_one_picture(img_file, line, columns, alphai, alphaf_center, calibration, PIXEL_WIDTH)
  if import_images:  
    data_append=data_object.append
    # append the integrated data to the object
    map(data_append, data_list)
  scan_data_append=scan_data_object.append
  # sqrt of intensities is error
  def sqrt_34_gtm(point):
    point[0]=GRAD_TO_MRAD*point[0]
    point[3]=sqrt(point[3])
    point[4]=sqrt(point[4])
    point[5]=point[1]/point[5]
    point[6]=point[3]/point[6]
    point[7]=point[1]/point[7]
    point[8]=point[3]/point[8]
  map(sqrt_34_gtm, scan_data_list)
  map(scan_data_append, scan_data_list)
  return data_object, scan_data_object, detector_images

def integrate_one_picture(img_file, line, columns, alphai, alphaf_center, calibration, pixel_width):
  '''
    Map detector columns to alphai, alphaf and intensities.
    Quite optimized, too.
    
    @param img_data List of intensities from the detector
    @param line The corresponding data line from the original input file (contains e.g. Monitor counts)
    @param columns Dictionary for the interesting columns
    @param alphai Incident angle of the reflectometer
    @param alphaf_center Angle from the detector arm to the sample
    @param calibration Calibration data for the 2d detector as List of integers
    @param pixel_width Width of one pixel on the 2d detector

    @return List of 256 detector columns with corresponding angle values and errors
  '''
  # read the data of an image file and split the lines 
  img_data=img_file.read()[:-1]
  img_file.close()
  img_data=img_data.split('\n')
  sqrt=math.sqrt
  log10=math.log10
  sin=math.sin
  cos=math.cos
  data_list=[]
  # for faster function lookup
  append_to_list=data_list.append
  # every image file consists of 256 rows and 256 columns of the detector
  # as the sum function returns 0 for empty list we can remove '0' from the lists
  # to increase the speed of the integer conversion
  try:
    parts=[[img_data[i] for i in map_i if not img_data[i] is '0'] for map_i in DETECTOR_ROWS_MAP]
  except IndexError:
    return []
  monitor=float(line[columns['Monitor']])
  for i in range(len(calibration)):
    if calibration[i] <= 0 :
      continue # ignore blind spots of detector
    # convet strings into integer
    int_data=map(int, parts[i])
    img_integral=sum(int_data)
    alphaf = alphaf_center + pixel_width * (CENTER_PIXEL - i)
    intensity = img_integral / monitor * calibration[i]
    if intensity > 0:
      logintensity = log10(intensity)
    else:
      logintensity = -10.0
    error = sqrt(img_integral) / monitor * calibration[i]
    # convert to mrad and create point list.
    append_to_list((GRAD_TO_MRAD * alphai, 
                    GRAD_TO_MRAD * alphaf, 
                    GRAD_TO_MRAD * (alphai + alphaf), 
                    GRAD_TO_MRAD * (alphai - alphaf), 
                    PI_4_OVER_LAMBDA/2.*(cos(GRAD_TO_RAD * alphaf) - cos(GRAD_TO_RAD * alphai)), 
                    PI_4_OVER_LAMBDA/2.*(sin(GRAD_TO_RAD * alphai) + sin(GRAD_TO_RAD * alphaf)), 
                    intensity, 
                    logintensity, 
                    error))
  return data_list, img_data

def integrate_one_picture_neu(img_file, line, columns, alphai, alphaf_center, calibration, pixel_width):
  '''
    Map detector columns to alphai, alphaf and intensities.
    Quite optimized, too.
    
    @param img_data 2d numpy array of detector counts
    @param line The corresponding data line from the original input file (contains e.g. Monitor counts)
    @param columns Dictionary for the interesting columns
    @param alphai Incident angle of the reflectometer
    @param alphaf_center Angle from the detector arm to the sample
    @param calibration Calibration data for the 2d detector as List of integers
    @param pixel_width Width of one pixel on the 2d detector

    @return List of 256 detector columns with corresponding angle values and errors
  '''
  # read the data of an image file and split the lines 
  img_data=numpy.fromstring(img_file.read(), int, sep=" ")
  try:
    img_data=img_data.reshape(DETECTOR_PIXELS, -1)
  except ValueError:
    return []
  img_file.close()
  cos=math.cos
  sin=math.sin
  data_list=[]
  # for faster function lookup
  append_to_list=data_list.append
  monitor=float(line[columns['Monitor']])
  calibration=numpy.array(calibration)
  img_columns_data=img_data.transpose()
  img_intensities=numpy.array(map(lambda item: item.sum(), img_columns_data))
  try:
    intensities=img_intensities/monitor*calibration
  except ValueError:
    return []
  logintensities=numpy.log10(numpy.maximum(img_intensities, 0.1)/monitor*calibration)
  errors=numpy.sqrt(img_intensities)/monitor*calibration
  alphaf=[alphaf_center + pixel_width * (CENTER_PIXEL - i) for i in range(DETECTOR_PIXELS)]
  for i in range(DETECTOR_PIXELS):
    if calibration[i] <= 0 :
      continue # ignore blind spots of detector
    # convert to mrad and create point list.
    append_to_list((GRAD_TO_MRAD * alphai, 
                    GRAD_TO_MRAD * alphaf[i], 
                    GRAD_TO_MRAD * (alphai + alphaf[i]), 
                    GRAD_TO_MRAD * (alphai - alphaf[i]), 
                    PI_4_OVER_LAMBDA/2.*(cos(GRAD_TO_RAD * alphaf[i]) - cos(GRAD_TO_RAD * alphai)), 
                    PI_4_OVER_LAMBDA/2.*(sin(GRAD_TO_RAD * alphai) + sin(GRAD_TO_RAD * alphaf[i])), 
                    intensities[i], 
                    logintensities[i], 
                    errors[i]))
  return data_list, img_data

def read_simulation(file_name):
  '''
    Read a pnr_multi output file as MeasurementData object.
    
    @return One MeasurementData object
  '''
  sim_file=open(file_name,'r')
  sim_lines=sim_file.readlines()
  sim_file.close()
  data=MeasurementData([['Θ','mrad'],['Intensity','a.u.'],['Unknown','counts/s'],['Unknown2','counts/s']],[],0,1,2)
  data.info='Simulation'
  for line in sim_lines:
    if len(line.split())>1:
      point=map(float,line.split())
      data.append(point)
  return data

def read_data_maria(file_name, script_path, import_images, return_detector_images):
  '''
    Read the data of a maria raw data file, integrate the corresponding .img files.
    
    @param file_name Name of the file to import
    @param script_path Path of the plot scripts to get the treff calibration file
    @param import_images Boolian to select if only the datafile should be imported or the 2d-detector images, too
    
    @return List of MeasurementData objects for the 2d maps and scans splitted by polarization channels
  '''
  global DETECTOR_ROWS_MAP, DETECTOR_PIXELS, PIXEL_WIDTH, CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION
  from config.maria import DETECTOR_ROWS_MAP, COLUMNS_MAPPING,  DETECTOR_PIXELS, \
                          PIXEL_WIDTH,CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  if file_name.endswith('.zip'):
    # All data is stored in one zip file, open the files in the zip file
    maria_zip=ZipFile(file_name)
    file_name=os.path.split(file_name[:-4])[1]
    file_handler=maria_zip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
    maria_zip=None
  lines=file_handler.readlines()
  file_handler.close()
  if len(lines)<5:
    print 'Not a valid datafile, skipped.'
    return 'NULL'
  # devide comment lines from data lines
  lines_columns=map(str.split, lines)
  comments=map(string_or_float, lines_columns)
  headers=filter(lambda i: not comments[lines_columns.index(i)], lines_columns)
  data_lines=filter(lambda i: comments[lines_columns.index(i)], lines_columns)
  # define the data columns
  columns={}
  if headers[-1][0][0]=='#' and headers[-1][0].strip()!='#':
    headers[-1].insert(1, headers[-1][0][1:])
  columns_line=headers[-1][1:]
  for i, column in enumerate(columns_line):
    column_name=column.rsplit('[', 1)[0]
    if column_name in COLUMNS_MAPPING:
      columns[COLUMNS_MAPPING[column_name]]=i
  # get the columns of interest
  if not 'Image' in columns:
    import_images=False
  global negative_omega
  negative_omega=False
  const_information={}
  for i, line in enumerate(headers):
    if ['#Scan','command','arguments:'] == line:
      arguments=" ".join(headers[i+1]).split('+-')[1].split()
      arguments=map(lambda item: item.replace('[', '').replace(']', ''), arguments)
      if 'omega' in arguments:
        columns['Scantype']='omega'
      else:
        if arguments[0] in COLUMNS_MAPPING:
          columns['Scantype']=COLUMNS_MAPPING[arguments[0]]
        else:
          columns['Scantype']=COLUMNS_MAPPING['Time[sec]']
      break

  if 'Wavelength' in columns:
    global PI_4_OVER_LAMBDA
    lambda_n=float(data_lines[0][columns['Wavelength']])
    PI_4_OVER_LAMBDA=4*numpy.pi/lambda_n

  if import_images:
    # remove .gz from image columns
    for i, line in enumerate(data_lines):
      try:
        data_lines[i][columns['Image']]=os.path.split(line[columns['Image']])[1].replace('.gz', '')
      except IndexError:
        data_lines[i][columns['Image']]=line[columns['Image']].replace('.gz', '')
  # devide polarization directions
  try:
    data_uu_lines=filter(lambda line: line[columns['PolarizerFlipped']]=='0' and line[columns['AnalyzerFlipped']]=='0', data_lines)
    data_dd_lines=filter(lambda line: line[columns['PolarizerFlipped']]=='1' and line[columns['AnalyzerFlipped']]=='1', data_lines)
    data_ud_lines=filter(lambda line: line[columns['PolarizerFlipped']]=='0' and line[columns['AnalyzerFlipped']]=='1', data_lines)
    data_du_lines=filter(lambda line: line[columns['PolarizerFlipped']]=='1' and line[columns['AnalyzerFlipped']]=='0', data_lines)
    data_xx_lines=[]
  except:
    data_uu_lines=[]
    data_dd_lines=[]
    data_ud_lines=[]
    data_du_lines=[]
    data_xx_lines=data_lines
  # import calibration from file, need to get this as relative path
  # cali_file=script_path+'config/treff_calibration.dat'
  # cali_open=open(cali_file, 'r')
  # calibration=map(float, cali_open.readlines())
  # cali_open.close()
  calibration=[1.0 for i in range(1024)]
  # get the path of the input file for the images
  path_name=os.path.dirname(file_name)
  if len(path_name)>0:
    path_name+='/'
  #++++++++++++ evaluating images and creating data objects ++++++++++++
  maps=[]
  scans=[]
  detector_images=[]
  if len(data_uu_lines)>0:
    print "\tEvaluating up-up images."
    data_uu, scan_uu, detector_image_uu=integrate_pictures(data_uu_lines, columns, const_information, 
                                        path_name, calibration, import_images, maria_zip, return_detector_images)
    if len(data_uu)>0:
      data_uu.short_info='++ map'
      maps.append(data_uu)
    scan_uu.short_info='++'
    scans.append(scan_uu)
    for image in detector_image_uu:
      image.short_info+=' - ++'
    detector_images.append(detector_image_uu)
  if len(data_dd_lines)>0:
    print "\tEvaluating down-down images."
    data_dd, scan_dd, detector_image_dd=integrate_pictures(data_dd_lines, columns, const_information, 
                                        path_name, calibration, import_images, maria_zip, return_detector_images)
    if len(data_dd)>0:
      data_dd.short_info='-- map'
      maps.append(data_dd)
    scan_dd.short_info='--'
    scans.append(scan_dd)
    for image in detector_image_dd:
      image.short_info+=' - --'
    detector_images.append(detector_image_dd)
  if len(data_ud_lines)>0:
    print "\tEvaluating up-down images."
    data_ud, scan_ud, detector_image_ud=integrate_pictures(data_ud_lines, columns, const_information, 
                                        path_name, calibration, import_images, maria_zip, return_detector_images)
    if len(data_ud)>0:
      data_ud.short_info='+- map'
      maps.append(data_ud)
    scan_ud.short_info='+-'
    scans.append(scan_ud)
    for image in detector_image_ud:
      image.short_info+=' - +-'
    detector_images.append(detector_image_ud)
  if len(data_du_lines)>0:
    print "\tEvaluating down-up images."
    data_du, scan_du, detector_image_du=integrate_pictures(data_du_lines, columns, const_information, 
                                        path_name, calibration, import_images, maria_zip, return_detector_images)
    if len(data_du)>0:
      data_du.short_info='-+ map'
      maps.append(data_du)
    scan_du.short_info='-+'
    scans.append(scan_du)
    for image in detector_image_du:
      image.short_info+=' - -+'
    detector_images.append(detector_image_du)
  if len(data_xx_lines)>0:
    print "\tEvaluating unpolarized images."
    data_xx, scan_xx, detector_image_xx=integrate_pictures(data_xx_lines, columns, const_information, 
                                        path_name, calibration, import_images, maria_zip, return_detector_images)
    if len(data_xx)>0:
      data_xx.short_info='unpolarized'
      maps.append(data_xx)
    scan_xx.short_info='unpolarized'
    scans.append(scan_xx)
    detector_images.append(detector_image_xx)
  for mapi in maps:
    mapi.logz=True
    mapi.plot_options='set cbrange [1e-4:]\nset zrange [1e-4:]\n'
  for scan in scans:
    scan.logy=True
  if import_images:
    output=maps + scans
  else:
    output= scans
  if maria_zip:
    # this is very importent as the zip file could be damadged otherwise!
    maria_zip.close()
  if return_detector_images:
    return output, detector_images
  else:
    return output

def create_img_object(data, alphai=0., alphaf_center=0., cnt_time=1.):
  '''
    Create a KWS2MeasurementData object from an detector raw data array.
  '''
  from kws2 import KWS2MeasurementData
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  # remove colmuns not part of the detector
  data_array=numpy.array(data)
  first_row, last_row, first_col, last_col=DETECTOR_REGION
  data=data_array[first_row:last_row+1, first_col:last_col+1]  
  # get pixels per row or column of remainig data
  x_array=numpy.arange((last_col-first_col+1)*(last_row-first_row+1))%(last_col-first_col+1)+first_col
  z_angle=alphai + alphaf_center + PIXEL_WIDTH * (CENTER_PIXEL - x_array)
  y_array=numpy.arange((last_col-first_col+1)*(last_row-first_row+1))/(last_col-first_col+1)+first_row
  y_angle=PIXEL_WIDTH * (CENTER_PIXEL_Y - y_array)
  q_y=PI_4_OVER_LAMBDA*numpy.sin(GRAD_TO_RAD*y_angle/2.)
  q_z=PI_4_OVER_LAMBDA*numpy.sin(GRAD_TO_RAD*z_angle/2.)
  data_array=numpy.array(data).flatten()
  error_array=numpy.sqrt(data_array)
  dataobj.number_of_points=len(data_array)
  dataobj.data[0].values=x_array.tolist()
  dataobj.data[1].values=y_array.tolist()
  dataobj.data[2].values=(data_array/cnt_time).tolist()
  dataobj.data[3].values=(error_array/cnt_time).tolist()
  dataobj.data[4].values=q_y.tolist()
  dataobj.data[5].values=q_z.tolist()
  dataobj.data[6].values=data_array.tolist()
  dataobj.data[7].values=error_array.tolist()
  min_z=numpy.where(data_array!=0, data_array/cnt_time, (data_array/cnt_time).max()).min()
  dataobj.logz=True
  dataobj.plot_options.zrange[0]=min_z
  return dataobj
  


if not getattr(ZipFile, 'open', False):
  import zipfile
  
  class ZipFileWrapper:
    '''
      Small class bahaving as filelike object for python versions < 2.6.
    '''
    
    def __init__(self, zip_object, file_name):
      self.zip_object=zip_object
      self.file_name=file_name
    
    def read(self):
      return self.zip_object.read(self.file_name)
    
    def close(self):
      pass
    
    def readlines(self):
      return self.read().splitlines()
  
  class ZipFile(zipfile.ZipFile):
    '''
      Use ZipFileWrapper for open method.
    '''
    def open(self, file_name, ignore):
      return ZipFileWrapper(self, file_name)
