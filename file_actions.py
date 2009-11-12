#!/usr/bin/env python
'''
   Module for data treatment and macro processing.
'''

from configobj import ConfigObj
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6b4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

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
    # action functions that can be executed from activate_action,
    # can be altered in runtime by the specific sessions
    self.actions={
                  'change filter': self.change_data_filter, 
                  'cross-section': self.cross_section, 
                  'iterate_through_measurements': self.iterate_through_measurements, 
                  'create_fit_object': self.create_fit_object, 
                  'change_color_pattern': self.change_color_pattern, 
                  'unit_transformations': self.unit_transformations, 
                  }
    # add session specific functions
    for key, item in window.active_session.file_actions_addon.items():
      self.actions[key]=lambda *args: item(self, *args)

  def activate_action(self, action, *args):
    '''
      Every action performed by this class is stored so
      it can be shown in a log or reused in makros for other sequences.
      
      @param action The function to be called
      @param *args The arguments of that function
      
      @return Return values of the called function
    '''
    # Store the function name and parameters 
    self.history.append((action, args))
    return self.actions[action](*args)
  
  def reactivate_action(self, action):
    '''
      Run an action without storing it in the history.
      Used when running a makro.
      
      @param action Function and parameters to use.
      
      @return Return values of the funciton
    '''
    return self.actions[action[0]](*action[1])

  def store(self, from_index=None, to_index=None):
    '''
      Store a subset of the history actions as a MakroRepr object.
      
      @return The MakroRepr object
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

  def cross_section(self, x, x_0, y, y_0, w, binning, gauss_weighting=False, sigma_gauss=1e10, at_end=False, bin_distance=None):
    '''
      Create a slice through a dataset using the create_cross_section function.
      This funcion is called as the action.
      
      @param binning Number of points to take a mean value of
      @param gauss_weighting If mean value of points is calculated the points are weighted by the distance to the crossection line
      @param sigma_gauss Sigma value of the gauss function used for weighting the points
      @param at_end Put the created picture at the end of the plot list, not after the picture it was created from
      @param bin_distance Use a specific distance window for binning, not a fix number of points
      
      @return If the extraction has been sucessful
    '''
    data=self.window.measurement[self.window.index_mess]
    try:
      cs_object=self.create_cross_section(x, x_0, y, y_0, w, binning, gauss_weighting, sigma_gauss, bin_distance)
      if cs_object is None:
        return False
      cs_object.number=data.number
      cs_object.short_info='%s - Cross-Section through (%g,%g)+x*(%g,%g)' % (
                           data.short_info, x_0, y_0, x,y) 
      cs_object.sample_name=data.sample_name
      cs_object.info=data.info
      if at_end:
        self.window.measurement.append(cs_object)
        self.window.index_mess=len(self.window.measurement)-1
      else:
        self.window.measurement.insert(self.window.index_mess+1, cs_object)
        self.window.index_mess+=1
      return True
    except ValueError:
      return False
  
  def iterate_through_measurements(self, action_name):
    '''
      Change the active plotted sequence.
    '''
    if action_name=='Prev':
      self.window.index_mess=max(0,self.window.index_mess-1)
      self.window.plot_page_entry.set_text(str(self.window.index_mess))
    elif action_name=='First':
      self.window.index_mess=0
      self.window.plot_page_entry.set_text(str(self.window.index_mess))
    elif action_name=='Last':
      self.window.index_mess=len(self.window.measurement)-1
      self.window.plot_page_entry.set_text(str(self.window.index_mess))
    elif action_name=='Next':
      self.window.index_mess=min(len(self.window.measurement)-1,self.window.index_mess+1)
      self.window.plot_page_entry.set_text(str(self.window.index_mess))
    else:
      try:
        if len(self.window.measurement)>int(self.window.plot_page_entry.get_text()):
          self.window.index_mess=int(self.window.plot_page_entry.get_text())
      except ValueError:
        self.window.plot_page_entry.set_text(str(self.window.index_mess))        

  def create_fit_object(self):
    '''
      Creates an FitSession object for data fitting and
      binds it to the active dataset.
    '''
    dataset=self.window.measurement[self.window.index_mess]
    from fit_data import FitSession
    dataset.fit_object=FitSession(dataset, self)
  
  def change_color_pattern(self, pattern):
    '''
      Change the color palette used in pm3d plots.
      
      @param pattern pattern The string used for the palette in gnuplot
    '''
    import config.gnuplot_preferences as gnuplot_preferences
    options_list_3d=gnuplot_preferences.settings_3d.splitlines()
    options_list_3dmap=gnuplot_preferences.settings_3dmap.splitlines()
    for line in reversed(options_list_3d):
      if 'palette' in line:
        options_list_3d.remove(line)
    options_list_3d.append('set palette ' + pattern)
    for line in reversed(options_list_3dmap):
      if 'palette' in line:
        options_list_3dmap.remove(line)
    options_list_3dmap.append('set palette ' + pattern)
    gnuplot_preferences.settings_3d="\n".join(options_list_3d) + "\n"
    gnuplot_preferences.settings_3dmap="\n".join(options_list_3dmap) + "\n"
    
  def unit_transformations(self, transformations):
    '''
      Make a unit transformation with the active dataset.
      
      @param transformations A sequence of the transformation settings
    '''
    dataset=self.window.measurement[self.window.index_mess]
    dataset.unit_trans(transformations)

  #----------- The performable actions --------------------


  #++++++++ Functions not directly called as actions ++++++
  
  def create_cross_section(self, x, x_0, y, y_0, w, binning, gauss_weighting=False, sigma_gauss=1e10, bin_distance=None):
    '''
      Create a cross-section of 3d-data along an arbitrary line. It is possible to
      bin the extracted data and to weight the binning with a gaussian.
    '''
    from math import sqrt, exp
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
    new_cols=[(first_dim, first_unit)]+new_cols+[('distance', first_unit)]
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
      if dist<=w:
        return True
      else:
        return False
    # remove all points not inside the scanned region
    data2=filter(point_filter, data)
    if len(data2)==0:
      return None
    len_vec=sqrt(x**2+y**2)
    data3=[[(vec_e[0]*dat[0]+vec_e[1]*dat[1])*len_vec, dat[0], dat[1], dat[2], dat[3], (vec_n[0]*dat[0]+vec_n[1]*dat[1])] for dat in data2]
    data3.sort()
    # Start to bin the datapoints
    dat_tmp=[]
    if gauss_weighting:
      def gauss_sum(data_list):
        output=0.
        for i, dat in enumerate(data_list):
          output+=dat*exp(-din[i][5]**2/(2*sigma_gauss**2))
        return output
    if bin_distance:
      bin_dist_position=int(data3[0][0]/bin_distance)
      din=[]
    for i, point in enumerate(data3):
      if bin_distance:
        if point[0]<=bin_distance*(bin_dist_position+0.5):
          din.append([bin_dist_position*bin_distance]+point[1:])
        else:
          while point[0]>bin_distance*(bin_dist_position+0.5):
            bin_dist_position+=1
          din=[[bin_dist_position*bin_distance]+point[1:]]
        if (i+1)==len(data3) or data3[i+1][0]<=bin_distance*(bin_dist_position+0.5):
          continue
      else:
        if i%binning==0:
          din=[point]
        else:
          din.append(point)
        if (i+1)%binning!=0:
          continue
      # Create the mean value of the collected points
      dout=[]
      if gauss_weighting:
        g_sum=gauss_sum([1 for d in din])
        for j in range(4):
          dout.append(gauss_sum([d[j] for d in din])/g_sum)
        dout.append(sqrt(gauss_sum([d[4]**2 for d in din]))/g_sum)
        dout.append(g_sum/len(din))          
      else:
        for j in range(4):
          dout.append(sum([d[j] for d in din])/len(din))
        dout.append(sqrt(sum([d[4]**2 for d in din]))/len(din))
        dout.append(sum([d[5] for d in din])/len(din))
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
