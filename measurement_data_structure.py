#!/usr/bin/env python
#
# Class for storing the measurement data of any kind
# units and dimensions are also stored for easier accessing and transformation
#
# At this moment used for SQUID,4circle and reflectometer plotting
#  can easyly be used for other file types togather with measurement_data_plotting.py
#
# Last change: 26.11.08
#
# To do:
# -clean up code and create better class structure with childs

# Pleas do not make any changes here unless you know what you are doing.

import globals

#++++++++++++++++++++++++++++++++++++++MeasurementData-Class+++++++++++++++++++++++++++++++++++++++++++++++++++++#
class MeasurementData:
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

  def __init__(self, columns, const,x,y,yerror,zdata=-1): # constructor for the class - if the values are not reinitialized we get problem with creating objects with the same variable name
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

  def __iter__(self): # see next()
    return self
 
# function to iterate through the data-points, object can be used in "for bla in data:"
# skippes pointes that are filtered
  def next(self): 
    filtered=True
    while filtered:
      if self.index == self.number_of_points:
        self.index=0
        raise StopIteration
      filtered = False
      for data_filter in self.filters:
        # if the datapoint is not included (filter[3]=True) or excluded skip it
        filtered = (filtered | (not ((data_filter[3] & \
                    (self.data[data_filter[0]].values[self.index]>data_filter[1]) & \
                    (self.data[data_filter[0]].values[self.index]<data_filter[2])\
              ) | ((not data_filter[3]) & \
                  ((self.data[data_filter[0]].values[self.index]<data_filter[1]) | \
                    (self.data[data_filter[0]].values[self.index]>data_filter[2]))))))
      self.index=self.index+1
    return self.get_data(self.index-1)

  def __len__(self): # len(MeasurementData) returns number of Datapoints
    return len(self.data[0])

  def append(self, point): # add point to the sequence
    data=self.data # speedup data_lookup
    if len(point)==len(data):
      for i,val in enumerate(point):
        data[i].append(val)
      self.number_of_points+=1
      return point#self.get_data(self.number_of_points-1)
    else:
      return 'NULL'

  def get_data(self,count): # get datapoint at position count
    return [value.values[count] for value in self.data]

  def set_data(self,point,count): # set datapoint at position count
    for value in self.data:
      value.values[count]=point[self.data.index(value)]
    return self.get_data(count)

  def list(self): # get x-y list of all data
    if (self.xdata<0)&(self.ydata<0):
      return [[i+1,i+1] for i,point in enumerate(self)]
    elif self.xdata<0:
      return [[i+1,point[self.ydata]] for i,point in enumerate(self)]
    elif self.ydata<0:
      return [[point[self.xdata],i+1] for i,point in enumerate(self)]
    elif self.zdata>=0:
      return [[point[self.xdata],point[self.ydata],point[self.zdata]] for point in self]
    else:
      return [[point[self.xdata],point[self.ydata]] for point in self]

  def list_err(self): # get x-y-dy list of all data
    if (self.xdata<0)&(self.ydata<0):
      return [[i+1,i+1,point[self.yerror]] for i,point in enumerate(self)]
    elif self.xdata<0:
      return [[i+1,point[self.ydata],point[self.yerror]] for i,point in enumerate(self)]
    elif self.ydata<0:
      return [[point[self.xdata],i+1,point[self.yerror]] for i,point in enumerate(self)]
    else:
      return [[point[self.xdata],point[self.ydata],point[self.yerror]] for point in self]

  def listxy(self,x,y): # get x-y list of data with different x,y values
    return [[point[x],point[y]] for point in self]

  def type(self): # short form to get the first constant data column
    if len(self.const_data)>0:
      return self.const_data[0][0]
    else:
      return 0

  def first(self): # return the first datapoint
    return self.get_data(0)

  def last(self): # return the last datapoint
    return self.get_data(self.number_of_points-1)

  def is_type(self, dataset): # check if a point is consistant with constand data of this sequence
      last=self.last()
      for const in self.const_data:
        if (abs(dataset[const[0]]-last[const[0]])<const[1].values[0]):
          continue
        else:
          return False
      return True

  def units(self): # return units of all columns
    return [value.unit for value in self.data]

  def dimensions(self): # return dimensions of all columns
    return [value.dimension for value in self.data]

  def xunit(self): # get unit of xcolumn
    return self.units()[self.xdata]

  def yunit(self): # get unit of ycolumn
    return self.units()[self.ydata]

  def zunit(self): # get unit of ycolumn
    return self.units()[self.zdata]

  def xdim(self): # get dimension of xcolumn
    return self.dimensions()[self.xdata]

  def ydim(self): # get dimension of ycolumn
    return self.dimensions()[self.ydata]

  def zdim(self): # get dimension of ycolumn
    return self.dimensions()[self.zdata]

  def unit_trans(self,unit_list): # change units of all columns according to a given list of translations
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

  def unit_trans_one(self,col,unit_list): # change units of one column according to a given list of translations
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

  def process_funcion(self,function): # processing a function on every data point
    for i in range(self.number_of_points):
      point = self.get_data(i)
      self.set_data(function(point),i)
    return self.last()

  def export(self,file_name,print_info=True,seperator=' ',xfrom=None,xto=None): # write data in text file seperated by 'seperator'
    # find indices within the selected export range between xfrom and xto, xvalues must be sorted for this to work
    xfrom_index=0
    xto_index=len(self)-1
    for i,value in enumerate(self.data[self.xdata].values):
      if not xfrom==None:
        if xfrom>=value:
          xfrom_index=i
      if not xto==None:
        if xto<=self.data[self.xdata].values[-1-i]:
          xto_index=len(self)-1-i
    write_file=open(file_name,'w')
    if print_info:
      write_file.write('# exportet dataset from measurement_data_structure.py\n# Sample: '+self.sample_name+'\n#\n# other informations:\n#'+self.info.replace('\n','\n#'))
      columns=''
      for i in range(len(self.data)):
        columns=columns+' '+self.dimensions()[i]+'['+self.units()[i]+']'
      write_file.write('#\n#\n# Begin of Dataoutput:\n#'+columns+'\n')
    last_point=self.get_data(0)
    for i,point in enumerate(self):
      if (i>=xfrom_index)&(i<=xto_index):
        if (self.zdata>=0)&(not round(point[self.ydata],5)==round(last_point[self.ydata],5)):
          write_file.write('\n')
        last_point=point
        line=''
        for value in point:
          line = line+str(value)+seperator
        write_file.write(line+'\n')
    write_file.close()
    return xto_index-xfrom_index+1 # return the number of exported data lines

  def max(self,xstart=None,xstop=None): # returns x and y value of point with maximum x
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

  def min(self,xstart=None,xstop=None): # returns x and y value of point with minimum x
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
      
