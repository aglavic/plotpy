# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os, sys

from numpy import linspace, float32, float64, asarray, array
# use PIL image readout
import Image
# py2exe hack
import PngImagePlugin #@UnusedImport
Image._initialized=2

from plot_script.measurement_data_structure import HugeMD, PhysicalProperty, MeasurementData
from plot_script.config import gnuplot_preferences

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

def read_data(file_name):
  '''
    Read the data of a LEED data file.
    
    :param file_name: The name of the file to import
    
    :return: MeasurementData object with the file data
  '''
  if file_name.endswith('.png'):
    gnuplot_preferences.settings_3dmap=gnuplot_preferences.settings_3dmap.replace('interpolate 3,3', '')
    return read_png_data(file_name)
  elif file_name.endswith('.dat'):
    return read_dat_data(file_name)
  elif file_name.endswith('.log'):
    return read_dca_log_data(file_name)
  return []

def read_dca_log_data(file_name):
  ''' 
    Read DCA log files
  '''
  data_lines=open(file_name).readlines()
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
    cols=["Col-%i"%i for i in range(len(data_lines[0].split('\t')))]
    sample_name=''
  data_lines=data_lines[i:]
  data_lines=map(str.strip, data_lines)
  data_lines=map(lambda item: item.split('\t'), data_lines)

  data=array(data_lines, dtype=float64).transpose()
  output=MeasurementData()
  output.short_info=os.path.split(file_name)[1].rsplit('.', 1)[0]
  output.sample_name=sample_name
  for i, col in enumerate(cols):
    try:
      output.data.append(PhysicalProperty(col, '', data[i], dtype=float64))
    except IndexError:
      return 'NULL'
  return [output]

def read_dat_data(file_name):
  ''' 
    Read AES dat file
  '''
  data_lines=open(file_name).readlines()
  i=0
  while 'Basis' not in data_lines[i]:
    i+=1
  ignore=data_lines[:i+1]
  data_lines=data_lines[i+1:]
  data_lines=map(str.strip, data_lines)
  data_lines=map(str.split, data_lines)

  cols=array(data_lines, dtype=float32).transpose()
  output=MeasurementData()
  output.data.append(PhysicalProperty('E', 'eV', cols[0]/1000.))
  output.data.append(PhysicalProperty('I', 'a.u.', cols[1]))
  output.short_info=os.path.split(file_name)[1].rsplit('.', 1)[0]
  for i, col in enumerate(cols[2:]):
    output.data.append(PhysicalProperty('I_%i'%(i+2), 'a.u.', col))
  return [output]

def read_png_data(file_name):
  '''
    Read a png datafile.
  '''
  ignore, rel_file_name=os.path.split(os.path.realpath(file_name))
  #setups=ConfigObj(os.path.join(folder, 'leed_setup.ini'), unrepr=True)
  #setup=None
  #for key, value in setups.items():
  #  if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
  #    setup=value
  #if setup is None:
  #  raise ValueError, 'no setup found for %s'%file_name
  sys.stdout.write("\tReading...")
  sys.stdout.flush()
  # read the data
  sys.stdout.write("\b\b\b PNG Image...")
  sys.stdout.flush()
  data_array=read_raw_png_data(file_name)
  pixels_x, pixels_y=data_array.shape
  data_array=data_array.reshape(pixels_y, pixels_x)
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
  y_array=linspace(0, (pixels_x)*(pixels_y)-1,
                   (pixels_x)*(pixels_y))//(pixels_y)
  x_array=linspace(0, (pixels_x)*(pixels_y)-1,
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
  dataobj.short_info=rel_file_name.rsplit('.', 1)[0]
  #dataobj.logz=True
  sys.stdout.write("\b\b\b done!\n")
  sys.stdout.flush()
  return [dataobj]

def read_raw_png_data(file_name):
  img=Image.open(file_name)
  data_array=asarray(img.getdata())
  data_array=data_array.reshape(*img.size)
  data_array=data_array.astype(float32)
  return data_array
