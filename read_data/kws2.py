# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os, sys
from copy import deepcopy
from numpy import sqrt, array, pi, sin, arctan, maximum, linspace, savetxt, resize, where, int8, float32, uint16, fromstring, arange, meshgrid, zeros
from configobj import ConfigObj
from glob import glob
from measurement_data_structure import MeasurementData, HugeMD, PhysicalProperty
import config.kws2
import config.gnuplot_preferences
import array as array_module
import gzip

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.5"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

# plack times speed of light
h_c=1.239842E4 #eV⋅Å
detector_sensitivities={}
background_data={}
imported_edfs=[]
import_subframes=False

def read_data(file_name):
  '''
    Read the data of a kws2 data file.
    
    @param file_name The name of the file to import
    
    @return MeasurementData object with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  if file_name.endswith('.cmb') or file_name.endswith('.cmb.gz'):
    #config.gnuplot_preferences.plotting_parameters_3d='w points palette pt 5'
    config.gnuplot_preferences.settings_3dmap=config.gnuplot_preferences.settings_3dmap.replace('interpolate 5,5', '')
    return read_cmb_file(file_name)
  elif file_name.endswith('.edf') or file_name.endswith('.edf.gz'):
    # Read .edf GISAXS data (Soleil)
    #config.gnuplot_preferences.plotting_parameters_3d='w points palette pt 5'
    config.gnuplot_preferences.settings_3dmap=config.gnuplot_preferences.settings_3dmap.replace('interpolate 5,5', '')
    return read_edf_file(file_name)
  elif file_name.endswith('.bin') or file_name.endswith('.bin.gz') or file_name.endswith('.tif'):
    # Read .bin data (p08)
    config.gnuplot_preferences.settings_3dmap=config.gnuplot_preferences.settings_3dmap.replace('interpolate 5,5', '')
    return read_p08_binary(file_name)
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'gisas_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
    read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  if setup['BACKGROUND'] and not setup['BACKGROUND'] in detector_sensitivities:
    read_background(folder, setup['BACKGROUND'])
  if file_name.endswith('.gz'):
    # use gziped data format
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  header_lines=lines[:config.kws2.HEADER]
  countingtime=read_countingtime(header_lines)
  data_lines=lines[config.kws2.HEADER:]
  file_handler.close()
  output= create_dataobj(data_lines,  header_lines, countingtime, setup)
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
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  data_joined=" ".join(data_lines)
  data_array=array(map(float, data_joined.split()))
  y_array=array([i%config.kws2.PIXEL_X for i in range(config.kws2.PIXEL_X**2)])
  z_array=array([i/config.kws2.PIXEL_X for i in range(config.kws2.PIXEL_X**2)])
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
    lambda_n=config.kws2.LAMBDA_N
  qy_array=4.*pi/lambda_n*\
           sin(arctan((y_array-setup['CENTER_X'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  qz_array=4.*pi/lambda_n*\
           sin(arctan((z_array-setup['CENTER_Y'])*config.kws2.PIXEL_SIZE/setup['DETECTOR_DISTANCE'])/2.)
  if setup['SWAP_YZ']:
    # swap the directions
    tmp=qz_array
    qz_array=qy_array
    qy_array=tmp
  for i in range(config.kws2.PIXEL_X**2):
    dataobj.append((y_array[i], z_array[i], corrected_data[i], corrected_error[i], 
                    qy_array[i], qz_array[i], data_array[i], error_array[i]))
  return dataobj
  
def read_sensitivities(folder, name):
  '''
    Read data from the sensitivity file.
  '''
  global detector_sensitivities
  print "\treading detector sesitivity from %s" % name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.kws2.HEADER])
  data_lines=lines[config.kws2.HEADER:]
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
  print "\treading background data from %s" % name
  file_name=os.path.join(folder, name)
  if file_name.endswith('.gz'):
    # use gziped data format
    file_handler=gzip.open(file_name, 'r')
  else:
    file_handler=open(file_name, 'r')
  lines=file_handler.readlines()
  countingtime=read_countingtime(lines[:config.kws2.HEADER])
  data_lines=lines[config.kws2.HEADER:]
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
  sys.stdout.write( "\tReading...\n")
  sys.stdout.flush()
  background=2.
  countingtime=1.
  detector_distance=1435. #mm
  pixelsize_x= 0.2171 #mm
  pixelsize_y= 0.2071 #mm
  sample_name=''
  center_x=345.
  center_y=498.5
  q_window=[-0.2, 0.2, -0.05, 0.35]
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  if file_name.endswith('.gz'):
    file_handler=gzip.open(file_name, 'rb')
  else:
    file_handler=open(file_name, 'rb')
  header=file_handler.read(256)
  file_handler.read(256)
  data_array=array_module.array('i')
  data_array.fromfile(file_handler, 1024**2)
  # read additional info from end of file
  lines=file_handler.readlines()
  for line in lines:
    if line.startswith('#sca'):
      countingtime=float(line.split()[1])
    #elif line.startswith('#dst'):
    #  detector_distance=float(line.split()[1])
    elif line.startswith('#txt'):
      sample_name+=" ".join(line.split()[1:])
  sys.stdout.write( "\b\b\b done!\n\tProcessing...")
  sys.stdout.flush()
  data_array=array(data_array)
  z_array=linspace(0, 1024**2-1, 1024**2)%1024
  y_array=linspace(0, 1024**2-1, 1024**2)//1024
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  lambda_x=1.54
  qy_array=4.*pi/lambda_x*\
           sin(arctan((y_array-center_y)*pixelsize_y/detector_distance/2.))
  qz_array=4.*pi/lambda_x*\
           sin(arctan((z_array-center_x)*pixelsize_x/detector_distance/2.))

  use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
  dataobj.data[0].values=y_array[use_indices].tolist()
  dataobj.data[1].values=z_array[use_indices].tolist()
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
  sys.stdout.write( "\b\b\b done!\n")
  sys.stdout.flush()
  return [dataobj]
 
def read_edf_file(file_name):
  '''
    Read the binary .edf (european data format) file including header.
    The data is taken from many pictures and summed up. To prevent double
    import the file names already used are stored in a global list.
  '''
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'gisas_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  
  q_window=[-0.9, 0.9, -0.9, 0.9]
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ],
                            [], 4, 5, 3, 2)
  # Get header information
  if setup['BACKGROUND']:
    if not setup['BACKGROUND'] in background_data:
      read_background_edf(setup['BACKGROUND'])
    background_array=background_data[setup['BACKGROUND']]
  else:
    background_array=None

  if import_subframes:
    input_array, header_settings, header_info=import_edf_file(file_name)
  else:
    # get a list of files, which belong together
    file_prefix, file_ending=file_name.split('_im_')
    file_postfix=file_ending.split('.', 1)[1] # remove number
    if file_prefix in imported_edfs:
      return 'NULL'
    input_array, header_settings, header_info=import_edf_set(file_name)

  if setup['CENTER_X']:
    center_x=setup['CENTER_X']
  else:
    center_x=header_info['pixel_x']
  if setup['CENTER_Y']:
    center_y=setup['CENTER_Y']
  else:
    center_y=header_info['pixel_y']
  countingtime=header_info['time']
  # subtract background
  if setup['BACKGROUND']:
    input_array-=background_array*countingtime
  sys.stdout.write('\tData Processing ...')
  sys.stdout.flush()
  # define other quantities for the input data
  x_array=linspace(0, header_info['xdim']**2-1, header_info['xdim']**2)%header_info['ydim']
  y_array=linspace(0, header_info['ydim']**2-1, header_info['ydim']**2)//header_info['ydim']
  error_array=sqrt(input_array)
  corrected_data_array=input_array/countingtime
  corrected_error_array=error_array/countingtime
  qy_array=4.*pi/header_info['lambda_γ']*\
           sin(arctan((x_array-center_x)*header_info['pixelsize_x']/setup['DETECTOR_DISTANCE']/2.))
  qz_array=-4.*pi/header_info['lambda_γ']*\
           sin(arctan((y_array-center_y)*header_info['pixelsize_y']/setup['DETECTOR_DISTANCE']/2.))
  use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
  dataobj.data[0].values=x_array[use_indices].tolist()
  dataobj.data[1].values=y_array[use_indices].tolist()
  # convert indices to integers to save memory
  dataobj.data[0]=dataobj.data[0]
  dataobj.data[1]=dataobj.data[1]
  dataobj.data[2].values=corrected_data_array[use_indices].tolist()
  dataobj.data[3].values=corrected_error_array[use_indices].tolist()
  dataobj.data[4].values=qy_array[use_indices].tolist()
  dataobj.data[5].values=qz_array[use_indices].tolist()
  dataobj.sample_name=header_info['sample_name']
  dataobj.info="\n".join([item[0]+': '+item[1] for item in sorted(header_settings.items())])
  if import_subframes:
    dataobj.short_info=""
  else:
    dataobj.short_info="Sum of frames"
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  dataobj.logz=True
  sys.stdout.write('\b'*3+'complete!\n')
  sys.stdout.flush()
  if not import_subframes:
    print "\tImport complete, ignoring file names belonging to the same series."
  return [dataobj]

def import_edf_set(file_name):
  '''
    Read a complete set of data and sum the files together.
    
    @return array of sum of the data and changed header settings.
  '''
  # get a list of files, which belong together
  file_prefix, file_ending=file_name.split('_im_')
  file_postfix=file_ending.split('.', 1)[1] # remove number
  if file_prefix in imported_edfs:
    return 'NULL'
  imported_edfs.append(file_prefix)
  file_list=glob(file_prefix+'_im_'+'*'+'.edf')+glob(file_prefix+'_im_'+'*'+'.edf.gz')
  file_list.sort()
  if file_prefix+'_im_full.edf' in file_list:
    return import_edf_file(file_prefix+'_im_full.edf')
  file_name=file_list[0]
  sys.stdout.write('\tReading file 1/%i' % len(file_list))
  sys.stdout.flush()
  input_array, header_settings, header_info=import_edf_file(file_name)
  i=0
  # import all other files and add them together
  for i, file_name in enumerate(file_list[1:]):
    sys.stdout.write('\b'*(len(str(i+1))+len(str(len(file_list))))+'\b%i/%i' % (i+2, len(file_list)))
    sys.stdout.flush()
    input_array_tmp, header_settings_tmp, header_info_tmp=import_edf_file(file_name)
    # add the collected data to the already imported
    input_array+=input_array_tmp
    header_info['time']+=header_info_tmp['time']
  sys.stdout.write('\b'*(len(str(i+2))+len(str(len(file_list))))+'\breadout complete, writing sum to %s!\n' % (file_prefix+'_im_full.edf'))
  sys.stdout.flush()
  write_edf_file(file_prefix, input_array, header_info['time'])
  return input_array, header_settings, header_info
  
def read_background_edf(background_file_name):
  '''
    Read the binary .edf (european data format) file including header.
    The data is taken from many pictures and summed up. To prevent double
    import the file names already used are stored in a global list.
  '''
  file_list=glob(background_file_name)
  file_list.sort()
  file_name=file_list[0]
  sys.stdout.write('\tReading background file 1/%i' % len(file_list))
  sys.stdout.flush()
  if file_name.endswith('.gz'):
    file_handler=gzip.open(file_name, 'rb')
  else:
    file_handler=open(file_name, 'rb')
  header_settings, header_info=read_edf_header(file_handler)
  import array as array_module
  input_array=array_module.array('H')
  #data_array.fromfile(file_handler, header_info['xdim']*header_info['ydim']) # deosn't work with gzip
  input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*2))
  file_handler.close()
  bg_data=array(input_array)
  bg_time=header_info['time']
  # import all other files and add them together
  for i, file_name in enumerate(file_list[1:]):
    sys.stdout.write('\b'*(len(str(i+1))+len(str(len(file_list))))+'\b%i/%i' % (i+2, len(file_list)))
    sys.stdout.flush()
    if file_name.endswith('.gz'):
      file_handler=gzip.open(file_name, 'rb')
    else:
      file_handler=open(file_name, 'rb')
    header_settings, header_info=read_edf_header(file_handler)
    input_array=array_module.array('H')
    input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*2))
    file_handler.close()
    # add the collected data to the already imported
    bg_data+=array(input_array)
    bg_time+=header_info['time']
  background_data[background_file_name]=bg_data/bg_time
  sys.stdout.write('\b'*(len(str(i+2))+len(str(len(file_list))))+'\breadout complete!\n')
  sys.stdout.flush()

def read_edf_header(file_handler):
  '''
    Read the header of an edf file from an open file object.
  '''
  line=file_handler.readline()
  header_lines=[]
  settings={}
  # Set standart values which are overwritten if found in the header
  info={
      'lambda_γ': 1.771, 
      'xdim': 1024, 
      'ydim': 1024, 
      'sample_name': '', 
      'time': 1., 
      'pixel_x': 512.5, 
      'pixelsize_x': 0.16696,#0.0914, 
      'pixel_y': 512.5, 
      'pixelsize_y': 0.16696,#0.0914, 
      'detector_distance': 102., 
      }
  while '}' not in line:
    if "=" in line:
      key, value= line.split('=', 1)
      key=key.strip()
      value=value.strip().rstrip(';').strip()
      settings[key]=value
    header_lines.append(line)
    line=file_handler.readline()
  header_lines.append(line)
  # Read some settings
  if 'Dim_1' in settings:
    info['xdim']=int(settings['Dim_1'])
  if 'Dim_2' in settings:
    info['ydim']=int(settings['Dim_2'])
  if 'Distance_sample-detector' in settings:
    info['detector_distance']=float(settings['Distance_sample-detector'].rstrip('mm'))
  if 'Monochromator_energy' in settings:
    energy=float(settings['Monochromator_energy'].rstrip('keV'))*1000.
    info['lambda_γ']= h_c/energy
  if 'Sample_comments' in settings:
    info['sample_name']=settings['Sample_comments']
  if 'Exposure_time' in settings:
    info['time']=float(settings['Exposure_time'].rstrip('ms'))/1000.
  return settings, info, header_lines

def import_edf_file(file_name):
  '''
    Read the header and data from one edf file.
    
    @return array of the data and the header string.
  '''
  #  check if file is in gzip format
  if file_name.endswith('.gz'):
    file_handler=gzip.open(file_name, 'rb')
  else:
    file_handler=open(file_name, 'rb')
  # read file header information
  header_settings, header_info, header_lines=read_edf_header(file_handler)
  if header_settings['DataType']=='UnsignedShort':
    # load data as binary integer values
    input_array=array_module.array('H')
    input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*2))
    input_array=array(input_array)-200
  elif header_settings['DataType']=='SignedInteger':
    # load data as binary integer values
    input_array=array_module.array('i')
    input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*4))
  else:
    raise IOError, 'Unknown data format in header: %s' % header_settings['DataType']
  file_handler.close()
  return array(input_array), header_settings, header_info

def write_edf_file(file_prefix, data, countingtime):
  '''
    Write a new edf file for sumed up data.
  '''
  file_list=glob(file_prefix+'_im_'+'*'+'.edf')+glob(file_prefix+'_im_'+'*'+'.edf.gz')
  file_list.sort()
  if file_list[0].endswith('.gz'):
    file_handler=gzip.open(file_list[0], 'rb')
  else:
    file_handler=open(file_list[0], 'rb')
  old_file_parts=read_edf_header(file_handler)
  file_handler.close()
  write_file=open(file_prefix+'_im_full.edf', 'wb')
  for header_line in old_file_parts[2]:
    if 'Exposure_time' in header_line:
      write_file.write("Exposure_time = %fms ;\n" % (countingtime*1000.))
    elif 'DataType' in header_line:
      write_file.write("DataType = SignedInteger ;\n")
    else:
      write_file.write(header_line)
  output_array=array_module.array('i')
  int_data=map(int, data.tolist())
  output_array.fromlist(int_data)
  output_array.tofile(write_file)
  write_file.close()  

def read_p08_binary(file_name):
  '''
    Read the binary .bin file format of P08@PETRA-3 CCD camera.
  '''
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'gisas_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  sys.stdout.write( "\tReading...")
  sys.stdout.flush()
  countingtime=1.
  detector_distance=setup['DETECTOR_DISTANCE'] #mm
  join_pixels=4.
  pixelsize_x= 0.015 * join_pixels#mm
  pixelsize_y= 0.015 * join_pixels#mm
  sample_name=''
  center_x=setup['CENTER_X']/join_pixels
  center_y=setup['CENTER_Y']/join_pixels
  q_window=[-0.5, 0.5, -0.5, 0.5]
  dataobj=KWS2MeasurementData([], 
                            [], 2, 3, -1, 4)
  # read the data
  sys.stdout.write( "\b\b\b binary...")
  sys.stdout.flush()
  header, data_array=read_p08_binarydata(file_name)
  if setup['BACKGROUND'] is not None:
    sys.stdout.write( "\b\b\b subtracting background %s..." % setup['BACKGROUND'])
    sys.stdout.flush()
    data_array-=read_p08_binarydata(setup['BACKGROUND'])[1]
  # averadge 4x4 pixels
  sys.stdout.write( "\b\b\b, joining %ix%i pixels..." % (join_pixels, join_pixels))
  sys.stdout.flush()
  # neighboring pixels
  use_ids=arange(4096/join_pixels).astype(int)*int(join_pixels)
  grid=meshgrid(use_ids, use_ids)
  data_array2=zeros((4096/join_pixels, 4096/join_pixels))
  for i in range(int(join_pixels)):
    for j in range(int(join_pixels)):
      data_array2+=data_array[use_ids+i][:,use_ids+j]
  data_array=data_array2.flatten()
  sys.stdout.write( "\b\b\b, calculating q-positions and joining data...")
  sys.stdout.flush()
  # read additional info from end of file
  z_array=linspace(0, (4096/join_pixels)**2-1, (4096/join_pixels)**2)%(4096/join_pixels)
  y_array=linspace(0, (4096/join_pixels)**2-1, (4096/join_pixels)**2)//(4096/join_pixels)
  error_array=sqrt(data_array)
  corrected_data=data_array/countingtime
  corrected_error=error_array/countingtime
  lambda_x=setup['LAMBDA_N']
  qy_array=4.*pi/lambda_x*\
           sin(arctan((y_array-center_y)*pixelsize_y/detector_distance/2.))
  qz_array=4.*pi/lambda_x*\
           sin(arctan((z_array-center_x)*pixelsize_x/detector_distance/2.))

  use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
  dataobj.data.append(PhysicalProperty('pixel_x', 'pix', y_array[use_indices]))
  dataobj.data.append(PhysicalProperty('pixel_y', 'pix', z_array[use_indices]))
  dataobj.data.append(PhysicalProperty('q_y', 'Å^{-1}', qy_array[use_indices]))
  dataobj.data.append(PhysicalProperty('q_z', 'Å^{-1}', qz_array[use_indices]))
  dataobj.data.append(PhysicalProperty('intensity', 'counts/s', corrected_data[use_indices]))
  dataobj.data[-1].error=corrected_error[use_indices]
  #dataobj.data[3]=PhysicalProperty('raw_int', 'counts', data_array[use_indices])
  #dataobj.data[3].error=error_array[use_indices]

  dataobj.sample_name=sample_name
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  dataobj.logz=True
  sys.stdout.write( "\b\b\b done!\n")
  sys.stdout.flush()
  return [dataobj]

def read_p08_binarydata(file_name):
  '''
    Read the raw data of p08 file.
  '''
  if file_name.endswith('.tif'):
    header=''
    import Image
    image=Image.open(file_name)
    data=fromstring(image.tostring(), uint16)
    data=data.reshape(4096,  4096)
  else:
    if file_name.endswith('.gz'):
      file_handler=gzip.open(file_name, 'rb')
    else:
      file_handler=open(file_name, 'rb')
    header=file_handler.read(216)
    data=fromstring(file_handler.read(), uint16).reshape(4096, 4096)
    file_handler.close()
  return header, data
  
class KWS2MeasurementData(HugeMD):
  '''
    Class implementing additions for KWS2 data objects.
  '''
  
  def __add__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.tmp_export_file=self.tmp_export_file+'_'+os.path.split(other.tmp_export_file)[1]
    out.data[2].values=(array(self.data[2].values)+array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2+array(other.data[3].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)+array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2+array(other.data[7].values)**2)).tolist()
    out.changed_after_export=True
    return out
  
  def __sub__(self, other):
    '''
      Subtract two measurements from another.
    '''
    out=deepcopy(self)
    out.short_info=self.short_info+'-'+other.short_info
    out.tmp_export_file=self.tmp_export_file+'_'+os.path.split(other.tmp_export_file)[1]
    out.data[2].values=(array(self.data[2].values)-array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2+array(other.data[3].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)-array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2+array(other.data[7].values)**2)).tolist()
    out.changed_after_export=True
    return out
  
  def __rmul__(self, other):
    '''
      Add two measurements together.
    '''
    out=deepcopy(self)
    out.tmp_export_file=self.tmp_export_file+'_'+str(other)
    out.data[2].values=(other*array(self.data[2].values)).tolist()    
    out.data[3].values=(other*array(self.data[3].values)).tolist()    
    out.data[6].values=(other*array(self.data[6].values)).tolist()    
    out.data[7].values=(other*array(self.data[7].values)).tolist()    
    out.changed_after_export=True
    return out
  
  def __mul__(self, other):
    '''
      Multiply two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.tmp_export_file=self.tmp_export_file+'_'+os.path.split(other.tmp_export_file)[1]
    out.data[2].values=(array(self.data[2].values)*array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2*array(other.data[2].values)**2+\
                             array(other.data[3].values)**2*array(self.data[2].values)**2)).tolist()
    out.data[6].values=(array(self.data[6].values)*array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2*array(other.data[6].values)**2+\
                             array(other.data[7].values)**2*array(self.data[6].values)**2)).tolist()
    out.changed_after_export=True
    return out
  
  def __div__(self, other):
    '''
      Divide two measurements.
    '''
    if type(self)!=type(other):
      return self.__rmul__(1./other)
    out=deepcopy(self)
    out.short_info=self.short_info+'+'+other.short_info
    out.tmp_export_file=self.tmp_export_file+'_'+os.path.split(other.tmp_export_file)[1]
    out.data[2].values=(array(self.data[2].values)/array(other.data[2].values)).tolist()    
    out.data[3].values=(sqrt(array(self.data[3].values)**2/array(other.data[2].values)**2+\
                             array(other.data[3].values)**2*array(self.data[2].values)**2\
                             /array(other.data[2].values)**4)).tolist()
    out.data[6].values=(array(self.data[6].values)/array(other.data[6].values)).tolist()    
    out.data[7].values=(sqrt(array(self.data[7].values)**2/array(other.data[6].values)**2+\
                             array(other.data[7].values)**2*array(self.data[6].values)**2\
                             /array(other.data[6].values)**4)).tolist()
    out.changed_after_export=True
    return out
