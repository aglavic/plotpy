# -*- encoding: utf-8 -*-
'''
 Classes for storing the measurement data of any session.
 Units and dimensions are also stored for easier accessing and transformation.
'''

# Pleas do not make any changes here unless you know what you are doing.

from sys import hexversion
import os
from shutil import copyfile
from copy import deepcopy
from cPickle import load, dump
import numpy
from tempfile import gettempdir

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta3"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

hmd_file_number=0
TEMP_DIR=gettempdir()

#++++++++++++++++++++++++++++++++++++++MeasurementData-Class+++++++++++++++++++++++++++++++++++++++++++++++++++++#
class MeasurementData(object):
  '''
    The main class for the data storage. Stores the data as a list of
    PhysicalProperty objects. Sample name and measurement informations
    are stored as well as plot options and columns which have to stay
    constant in one sequence.
  '''
  number_of_points=0 #count number of stored data-points
  index=0
  # every data value is a pysical property
  data=[]
  # for plotting the measurement select x and y data
  xdata=0
  ydata=0
  yerror=0
  zdata=-1
  # Logarithmic scale plotting
  logx=False
  logy=False
  logz=False
  crop_zdata=True # Crop the z-range values to the selected plot range
  scan_line_constant=-1 # the column to sort the data for when using 3d plots.
  scan_line=-1 # the column changed in one scan.
  const_data=[] # select, which data should not be varied in this maesurement and the accouracy
  info=''
  short_info=''
  number=''
  sample_name=''
  # view angle for the 3d plot
  view_x=60
  view_z=30
  filters=[] # a list of filters to be applied when returning the data, the format is:
             # ( column , from , to , include )
  SPLIT_SENSITIVITY=0.01

  def __init__(self, columns, const,x,y,yerror,zdata=-1): 
    '''
      Constructor for the class.
      If the values are not reinitialized we get problems
      with the creation of objects with the same variable name.
      
      @param columns List of columns [(Unit, Dim), ...] in this object
      @param const List of constant colums for a sequence
      @param x Index of x column
      @param y Index of y column
      @param yerror Index of error column
      @param zdata Index of z column or -1 for None
    '''
    self.number_of_points=0 #counts number of stored data-points
    self.index=0
    self.info=''
    self.sample_name=''
    self._plot_options=PlotOptions()
    self.data=[]
    for column in columns: # create Property for every column
      self.data.append(PhysicalProperty(column[0],column[1]))
    self.xdata=x
    self.ydata=y
    self.zdata=zdata
    self.view_x=0 #3d view point
    self.view_z=0
    self.logx=False
    self.logy=False
    self.yerror=yerror
    self.const_data=[]
    for con in const: # create const_data column,Property for every const
      self.const_data.append([con[0],PhysicalProperty(self.data[con[0]].dimension,self.data[con[0]].unit)])
      self.const_data[-1][1].append(con[1])
    self.plot_together=[self] # list of datasets, which will be plotted together
    self.fit_object=None

  def __iter__(self): # see next()
    '''
      Function to iterate through the data-points, object can be used in "for bla in data:".
      Skippes pointes that are filtered.
    '''
    data=self.get_filtered_data_matrix().transpose().tolist()
    for point in data:
      # return the next datapoint
      yield point

  def get_filtered_data_matrix(self):
    '''
      Return the data as numpy array with applied filters.
      
      @return numpy array of point lists
    '''
    #try:
    data=numpy.array([col.values for col in self.data])
    #except ValueError:
     # min_length=min([len(col.values) for col in self.data])
      #data=numpy.array([col.values[:min_length] for col in self.data])
    filters=self.filters
    for data_filter in filters:
      filter_column=data[data_filter[0]]
      filter_from, filter_to=data_filter[1:3]
      if filter_from>filter_to:
        filter_from=data_filter[2]
        filter_to=data_filter[1]
      if data_filter[3]:
        if filter_from is None:
          filter_from=filter_column.min()
        if filter_to is None:
          filter_to=filter_column.max()
        data_indices=numpy.where(1-((filter_column<filter_from)+(filter_column>filter_to)))
      else:
        if filter_from is None:
          filter_from=filter_column.max()
        if filter_to is None:
          filter_to=filter_column.min()
        data_indices=numpy.where(((filter_column>filter_to)+(filter_column<filter_from)))
      data=data.transpose()[data_indices].transpose()
    return data

  def __getstate__(self):
    '''
      Define how the class is pickled and copied.
    '''
    self.preview=None
    return self.__dict__
 
  def __len__(self): 
    '''
      len(MeasurementData) returns number of Datapoints.
    '''
    return len(self.data[0])

  def __getitem__(self, index):
    '''
      MeasurementData[index] returns one datapoint.
    '''
    return self.get_data(index)
  
  def __getslice__(self, start, end):
    '''
      MeasurementData[start:end] returns a list of datapoints.
    '''
    if start<0:
      start=max(0, self.number_of_points+start)
    if end<0:
      end=max(0, self.number_of_points+end)
    else:
      end=min(self.number_of_points, end)
    region=range(start, end)
    return [point for i, point in enumerate(self) if i in region]

  def get_plot_options(self): return self._plot_options
  
  def set_plot_options(self, input):
    '''
      Set the PlotOptions object from a string or item input.
    '''
    if type(input) is str:
      self._plot_options=PlotOptions(input)
    elif type(input) is PlotOptions:
      self._plot_options=input
    else:
      raise TypeError, "plot_options has to be of type PlotOptions or String"

  plot_options=property(get_plot_options, set_plot_options)

  def append(self, point):
    '''
      Add a point to this sequence.
      
      @param point List of entries by columns
      
      @return The added point or 'NULL' if an error has occured
    '''
    data=self.data # speedup data_lookup
    append_fast=list.append
    if len(point)==len(data):
      for i,val in enumerate(point):
        append_fast(data[i].values, val)
      self.number_of_points+=1
      return point
    else:
      return 'NULL'

  def append_column(self, column, dimension="", unit=""):
    '''
      Append a new column to the datastructure.
      If the column is already a PhysicalProperty, a copy
      of it is used, otherwise a new PhysicalProperty object
      is created with the column data.
    '''
    if len(column)!=len(self):
      return False
    if getattr(column, "unit", False) and getattr(column, "dimension", False):
      self.data.append(deepcopy(column))
      return True
    else:
      col=PhysicalProperty(dimension, unit)
      col.values=list(column)
      self.data.append(col)
      return True

  def get_data(self,count): 
    '''
      Get datapoint at index count.
      
      @return List of values at this index
    '''
    return [value.values[count] for value in self.data]

  def set_data(self,point,count): 
    '''
      Set data point at position count.
    '''
    for value in self.data:
      value.values[count]=point[self.data.index(value)]

  def list(self): 
    '''
      Get x-y-(z) list of all data points.
      If x or y columns are negative the index is returned instead
    '''
    xd=self.xdata
    yd=self.ydata
    zd=self.zdata
    if (xd>=0) and (yd>=0):
      if (zd<0):
        return [[point[xd],point[yd]] for point in self]
      return [[point[xd],point[yd],point[zd]] for point in self]
    elif yd>=0:
      return [[i+1,point[yd]] for i,point in enumerate(self)]
    elif xd>=0:
      return [[point[xd],i+1] for i,point in enumerate(self)]
    return [[i+1,i+1] for i,point in enumerate(self)]

  def list_err(self): 
    '''
      Get x-y-dy list of all data.
      If x or y columns are negative the index is returned instead
    '''
    xd=self.xdata
    yd=self.ydata
    ye=self.yerror
    zd=self.zdata
    if ye<0:
      return [point.append(0) for point in self.list()]
    if (xd>=0) and (yd>=0):
      if (zd<0):
        return [[point[xd], point[yd], point[ye]] for point in self]
      return [[point[xd], point[yd], point[zd], point[ye]] for point in self]
    elif yd>=0:
      return [[i+1, point[yd], point[ye]] for i,point in enumerate(self)]
    elif xd>=0:
      return [[point[xd], i+1, point[ye]] for i,point in enumerate(self)]
    return [[i+1,i+1, point[ye]] for i,point in enumerate(self)]

  def listxy(self,x,y): 
    '''
      Get x-y list of data with different x,y values.
    '''
    return [[point[x],point[y]] for point in self]

  def type(self): 
    '''
      Short form to get the first constant data column.
    '''
    if len(self.const_data)>0:
      return self.const_data[0][0]
    else:
      return 0

  def first(self): 
    '''
      Return the first datapoint.
    '''
    return self.get_data(0)

  def last(self): 
    '''
      Return the last datapoint.
    '''
    return self.get_data(self.number_of_points-1)

  def is_type(self, dataset): 
    '''
      Check if a point is consistant with constand data of this sequence.
    '''
    last=self.last()
    for const in self.const_data:
      if (abs(dataset[const[0]]-last[const[0]])<const[1].values[0]):
        continue
      else:
        return False
    return True

  def units(self): 
    '''
      Return units of all columns.
    '''
    return [value.unit for value in self.data]

  def dimensions(self): 
    '''
      Return dimensions of all columns-
    '''
    return [value.dimension for value in self.data]

  def xunit(self): 
    '''
      Get unit of xcolumn.
    '''
    return self.units()[self.xdata]

  def yunit(self): 
    '''
      Get unit of ycolumn.
    '''
    return self.units()[self.ydata]

  def zunit(self): 
    '''
      Get unit of ycolumn.
    '''
    return self.units()[self.zdata]

  def xdim(self): 
    '''
      Get dimension of xcolumn.
    '''
    return self.dimensions()[self.xdata]

  def ydim(self): 
    ''' 
      Get dimension of ycolumn.
    '''
    return self.dimensions()[self.ydata]

  def zdim(self): 
    '''
      Get dimension of ycolumn.
    '''
    return self.dimensions()[self.zdata]

  def unit_trans(self,unit_list): 
    '''
      Change units of all columns according to a given list of translations.
      
      @return List of new dimensions and units
    '''
    for unit in unit_list:
      for value in self.data:
        if len(unit)==4:
          value.unit_trans(unit)
        else:
          value.dim_unit_trans(unit)
      if len(unit)==4:
        for con in self.const_data:
          con[1].unit_trans(unit)
      else:
        for con in self.const_data:
          con[1].dim_unit_trans(unit)
    return [self.dimensions(),self.units()]

  def unit_trans_one(self,col,unit_list): 
    '''
      Change units of one column according to a given list of translations and
      return this column.
      
      @return The changed column and the applied translation
    '''
    from copy import deepcopy
    data=deepcopy(self.data[col])
    unit_used=None
    for unit in unit_list:
      if len(unit)==4:
        transformed=data.unit_trans(unit)
      else:
        transformed=data.dim_unit_trans(unit)
      if transformed:
        unit_used=unit[-1]
