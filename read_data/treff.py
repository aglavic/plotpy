# -*- encoding: utf-8 -*-
'''
  Functions to read from treff data and .img. files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
  Image files can be gziped or plain.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os, sys
import math
import numpy
from copy import deepcopy
from glob import glob
from measurement_data_structure import MeasurementData, PhysicalProperty, PhysicalConstant
from config.treff import GRAD_TO_MRAD, DETECTOR_ROWS_MAP, PI_4_OVER_LAMBDA, GRAD_TO_RAD, \
                          PIXEL_WIDTH, DETECTOR_PIXELS,CENTER_PIXEL, CENTER_PIXEL_Y, DETECTOR_REGION
from zipfile import ZipFile

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.7.4"
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
    # ignore warning from numpy.unique1d
    import warnings
    original_filters = warnings.filters[:]
    # Ignore warnings.
    warnings.simplefilter("ignore")
    
    if join_type==1:
      new=deepcopy(other)
      add_obj=self
    else:
      new=deepcopy(self)
      add_obj=other
    xy=numpy.array([numpy.append(new.x, add_obj.x), numpy.append(new.y, add_obj.y)]).transpose()
    # use tuple hash values to find unique items
    xyitems=map(tuple, xy)
    xyitems=map(tuple.__hash__, xyitems)
    ignore, indices=numpy.unique1d(xyitems, return_index=True)
    for i, col in enumerate(new.data):
      col.append(add_obj.data[i])
      new.data[i]=col[indices]
    # restore old warning filters
    warnings.filters = original_filters
    return new

def read_data(file_name, script_path, import_images, return_detector_images):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
    
    @param file_name Name of the file to import
    @param script_path Path of the plot scripts to get the treff calibration file
    @param import_images Boolian to select if only the datafile should be imported or the 2d-detector images, too
    
    @return List of MeasurementData objects for the 2d maps and scans splitted by polarization channels
  '''
  #
  if file_name.endswith('.d17'):
    return read_d17_processed_data(file_name)
  if len(file_name.split('-'))==2:
    file_from, file_to=file_name.split('-')
    if os.path.split(file_from)[1].isdigit() and file_to.isdigit():
      return read_d17_raw_data(file_from, file_to)
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
                               ['error','a.u.']], 
                              [], 0, 1, 7, 6)  
  # alpha_i is used as main column for the line splitteng used for pm3d
  data_object.scan_line_constant=0
  data_object.scan_line=1
  data_list=[]
  scan_data_list=[]
  if (import_images  or return_detector_images):
    sys.stdout.write('\t\t Image %03i/%03i' % (1, len(data_lines)))
    sys.stdout.flush()
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
    sys.stdout.write('\b'*14+' Image %03i/%03i' % (index+1, len(data_lines)))
    sys.stdout.flush()
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
      sys.stdout.write( '\n\t\t\t'+ data_path + line[columns['Image']] + \
                    '(.gz) does not exist, check your files.\n\t\t Image %03i/%03i' % (1, len(data_lines)))
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
  if (import_images  or return_detector_images):
    print ""
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
                    error))
  return data_list, img_data

filter_indices=None

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
  cos=numpy.cos
  sin=numpy.sin
  data_list=[]
  monitor=float(line[columns['Monitor']])
  img_columns_data=img_data.transpose()
  calibration=numpy.array(calibration)
  filter_indices=numpy.where(calibration>0)
  img_intensities=img_columns_data.sum(axis=1)[filter_indices]
  try:
    intensities=img_intensities/monitor*calibration
  except ValueError:
    return []
  errors=numpy.sqrt(img_intensities)/monitor*calibration
  alphaf=alphaf_center + pixel_width * (CENTER_PIXEL - numpy.arange(DETECTOR_PIXELS))[filter_indices]
  # create importent columns
  data_list.append(GRAD_TO_MRAD*(numpy.zeros_like(alphaf)+alphai))
  data_list.append(GRAD_TO_MRAD*alphaf)
  data_list.append(data_list[0]+data_list[1])
  data_list.append(data_list[0]-data_list[1])
  data_list.append(PI_4_OVER_LAMBDA/2.*(cos(0.001*data_list[1]) - cos(0.001*data_list[0])))
  data_list.append(PI_4_OVER_LAMBDA/2.*(sin(0.001*data_list[0]) + sin(0.001*data_list[1])))
  data_list.append(intensities)
  data_list.append(errors)
  data_list=numpy.array(data_list).transpose().tolist()
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
  import config.gnuplot_preferences
  # speedup plotting using no interpolation or averidgeing
  config.gnuplot_preferences.settings_3dmap='''set pm3d map corners2color c1
set ticslevel 0.05
set palette defined (0 "blue", 1 "green", 2 "yellow", 3 "red", 4 "purple", 5 "black")
set size square
'''
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
  


