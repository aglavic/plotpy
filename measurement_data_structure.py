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
from config.transformations import known_unit_transformations

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

hmd_file_number=0
TEMP_DIR=gettempdir()

#++++++++++++++++++++++++++++++++++++++MeasurementData-Class+++++++++++++++++++++++++++++++++++++++++++++++++++++#
class MeasurementData(object):
  '''
    The main class for the data storage. Stores the data as a list of PhysicalProperty objects. 
    Sample name and measurement informations are stored as well as plot options and columns 
    which have to stay constant in one sequence.
    
    Main Attributes:
      number_of_points          Number of datapoints stored in the class
      data                      List of PhysicalProperty instances for every data column
      [x,y,z]data/.yerror       Indices of the plotted columns in the .data list. 
                                If z=-1 the plot is 2d
      log[x,y,z]                Boolean defining the logarithmic scale plotting of the columns
      crop_zdata                Boolean to set z data to be croped when the zrange is smaller 
                                than the datarange. For plot to be without empty spots
      short_info                Second part of the plot title and name of line in multiplot
      sample_name               First part of the plot title.
      filters                   List of filters which are applied to the dataset before export 
                                for plotting.
      plot_options              PlotOptions object storing the visualization options
    
    Main Methods:
      append                    Append a datapoint at the end of the dataset
      append_column             Add a new datacolumn to the object
      dimensions                Return the dimensions of all columns
      export                    Export the data to a file
      process_function          Call a function for all data of the object, e.g. square the y data
      sort                      Sort the datapoints for one column
      unit_trans                Transform units
      units                     Return the units of all columns
  '''
  index=0
  # every data value is a pysical property
  data=[]
  # for plotting the measurement select x and y data
  xdata=0
  ydata=0
  _yerror=-1
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
  is_matrix_data=False

  def __init__(self, columns=[], const=[],x=0,y=1,yerror=-1,zdata=-1): 
    '''
      Constructor for the class.
      If the values are not reinitialized we get problems
      with the creation of objects with the same variable name.
      
      There are two standart ways of creating these object:
        - creating a complete set of columns with empty PhysicalProperty object and
          appending each point to that object (slow, for small amount of data (e.g. <10000))
        - creating an empty instance with MeasurementData() and appending each column as
          PhysicalProperty object
      
      @param columns List of columns [(Unit, Dim), ...] in this object
      @param const List of constant colums for a sequence
      @param x Index of x column
      @param y Index of y column
      @param yerror Index of error column
      @param zdata Index of z column or -1 for None
    '''
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
    self._yerror=yerror
    self.const_data=[]
    for con in const: # create const_data column,Property for every const
      self.const_data.append([con[0],PhysicalProperty(self.data[con[0]].dimension,self.data[con[0]].unit)])
      self.const_data[-1][1].append(con[1])
    self.plot_together=[self] # list of datasets, which will be plotted together
    self.plot_together_zindex=0
    self.fit_object=None

  def __iter__(self): # see next()
    '''
      Function to iterate through the data-points, object can be used in "for bla in data:".
      Skippes pointes that are filtered.
    '''
    for point in self.get_filtered_data_matrix().transpose():
      yield point

  def get_filtered_data_matrix(self):
    '''
      Return the data as numpy array with applied filters.
      
      @return numpy array of point lists
    '''
    #try:
    data=numpy.array(self.data+[item.error.tolist() for item in self.data if item.has_error])#numpy.array([col.values for col in self.data])
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
    try:
      return len(self.data[0])
    except IndexError:
      return 0

  def __getitem__(self, index):
    '''
      MeasurementData[index] returns one datapoint.
    '''
    if hasattr(index, '__iter__'):
      output=deepcopy(self)
      for i, col in enumerate(output.data):
        output.data[i]=col[index]
      return output
    else:
      return [float(col[index]) for col in self.data]+[col.error[index] for col in self.data if col.has_error]
  
  def __getslice__(self, start, end):
    '''
      MeasurementData[start:end] returns a MeasurementData instance with data columns in the given range.
    '''
    output=deepcopy(self)
    for i, col in enumerate(output.data):
      output.data[i]=col[start:end]
    return output
  
  def __setitem__(self, index, item):
    '''
      Set data at index reverse of __getitem__
    '''
    for col, data in zip(self.data, item):
      col[index]=data
  
  def __setslice__(self, i, j, items):
    '''
      Inverse of __getslice__, items shoule be another MeasurementData instance.
    '''
    if not hasattr(items, 'data') or len(items)!=(j-i):
      raise ValueError, "can only set slice if input object is MeasurementData with length %i" % (j-i)
    for idx, col in enumerate(self.data):
      col[i:j]=items.data[idx]
  
  def __repr__(self):
    '''
      Define the string representation of the object. Just some useful information for debugging/IPython console
    '''
    output="<MeasurementData at %s, cols=%i, points=%i" % (hex(id(self)), len(self.data), len(self))
    if self.zdata<0:
      output+=", x='%s', y='%s'>" % (self.x.dimension, self.y.dimension)
    else:
      output+=", x='%s', y='%s', z='%s'>" % (self.x.dimension, self.y.dimension, self.z.dimension)
    return output
  
  def __add__(self, other):
    '''
      Define how to add two datasets together.
    '''
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z+=other
      else:
        output.y+=other
      return output
    if type(other)!=type(self) or len(self)!=len(other) or \
          (self.zdata<0 and self.y.unit!=other.y.unit) or \
          (self.zdata>=0 and (other.z is None or self.z.unit!=other.z.unit)):
      raise ValueError, "can only add two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1, -1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z+other.z)
    else:
      output=self.__class__([], [], 0, 1, -1, -1)
      output.data.append(self.x.copy())
      output.data.append(self.y+other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+'+'+other.short_info
    return output
  
  def __radd__(self, other):
    return self.__add__(other)
    
  def __sub__(self, other):
    '''
      Define how to add two datasets together.
    '''
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z-=other
      else:
        output.y-=other
      return output
    if type(other)!=type(self) or len(self)!=len(other) or \
          (self.zdata<0 and self.y.unit!=other.y.unit) or \
          (self.zdata>=0 and (other.z is None or self.z.unit!=other.z.unit)):
      raise ValueError, "can only subtract two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1, -1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z-other.z)
    else:
      output=self.__class__([], [], 0, 1, -1, -1)
      output.data.append(self.x.copy())
      output.data.append(self.y-other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+'-'+other.short_info
    return output
  
  def __rsub__(self, other):
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z=other-output.z
      else:
        output.y=other-output.y
      return output
    raise ValueError, "can only subtrac a MeasurementData from a scalar or array"
    
  def __div__(self, other):
    '''
      Define how to divide two datasets together.
    '''
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z/=other
      else:
        output.y/=other
      return output
    if type(other)!=type(self) or len(self)!=len(other) or \
          (self.zdata>=0 and other.z is None):
      raise ValueError, "can only devide two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1, -1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z/other.z)
    else:
      output=self.__class__([], [], 0, 1, -1, -1)
      output.data.append(self.x.copy())
      output.data.append(self.y/other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+'/'+other.short_info
    return output
  
  def __rdiv__(self, other):
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z=other/output.z
      else:
        output.y=other/output.y
      return output
    raise ValueError, "can only devide a scalar or array by a MeasurementData object"
    
  def __mul__(self, other):
    '''
      Define how to multiply two datasets together.
    '''
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z*=other
      else:
        output.y*=other
      return output
    if type(other)!=type(self) or len(self)!=len(other) or \
          (self.zdata>=0 and other.z is None):
      raise ValueError, "can only multiply two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1, -1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z*other.z)
    else:
      output=self.__class__([], [], 0, 1, -1, -1)
      output.data.append(self.x.copy())
      output.data.append(self.y*other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+'*'+other.short_info
    return output
  
  def __rmul__(self, other):
    '''
      Define how to multiply the MeasurementData from the left.
    '''
    return self.__mul__(other)

  def _get_plot_options(self): return self._plot_options
  
  def _set_plot_options(self, input):
    '''
      Set the PlotOptions object from a string or item input.
    '''
    if type(input) is str:
      self._plot_options=PlotOptions(input)
    elif type(input) is PlotOptions:
      self._plot_options=input
    else:
      raise TypeError, "plot_options has to be of type PlotOptions or String"

  def _get_error(self):
    '''
      Implement the possibility to ither define the error as extra column or property
      of y/z data.
    '''
    if self._yerror>=0:
      return self._yerror
    else:
      if self.zdata<0:
        if self.y.has_error:
          outidx=len(self.data)
          outidx+=len([1 for item in self.data[:self.ydata] if item.has_error])
          return outidx
        else:
          return -1
      else:
        if self.z.has_error:
          outidx=len(self.data)
          outidx+=len([1 for item in self.data[:self.zdata] if item.has_error])
          return outidx
        else:
          return -1
  
  def _set_error(self, index):
    if index>=len(self.data):
      self._yerror=-1
    else:
      self._yerror=index
  
  def _get_number_of_points(self):
    if len(self.data)>0:
      return len(self.data[0])
    else:
      return 0

  plot_options=property(_get_plot_options, _set_plot_options)
  yerror=property(_get_error, _set_error)  
  number_of_points=property(_get_number_of_points)

  def get_info(self):
    '''
      Return a string containing some information about the data stored
      in this object.
    '''
    return "Dataset containing %i points.\n\nInformation read from header:\n%s" % (self.number_of_points, self.info)

  def append(self, point):
    '''
      Add a point to this sequence.
      
      @param point List of entries by columns
      
      @return The added point or 'NULL' if an error has occured
    '''
    data=self.data # speedup data_lookup
    append_fast=PhysicalProperty.append
    nop=self.number_of_points
    if len(point)==len(data):
      try:
        for i,val in enumerate(point):
          append_fast(data[i], val)
      except ValueError, error:
        # make sure the length of all columns is the same after encountering an error
        for j in range(i):
          data[j]=data[j][:nop]
        raise ValueError, error
      return point
    elif len(point)==len(self.units()):
      # point is a set of [val1,val2...]+[err1,err2...]
      try:
        for i,val in enumerate(point[:len(data)]):
          if data[i].has_error:
            append_fast(data[i], (val, point[len(data)+len([col for col in data[:i] if col.has_error])]))
          else:
            append_fast(data[i], val)
      except ValueError, error:
        # make sure the length of all columns is the same after encountering an error
        for j in range(i):
          data[j]=data[j][:nop]
        raise ValueError, error
      return point
    else:
      raise ValueError, 'can only append data with %i/%i items, input has %i' % (len(data), len(self.units()), len(point))

  def append_column(self, column, dimension="", unit=""):
    '''
      Append a new column to the datastructure.
      If the column is already a PhysicalProperty, a copy
      of it is used, otherwise a new PhysicalProperty object
      is created with the column data.
    '''
    if len(self.data)!=0 and len(column)!=len(self):
      raise ValueError, 'Collumn to append has to be of size %i' % len(self)
    if hasattr(column, 'dimension'):
      self.data.append(column)
    else:
      col=PhysicalProperty(dimension, unit, column)
      self.data.append(col)

  get_data=__getitem__
  set_data=__setitem__

  def _get_x(self):
    '''
      Get the data for column x
    '''
    return self.data[self.xdata]
  
  def _set_x(self, item):
    '''
      Set the data for column x
    '''
    if len(item)!=len(self):
      raise ValueError, "shape mismatch: x needs to have %i items" % len(self)
    if hasattr(item, 'unit') and hasattr(item, 'dimension'):
      self.data[self.xdata]=item
    else:
      self.data[self.xdata][:]=item

  def _get_y(self):
    '''
      Get the data for column y
    '''
    return self.data[self.ydata]
  
  def _set_y(self, item):
    '''
      Set the data for column y
    '''
    if len(item)!=len(self):
      raise ValueError, "shape mismatch: y needs to have %i items" % len(self)
    if hasattr(item, 'unit') and hasattr(item, 'dimension'):
      self.data[self.ydata]=item
    else:
      self.data[self.ydata][:]=item

  def _get_z(self):
    '''
      Get the data for column z
    '''
    if self.zdata>=0:
      return self.data[self.zdata]
    else:
      return None
  
  def _set_z(self, item):
    '''
      Set the data for column z
    '''
    if self.zdata>=0:
      if len(item)!=len(self):
        raise ValueError, "shape mismatch: z needs to have %i items" % len(self)
      if hasattr(item, 'unit') and hasattr(item, 'dimension'):
        self.data[self.zdata]=item
      else:
        self.data[self.zdata][:]=item
    else:
      raise IndexError, "z-index not defined, can't set z data"

  x=property(_get_x, _set_x)
  y=property(_get_y, _set_y)
  z=property(_get_z, _set_z)

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
    if ye<0 or ye is None:
      return [point+[0] for point in self.list()]
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

  def join(self, other):
    '''
      Return a joined instance of two measurements with the same columns.
    '''
    if type(other) is list:
      if len(other)==1:
        other=other[0]
      else:
        other=other[0].join(other[1:])
    if not self.__class__ is other.__class__:
      raise TypeError, 'Can only join with instance of type %s' % self.__class__
    if not ( [(col.dimension, col.unit) for col in self.data] == \
             [(col.dimension, col.unit) for col in other.data]):
      raise ValueError, 'Can only join with instance with the same columns (dimension and unit)'
    output=deepcopy(self)
    for i, col in enumerate(output.data):
      output.data[i]=col.join(other.data[i])
    return output
  
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
    return self[-1]

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
    return [str(value.unit) for value in self.data]+[str(value.unit) for value in self.data if value.has_error]

  def dimensions(self): 
    '''
      Return dimensions of all columns-
    '''
    return [str(value.dimension) for value in self.data]+['δ'+value.dimension for value in self.data if value.has_error]

  def xunit(self): 
    '''
      Get unit of xcolumn.
    '''
    return str(self.units()[self.xdata])

  def yunit(self): 
    '''
      Get unit of ycolumn.
    '''
    return str(self.units()[self.ydata])

  def zunit(self): 
    '''
      Get unit of ycolumn.
    '''
    return str(self.units()[self.zdata])

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
      #arrays=[]
      #for column in self.data:
        #array=numpy.array(column.values)
        #arrays.append(array)
      processed_data=function(self.data)
      self.data=processed_data
      #for i, array in enumerate(self.data):
       # self.data[i].values=list(array)
    except (TypeError, 
            ValueError, 
            IndexError, 
            ZeroDivisionError), error: # if the function does not work with arrays the conventional method is used.
     raise ValueError, "could not process function: %s" % error
      #self.process_function_nonumpy(function)
    return self.last()

  def sort(self, column=None):
    '''
      Sort the datapoints for one column.
    '''
    if column is None:
      column=self.xdata
    sort_indices=numpy.argsort(self.data[column])
    for i, data in enumerate(self.data):
      self.data[i]=data[sort_indices]

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
      write_file.write('# exportet dataset from measurement_data_structure.py\n# Sample: '+self.sample_name+\
                       '\n#\n# other informations:\n#'+self.info.replace('\n','\n#'))
      columns=''
      for i in range(len(self.data)):
        columns=columns+' '+self.dimensions()[i]+'['+self.units()[i]+']'
      write_file.write('#\n#\n# Begin of Dataoutput:\n#'+columns+'\n')
    #self.write_data_matrix(write_file, data, split_indices)
    # Convert the data from matrix format to a string which can be written to a file
    data_string=self.string_from_data_matrix(seperator, data, split_indices)
    write_file.write(data_string)
    write_file.write('\n')
    write_file.close()
    return split_indices[-1] # return the number of exported data lines

  def export_matrix(self, file_name):
    '''
      Quick export only the xyz values as binary file.
    '''
    # Create data as list of x1,y1,z1,x2,y2,z2...,xn,yn,zn
    xyz=numpy.append(numpy.append(self.x, self.y), self.z).astype(numpy.float32)\
          .reshape(3,len(self.x)).transpose().flatten()
    xyz.tofile(open(file_name, 'wb'))

  def rough_sort(self, ds1, ds2, sensitivity):
    '''
      Return the sorting indices from a first and second column ignoring small
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

  def string_from_data_matrix(self, seperator, data, split_indices):
    '''
      Create a string that can be written to a file from a given data matrix.
      The function may look quite strange because of a lot of optimization,
      thus the result is almost as fast as c-code (faster if the c-code is not optimized).
      
      @param seperator A string to seperate each data value.
      @param data A matrix of data points
      @param split_indices Index of the points where empty lines should be added
      
      @return A string with the data.
    '''
    lines, cols=data.shape
    # convert data to a long 1d array
    data=numpy.nan_to_num(data.reshape(lines*cols))
    # create the format string for one line of data
    output_line=(("%g"+seperator)*cols)[:-len(seperator)]
    # join format string line by line
    output_list=["\n".join([output_line for j in range(split_indices[0])])]
    for i, split_i in enumerate(split_indices[1:]):
      output_list.append("\n".join([output_line for j in range(split_i-split_indices[i])]))
    # insert the values in the given format
    output=("\n\n".join(output_list)) % tuple(data)
    return output

  def max(self,xstart=None,xstop=None): 
    '''
      Returns x and y value of point with maximum x.
    '''
    x=self.data[self.xdata][:]
    y=self.data[self.ydata][:]
    if xstart is None:
      xstart=x.min()
    if xstop is None:
      xstop=x.max()
    indices=numpy.where((x>=xstart)*(x<=xstop))[0]
    max_point=self.data[self.ydata].values.index(y[indices].max())
    return [self.data[self.xdata].values[max_point],self.data[self.ydata].values[max_point]]

  def min(self,xstart=None,xstop=None): 
    '''
      Returns x and y value of point with minimum x.
    '''
    x=self.data[self.xdata][:]
    y=self.data[self.ydata][:]
    if xstart is None:
      xstart=x.min()
    if xstop is None:
      xstop=x.max()
    indices=numpy.where((x>=xstart)*(x<=xstop))[0]
    min_point=self.data[self.ydata].values.index(y[indices].min())
    return [self.data[self.xdata].values[min_point],self.data[self.ydata].values[min_point]]
  
  def get_xprojection(self, numpoints=200):
    '''
      Return the projection of 3d data on the x-axis.
    '''
    if self.zdata<0:
      raise TypeError, "Only 3d datasets can be used to calculate a projection."
    x=numpy.array(self.x, dtype=numpy.float32)
    z=numpy.array(self.z, dtype=numpy.float32)
    steps=numpy.linspace(float(x.min()), float(x.max()), numpoints)
    dsteps=steps[1]-steps[0]
    y=numpy.zeros_like(steps)
    for i, step in enumerate(steps):
      idx=numpy.where((x>=step)*(x<(step+dsteps)))[0]
      if len(idx)==1:
        y[i]=z[idx].sum()
      elif len(idx)>1:
        y[i]=z[idx].mean()
    steps=steps[y!=0]
    y=y[y!=0]
    return PhysicalProperty(self.x.dimension, self.x.unit, steps), PhysicalProperty(self.z.dimension, self.z.unit, y)

  def get_yprojection(self, numpoints=200):
    '''
      Return the projection of 3d data on the x-axis.
    '''
    if self.zdata<0:
      raise TypeError, "Only 3d datasets can be used to calculate a projection."
    x=numpy.array(self.y, dtype=numpy.float32)
    z=numpy.array(self.z, dtype=numpy.float32)
    steps=numpy.linspace(float(x.min()), float(x.max()), numpoints)
    dsteps=steps[1]-steps[0]
    y=numpy.zeros_like(steps)
    for i, step in enumerate(steps):
      idx=numpy.where((x>=step)*(x<(step+dsteps)))[0]
      if len(idx)==1:
        y[i]=z[idx].sum()
      elif len(idx)>1:
        y[i]=z[idx].mean()
    steps=steps[y!=0]
    y=y[y!=0]
    return PhysicalProperty(self.y.dimension, self.y.unit, steps), PhysicalProperty(self.z.dimension, self.z.unit, y)
  
  def export_projections(self, file_name, numpoints=200):
    '''
      Export x and y projections to a 4-column file.
    '''
    #file_handler=open(file_name, 'w')
    xx, xy=self.get_xprojection(numpoints)
    yx, yy=self.get_yprojection(numpoints)
    if len(xx)<len(yx):
      xx.resize(len(yx), refcheck=False)
      xy.resize(len(yx), refcheck=False)
    elif len(yx)<len(xx):
      yx.resize(len(xx), refcheck=False)
      yy.resize(len(xx), refcheck=False)
    #file_handler.write('# Projection on x and y axes of %s-%s map\n' % (self.sample_name,self.short_info))
    #columns=' '.join(col.dimension+'['+col.units+']' for col in [xx, xy, yx, yy])
    #write_file.write('#\n#\n# Begin of Dataoutput:\n#'+columns+'\n')
    data=numpy.array([xx.tolist(), xy.tolist(), yx.tolist(), yy.tolist()]).transpose()
    numpy.savetxt(file_name, data, fmt='%.10e')

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
  _units=None
  _dimensions=None
  _filters=[]
  _data=[]
  _len=None
  is_matrix_data=True
  
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
    if self._data is None:
      self._data=load(open(self.tmp_export_file, 'rb'))
      self._units=None
      self._dimensions=None
      self._len=None
    return self._data
  def set_data_object(self, object):
    self._data=object
    self.store_data()
  
  def units(self):
    if self._units is not None:
      return self._units
    else:
      return MeasurementData.units(self)
  
  def dimensions(self):
    if self._dimensions is not None:
      return self._dimensions
    else:
      return MeasurementData.dimensions(self)
  
  def get_len(self):
    if self._len is None:
      return MeasurementData.__len__(self)
    else:
      return self._len
  
  data=property(get_data_object, set_data_object)
  __len__=get_len
  
  def store_data(self):
    '''
      Pickle the data in this object to save memory.
    '''
    self._last_datapoint=MeasurementData.last(self)
    if self._data is not None:
      self._units=MeasurementData.units(self)
      self._dimensions=MeasurementData.dimensions(self)
      if len(self._data)>0:
        self._len=len(self._data[0])
      else:
        self._len=0
      dump(self._data, open(self.tmp_export_file , 'wb'), 2)
      self._data=None
  
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
    # restore saved data
    self.data
    return MeasurementData.__getstate__(self)
 
  def __setstate__(self, state):
    '''
      Unpickling the object will set a new temp file name.
    '''
    self.__dict__=state
    global hmd_file_number
    self.tmp_export_file=os.path.join(TEMP_DIR, 'HMD_'+ str(hmd_file_number)+ '.tmp')
    hmd_file_number+=1
    self.store_data()
    self.changed_after_export=True

  def __repr__(self):
    '''
      Get object information without reloading the data.
    '''
    if self._data is None:
      output="<HugeMD at %s, points=%i, state stored in: '%s'>" % (hex(id(self)), self._len, self.tmp_export_file)
    else:
      '''
        Define the string representation of the object. Just some useful information for debugging/IPython console
      '''
      output="<HugeMD at %s, cols=%i, points=%i" % (hex(id(self)), len(self.data), len(self))
      if self.zdata<0:
        output+=", x='%s', y='%s'>" % (self.x.dimension, self.y.dimension)
      else:
        output+=", x='%s', y='%s', z='%s'>" % (self.x.dimension, self.y.dimension, self.z.dimension)
    return output      

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
    self.changed_after_export=True
    output=MeasurementData.unit_trans_one(self, col, unit_lit)
    self.store_data()
    return output
  
  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None, only_fitted_columns=False): 
    if self.changed_after_export or self.plot_options.zrange!=self.last_export_zrange:
      print "Exporting large dataset, please stay patient"
      self.last_export_output=self.do_export(self.tmp_export_file+'.gptmp', print_info, seperator, xfrom, xto, only_fitted_columns)
      self.changed_after_export=False
      self.last_export_zrange=self.plot_options.zrange
      self.store_data()
    copyfile(self.tmp_export_file+'.gptmp',  file_name)
    return self.last_export_output
  
  def export_matrix(self, file_name):
    MeasurementData.export_matrix(self, file_name)
    self.store_data()    

  do_export=MeasurementData.export

#--------------------------------------    HugeMD-Class     -----------------------------------------------------#

def calculate_transformations(transformations):
  '''
    Use a dictionary of unit transformations to calculate
    all combinations of the transformations inside.
  '''
  output=deepcopy(transformations)
  keys=transformations.keys()
  # calculate inverse transformations
  for key in keys:
    if len(transformations[key])==2:
      output[(key[1], key[0])]=(1./transformations[key][0], -(transformations[key][1]/transformations[key][0]))
    else:
      output[(key[1], key[0])]=(1./transformations[key][0], -(transformations[key][1]/transformations[key][0]), 
                              transformations[key][3], transformations[key][2])
  # calculate transformations over two or more units.
  done=False
  while not done:
    # while there are still transformations changed, try to find new ones.
    done=True
    for key in output.keys():
      for key2 in output.keys():
        if key[1] == key2[0] and key[0] != key2[1] and (key[0], key2[1]) not in output and\
              len(output[key])==2 and len(output[key2])==2:
          done=False
          output[(key[0], key2[1])]=(output[key][0]*output[key2][0], output[key2][0]*output[key][1]+output[key2][1])
          output[(key2[1], key[0])]=(1./output[(key[0], key2[1])][0], -(output[(key[0], key2[1])][1]/output[(key[0], key2[1])][0]))
  return output

# Dictionary of transformations from one unit to another
known_transformations=calculate_transformations(known_unit_transformations)
# List of ufunc functions which need an angle as input
angle_functions=( 'sin', 'cos', 'tan', 'sec', 'sinh', 'cosh', 'tanh', 'sech' )

class PlotOptions(object):
  '''
    Object for storing information about the illustration of the data in the plot.
  '''
  special_plot_parameters=None
  special_using_parameters=""
  splot=''
  is_polar=False
  
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
  
  def overwrite_copy(self, other):
    '''
      Overwrite an other Plot option with the settings from this one.
    '''
    other._xrange=deepcopy(self._xrange)
    other._yrange=deepcopy(self._yrange)
    other._zrange=deepcopy(self._zrange)
    other.free_input=deepcopy(self.free_input)
    other.settings=deepcopy(self.settings)
    return other

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
    if self.is_polar:
      output+="set polar\nset grid polar\n set size square\n"
      output+=("set xrange [-%s:%s]\n" % (self._yrange[1], self._yrange[1] )).replace("-None", "").replace("None", "")
      output+=("set yrange [-%s:%s]\n" % (self._yrange[1], self._yrange[1] )).replace("-None", "").replace("None", "")
      output+=("set rrange [%s:%s]\n" % (self._xrange[0], self._xrange[1] )).replace("None", "")
    else:
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
        if range[0] not in  [None, '']:
          xrange[0]=float(range[0])
        if range[1] not in  [None, '']:
          xrange[1]=float(range[1])
        if None not in xrange and xrange[0]>xrange[1]:
          xrange=[xrange[1], xrange[0]]
        self._xrange=xrange
      except ValueError:
        raise ValueError, 'xrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, 'xrange has to be a tuple or list with two elements of float or None'

  def set_yrange(self, range): 
    if len(range)==2:
      try:
        yrange=[None, None]
        if range[0] not in  [None, '']:
          yrange[0]=float(range[0])
        if range[1] not in  [None, '']:
          yrange[1]=float(range[1])
        if None not in yrange and yrange[0]>yrange[1]:
          yrange=[yrange[1], yrange[0]]
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
        if None not in zrange and zrange[0]>zrange[1]:
          zrange=[zrange[1], zrange[0]]
        self._zrange=zrange
      except ValueError:
        raise ValueError, 'zrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, 'zrange has to be a tuple or list with two elements of float or None'


  xrange=property(get_xrange, set_xrange)
  yrange=property(get_yrange, set_yrange)
  zrange=property(get_zrange, set_zrange)


derivatives={# derivatives to numpy base functions for error propagation
             numpy.sin.__str__(): numpy.cos, 
             numpy.cos.__str__(): lambda input: -numpy.sin(input), 
             numpy.tan.__str__(): lambda input: 1./numpy.cos(input)**2, 
             numpy.exp.__str__(): numpy.exp, 
             numpy.arcsin.__str__(): lambda input: 1./(1.-input**2)**0.5, 
             numpy.arccos.__str__(): lambda input: -1./(1.-input**2)**0.5, 
             numpy.arctan.__str__(): lambda input: 1./(1.+input**2),
             numpy.log.__str__(): lambda input: 1./input,
             numpy.log10.__str__(): lambda input: 1./input,
             numpy.square.__str__(): lambda input: 2.*input , 
             numpy.sqrt.__str__(): lambda input: 1./(2.*numpy.sqrt(input)), 
             numpy.abs.__str__(): lambda input: input, 
             
             # functions with two parameters
             numpy.add.__str__(): ( lambda input1, input2: 1., lambda input1, input2: 1. ), 
             numpy.subtract.__str__(): ( lambda input1, input2: 1., lambda input1, input2: 1. ), 
             numpy.multiply.__str__(): ( lambda input1, input2: input2, lambda input1, input2: input1), 
             numpy.divide.__str__(): ( lambda input1, input2: 1./input2 , lambda input1, input2: -input1/input2**2), 
             numpy.power.__str__(): ( lambda input1, input2: input2*input1**(input2-1), 
                                     lambda input1, input2: numpy.log(input1)*input1**input2), 
             }

class LinkedList(list):
  '''
    A list which is linked to a PhysicalProperty so every change to the list
    data will also be made for the PhysicalProperty.
  '''
  link=None
  
  def __init__(self, data):
    list.__init__(self, data)
    self.link=data
  
  def __setitem__(self, index, item):
    list.__setitem__(self, index, item)
    self.link.__setitem__(index, item)
  
  def __setslice__(self, i, j, items):
    list.__setslice__(self, i, j, items)
    self.link.__setslice__(i, j, items)
  
  def append(self, item):
    list.append(self, item)
    self.link.append(item)
  
  def __iadd__(self, other):
    list.__iadd__(self, other)
    self.link.values=self
    return self
  
class PhysicalUnit(object):
  '''
    Object to store physical units. Implements combining units and exponential of units.
  '''
  
  def __init__(self, entry_str):
    '''
      Create the object data from an input string.
      The input string should be of the form n1*n2*n3/d1*d2*d3 where n are units in the 
      nummerator and d units in the denominator.
    '''
    if type(entry_str) not in [str, unicode, PhysicalUnit]:
      raise ValueError, 'can only construc unit from string or other PhysicalUnit not %s' % type(entry_str)
    object.__init__(self)
    if type(entry_str) is PhysicalUnit:
      self._unit_parts=deepcopy(entry_str._unit_parts)
    else:
      if len(entry_str.split('/'))>2:
        raise ValueError, 'the format of the input string should be n1*n2*n3/d1*d2*d3'
      self._unit_parts={}
      begin=0
      nummerator=True
      if len(entry_str)>0:
        for i in range(1, len(entry_str)):
          if entry_str[i] in ['*', '/']:
            pass
          elif entry_str[i:i+2] == '·':
            # unicode items have to bytes
            pass
          else:
            continue
          new_region=entry_str[begin:i]
          pow_idx=new_region.find('^')
          if pow_idx==-1:
            new_unit=new_region
            new_power=1.
          else:
            new_unit=new_region[:pow_idx]
            new_power=float(new_region[pow_idx+1:].strip('{}'))
          if not nummerator:
            new_power=-new_power
          begin=i+1
          if new_unit in self._unit_parts:
            self._unit_parts[new_unit]+=new_power
          else:
            self._unit_parts[new_unit]=new_power
          if entry_str[i] == '/':
            nummerator=False
          if entry_str[i:i+2] == '·':
            begin+=1
      new_region=entry_str[begin:]
      pow_idx=new_region.find('^')
      if pow_idx==-1:
        new_unit=new_region
        new_power=1.
      else:
        new_unit=new_region[:pow_idx]
        new_power=float(new_region[pow_idx+1:].strip('{}'))
      if not nummerator:
        new_power=-new_power
      if new_unit in self._unit_parts:
        self._unit_parts[new_unit]+=new_power
      else:
        self._unit_parts[new_unit]=new_power
    if '1' in self._unit_parts:
      del(self._unit_parts['1'])
    if '' in self._unit_parts:
      del(self._unit_parts[''])

  
  def __str__(self):
    '''
      Construct a combined string for the unit.
    '''
    items=self._unit_parts.items()
    nummerator=[item for item in items if item[1]>0.]
    denominator=[item for item in items if item[1]<0.]
    nummerator.sort()
    denominator.sort()
    output_str=""
    if len(nummerator)==0 and len(denominator)==0:
      return ''
    first=True
    for name, exponent in nummerator:
      if not first:
        output_str+='·'
      else:
        first=False
      if exponent==1.:
        output_str+=name
      else:
        if len("%g" % exponent)==1:
          output_str+="%s^%g" % (name, exponent)
        else:
          output_str+="%s^{%g}" % (name, exponent)
    if len(denominator)>0 and len(nummerator)!=0:
      output_str+='/'
      swap_exponen=-1.
    else:
      swap_exponen=1.
    if len(denominator)>1:
      output_str+='('
    first=True
    for name, exponent in denominator:
      if not first:
        output_str+='·'
      else:
        first=False
      if (swap_exponen*exponent)==1.:
        output_str+=name
      else:
        if len("%g" % (swap_exponen*exponent))==1:
          output_str+="%s^%g" % (name,  (swap_exponen*exponent))
        else:
          output_str+="%s^{%g}" % (name,  (swap_exponen*exponent))
    if len(denominator)>1:
      output_str+=')'
    return output_str
  
  def __repr__(self):
    return "<PhysicalUnit '%s'>" % self.__str__()
  
  def __add__(self, other):
    '''
      Implements adding a string to a unit.
    '''
    if type(other) is str:
      return self.__str__()+other
    else:
      raise TypeError, "unsupported operand type(s) for +: 'PhysicalUnit' and '%s'" % type(other).__name__
  
  def __radd__(self, other):
    '''
      Implements adding a unit to a string.
    '''
    if type(other) is str:
      return other+self.__str__()
    else:
      raise TypeError, "unsupported operand type(s) for +: 'PhysicalUnit' and '%s'" % type(other).__name__

  def __mul__(self, other):
    '''
      Implement multiplying units.
    '''
    if type(other) is str:
      other=PhysicalUnit(other)
    out=deepcopy(self)
    unit_parts=out._unit_parts
    unit_parts_other=other._unit_parts
    for key, value in unit_parts_other.items():
      if key in unit_parts:
        unit_parts[key]+=value
      else:
        unit_parts[key]=value
      if unit_parts[key]==0:
        del(unit_parts[key])
    return out
  
  def __rmul__(self, other):
    return self*other
  
  def __div__(self, other):
    '''
      Implement dividing units.
    '''
    if type(other) is str:
      other=PhysicalUnit(other)
    return self*other**-1.
  
  def __rdiv__(self, other):
    if other==1:
      other='1'
    return other*self**-1
  
  def __pow__(self, exponent):
    '''
      Implementing unit to the power of exponent.
    '''
    out=deepcopy(self)
    unit_parts=out._unit_parts
    for key, value in unit_parts.items():
      unit_parts[key]=value*exponent
    return out
  
  def __eq__(self, other):
    if type(other) is str:
      other=PhysicalUnit(other)
    return self._unit_parts==other._unit_parts
  
  def __ne__(self, other):
    if type(other) is str:
      other=PhysicalUnit(other)
    return self._unit_parts!=other._unit_parts   
  
  def __hash__(self):
    '''
      Defines the hash index for e.g. dict usage.
    '''
    return self.__str__().__hash__()
  
  def get_transformation(self, conversion):
    '''
      Try to calculate a transformation to a given unit.
    '''
    conversion=PhysicalUnit(conversion)
    if (self, conversion) in known_transformations:
      # if complete conversion in the list, use it
      return [self, known_transformations[(self, conversion)][0], 
                    known_transformations[(self, conversion)][1], conversion]
    output=[self, 1., 0., conversion]
    # go through each partial unit of the conversion
    # and check if it is the same in this unit
    # or if it can be transformed
    own_parts=self._unit_parts
    found_keys=[]
    # try to extract conversions for all parts of the unit
    for key, value in conversion._unit_parts.items():
      if key in own_parts:
        if value==own_parts[key]:
          found_keys.append(key)
        else:
          raise ValueError, "conversion from '%s'->'%s' is impossible" % (self, conversion)
      else:
        found=False
        for own_key in own_parts.keys():
          if (own_key, key) in known_transformations:
            if not own_parts[own_key]==value:
              raise ValueError, "conversion from '%s'->'%s' is impossible" % (self, conversion)
            found=True
            # get base unit conversion
            multiplyer, addition=known_transformations[(own_key, key)]
            # calculate conversion for unit^value
            if addition==0:
              multiplyer**=value
            # for integer values it is also possible to calculate with offset
            elif value==1.:
              pass
            elif value==-1.:
              pass
            else:
              raise ValueError, "automatic conversion not implemented for '%s'->'%s' because of unit offset." % (self, conversion)
            output[1]*=multiplyer
            output[2]=output[2]*multiplyer+addition
        if not found:
          raise ValueError, "automatic conversion not implemented for '%s'->'%s'." % (self, conversion)
        else:
          found_keys.append(own_key)
    if len(found_keys)!=len(own_parts.keys()):
      raise ValueError, "automatic conversion not implemented for '%s'->'%s'." % (self, conversion)
    return output
  

class PhysicalConstant(numpy.ndarray):
  '''
    Class to store physical constants. Adds a unit, symbol/name and discription to
    the float value.
    Quite similar to PhysicalProperty but only as scalar.
  '''
  
  def __new__(subtype, value, unit, symbol='', discription=''):
    obj=numpy.ndarray.__new__(subtype, 1, dtype=numpy.float32)
    obj.__setitem__(0, value)
    obj.unit=PhysicalUnit(unit)
    obj.symbol=symbol
    obj.discription=discription
    return obj
  
  def _get_unit(self):
    return self._unit
  
  def _set_unit(self, unit):
    self._unit=PhysicalUnit(unit)
  
  unit=property(_get_unit, _set_unit)
  
  def __array_finalize__(self, obj):
    self.unit=getattr(obj, 'unit', PhysicalUnit(''))
    self.symbol=getattr(obj, 'symbol', '')
    self.discription=getattr(obj, 'discription', '')
  
  def __str__(self):
    if self.symbol!='':
      return self.symbol
    else:
      return str(self[0])+' '+self.unit

  def __repr__(self):
    if self.symbol:
      pre=self.symbol+'='
    else:
      pre=''
    if self.discription!='':
      return pre+str(self[0])+' '+self.unit +' - '+self.discription
    else:
      return pre+str(self[0])+' '+self.unit

  def __array_wrap__(self, out_const, context=None):
    '''
      Function that get's called by numpy ufunct functions after they get
      called with one instance from this class. Makes PhysicalConstant objects
      usable with all standart numpy functions.
      
      @return PhysicalConstant object with values as result from the function
    '''
    out_const=out_const.view(type(self))
    return out_const
  
  def unit_trans(self,transfere): 
    '''
      Transform one unit to another. transfere variable is of type [from,b,a,to].
    '''
    if transfere[0]==self.unit: # only transform if right 'from' parameter
      output=self*transfere[1]+transfere[2]
      output.unit=PhysicalUnit(transfere[3])
      return output
    else:
      return None

  def __mod__(self, conversion):
    '''
      Convenience method to easily get the same PhysicalProperty with a converted unit. Examples:
      pp % 'm' -> a copy of the PhysicalProperty with the unit converted to m
      pp % ('m', 1.32, -0.2) -> a copy of the PhysicalProperty with the unit converted to 'm' 
                                multiplying by 1.32 and subtracting 0.2
      
      @return New object instance.    
    '''
    if type(conversion) in [str, PhysicalUnit]:
      if (self.unit, conversion) in known_transformations:
        multiplyer, addition=known_transformations[(self.unit, conversion)]
        output=self.unit_trans([self.unit, multiplyer, addition, conversion])
        return output
      else:
        raise ValueError, "Automatic conversion not implemented for '%s'->'%s'." % (self.unit, conversion)
    else:
      if getattr(conversion, '__iter__', False) and len(conversion)>=3 and \
          type(conversion[0]) in [str, PhysicalUnit] and type(conversion[1]) in (float, int) and type(conversion[2]) in (float, int):
        output=self.unit_trans([self.unit, conversion[1], conversion[2], conversion[0]])
        return output
      else:
        raise ValueError, '% only defined with str or iterable object of at least one string and two floats/ints'

  def __add__(self, other):
    '''
      Define addition of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other._radd__(self)
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    output=numpy.ndarray.__add__(self, other)
    output.unit=self.unit
    return output
    
  def _radd__(self, other):
    return self+other

  def __sub__(self, other):
    '''
      Define subtraction of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rsub__(self)
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    output=numpy.ndarray.__sub__(self, other)
    output.unit=self.unit
    return output
  
  def __rsub__(self, other):
    return -self+other

  def __mul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rmul__(self)
    output=numpy.ndarray.__mul__(self, other)
    if hasattr(other, 'unit'):
      output.unit=self.unit * other.unit
    else:
      output.unit=self.unit
    return output
  
  def __rmul__(self, other):
    return self*other

  def __div__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rdiv__(self)
    output=numpy.ndarray.__div__(self, other)
    if hasattr(other, 'unit'):
      output.unit=self.unit / other.unit
    else:
      output.unit=self.unit
    return output

  def __rdiv__(self, other):
    '''
      Define division of other object by PhysicalProperty instances.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__rdiv__(self, other)
    if hasattr(other, 'unit'):
      output.unit=other.unit / self.unit
    else:
      output.unit=self.unit**-1
    return output

  def __pow__(self, to_power):
    '''
      Define calculation of PhysicalProperty instance to a specified power.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__pow__(self, to_power)
    output.unit=self.unit**to_power
    return output

  def __iadd__(self, other): raise NotImplementedError, "you can't modify physical constants"
  def __isub__(self, other): raise NotImplementedError, "you can't modify physical constants"
  def __imul__(self, other): raise NotImplementedError, "you can't modify physical constants"
  def __idiv__(self, other): raise NotImplementedError, "you can't modify physical constants"
  def __ipow__(self, to_power): raise NotImplementedError, "you can't modify physical constants"

class PhysicalProperty(numpy.ndarray):
  '''
    Class for any physical property. Stores the data, unit and dimension
    to make unit transformations possible. Can be used with numpy functions.
    Error values are stored and propagated in arithmetric operations.
    
    Attributes:
      dimension  String for the dimension of the instance
      unit       PhysicalUnit object
      error      Error value as array
    
    Hints:
      PhysicalProperty can be used with different convenience operators/functions,
      for a PhysicalProperty 'P' these are e.g.:
      
      P % [unit]                  Transform the instance to the unit
      P % ([name], [mul], [add])  Transform the instance to [name] using the multiplyer [mul]
                                  and adding [add]
      P // [dim]                  Get P with different dimension name [dim]
      P // ([dim], [unit])        Get P with different dimension and unit name
      
      Additionally PhysicalProperty instances can be used like numpy arrays in functions
      and with respect to slicing. Addition and subtraction is unit dependent and angular
      functions only take angles as input.
  '''
  dimension=''
  # if defined this is the error value of the property
  # the error will be automatically propagated when functions
  # get called with instances of this class
  _error=None
  unit_save=True # if true changes units after arithmetic operation and checks if correct

  def __new__(subtype, dimension_in, unit_in, input_data=[], input_error=None, unit_save=True):
    '''
      Class constructor when explcidly called.
      
      @param dimension_in String with the dimensions for that instance
      @param unit_in String with unit for that instance
    '''
    #obj=numpy.ndarray.__new__(subtype, len(input_data), dtype=numpy.float32)
    obj=numpy.asarray(input_data, dtype=numpy.float32).view(subtype).copy()
    obj.unit=PhysicalUnit(unit_in)
    obj.dimension=dimension_in
    obj.unit_save=True
    if input_error is not None:
      if len(input_error)!=len(input_data):
        raise ValueError, 'shape mismatch: error and data have different lengths'
      obj.error=numpy.array(input_error, dtype=numpy.float32)
    obj.__setslice__(0, len(input_data), input_data)
    return obj
  
  def __array_finalize__(self, obj):
    self.unit=getattr(obj, 'unit', PhysicalUnit(''))
    self.dimension=getattr(obj, 'dimension', "")
    self._error=getattr(obj, '_error', None)
    #print "finalize", self.__dict__

  def __reduce__(self):
    '''
      Method used by cPickle to get the object state
    '''
    state=list(numpy.ndarray.__reduce__(self))
    state[2]=state[2]+tuple([self.__dict__])
    return tuple(state)

  def __setstate__(self, state):
    '''
      Reconstruct the object from the state saved via __reduce__.
    '''    
    numpy.ndarray.__setstate__(self, state[1:5])
    self.__dict__=state[5]
  
  def append(self, item):
    '''
      Append an item to the end of the data, if the array is to small it is enlarged.
    '''
    if hasattr(item, 'dimension'):
      length=self.__len__()
      if self.has_error!=item.has_error:
        raise ValueError, 'items do not have the same error status'
      # item is PhysicalProperty or derived
      self.resize(length+len(item), refcheck=False)
      if self.has_error:
        self._error.resize(length+len(item), refcheck=False)
        self._error.__setslice__(length, length+len(item), item.error)
      self.__setslice__(length, length+len(item), item.view(numpy.ndarray))
    elif hasattr(item, '__iter__'):
      if len(item)==2:
        if len(self)==0:
          self.error=[]
        if self.has_error:      
          length=self.__len__()
          self.resize(length+1, refcheck=False)
          self.__setitem__(length, item[0])
          self.error.resize(length+1, refcheck=False)
          self.error.__setitem__(length, item[1])
        else:
          raise ValueError, "the input needs to be a scalar without error value"
      else:
        raise ValueError, "can only append scalar or iterable with length 2"
    else:
      if self.has_error:
        raise ValueError, "need a value with corresponding error to append data"
      length=self.__len__()
      self.resize(length+1, refcheck=False)
      self.__setitem__(length, item)
  
  def copy(self):
    '''
      Return a copy of self.
    '''
    output=numpy.ndarray.copy(self)
    if self.has_error:
      output._error=output._error.copy()
    return output
  
  def __repr__(self):
    '''
      Return a string representation of the data.
    '''
    output='PhysicalProperty(['
    if len(self)<10:
      sval=map(str, self.view(numpy.ndarray))
      output+=", ".join(sval)
    else:
      sval=map(str, self[:5].view(numpy.ndarray))
      output+=", ".join(sval)
      output+=" ... "
      sval=map(str, self[-5:].view(numpy.ndarray))
      output+=", ".join(sval)
    if self.has_error:
      output+="],\tdimension='%s', unit='%s', length=%i, avg.error=%g)" % (self.dimension, self.unit,  
                                                                            len(self), self.error.mean())
    else:
      output+="],\tdimension='%s', unit='%s', length=%i)" % (self.dimension, self.unit,  len(self))
    return output

  def __str__(self):
    '''
      Return the values as string.
    '''
    output='['
    if len(self)<10:
      sval=map(str, self.view(numpy.ndarray))
      output+=", ".join(sval)
    else:
      sval=map(str, self[:5].view(numpy.ndarray))
      output+=", ".join(sval)
      output+=" ... "
      sval=map(str, self[-5:].view(numpy.ndarray))
      output+=", ".join(sval)
    output+="]"
    return output
  
  def _get_values(self):
    '''
      Wrapper to simulate the old .values list
    '''
    return LinkedList(self.view(numpy.ndarray))
  
  def _set_values(self, values):
    self.resize(len(values), refcheck=False)
    self.__setslice__(0, len(values), values)
    if self.has_error:
      if len(values)==0:
        self.error=[]
      elif len(self.error)!=len(self):
        # remove the error values, if the number of items differs
        self.error=None
  
  def _get_has_error(self):
    return (self._error is not None)
  
  def _get_error(self):
    return self._error
  
  def _set_error(self, value):
    if value is None:
      self._error=None
    else:
      if len(self)>1:
        assert len(value)==len(self), "Error needs to have %i values" % len(self)
      self._error=numpy.array(value)
  
  def _get_unit(self):
    return self._unit
  
  def _set_unit(self, unit):
    self._unit=PhysicalUnit(unit)
  
  values=property(_get_values, _set_values)
  has_error=property(_get_has_error)
  error=property(_get_error, _set_error)
  unit=property(_get_unit, _set_unit)

  def unit_trans(self,transfere): 
    '''
      Transform one unit to another. transfere variable is of type [from,b,a,to].
    '''
    if transfere[0]==self.unit: # only transform if right 'from' parameter
      self.unit=PhysicalUnit(transfere[3])
      if self.has_error:
        self._error*=transfere[1]
      self*=transfere[1]
      self+=transfere[2]
      return True
    else:
      return False

  def dim_unit_trans(self,transfere): 
    '''
      Transform dimension and unit to another. Variable transfere is of type
      [from_dim,from_unit,b,a,to_dim,to_unit].
    '''
    if len(transfere)>0 and (transfere[1]==self.unit)&(transfere[0]==self.dimension): # only transform if right 'from_dim' and 'from_unit'
      self.unit=PhysicalUnit(transfere[5])
      self.dimension=transfere[4]
      if self.has_error:
        self._error*=transfere[2]
      self*=transfere[2]
      self+=transfere[3]
      return True
    else:
      return False

  def __array_wrap__(self, out_arr, context=None):
    '''
      Function that get's called by numpy ufunct functions after they get
      called with one instance from this class. Makes PhysicalProperty objects
      usable with all standart numpy functions.
      
      @return PhysicalProperty object with values as result from the function
    '''
    out_arr=out_arr.view(type(self))
    if self.has_error and context is not None:
      out_arr=self._propagate_errors(out_arr, context)
    out_arr.unit=self.unit
    out_arr.dimension=self.dimension
    if context:
      ## make sure angular dependent functions are called with radian unit
      if context[0].__name__ in angle_functions:
        if self.unit!='rad':
          try:
            out_arr=context[0](self%'rad')
          except ValueError:
            raise ValueError, 'Input to function %s needs to be an angle' % context[0].__name__
        out_arr.unit=PhysicalUnit('')
      ## make sure inverse angular functions get called with dimensioinless input
      elif context[0].__name__.startswith('arc'):
        if self.unit=='':
          out_arr.unit=PhysicalUnit('rad')
        else:
          raise ValueError, "Input to function %s needs to have empty unit" % context[0].__name__
      elif context[0] in [numpy.exp, numpy.log]:
        if self.unit!='':
          raise ValueError, "Input to function %s needs to have empty unit" % context[0].__name__
      elif context[0] is numpy.sqrt:
        out_arr.unit**=0.5
    return out_arr

  def __getitem__(self, item):
    '''
      Get an item of the object.
    '''
    if hasattr(item, '__iter__'):
      output=numpy.ndarray.__getitem__(self, item).view(type(self))
    else:
      output=numpy.array([numpy.ndarray.__getitem__(self, item)]).view(type(self)).copy()
    output.unit=self.unit
    output.dimension=self.dimension
    if self.has_error:
      output._error=self._error.__getitem__(item)
    return output

  def __getslice__(self, i, j):
    '''
      Get an item of the object.
    '''
    output=numpy.ndarray.__getslice__(self, i, j).view(type(self))
    output.unit=self.unit
    output.dimension=self.dimension
    if self.has_error:
      output._error=self._error.__getslice__(i, j)
    return output

  def __setitem__(self, i, item):
    '''
      Set an item of the object. If input and self has an error set this, too.
    '''
    numpy.ndarray.__setitem__(self, i, item)
    if hasattr(item, 'dimension') and (self.has_error and item.has_error):
      self._error.__setitem__(i, item.error)
    
  def __setslice__(self, i, j, items):
    '''
      Define a slice from i to j. If input and self has an error set this, too.
    '''
    numpy.ndarray.__setslice__(self, i, j, items)
    if hasattr(items, 'dimension') and (self.has_error and items.has_error):
      self._error.__setslice__(i, j, items.error)

  def _propagate_errors(self, out_arr, context):
    '''
      Calculate the errorpropatation after a function has been processed.
    '''
    try:
      if len(context[1])==1:
        # only a function of one parameter
        out_arr.error=abs(derivatives[context[0].__str__()](self.view(numpy.ndarray))*self.error)
      else:
        # a function of two patameters
        if context[1][0] is self:
          # the first patameter is self
          other=context[1][1]
          # if both arguments to ufunc have an error value
          if getattr(context[1][1], 'error', None) is not None:
            out_arr.error=numpy.sqrt(
                          (derivatives[context[0].__str__()][0](self.view(numpy.ndarray), 
                                                                other.view(numpy.ndarray))*self.error)**2+\
                          (derivatives[context[0].__str__()][1](self.view(numpy.ndarray), 
                                                                other.view(numpy.ndarray))*other.error)**2
                                    )
          # only the first argument has an error value
          else:
            out_arr.error=abs(derivatives[context[0].__str__()][0](self.view(numpy.ndarray), numpy.array(other))*self.error)
        else:
          # the second argument is self, so the first is no PhysicalProperty instance
          out_arr.error=abs(derivatives[context[0].__str__()][1](numpy.array(context[1][0]), self.view(numpy.ndarray))*self.error)
    except KeyError:
      raise NotImplementedError, "no derivative defined for function '%s'" % context[0].__name__
    return out_arr
  
  def __neg__(self):
    '''
      Define -self
    '''
    return -1.*self

  def __add__(self, other):
    '''
      Define addition of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    output=numpy.ndarray.__add__(self, other)
    return output
  
  def __iadd__(self, other):
    '''
      Define addition of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    return numpy.ndarray.__iadd__(self, other)
  
  def _radd__(self, other):
    return self+other

  def __sub__(self, other):
    '''
      Define subtraction of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    return numpy.ndarray.__sub__(self, other)
  
  def __isub__(self, other):
    '''
      Define subtraction of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      if self.unit != other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)
    return numpy.ndarray.__isub__(self, other)
  
  def __rsub__(self, other):
    return -self+other

  def __mul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__mul__(self, other)
    if hasattr(other, 'unit'):
      output.unit=self.unit * other.unit
    return output
  
  def __imul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      self.unit*=other.unit
    return numpy.ndarray.__imul__(self, other)
  
  def __rmul__(self, other):
    return self*other

  def __div__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__div__(self, other)
    if hasattr(other, 'unit'):
      output.unit=self.unit / other.unit
    return output

  def __idiv__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      @return New instance of PhysicalProperty
    '''
    if hasattr(other, 'unit'):
      self.unit/=other.unit
    return numpy.ndarray.__idiv__(self, other)

  def __rdiv__(self, other):
    '''
      Define division of other object by PhysicalProperty instances.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__rdiv__(self, other)
    if hasattr(other, 'unit'):
      output.unit=other.unit / self.unit
    else:
      output.unit=self.unit**-1
    return output

  def __pow__(self, to_power):
    '''
      Define calculation of PhysicalProperty instance to a specified power.
      
      @return New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__pow__(self, to_power)
    output.unit=self.unit**to_power
    return output

  def __ipow__(self, to_power):
    '''
      Define calculation of this PhysicalProperty instance to a specified power.
      
      @return This instance of PhysicalProperty altered
    '''
    self.unit**=to_power
    if self.has_error and to_power in [2., 0.5]:
      # errorpropagation doesn't work properly for square and sqrt if done inline
      return self**to_power
    return numpy.ndarray.__ipow__(self, to_power)

  def __floordiv__(self, new_dim_unit):
    '''
      Convenience method to easily get the same PhysicalProperty with another dimension or
      dimension and unit. Examples:
      pp // 'new' -> a copy of the PhysicalProperty with the new dimension 'new'
      pp // ('length','m') -> a copy of the PhysicalProperty with the new dimension 'length' and the unit 'm'
      
      @return New object instance.
    '''
    output=deepcopy(self)
    if type(new_dim_unit) is str:
      output.dimension=new_dim_unit
      return output
    else:
      if getattr(new_dim_unit, '__iter__', False) and len(new_dim_unit)>=2 and \
          type(new_dim_unit[0]) is str and type(new_dim_unit[1]) is str:
        output.dimension=new_dim_unit[0]
        output.unit=PhysicalUnit(new_dim_unit[1])
        return output
      else:
        raise ValueError, '// only defined with str or iterable object of at least two strings'
  
  def __mod__(self, conversion):
    '''
      Convenience method to easily get the same PhysicalProperty with a converted unit. Examples:
      pp % 'm' -> a copy of the PhysicalProperty with the unit converted to m
      pp % ('m', 1.32, -0.2) -> a copy of the PhysicalProperty with the unit converted to 'm' 
                                multiplying by 1.32 and subtracting 0.2
      
      @return New object instance.    
    '''
    output=deepcopy(self)
    if type(conversion) in [str, PhysicalUnit]:
      output.unit_trans(self.unit.get_transformation(conversion))
      return output
    else:
      if getattr(conversion, '__iter__', False) and len(conversion)>=3 and \
          type(conversion[0]) is str and type(conversion[1]) in (float, int) and type(conversion[2]) in (float, int):
        output.unit_trans([self.unit, conversion[1], conversion[2], conversion[0]])
        return output
      else:
        raise ValueError, '% only defined with str or iterable object of at least one string and two floats/ints'

  # Boolean operations:
  def __eq__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__eq__(self.view(numpy.ndarray), other)

  def __gt__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__gt__(self.view(numpy.ndarray), other)

  def __ge__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__ge__(self.view(numpy.ndarray), other)

  def __lt__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__lt__(self.view(numpy.ndarray), other)

  def __le__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__le__(self.view(numpy.ndarray), other)

  def __ne__(self, other):
    if hasattr(other, 'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__ne__(self.view(numpy.ndarray), other)

  def min(self):
    '''
      Get minimal value as PhysicalProperty object.
    '''
    if self.has_error:
      index=numpy.argmin(self)
      return self[index]
    else:
      return PhysicalProperty('min('+self.dimension+')', self.unit, [numpy.ndarray.min(self)])
  
  def max(self):
    '''
      Get maximal value as PhysicalProperty object.
    '''
    if self.has_error:
      index=numpy.argmax(self)
      return self[index]
    else:
      return PhysicalProperty('max('+self.dimension+')', self.unit, [numpy.ndarray.max(self)])
  
  def mean(self):
    '''
      Get (weighted) mean value as PhysicalProperty object.
    '''
    if self.has_error:
      # if the object has an error value calculate the weighted mean
      data=self.view(numpy.ndarray)
      error=self._error
      over_error_sum=(1./error**2).sum()
      weighted_mean_data=(data/error**2).sum()/over_error_sum
      weighted_mean_error=numpy.sqrt(1./over_error_sum)
      return PhysicalProperty('mean('+self.dimension+')', self.unit, 
                              [weighted_mean_data], [weighted_mean_error])
    else:
      return PhysicalProperty('mean('+self.dimension+')', self.unit, [numpy.ndarray.mean(self)])

  def sum(self, *args, **opts):
    '''
      Get the sum of value as PhysicalProperty object.
    '''
    if self.has_error:
      # if the object has an error value calculate the weighted mean
      output_error=numpy.sqrt((self._error**2).sum(*args, **opts))
      return PhysicalProperty('sum('+self.dimension+')', self.unit, 
                              [numpy.ndarray.sum(self, *args, **opts)], [output_error])      
    else:
      return PhysicalProperty('sum('+self.dimension+')', self.unit, [numpy.ndarray.sum(self, *args, **opts)])
  
  def reshape(self, *a, **opts):
    '''
      Change the dimensional order of the data.
    '''
    output=numpy.ndarray.reshape(self, *a, **opts)
    output._error=self._error.reshape(*a, **opts)
    return output
  
  def flatten(self):
    '''
      Reduce data to one dimension.
    '''
    output=numpy.ndarray.flatten(self)
    output._error=self._error.flatten()
    return output
  
  def join(self, other):
    '''
      Combine two PhysicalProperty objects of the same unit.
    '''
    # can join with a list of PhysicalProperty objects
    if type(other) is list:
      if len(other) == 1:
        other=other[0]
      else:
        other=other[0].join(other[1:])
    
    if hasattr(other, 'unit') and (self.unit!=other.unit or (self.has_error!=other.has_error)):
      try:
        other=other%self.unit
      except ValueError:
        raise ValueError, "Wrong unit, %s!=%s" % (self.unit, other.unit)        
    joined_data=numpy.append(self, other)
    output=self.__class__(self.dimension, self.unit, joined_data)
    if (self.has_error and hasattr(other, 'unit') and other.has_error):
      joined_error=numpy.append(self.error, other.error)
      output.error=joined_error
    return output

################### define some common physical constants

constants={
           #
           'h': PhysicalConstant(6.6260693E-31, 'g·m^2/s', 'h', 'plancks constant'), 
           'hbar': PhysicalConstant(1.0545717E-31, 'g⋅m^2/s', 'hbar', 'plancks constant over 2π'), 
           'c': PhysicalConstant(2.9979246E8, 'm/s', 'c', 'speed of light'), 
           #
           'µ_0': PhysicalConstant(1.2566371E-3, 'g⋅m/A^2·s^2', 'µ_0', 'magnetic constant'), 
           'µ_B': PhysicalConstant(9.2740095E-24 , 'A⋅m^2', 'µ_B', 'Bohr magneton'), 
           #
           'r_B': PhysicalConstant(5.291772E-11 , 'm', 'r_B', 'Bohr radius'), 
           'r_e': PhysicalConstant(2.81794E-15 , 'm', 'r_e', 'Classical electron radius'), 
           #
           'm_n': PhysicalConstant(1.67493E-24 , 'g', 'm_n', 'Neutron mass'), 
           'm_e': PhysicalConstant(9.1094E-28  , 'g', 'm_e', 'Electron mass'), 
           }
