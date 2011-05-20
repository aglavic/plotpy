# -*- encoding: utf-8 -*-
'''
   Module for data treatment and macro processing.
'''

import numpy
from configobj import ConfigObj
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.6.1"
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
    self.init_fit_functions()
    # action functions that can be executed from activate_action,
    # can be altered in runtime by the specific sessions
    self.actions={
                  'change filter': self.change_data_filter, 
                  'cross-section': self.cross_section, 
                  'radial_integration': self.radial_integration, 
                  'combine-data': self.combine_data_points, 
                  'iterate_through_measurements': self.iterate_through_measurements, 
                  'create_fit_object': self.create_fit_object, 
                  'add_function': self.fit_functions['add'], 
                  'sum_up_functions': self.fit_functions['sum'], 
                  'set_function_parameters': self.fit_functions['set_parameters'], 
                  'fit_functions': self.fit_functions['fit'], 
                  'simmulate_functions': self.fit_functions['simulate'], 
                  'change_color_pattern': self.change_color_pattern, 
                  'unit_transformations': self.unit_transformations, 
                  'integrate_intensities': self.integrate_intensities, 
                  'savitzky_golay': self.get_savitzky_golay, 
                  }
    # add session specific functions
    for key, item in window.active_session.file_actions_addon.items():
      self.actions[key]=lambda *args: item(self, *args)

  def init_fit_functions(self):
    fit_functions={
                 "add": lambda *args: \
                  self.window.measurement[self.window.index_mess].fit_object.add_function(*args), 
                 "sum": lambda *args: \
                  self.window.measurement[self.window.index_mess].fit_object.sum(*args), 
                 "set_parameters": lambda *args: \
                  self.window.measurement[self.window.index_mess].fit_object.set_function_parameters(*args), 
                 "fit": lambda *args:  \
                  self.window.measurement[self.window.index_mess].fit_object.fit(*args), 
                 "simulate": lambda *args: \
                  self.window.measurement[self.window.index_mess].fit_object.simulate(*args), 
                 
                 }
    self.fit_functions=fit_functions

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

  def radial_integration(self, x_0, y_0, dr, max_r, at_end=False):
    '''
      Create a radial integration around one point of a dataset
      
      @param x_0 Center point x position
      @param y_0 Center point y position
      @param dr  Step width in radius
      @param max_r Maximal radius to integrate to
      
      @return If the extraction has been sucessful
    '''
    data=self.window.measurement[self.window.index_mess]
    try:
      cs_object=self.create_radial_integration(x_0, y_0, dr, max_r)
      if cs_object is None:
        return False
      cs_object.number=data.number
      cs_object.short_info='%s - Radial integration around (%g,%g)' % (
                           data.short_info, x_0, y_0) 
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

  def get_savitzky_golay(self, window_size, order, max_deriv, at_end=False):
    '''
      See calculate_savitzky_golay.
    '''
    data=self.window.measurement[self.window.index_mess]
    sg_object=self.calculate_savitzky_golay(data, window_size, order, max_deriv)
    if sg_object is None:
      return False
    sg_object.number=data.number
    sg_object.info=data.info
    if at_end:
      self.window.measurement.append(sg_object)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, sg_object)
      self.window.index_mess+=1
    return True


  def combine_data_points(self, binning, bin_distance=None):
    '''
      Combine points of a line scan to decrease their errors.
    '''
    dataset=self.window.measurement[self.window.index_mess]
    data=dataset.list_err()
    dims=dataset.dimensions()
    units=dataset.units()
    cols=(dataset.xdata, dataset.ydata, dataset.yerror)
    new_cols=[(dims[col], units[col]) for col in cols]
    output=MeasurementData(new_cols, 
                           [], 
                           0, 
                           1, 
                           2,
                           )
    def prepare_data(point):
      return [point[0], point[0], point[0], point[1], point[2], 0]
    def rebuild_data(point):
      return [point[0], point[3], point[4]]
    data2=map(prepare_data, data)
    data3=self.sort_and_bin(data2, binning, bin_distance=bin_distance)
    data3=map(rebuild_data, data3)
    map(output.append, data3)
    output.number=dataset.number
    if not bin_distance:
      output.short_info='%s - combined data points with %i binning' % (
                           dataset.short_info, binning) 
    else:
      output.short_info='%s - combined data points every %g step' % (
                     dataset.short_info, bin_distance) 
    output.sample_name=dataset.sample_name
    output.info=dataset.info