def read_d17_processed_data(file_name):
  '''
    Read already processed data from the d17 instrument.
  '''
  PI_2_OVER_LAMBDA=numpy.pi*2./5.3
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  file_text=open(file_name, 'r').read()
  file_lines=file_text.splitlines()
  first_block=-1
  for i in range(10):
    if file_lines[i].startswith('X-axis:'):
      first_block=i+1
      scan_points=int(file_lines[i].split('by')[-1].split('rows')[0])
  if first_block==-1:
    print 'No valid D17 data header found.'
    return 'NULL'
  sample_name=file_lines[0]
  pol_channels=['++', '-+', '+-', '--']
  alphaf=d17_pp_from_block('α_f', '°', file_lines[first_block:first_block+scan_points])
  alphai=d17_pp_from_block('α_i', '°', file_lines[first_block+scan_points+2:first_block+2+2*scan_points])
  sort_order=numpy.lexsort(keys=(alphai, alphaf))
  alphai=alphai[sort_order]
  alphaf=alphaf[sort_order]
  aipaf=alphai+alphaf
  aipaf.dimension='α_i+α_f'
  aimaf=alphai-alphaf
  aimaf.dimension='α_i-α_f'
  qx=PI_2_OVER_LAMBDA*(numpy.cos(alphaf) - numpy.cos(alphai))
  qx.dimension='q_x'
  qx.unit='Å^{-1}'
  qz=PI_2_OVER_LAMBDA*(numpy.sin(alphai) + numpy.sin(alphaf))
  qz.dimension='q_z'
  qz.unit='Å^{-1}'
  channels=int(file_lines[first_block+scan_points*2+2].split('(')[1].split('arrays')[0])
  # import the data for the channels
  datasets=[]
  min_int=1.e6
  max_int=0.
  for i in range(channels):
    index=(scan_points+1)*i+(scan_points+2)*2+first_block
    error_index=(scan_points+1)*(i+channels-1)+(scan_points+2)*3+first_block
    intensity=d17_pp_from_block('Intensity', 
                                'a.u.', 
                                file_lines[index:index+scan_points],
                                error_block=file_lines[error_index:error_index+scan_points])
    intensity=intensity[sort_order]
    dataset=MeasurementDataTREFF(zdata=2)
    dataset.append_column(alphai)
    dataset.append_column(alphaf)
    dataset.append_column(intensity)
    dataset.append_column(aipaf)
    dataset.append_column(aimaf)
    dataset.append_column(qx)
    dataset.append_column(qz)
    dataset.logz=True
    dataset.sample_name=sample_name
    dataset.short_info=pol_channels[i]
    dataset.scan_line=1
    dataset.scan_line_constant=0
    min_int=min(min_int, intensity[numpy.where(intensity>0)].min())
    max_int=max(max_int, intensity.max())
    datasets.append(dataset)
  # define same colorscale for all plots as powers of 10
  min_int=10.**(int(math.log10(min_int)))
  max_int=10.**(int(math.log10(max_int))+1)
  for dataset in datasets:
    dataset.plot_options.zrange=(min_int, max_int)
  if len(datasets)==4:
    datasets=[datasets[0], datasets[3], datasets[2], datasets[1]]
  return datasets
  
  

def d17_pp_from_block(dimension, unit, block, error_block=None):
  '''
    Convert a block of data lines into a phyical property.
  '''
  split_block=map(str.split, block)
  if error_block is not None:
    split_error_block=map(str.split, error_block)
    error_data=numpy.array(split_error_block, dtype=numpy.float32).flatten()
  pp=PhysicalProperty(dimension, unit, split_block)
  pp=pp.flatten()
  if error_block is not None:
    pp.error=error_data
  return pp

d17_calibration={'water': None, 'transmission': None}
from config.treff import D17_CALIBRATION_FILES, D17_MASK

