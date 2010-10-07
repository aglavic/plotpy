# -*- encoding: utf-8 -*-
'''
  Functions to read from kws2 data files.
  MeasurementData Object from 'measurement_data_structure' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os, sys
from copy import deepcopy
from numpy import sqrt, array, pi, sin, arctan, maximum, linspace, savetxt, resize, where
from configobj import ConfigObj
from glob import glob
from measurement_data_structure import MeasurementData, HugeMD
import config.kws2
import config.gnuplot_preferences

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta6"
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
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'kws2_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
    read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  if setup['BACKGROUND'] and not setup['BACKGROUND'] in detector_sensitivities:
    read_background(folder, setup['BACKGROUND'])
  if file_name.endswith('.gz'):
    # use gziped data format
    import gzip
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
    import gzip
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
    import gzip
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
    import gzip
    file_handler=gzip.open(file_name, 'rb')
  else:
    file_handler=open(file_name, 'rb')
  header=file_handler.read(256)
  file_handler.read(256)
  import array as array_module
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
  data=array([y_array, z_array, corrected_data, corrected_error, qy_array, qz_array, 
              data_array, error_array, \
              (qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3])]).transpose()
  data_lines=[data_line[:8] for data_line in data if not data_line[8]]
  #dataobj.number_of_points=1024**2
  #dataobj.data[0].values=y_array.tolist()
  #dataobj.data[1].values=z_array.tolist()
  #dataobj.data[2].values=corrected_data.tolist()
  #dataobj.data[3].values=corrected_error.tolist()
  #dataobj.data[4].values=qy_array.tolist()
  #dataobj.data[5].values=qz_array.tolist()
  #dataobj.data[6].values=data_array.tolist()
  #dataobj.data[7].values=error_array.tolist()
  for data_line in data_lines:
    dataobj.append(data_line)
  dataobj.sample_name=sample_name
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  return [dataobj]
 
def read_edf_file(file_name):
  '''
    Read the binary .edf (european data format) file including header.
    The data is taken from many pictures and summed up. To prevent double
    import the file names already used are stored in a global list.
  '''
  # get a list of files, which belong together
  file_prefix, file_ending=file_name.split('_im_')
  file_postfix=file_ending.split('.', 1)[1] # remove number
  if file_prefix in imported_edfs:
    return 'NULL'
  imported_edfs.append(file_prefix)
  file_list=glob(file_prefix+'_im_'+'*'+'.edf')+glob(file_prefix+'_im_'+'*'+'.edf.gz')
  file_list.sort()
  q_window=[-0.9, 0.9, -0.9, 0.9]
  dataobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                           ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                            [], 4, 5, 3, 2)
  folder, rel_file_name=os.path.split(os.path.realpath(file_name))
  setups=ConfigObj(os.path.join(folder, 'kws2_setup.ini'), unrepr=True)
  for key, value in setups.items():
    if os.path.join(folder, rel_file_name) in glob(os.path.join(folder, key)):
      setup=value
  #if setup['DETECTOR_SENSITIVITY'] and not setup['DETECTOR_SENSITIVITY'] in detector_sensitivities:
  #  read_sensitivities(folder, setup['DETECTOR_SENSITIVITY'])
  #if setup['BACKGROUND'] and not setup['BACKGROUND'] in detector_sensitivities:
  #  read_background(folder, setup['BACKGROUND'])
  
  # Get header information from the first file
  if setup['BACKGROUND']:
    if not setup['BACKGROUND'] in background_data:
      read_background_edf(setup['BACKGROUND'])
    background_array=background_data[setup['BACKGROUND']]
  else:
    background_array=None
  file_name=file_list[0]
  sys.stdout.write('\tReading file 1/%i' % len(file_list))
  sys.stdout.flush()
  if file_name.endswith('.gz'):
    import gzip
    file_handler=gzip.open(file_name, 'rb')
  else:
    file_handler=open(file_name, 'rb')
  header_settings, header_info=read_edf_header(file_handler)
  if setup['CENTER_X']:
    center_x=setup['CENTER_X']
  else:
    center_x=header_info['pixel_x']
  if setup['CENTER_Y']:
    center_y=setup['CENTER_Y']
  else:
    center_y=header_info['pixel_y']
  import array as array_module
  input_array=array_module.array('H')
  #data_array.fromfile(file_handler, header_info['xdim']*header_info['ydim']) # deosn't work with gzip
  input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*2))
  file_handler.close()
  data_arrays=[[array(input_array), header_info['time']]]
  if setup['BACKGROUND']:
    data_arrays[-1][0]-=background_array*data_arrays[-1][1]
  # import all other files and add them together
  for i, file_name in enumerate(file_list[1:]):
    sys.stdout.write('\b'*(len(str(i+1))+len(str(len(file_list))))+'\b%i/%i' % (i+2, len(file_list)))
    sys.stdout.flush()
    if file_name.endswith('.gz'):
      import gzip
      file_handler=gzip.open(file_name, 'rb')
    else:
      file_handler=open(file_name, 'rb')
    header_settings_tmp, header_info_tmp=read_edf_header(file_handler)
    input_array=array_module.array('H')
    #data_array.fromfile(file_handler, header_info['xdim']*header_info['ydim']) # deosn't work with gzip
    input_array.fromstring(file_handler.read(header_info['xdim']*header_info['ydim']*2))
    file_handler.close()
    # add the collected data to the already imported
    data_arrays.append([array(input_array), header_info_tmp['time']])
    if setup['BACKGROUND']:
      data_arrays[-1][0]-=background_array*data_arrays[-1][1]
  sys.stdout.write('\b'*(len(str(i+2))+len(str(len(file_list))))+'\breadout complete!\n')
  sys.stdout.flush()
  sys.stdout.write('\tData Processing 1/%i' % len(file_list))
  sys.stdout.flush()
  # define other quantities for the input data
  x_array=linspace(0, header_info['xdim']**2-1, header_info['xdim']**2)%header_info['ydim']
  y_array=linspace(0, header_info['ydim']**2-1, header_info['ydim']**2)//header_info['ydim']
  error_array=sqrt(data_arrays[0][0])
  corrected_data_array=data_arrays[0][0]/data_arrays[0][1]
  corrected_error_array=error_array/data_arrays[0][1]
  qy_array=4.*pi/header_info['lambda_γ']*\
           sin(arctan((x_array-center_x)*header_info['pixelsize_x']/header_info['detector_distance']/2.))
  qz_array=-4.*pi/header_info['lambda_γ']*\
           sin(arctan((y_array-center_y)*header_info['pixelsize_y']/header_info['detector_distance']/2.))
  use_indices=where(((qy_array<q_window[0])+(qy_array>q_window[1])+\
              (qz_array<q_window[2])+(qz_array>q_window[3]))==0)[0]
  dataobj.number_of_points=len(use_indices)
  dataobj.data[0].values=x_array[use_indices].tolist()
  dataobj.data[1].values=y_array[use_indices].tolist()
  dataobj.data[2].values=corrected_data_array[use_indices].tolist()
  dataobj.data[3].values=corrected_error_array[use_indices].tolist()
  dataobj.data[4].values=qy_array[use_indices].tolist()
  dataobj.data[5].values=qz_array[use_indices].tolist()
  dataobj.data[6].values=data_arrays[0][0][use_indices].tolist()
  dataobj.data[7].values=error_array[use_indices].tolist()
  dataobj.sample_name=header_info['sample_name']
  dataobj.info="#"+"\n#".join([item[1] for item in sorted(header_settings.items())])
  dataobj.short_info="Frame 1"
  dataobj.scan_line=1
  dataobj.scan_line_constant=0
  dataobj.logz=True
  output=[]
  if import_subframes:
    output.append(dataobj)
  sumdata=data_arrays[0][0][use_indices]
  sumtime=data_arrays[0][1]
  tmpa=data_arrays.pop(0)
  del(tmpa)
  # Process all datasets
  for i in range(len(data_arrays)):
    data_seq=data_arrays.pop(0)
    data, time=data_seq
    data=data[use_indices]
    sys.stdout.write('\b'*(len(str(i+1))+len(str(len(file_list))))+'\b%i/%i' % (i+2, len(file_list)))
    sys.stdout.flush()
    if import_subframes:
      addobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                             ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                              [], 4, 5, 3, 2)
      addobj.short_info="Frame %i" % (i+2)
      addobj.number_of_points=len(use_indices)
      addobj.sample_name=header_info['sample_name']
      addobj.info="#"+"\n#".join([item[1] for item in sorted(header_settings.items())])
      addobj.scan_line=1
      addobj.scan_line_constant=0
      addobj.logz=True
      addobj.data[0]=dataobj.data[0]
      addobj.data[1]=dataobj.data[1]
      addobj.data[4]=dataobj.data[4]
      addobj.data[5]=dataobj.data[5]
      error_array=sqrt(data)
      addobj.data[2].values=(data/time).tolist()
      addobj.data[3].values=(error_array/time).tolist()
      addobj.data[6].values=data.tolist()
      addobj.data[7].values=error_array.tolist()
      output.append(addobj)
    sumdata+=data
    sumtime+=time
  sys.stdout.write('\b'*(2*len(str(len(file_list)+1))+1)+'complete!\n')
  sys.stdout.flush()
  # process the sum of datasets
  sumobj=KWS2MeasurementData([['pixel_x', 'pix'], ['pixel_y', 'pix'], ['intensity', 'counts/s'], ['error', 'counts/s'], 
                         ['q_y', 'Å^{-1}'], ['q_z', 'Å^{-1}'], ['raw_int', 'counts'], ['raw_errors', 'counts']], 
                          [], 4, 5, 3, 2)
  sumobj.short_info="Sum of all Frames"
  sumobj.number_of_points=len(use_indices)
  sumobj.sample_name=header_info['sample_name']
  sumobj.info="#"+"\n#".join([item[1] for item in sorted(header_settings.items())])
  sumobj.scan_line=1
  sumobj.scan_line_constant=0
  sumobj.logz=True
  sumobj.data[0]=dataobj.data[0]
  sumobj.data[1]=dataobj.data[1]
  sumobj.data[4]=dataobj.data[4]
  sumobj.data[5]=dataobj.data[5]
  sumerror=sqrt(sumdata)
  sumobj.data[2].values=(sumdata/sumtime).tolist()
  sumobj.data[3].values=(sumerror/sumtime).tolist()
  sumobj.data[6].values=sumdata.tolist()
  sumobj.data[7].values=sumerror.tolist()
  output.insert(0, sumobj)
  print "\tImport complete, ignoring file names belonging to the same series."
  return output

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
    import gzip
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
      import gzip
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
  settings={}
  # Set standart values which are overwritten if found in the header
  info={
      'lambda_γ': 1.771, 
      'xdim': 1024, 
      'ydim': 1024, 
      'sample_name': '', 
      'time': 1., 
      'pixel_x': 512.5, 
      'pixelsize_x': 0.0815,#0.0914, 
      'pixel_y': 512.5, 
      'pixelsize_y': 0.0815,#0.0914, 
      'detector_distance': 102., 
      }
  while '}' not in line:
    if "=" in line:
      key, value= line.split('=', 1)
      key=key.strip()
      value=value.strip().rstrip(';').strip()
      settings[key]=value
    line=file_handler.readline()
  
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
  return settings, info

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
