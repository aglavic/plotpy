#!/usr/bin/env python
'''
  Functions to read from treff data and .img. files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
  Image files can be gziped or plain.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
import math
from measurement_data_structure import MeasurementData
from config.treff import GRAD_TO_MRAD, DETECTOR_ROWS_MAP, PI_4_OVER_LAMBDA, GRAD_TO_RAD, PIXEL_WIDTH

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.6a2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

def read_data(file_name, script_path, import_images):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  file_handler=open(file_name, 'r')
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
  columns_line=headers[2]
  if 'MF' in columns_line:
    columns_line.insert(columns_line.index('MF'), 'MF [G]')
    columns_line.remove('MF')
    columns_line.remove('[G]')
  # get the columns of interest
  columns={ 'Image': columns_line.index('Image'), 
           'Polarization': columns_line.index('Pol.'),
           'Monitor': columns_line.index('Monitor'), 
           '2DWindow': columns_line.index('2DWind.'), 
           'DetectorTotal': columns_line.index('2DTotal'), 
           'omega': -1, 
           'detector': -1
           }
  const_information={}
  for line in headers:
    try:
      if line[0] == 'Scan':
        columns['Scantype']=line[-1]
        if line[-1] == 'omega':
          columns['omega']=0
        elif line[-1] == 'detector':
          columns['detector']=0
      elif line[0] == '2nd':
        if line[-1] == 'omega':
          columns['omega']=1
        elif line[-1] == 'detector':
          columns['detector']=1
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
  if len(data_uu_lines)>0:
    print "Evaluating up-up images."
    data_uu, scan_uu=integrate_pictures(data_uu_lines, columns, const_information, path_name, calibration, import_images)
    data_uu.short_info='++ map'
    maps.append(data_uu)
    scan_uu.short_info='++'
    scans.append(scan_uu)
  if len(data_dd_lines)>0:
    print "Evaluating down-down images."
    data_dd, scan_dd=integrate_pictures(data_dd_lines, columns, const_information, path_name, calibration, import_images)
    data_dd.short_info='-- map'
    maps.append(data_dd)
    scan_dd.short_info='--'
    scans.append(scan_dd)
  if len(data_ud_lines)>0:
    print "Evaluating up-down images."
    data_ud, scan_ud=integrate_pictures(data_ud_lines, columns, const_information, path_name, calibration, import_images)
    data_ud.short_info='+- map'
    maps.append(data_ud)
    scan_ud.short_info='+-'
    scans.append(scan_ud)
  if len(data_du_lines)>0:
    print "Evaluating down-up images."
    data_du, scan_du=integrate_pictures(data_du_lines, columns, const_information, path_name, calibration, import_images)
    data_du.short_info='-+ map'
    maps.append(data_du)
    scan_du.short_info='-+'
    scans.append(scan_du)
  if len(data_xx_lines)>0:
    print "Evaluating unpolarized images."
    data_xx, scan_xx=integrate_pictures(data_xx_lines, columns, const_information, path_name, calibration, import_images)
    data_uu.short_info='unpolarized'
    maps.append(data_xx)
    scan_xx.short_info='unpolarized'
    scans.append(scan_xx)
  if import_images:
    output=maps + scans
  else:
    output= scans
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

def integrate_pictures(data_lines, columns, const_information, data_path, calibration, import_images):
  '''
    Integrate detector rows of the image files corresponding to one polarization direction.
    This function is tuned quite much for fast readout, so some parts are a bit tricky.
  '''
  sqrt=math.sqrt
  # create the data object
  scan_data_object=MeasurementData([[columns['Scantype'], 'mrad'], 
                               ['2DWindow', 'counts'], 
                               ['DetectorTotal', 'counts'], 
                               ['error','counts'], 
                               ['errorTotal','counts']], 
                              [], 0, 1, 3)
  data_object=MeasurementData([['\316\261_i', 'mrad'], 
                               ['\316\261_f', 'mrad'], 
                               ['\316\261_i+\316\261_f', 'mrad'], 
                               ['\316\261_i-\316\261_f', 'mrad'], 
                               ['q_x', '\303\205^{-1}'], 
                               ['q_z', '\303\205^{-1}'], 
                               ['Intensity', 'a.u.'], 
                               ['log_{10}(Intensity)', 'a.u.'], 
                               ['error','a.u.']], 
                              [], 0, 1, 8, 6)  
  # alpha_i is used as main column for the line splitteng used for pm3d
  data_object.scan_line_constant=0
  data_list=[]
  scan_data_list=[]
  for line in data_lines:
    if float(line[columns['Monitor']]) == 0.:
      continue # measurement error, nothing to do
    scan_data_list.append(map(float, (line[0], 
                                      line[columns['2DWindow']], 
                                      line[columns['DetectorTotal']], 
                                      line[columns['2DWindow']], 
                                      line[columns['DetectorTotal']])))
    if not import_images:
      continue
    if os.path.exists(data_path + line[columns['Image']]):
      # unziped images
      img_file=open(data_path + line[columns['Image']], 'r')
    elif os.path.exists(data_path + line[columns['Image']] + '.gz'):
      # ziped images
      import gzip
      img_file=gzip.open(data_path + line[columns['Image']] + '.gz', 'rb')
    else:
      # no image file
      print 'Image ' + data_path + line[columns['Image']] + '(.gz) does not exist, check your files.'
      continue
    # define alphai and alphaf (for the detector center)
    if columns['omega'] >= 0:
      alphai = float(line[columns['omega']])
    else:
      alphai = const_information['omega']
    if columns['detector'] >= 0:
      alphaf_center = float(line[columns['detector']]) - alphai
    else:
      alphaf_center = const_information['detector'] - alphai
    # read the data of an image file and split the lines 
    img_data=img_file.read()[:-1]
    img_file.close()
    img_data=img_data.split('\n')
    # integrate the image
    data_list+=integrate_one_picture(img_data, line, columns, alphai, alphaf_center, calibration, PIXEL_WIDTH)
  if import_images:  
    data_append=data_object.append
    # append the integrated data to the object
    map(data_append, data_list)
  scan_data_append=scan_data_object.append
  # sqrt of intensities is error
  def sqrt_34_gtm(point):
    point[0]=GRAD_TO_MRAD*point[0]
    point[3]=max(sqrt(point[3]), 1)
    point[4]=max(sqrt(point[4]), 1)
  map(sqrt_34_gtm, scan_data_list)
  map(scan_data_append, scan_data_list)
  return data_object, scan_data_object

def integrate_one_picture(img_data, line, columns, alphai, alphaf_center, calibration, pixelbreite):
  '''
    Map detector columns to alphai, alphaf and intensities.
    Quite optimized, too.
  '''
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
  parts=[[img_data[i] for i in map_i if not img_data[i] is '0'] for map_i in DETECTOR_ROWS_MAP]
  monitor=float(line[columns['Monitor']])
  for i in range(256):
    if calibration[i] <= 0 :
      continue # ignore blind spots of detector
    # convet strings into integer
    int_data=map(int, parts[i])
    img_integral=sum(int_data)
    alphaf = alphaf_center + pixelbreite * (130.8 - i)
    intensity = img_integral / monitor * calibration[i]
    if intensity > 0:
      logintensity = log10(intensity)
    else:
      logintensity = -10.0
    error = max(sqrt(img_integral), 1) / monitor * calibration[i]
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
  return data_list

def read_simulation(file_name):
  '''
    Read a fit.f90 output file as MeasurementData object.
  '''
  sim_file=open(file_name,'r')
  sim_lines=sim_file.readlines()
  sim_file.close()
  data=MeasurementData([['Theta','mrad'],['Intensity','counts/s'],['Unknown','counts/s'],['Unknown2','counts/s']],[],0,1,2)
  data.info='Simulation'
  for line in sim_lines:
    if len(line.split())>1:
      point=map(float,line.split())
      data.append(point)
  return data

if __name__ == '__main__':    #code to execute if called from command-line for testing
  import sys
  read_data(sys.argv[1])
