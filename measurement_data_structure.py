#!/usr/bin/env python
'''
 Classes for storing the measurement data of any session.
 Units and dimensions are also stored for easier accessing and transformation.
'''

# Pleas do not make any changes here unless you know what you are doing.

import globals
from sys import hexversion

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

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
    if globals.debug:
      globals.debug_file.write('construct MeasurementData(self,'+ str(columns)+','+ str(const)+','+ str(x)+','+ str(y)+','+ str(yerror)+','+ str(zdata)+ ')\n')
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

  def __iter__(self): # see next()
    '''
      Function to iterate through the data-points, object can be used in "for bla in data:".
      Skippes pointes that are filtered.
    '''
    data_pointer=0
    # for faster access use local variables
    data=self.data
    get_data=self.get_data
    filters=self.filters
    number_points=len(data[0])
    values=[value.values for value in data]
    while data_pointer<number_points:
      filtered=True
      while filtered:
        filtered = False
        for data_filter in filters:
          # if the datapoint is not included (filter[3]=True) or excluded skip it
          filtered = (filtered | (not ((data_filter[3] & \
                      (data[data_filter[0]].values[data_pointer]>data_filter[1]) & \
                      (data[data_filter[0]].values[data_pointer]<data_filter[2])\
                ) | ((not data_filter[3]) & \
                    ((data[data_filter[0]].values[data_pointer]<data_filter[1]) | \
                      (data[data_filter[0]].values[data_pointer]>data_filter[2]))))))
        data_pointer+=1
      yield [value[(data_pointer-1)] for value in values]
 
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
    yd=self.xdata
    zd=self.xdata
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
    if (self.xdata<0)&(self.ydata<0):
      return [[i+1,i+1,point[self.yerror]] for i,point in enumerate(self)]
    elif self.xdata<0:
      return [[i+1,point[self.ydata],point[self.yerror]] for i,point in enumerate(self)]
    elif self.ydata<0:
      return [[point[self.xdata],i+1,point[self.yerror]] for i,point in enumerate(self)]
    elif self.yerror<0:
      return [[point[self.xdata],point[self.ydata],0] for i,point in enumerate(self)]
    else:
      return [[point[self.xdata],point[self.ydata],point[self.yerror]] for point in self]

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

  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None): 
    '''
      Write data in text file seperated by 'seperator'.
    '''
    data=[point for point in self if (((xfrom is None) or (point[self.xdata]<=xfrom)) and \
                                      ((xfrom is None) or (point[self.xdata]<=xfrom)))]
    # convert Numbers to str
    if self.zdata>=0:
      xd=self.xdata
      yd=self.ydata
      if self.scan_line_constant >= 0:
        scan_line_constant=self.scan_line_constant
        if xd!=scan_line_constant:
          cmp_to=xd
        else:
          cmp_to=yd
        def compare_columns(point1, point2):
          if point1[scan_line_constant]>point2[scan_line_constant]:
            return 1
          if point1[scan_line_constant]<point2[scan_line_constant]:
            return -1
          return cmp(point1[cmp_to], point2[cmp_to])
        data.sort(compare_columns)
        insert_indices=[i for i in range(len(data)-1) if (data[i+1][cmp_to]<data[i][cmp_to])]
      else:
        def compare_xy_columns(point1, point2):
          '''Compare two points by y- and x-column'''
          if point1[xd]>point2[xd]:
            return 1
          if point1[xd]<point2[xd]:
            return -1
          return cmp(point1[yd], point2[yd])
            
        def compare_yx_columns(point1, point2):
          if point1[yd]>point2[yd]:
            return 1
          if point1[yd]<point2[yd]:
            return -1
          return cmp(point1[xd], point2[xd])
        

        data_xysort=list(data)
        data_yxsort=data
        data_xysort.sort(compare_xy_columns)
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
    write_file.write('\n'.join(data_lines))
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