#    if at_end:
#      self.window.measurement.append(cs_object)
#      self.window.index_mess=len(self.window.measurement)-1
#    else:
    self.window.measurement.insert(self.window.index_mess+1, output)
    self.window.index_mess+=1

  def iterate_through_measurements(self, action_name):
    '''
      Change the active plotted sequence.
    '''
    if action_name=='Prev':
      self.window.index_mess=max(0,self.window.index_mess-1)
      self.window.plot_page_entry.SetValue(str(self.window.index_mess))
    elif action_name=='First':
      self.window.index_mess=0
      self.window.plot_page_entry.SetValue(str(self.window.index_mess))
    elif action_name=='Last':
      self.window.index_mess=len(self.window.measurement)-1
      self.window.plot_page_entry.SetValue(str(self.window.index_mess))
    elif action_name=='Next':
      self.window.index_mess=min(len(self.window.measurement)-1,self.window.index_mess+1)
      self.window.plot_page_entry.SetValue(str(self.window.index_mess))
    else:
      try:
        if len(self.window.measurement)>int(self.window.plot_page_entry.GetValue()):
          self.window.index_mess=int(self.window.plot_page_entry.GetValue())
      except ValueError:
        self.window.plot_page_entry.SetValue(str(self.window.index_mess))        

  def create_fit_object(self):
    '''
      Creates an FitSession object for data fitting and
      binds it to the active dataset.
    '''
    dataset=self.window.measurement[self.window.index_mess]
    from fit_data import FitSession
    dataset.fit_object=FitSession(dataset)
  
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

  def integrate_intensities(self, x_pos, y_pos, radius, destination_dimension, destination_unit, 
                           dataset_indices, dataset_destination_values):
    '''
      Integrate the intensities of differt datasets around the position (x_pos, y_pos) up to a distance radius.
      
      @param x_pos X-position of the reflex to be integrated
      @param y_pos Y-position of the reflex to be integrated
      @param radius Maximal distance from (x_pos,y_pos) to which points are included
      @param destination_dimension The dimension of the values in x to which the integrated points should be assigned to
      @param destination_unit The unit of the values in x to which the integrated points should be assigned to
      @param dataset_indices a list of ('name', i) to define the datasets to be integrated
      @param dataset_destination_values The x value of all datasets from dataset_indices
    '''
    file_data=self.window.active_session.file_data
    integrated_values=[]
    y_dimunit=None
    error_dimunit=None
    # collect informations of the datasets which will be included in the calculations
    # after that the integrated intensities are calculated and collected
    for dataset_index in dataset_indices:
      if dataset_index[0] not in file_data or \
         len(file_data[dataset_index[0]])<dataset_index[1]:
        raise IndexError, "%s[%i] not in list" % (dataset_index[0], dataset_index[1])
      dataset=file_data[dataset_index[0]][dataset_index[1]]
      if not y_dimunit:
        y_dimunit=( dataset.dimensions()[dataset.zdata],
                    dataset.units()[dataset.zdata] )
        error_dimunit=( dataset.dimensions()[dataset.yerror],
                    dataset.units()[dataset.yerror] )
        info_data=(dataset.dimensions()[dataset.xdata],
                   x_pos,
                   dataset.dimensions()[dataset.ydata],
                   y_pos,
                   )
      integrated_values.append(self.integrate_around_point(x_pos, y_pos, radius, dataset))
    # add the data to a MeasurementData object
    integrated_object=MeasurementData([(destination_dimension, destination_unit), y_dimunit, error_dimunit], 
                                        [],0,1,2)
    for i, item in enumerate(integrated_values):
      integrated_object.append([dataset_destination_values[i], item[0], item[1]])
    integrated_object.short_info='(%s=%.2g, %s=%.2g) ' % info_data
    integrated_object.sample_name="Integrated intensity vs. %s" % str(destination_dimension)
    # paste the object in the active session
    if "Integrated intensities" in file_data:
      integrated_object.number=str(len(file_data["Integrated intensities"]))
      file_data["Integrated intensities"].append(integrated_object)
    else:
      integrated_object.number='0'
      file_data["Integrated intensities"]=[integrated_object]
    self.window.measurement=file_data["Integrated intensities"]
    self.window.index_mess=len(file_data["Integrated intensities"])-1
    self.window.active_session.active_file_data=file_data["Integrated intensities"]
    self.window.active_session.active_file_name="Integrated intensities"
    self.window.rebuild_menus()

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
      if dist<=(w/2.):
        return True
      else:
        return False
    # remove all points not inside the scanned region
    data2=filter(point_filter, data)
    if len(data2)==0:
      return None
    len_vec=sqrt(x**2+y**2)
    data3=[[(vec_e[0]*dat[0]+vec_e[1]*dat[1])*len_vec, dat[0], dat[1], dat[2], dat[3], 
                                          (vec_n[0]*(dat[0]-origin[0])+vec_n[1]*(dat[1]-origin[1]))] for dat in data2]
    data3=self.sort_and_bin(data3, binning,  gauss_weighting, sigma_gauss, bin_distance)
    map(output.append, data3)
    return output
  
  def create_radial_integration(self, x_0, y_0, dr, max_r):
    '''
      Create a radial integration around one point (x_0,y_0)
      
      @param x_0 x-position of the center point
      @param y_0 y-position of the center point
      @param dr Step size in radius for the created plot
      @param max_r Maximal radius to integrate to
    '''
    from numpy import sqrt, array
    dataset=[data.values for data in self.window.measurement[self.window.index_mess].data]
    data=map(array, dataset)
    dims=self.window.measurement[self.window.index_mess].dimensions()
    units=self.window.measurement[self.window.index_mess].units()
    cols=(self.window.measurement[self.window.index_mess].xdata, 
          self.window.measurement[self.window.index_mess].ydata, 
          self.window.measurement[self.window.index_mess].zdata, 
          self.window.measurement[self.window.index_mess].yerror)
    new_cols=[(dims[col], units[col]) for col in cols]
    # Distances to the point
    dist_r=sqrt((data[cols[0]]-x_0)**2+(data[cols[1]]-y_0)**2)
    max_r=min(dist_r.max(), max_r)
    values=data[cols[2]]
    errors=data[cols[3]]
    first_dim="r"
    first_unit=units[cols[0]]
    new_cols=[(first_dim, first_unit), (dims[cols[2]], units[cols[2]]), (dims[cols[3]], units[cols[3]])]
    output=MeasurementData(new_cols, 
                           [], 
                           0, 
                           1, 
                           2,
                           )
    # go from 0 to max_r in dr steps
    for i in range(int(max_r/dr)+1):
      r=i*dr
      x_val=(i+0.5)*dr
      y_vals=[]
      dy_vals=[]
      for i, dist in enumerate(dist_r):
        if dist>=x_val and dist<x_val+dr:
          y_vals.append(values[i])
          dy_vals.append(errors[i])
      if len(y_vals)>0:
        y_val=sum(y_vals)/float(len(y_vals))
        dy_val=sqrt( (array(dy_vals)**2).sum()) /float(len(y_vals))
        output.append( (x_val, y_val, dy_val) )
    if len(output)==0:
      return None
    else:
      return output
  
  def sort_and_bin(self, data, binning, gauss_weighting=False, sigma_gauss=1e10, bin_distance=None):
    '''
      Sort a dataset and bin the datapoints together. Gaussian weighting is possible and
      errors are calculated.
      
      @param data A list of datapoints consisting of (x0, x1, x2, y, dy, weighting)
      
      @return Binned dataset
    '''
    from math import sqrt, exp
    data.sort()
    # Start to bin the datapoints
    dat_tmp=[]
    if gauss_weighting:
      def gauss_sum(data_list):
        output=0.
        for i, dat in enumerate(data_list):
          output+=dat*exp(-din[i][5]**2/(2*sigma_gauss**2))
        return output
    if bin_distance:
      bin_dist_position=int(data[0][0]/bin_distance)
      din=[]
    for i, point in enumerate(data):
      if bin_distance:
        if point[0]<=bin_distance*(bin_dist_position+0.5):
          din.append([bin_dist_position*bin_distance]+point[1:])
        else:
          while point[0]>bin_distance*(bin_dist_position+0.5):
            bin_dist_position+=1
          din=[[bin_dist_position*bin_distance]+point[1:]]
        if (i+1)==len(data) or data[i+1][0]<=bin_distance*(bin_dist_position+0.5):
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
    return dat_tmp
 
  def integrate_around_point(self, x_pos, y_pos, radius, dataset):
    '''
      Integrate the intensities of dataset around the point (x_pos, y_pos) up to
      a distance radius.
      
      @return The average of the integrated values with their errors.
    '''
    from numpy import array, sqrt
    x=array(dataset.data[dataset.xdata].values)
    y=array(dataset.data[dataset.ydata].values)
    z=array(dataset.data[dataset.zdata].values)
    dz=array(dataset.data[dataset.yerror].values)
    distances=sqrt((x-x_pos)**2 + (y-y_pos)**2)
    values=[]
    errors=[]
    for i, dist in enumerate(distances):
      if dist<=radius:
        values.append(z[i])
        errors.append(dz[i])
    if len(values)>0:
      values=array(values)
      errors=array(errors)
      # calculate mean of the values
      value=values.sum() / len(values)
      # calculate the error of the value
      error=sqrt((errors**2).sum()) / len(values)
      return (value, error)
    else:
      return (0., 1.)

  #-------- Functions not directly called as actions ------

  def calculate_savitzky_golay(self, dataset, window_size, order, max_deriv):
    '''
      Calculate smoothed dataset with savitzky golay filter up do a maximal derivative.
      
      @param dataset The dataset to use for the data
      @param window_size Size of the filter window in points
      @param order Order of polynomials to be used for the filtering
      @param max_deriv maximal derivative to be calculated
      
      @return a dataset containing the smoothed data and it's derivatives.
    '''
    if dataset.zdata>=0:
      return None
    units=dataset.units()
    dims=dataset.dimensions()
    xindex=dataset.xdata
    yindex=dataset.ydata
    yerror=dataset.yerror
    newcols=[[dims[xindex], units[xindex]], [dims[yerror], units[yerror]], 
                                ['smoothed '+dims[yindex], units[yindex]]
                                                         ]
    max_deriv=min(order, max_deriv)
    for i in range(1, max_deriv):
      if i>1:
        newcols.append([dims[yindex]+("\\047"*i), units[yindex]+'/'+units[xindex]+'^%i'%i])
      else:
        newcols.append([dims[yindex]+"\\047", units[yindex]+'/'+units[xindex]])
    output=MeasurementData(newcols, [], 0, 2, 1)
    xlist=[]
    ylist=[]
    elist=[]
    # get only points which are not filtered
    for point in dataset:
      xlist.append(point[xindex])
      ylist.append(point[yindex])
      elist.append(point[yerror])
    x=numpy.array(xlist)
    y=numpy.array(ylist)
    error=numpy.array(elist)
    output.data[0].values=xlist
    output.data[1].values=elist
    # calculate smoothed data and derivatives
    for i in range(max_deriv):
      output.data[i+2].values=savitzky_golay(y, window_size, order, i).tolist()
    output.short_info=dataset.short_info+' filtered with savitzky golay'
    output.sample_name=dataset.sample_name
    return output


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
    if self.string.strip()=="":
      return ""
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

def savitzky_golay(y, window_size, order, deriv=0):
  '''
    Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techhniques.

    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688


    @param y the values of the time history of the signal (array)
    @param window_size the length of the window, must be an odd integer number.
    @param order the order of the polynomial used in the filtering, must be less then `window_size` - 1.
    @param deriv the order of the derivative to compute (default = 0 means only smoothing)
    
    @return ys the smoothed signal (or it's n-th derivative).

  '''
  np=numpy
  try:
      window_size = np.abs(np.int(window_size))
      order = np.abs(np.int(order))
  except ValueError, msg:
      raise ValueError("window_size and order have to be of type int")
  if window_size % 2 != 1:
    window_size-=1
  if window_size < 1:
      raise TypeError("window_size size must be a positive odd number")
  if window_size < order + 2:
      raise TypeError("window_size is too small for the polynomials order")
  order_range = range(order+1)
  half_window = (window_size -1) // 2
  # precompute coefficients
  b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
  m = np.linalg.pinv(b).A[deriv]
  # pad the signal at the extremes with
  # values taken from the signal itself
  firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
  lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
  y = np.concatenate((firstvals, y, lastvals))
  return np.convolve( m, y, mode='valid')
