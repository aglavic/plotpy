#!/usr/bin/env python
'''
   Module for data treatment and macro processing.
'''

from configobj import ConfigObj
from measurement_data_structure import MeasurementData

class FileActions:
  '''
    A Class designed to preform simple operations on one dataset and
    to store those in a history for later macro prosession.
  '''
  history=None
  actions=None

  def __init__(self, window):
    '''
      Constructor creating a histroy, the allowed actions
      and connecting the object to the open window.
    '''
    self.history=[]
    self.window=window
    self.actions={
                  'change filter': self.change_data_filter, 
                  'cross-section': self.cross_section
                  }

  def activate_action(self, action, *args):
    '''
      Every action performed by this class is stored so
      it can be shown in a log or reused in makros for other sequences.
    '''
    self.history.append((action, args))
    self.actions[action](*args)
    return True
  
  def reactivate_action(self, action):
    '''
      Run an action without storing it in the history.
      Used when running a makro.
    '''
    self.actions[action[0]](*action[1])

  def store(self, from_index=None, to_index=None):
    '''
      Store a subset of the history actions as a makro.
    '''
    conf=ConfigObj(unrepr=True)
    for i, action in enumerate(self.history[from_index:to_index]):
     conf[str(i)]=action
    output=MakroRepr()
    conf.write(output)
    return output
  
  def run_makro(self, makro):
    '''
      Execute the actions from a MakroRepr object.
    '''
    makro_obj=ConfigObj(infile=makro, unrepr=True)
    for i in range(len(makro_obj.items())):
      if str(i) in makro_obj:
        self.reactivate_action(makro_obj[str(i)])

  #+++++++++++ The performable actions ++++++++++++++++++++

  def change_data_filter(self, filters):
    '''
      Change the filter settings of a MeasurementData object.
    '''
    self.window.measurement[self.window.index_mess].filters=filters

  def cross_section(self, x, x_0, y, y_0, w, binning):
    '''
      Create a slice through a dataset using the create_cross_section function.
      This funcion is called as the action.
    '''
    data=self.window.measurement[self.window.index_mess]
    try:
      cs_object=self.create_cross_section(x, x_0, y, y_0, w, binning)
      if cs_object is None:
        return False
      cs_object.number=data.number
      cs_object.short_info='%s - Cross-Section through (%g,%g)+x*(%g,%g)' % (
                           data.short_info, x_0, y_0, x,y) 
      cs_object.sample_name=data.sample_name
      cs_object.info=data.info
      self.window.measurement.insert(self.window.index_mess+1, cs_object)
      self.window.index_mess+=1
    except ValueError:
      return False

  #----------- The performable actions --------------------


  #++++++++ Functions not directly called as actions ++++++
  
  def create_cross_section(self, x, x_0, y, y_0, w, binning):
    '''
      Create a cross-section of 3d-data along an arbitrary line.
    '''
    from math import sqrt
    data=self.window.measurement[self.window.index_mess].list_err()
    dims=self.window.measurement[self.window.index_mess].dimensions()
    units=self.window.measurement[self.window.index_mess].units()
    cols=(self.window.measurement[self.window.index_mess].xdata, 
          self.window.measurement[self.window.index_mess].ydata, 
          self.window.measurement[self.window.index_mess].zdata, 
          self.window.measurement[self.window.index_mess].yerror)
    new_cols=[(dims[col], units[col]) for col in cols]
    # Einheitsvector of line
    vec_e=(x/sqrt(x**2+y**2), y/sqrt(x**2+y**2))
    # Vector normal to the line
    vec_n=(vec_e[1], -1*vec_e[0])
    # starting point of cross-section line
    origin=(x_0, y_0)
    first_dim=''
    first_unit=''
    if x!=0:
      first_dim+='%g %s' % (x, new_cols[0][0])
      if y==0:
        first_unit=new_cols[0][1]
    if x!=0 and y!=0:
      if y>0:
        first_dim+=' + '
      if new_cols[0][1]==new_cols[1][1]:
        first_unit=new_cols[0][1]
      else:
        first_unit="Unknown"
    if y!=0:
      first_dim+='%g %s' % (y, new_cols[1][0])
      if x==0:
        first_unit=new_cols[1][1]
    new_cols=[(first_dim, first_unit)]+new_cols
    output=MeasurementData(new_cols, 
                           [], 
                           0, 
                           3, 
                           4,
                           )
    def point_filter(point):
      '''
        Test if point lies in the region expressed by origin, vec_n and w (width).
        
        @return Boolean
      '''
      v1=(point[0]-origin[0], point[1]-origin[1])
      dist=abs(v1[0]*vec_n[0] + v1[1]*vec_n[1])
      return (dist<=w)
    data2=filter(point_filter, data)
    if len(data2)==0:
      return None
    len_vec=sqrt(x**2+y**2)
    data3=[((vec_e[0]*dat[0]+vec_e[1]*dat[1])*len_vec, dat[0], dat[1], dat[2], dat[3]) for dat in data2]
    data3.sort()
    if binning > 1:
      dat_tmp=[]
      for i in range(len(data3)/binning):
        dout=[]
        din=data3[i*binning:(i+1)*binning]
        for j in range(4):
          dout.append(sum([d[j] for d in din])/binning)
        dout.append(sqrt(sum([d[4]**2 for d in din]))/binning)
        dat_tmp.append(dout)
      data3=dat_tmp
    map(output.append, data3)
    return output

  #-------- Functions not directly called as actions ------


class MakroRepr:
  '''
    FileObject implementation to store makros in string representation.
    The class can be used to store general types with ConfigObj.
  '''
  
  string=None #: Stringrepresentation of the data.
  
  def __init__(self):
    '''
      Constructor creates an empty string.
    '''
    self.string=''
  
  def write(self, string):
    '''
      As the write method from files this adds the input to it's own string.
    '''
    self.string+=string
  
  def writelines(self, list_lines):
    '''
      Simulate writelines, see write.
    '''
    self.string+=''.join(list_lines)
  
  def read(self):
    '''
      Simulate read from file object.
    '''
    return self.string
  
  def close(self):
    '''
      Dummifunction to complete file object possibilities.
    '''
    pass
  
  def readline(self):
    '''
      Simulate readline, see read.
    '''
    splt=self.string.splitlines()
    for line in splt:
      yield line
  
  def readlines(self):
    '''
      Simulate readlines, see read.
    '''
    return self.string.splitlines()
  
  def flush(self):
    '''
      Dummifunction to complete file object possibilities.
    '''
    pass
  
  def seek(self):
    '''
      Dummifunction to complete file object possibilities.
    '''
    pass
  
  def tell(self):
    '''
      Dummifunction to complete file object possibilities.
    '''
    return 0
  
  def next(self):
    '''
      Dummifunction to complete file object possibilities.
    '''
    return self
  
  def __str__(self):
    '''
      String representation for the makro.
    '''
    out=self.string.splitlines()
    def getlines(item):
      return item.split('=', 1)[1]
    out=map(getlines, out)
    return '\n'.join(out)
  
  def from_string(self, string):
    '''
      Recreate makro from string representation.
    '''
    lines=string.splitlines()
    new_lines=[]
    for i, line in enumerate(lines):
      new_lines.append("%i = %s" % (i, line))
    self.string='\n'.join(new_lines)
