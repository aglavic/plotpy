# -*- encoding: utf-8 -*-
'''
 Classes for storing the measurement data of any session.
 Units and dimensions are also stored for easier accessing and transformation.
'''

import os
from shutil import copyfile
from copy import deepcopy
from cPickle import load, dump
import numpy
from tempfile import gettempdir
from config import transformations
from plotpy.message import in_encoding, out_encoding

hmd_file_number=0
TEMP_DIR=gettempdir()

#++++++++++++++++++++++++++++++++++++++MeasurementData-Class+++++++++++++++++++++++++++++++++++++++++++++++++++++#
class MeasurementData(object):
  '''
    The main class for the data storage. Stores the data as a list of PhysicalProperty objects. 
    Sample name and measurement informations are stored as well as plot options and columns 
    which have to stay constant in one sequence.
    
    ======================    =================================================
    Main Attributes           Description
    ======================    =================================================
    number_of_points          Number of datapoints stored in the class
    ----------------------    -------------------------------------------------
    data                      List of PhysicalProperty instances for every 
                              data column
    ----------------------    -------------------------------------------------
    [x,y,z]data/.yerror       Indices of the plotted columns in the .data list. 
                              If z=-1 the plot is 2d
    ----------------------    -------------------------------------------------
    log[x,y,z]                Boolean defining the logarithmic scale plotting 
                              of the columns
    ----------------------    -------------------------------------------------
    crop_zdata                Boolean to set z data to be croped when the 
                              zrange is smaller than the data range. 
                              For plot to be without empty spots
    ----------------------    -------------------------------------------------
    short_info                Second part of the plot title and 
                              name of line in multiplot
    ----------------------    -------------------------------------------------
    sample_name               First part of the plot title.
    filters                   List of filters which are applied to the 
                              dataset before export for plotting.
    ----------------------    -------------------------------------------------
    plot_options              PlotOptions object storing the visualization 
                              options
    ======================    =================================================
    
    ======================    =================================================
    Main Methods              Description
    ======================    =================================================
    append                    Append a datapoint at the end of the dataset
    ----------------------    -------------------------------------------------
    append_column             Add a new datacolumn to the object
    ----------------------    -------------------------------------------------
    dimensions                Return the dimensions of all columns
    ----------------------    -------------------------------------------------
    export                    Export the data to a file
    ----------------------    -------------------------------------------------
    process_function          Call a function for all data of the object, 
                              e.g. square the y data
    ----------------------    -------------------------------------------------
    sort                      Sort the datapoints for one column
    ----------------------    -------------------------------------------------
    unit_trans                Transform units
    ----------------------    -------------------------------------------------
    units                     Return the units of all columns
    ======================    =================================================
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
  crop_zdata=True  # Crop the z-range values to the selected plot range
  scan_line_constant=-1  # the column to sort the data for when using 3d plots.
  scan_line=-1  # the column changed in one scan.
  const_data=[]  # select, which data should not be varied in this maesurement and the accouracy
  info=u''
  short_info=u''
  number=u''
  sample_name=u''
  # view angle for the 3d plot
  view_x=60
  view_z=30
  filters=[]  # a list of filters to be applied when returning the data, the format is:
              # ( column , from , to , include )
  SPLIT_SENSITIVITY=0.01
  is_matrix_data=False
  plot_together_zindex=0
  fit_object=None
  _functional=None

  def __init__(self, columns=[], const=[], x=0, y=1, yerror=-1, zdata=-1, dtype=numpy.float32):
    '''
      Constructor for the class.
      If the values are not reinitialized we get problems
      with the creation of objects with the same variable name.
      
      There are two standart ways of creating these object:
        - creating a complete set of columns with empty PhysicalProperty object and
          appending each point to that object (slow, for small amount of data (e.g. <10000))
        - creating an empty instance with MeasurementData() and appending each column as
          PhysicalProperty object
      
      :param columns: List of columns [(Unit, Dim), ...] in this object
      :param const: List of constant colums for a sequence
      :param x: Index of x column
      :param y: Index of y column
      :param yerror: Index of error column
      :param zdata: Index of z column or -1 for None
    '''
    self.index=0
    self.info=u''
    self.sample_name=u''
    self._plot_options=PlotOptions()
    self.data=[]
    for column in columns:  # create Property for every column
      self.data.append(PhysicalProperty(column[0], column[1], dtype=dtype))
    self.xdata=x
    self.ydata=y
    self.zdata=zdata
    self.view_x=0  # 3d view point
    self.view_z=0
    self.logx=False
    self.logy=False
    self._yerror=yerror
    self.const_data=[]
    for con in const:  # create const_data column,Property for every const
      self.const_data.append([con[0], PhysicalProperty(self.data[con[0]].dimension, self.data[con[0]].unit)])
      self.const_data[-1][1].append(con[1])
    self.plot_together=[self]  # list of datasets, which will be plotted together

  def __iter__(self):  # see next()
    '''
      Function to iterate through the data-points, object can be used in u"for bla in data:".
      Skippes pointes that are filtered.
    '''
    for point in self.get_filtered_data_matrix().transpose():
      yield point

  def get_filtered_data_matrix(self):
    '''
      Return the data as numpy array with applied filters.
      
      :return: numpy array of point lists
    '''
    # try:
    data=numpy.vstack(self.data+[item.error for item in self.data if item.has_error])  # numpy.array([col.values for col in self.data])
    # except ValueError:
      # min_length=min([len(col.values) for col in self.data])
      # data=numpy.array([col.values[:min_length] for col in self.data])
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
        data_indices=numpy.where((filter_column>=filter_from)&(filter_column<=filter_to))
      else:
        if filter_from is None:
          filter_from=filter_column.max()
        if filter_to is None:
          filter_to=filter_column.min()
        data_indices=numpy.where((filter_column>=filter_to)|(filter_column<=filter_from))
      data=data[:, data_indices[0]]
    return data

  def get_filter_indices(self):
    '''
      Return the boolean array of not filtered data points.
      
      :return: numpy array of filters
    '''
    data=numpy.vstack(self.data+[item.error for item in self.data if item.has_error])
    # initialize true array
    indices=(data[0]==data[0])
    filters=self.filters
    lnot=numpy.logical_not
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
        indices&=(filter_column>=filter_from)&(filter_column<=filter_to)
      else:
        if filter_from is None:
          filter_from=filter_column.max()
        if filter_to is None:
          filter_to=filter_column.min()
        indices&=lnot((filter_column>=filter_from)&(filter_column<=filter_to))
    return indices

  def __getstate__(self):
    '''
      Define how the class is pickled and copied.
    '''
    self.preview=None
    self._functional=None
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
    if isinstance(index, basestring):
      dims=self.dimensions()
      return self.data[dims.index(index)]
    elif hasattr(index, u'__iter__'):
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
    if isinstance(index, basestring):
      if not len(item)==len(self):
        raise ValueError, 'Can only assign columns with length %i'%len(self)
      dims=self.dimensions()
      if index in dims:
        self.data[dims.index(index)]=item
      elif hasattr(item, 'dimension'):
        self.data.append(item)
      else:
        self.data.append(PhysicalProperty(index, '', item))
    else:
      for col, data in zip(self.data, item):
        col[index]=data

  def __setslice__(self, i, j, items):
    '''
      Inverse of __getslice__, items shoule be another MeasurementData instance.
    '''
    if not hasattr(items, u'data') or len(items)!=(j-i):
      raise ValueError, u"can only set slice if input object is MeasurementData with length %i"%(j-i)
    for idx, col in enumerate(self.data):
      col[i:j]=items.data[idx]

  def __repr__(self):
    '''
      Define the string representation of the object. Just some useful information for debugging/IPython console
    '''
    output=u"<%s at %s, cols=%i, points=%i"%(self.__class__.__name__,
                                            hex(id(self)), len(self.data),
                                            len(self))
    if self.zdata<0:
      output+=u", x='%s', y='%s'>"%(self.x.dimension,
                                    self.y.dimension)
    else:
      output+=u", x='%s', y='%s', z='%s'>"%(self.x.dimension,
                                            self.y.dimension,
                                            self.z.dimension)
    return output.encode(out_encoding)

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
      raise ValueError, u"can only add two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1,-1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z+other.z)
    else:
      output=self.__class__([], [], 0, 1,-1,-1)
      output.data.append(self.x.copy())
      output.data.append(self.y+other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+u'+'+other.short_info
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
      raise ValueError, u"can only subtract two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1,-1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z-other.z)
    else:
      output=self.__class__([], [], 0, 1,-1,-1)
      output.data.append(self.x.copy())
      output.data.append(self.y-other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+u'-'+other.short_info
    return output

  def __rsub__(self, other):
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z=other-output.z
      else:
        output.y=other-output.y
      return output
    raise ValueError, u"can only subtrac a MeasurementData from a scalar or array"

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
      raise ValueError, u"can only devide two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1,-1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z/other.z)
    else:
      output=self.__class__([], [], 0, 1,-1,-1)
      output.data.append(self.x.copy())
      output.data.append(self.y/other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+u'/'+other.short_info
    return output

  def __rdiv__(self, other):
    if type(other) in [float, int, numpy.ndarray]:
      output=deepcopy(self)
      if self.zdata>=0:
        output.z=other/output.z
      else:
        output.y=other/output.y
      return output
    raise ValueError, u"can only devide a scalar or array by a MeasurementData object"

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
      raise ValueError, u"can only multiply two MeasurementData instances with the same shape and unit"
    if self.z is not None:
      output=self.__class__([], [], 0, 1,-1, 2)
      output.data.append(self.x.copy())
      output.data.append(self.y.copy())
      output.data.append(self.z*other.z)
    else:
      output=self.__class__([], [], 0, 1,-1,-1)
      output.data.append(self.x.copy())
      output.data.append(self.y*other.y)
    output.sample_name=self.sample_name
    output.number=self.number
    output.short_info=self.short_info+u'*'+other.short_info
    return output

  def __rmul__(self, other):
    '''
      Define how to multiply the MeasurementData from the left.
    '''
    return self.__mul__(other)

  def __setstate__(self, state):
    '''
      For compatibility with old .mdd files.
    '''
    self.__dict__=state
    if not hasattr(self, u'_plot_options'):
      self._plot_options=PlotOptions()

  def __call__(self, x):
    '''
      Makes it possible to use the measurment data as a function by interpolating
      measured values for any x value.
      If a functional representation created with scipy.interpolate is present, 
      it is used for the interpolation.
    '''
    if self.zdata>=0:
      raise NotImplementedError, u"Calling a MeasurementData object is only implemented for 2d data at the moment"
    if any(x<=self.x.min()) or any(x>=self.x.max()):
      raise ValueError, u"x not in measured range"
    if self._functional is not None:
      out=self._functional(x)
      return PhysicalProperty(self.y.dimension, self.y.unit, out)
    xm=self.x
    ym=self.y
    if hasattr(x, u'__iter__'):
      # scipy interpolation is much better for arrays, try to create it:
      try:
        from scipy.interpolate import interp1d  # @UnusedImport
      except ImportError:
        idx=numpy.where(xm<x[0])[0][-1]
        # calculate the interpolation
        out=((ym[idx+1]*(x[0]-xm[idx])+ym[idx]*(xm[idx+1]-x[0]))/(xm[idx+1]-xm[idx])).copy()
        for xi in x[1:]:
          idx=numpy.where(xm<xi)[0][-1]
          # calculate the interpolation
          out.append((ym[idx+1]*(xi-xm[idx])+ym[idx]*(xm[idx+1]-xi))/(xm[idx+1]-xm[idx]))
      else:
        print u"Creating interpolation with scipy."
        self.create_interpolation()
        return self(x)
    else:
      idx=numpy.where(xm<x)[0][-1]
      # calculate the interpolation
      out=float((ym[idx+1]*(x-xm[idx])+ym[idx]*(xm[idx+1]-x))/(xm[idx+1]-xm[idx]))
    return out

  def create_interpolation(self):
    '''
      Use scipy.interpolate to create a functional representation
      of the data.
    '''
    if self.zdata>=0:
      raise NotImplementedError, u"Calling a MeasurementData object is only implemented for 2d data at the moment"
    from scipy.interpolate import interp1d
    self._functional=interp1d(self.x.view(numpy.ndarray),
                              self.y.view(numpy.ndarray),
                              kind=u'cubic',
                              bounds_error=True,
                              fill_value=numpy.nan)

  def _get_plot_options(self): return self._plot_options

  def _set_plot_options(self, input_):
    '''
      Set the PlotOptions object from a string or item input.
    '''
    if isinstance(input_, basestring):
      self._plot_options=PlotOptions(input_)
    elif type(input_) is PlotOptions:
      self._plot_options=input_
    else:
      raise TypeError, u"plot_options has to be of type PlotOptions or String"

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
          return-1
      else:
        if self.z.has_error:
          outidx=len(self.data)
          outidx+=len([1 for item in self.data[:self.zdata] if item.has_error])
          return outidx
        else:
          return-1

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
    return u"Dataset containing %i points.\n\nInformation read from header:\n%s"%(self.number_of_points, self.info)

  def get_approx_size(self):
    '''
      Return the approximate data size in bytes.
    '''
    output=0
    for col in self.data:
      output+=col.get_approx_size()
    return output

  def append(self, point):
    '''
      Add a point to this sequence.
      
      :param point: List of entries by columns
      
      :return: The added point or u'NULL' if an error has occured
    '''
    data=self.data  # speedup data_lookup
    append_fast=PhysicalProperty.append
    nop=self.number_of_points
    if len(point)==len(data):
      try:
        for i, val in enumerate(point):
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
        for i, val in enumerate(point[:len(data)]):
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
      raise ValueError, u'can only append data with %i/%i items, input has %i'%(len(data), len(self.units()), len(point))

  def append_column(self, column, dimension=u"", unit=u""):
    '''
      Append a new column to the datastructure.
      If the column is already a PhysicalProperty, a copy
      of it is used, otherwise a new PhysicalProperty object
      is created with the column data.
    '''
    if len(self.data)!=0 and len(column)!=len(self):
      raise ValueError, u'Collumn to append has to be of size %i'%len(self)
    if hasattr(column, u'dimension'):
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
      raise ValueError, u"shape mismatch: x needs to have %i items"%len(self)
    if hasattr(item, u'unit') and hasattr(item, u'dimension'):
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
      raise ValueError, u"shape mismatch: y needs to have %i items"%len(self)
    if hasattr(item, u'unit') and hasattr(item, u'dimension'):
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
        raise ValueError, u"shape mismatch: z needs to have %i items"%len(self)
      if hasattr(item, u'unit') and hasattr(item, u'dimension'):
        self.data[self.zdata]=item
      else:
        self.data[self.zdata][:]=item
    else:
      raise IndexError, u"z-index not defined, can't set z data"

  x=property(_get_x, _set_x)
  y=property(_get_y, _set_y)
  z=property(_get_z, _set_z)

  def list(self):  # @ReservedAssignment
    '''
      Get x-y-(z) list of all data points.
      If x or y columns are negative the index is returned instead
    '''
    data=self.get_filtered_data_matrix()
    xd=self.xdata
    yd=self.ydata
    zd=self.zdata
    if (xd>=0) and (yd>=0):
      if (zd<0):
        return data[numpy.array([xd, yd])].transpose().tolist()
      return data[numpy.array([xd, yd, zd])].transpose().tolist()
    elif yd>=0:
      return numpy.vstack([numpy.arange(len(data[0])), data[yd]]).transpose().tolist()
    elif xd>=0:
      return numpy.vstack([ data[xd], numpy.arange(len(data[0]))]).transpose().tolist()
    return numpy.vstack([numpy.arange(len(data[0])), numpy.arange(len(data[0]))]).transpose().tolist()

  def list_err(self):
    '''
      Get x-y-dy list of all data.
      If x or y columns are negative the index is returned instead
    '''
    data=self.get_filtered_data_matrix()
    xd=self.xdata
    yd=self.ydata
    ye=self.yerror
    zd=self.zdata
    if ye<0 or ye is None:
      return [point+[0] for point in self.list()]
    if (xd>=0) and (yd>=0):
      if (zd<0):
        return data[numpy.array([xd, yd, ye])].transpose().tolist()
      return data[numpy.array([xd, yd, zd, ye])].transpose().tolist()
    elif yd>=0:
      return numpy.vstack([numpy.arange(len(data[0])),
                           data[numpy.array([yd, ye])]]).transpose().tolist()
    elif xd>=0:
      return numpy.vstack([ data[xd], numpy.arange(len(data[0]))]).transpose().tolist()
    return numpy.vstack([numpy.arange(len(data[0])), numpy.arange(len(data[0]))]).transpose().tolist()

  def listxy(self, x, y):
    '''
      Get x-y list of data with different x,y values.
    '''
    return [[point[x], point[y]] for point in self]

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
      raise TypeError, u'Can only join with instance of type %s'%self.__class__
    if not ([(col.dimension, col.unit) for col in self.data]==\
             [(col.dimension, col.unit) for col in other.data]):
      raise ValueError, u'Can only join with instance with the same columns (dimension and unit)'
    output=deepcopy(self)
    for i, col in enumerate(output.data):
      output.data[i]=col.join(other.data[i])
    return output

  def type(self):  # @ReservedAssignment
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
      Check if a point is consistent with constant data of this sequence.
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
    return [value.unit.str() for value in self.data]+[value.unit.str() for value in self.data if value.has_error]

  def dimensions(self):
    '''
      Return dimensions of all columns-
    '''
    return [value.dimension for value in self.data]+[u'δ'+value.dimension for value in self.data if value.has_error]

  def xunit(self):
    '''
      Get unit of xcolumn.
    '''
    if self.xdata>=0:
      return str(self.units()[self.xdata])
    else:
      return u''

  def yunit(self):
    '''
      Get unit of ycolumn.
    '''
    if self.ydata>=0:
      return str(self.units()[self.ydata])
    else:
      return u''

  def zunit(self):
    '''
      Get unit of ycolumn.
    '''
    return str(self.units()[self.zdata])

  def xdim(self):
    '''
      Get dimension of xcolumn.
    '''
    if self.xdata>=0:
      return self.dimensions()[self.xdata]
    else:
      return u'Index'

  def ydim(self):
    ''' 
      Get dimension of ycolumn.
    '''
    if self.ydata>=0:
      return self.dimensions()[self.ydata]
    else:
      return u'Index'

  def zdim(self):
    '''
      Get dimension of ycolumn.
    '''
    return self.dimensions()[self.zdata]

  def unit_trans(self, unit_list):
    '''
      Change units of all columns according to a given list of translations.
      
      :return: List of new dimensions and units
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
    return [self.dimensions(), self.units()]

  def unit_trans_one(self, col, unit_list):
    '''
      Change units of one column according to a given list of translations and
      return this column.
      
      :return: The changed column and the applied translation
    '''
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

  def process_function_nonumpy(self, function):
    '''
      Processing a function on every data point.
      
      :param function: Python function to execute on each point
      
      :return: Last point after function execution
    '''
    for i in range(self.number_of_points):
      point=self.get_data(i)
      self.set_data(function(point), i)
    return self.last()

  def process_function(self, function):
    '''
      Processing a function on every data point.
      When numpy is installed this is done via one proccess call 
      for arrays. (This leads to a huge speedup)
      
      :param function: Python function to execute on each point
      
      :return: Last point after function execution
    '''
    try:
      # arrays=[]
      # for column in self.data:
        # array=numpy.array(column.values)
        # arrays.append(array)
      processed_data=function(self.data)
      self.data=processed_data
      # for i, array in enumerate(self.data):
        # self.data[i].values=list(array)
    except (TypeError,
            ValueError,
            IndexError,
            ZeroDivisionError), error:  # if the function does not work with arrays the conventional method is used.
      raise ValueError, u"could not process function: %s"%error
      # self.process_function_nonumpy(function)
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

  def export(self, file_name, print_info=True, seperator=u' ',
             xfrom=None, xto=None, only_fitted_columns=False,
             format_string=None):
    '''
      Write data in text file.
      
      :param file_name: Name of the export file
      :param print_info: Put a header ontop of the data
      :param seperator: Seperator characters to be used between columns
      :param xfrom: Start value of x for the export
      :param xto: End value of x for the export
      :param only_fitted_columns: Only export columns used for fitting.
      
      :return: The number of data lines exported
    '''
    # The procedure is extremely optimized for fast exports
    # the bottleneck is the conversion from data array to string. (5/6)
    # Tried all ideas from e.g.
    # http://stackoverflow.com/questions/2721521/fastest-way-to-generate-delimited-string-from-1d-numpy-array
    # http://www.skymind.com/~ocrow/python_string/
    if format_string is None:
      if numpy.float64 in [self.x.dtype, self.y.dtype]:
        format_string="%.15g"
      else:
        format_string="%.7g"
    xd=self.xdata
    yd=self.ydata
    zd=self.zdata
    ed=self.yerror
    SPLIT_SENSITIVITY=self.SPLIT_SENSITIVITY
    data=self.get_filtered_data_matrix()
    if not xto:
      xto=data[xd].max()
    data_window=numpy.where((data[xd]>=xfrom)&(data[xd]<=xto))[0]
    data=data[:, data_window]
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
          if not absmin>0:
            absmin=(numpy.abs(numpy.nan_to_num(data[zd]))).min()
          if absmin==0:
            absmin=1e-10
        data[zd]=numpy.where(data[zd]>=absmin, data[zd], absmin)
        data[zd]=numpy.where(data[zd]<=absmax, data[zd], absmax)
      # get the best way to sort and split the data for gnuplot
      if self.scan_line_constant<0:
        x_sort_indices=self.rough_sort(data[xd], data[yd], SPLIT_SENSITIVITY)
        y_sort_indices=self.rough_sort(data[yd], data[xd], SPLIT_SENSITIVITY)
        sorted_x=data[:, x_sort_indices]
        sorted_y=data[:, y_sort_indices]
        split_indices_x=numpy.where(sorted_x[yd, :-1]<sorted_x[yd, 1:])[0]
        split_indices_y=numpy.where(sorted_y[xd, :-1]<sorted_y[xd, 1:])[0]
        if len(split_indices_x)<=len(split_indices_y):
          split_indices=split_indices_x+1
          data=sorted_x
        else:
          split_indices=split_indices_y+1
          data=sorted_y
      else:
        sort_indices=self.rough_sort(data[self.scan_line_constant], data[self.scan_line], SPLIT_SENSITIVITY)
        data=data[:, sort_indices]
        split_indices=numpy.where(data[self.scan_line, :-1]<data[self.scan_line, 1:])[0]+1
    split_indices=split_indices.tolist()+[len(data[0])]
    # write data to file
    write_file=open(file_name, u'w')
    if print_info:
      write_file.write(u'# exportet dataset from mds.py\n# Sample: '+self.sample_name+\
                       u'\n#\n# other informations:\n#'+self.info.replace(u'\n', u'\n#'))
      columns=u''
      for i in range(len(self.data)):
        columns=columns+u' '+self.dimensions()[i]+u'['+self.units()[i]+u']'
      write_file.write(u'#\n#\n# Begin of Dataoutput:\n#'+columns+u'\n')
    # Convert the data from matrix format to a string which can be written to a file
    data_string=self.string_from_data_matrix(seperator, data, split_indices, format_string=format_string)
    write_file.write(data_string)
    write_file.write(u'\n')
    write_file.close()
    return data.shape[1]  # return the number of exported data lines

  def export_matrix(self, file_name):
    '''
      Quick export only the xyz values as binary file.
    '''
    # Create data as list of x1,y1,z1,x2,y2,z2...,xn,yn,zn
    filter_indices=numpy.logical_not(self.get_filter_indices())
    x=self.x
    y=self.y
    z=numpy.array(self.z, copy=True, dtype=numpy.float32)
    if numpy.any(filter_indices):
      # although matrix points cannot be left out,
      # filtered points are changed to NaN
      z[filter_indices]=numpy.nan
    xyz=numpy.vstack([x, y, z]).astype(numpy.float32).transpose().flatten()
    xyz.tofile(open(file_name, u'wb'))

  def export_npz(self, file_name):
    '''
      Export data into a numpy npz file.
    '''
    cols=self.get_filtered_data_matrix()
    items={
           u'dimensions': map(unicode, self.dimensions()),
           u'units': map(unicode, self.units()),
           u'x': unicode(self.dimensions()[self.xdata]),
           u'y': unicode(self.dimensions()[self.ydata]),
           }
    if self.zdata>=0:
      items[u'z']=unicode(self.dimensions()[self.zdata])
    if self.yerror>=0:
      items[u'error']=unicode(self.dimensions()[self.yerror])
    for i, dim in enumerate(self.dimensions()):
      items[unicode(dim)]=cols[i]
    numpy.savez(file_name, **items)

  def rough_sort(self, ds1, ds2, sensitivity):
    '''
      Return the sorting indices from a first and second column ignoring small
      differences.
    '''
    srt_run1=numpy.argsort(ds1)
    ds1_run1=ds1[srt_run1]
    max_step=(ds1_run1[1:]-ds1_run1[:-1]).max()
    abs_sensitivity=max_step*sensitivity
    small_step_indices=numpy.where(((ds1_run1[1:]-ds1_run1[:-1])<abs_sensitivity)*((ds1_run1[:-1]-ds1_run1[1:])!=0))
    for index in small_step_indices[0][1:]:
      from_data=ds1_run1[index+1]
      to_data=ds1_run1[index]
      ds1=numpy.where(ds1==from_data, ds1, to_data)
    srt_run2=numpy.lexsort(keys=(ds1, ds2))
    return srt_run2

  def string_from_data_matrix(self, seperator, data, split_indices, format_string=u"%g"):
    '''
      Create a string that can be written to a file from a given data matrix.
      The function may look quite strange because of a lot of optimization,
      thus the result is almost as fast as c-code (faster if the c-code is not optimized)
      while having the flexibility to define empty line indices and format options.
      
      :param seperator: A string to seperate each data value.
      :param data: A matrix of data points
      :param split_indices: Index of the points where empty lines should be added
      :param format_string: Specifies the format option to be used for string conversion of the numbers
      
      :return: A string with the data.
    '''
    cols, ignore=data.shape
    data=data.transpose()
    # convert data to a long 1d array
    data=numpy.nan_to_num(data.flatten())
    # create the format string for one line of data
    output_line=((format_string+seperator)*cols)[:-len(seperator)]
    # join format string line by line
    output_list=[u"\n".join([output_line for ignore in range(split_indices[0])])]
    for i, split_i in enumerate(split_indices[1:]):
      output_list.append(u"\n".join([output_line for ignore in range(split_i-split_indices[i])]))
    # insert the values in the given format
    output=(u"\n\n".join(output_list))%tuple(data)
    return output

  def max(self, xstart=None, xstop=None):  # @ReservedAssignment
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
    return [self.data[self.xdata].values[max_point], self.data[self.ydata].values[max_point]]

  def min(self, xstart=None, xstop=None):  # @ReservedAssignment
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
    return [self.data[self.xdata].values[min_point], self.data[self.ydata].values[min_point]]

  def get_xprojection(self, numpoints):
    '''
      Return the projection of 3d data on the x-axis.
    '''
    if self.zdata<0:
      raise TypeError, u"Only 3d datasets can be used to calculate a projection."
    # get the data columns
    if not self.is_matrix_data:
      data=self.get_filtered_data_matrix()
      x=data[self.xdata]
      y=data[self.ydata]
      z=data[self.zdata]
    else:
      x=numpy.array(self.x, dtype=numpy.float32)
      y=numpy.array(self.y, dtype=numpy.float32)
      z=numpy.array(self.z, dtype=numpy.float32)
    # filter the columns by xy-range
    result=numpy.ones(x.shape, dtype=bool)
    if self.plot_options.xrange[0] is not None:
      result&=(x>=self.plot_options.xrange[0])
    if self.plot_options.xrange[1] is not None:
      result&=(x<=self.plot_options.xrange[1])
    if self.plot_options.yrange[0] is not None:
      result&=(y>=self.plot_options.yrange[0])
    if self.plot_options.yrange[1] is not None:
      result&=(y<=self.plot_options.yrange[1])
    x=x[result]
    z=z[result]
    if numpoints is None:
      numpoints=int(numpy.sqrt(len(x)))
    projection, ignore=numpy.histogram(x, numpoints, weights=z)
    counts, px=numpy.histogram(x, numpoints)
    px=(px[:-1]+px[1:])/2.
    py=projection/counts
    return PhysicalProperty(self.x.dimension, self.x.unit, px), \
            PhysicalProperty(self.z.dimension, self.z.unit, py)

  def get_yprojection(self, numpoints):
    '''
      Return the projection of 3d data on the y-axis.
    '''
    if self.zdata<0:
      raise TypeError, u"Only 3d datasets can be used to calculate a projection."
    if not self.is_matrix_data:
      data=self.get_filtered_data_matrix()
      x=data[self.xdata]
      y=data[self.ydata]
      z=data[self.zdata]
    else:
      x=numpy.array(self.x, dtype=numpy.float32)
      y=numpy.array(self.y, dtype=numpy.float32)
      z=numpy.array(self.z, dtype=numpy.float32)
    # filter the columns by xy-range
    result=numpy.ones(x.shape, dtype=bool)
    if self.plot_options.xrange[0] is not None:
      result&=(x>=self.plot_options.xrange[0])
    if self.plot_options.xrange[1] is not None:
      result&=(x<=self.plot_options.xrange[1])
    if self.plot_options.yrange[0] is not None:
      result&=(y>=self.plot_options.yrange[0])
    if self.plot_options.yrange[1] is not None:
      result&=(y<=self.plot_options.yrange[1])
    y=y[result]
    z=z[result]
    if numpoints is None:
      numpoints=int(numpy.sqrt(len(y)))
    projection, ignore=numpy.histogram(y, numpoints, weights=z)
    counts, px=numpy.histogram(y, numpoints)
    px=(px[:-1]+px[1:])/2.
    py=projection/counts
    return PhysicalProperty(self.y.dimension, self.y.unit, px), \
            PhysicalProperty(self.z.dimension, self.z.unit, py)

  def export_projections(self, file_name, numpoints=None):
    '''
      Export x and y projections to a 4-column file.
    '''
    # file_handler=open(file_name, u'w')
    xx, xy=self.get_xprojection(numpoints)
    yx, yy=self.get_yprojection(numpoints)
    if len(xx)<len(yx):
      xx.resize(len(yx), refcheck=False)
      xy.resize(len(yx), refcheck=False)
    elif len(yx)<len(xx):
      yx.resize(len(xx), refcheck=False)
      yy.resize(len(xx), refcheck=False)
    # file_handler.write(u'# Projection on x and y axes of %s-%s map\n' % (self.sample_name,self.short_info))
    # columns=u' '.join(col.dimension+u'['+col.units+u']' for col in [xx, xy, yx, yy])
    # write_file.write(u'#\n#\n# Begin of Dataoutput:\n#'+columns+u'\n')
    data=numpy.vstack([xx, xy, yx, yy]).transpose()
    numpy.savetxt(file_name, data)

