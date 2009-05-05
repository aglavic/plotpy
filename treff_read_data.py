#!/usr/bin/env python
'''
  Functions to read from treff data and .img. files. Mostly just string processing.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects
'''

# Pleas do not make any changes here unless you know what you are doing.

import os
import math
from measurement_data_structure import *

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Ulrich Ruecker"]
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Prototype"

def read_data(file_name):
  '''
    Read the data of a treff raw data file, integrate the corresponding .img files.
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return None
  file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  file_handler.close()
  # devide comment lines from data lines
  lines_columns=map(str.split, lines)
  comments=map(string_or_float, lines_columns)
  headers=filter(lambda i: not comments[lines_columns.index(i)], lines_columns)
  data_lines=filter(lambda i: comments[lines_columns.index(i)], lines_columns)
  columns_line=headers[2]
  if 'MF' in columns_line:
    columns_line.insert(columns_line.index('MF'), 'MF [G]')
    columns_line.remove('MF')
    columns_line.remove('[G]')
  # get the columns of interest
  columns={ 'Image': columns_line.index('Image'), 
           'Polarization': columns_line.index('Pol.'),
           'Monitor': columns_line.index('Monitor'), 
           'omega': -1, 
           'detector': -1
           }
  for line in headers[0:6]:
    if line[0] == 'Scan':
      if line[-1] == 'omega':
        columns['omega']=0
      elif line[-1] == 'detector':
        columns['detector']=0
    if line[0] == '2nd':
      if line[-1] == 'omega':
        columns['omega']=1
      elif line[-1] == 'detector':
        columns['detector']=1
  const_information={}
  for line in headers[6:]:
    try:
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
  # import calibration from file
  cali_file='/home/glavic/Software/Scripte/Plotting/treff/KALIBR2.DAT'
  cali_open=open(cali_file, 'r')
  calibration=map(float, cali_open.readlines())
  cali_open.close()
  
  path_name=os.path.dirname(file_name)
  if len(path_name)>0:
    path_name+='/'
  
  output=[]
  if len(data_uu_lines)>0:
    print "Evaluating up-up images."
    data_uu=integrate_pictures(data_uu_lines, columns, path_name, calibration)
    data_uu.short_info='++'
    output.append(data_uu)
  if len(data_dd_lines)>0:
    print "Evaluating down-down images."
    data_dd=integrate_pictures(data_dd_lines, columns, path_name, calibration)
    data_dd.short_info='--'
    output.append(data_dd)
  if len(data_ud_lines)>0:
    print "Evaluating up-down images."
    data_ud=integrate_pictures(data_ud_lines, columns, path_name, calibration)
    data_ud.short_info='+-'
    output.append(data_ud)
  if len(data_du_lines)>0:
    print "Evaluating down-up images."
    data_du=integrate_pictures(data_du_lines, columns, path_name, calibration)
    data_du.short_info='-+'
    output.append(data_du)
  if len(data_xx_lines)>0:
    print "Evaluating unpolarized images."
    data_xx=integrate_pictures(data_xx_lines, columns, path_name, calibration)
    data_xx.short_info='unpolarized'
    output.append(data_xx)
  return output

def string_or_float(string_line):
  '''
    Short help function test if first column is a float number.
  '''
  if len(string_line)==0:
    return False
  try:
    float(string_line[0])
    return True
  except ValueError:
    return False

def integrate_pictures(data_lines, columns, data_path, calibration):
  data_object=MeasurementData([['alpha_i', 'mrad'], 
                               ['alpha_f', 'mrad'], 
                               ['Intensity', 'a.u.'], 
                               ['log_{10}(Intensity)', 'a.u.'], 
                               ['error','a.u.']], 
                              [], 0, 1, 4, 2)
  data_list=[]
  pixelbreite=0.014645
  for line in data_lines:
    if float(line[columns['Monitor']]) == 0.:
      continue
    if os.path.exists(data_path + line[columns['Image']]):
      # unziped images
      img_file=open(data_path + line[columns['Image']], 'r')
    elif os.path.exists(data_path + line[columns['Image']] + '.gz'):
      # ziped images
      import gzip
      img_file=gzip.open(data_path + line[columns['Image']] + '.gz', 'rb')
    else:
      print 'Image ' + data_path + line[columns['Image']] + '(.gz) does not exist, check your files.'
      return None
    alphai = float(line[columns['omega']])
    alphaf_center = float(line[columns['detector']]) - alphai
    # read the data of an image file and convet it to integer
    # every image file consists of 256 rows and 256 columns of the detector
    img_data=img_file.read()[:-1]
    img_file.close()
    img_data=img_data.split('\n')
    data_list+=integrate_one_picture(img_data, line, columns, alphai, alphaf_center, calibration, pixelbreite)
  data_append=data_object.append
  map(data_append, data_list)
  return data_object

def integrate_one_picture(img_data, line, columns, alphai, alphaf_center, calibration, pixelbreite):
  '''Map detector columns to alphai, alphaf and intensities.'''
  from math import sqrt, log10
  data_list=[]
  append_to_list=data_list.append
  parts=map(lambda i: img_data[i*256:(i+1)*256], range(256))
  for i in range(256):
    if calibration[i] <= 0 :
      continue
    int_data=map(int, parts[i])
    img_integral=sum(int_data)
    alphaf = alphaf_center + pixelbreite * (130.8 - i)
    intensity = img_integral / float(line[columns['Monitor']]) * calibration[i]
    if intensity > 0:
      logintensity = log10(intensity)
    else:
      logintensity = -10.0
    error = sqrt(img_integral) / float(line[columns['Monitor']]) * calibration[i]
      # convert to mrad
    append_to_list([17.45329 * alphai, 
                    17.45329 * alphaf, 
                    intensity, 
                    logintensity, 
                    error])
  return data_list


if __name__ == '__main__':    #code to execute if called from command-line
  import sys
  read_data(sys.argv[1])