#    for con in self.const_data:
#      if con[0]==col:
#        if len(unit)==4:
#            con[1].unit_trans(unit)
#        else:
#            con[1].dim_unit_trans(unit)
    return data.values[-1], unit_used

  # When numpy is accessible use a faster array approach
  def process_function_nonumpy(self,function): 
    '''
      Processing a function on every data point.
      
      @param function Python function to execute on each point
      
      @return Last point after function execution
    '''
    for i in range(self.number_of_points):
      point = self.get_data(i)
      self.set_data(function(point),i)
    return self.last()

  def process_function(self,function): 
    '''
      Processing a function on every data point.
      When numpy is installed this is done via one proccess call 
      for arrays. (This leads to a huge speedup)
      
      @param function Python function to execute on each point
      
      @return Last point after function execution
    '''
    try:
      arrays=[]
      for column in self.data:
        array=numpy.array(column.values)
        arrays.append(array)
      processed_arrays=function(arrays)
      for i, array in enumerate(processed_arrays):
        self.data[i].values=list(array)
    except: # if the function does not work with arrays the conventional method is used.
      self.process_function_nonumpy(function)
    return self.last()

  def sort(self, column=None):
    '''
      Sort the datapoints for one column.
    '''
    if column is None:
      column=self.xdata
    data_list=[point for point in self]    
    def sort_by_column(point1, point2):
      return cmp(point1[column], point2[column])
    data_list.sort(sort_by_column)
    for i, point in enumerate(data_list):
      self.set_data(point, i)

  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None, only_fitted_columns=False): 
    '''
      Write data in text file.
      
      @param file_name Name of the export file
      @param print_info Put a header ontop of the data
      @param seperator Seperator characters to be used between columns
      @param xfrom Start value of x for the export
      @param xto End value of x for the export
      @param only_fitted_columns Only export columns used for fitting.
      
      @return The number of data lines exported
    '''
    xd=self.xdata
    yd=self.ydata
    zd=self.zdata
    ed=self.yerror
    SPLIT_SENSITIVITY=self.SPLIT_SENSITIVITY
    data=self.get_filtered_data_matrix()
    if not xto:
      xto=data[xd].max()
    data_window=numpy.where((1-((data[xd]<xfrom) + (data[xd]>xto))))[0]
    data=data.transpose()[data_window].transpose()
    if only_fitted_columns:
      if zd>=0:
        data=data[numpy.array([xd, yd, zd, ed])]
      else:
        data=data[numpy.array([xd, yd, ed])]
    split_indices=numpy.array([])
    if zd>=0:
      # crop data to prevent white holes in the plot
      if self.crop_zdata:
        absmin, absmax=self.plot_options.zrange
        if absmin is None:
          absmin=numpy.nan_to_num(data[zd]).min()
        if absmax is None:
          absmax=numpy.nan_to_num(data[zd]).max()
        if self.logz:
          if not absmin > 0:
            absmin=(numpy.abs(numpy.nan_to_num(data[zd]))).min()
          if absmin==0:
            absmin=1e-10
        data[zd]=numpy.where(data[zd]>=absmin, data[zd], absmin)
        data[zd]=numpy.where(data[zd]<=absmax, data[zd], absmax)
      # for large datasets just export points lying in the plotted region
      #if len(data[0])>10000:
        #xrange=self.plot_options.xrange
        #yrange=self.plot_options.yrange
        #if xrange[0] is not None:
          #indices=numpy.where(data[xd]>=xrange[0])[0]
          #data=data.transpose()[indices].transpose()
        #if xrange[1] is not None:
          #indices=numpy.where(data[xd]<=xrange[1])[0]
          #data=data.transpose()[indices].transpose()
        #if yrange[0] is not None:
          #indices=numpy.where(data[yd]>=yrange[0])[0]
          #data=data.transpose()[indices].transpose()
        #if yrange[1] is not None:
          #indices=numpy.where(data[yd]<=yrange[1])[0]
          #data=data.transpose()[indices].transpose()
      # get the best way to sort and split the data for gnuplot
      if self.scan_line_constant<0:
        x_sort_indices=self.rough_sort(data[xd], data[yd], SPLIT_SENSITIVITY)
        y_sort_indices=self.rough_sort(data[yd], data[xd], SPLIT_SENSITIVITY)
        sorted_x=data.transpose()[x_sort_indices].transpose()
        sorted_y=data.transpose()[y_sort_indices].transpose()
        #max_dx=(data[xd][1:]-data[xd][:-1]).max()
        #max_dy=(data[xd][1:]-data[xd][:-1]).max()
        split_indices_x=numpy.where(sorted_x[yd][:-1]>sorted_x[yd][1:])[0]
        split_indices_y=numpy.where(sorted_y[xd][:-1]>sorted_y[xd][1:])[0]
        if len(split_indices_x)<=len(split_indices_y):
          split_indices=split_indices_x+1
          data=sorted_x
        else:
          split_indices=split_indices_y+1
          data=sorted_y
      else:
        sort_indices=self.rough_sort(data[self.scan_line_constant], data[self.scan_line], SPLIT_SENSITIVITY)
        data=data.transpose()[sort_indices].transpose()
        split_indices=numpy.where(data[self.scan_line][:-1]>data[self.scan_line][1:])[0]+1
    split_indices=split_indices.tolist()+[len(data[0])]
    data=data.transpose()
    # write data to file
    write_file=open(file_name,'w')
    if print_info:
      write_file.write('# exportet dataset from measurement_data_structure.py\n# Sample: '+self.sample_name+'\n#\n# other informations:\n#'+self.info.replace('\n','\n#'))
      columns=''
      for i in range(len(self.data)):
        columns=columns+' '+self.dimensions()[i]+'['+self.units()[i]+']'
      write_file.write('#\n#\n# Begin of Dataoutput:\n#'+columns+'\n')
    #self.write_data_matrix(write_file, data, split_indices)
    self.write_data_matrix2(write_file, data, split_indices)
    write_file.write('\n')
    write_file.close()
    return split_indices[-1] # return the number of exported data lines

  def rough_sort(self, ds1, ds2, sensitivity):
    '''
      Return the sorting index from a first and second column ignoring small
      differences.
    '''
    srt_run1=numpy.lexsort(keys=(ds2, ds1))
    ds1_run1=ds1[srt_run1]
    max_step=(ds1_run1[1:]-ds1_run1[:-1]).max()
    abs_sensitivity=max_step*sensitivity
    small_step_indices=numpy.where(((ds1_run1[1:]-ds1_run1[:-1])<abs_sensitivity)*((ds1_run1[:-1]-ds1_run1[1:])!=0))
    for i, index in enumerate(small_step_indices[1:]):
      from_data=ds1_run1[i+1]
      to_data=ds1_run1[i]
      ds1=numpy.where(ds1==from_data, ds1, to_data)
    srt_run2=numpy.lexsort(keys=(ds2, ds1))
    return srt_run2

  def write_data_matrix(self, write_file, data, split_indices, seperator=" "):
    '''
      Write a given matrix of data to a file object.
    '''
    
    numpy.savetxt(write_file, data[:split_indices[0]], fmt='%g', delimiter=seperator)
    write_file.write('\n')
    for i, split_i in enumerate(split_indices[1:]):
      numpy.savetxt(write_file, data[split_indices[i]:split_i], fmt='%.6g', delimiter=seperator)
      write_file.write('\n')

  def write_data_matrix2(self, write_file, data, split_indices):
    '''
      Write a given matrix of data to a file object.
    '''
    lines, cols=data.shape
    # convert data to a log 1d array
    data=numpy.nan_to_num(data.reshape(lines*cols))
    output_line=("%g "*cols)[:-1]
    output_list=["\n".join([output_line for j in range(split_indices[0])])]
    for i, split_i in enumerate(split_indices[1:]):
      output_list.append("\n".join([output_line for j in range(split_i-split_indices[i])]))
    output=("\n\n".join(output_list)) % tuple(data)
    write_file.write(output)

  def max(self,xstart=None,xstop=None): 
    '''
      Returns x and y value of point with maximum x.
    '''
    if xstart==None:
      xstart=self.data[self.xdata].min()
    if xstop==None:
      xstop=self.data[self.xdata].max()
    from_index=0
    to_index=len(self)-1
    for i,value in enumerate(self.data[self.xdata].values):
      if value<=xstart:
        from_index=i
      if self.data[self.xdata].values[-1-i]>=xstop:
        to_index=len(self)-1-i
    max_point=self.data[self.ydata].values.index(self.data[self.ydata].max(from_index,to_index))
    return [self.data[self.xdata].values[max_point],self.data[self.ydata].values[max_point]]

  def min(self,xstart=None,xstop=None): 
    '''
      Returns x and y value of point with minimum x.
    '''
    if xstart==None:
      xstart=self.data[self.xdata].min()
    if xstop==None:
      xstop=self.data[self.xdata].max()
    from_index=0
    to_index=len(self)-1
    for i,value in enumerate(self.data[self.xdata].values):
      if value<=xstart:
        from_index=i
      if self.data[self.xdata].values[-1-i]>=xstop:
        to_index=len(self)-1-i
    max_point=self.data[self.ydata].values.index(self.data[self.ydata].min(from_index,to_index))
    return [self.data[self.xdata].values[max_point],self.data[self.ydata].values[max_point]]