# Class for any physical property
class PysicalProperty:
  index=0
  values=[]
  unit=''
  dimension=''
  def __init__(self, dimension_in, unit_in):
    self.values=[]
    self.index=0
    self.unit=unit_in
    self.dimension=dimension_in

  def __iter__(self): # see next()
    return self
 
  def next(self): # function to iterate through the data-points, object can be used in "for bla in data:"
    if self.index == len(self.values):
      self.index=0
      raise StopIteration
    self.index=self.index+1
    return self.values[index]

  def __len__(self): # len(PhysicalProperty) returns number of Datapoints
    return len(self.values)

  def append(self, number): # add value
    self.values.append(number)

  def unit_trans(self,transfere): # transform one unit to another transfere is of type [from,b,a,to]
    if transfere[0]==self.unit: # only transform if right 'from' parameter
      new_values=[]
      for value in self.values:
        new_values.append(value*transfere[1]+transfere[2])
      self.values=new_values
      self.unit=transfere[3]
      return [self.values[-1],self.unit]
    else:
      return [self.values[-1],self.unit]

  def dim_unit_trans(self,transfere): # transform dim. and unit to another [from_dim,from_unit,b,a,to_dim,to_unit]
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
    if to_index==None:
      to_index=len(self)-1
    return max([self.values[i] for i in range(from_index,to_index)])

  def min(self,from_index=0,to_index=None):
    if to_index==None:
      to_index=len(self)-1
    return min([self.values[i] for i in range(from_index,to_index)])