def read_d17_raw_data(file_from, file_to):
  '''
    Read d17 raw detector images.
  '''
  import config.treff
  config.treff.LAMBDA_N=5.3
  PI_2_OVER_LAMBDA=numpy.pi*2./5.3
  config.treff.PI_4_OVER_LAMBDA=4.*numpy.pi/5.3
  if d17_calibration['water'] is None:
    mask=D17_MASK
    scaling=mask.copy()
    scaling/=mask.sum(axis=0)
    scaling=scaling.flatten()
    scaling=numpy.nan_to_num(scaling)*mask.flatten()
    # normalize to the mean value to stay at about counts/s
    scaling/=scaling[numpy.where(mask.flatten()!=0)].mean()
    d17_calibration['water']=scaling
  #if d17_calibration['water'] is None and D17_CALIBRATION_FILES['water'] is not None:
    #print "    Reading calibration file 'water' which will be used for all imports..."
    ## using water measurement as mask and scale by the number of non zero elements per column
    #water=read_d17_calibration(D17_CALIBRATION_FILES['water']).z
    #mask=numpy.where(water!=0., 1., 0.).reshape(64, 256)
    #if D17_MASK_BOUNDS:
      #mask=(mask.transpose()*numpy.where((numpy.arange(0, 64)>=D17_MASK_BOUNDS[0])*\
                        #(numpy.arange(0, 64)<=D17_MASK_BOUNDS[1]), 1., 0.)).transpose()
    #scaling=mask.copy()#numpy.where(water!=0., 1./water, 0.).reshape(64, 256)
    #scaling/=mask.sum(axis=0)
    #scaling=scaling.flatten()
    #scaling=numpy.nan_to_num(scaling)*mask.flatten()
    ## normalize to the mean value to stay at about counts/s
    #scaling/=scaling[numpy.where(water!=0)].mean()
    #d17_calibration['water']=scaling
  #if d17_calibration['transmission'] is None and D17_CALIBRATION_FILES['transmission'] is not None:
    #print "    Reading calibration file 'transmission' which will be used for all imports..."
    #transmission=read_d17_calibration(D17_CALIBRATION_FILES['transmission']).z
    #scaling_factor=numpy.where(transmission!=0, 1./transmission, 0.)
    #scaling_factor/=scaling_factor[numpy.where(transmission!=0)].mean()
    #d17_calibration['transmission']=scaling_factor
  folder, file_from=os.path.split(file_from)
  file_to=os.path.join(folder, file_to)
  file_from=os.path.join(folder, file_from)
  file_list=glob(os.path.join(folder, '*'))
  file_list=filter(lambda item: os.path.split(item)[1].isdigit(), file_list)
  file_list.sort()
  if not (file_from in file_list and file_to in file_list):
    print 'File not found: %s and %s.' % (file_from, file_to)
    return 'NULL'
  from_index=file_list.index(file_from)
  to_index=file_list.index(file_to)
  file_list=file_list[from_index:to_index]
  datasets={(0, 0): [], (0, 1):[], (1, 0):[], (1, 1):[]}
  sys.stdout.write('    Reading %3i/%3i' % (1, len(file_list)))
  sys.stdout.flush()
  notfound=[]
  join_sets=[]
  for i, file_name in enumerate(file_list):
    sys.stdout.write('\b'*7+'%3i/%3i' % (i, len(file_list)))
    sys.stdout.flush()
    dataset=read_d17_raw_file(file_name)
    if dataset is None:
      notfound.append(i)
      continue
    dataset.number=str(i)
    join_sets.append(dataset)
    if i%7==6:
      datasets[(0, 0)].append(join_sets[0])
      datasets[(1, 1)].append(join_sets[2])
      datasets[(1, 0)].append(join_sets[1])
      datasets[(0, 1)].append(join_sets[3])
      datasets[(0, 0)][-1].y=(datasets[(0, 0)][-1].y+join_sets[6].y)/2.
      datasets[(1, 0)][-1].y=(datasets[(1, 0)][-1].y+join_sets[5].y)/2.
      datasets[(1, 1)][-1].y=(datasets[(1, 1)][-1].y+join_sets[4].y)/2.
      join_sets=[]
  sys.stdout.write('\n')
  output=[]
  absmin=100.
  absmax=0.
  for i, polarization_data in enumerate([datasets[(0, 0)], datasets[(1, 1)], datasets[(0, 1)], datasets[(1, 0)]]):
    dataset=MeasurementDataTREFF(zdata=2)
    dataset.append_column(polarization_data[0].data[2].copy())
    dataset.append_column(polarization_data[0].data[0].copy())
    dataset.append_column(polarization_data[0].data[1].copy())
    dataset.sample_name=polarization_data[0].sample_name
    dataset.short_info="("+"".join(map(str, polarization_data[0].flipper)).replace('1', '-').replace('0', '+')+")"
    dataset.number=str(i)
    for dataset_i in polarization_data[1:]:
      dataset.data[0].append(dataset_i.data[2])
      dataset.data[1].append(dataset_i.data[0])
      dataset.data[2].append(dataset_i.data[1])
    alphai=dataset.data[0]
    alphaf=dataset.data[1]
    dataset.append_column((alphai+alphaf)//'α_i+α_f')
    dataset.append_column((alphai-alphaf)//'α_i-α_f')
    dataset.append_column((PI_2_OVER_LAMBDA*(numpy.cos(alphaf) - numpy.cos(alphai)))//('q_x', 'Å^{-1}'))
    dataset.append_column((PI_2_OVER_LAMBDA*(numpy.sin(alphai) + numpy.sin(alphaf)))//('q_z', 'Å^{-1}'))
    dataset.logz=True
    dataset.scan_line=1
    dataset.scan_line_constant=0
    absmin=numpy.minimum(absmin, dataset.z.view(numpy.ndarray)[numpy.where(dataset.z!=0)].min())
    absmax=numpy.maximum(absmax, dataset.z.view(numpy.ndarray).max())
    output.append(dataset)
  zfrom=10**(int(math.log10(absmin)))
  zto=10**(int(math.log10(absmax))+1)
  for dataset in output:
    dataset.plot_options.zrange=(zfrom, zto)
  if len(notfound)>0:
    print "Could not import files %s" % str([file_name[i] for i in notfound])
  return output

def read_d17_raw_file(file_name):
  '''
    Read one single detector image.
  '''
  file_text=open(file_name, 'r').read()
  if not file_text.startswith('RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR'):
    #print "No D17 raw data header found."
    return None
  regions=file_text.split('IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
  regions=map(str.strip, regions)
  dataset=MeasurementDataTREFF()
  # evaluate header
  header_1=regions[1].split('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')[1].strip()
  header_1=header_1.splitlines()[1]
  sample_name=header_1.split()[0].strip()
  F1=int(header_1.split('*F1=')[1].split('*')[0])
  F2=int(header_1.split('*F2=')[1].split('*')[0])
  dataset.flipper=(F1, F2)
  dataset.sample_name=sample_name
  info_block1=regions[1].split('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')[1].strip()
  info_block2=regions[1].split('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')[2].strip()
  info_block1=info_block1.split()[1:]
  info_block2=info_block2.split()[1:]
  counting_time=PhysicalConstant(float(info_block1[2]), 's')
  monitor=PhysicalConstant(float(info_block1[4]), 'monitor')
  temp=float(info_block1[29])
  detector_angle=float(info_block2[16])
  omega=float(info_block2[2])
  # get the data 
  data=regions[-1].splitlines()[1:]
  data=map(str.split, data)
  # flatten data list
  data=[item for sublist in data for item in sublist]
  alphaf=PhysicalProperty('α_f', '°', numpy.arange(128, -128, -1)*0.02225+0.225+detector_angle-omega)
  alphai=PhysicalProperty('α_i', '°', numpy.zeros_like(alphaf)+omega)
  dataset.append_column(alphaf)
  intensity=PhysicalProperty('Intensity', 'counts', data)
  intensity/=counting_time
  if d17_calibration['water'] is not None:
    scaling=d17_calibration['water']
    intensity=intensity*scaling
    intensity.unit='a.u.'
  if d17_calibration['transmission'] is not None:
    scaling_factor=d17_calibration['transmission']
    intensity=intensity*scaling
    intensity.unit='a.u.'
  intensity=intensity.reshape(64, 256).sum(axis=0).flatten()
  intensity.dimension='Intensity'
  intensity.error=numpy.sqrt(intensity.view(numpy.ndarray))
  dataset.append_column(intensity)
  dataset.append_column(alphai)
  return dataset

def read_d17_calibration(file_name):
  '''
    Read one single detector image as calibration file.
  '''
  file_text=open(file_name, 'r').read()
  if not file_text.startswith('RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR'):
    #print "No D17 raw data header found."
    return None
  regions=file_text.split('IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
  regions=map(str.strip, regions)
  dataset=MeasurementDataTREFF(zdata=2)
  # evaluate header
  header_1=regions[1].split('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')[1].strip()
  header_1=header_1.splitlines()[1]
  sample_name=header_1.split()[0].strip()
  dataset.sample_name=sample_name
  info_block1=regions[1].split('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')[1].strip()
  info_block2=regions[1].split('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')[2].strip()
  info_block1=info_block1.split()[1:]
  info_block2=info_block2.split()[1:]
  counting_time=PhysicalConstant(float(info_block1[2]), 's')
  monitor=PhysicalConstant(float(info_block1[4]), 'monitor')
  # get the data 
  data=regions[-1].splitlines()[1:]
  data=map(str.split, data)
  # flatten data list
  data=[item for sublist in data for item in sublist]
  pix_x=PhysicalProperty('x', 'pix', [range(256) for i in range(64)]).flatten()
  pix_y=PhysicalProperty('y', 'pix', [[i for j in range(256)] for i in range(64)]).flatten()
  dataset.append_column(pix_x)
  dataset.append_column(pix_y)
  intensity=PhysicalProperty('Intensity', 'counts', data)
  intensity.dimension='Intensity'
  intensity.error=numpy.sqrt(intensity.view(numpy.ndarray))
  dataset.append_column(intensity)
  dataset.z/=counting_time
  return dataset


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