#--------------------------------------MeasurementData-Class-----------------------------------------------------#

#++++++++++++++++++++++++++++++++++++++    HugeMD-Class     +++++++++++++++++++++++++++++++++++++++++++++++++++++#

class HugeMD(MeasurementData):
  '''
    For huge datasets (50 000 points +) this datastructure uses a arbitrary temporary file to sotre exported data.
    The data is only reexported after a change or changes to the filters.
  '''
  
  changed_after_export=True
  tmp_export_file=''
  _last_datapoint=None
  _filters=[]
  _data=[]
  
  # When filters have changed the data has to be reexported
  def get_filters(self):
    return self._filters
  def set_filters(self, value):
    self.changed_after_export=True
    self._filters=value    
  filters=property(get_filters, set_filters)
  
  # since these objects can store a lot of data (Several MB per object) it is a huge memory saving
  # to pickle the data and unpickle it when it is needed
  
  def get_data_object(self):
    return self._data
  def set_data_object(self, object):
    self._data=object
    self.store_data()
  
  data=property(get_data_object, set_data_object)
  
  def store_data(self):
    '''
      Pickle the data in this object to save memory.
    '''
    self._last_datapoint=MeasurementData.last(self)
    for i, d in enumerate(self._data):
      if type(d) is not HugePhysicalProperty:
        self._data[i]=HugePhysicalProperty(d)
        del(d)
        d=self._data[i]
      d.store_data()
  
  def last(self):
    if self._last_datapoint:
      return self._last_datapoint
    else:
      return MeasurementData.last(self)
  
  def __init__(self, *args, **opts):
    global hmd_file_number
    self.tmp_export_file=os.path.join(TEMP_DIR, 'HMD_'+ str(hmd_file_number)+ '.tmp')
    hmd_file_number+=1
    MeasurementData.__init__(self, *args, **opts)
  
  def __getstate__(self):
    '''
      Define how the class is pickled and copied.
    '''
    self.changed_after_export=True
    return MeasurementData.__getstate__(self)
 
  def __setstate__(self, state):
    '''
      Unpickling the object will set a new temp file name.
    '''
    self.__dict__=state
    global hmd_file_number
    self.tmp_export_file=os.path.join(TEMP_DIR, 'HMD_'+ str(hmd_file_number)+ '.tmp')
    hmd_file_number+=1

  def __del__(self):
    '''
      Cleanup after delition of this object.
    '''
    tmp_export_file=self.tmp_export_file
    del self.__dict__
    try:
      os.remove(tmp_export_file)
    except OSError:
      pass

  def process_function(self, function):
    '''
      Wrapper to MeasurementData.process_function which sets the data to be reexported after change.
    '''
    self.changed_after_export=True
    output=MeasurementData.process_function(self, function)
    self.store_data()
    return output
  
  def unit_trans(self, unit_list):
    '''
      Wrapper to MeasurementData.unit_trans which sets the data to be reexported after change.
    '''
    self.changed_after_export=True
    output=MeasurementData.unit_trans(self, unit_list)
    self.store_data()
    return output
    
  def unit_trans_one(self, col, unit_lit):
    '''
      Wrapper to MeasurementData.unit_trans_one which sets the data to be reexported after change.
    '''
    self.unit_trans_one=True
    output=MeasurementData.unit_trans_one(self, col, unit_lit)
    self.store_data()
    return output
  
  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None, only_fitted_columns=False): 
    if self.changed_after_export or self.plot_options.zrange!=self.last_export_zrange:
      print "Exporting large dataset, please stay patient"
      self.last_export_output=self.do_export(self.tmp_export_file, print_info, seperator, xfrom, xto, only_fitted_columns)
      self.changed_after_export=False
      self.last_export_zrange=self.plot_options.zrange
      self.store_data()
    copyfile(self.tmp_export_file,  file_name)
    return self.last_export_output
  
  do_export=MeasurementData.export