#--------------------------------------MeasurementData-Class-----------------------------------------------------#

#++++++++++++++++++++++++++++++++++++++    HugeMD-Class     +++++++++++++++++++++++++++++++++++++++++++++++++++++#

class HugeMD(MeasurementData):
  '''
    For huge datasets (50 000 points +) this datastructure uses a arbitrary temporary file to sotre exported data.
    The data is only reexported after a change or changes to the filters.
  '''

  changed_after_export=True
  tmp_export_file=u''
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
      self._data=load(open(self.tmp_export_file, u'rb'))
      self._units=None
      self._dimensions=None
      self._len=None
      # os.remove(self.tmp_export_file)
    return self._data

  def set_data_object(self, object_):
    self._data=object_
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
      dump(self._data, open(self.tmp_export_file , u'wb'), 2)
      self._data=None

  def last(self):
    if self._last_datapoint:
      return self._last_datapoint
    else:
      return MeasurementData.last(self)

  def __init__(self, *args, **opts):
    global hmd_file_number
    self.tmp_export_file=os.path.join(TEMP_DIR, u'HMD_'+str(hmd_file_number)+u'.tmp')
    hmd_file_number+=1
    MeasurementData.__init__(self, *args, **opts)

  def __getstate__(self):
    '''
      Define how the class is pickled and copied.
    '''
    self.changed_after_export=True
    # restore saved data, get the object state and save the data again
    self.data
    output=dict(MeasurementData.__getstate__(self))
    self.store_data()
    return output

  def __setstate__(self, state):
    '''
      Unpickling the object will set a new temp file name.
    '''
    global hmd_file_number
    tmp_export_file=os.path.join(TEMP_DIR, u'HMD_'+str(hmd_file_number)+u'.tmp')
    state[u'tmp_export_file']=tmp_export_file
    MeasurementData.__setstate__(self, state)
    hmd_file_number+=1
    self.store_data()
    self.changed_after_export=True

  def __repr__(self):
    '''
      Get object information without reloading the data.
    '''
    if self._data is None:
      output=u"<HugeMD at %s, points=%i"%(hex(id(self)), self._len)
      x, y, z=self.xdata, self.ydata, self.zdata
      dimensions=self.dimensions()
      if z<0:
        output+=u", x='%s', y='%s'"%(dimensions[x], dimensions[y])
      else:
        output+=u", x='%s', y='%s', z='%s'"%(dimensions[x], dimensions[y], dimensions[z])
      output+=u", state stored in: '%s'>"%self.tmp_export_file
    else:
      '''
        Define the string representation of the object. Just some useful information for debugging/IPython console
      '''
      output=u"<HugeMD at %s, cols=%i, points=%i"%(hex(id(self)), len(self.data), len(self))
      if self.zdata<0:
        output+=u", x='%s', y='%s'>"%(self.x.dimension, self.y.dimension)
      else:
        output+=u", x='%s', y='%s', z='%s'>"%(self.x.dimension, self.y.dimension, self.z.dimension)
    return output.encode(out_encoding)

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

  def export(self, file_name, print_info=True, seperator=u' ',
             xfrom=None, xto=None, only_fitted_columns=False):
    if self.changed_after_export or self.plot_options.zrange!=self.last_export_zrange:
      print u"Exporting large dataset, please stay patient"
      self.last_export_output=self.do_export(self.tmp_export_file+u'.gptmp', print_info, seperator, xfrom, xto, only_fitted_columns)
      self.changed_after_export=False
      self.last_export_zrange=self.plot_options.zrange
    # self.store_data()
    copyfile(self.tmp_export_file+u'.gptmp', file_name)
    return self.last_export_output

  def export_matrix(self, file_name):
    MeasurementData.export_matrix(self, file_name)
    # self.store_data()

  do_export=MeasurementData.export

  def __add__(self, other):
    output=MeasurementData.__add__(self, other)
    output.store_data()
    return output

  def __sub__(self, other):
    output=MeasurementData.__sub__(self, other)
    output.store_data()
    return output

  def __mul__(self, other):
    output=MeasurementData.__mul__(self, other)
    output.store_data()
    return output

  def __div__(self, other):
    output=MeasurementData.__div__(self, other)
    output.store_data()
    return output


