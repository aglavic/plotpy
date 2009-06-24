#!/usr/bin/env python
'''
 Classes for storing the measurement data of any session.
 Units and dimensions are also stored for easier accessing and transformation.
'''

# Pleas do not make any changes here unless you know what you are doing.

from sys import hexversion
try:
  import numpy
except ImportError:
  numpy=None

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

SPLIT_SENSITIVITY=0.001

#++++++++++++++++++++++++++++++++++++++MeasurementData-Class+++++++++++++++++++++++++++++++++++++++++++++++++++++#
class MeasurementData:
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
  logx=False
  logy=False
  logz=False
  zdata=-1
  scan_line_constant=-1 # the column to sort the data for when using 3d plots.
  scan_line=-1 # the column changed in one scan.
  const_data=[] # select, which data should not be varied in this maesurement and the accouracy
  info=''
  short_info=''
  number=''
  sample_name=''
  plot_options=''
  view_x=60
  view_z=30
  filters=[] # a list of filters to be applied when returning the data, the format is:
             # ( column , from , to , include )

  def __init__(self, columns, const,x,y,yerror,zdata=-1): 
    '''
      Constructor for the class.
      If the values are not reinitialized we get problems
      with the creation of objects with the same variable name.
    '''
    self.number_of_points=0 #counts number of stored data-points
    self.index=0
    self.info=''
    self.sample_name=''
    self.plot_options=''
    self.data=[]
    for column in columns: # create Property for every column
      self.data.append(PysicalProperty(column[0],column[1]))
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
      self.const_data.append([con[0],PysicalProperty(self.data[con[0]].dimension,self.data[con[0]].unit)])
      self.const_data[-1][1].append(con[1])
    self.plot_together=[self] # list of datasets, which will be plotted together
    self.fit_object=None
    if not numpy is None:
      self.process_funcion=self.process_funcion_numpy

  def __iter__(self): # see next()
    '''
      Function to iterate through the data-points, object can be used in "for bla in data:".
      Skippes pointes that are filtered.
    '''
    data_pointer=0
    # for faster access use local variables
    data=self.data
    filters=self.filters
    number_points=len(data[0])
    while data_pointer<number_points:
      filtered=False
      for data_filter in filters:
        # if the datapoint is not included (filter[3]=True) or excluded skip it
        filtered = (filtered or (not ((data_filter[3] and \
                    (data[data_filter[0]].values[data_pointer]>data_filter[1]) and \
                    (data[data_filter[0]].values[data_pointer]<data_filter[2])\
              ) or ((not data_filter[3]) and \
                  ((data[data_filter[0]].values[data_pointer]<data_filter[1]) or \
                    (data[data_filter[0]].values[data_pointer]>data_filter[2]))))))
      data_pointer+=1
      if filtered:
        continue
      yield [value.values[(data_pointer-1)] for value in data]
 
  def __len__(self): 
    '''
      len(MeasurementData) returns number of Datapoints.
    '''
    return len(self.data[0])

  def append(self, point):
    '''
      Add a point to this sequence.
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

  def get_data(self,count): 
    '''
      Get datapoint at position count.
    '''
    return [value.values[count] for value in self.data]

  def set_data(self,point,count): 
    '''
      Set datapoint at position count.
    '''
    for value in self.data:
      value.values[count]=point[self.data.index(value)]
    return self.get_data(count)

  def list(self): 
    '''
      Get x-y list of all data.
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
      Change units of one column according to a given list of translations.
    '''
    for unit in unit_list:
      if len(unit)==4:
        self.data[col].unit_trans(unit)
      else:
        self.data[col].dim_unit_trans(unit)
    for con in self.const_data:
      if con[0]==col:
        if len(unit)==4:
            con[1].unit_trans(unit)
        else:
            con[1].dim_unit_trans(unit)
    return [self.last()[col],self.units()[col]]

  def process_funcion(self,function): 
    '''
      Processing a function on every data point.
    '''
    for i in range(self.number_of_points):
      point = self.get_data(i)
      self.set_data(function(point),i)
    return self.last()

  def process_funcion_numpy(self,function): 
    '''
      Processing a function on every data point.
      When numpy is installed this is done via one proccess call 
      for arrays. (This leads to a huge speedup)
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
      MeasurementData.process_funcion(self, function)
    return self.last()

  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None): 
    '''
      Write data in text file seperated by 'seperator'.
    '''
    xd=self.xdata
    yd=self.ydata
    zd=self.zdata
    data=[point for point in self if (((xfrom is None) or (point[xd]>=xfrom)) and \
                                      ((xto is None) or (point[xd]<=xto)))]
    # convert Numbers to str
    if zd>=0:
      if self.scan_line_constant<0:
        max_dx=max([abs(data[i][xd]-data[i+1][xd]) for i in range(len(data)-1)])
        max_dy=max([abs(data[i][yd]-data[i+1][yd]) for i in range(len(data)-1)])
      else:
        slc=self.scan_line_constant
        max_dslc=max([abs(data[i][slc]-data[i+1][slc]) for i in range(len(data)-1)])
      # for logarithmic data avoid holes because of low values
      if self.logz:
        absmin=None
        for line in self.plot_options.splitlines():
          if 'cbrange' in line:
            try:
              absmin=float(line.split('[')[1].split(':')[0])
            except ValueError:
              absmin=None
        if not absmin > 0:
          absmin=min(map(abs, self.data[zd].values))
        if absmin==0:
          absmin=1e-10
        def zdata_to_absmin(point):
          point[zd]=max(absmin, point[zd])
          return point
        map(zdata_to_absmin, data)
      
      # try to find the best way to split the data for Gnuplot
      if self.scan_line_constant >= 0:
        scan_line_constant=self.scan_line_constant
        if self.scan_line >= 0:
          cmp_to=self.scan_line
        elif xd!=scan_line_constant:
          cmp_to=xd
        else:
          cmp_to=yd
        sensitivity=SPLIT_SENSITIVITY*max_dslc
        def compare_columns(point1, point2):
          if point1[scan_line_constant]-sensitivity>point2[scan_line_constant]:
            return 1
          if point1[scan_line_constant]<point2[scan_line_constant]-sensitivity:
            return -1
          return cmp(point1[cmp_to], point2[cmp_to])
        data.sort(compare_columns)
        insert_indices=[i for i in range(len(data)-1) if (data[i+1][cmp_to]<data[i][cmp_to])]
      else:
        def compare_xy_columns(point1, point2):
          '''Compare two points by y- and x-column'''
          if point1[xd]-sensitivity>point2[xd]:
            return 1
          if point1[xd]<point2[xd]-sensitivity:
            return -1
          return cmp(point1[yd], point2[yd])
            
        def compare_yx_columns(point1, point2):
          if point1[yd]-sensitivity>point2[yd]:
            return 1
          if point1[yd]<point2[yd]-sensitivity:
            return -1
          return cmp(point1[xd], point2[xd])
        
        data_xysort=list(data)
        data_yxsort=data
        sensitivity=SPLIT_SENSITIVITY*max_dx
        data_xysort.sort(compare_xy_columns)
        sensitivity=SPLIT_SENSITIVITY*max_dy
        data_yxsort.sort(compare_yx_columns)
        # insert blanck lines between scans for 3d plot
        insert_indices_xy=[i for i in range(len(data)-1) if (data_xysort[i+1][yd]<data_xysort[i][yd])]
        insert_indices_yx=[i for i in range(len(data)-1) if (data_yxsort[i+1][xd]<data_yxsort[i][xd])]
        if len(insert_indices_xy) <= len(insert_indices_yx):
          insert_indices=insert_indices_xy
          data=data_xysort
        else:
          insert_indices=insert_indices_yx
          data=data_yxsort
    if hex(hexversion) >= '0x2060000': # test if format function is available (py 2.6.0)
      float_format='{0:g}'.format
    else:
      def float_format(string):
        return "%g" % string
    data_str=map(lambda point: map(float_format, point), data)
    data_lines=map(seperator.join, data_str)
    if self.zdata>=0:
      for i, j in enumerate(insert_indices):
        data_lines.insert(i+j+1, '')
    write_file=open(file_name,'w')
    if print_info:
      write_file.write('# exportet dataset from measurement_data_structure.py\n# Sample: '+self.sample_name+'\n#\n# other informations:\n#'+self.info.replace('\n','\n#'))
      columns=''
      for i in range(len(self.data)):
        columns=columns+' '+self.dimensions()[i]+'['+self.units()[i]+']'
      write_file.write('#\n#\n# Begin of Dataoutput:\n#'+columns+'\n')
    write_file.write('\n'.join(data_lines)+'\n')
    write_file.close()
    return len(data_lines) # return the number of exported data lines

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
      
class PysicalProperty:
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
    return self.values[index]

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
      return [self.values[-1],self.unit]
    else:
      return [self.values[-1],self.unit]

  def dim_unit_trans(self,transfere): 
    '''
      Transform dimension and unit to another. Variable transfere is of type
      [from_dim,from_unit,b,a,to_dim,to_unit].
    '''
    if (transfere[1]==self.unit)&(transfere[0]==self.dimension): # only transform if right 'from_dim' and 'from_unit'
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