#--------------------------------------    HugeMD-Class     -----------------------------------------------------#

class PhysicalProperty:
  '''
    Class for any physical property. Stores the data, unit and dimension
    to make unit transformations possible.
  '''
  index=0
  values=[]
  unit=''
  dimension=''
  
  def __init__(self, dimension_in, unit_in):
    '''
      Class constructor.
    '''
    self.values=[]
    self.index=0
    self.unit=unit_in
    self.dimension=dimension_in

  def __iter__(self): # see next()
    return self
 
  def next(self): 
    '''
      Function to iterate through the data-points, object can be used in "for bla in data:".
    '''
    if self.index == len(self.values):
      self.index=0
      raise StopIteration
    self.index=self.index+1
    return self.values[self.index-1]

  def __len__(self): 
    '''
      len(PhysicalProperty) returns number of Datapoints.
    '''
    return len(self.values)

  def append(self, number): 
    '''
      Add value.
    '''
    self.values.append(number)

  def unit_trans(self,transfere): 
    '''
      Transform one unit to another. transfere variable is of type [from,b,a,to].
    '''
    if transfere[0]==self.unit: # only transform if right 'from' parameter
      new_values=[]
      for value in self.values:
        new_values.append(value*transfere[1]+transfere[2])
      self.values=new_values
      self.unit=transfere[3]
      return True
    else:
      return False

  def dim_unit_trans(self,transfere): 
    '''
      Transform dimension and unit to another. Variable transfere is of type
      [from_dim,from_unit,b,a,to_dim,to_unit].
    '''
    if len(transfere)>0 and (transfere[1]==self.unit)&(transfere[0]==self.dimension): # only transform if right 'from_dim' and 'from_unit'
      new_values=[]
      for value in self.values:
        new_values.append(value*transfere[2]+transfere[3])
      self.values=new_values
      self.unit=transfere[5]
      self.dimension=transfere[4]
      return True
    else:
      return False

  def max(self,from_index=0,to_index=None):
    '''
      Return maximum value in data.
    '''
    if to_index==None:
      to_index=len(self)-1
    return max([self.values[i] for i in range(from_index,to_index)])

  def min(self,from_index=0,to_index=None):
    '''
      Return minimum value in data.
    '''
    if to_index==None:
      to_index=len(self)-1
    return min([self.values[i] for i in range(from_index,to_index)])