#--------------------------------------    HugeMD-Class     -----------------------------------------------------#

class MeasurementData4D(MeasurementData):
  '''
    A dataset of x,y,z and I data which can be sliced or 
    projected on a given grid. The grid can be a clolumn of the data or
    calculated as a function of columns.
  '''
  def _get_imd(self): return True
  def _set_imd(self): pass
  is_matrix_data=property(_get_imd)

  def __init__(self, columns=[], const=[], x=0, y=1, error=-1, z=3,
               y2=-1, slice_width=None, slice_center=None,
               gridsize_x=100, gridsize_y=100):
    MeasurementData.__init__(self, columns, const, x, y, error, z)
    self.y2data=y2
    self.gridsize_x=gridsize_x
    self.gridsize_y=gridsize_y
    self.slice_width=slice_width
    self.slice_center=slice_center

  def _get_slice_width(self):
    return self._slice_width


  def _get_slice_center(self):
    return self._slice_center


  def _set_slice_width(self, value):
    if value is not None and value<=0:
      raise ValueError, u'slice_width needs to be a possitive numer or None'
    self._slice_width=value


  def _set_slice_center(self, value):
    if value is not None and (value<self.y2.min() or value>self.y2.max()):
      raise ValueError, u'%g<slice_center<%g must be fullfilled'%(self.y2.min(),
                                                                   self.y2.max())
    self._slice_center=value

  slice_width=property(_get_slice_width, _set_slice_width, None,
                       u"The width of the slice in y2 to plot")
  slice_center=property(_get_slice_center, _set_slice_center, None,
                        u"The center in y2 to plot")


  def _get_y2(self):
    '''
      Get the data for column y2
    '''
    if self.y2data>=0:
      return self.data[self.y2data]
    else:
      return None

  def _set_y2(self, item):
    '''
      Set the data for column y2
    '''
    if self.y2data>=0:
      if len(item)!=len(self):
        raise ValueError, u"shape mismatch: y2 needs to have %i items"%len(self)
      if hasattr(item, u'unit') and hasattr(item, u'dimension'):
        self.data[self.y2data]=item
      else:
        self.data[self.y2data][:]=item
    else:
      raise IndexError, u"y2-index not defined, can't set y2 data"

  y2=property(_get_y2, _set_y2)

  @classmethod
  def from_md(cls, other, y2=-1):
    '''
      Create a new instance of this class using a MeasurementData object.
    '''
    new=cls(y2=y2)
    for item in [
                 u'info',
                 u'short_info',
                 u'sample_name',
                 u'number',
                 u'_yerror',
                 u'logx',
                 u'logy',
                 u'view_x',
                 u'view_z',
                 u'_plot_options',
                 u'xdata',
                 u'ydata',
                 u'zdata',
                 u'sample_name',
                 u'data',
                 u'scan_line',
                 u'scan_line_constant',
                 u'filters',

                ]:
      setattr(new, item,
              getattr(other, item))
    new.plot_together=[new]
    return new

  def export_matrix(self, file_name):
    '''
      Export the filtered data points. If slicing is enabled the data are
      filtered to be inside the slice.
      The data is then projected onto a regular grid in x and y.
    '''
    data=MeasurementData.get_filtered_data_matrix(self)
    x, y, y2, z=self.xdata, self.ydata, self.y2data, self.zdata
    slice_width, slice_center=self.slice_width, self.slice_center
    if slice_center is not None and slice_width is not None:
      slice_idx=numpy.where((data[y2]>=(slice_center-slice_width/2.))&
                            (data[y2]<=(slice_center+slice_width/2.)))[0]
      data=data[:, slice_idx]
    # constrain to plot region
    if self.plot_options.xrange!=[None, None]:
      xrange_idx=numpy.where((data[x]>=self.plot_options.xrange[0])&
                             (data[x]<=self.plot_options.xrange[1]))[0]
      data=data[:, xrange_idx]
    if self.plot_options.yrange!=[None, None]:
      yrange_idx=numpy.where((data[y]>=self.plot_options.yrange[0])&
                             (data[y]<=self.plot_options.yrange[1]))[0]
      data=data[:, yrange_idx]
    I, ignore, ignore=numpy.histogram2d(data[x], data[y], (self.gridsize_x, self.gridsize_y),
                        weights=data[z])
    count, x, y=numpy.histogram2d(data[x], data[y],
                                            (self.gridsize_x, self.gridsize_y))
    I/=numpy.maximum(1, count)
    I[count==0]=numpy.NaN
    Y, X=numpy.meshgrid(y[1:]+(y[1]-y[0])/2., x[1:]+(x[1]-x[0])/2.)

    # Create data as list of x1,y1,z1,x2,y2,z2...,xn,yn,zn
    xyz=numpy.vstack([X.flatten(), Y.flatten(), I.flatten()]
                    ).astype(numpy.float32).transpose().flatten()
    xyz.tofile(open(file_name, u'wb'))



