# -*- encoding: utf-8 -*-
'''
  class for 4 circle data sessions
'''
#################################################################################################
#                     Script to plot 4Circle-measurements with gnuplot                          #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -import spec .spec files, splitted by sequences                                               #
# -plot every sequence as extra picture or in one graph                                         # 
#    (h,k,l,phi,th,chi scan/mesh found by const. columns)                                       #
# -convert to counts/s                                                                          #
# -plot meshes in 3d                                                                            #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

import os
from time import time
import numpy
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# importing preferences and data readout
import read_data.circle
import config.circle
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.circle', fromlist=['CircleGUI']).CircleGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class CircleSession(GUI, GenericSession):
  '''
    Class to handle 4 circle data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\t4 CIRCLE-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  show_counts=False
  FILE_WILDCARDS=[('4circle','*.spec', '*.spec.gz', '*.fio', '*.fio.gz', 
                    '*.[0-9][0-9][0-9][0-9]', '*.[0-9][0-9][0-9][0-9].gz')]
  mds_create=False
  read_directly=True
  autoreload_active=False
  join_p09=False
  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['counts', 'jp9']
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.TRANSFORMATIONS=config.circle.TRANSFORMATIONS
    GenericSession.__init__(self, arguments)
    if self.join_p09:
      self.join_sequences_p09()
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        found=False
      elif argument=='-counts':
        self.show_counts=True
      elif argument=='-jp9':
        self.join_p09=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      function to read data files
    '''
    datasets=read_data.circle.read_data(file_name)
    if datasets=='NULL':
      return datasets
    for dataset in datasets:
      if 'timescan_cm' in dataset.info:
        self.filter_fast_energyscan_ue64(dataset)
    return datasets



  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to GenericSession short info is set.
    '''
    datasets=GenericSession.add_file(self, filename, append)
    for dataset in datasets:
      dataset.logx=self.logx
      dataset.logy=self.logy
      # name the dataset
      dims=dataset.dimensions()
      set_reciprocal_space=True
      try:
        h_idx=dims.index('H')
        k_idx=dims.index('K')
        l_idx=dims.index('L')
      except ValueError:
        try:
          h_idx=dims.index('h')
          k_idx=dims.index('k')
          l_idx=dims.index('l')
        except ValueError:
          set_reciprocal_space=False
      if set_reciprocal_space:
        hkl=[str(round(dataset.data[h_idx].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
        str(round(dataset.data[k_idx].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
        str(round(dataset.data[l_idx].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0')] # h,k,l information from middle of the Scan with 2 post point digits but with trailing 0 striped      
        if dataset.zdata<0:
          dataset.short_info+=dataset.x.dimension+'-scan around (%s %s %s)' % (hkl[0], hkl[1], hkl[2])
        else:
          dataset.short_info+=dataset.x.dimension+dataset.y.dimension+'-mesh around (%s %s %s)' % (hkl[0], hkl[1], hkl[2])
      if not self.show_counts:
        self.counts_to_cps(dataset)
    return datasets

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def counts_to_cps(self, dataset):
    '''
      Convert couts to couts per second.
    '''
    self.units=dataset.units()
    if not 's' in self.units:
      return
    dataset.process_function(self.counts_to_cps_calc)
    dataset.unit_trans([['counts',1,0,'counts/s']])
  
  def cps_to_counts(self, dataset):
    '''
      Convert couts to couts per second.
    '''
    self.units=dataset.units()
    dataset.process_function(self.cps_to_counts_calc)
    dataset.unit_trans([['counts/s',1,0,'counts']])    
  
  def counts_to_cps_calc(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    time_column=-1
    for i,col in enumerate(input_data): 
  # selection of the columns for counts
      if col.unit=='counts':
        counts_column.append(i)
      if col.unit=='s':
        time_column=i
    if time_column<0:
      return input_data
    for counts in counts_column:
      output_data[counts]/=output_data[time_column]# calculate cps
    return output_data

  def cps_to_counts_calc(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    time_column=0
    for i,col in enumerate(input_data): 
  # selection of the columns for counts
      if col.unit=='counts/s':
        counts_column.append(i)
      if col.unit=='s':
        time_column=i
    for counts in counts_column:
      output_data[counts]=output_data[counts]*output_data[time_column]# calculate cps
    return output_data
  
  def get_ds_hkl(self, dataset, round_by=1):
    '''
      Return the approximate hkl position of one scan.
    '''
    dims=dataset.dimensions()
    h_idx=dims.index('H')
    k_idx=dims.index('K')
    l_idx=dims.index('L')
    h=round(dataset.data[h_idx].mean(), round_by)
    k=round(dataset.data[k_idx].mean(), round_by)
    l=round(dataset.data[l_idx].mean(), round_by)
    return (h, k, l)
  
  def join_sequences_p09(self):
    '''
      Combine scans to one file_data entry, which are around the same HKL position.
    '''
    datasets=self.file_data.items()
    datasets.sort()
    start_name=datasets[0][0]
    last_name=start_name
    start_hkl=self.get_ds_hkl(datasets[0][1][0])
    joint=datasets[0][1]
    del(self.file_data[start_name])
    for name, data in datasets[1:]:
      del(self.file_data[name])
      hkl=self.get_ds_hkl(data[0])
      if hkl==start_hkl:
        joint+=data
        last_name=name
      else:
        if last_name==start_name:
          self.file_data[last_name]=joint
        else:
          if self.compare_types_p09(joint):
            self.file_data[start_name+'-'+os.path.split(last_name)[1]]=self.create_mesh(joint)
          else:
            self.file_data[start_name+'-'+os.path.split(last_name)[1]]=joint
        joint=data
        start_name=name
        last_name=name
        start_hkl=hkl
    if last_name==start_name:
      self.file_data[last_name]=joint
    else:
      if self.compare_types_p09(joint):
        self.file_data[start_name+'-'+os.path.split(last_name)[1]]=self.create_mesh(joint)
        self.active_file_data=self.file_data[start_name+'-'+os.path.split(last_name)[1]]
      else:
        self.file_data[start_name+'-'+os.path.split(last_name)[1]]=joint

  def compare_types_p09(self, datasets):
    '''
      Check if all scans have the same scan type.
    '''
    type1=datasets[0].x.dimension
    if not type1.endswith('-Scan'):
      return False
    for dataset in datasets:
      if dataset.x.dimension==type1:
        continue
      else:
        return False
    return True
  
  def filter_fast_energyscan_ue64(self, dataset):
    '''
      Remove points with wrong energy reading from the fast E-scan performed at ue64.
    '''
    tolerance=10
    try:
      from scipy.interpolate import interp1d
      interpolate=True
    except ImportError:
      interpolate=False
    from measurement_data_structure import PhysicalProperty
    x=dataset.x.tolist()
    idxs=[]
    x_index=dataset.xdata
    old_length=len(dataset)
    for i in range(1, old_length-1):
      if abs(x[i]-x[i-1])<tolerance and abs(x[i]-x[i+1])<tolerance:
        idxs.append(i)
    idxs=numpy.array(idxs)
    new_x=numpy.arange(x[0], x[-1], (x[-1]-x[0])/len(x))
    filter_x=dataset.x[idxs]
    if len(idxs)<10:
      return 0
    if interpolate:
      for i, col in enumerate(dataset.data):
        if i==x_index:
          dataset.data[i]=PhysicalProperty(col.dimension, col.unit, new_x)
        else:
          f=interp1d(filter_x, col[idxs], bounds_error=False, fill_value=col[idxs].min())
          dataset.data[i]=PhysicalProperty(col.dimension, col.unit, f(new_x))
    else:
      for i, col in enumerate(dataset.data):
        dataset.data[i]=PhysicalProperty(col.dimension, col.unit, col[idxs])
    return old_length-len(idxs)
  
  def create_mesh(self, datasets):
    '''
      Combine a list of scans to one mesh.
    '''
    import measurement_data_structure
    cols=datasets[0].dimensions()
    # define the scanned columns
    h, k, l=self.get_ds_hkl(datasets[0], 3)
    h2, k2, l2=self.get_ds_hkl(datasets[-1], 3)
    if datasets[0].x.dimension.startswith('H'):
      xids=cols.index('H')
      if k==k2:
        if l==l2:
          return datasets
        yids=cols.index('L')
        output_info='HL-Mesh'
      else:
        yids=cols.index('K')
        output_info='HK-Mesh'
    elif datasets[0].x.dimension.startswith('K'):
      xids=cols.index('K')
      if l==l2:
        if h==h2:
          return datasets
        yids=cols.index('H')
        output_info='HK-Mesh'
      else:
        yids=cols.index('L')
        output_info='KL-Mesh'
    elif datasets[0].x.dimension.startswith('L'):
      xids=cols.index('L')
      if k==k2:
        if h==h2:
          return datasets
        yids=cols.index('H')
        output_info='HL-Mesh'        
      else:
        yids=cols.index('K')
        output_info='KL-Mesh'
    #combine the datasets
    output=measurement_data_structure.MeasurementData(x=xids, y=yids, zdata=datasets[0].ydata)
    output.short_info+=output_info
    output.sample_name=datasets[0].sample_name+'-'+datasets[-1].sample_name
    for col in datasets[0].data:
      output.append_column(col.copy())
    for j, dataset in enumerate(datasets[1:]):
      for i, col in enumerate(dataset.data):
        if j%2==0:
          output.data[i].append(col[numpy.arange(len(col)-1, -1)])
        else:
          output.data[i].append(col)
    output.number='0'
    output.scan_line=xids
    output.scan_line_constant=yids
    #order=numpy.lexsort(keys=(output.x, output.y))
    #for i, col in enumerate(output.data):
    #  output.data[i]=col[order]
    return [output]
  