class HugePhysicalProperty(object, PhysicalProperty):
  '''
    PhysicalProperty which can write data to a pickled file if it is not accessed.
  '''
  _values=None
  store_file=''
  
  def get_values(self):
    if self._values is None:
      self._values=load(open(self.store_file, 'rb'))
    return self._values
  def set_values(self, values):
    self._values=values
  values=property(get_values, set_values)
  
  def store_data(self):
    '''
      Store the data in a pickled file and delete the object to save memory.
    '''
    if self._values is not None:
      dump(self._values, open(self.store_file, 'wb'), -1)
      del(self._values)
      self._values=None
  
  def __init__(self, physprop_in):
    '''
      Class constructor.
    '''
    self.values=physprop_in.values
    self.index=physprop_in.index
    self.unit=physprop_in.unit
    self.dimension=physprop_in.dimension
    global hmd_file_number
    self.store_file=os.path.join(TEMP_DIR, 'HMD_'+ str(hmd_file_number)+'.pkl')
    hmd_file_number+=1
  
  def __getstate__(self):
    '''
      What to do when pickling the data.
    '''
    # restore the dataset
    self.values
    return self.__dict__
  
  def __setstate__(self, state):
    self.__dict__=state
    #assign a new temp file name
    global hmd_file_number
    self.store_file=os.path.join(TEMP_DIR, 'HMD_'+ str(hmd_file_number)+'.pkl') 
    hmd_file_number+=1
  
  def __del__(self):
    '''
      Clean up temporary file after delition.
    '''
    store_file=self.store_file
    del self.__dict__
    os.remove(store_file)