# List of ufunc functions which need an angle as input
angle_functions=(u'sin', u'cos', u'tan', u'sinh', u'cosh', u'tanh')
compare_functions=(u'maximum', u'minimum')

class PlotOptions(object):
  '''
    Object for storing information about the illustration of the data in the plot.
  '''
  _special_plot_parameters=None
  special_using_parameters=u""
  splot=u''
  is_polar=False
  bar_endmarks=True
  short_info_in_title=True
  labels=[]
  arrows=[]
  rectangles=[]
  ellipses=[]
  free_input=[]
  free_input_after=[]
  tics=[None, None, None]
  exp_format=[0, 0, 0]  # set the axis label format to 10^{%L} for xyz
  scan_info=[False, None]

  def __init__(self, initial_text=u""):
    '''
      Initialize the object with optional start parameters.
    '''
    self.settings={}
    self.free_input=[]
    self.free_input_after=[]
    self._xrange=[None, None]
    self._yrange=[None, None]
    self._zrange=[None, None]
    self.labels=[]
    self.arrows=[]
    self.rectangles=[]
    self.ellipses=[]
    self.tics=[None, None, None]
    self.exp_format=[0, 0, 0]
    self.scan_info=[False, None]
    self.input_string(initial_text)

  def overwrite_copy(self, other):
    '''
      Overwrite an other Plot option with the settings from this one.
    '''
    other._xrange=deepcopy(self._xrange)
    other._yrange=deepcopy(self._yrange)
    other._zrange=deepcopy(self._zrange)
    other.free_input=deepcopy(self.free_input)
    other.free_input_after=deepcopy(self.free_input_after)
    other.settings=deepcopy(self.settings)
    other._special_plot_parameters=deepcopy(self._special_plot_parameters)
    other.labels=deepcopy(self.labels)
    other.arrows=deepcopy(self.arrows)
    other.tics=deepcopy(self.tics)
    other.exp_format=deepcopy(self.exp_format)
    return other

  def __str__(self):
    '''
      Return the settings as a string., u"arrow", u"label", u"xtics", u"ytics", u"ztics"
    '''
    output=u""
    for key, items in self.settings.items():
      for value in items:
        output+=u"set "+key+u" "+value+u"\n"
    for value in self.free_input:
      output+=value+u"\n"
    if self.is_polar:
      output+=u"set polar\nset grid polar\n set size square\n"
      output+=(u"set xrange [-%s:%s]\n"%(self._yrange[1], self._yrange[1])).replace(u"-None", u"").replace(u"None", u"")
      output+=(u"set yrange [-%s:%s]\n"%(self._yrange[1], self._yrange[1])).replace(u"-None", u"").replace(u"None", u"")
      output+=(u"set rrange [%s:%s]\n"%(self._xrange[0], self._xrange[1])).replace(u"None", u"")
    else:
      output+=(u"set xrange [%s:%s]\n"%(self._xrange[0], self._xrange[1])).replace(u"None", u"")
      output+=(u"set yrange [%s:%s]\n"%(self._yrange[0], self._yrange[1])).replace(u"None", u"")
      output+=(u"set zrange [%s:%s]\n"%(self._zrange[0], self._zrange[1])).replace(u"None", u"")
      output+=(u"set cbrange [%s:%s]\n"%(self._zrange[0], self._zrange[1])).replace(u"None", u"")
    if not self.bar_endmarks:
      output+=u'set bars small\n'
    for i, label in enumerate(self.labels):
      pos=label[0]
      text=label[1]
      if label[4]:
        # draw box around the label
        output+=u'set object %i rect at %g,%g,%g size char strlen("%s"), char 1 front fs transparent solid 0.75 lw 0.5 # FRAME\n'%(
                                    i+200, pos[0], pos[1], pos[2], text)
      output+=u'set label %i "%s" at %g,%g,%g'%(i+100, text, pos[0], pos[1], pos[2])
      if label[2]:
        output+=u' front'
      if label[3]:
        output+=u' point pt 7'
      if label[4] or label[5]:
        output+=u' center'
      output+=u' %s # LABEL\n'%label[6]
    if self.scan_info[0]:
      output+=u'set label 50 "%s" at graph 0,1 front offset 1.5,-1 # SCAN-INFO\n'%self.scan_info[1]
    for i, arrow in enumerate(self.arrows):
      pos=arrow[0]
      output+=u'set arrow %i from %g,%g,%g to %g,%g,%g'%(i+100,
                          pos[0][0], pos[0][1], pos[0][2],
                          pos[1][0], pos[1][1], pos[1][2])
      if arrow[1]:
        output+=u' nohead'
      if arrow[2]:
        output+=u' front'
      output+=u' %s # ARROW\n'%arrow[3]
    for i, rectangle in enumerate(self.rectangles):
      pos=rectangle[0]
      output+=u'set object %i rectangle from %g,%g,%g to %g,%g,%g'%(i+300,
                          pos[0][0], pos[0][1], pos[0][2],
                          pos[1][0], pos[1][1], pos[1][2])
      if rectangle[1]:
        output+=u' front'
      if not rectangle[2]:
        output+=u' fs empty'
      elif rectangle[3]>=1.:
        output+=u' fs solid 1.0'
      else:
        output+=u' fs transparent solid %g'%rectangle[3]
      if rectangle[5]:
        output+=u' border rgb "%s"'%rectangle[6]
      else:
        output+=u' noborder'
      output+=u' fc rgb "%s"'%rectangle[4]  # fill color
      output+=u' %s # RECTANGLE\n'%rectangle[7]
    for i, ellipses in enumerate(self.ellipses):
      pos=ellipses[0]
      output+=u'set object %i ellipse at %g,%g,%g size %g,%g angle %g'%(i+400,
                          pos[0][0], pos[0][1], pos[0][2],
                          pos[1][0], pos[1][1], pos[2])
      if ellipses[1]:
        output+=u' front'
      if not ellipses[2]:
        output+=u' fs empty'
      elif ellipses[3]>=1.:
        output+=u' fs solid 1.0'
      else:
        output+=u' fs transparent solid %g'%ellipses[3]
      if ellipses[5]:
        output+=u' border rgb "%s"'%ellipses[6]
      else:
        output+=u' noborder'
      output+=u' fc rgb "%s"'%ellipses[4]  # fill color
      output+=u' %s # ELLIPSE\n'%ellipses[7]
    for i, tics in zip([u'x', u'y', u'cb'], self.tics):
      if tics is not None:
        output+=u'set %stics %f\n'%(i, tics)
    for i, exp_format in zip([u'x', u'y', u'cb'], self.exp_format):
      if exp_format==1:
        output+=u'set format %s "10^{%%T}"\n'%(i)
      elif exp_format==2:
        output+=u'set format %s "%%.1t·10^{%%T}"\n'%(i)
      elif exp_format==3:
        output+=u'set format %s "%%.0s %%c"\n'%(i)
      elif exp_format==4:
        output+=u'set format %s "%%.0s %%c[%s-unit]"\n'%(i, i)
      elif exp_format==5:
        output+=u'set format %s "%%.1t{/=[small-font-size] x10^{%%T}}"\n'%(i)
      elif exp_format==6:
        output+=u'set format %s "%%.1te%%T"\n'%(i)
    if self.exp_format[2]:
      output+=u'set cblabel offset 1.5\n'
    for value in self.free_input_after:
      output+=value+u"\n"
    return output

  def __add__(self, input_string):
    '''
      Joing own string with other string.
    '''
    return str(self)+input_string

  def __radd__(self, input_string):
    '''
      Joing own string with other string.
    '''
    return input_string+str(self)

  def input_string(self, text):
    '''
      Get setting information from a text.
    '''
    lines=text.splitlines()
    last_was_frame=False
    for line in lines:
      if line.startswith(u"set"):
        split=line.split(u" ", 2)
        if len(split)==2:
          split.append(u'')
        if split[1]==u"xrange":
          try:
            subsplit=split[2].split(u":")
            xfrom=subsplit[0].lstrip(u"[")
            xto=subsplit[1].rstrip(u"]")
            self.xrange=[xfrom, xto]
          except:
            pass
        elif split[1]==u"yrange":
          try:
            subsplit=split[2].split(u":")
            yfrom=subsplit[0].lstrip(u"[")
            yto=subsplit[1].rstrip(u"]")
            self.yrange=[yfrom, yto]
          except:
            pass
        elif split[1] in [u"zrange", u"cbrange"]:
          try:
            subsplit=split[2].split(u":")
            zfrom=subsplit[0].lstrip(u"[")
            zto=subsplit[1].rstrip(u"]")
            self.zrange=[zfrom, zto]
          except:
            pass
        elif split[1]==u'label' and u' # LABEL' in split[2]:
          try:
            label=split[2].split(u'"', 2)[1]
            position, settings=split[2].split(u' at ')[1].split(u' ', 1)
            position=map(float, position.split(u','))
            front=u'front' in settings
            point=u'point pt 7' in settings
            center=u'center' in settings
            settings=settings.replace(u'front', u'').replace(u'point pt 7', u'')\
                             .replace(u'# LABEL', u'').strip()
            self.labels.append([position, label, front, point,
                                last_was_frame, center, settings])
          except:
            pass
        elif split[1]==u'arrow' and u' # ARROW' in split[2]:
          try:
            pos_from, ignore, pos_to, settings=split[2].split(u'from ')[1].split(u' ', 3)
            pos_from=map(float, pos_from.split(u','))
            pos_to=map(float, pos_to.split(u','))
            front=u'front' in settings
            nohead=u'nohead' in settings
            settings=settings.replace(u'front', u'').replace(u'nohead', u'')\
                             .replace(u'# ARROW', u'').strip()
            self.arrows.append([(pos_from, pos_to), nohead, front, settings])
          except:
            pass
        elif split[1]==u'object':
          if u'# FRAME' in split[2]:
            last_was_frame=True
            continue
        else:
          if split[1] in self.settings:
            self.settings[split[1]].append(split[2])
          else:
            self.settings[split[1]]=[split[2]]
      else:
        self.free_input.append(line)
      last_was_frame=False

  def get_xrange(self): return self._xrange
  def get_yrange(self): return self._yrange
  def get_zrange(self): return self._zrange
  def set_xrange(self, range_):
    if len(range_)==2:
      try:
        x_range=[None, None]
        if range_[0] not in [None, u'']:
          x_range[0]=float(range_[0])
        if range_[1] not in [None, u'']:
          x_range[1]=float(range_[1])
        if None not in x_range and x_range[0]>x_range[1]:
          x_range=[xrange[1], xrange[0]]
        self._xrange=x_range
      except ValueError:
        raise ValueError, u'xrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, u'xrange has to be a tuple or list with two elements of float or None'

  def set_yrange(self, range_):
    if len(range_)==2:
      try:
        yrange=[None, None]
        if range_[0] not in  [None, u'']:
          yrange[0]=float(range_[0])
        if range_[1] not in  [None, u'']:
          yrange[1]=float(range_[1])
        if None not in yrange and yrange[0]>yrange[1]:
          yrange=[yrange[1], yrange[0]]
        self._yrange=yrange
      except ValueError:
        raise ValueError, u'yrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, u'yrange has to be a tuple or list with two elements of float or None'

  def set_zrange(self, range_):
    if len(range_)==2:
      try:
        zrange=[None, None]
        if range_[0]:
          zrange[0]=float(range_[0])
        if range_[1]:
          zrange[1]=float(range_[1])
        if None not in zrange and zrange[0]>zrange[1]:
          zrange=[zrange[1], zrange[0]]
        self._zrange=zrange
      except ValueError:
        raise ValueError, u'zrange has to be a tuple or list with two elements of float or None'
    else:
      raise ValueError, u'zrange has to be a tuple or list with two elements of float or None'


  xrange=property(get_xrange, set_xrange)  # @ReservedAssignment
  yrange=property(get_yrange, set_yrange)
  zrange=property(get_zrange, set_zrange)

  def _get_special_plot_parameters(self):
    if self._special_plot_parameters is not None:
      return str(self._special_plot_parameters)
    else:
      return None

  def _set_special_plot_parameters(self, special_plot_parameters):
    self._special_plot_parameters=special_plot_parameters

  special_plot_parameters=property(_get_special_plot_parameters, _set_special_plot_parameters)

  def _get_werror(self):
    if type(self._special_plot_parameters) is PlotStyle:
      return self._special_plot_parameters.with_errorbars
    else:
      return None

  with_errorbars=property(_get_werror)

