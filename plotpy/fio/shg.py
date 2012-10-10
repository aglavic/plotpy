# -*- encoding: utf-8 -*-
'''
  Functions to read from SHG data files.
  MeasurementData Object from 'mds' is used to store the data points.
  read_data is the main procedure, returning a list of MeasurementData objects.
'''

# Pleas do not make any changes here unless you know what you are doing.
import os
from plotpy.mds import MeasurementData, PhysicalProperty
import numpy

column_rename={
               'Temp. sample holder': 'T_{sample}',
               'Temp. needle valve': 'T_{cryo}',
               'signal': 'I',

               }

def read_data(file_name):
  '''
    Read the data of a shg parameter file and according data files.
    
    :param file_name: The name of the file to import
    
    :return: list of MeasurementData objects with the file data
  '''
  if not os.path.exists(file_name):
    print 'File '+file_name+' does not exist.'
    return 'NULL'
  global_info, file_infos=read_parameterfile(file_name)
  try:
    global_info['par_index']=int(file_name.split('Nr', 1)[1].split('.', 1)[0])
  except:
    global_info['par_index']=0
  output=[]
  for file_info in file_infos:
    if not os.path.exists(file_info['name']):
      print 'File %s not found.'%file_info['name']
      continue
    output.append(read_dat_file(file_info, global_info))
  return output

def read_parameterfile(file_name):
  '''
    Read information on the measurement from the parameter file.
  '''
  file_text=open(file_name, 'r').read().decode('iso-8859-15')
  prefix=file_name.rsplit('.par', 1)[0]
  global_info={
              'sample': file_text.split('Sample         : ')[1].splitlines()[0],
              'type': file_text.split('Experiment     : ')[1].splitlines()[0],
              'user': file_text.split('Experiment by  : ')[1].splitlines()[0],
              'datetime': file_text.split('Date : ')[1].splitlines()[0]+' '+\
                          file_text.split('Time : ')[1].splitlines()[0],
              'comments': file_text.split('----------')[1],
              }
  # extract measurement specific parameters
  if global_info['type']=='Anisotropy':
    file_infos=[{
                 'name': prefix+'.dat',
                 'polarizer offset': float(file_text.split('Relative angle polariser/analyser : ')[1].split('°', 1)[0]),
                 'index': 1,
                 }]
  else:
    infolines=file_text.split('Configuration :')[1].split('y-devices:')[0].splitlines()[1:]
    while infolines[-1].strip()!='':
      infolines.pop(-1)
    infolines.pop(-1)
    file_infos=[]
    indices=range(len(infolines[0].split(':')[1].split()))
    for index in indices:
      info={}
      file_infos.append(info)
      info['name']=prefix+'_%i.dat'%(index+1)
      info['index']=index+1
      for line in infolines:
        param=line.split(':')[0].strip()
        dim=param.split()[0]
        unit=param.split()[1].strip('[]')
        info[dim]=(float(line.split(':')[1].split()[index]), unit)
  return global_info, file_infos

def read_dat_file(file_info, global_info):
  '''
    Read one .dat file.
  '''
  text_lines=open(file_info['name'], 'r').readlines()
  text_lines=map(lambda line: line.decode('iso-8859-15'), text_lines)
  head_lines=text_lines[:3]
  data='\n'.join(text_lines[3:])
  dimensions=head_lines[2].strip().split('\t')
  units=head_lines[1].strip().split('\t')
  data=numpy.fromstring(data, sep='\t').reshape(-1, len(units))
  cols=[]
  for i, dimension, unit in zip(range(len(units)), dimensions, units)[1:]:
    if dimension in column_rename:
      dimension=column_rename[dimension]
    cols.append(PhysicalProperty(str(dimension), str(unit), data[:, i]))
  if 'Polariser' in file_info:
    pol=file_info['Polariser']
    cols.append(PhysicalProperty('Polariser', str(pol[1]), pol[0]+numpy.zeros_like(cols[0])))
  if 'Analyser' in file_info:
    ana=file_info['Analyser']
    cols.append(PhysicalProperty('Analyser', str(ana[1]), ana[0]+numpy.zeros_like(cols[0])))
  if 'polarizer offset' in file_info:
    for col in cols:
      if col.dimension=='Analyser':
        ana=col
        break
    cols.append((ana+file_info['polarizer offset'])//'Polariser')
  output=MeasurementData()
  output.sample_name="%s - %s "%(global_info['sample'], global_info['type'])
  output.short_info="%i_{%i}:"%(global_info['par_index'], file_info['index'])
  output.data=cols
  output.info="User: %s\nDate: %s\n\nComments:\n%s"%(global_info['user'], global_info['datetime'], global_info['comments'])
  # type specific column settings_3d
  if global_info['type']=='Time':
    Tidx=output.dimensions().index('T_{sample}')
    T=cols[Tidx]
    if (T.max()-T.min())>5:
      output.xdata=Tidx
  if global_info['type'] in ['Polariser', 'Analyser', 'Anisotropy']:
    if global_info['type']=='Polariser':
      output.short_info+=' Analyser at %.0f%s'%file_info['Analyser']
    elif global_info['type']=='Analyser':
      output.short_info+=' Polariser at %.0f%s'%file_info['Polariser']
    else:

      output.short_info+=' Polariser at +%.0f°'%file_info['polarizer offset']
    # plot in polar coordinates
    po=output.plot_options
    po.is_polar=True
    maxI=cols[1].max()
    po.yrange=[None, maxI]
  return output