class PlotOptions(object):
  '''
    Object for storing information about the illustration of the data in the plot.
  '''
  special_plot_parameters=None
  special_using_parameters=""
  splot=''
  
  def __init__(self, initial_text=""):
    '''
      Initialize the object with optional start parameters.
    '''
    self.settings={}
    self.free_input=[]
    self._xrange=[None, None]
    self._yrange=[None, None]
    self._zrange=[None, None]
    self.input_string(initial_text)

  def __str__(self):
    '''
      Return the settings as a string.
    '''
    output=""
    for key, items in self.settings.items():
      for value in items:
        output+="set "+key+" "+value+"\n"
    for value in self.free_input:
      output+=value+"\n"
    output+=("set xrange [%s:%s]\n" % (self._xrange[0], self._xrange[1] )).replace("None", "")
    output+=("set yrange [%s:%s]\n" % (self._yrange[0], self._yrange[1] )).replace("None", "")
    output+=("set zrange [%s:%s]\n" % (self._zrange[0], self._zrange[1] )).replace("None", "")
    output+=("set cbrange [%s:%s]\n" % (self._zrange[0], self._zrange[1] )).replace("None", "")
    return output
  
  def __add__(self, input_string):
    '''
      Joing own string with other string.
    '''
    return str(self) + input_string
  
  def __radd__(self, input_string):
    '''
      Joing own string with other string.
    '''
    return input_string + str(self) 
  
  def input_string(self, text):
    '''
      Get setting information from a text.
    '''
    lines=text.splitlines()
    for line in lines:
      if line.startswith("set"):
        split=line.split(" ", 2)
        if len(split)==2:
          split.append('')
        if split[1] not in ["xrange", "yrange", "zrange", "cbrange"]:
          if split[1] in self.settings:
            self.settings[split[1]].append(split[2])
          else:
            self.settings[split[1]]=[split[2]]
        elif split[1]=="xrange":
          try:
            subsplit=split[2].split(":")
            xfrom=subsplit[0].lstrip("[")
            xto=subsplit[1].rstrip("]")
            self.xrange=[xfrom, xto]
          except:
            pass
        elif split[1]=="yrange":
          try:
            subsplit=split[2].split(":")
            yfrom=subsplit[0].lstrip("[")
            yto=subsplit[1].rstrip("]")
            self.yrange=[yfrom, yto]
          except:
            pass
        elif split[1] in ["zrange", "cbrange"]:
          try:
            subsplit=split[2].split(":")
            zfrom=subsplit[0].lstrip("[")
            zto=subsplit[1].rstrip("]")
            self.zrange=[zfrom, zto]
          except:
            pass
      else:
        self.free_input.append(line)
      

  def get_xrange(self): return self._xrange  
  def get_yrange(self): return self._yrange
  def get_zrange(self): return self._zrange
  def set_xrange(self, range): 
    if len(range)==2:
      try:
        xrange=[None, None]
        if range[0]:
          xrange[0]=float(range[0])
        if range[1]:
          xrange[1]=float(range[1])
        self._xrange=xrange
      except ValueError:
        raise ValueError, 'xrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, 'xrange has to be a tuple or list with two elements of float or None'

  def set_yrange(self, range): 
    if len(range)==2:
      try:
        yrange=[None, None]
        if range[0]:
          yrange[0]=float(range[0])
        if range[1]:
          yrange[1]=float(range[1])
        self._yrange=yrange
      except ValueError:
        raise ValueError, 'yrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, 'yrange has to be a tuple or list with two elements of float or None'

  def set_zrange(self, range): 
    if len(range)==2:
      try:
        zrange=[None, None]
        if range[0]:
          zrange[0]=float(range[0])
        if range[1]:
          zrange[1]=float(range[1])
        self._zrange=zrange
      except ValueError:
        raise ValueError, 'zrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, 'zrange has to be a tuple or list with two elements of float or None'


  xrange=property(get_xrange, set_xrange)
  yrange=property(get_yrange, set_yrange)
  zrange=property(get_zrange, set_zrange)