class PlotStyle(object):
  '''
    Class to define the plot style of one line. Automatically
    creates the u"with" settings for gnuplot according to some options.
  '''

  _basic_styles={
                 u'lines': u'lines',
                 u'points': u'points',
                 u'linespoints': u'linespoints',
                 u'errorbars': u'errorbars',
                 u'errorlines': u'errorlines',
                 u'dots': u'dots',
                 u'bars': u'boxes',
                 u'steps': u'histeps',
                 u'filled': u'filledcurves',
                 # u'circles': u'circles',
                 }
  _substyles={
              u'filled': {
                         u'default': u'x1 fillstyle transparent solid 0.5',
                         u's. bottom': u'x1',
                         u's. top': u'x2',
                         u's. left': u'y1',
                         u's. right': u'y2',
                         u't. bottom': u'x1 fillstyle transparent solid 0.5',
                         u't. top': u'x2 fillstyle transparent solid 0.5',
                         u't. left': u'y1 fillstyle transparent solid 0.5',
                         u't. right': u'y2 fillstyle transparent solid 0.5',
                         },
              # u'circles': {
                         # u'default': u'fillstyle transparent solid 0.5',
                         # u'empty': u'',
                         # u'transparent': u'fillstyle transparent solid 0.5',
                         # u'full': u'fillstyle solid 1.',
                         # }
              }

  _has_points=[u'points', u'linespoints', u'errorbars', u'errorlines']
  _has_errors=[u'errorbars', u'errorlines', u'circles']
  _point_types=[
                (u' ', 0),
                (u'+', 1),
                (u'x', 2),
                (u'*', 3),
                (u'⊡', 4),
                (u'◼', 5),
                (u'⨀', 6),
                (u'●', 7),
                (u'◬', 8),
                (u'▲', 9),
                ]

  linewidth=1.5
  pointsize=0.5
  pointtype=7
  _color=None
  style=u'lines'
  substyle=u'default'

  def __str__(self):
    output=u'w '
    output+=self._basic_styles[self.style]+u' '
    if self.style in self._substyles:
      output+=self._substyles[self.style][self.substyle]+u' '
    output+=u'lw %g '%self.linewidth
    if self._color is not None:
      if type(self._color) is int:
        output+=u'lc %i '%(self._color)
      else:
        output+=u'lc rgb "#%.2X%.2X%.2X" '%tuple(self._color)
    if self.style in self._has_points:
      output+=u'pt %i ps %g '%(self.pointtype, self.pointsize)
    return output

  def _get_color(self):
    return self._color

  def _set_color(self, color):
    if color is None:
      # unset color specification
      self._color=None
    elif type(color) is int:
      self._color=color
    elif hasattr(color, u'get_current_color'):
      # use gtk.ColorSelection to retrieve the color to be set
      colorspec=color.get_current_color()
      self._color=(colorspec.red_float*255, colorspec.green_float*255, colorspec.blue_float*255)
    elif hasattr(color, u'__iter__'):
      if len(color)!=3:
        raise ValueError, u'color tuple needs to have 3 items'
      if not (color[0]>=0 and color[0]<=255 and \
              color[1]>=0 and color[1]<=255 and \
              color[2]>=0 and color[2]<=255):
        raise ValueError, u'all color entries need to be numbers between 0 and 255'
      self._color=color
    else:
      raise ValueError, u'color needs to be a tuple of 3 numbers, a gtk.ColorSelection or None'

  def _get_werror(self):
    return self.style in self._has_errors

  color=property(_get_color, _set_color)
  with_errorbars=property(_get_werror)

derivatives={  # derivatives to numpy base functions for error propagation
   numpy.sin.__str__(): numpy.cos,
   numpy.cos.__str__(): lambda input_:-numpy.sin(input_),
   numpy.tan.__str__(): lambda input_: 1./numpy.cos(input_)**2,
   numpy.arcsin.__str__(): lambda input_: 1./(numpy.sqrt(1.-input_**2)),
   numpy.arccos.__str__(): lambda input_:-1./(numpy.sqrt(1.-input_**2)),
   numpy.arctan.__str__(): lambda input_: 1./(1.+input_**2),
   numpy.sinh.__str__(): numpy.cosh,
   numpy.cosh.__str__(): numpy.sinh,
   numpy.tanh.__str__(): lambda input_: 1./numpy.cosh(input_)**2,
   numpy.arcsinh.__str__(): lambda input_: 1./(numpy.sqrt(input_**2+1)),
   numpy.arccosh.__str__(): lambda input_:-1./(numpy.sqrt(input_**2-1)),
   numpy.arctanh.__str__(): lambda input_: 1./(1.-input_**2),
   numpy.exp.__str__(): numpy.exp,
   numpy.arcsin.__str__(): lambda input_: 1./(1.-input_**2)**0.5,
   numpy.arccos.__str__(): lambda input_:-1./(1.-input_**2)**0.5,
   numpy.arctan.__str__(): lambda input_: 1./(1.+input_**2),
   numpy.log.__str__(): lambda input_: 1./input_,
   numpy.log10.__str__(): lambda input_: 1./input_,
   numpy.square.__str__(): lambda input_: 2.*input_ ,
   numpy.sqrt.__str__(): lambda input_: 1./(2.*numpy.sqrt(input_)),
   numpy.abs.__str__(): lambda input_: input_,

   # functions with two parameters
   numpy.add.__str__(): (lambda input1, input2: 1., lambda input1, input2: 1.),
   numpy.subtract.__str__(): (lambda input1, input2: 1., lambda input1, input2: 1.),
   numpy.multiply.__str__(): (lambda input1, input2: input2, lambda input1, input2: input1),
   numpy.divide.__str__(): (lambda input1, input2: 1./input2 , lambda input1, input2:-input1/input2**2),
   numpy.power.__str__(): (lambda input1, input2: input2*input1**(input2-1),
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
      The input string should be of the form n1*n2*n3/(d1*d2*d3) where n are units in the 
      nummerator and d units in the denominator.
    '''
    if type(entry_str) not in [str, unicode, PhysicalUnit]:
      raise ValueError, 'can only construct unit from string or other PhysicalUnit not %s'%type(entry_str)
    if type(entry_str) is PhysicalUnit:
      self._unit_parts=deepcopy(entry_str._unit_parts)
    else:
      if type(entry_str) is str:
        # conver string to unicode
        entry_str=unicode(entry_str, in_encoding)
      if len(entry_str.split(u'/'))>2 or len(entry_str.split(u'÷'))>2:
        raise ValueError, 'the format of the input string should be n1*n2*n3/d1*d2*d3'
      self._unit_parts={}
      begin=0
      nummerator=True
      if len(entry_str)>0:
        for i in range(1, len(entry_str)):
          if entry_str[i] in [u'*', u'/', u'·', u'÷']:
            pass
          else:
            continue
          new_region=entry_str[begin:i]
          new_power, new_unit=self._get_unit_exponent(new_region)
          if not nummerator:
            new_power=-new_power
          begin=i+1
          if new_unit in self._unit_parts:
            self._unit_parts[new_unit]+=new_power
          else:
            self._unit_parts[new_unit]=new_power
          if entry_str[i] in [u'/', u'÷']:
            nummerator=False
        new_region=entry_str[begin:]
        new_power, new_unit=self._get_unit_exponent(new_region)
        if not nummerator:
          new_power=-new_power
        if new_unit in self._unit_parts:
          self._unit_parts[new_unit]+=new_power
        else:
          self._unit_parts[new_unit]=new_power
    self._clean_units()

  def _get_unit_exponent(self, new_region):
    '''
      Extract the name and exponent of a unit from string.
    '''
    if len(new_region)==0:
      return '', 0
    new_region=new_region.strip(' ({[]})')
    pow_idx=new_region.find(u'^')
    if pow_idx==-1:
      if new_region[-1]==u'²':
        new_power=2.
        new_region=new_region[:-1]
      elif new_region[-1]==u'³':
        new_power=3.
        new_region=new_region[:-1]
      elif new_region[0]==u'√':
        new_power=0.5
        new_region=new_region[1:]
      else:
        new_power=1.
      new_unit=new_region
    else:
      new_unit=new_region[:pow_idx]
      new_power=float(new_region[pow_idx+1:].strip(u'([{}])'))
    return new_power, new_unit

  def _clean_units(self):
    if u'1' in self._unit_parts:
      del(self._unit_parts[u'1'])
    if u'' in self._unit_parts:
      del(self._unit_parts[u''])
#    keys=list(self._unit_parts.keys())
#    for i, key in enumerate(keys):
#      for key2 in keys[i+1:]:
#        if (key, key2) in known_transformations:
#          if key2 in transformations.SI_base_units:
#            pass
#          else:
#            pass

  def str(self):
    '''
      Construct a combined string for the unit.
    '''
    items=self._unit_parts.items()
    nummerator=[item for item in items if item[1]>0.]
    denominator=[item for item in items if item[1]<0.]
    nummerator.sort()
    denominator.sort()
    output_str=u""
    if len(nummerator)==0 and len(denominator)==0:
      return u''
    first=True
    for name, exponent in nummerator:
      if not first:
        output_str+=u'·'
      else:
        first=False
      if exponent==1.:
        output_str+=name
      else:
        if len(u"%g"%exponent)==1:
          if exponent==2:
            output_str+=u"%s²"%(name)
          elif exponent==3:
            output_str+=u"%s³"%(name)
          else:
            output_str+=u"%s^%g"%(name, exponent)
        else:
          output_str+=u"%s^{%g}"%(name, exponent)
    if len(denominator)>0 and len(nummerator)!=0:
      output_str+=u'/'
      swap_exponen=-1.
    else:
      swap_exponen=1.
    if len(denominator)>1:
      output_str+=u'('
    first=True
    for name, exponent in denominator:
      if not first:
        output_str+=u'·'
      else:
        first=False
      if (swap_exponen*exponent)==1.:
        output_str+=name
      else:
        if len(u"%g"%(swap_exponen*exponent))==1:
          if (swap_exponen*exponent)==2:
            output_str+=u"%s²"%(name)
          elif (swap_exponen*exponent)==3:
            output_str+=u"%s³"%(name)
          else:
            output_str+=u"%s^%g"%(name, (swap_exponen*exponent))
        else:
          output_str+=u"%s^{%g}"%(name, (swap_exponen*exponent))
    if len(denominator)>1:
      output_str+=u')'
    return output_str

  def __str__(self):
    # make sure output is str not unicode
    return self.str().encode(out_encoding)

  def __repr__(self):
    return "<PhysicalUnit '%s'>"%self.__str__()

  def __add__(self, other):
    '''
      Implements adding a string to a unit.
    '''
    if type(other) is str:
      return str(self)+other
    elif type(other) is unicode:
      return self.str()+other
    else:
      raise TypeError, "unsupported operand type(s) for +: 'PhysicalUnit' and '%s'"%type(other).__name__

  def __radd__(self, other):
    '''
      Implements adding a unit to a string.
    '''
    if type(other) is str:
      return other+str(self)
    elif type(other) is unicode:
      return other+self.str()
    else:
      raise TypeError, "unsupported operand type(s) for +: 'PhysicalUnit' and '%s'"%type(other).__name__

  def __mul__(self, other):
    '''
      Implement multiplying units.
    '''
    if isinstance(other, basestring):
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
    if isinstance(other, basestring):
      other=PhysicalUnit(other)
    return self*other**-1.

  def __rdiv__(self, other):
    if other==1:
      other=u'1'
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
    if isinstance(other, basestring):
      other=PhysicalUnit(other)
    return self._unit_parts==other._unit_parts

  def __ne__(self, other):
    if isinstance(other, basestring):
      other=PhysicalUnit(other)
    return self._unit_parts!=other._unit_parts

  def __hash__(self):
    '''
      Defines the hash index for e.g. dict usage as the
      hash of the unicode string of it's representation.
      Makes sure that units can be compared with strings.
    '''
    return self.str().__hash__()

  def simplify(self):
    '''
      Try simplify the unit with the known transformations.
      
      :returns: Tuple of simplified unit and a factor needed for the transformation.
    '''
    i=0
    factor=1.
    # offset=0.
    new=deepcopy(self)
    while (i+1)<len(new._unit_parts):
      item1=sorted(new._unit_parts.keys())[i]
      j=i+1
      while j<len(new._unit_parts):
        item2=sorted(new._unit_parts.keys())[j]
        if (item1, item2) in known_transformations:
          if item2 in transformations.SI_base_units:
            trans=known_transformations[(item1, item2)]
            if trans[1]!=0:
              j+=1
              continue
            exponent=new._unit_parts[item1]
            new._unit_parts[item2]+=exponent
            del(new._unit_parts[item1])
            factor*=trans[0]**exponent
            # offset=offset*trans[0]**exponent+trans[1]
            item1=sorted(new._unit_parts.keys())[i]
            j=i+1
          else:
            trans=known_transformations[(item2, item1)]
            if trans[1]!=0:
              j+=1
              continue
            exponent=new._unit_parts[item2]
            new._unit_parts[item1]+=exponent
            del(new._unit_parts[item2])
            factor*=trans[0]**exponent
            # offset=offset*trans[0]**exponent+trans[1]
        else:
          j+=1
      i+=1
    return new, factor  # , offset)

  def get_transformation(self, conversion):
    '''
      Try to calculate a transformation to a given unit.
    '''
    other=PhysicalUnit(conversion)
    if (self, other) in known_transformations:
      # if complete conversion in the list, use it
      return [self, known_transformations[(self, other)][0],
                    known_transformations[(self, other)][1], other]
    unit1, factor1=self.simplify()
    unit2, factor2=other.simplify()
    output=[self, factor1/factor2, 0., other]
    # go through each partial unit of the conversion
    # and check if it is the same in this unit
    # or if it can be transformed
    own_parts=unit1._unit_parts
    found_keys=[]
    # try to extract conversions for all parts of the unit
    for key, value in unit2._unit_parts.items():
      if key in own_parts:
        if value==own_parts[key]:
          found_keys.append(key)
        else:
          raise ValueError, "conversion from '%s'->'%s' is impossible"%(self, other)
      else:
        found=False
        for own_key in own_parts.keys():
          if (own_key, key) in known_transformations:
            if not own_parts[own_key]==value:
              raise ValueError, "conversion from '%s'->'%s' is impossible"%(self, other)
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
              raise ValueError, "automatic conversion not implemented for '%s'->'%s' because of unit offset."%(self, other)
            output[1]*=multiplyer
            output[2]=output[2]*multiplyer+addition
        if not found:
          raise ValueError, "automatic conversion not implemented for '%s'->'%s'."%(self, other)
        else:
          found_keys.append(own_key)
    if len(found_keys)!=len(own_parts.keys()):
      raise ValueError, "automatic conversion not implemented for '%s'->'%s'."%(self, other)
    return output


class PhysicalConstant(numpy.ndarray):
  '''
    Class to store physical constants. Adds a unit, symbol/name and description to
    the float value.
    Quite similar to PhysicalProperty but only as scalar.
  '''

  def __new__(cls, value, unit=None, symbol=u'', description=u'', dtype=numpy.float64):
    if unit is None:
      if type(value) in [PhysicalConstant, PhysicalProperty] and len(value)==1:
        unit=value.unit
        if type(value) is PhysicalProperty:
          symbol=value.dimension
        else:
          symbol=value.symbol
        value=float(value)
      else:
        raise ValueError, 'You need to supply value and unit'
    obj=numpy.ndarray.__new__(cls, 1, dtype=dtype)
    obj.__setitem__(0, value)
    obj.unit=PhysicalUnit(unit)
    if type(symbol) is str:
      symbol=unicode(symbol, in_encoding)
    if type(description) is str:
      description=unicode(description, in_encoding)
    obj.symbol=symbol
    obj.description=description
    return obj

  def _get_unit(self):
    return self._unit

  def _set_unit(self, unit):
    self._unit=PhysicalUnit(unit)

  unit=property(_get_unit, _set_unit)

  def __array_finalize__(self, obj):
    self.unit=getattr(obj, 'unit', PhysicalUnit(u''))
    self.symbol=getattr(obj, 'symbol', u'')
    self.description=getattr(obj, 'description', u'')

  def __str__(self):
    if self.symbol!=u'':
      return (self.symbol).encode(out_encoding)
    else:
      return (str(self[0])+u' '+self.unit).encode(out_encoding)

  def __repr__(self):
    if self.symbol:
      pre=self.symbol+u'='
    else:
      pre=u''
    if self.description!=u'':
      return (pre+str(self[0])+u' '+self.unit+u' - '+self.description).encode(out_encoding)
    else:
      return (pre+str(self[0])+u' '+self.unit).encode(out_encoding)

  def __array_wrap__(self, out_const, context=None):
    '''
      Function that get's called by numpy ufunct functions after they get
      called with one instance from this class. Makes PhysicalConstant objects
      usable with all standart numpy functions.
      
      :return: PhysicalConstant object with values as result from the function
    '''
    # make use of the functionality of a PhysicalProperty
    PP=PhysicalProperty(self)
    result=PP.__array_wrap__(out_const, context)
    return PhysicalConstant(result)

  def unit_trans(self, transfere):
    '''
      Transform one unit to another. transfere variable is of type [from,b,a,to].
    '''
    if transfere[0]==self.unit:  # only transform if right u'from' parameter
      output=self*transfere[1]+transfere[2]
      output.unit=PhysicalUnit(transfere[3])
      return output
    else:
      return None

  def __mod__(self, conversion):
    '''
      Convenience method to easily get the same PhysicalProperty with a converted unit. Examples:
      pp % u'm' -> a copy of the PhysicalProperty with the unit converted to m
      pp % (u'm', 1.32, -0.2) -> a copy of the PhysicalProperty with the unit converted to u'm' 
                                multiplying by 1.32 and subtracting 0.2
      
      :return: New object instance.    
    '''
    if type(conversion) in [str, unicode, PhysicalUnit]:
      output=self.unit_trans(self.unit.get_transformation(conversion))
      return output
    else:
      if getattr(conversion, u'__iter__', False) and len(conversion)>=3 and \
          type(conversion[0]) in [str, PhysicalUnit] and type(conversion[1]) in (float, int) and type(conversion[2]) in (float, int):
        output=self.unit_trans([self.unit, conversion[1], conversion[2], conversion[0]])
        return output
      else:
        raise ValueError, u'% only defined with str or iterable object of at least one string and two floats/ints'

  def __add__(self, other):
    '''
      Define addition of two PhysicalConstant instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      :return: New instance of PhysicalConstant
    '''
    if hasattr(other, u'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other._radd__(self)
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, "Wrong unit, %s!=%s"%(self.unit, other.unit)
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
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rsub__(self)
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    output=numpy.ndarray.__sub__(self, other)
    output.unit=self.unit
    return output

  def __rsub__(self, other):
    return-self+other

  def __mul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rmul__(self)
    output=numpy.ndarray.__mul__(self, other)
    if hasattr(other, u'unit'):
      output.unit=self.unit*other.unit
    else:
      output.unit=self.unit
    return output

  def __rmul__(self, other):
    return self*other

  def __div__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'dimension'):
      # if other is PhysicalProperty or derived use it's function
      return other.__rdiv__(self)
    output=numpy.ndarray.__div__(self, other)
    if hasattr(other, u'unit'):
      output.unit=self.unit/other.unit
    else:
      output.unit=self.unit
    return output

  def __rdiv__(self, other):
    '''
      Define division of other object by PhysicalProperty instances.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__rdiv__(self, other)
    if hasattr(other, u'unit'):
      output.unit=other.unit/self.unit
    else:
      output.unit=self.unit**-1
    return output

  def __pow__(self, to_power):
    '''
      Define calculation of PhysicalProperty instance to a specified power.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__pow__(self, to_power)
    output.unit=self.unit**to_power
    return output

  def __iadd__(self, other): raise NotImplementedError, u"you can't modify physical constants"
  def __isub__(self, other): raise NotImplementedError, u"you can't modify physical constants"
  def __imul__(self, other): raise NotImplementedError, u"you can't modify physical constants"
  def __idiv__(self, other): raise NotImplementedError, u"you can't modify physical constants"
  def __ipow__(self, to_power): raise NotImplementedError, u"you can't modify physical constants"

class PhysicalWarning(UserWarning):
  '''
    Warning raised when array operations don't make physical sense.
  '''

class PhysicalProperty(numpy.ndarray):
  '''
    Class for any physical property. Stores the data, unit and dimension
    to make unit transformations possible. Can be used with numpy functions.
    Error values are stored and propagated in arithmetric operations.
    
    ===========  ========================================
    Attributes
    ===========  ========================================
      dimension  String for the dimension of the instance
      unit       PhysicalUnit object
      error      Error value as array
    ===========  ========================================
    
    Hints:
      PhysicalProperty can be used with different convenience operators/functions,
      for a PhysicalProperty u'P' these are e.g.:
      
      ==========================  =============================================
      P % [unit]                  Transform the instance to the unit
      P % ([name], [mul], [add])  Transform the instance to [name] using the 
                                  multiplyer [mul] and adding [add]
      P // [dim]                  Get P with different dimension name [dim]
      P // ([dim], [unit])        Get P with different dimension and unit name
      ==========================  =============================================
      
      Additionally PhysicalProperty instances can be used like numpy arrays in functions
      and with respect to slicing. Addition and subtraction is unit dependent and angular
      functions only take angles as input.
  '''
  dimension=u''
  _error=None
  '''
    if defined this is the error value of the property
    the error will be automatically propagated when functions
    get called with instances of this class
  '''

  unit_save=True  # : if true changes units after arithmetic operation and checks if correct

  def __new__(cls, dimension_in, unit_in=None, input_data=[], input_error=None, unit_save=True,
              dtype=numpy.float32):
    '''
      Class constructor when explcidly called.
      
      :param dimension_in: String with the dimensions for that instance
      :param unit_in: String with unit for that instance
    '''
    if unit_in is None:
      if type(dimension_in) in [PhysicalConstant, PhysicalProperty]:
        input_data=dimension_in.view(numpy.ndarray)
        unit_in=dimension_in.unit
        if type(dimension_in) is PhysicalProperty:
          dimension_in=dimension_in.dimension
        else:
          dimension_in=dimension_in.symbol
      else:
        raise ValueError, 'You need to supply dimension and unit'
    # obj=numpy.ndarray.__new__(cls, len(input_data), dtype=numpy.float32)
    obj=numpy.asarray(input_data, dtype=dtype).view(cls).copy()
    obj.unit=PhysicalUnit(unit_in)
    if type(dimension_in) is str:
      dimension_in=unicode(dimension_in, in_encoding)
    obj.dimension=dimension_in
    obj.unit_save=True
    if input_error is not None:
      if len(input_error)!=len(input_data):
        raise ValueError, u'shape mismatch: error and data have different lengths'
      obj.error=numpy.array(input_error, dtype=dtype)
    obj.__setslice__(0, len(input_data), input_data)
    return obj

  def __array_finalize__(self, obj):
    self.unit=getattr(obj, 'unit', PhysicalUnit(u''))
    self.dimension=getattr(obj, 'dimension', u"")
    self._error=getattr(obj, '_error', None)
    # print u"finalize", self.__dict__

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

  def asarray(self):
    return self.view(numpy.ndarray)

  def append(self, item):
    '''
      Append an item to the end of the data, if the array is to small it is enlarged.
    '''
    if hasattr(item, u'dimension'):
      length=self.__len__()
      if self.has_error!=item.has_error:
        raise ValueError, u'items do not have the same error status'
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
          raise ValueError, u"the input needs to be a scalar without error value"
      else:
        raise ValueError, u"can only append scalar or iterable with length 2"
    else:
      if self.has_error:
        raise ValueError, u"need a value with corresponding error to append data"
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

  def get_approx_size(self):
    '''
      Return the data size in bytes.
    '''
    return len(self.tostring())

  def __repr__(self):
    '''
      Return a string representation of the data.
    '''
    output=u'PhysicalProperty(['
    if len(self)<10:
      sval=map(str, self.view(numpy.ndarray))
      output+=u", ".join(sval)
    else:
      sval=map(str, self[:5].view(numpy.ndarray))
      output+=u", ".join(sval)
      output+=u" ... "
      sval=map(str, self[-5:].view(numpy.ndarray))
      output+=u", ".join(sval)
    if self.has_error:
      output+=u"],\tdimension='%s', unit='%s', length=%i, avg.error=%g)"%(self.dimension,
                                                                          self.unit.str(),
                                                                            len(self),
                                                                            self.error.mean())
    else:
      output+=u"],\tdimension='%s', unit='%s', length=%i)"%(self.dimension, self.unit.str(),
                                                            len(self))
    return output.encode(out_encoding)

  def __str__(self):
    '''
      Return the values as string.
    '''
    output=u'['
    if len(self)<10:
      sval=map(str, self.view(numpy.ndarray))
      output+=u", ".join(sval)
    else:
      sval=map(str, self[:5].view(numpy.ndarray))
      output+=u", ".join(sval)
      output+=u" ... "
      sval=map(str, self[-5:].view(numpy.ndarray))
      output+=u", ".join(sval)
    output+=u"]"
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
        assert len(value)==len(self), u"Error needs to have %i values"%len(self)
      self._error=numpy.array(value)

  def _get_unit(self):
    return self._unit

  def _set_unit(self, unit):
    self._unit=PhysicalUnit(unit)

  values=property(_get_values, _set_values)
  has_error=property(_get_has_error)
  error=property(_get_error, _set_error)
  unit=property(_get_unit, _set_unit)

  def unit_trans(self, transfere):
    '''
      Transform one unit to another. transfere variable is of type [from,b,a,to].
    '''
    if transfere[0]==self.unit:  # only transform if right u'from' parameter
      self.unit=PhysicalUnit(transfere[3])
      if self.has_error:
        self._error*=transfere[1]
      self*=transfere[1]
      self+=transfere[2]
      return True
    else:
      return False

  def dim_unit_trans(self, transfere):
    '''
      Transform dimension and unit to another. Variable transfere is of type
      [from_dim,from_unit,b,a,to_dim,to_unit].
    '''
    if len(transfere)>0 and (transfere[1]==self.unit)&(transfere[0]==self.dimension):  # only transform if right u'from_dim' and u'from_unit'
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
      
      :return: PhysicalProperty object with values as result from the function
    '''
    out_arr=out_arr.view(type(self))
    out_arr.unit=self.unit
    out_arr.dimension=self.dimension
    if context:
      # # make sure only physical properties with the same dimension are compared
      if context[0].__name__ in compare_functions:
        if hasattr(context[1][1], u'unit'):
          if self.unit!=context[1][1].unit:
            try:
              other=context[1][1]%self.unit
            except ValueError:
              raise PhysicalWarning, u"Comparing columns with different units"
            else:
              # call the function again with changed unit of other
              return context[0](self, other)
      # # make sure angular dependent functions are called with radian unit
      if context[0].__name__ in angle_functions:
        if self.unit!=u'rad':
          try:
            # call the function again with changed unit
            return context[0](self%u'rad')
          except ValueError:
            raise PhysicalWarning, u'Input to function %s needs to be an angle'%context[0].__name__
        out_arr.unit=PhysicalUnit(u'')
      # # make sure inverse angular functions get called with dimensioinless input
      elif context[0].__name__.startswith(u'arc'):
        if self.unit==u'':
          out_arr.unit=PhysicalUnit(u'rad')
        else:
          raise PhysicalWarning, u"Input to function %s needs to have empty unit"%context[0].__name__
      elif context[0] in [numpy.exp, numpy.log, numpy.log10, numpy.log2]:
        if self.unit!=u'':
          raise PhysicalWarning, u"Input to function %s needs to have empty unit"%context[0].__name__
      elif context[0] is numpy.sqrt:
        out_arr.unit**=0.5
    if self.has_error and context is not None:
      out_arr=self._propagate_errors(out_arr, context)
    return out_arr

  def __getitem__(self, item):
    '''
      Get an item of the object.
    '''
    if hasattr(item, u'__iter__'):
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
    if hasattr(item, u'dimension') and (self.has_error and item.has_error):
      self._error.__setitem__(i, item.error)

  def __setslice__(self, i, j, items):
    '''
      Define a slice from i to j. If input and self has an error set this, too.
    '''
    numpy.ndarray.__setslice__(self, i, j, items)
    if hasattr(items, u'dimension') and (self.has_error and items.has_error):
      self._error.__setslice__(i, j, items.error)

  def _propagate_errors(self, out_arr, context):
    '''
      Calculate the errorpropatation after a function has been processed.
    '''
    try:
      if len(context[1])==1:
        # only a function of one parameter
        out_arr.error=abs(derivatives[context[0].__str__()](
                                      self.view(numpy.ndarray))*self.error)
      elif context[0].__name__ in compare_functions:
        other=context[1][1]
        # if both arguments to compare function have an error value
        # the error of the item in the result array is taken
        if getattr(context[1][1], u'error', None) is not None:
          selfidx=numpy.where(out_arr==self)
          out_arr.error=other.error[:]
          if self.error is not None:
            out_arr.error[selfidx]=self.error
        elif self.error is not None:
          out_arr.error=self.error[:]
      else:
        # a function of two patameters
        if context[1][0] is self:
          # the first patameter is self
          other=context[1][1]
          # if both arguments to ufunc have an error value
          if getattr(context[1][1], u'error', None) is not None:
            out_arr.error=numpy.sqrt(
                          (derivatives[context[0].__str__()][0](self.view(numpy.ndarray),
                                                                other.view(numpy.ndarray))*self.error)**2+\
                          (derivatives[context[0].__str__()][1](self.view(numpy.ndarray),
                                                                other.view(numpy.ndarray))*other.error)**2
                                    )
          # only the first argument has an error value
          else:
            out_arr.error=abs(derivatives[context[0].__str__()][0](self.view(numpy.ndarray),
                                                                   numpy.array(other))*self.error)
        else:
          # the second argument is self, so the first is no PhysicalProperty instance
          out_arr.error=abs(derivatives[context[0].__str__()][1](numpy.array(context[1][0]), self.view(numpy.ndarray))*self.error)
    except KeyError:
      raise NotImplementedError, u"no derivative defined for error propagation of function '%s'"%context[0].__name__
    return out_arr

  def __neg__(self):
    '''
      Define -self
    '''
    return-1.*self

  def __add__(self, other):
    '''
      Define addition of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    output=numpy.ndarray.__add__(self, other)
    return output

  def __iadd__(self, other):
    '''
      Define addition of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    return numpy.ndarray.__iadd__(self, other)

  def _radd__(self, other):
    return self+other

  def __sub__(self, other):
    '''
      Define subtraction of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    return numpy.ndarray.__sub__(self, other)

  def __isub__(self, other):
    '''
      Define subtraction of two PhysicalProperty instances.
      Checking if the unit of both is the same otherwise
      try to convert the second argument to the same unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      if self.unit!=other.unit:
        try:
          other=other%self.unit
        except ValueError:
          raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    return numpy.ndarray.__isub__(self, other)

  def __rsub__(self, other):
    return-self+other

  def __mul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__mul__(self, other)
    if hasattr(other, u'unit'):
      output.unit=self.unit*other.unit
    return output

  def __imul__(self, other):
    '''
      Define multiplication of two PhysicalProperty instances.
      Changes the unit of the resulting object if both objects have a unit.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      self.unit*=other.unit
    return numpy.ndarray.__imul__(self, other)

  def __rmul__(self, other):
    return self*other

  def __div__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__div__(self, other)
    if hasattr(other, u'unit'):
      output.unit=self.unit/other.unit
    return output

  def __idiv__(self, other):
    '''
      Define division of two PhysicalProperty instances.
      
      :return: New instance of PhysicalProperty
    '''
    if hasattr(other, u'unit'):
      self.unit/=other.unit
    return numpy.ndarray.__idiv__(self, other)

  def __rdiv__(self, other):
    '''
      Define division of other object by PhysicalProperty instances.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__rdiv__(self, other)
    if hasattr(other, u'unit'):
      output.unit=other.unit/self.unit
    else:
      output.unit=self.unit**-1
    return output

  def __pow__(self, to_power):
    '''
      Define calculation of PhysicalProperty instance to a specified power.
      
      :return: New instance of PhysicalProperty
    '''
    output=numpy.ndarray.__pow__(self, to_power)
    output.unit=self.unit**to_power
    return output

  def __ipow__(self, to_power):
    '''
      Define calculation of this PhysicalProperty instance to a specified power.
      
      :return: This instance of PhysicalProperty altered
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
      pp // u'new' -> a copy of the PhysicalProperty with the new dimension u'new'
      pp // (u'length',u'm') -> a copy of the PhysicalProperty with the new dimension u'length' and the unit u'm'
      
      :return: New object instance.
    '''
    output=deepcopy(self)
    if isinstance(new_dim_unit, basestring):
      if type(new_dim_unit) is str:
        new_dim_unit=unicode(new_dim_unit, in_encoding)
      output.dimension=new_dim_unit
      return output
    else:
      if getattr(new_dim_unit, u'__iter__', False) and len(new_dim_unit)==2 and \
          isinstance(new_dim_unit[0], basestring) and \
          isinstance(new_dim_unit[1], basestring):
        if type(new_dim_unit[0]) is str:
          new_dim_unit=(unicode(new_dim_unit[0], in_encoding), new_dim_unit[1])
        output.dimension=new_dim_unit[0]
        output.unit=PhysicalUnit(new_dim_unit[1])
        return output
      else:
        raise ValueError, '// only defined with string or iterable object of two strings'

  def __mod__(self, conversion):
    '''
      Convenience method to easily get the same PhysicalProperty with a converted unit. Examples:
      pp % u'm' -> a copy of the PhysicalProperty with the unit converted to m
      pp % (u'm', 1.32, -0.2) -> a copy of the PhysicalProperty with the unit converted to u'm' 
                                multiplying by 1.32 and subtracting 0.2
      
      :return: New object instance.    
    '''
    output=deepcopy(self)
    if type(conversion) in [str, unicode, PhysicalUnit]:
      output.unit_trans(self.unit.get_transformation(conversion))
      return output
    else:
      if getattr(conversion, u'__iter__', False) and len(conversion)>=3 and \
          isinstance(conversion[0], basestring) and type(conversion[1]) in (float, int) and \
          type(conversion[2]) in (float, int):
        output.unit_trans([self.unit, conversion[1], conversion[2], conversion[0]])
        return output
      else:
        raise ValueError, u'% only defined with str or iterable object of at least one string and two floats/ints'

  # Boolean operations:
  def __eq__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__eq__(self.view(numpy.ndarray), other)

  def __gt__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__gt__(self.view(numpy.ndarray), other)

  def __ge__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__ge__(self.view(numpy.ndarray), other)

  def __lt__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__lt__(self.view(numpy.ndarray), other)

  def __le__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__le__(self.view(numpy.ndarray), other)

  def __ne__(self, other):
    if hasattr(other, u'dimension'):
      other=other.view(numpy.ndarray)
    return numpy.ndarray.__ne__(self.view(numpy.ndarray), other)

  def min(self):  # @ReservedAssignment
    '''
      Get minimal value as PhysicalProperty object.
    '''
    if self.has_error:
      index=numpy.argmin(self)
      return self[index]
    else:
      return PhysicalProperty(u'min('+self.dimension+u')', self.unit, [numpy.ndarray.min(self)])

  def max(self):  # @ReservedAssignment
    '''
      Get maximal value as PhysicalProperty object.
    '''
    if self.has_error:
      index=numpy.argmax(self)
      return self[index]
    else:
      return PhysicalProperty(u'max('+self.dimension+u')', self.unit, [numpy.ndarray.max(self)])

  def mean(self):
    '''
      Get (weighted) mean value as PhysicalProperty object.
    '''
    return (self.sum()/float(len(self)))//(u'mean('+self.dimension+u')')

  def sum(self, *args, **opts):  # @ReservedAssignment
    '''
      Get the sum of value as PhysicalProperty object.
    '''
    res=numpy.ndarray.sum(self, *args, **opts)
    if self.has_error:
      # if the object has an error value calculate the weighted mean
      output_error=numpy.sqrt((self._error**2).sum(*args, **opts))
      if res.shape==():
        return PhysicalProperty(u'sum('+self.dimension+u')', self.unit,
                              [numpy.ndarray.sum(self, *args, **opts)], [output_error])
      else:
        return PhysicalProperty(u'sum('+self.dimension+u')', self.unit,
                              numpy.ndarray.sum(self, *args, **opts), output_error)
    else:
      if res.shape==():
        return PhysicalProperty(u'sum('+self.dimension+u')', self.unit, [res])
      else:
        return PhysicalProperty(u'sum('+self.dimension+u')', self.unit, res)

  def reshape(self, *a, **opts):
    '''
      Change the dimensional order of the data.
    '''
    output=numpy.ndarray.reshape(self, *a, **opts)
    if output.has_error:
      output._error=self._error.reshape(*a, **opts)
    return output

  def flatten(self):
    '''
      Reduce data to one dimension.
    '''
    output=numpy.ndarray.flatten(self)
    if output.has_error:
      output._error=self._error.flatten()
    return output

  def join(self, other):
    '''
      Combine two PhysicalProperty objects of the same unit.
    '''
    # can join with a list of PhysicalProperty objects
    if type(other) is list:
      if len(other)==1:
        other=other[0]
      else:
        other=other[0].join(other[1:])

    if hasattr(other, u'unit') and (self.unit!=other.unit or (self.has_error!=other.has_error)):
      try:
        other=other%self.unit
      except ValueError:
        raise ValueError, u"Wrong unit, %s!=%s"%(self.unit, other.unit)
    joined_data=numpy.append(self, other)
    output=self.__class__(self.dimension, self.unit, joined_data)
    if (self.has_error and hasattr(other, u'unit') and other.has_error):
      joined_error=numpy.append(self.error, other.error)
      output.error=joined_error
    return output

################### define some common physical constants

constants={
           #
           u'h': PhysicalConstant(6.6260693E-31, u'g·m^2/s', u'h', u'plancks constant'),
           u'hbar': PhysicalConstant(1.0545717E-31, u'g⋅m^2/s', u'hbar', u'plancks constant over 2π'),
           u'c': PhysicalConstant(2.9979246E8, u'm/s', u'c', u'speed of light'),
           #
           u'µ_0': PhysicalConstant(1.2566371E-3, u'g⋅m/A^2·s^2', u'µ_0', u'magnetic constant'),
           u'µ_B': PhysicalConstant(9.2740095E-24 , u'A⋅m^2', u'µ_B', u'Bohr magneton'),
           #
           u'r_B': PhysicalConstant(5.291772E-11 , u'm', u'r_B', u'Bohr radius'),
           u'r_e': PhysicalConstant(2.81794E-15 , u'm', u'r_e', u'Classical electron radius'),
           #
           u'm_n': PhysicalConstant(1.67493E-24 , u'g', u'm_n', u'Neutron mass'),
           u'm_e': PhysicalConstant(9.1094E-28  , u'g', u'm_e', u'Electron mass'),
           }


class MultiplotList(list):
  '''
    A list of measurements for a multiplot.
  '''
  def __init__(self, input_list=None):
    self.title=u"Multiplot"
    if input_list is None:
      self.sample_name=u''
      list.__init__(self)

    else:
      self.sample_name=str(input_list[0][0].sample_name)
      list.__init__(self, input_list)

  def append(self, dataset):
    if len(dataset)!=2:
      raise ValueError, u'items of a MultiplotList need to be (MeasurementData, file_name) sets'
    if dataset[0] in [item[0] for item in self]:
      # do not add the same dataset twice
      return
    dataset=tuple(dataset)
    if len(self)==0:
      list.append(self, dataset)
      self.sample_name=dataset[0].sample_name
    elif (self[0][0].x.unit==dataset[0].x.unit and\
          self[0][0].y.unit==dataset[0].y.unit):
      list.append(self, dataset)
    else:
      raise ValueError, u'only items with units "%s" vs. "%s" can be added to this multiplot'%(
                            self[0][0].x.unit, self[0][0].y.unit)
  def __contains__(self, item):
    if hasattr(item, u'__iter__') and len(item)==2:
      return list.__contains__(self, item)
    else:
      return item in [i[0] for i in self]

  def remove(self, item):
    index=self.index(item)
    self.pop(index)

  def index(self, item):
    if hasattr(item, u'__iter__') and len(item)==2:
      return list.index(self, item)
    else:
      return [i[0] for i in self].index(item)

def calculate_transformations():
  '''
    Use a dictionary of unit transformations to calculate
    all combinations of the transformations inside.
  '''
  trans=transformations.unit_transformations
  output=dict([(tuple(key.split(u'->', 1)), value) for key, value in trans.items()])
  keys=list(output.keys())
  # calculate inverse transformations
  for key in keys:
    if len(output[key])==2:
      output[(key[1], key[0])]=(1./output[key][0],-(output[key][1]/output[key][0]))
    else:
      output[(key[1], key[0])]=(1./output[key][0],-(output[key][1]/output[key][0]),
                              output[key][3], output[key][2])
  # calculate transformations from units and prefixes
  prefixes=dict(transformations.unit_prefixes)
  prefixes.update({'':1.})
  SI_units=transformations.SI_base_units
  for unit in SI_units:
    for prefix, factor in prefixes.items():
      for prefix2, factor2 in prefixes.items():
        output[(prefix+unit, prefix2+unit)]=(factor/factor2, 0.)
  # calculate transformations over two or more units.
  done=False
  while not done:
    # while there are still transformations changed, try to find new ones.
    done=True
    for key in list(output.keys()):
      for key2 in list(output.keys()):
        if key[1]==key2[0] and key[0]!=key2[1] and (key[0], key2[1]) not in output and\
              len(output[key])==2 and len(output[key2])==2:
          done=False
          output[(key[0], key2[1])]=(output[key][0]*output[key2][0],
                                     output[key2][0]*output[key][1]+output[key2][1])
          output[(key2[1], key[0])]=(1./output[(key[0], key2[1])][0],
                                     -(output[(key[0], key2[1])][1]/output[(key[0], key2[1])][0]))
  return output

# Dictionary of transformations from one unit to another
if 'calculated' in transformations:
  known_transformations=dict([(tuple(key.split('->', 1)), value)
                              for key, value in transformations['calculated'].items()])
else:
  # calculate once and store in config
  known_transformations=calculate_transformations()
  transformations['calculated']=dict([(u'->'.join(key), value)
                              for key, value in known_transformations.items()])

