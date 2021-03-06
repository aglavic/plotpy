# -*- encoding: utf-8 -*-
'''
   Module for data treatment and macro processing.
'''

import numpy
from copy import deepcopy
from configobj import ConfigObj
from plot_script.measurement_data_structure import MeasurementData, \
                          PhysicalProperty, PhysicalUnit, HugeMD

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class FileActions:
  '''
    A Class designed to preform simple operations on one dataset and
    to store those in a history for later macro processing.
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
                  'multiply_functions': self.fit_functions['mul'],
                  'add_gaussian_resolution': self.fit_functions['res'],
                  'set_function_parameters': self.fit_functions['set_parameters'],
                  'fit_functions': self.fit_functions['fit'],
                  'simmulate_functions': self.fit_functions['simulate'],
                  'change_color_pattern': self.change_color_pattern,
                  'unit_transformations': self.unit_transformations,
                  'integrate_intensities': self.integrate_intensities,
                  'savitzky_golay': self.get_savitzky_golay,
                  'butterworth': self.get_butterworth,
                  'discrete_derivative': self.get_discrete_derivative,
                  'integral': self.get_integral,
                  'interpolate_and_smooth': self.do_interpolate_and_smooth,
                  'rebin_2d': self.do_rebin_2d,
                  }
    # add session specific functions
    for key, item in window.active_session.file_actions_addon.items():
      self.actions[key]=lambda*args: item(self, *args)

  def init_fit_functions(self):
    fit_functions={
                 "add": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.add_function(*args),
                 "sum": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.sum(*args),
                 "mul": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.multiply(*args),
                 "res": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.resolution(*args),
                 "set_parameters": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.set_function_parameters(*args),
                 "fit": lambda*args:  \
                  self.window.measurement[self.window.index_mess].fit_object.fit(*args),
                 "simulate": lambda*args: \
                  self.window.measurement[self.window.index_mess].fit_object.simulate(*args),

                 }
    self.fit_functions=fit_functions

  def activate_action(self, action, *args):
    '''
      Every action performed by this class is stored so
      it can be shown in a log or reused in makros for other sequences.
      
      :param action: The function to be called
      :param args: The arguments of that function
      
      :return: Return values of the called function
    '''
    # Store the function name and parameters 
    self.history.append((action, args))
    return self.actions[action](*args)

  def reactivate_action(self, action):
    '''
      Run an action without storing it in the history.
      Used when running a makro.
      
      :param action: Function and parameters to use.
      
      :return: Return values of the funciton
    '''
    return self.actions[action[0]](*action[1])

  def store(self, from_index=None, to_index=None):
    '''
      Store a subset of the history actions as a MakroRepr object.
      
      :return: The MakroRepr object
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

  def cross_section(self, x, x_0, y, y_0, w, binning,
                    gauss_weighting=False, sigma_gauss=1e10,
                    at_end=False, bin_distance=None):
    '''
      Create a slice through a dataset using the create_cross_section function.
      This funcion is called as the action.
      
      :param binning: Number of points to take a mean value of
      :param gauss_weighting: If mean value of points is calculated the points are weighted by the distance to the crossection line
      :param sigma_gauss: Sigma value of the gauss function used for weighting the points
      :param at_end: Put the created picture at the end of the plot list, not after the picture it was created from
      :param bin_distance: Use a specific distance window for binning, not a fix number of points
      
      :return: If the extraction has been sucessful
    '''
    dataset=self.window.measurement[self.window.index_mess]
    cs_object=self.create_cross_section(x, x_0, y, y_0, w, binning,
                                        gauss_weighting, sigma_gauss,
                                        bin_distance)
    try:
      if cs_object is None:
        return False
      cs_object.number=dataset.number
      cs_object.short_info='%s - Cross-Section through (%g,%g)+x*(%g,%g)'%(
                           dataset.short_info, x_0, y_0, x, y)
      cs_object.sample_name=dataset.sample_name
      cs_object.info=dataset.info
      if at_end:
        self.window.measurement.append(cs_object)
        self.window.index_mess=len(self.window.measurement)-1
      else:
        self.window.measurement.insert(self.window.index_mess+1, cs_object)
        self.window.index_mess+=1
      return True
    except ValueError:
      return False

  def radial_integration(self, x_0, y_0, dr, max_r,
                                  phi_0=0., dphi=180., symmetric=True,
                                  at_end=False):
    '''
      Create a radial integration around one point of a dataset
      
      :param x_0: Center point x position
      :param y_0: Center point y position
      :param dr: Step width in radius
      :param max_r: Maximal radius to integrate to
      
      :return: If the extraction has been sucessful
    '''
    data=self.window.measurement[self.window.index_mess]
    try:
      cs_object=self.create_radial_integration(x_0, y_0, dr, max_r,
                                               phi_0, dphi, symmetric)
      if cs_object is None:
        return False
      cs_object.number=data.number
      if dphi<180.:
        cs_object.short_info='%s - Arc integration with φ=%g±%g° from (%g,%g)'%(
                           data.short_info, phi_0, dphi,
                           x_0, y_0)
      else:
        cs_object.short_info='%s - Radial integration around (%g,%g)'%(
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

  def get_savitzky_golay(self, window_size=5, order=4, derivative=1, at_end=False):
    '''
      See calculate_savitzky_golay.
    '''
    data=self.window.measurement[self.window.index_mess]
    sg_object=calculate_savitzky_golay(data, window_size, order, derivative)
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

  def get_butterworth(self, filter_steepness=6, filter_cutoff=0.5, derivative=1, at_end=False):
    '''
      See calculate_butterworth.
    '''
    data=self.window.measurement[self.window.index_mess]
    bw_object=calculate_butterworth(data, filter_steepness, filter_cutoff, derivative)
    if bw_object is None:
      return False
    bw_object.number=data.number
    bw_object.info=data.info
    if at_end:
      self.window.measurement.append(bw_object)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, bw_object)
      self.window.index_mess+=1
    return True

  def get_discrete_derivative(self, at_end=False):
    '''
      See calculate_discrete_derivative.
    '''
    data=self.window.measurement[self.window.index_mess]
    deriv_object=calculate_discrete_derivative(data, 5.)
    deriv_object.number=data.number
    deriv_object.info=data.info
    if at_end:
      self.window.measurement.append(deriv_object)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, deriv_object)
      self.window.index_mess+=1
    return True

  def get_integral(self, at_end=False):
    '''
      See calculate_integral.
    '''
    data=self.window.measurement[self.window.index_mess]
    int_object=calculate_integral(data)
    int_object.number=data.number
    int_object.info=data.info
    if at_end:
      self.window.measurement.append(int_object)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, int_object)
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
    cols=(dataset.xdata, dataset.ydata)
    new_cols=[(dims[col], units[col]) for col in cols]
    output=MeasurementData(new_cols,
                           [],
                           0,
                           1,
                           -1,
                           )
    def prepare_data(point):
      return [point[0], point[0], point[0], point[1], point[2], 0]
    data2=map(prepare_data, data)
    data3=self.sort_and_bin(data2, binning, bin_distance=bin_distance)
    x, y, dy=numpy.array(data3).transpose()[numpy.array([0, 3, 4])]
    x=PhysicalProperty(dataset.x.dimension, dataset.x.unit, x)
    y=PhysicalProperty(dataset.y.dimension, dataset.y.unit, y)
    if dataset.yerror>=0:
      y.error=dy
    output.data=[x, y]
    output.number=dataset.number
    output.logx=dataset.logx
    output.logy=dataset.logy
    if not bin_distance:
      output.short_info='%s - combined data points with %i binning'%(
                           dataset.short_info, binning)
    else:
      output.short_info='%s - combined data points every %g step'%(
                     dataset.short_info, bin_distance)
    output.sample_name=dataset.sample_name
    output.info=dataset.info
    self.window.measurement.insert(self.window.index_mess+1, output)
    self.window.index_mess+=1

  def iterate_through_measurements(self, action_name):
    '''
      Change the active plotted sequence.
    '''
    if self.window.active_multiplot:
      mp=self.window.multiplot
      if action_name=='Prev':
        mp.select_item(max(0, mp.item_index-1))
      elif action_name=='First':
        mp.select_item(0)
      elif action_name=='Last':
        mp.select_item(-1)
      elif action_name=='Next':
        mp.select_item(min(len(mp.multiplots)-1, mp.item_index+1))
      else:
        try:
          if len(mp.multiplots)>int(self.window.plot_page_entry.get_text()) and\
            int(self.window.plot_page_entry.get_text())>=0:
            mp.select_item(int(self.window.plot_page_entry.get_text()))
        except ValueError:
          pass
      self.window.plot_page_entry.set_text(str(mp.item_index))
    else:
      if action_name=='Prev':
        self.window.index_mess=max(0, self.window.index_mess-1)
      elif action_name=='First':
        self.window.index_mess=0
      elif action_name=='Last':
        self.window.index_mess=len(self.window.measurement)-1
      elif action_name=='Next':
        self.window.index_mess=min(len(self.window.measurement)-1,
                                   self.window.index_mess+1)
      elif action_name=='Up':
        self.window.index_mess=0
        session=self.window.active_session
        dsname=session.active_file_name
        names=session.file_data.keys()
        names.sort()
        index=names.index(dsname)
        if index>0:
          index-=1
        else:
          index=len(names)-1
        new_name=names[index]
        session.active_file_data=session.file_data[new_name]
        session.active_file_name=new_name
        self.window.measurement=session.active_file_data
        self.window.input_file_name=new_name
      elif action_name=='Down':
        self.window.index_mess=0
        session=self.window.active_session
        dsname=session.active_file_name
        names=session.file_data.keys()
        names.sort()
        index=names.index(dsname)
        if index<(len(names)-1):
          index+=1
        else:
          index=0
        new_name=names[index]
        session.active_file_data=session.file_data[new_name]
        session.active_file_name=new_name
        self.window.measurement=session.active_file_data
        self.window.input_file_name=new_name
      else:
        try:
          if len(self.window.measurement)>int(self.window.plot_page_entry.get_text()):
            self.window.index_mess=int(self.window.plot_page_entry.get_text())
        except ValueError:
          pass
      self.window.plot_page_entry.set_text(str(self.window.index_mess))
      if self.window.label_arrow_dialog is not None:
        self.window.label_arrow_dialog.change_dataset(self.window.active_dataset)

  def create_fit_object(self):
    '''
      Creates an FitSession object for data fitting and
      binds it to the active dataset.
    '''
    dataset=self.window.measurement[self.window.index_mess]
    from plot_script.fit_data import FitSession
    dataset.fit_object=FitSession(dataset)

  def change_color_pattern(self, pattern):
    '''
      Change the color palette used in pm3d plots.
      
      :param pattern: pattern The string used for the palette in gnuplot
    '''
    import plot_script.config.gnuplot_preferences as gnuplot_preferences
    options_list_3d=gnuplot_preferences.settings_3d.splitlines()
    options_list_3dmap=gnuplot_preferences.settings_3dmap.splitlines()
    for line in reversed(options_list_3d):
      if 'palette' in line:
        options_list_3d.remove(line)
    options_list_3d.append('set palette '+pattern)
    for line in reversed(options_list_3dmap):
      if 'palette' in line:
        options_list_3dmap.remove(line)
    options_list_3dmap.append('set palette '+pattern)
    gnuplot_preferences.settings_3d="\n".join(options_list_3d)+"\n"
    gnuplot_preferences.settings_3dmap="\n".join(options_list_3dmap)+"\n"

  def unit_transformations(self, transformations):
    '''
      Make a unit transformation with the active dataset.
      
      :param transformations: A sequence of the transformation settings
    '''
    dataset=self.window.measurement[self.window.index_mess]
    dataset.unit_trans(transformations)

  def integrate_intensities(self, x_pos, y_pos, radius, destination_dimension, destination_unit,
                           dataset_indices, dataset_destination_values):
    '''
      Integrate the intensities of differt datasets around the position (x_pos, y_pos) up to a distance radius.
      
      :param x_pos: X-position of the reflex to be integrated
      :param y_pos: Y-position of the reflex to be integrated
      :param radius: Maximal distance from (x_pos,y_pos) to which points are included
      :param destination_dimension: The dimension of the values in x to which the integrated points should be assigned to
      :param destination_unit: The unit of the values in x to which the integrated points should be assigned to
      :param dataset_indices: a list of ('name', i) to define the datasets to be integrated
      :param dataset_destination_values: The x value of all datasets from dataset_indices
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
        raise IndexError, "%s[%i] not in list"%(dataset_index[0], dataset_index[1])
      dataset=file_data[dataset_index[0]][dataset_index[1]]
      if not y_dimunit:
        y_dimunit=(dataset.dimensions()[dataset.zdata],
                    dataset.units()[dataset.zdata])
        error_dimunit=(dataset.dimensions()[dataset.yerror],
                    dataset.units()[dataset.yerror])
        info_data=(dataset.dimensions()[dataset.xdata],
                   x_pos,
                   dataset.dimensions()[dataset.ydata],
                   y_pos,
                   )
      integrated_values.append(self.integrate_around_point(x_pos, y_pos, radius, dataset))
    # add the data to a MeasurementData object
    integrated_object=MeasurementData([(destination_dimension, destination_unit), y_dimunit, error_dimunit],
                                        [], 0, 1, 2)
    for i, item in enumerate(integrated_values):
      integrated_object.append([dataset_destination_values[i], item[0], item[1]])
    integrated_object.short_info='(%s=%.2g, %s=%.2g) '%info_data
    integrated_object.sample_name="Integrated intensity vs. %s"%str(destination_dimension)
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


  def do_interpolate_and_smooth(self, sigma_x, sigma_y, xfrom, xto, xsteps, yfrom, yto, ysteps, do_append=True):
    '''
      Interpolate the active dataset to a regular grid including smoothing using given parameters.
    '''
    # If no step numbers are given use sigma as step width
    if xsteps is None:
      xsteps=(xto-xfrom)/(sigma_x)
    if ysteps is None:
      ysteps=(yto-yfrom)/(sigma_y)
    dataset=self.window.measurement[self.window.index_mess]
    grid_x=numpy.linspace(xfrom, xto, xsteps)
    grid_y=numpy.linspace(yfrom, yto, ysteps)
    print "Start interpolation."
    interpolated_dataset=interpolate_and_smooth(dataset, sigma_x, sigma_y, grid_x, grid_y, use_matrix_data_output=False)
    interpolated_dataset.sample_name=dataset.sample_name
    interpolated_dataset.short_info=dataset.short_info+' - interpolated on (%i,%i)-grid'%(xsteps, ysteps)
    interpolated_dataset.plot_options=deepcopy(dataset.plot_options)
    interpolated_dataset.logx=dataset.logx
    interpolated_dataset.logy=dataset.logy
    interpolated_dataset.logz=dataset.logz
    if do_append:
      self.window.measurement.append(interpolated_dataset)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, interpolated_dataset)
      self.window.index_mess+=1

  def do_rebin_2d(self, join_pixels_x, join_pixels_y=None, do_append=True):
    '''
      Interpolate the active dataset to a regular grid 
      including smoothing using given parameters.
    '''
    dataset=self.window.measurement[self.window.index_mess]
    if join_pixels_y is None:
      join_pixels_y=join_pixels_x
    print "Start rebinning."
    rebinned_dataset=rebin_2d(dataset, join_pixels_x, join_pixels_y=join_pixels_y,
                              use_matrix_data_output=getattr(dataset, 'is_matrix_data', False))
    rebinned_dataset.sample_name=dataset.sample_name
    rebinned_dataset.short_info=dataset.short_info+' - rebinned by %i,%i'%(join_pixels_x, join_pixels_y)
    rebinned_dataset.plot_options=deepcopy(dataset.plot_options)
    rebinned_dataset.logx=dataset.logx
    rebinned_dataset.logy=dataset.logy
    rebinned_dataset.logz=dataset.logz
    if do_append:
      self.window.measurement.append(rebinned_dataset)
      self.window.index_mess=len(self.window.measurement)-1
    else:
      self.window.measurement.insert(self.window.index_mess+1, rebinned_dataset)
      self.window.index_mess+=1

  #----------- The performable actions --------------------


  #++++++++ Functions not directly called as actions ++++++

  def create_cross_section(self, x, x_0, y, y_0, w, binning, gauss_weighting=False, sigma_gauss=1e10, bin_distance=None):
    '''
      Create a cross-section of 3d-data along an arbitrary line. It is possible to
      bin the extracted data and to weight the binning with a gaussian.
    '''
    sqrt=numpy.sqrt
    dataset=self.window.measurement[self.window.index_mess]
    xdata=numpy.array(dataset.x)
    ydata=numpy.array(dataset.y)
    zdata=numpy.array(dataset.z)
    if dataset._yerror>=0:
      dzdata=numpy.array(dataset.data[dataset.yerror])
    else:
      dzdata=dataset.z.error
    # Einheitsvector of line
    vec_e=(x/sqrt(x**2+y**2), y/sqrt(x**2+y**2))
    # Vector normal to the line
    vec_n=(vec_e[1],-1*vec_e[0])
    # starting point of cross-section line
    origin=(x_0, y_0)
    # calculate distance to line
    v1=(xdata-origin[0], ydata-origin[1])
    dist=abs(v1[0]*vec_n[0]+v1[1]*vec_n[1])
    # filter by distanc
    filter_indices=numpy.where(dist<=(w/2.))[0]
    xdata=xdata[filter_indices]
    ydata=ydata[filter_indices]
    zdata=zdata[filter_indices]
    if dzdata is not None:
      dzdata=dzdata[filter_indices]
    # sort data for position on the line
    len_vec=sqrt(x**2+y**2)
    dist1=((xdata-x_0)*vec_e[0]+(ydata-y_0)*vec_e[1])*len_vec
    sort_idx=numpy.lexsort(keys=(dist1, ydata, xdata))
    xdata=xdata[sort_idx]
    ydata=ydata[sort_idx]
    zdata=zdata[sort_idx]
    if dzdata is not None:
      dzdata=dzdata[sort_idx]
    dist1=dist1[sort_idx]
    dist=dist[sort_idx]
    if dzdata is not None:
      data=numpy.array([dist1, xdata, ydata, zdata, dzdata, dist]).transpose().tolist()
    else:
      data=numpy.array([dist1, xdata, ydata, zdata, dist]).transpose().tolist()
    data=self.sort_and_bin(data, binning, gauss_weighting,
                           sigma_gauss, bin_distance)
    if len(data)<3:
      # if step size was too big there are not enough data points
      return None
    data=numpy.array(data).transpose()
    out_dataset=MeasurementData()
    out_dataset.yerror=-1
    first_dim=''
    first_unit=''
    if x!=0:
      first_dim+='%g %s'%(x, dataset.x.dimension)
      if y==0:
        first_unit=dataset.x.unit
    if x!=0 and y!=0:
      if y>0:
        first_dim+=' + '
      if dataset.x.unit==dataset.y.unit:
        first_unit=dataset.x.unit
      else:
        first_unit="Unknown"
    if y!=0:
      first_dim+='%g %s'%(y, dataset.y.dimension)
      if x==0:
        first_unit=dataset.y.unit
    out_dataset.append_column(PhysicalProperty(first_dim, first_unit, data[0]))
    if dzdata is not None:
      out_dataset.append_column(PhysicalProperty(dataset.z.dimension, dataset.z.unit, data[3], data[4]))
    else:
      out_dataset.append_column(PhysicalProperty(dataset.z.dimension, dataset.z.unit, data[3]))
    out_dataset.append_column(PhysicalProperty(dataset.x.dimension, dataset.x.unit, data[1]))
    out_dataset.append_column(PhysicalProperty(dataset.y.dimension, dataset.y.unit, data[2]))
    return out_dataset

  def create_radial_integration(self, x_0, y_0, dr, max_r,
                                    phi_0=0., dphi=180., symmetric=True):
    '''
      Create a radial integration around one point (x_0,y_0)
      
      :param x_0: x-position of the center point
      :param y_0: y-position of the center point
      :param dr: Step size in radius for the created plot
      :param max_r: Maximal radius to integrate to
      :param phi: Direction of radian
      :param dphi: Width of arc
      :param symmetric: Join negative and positive directions
    '''
    data=self.window.measurement[self.window.index_mess].get_filtered_data_matrix()
    dims=self.window.measurement[self.window.index_mess].dimensions()
    units=self.window.measurement[self.window.index_mess].units()
    cols=(self.window.measurement[self.window.index_mess].xdata,
          self.window.measurement[self.window.index_mess].ydata,
          self.window.measurement[self.window.index_mess].zdata,
          self.window.measurement[self.window.index_mess].yerror)
    # new_cols=[(dims[col], units[col]) for col in cols]
    # Distances to the point
    r=numpy.sqrt((data[cols[0]]-x_0)**2+(data[cols[1]]-y_0)**2)
    values=data[cols[2]]
    errors=data[cols[3]]
    max_r=min(r.max(), max_r)
    # remove points with too large r value
    rfilter=numpy.where(r<=max_r)
    r=r[rfilter]
    values=values[rfilter]
    errors=errors[rfilter]

    first_dim="r"
    first_unit=units[cols[0]]
    new_cols=[(first_dim, first_unit),
              (dims[cols[2]], units[cols[2]]),
              (dims[cols[3]], units[cols[3]])]
    output=MeasurementData([],
                           [],
                           0,
                           1,
                           -1,
                           )
    # calculate the histogam of points weighted by intensity, error² and 1
    # the result is than calculated as hist(intensity)/hist(1)
    # and sqrt(hist(error²))/hist(1)
    if dphi<180.:
      # take out just one arc region for the integration
      phi=numpy.arctan2(data[cols[1]]-y_0, data[cols[0]]-x_0)/numpy.pi*180.
      phi=phi[rfilter]
      phi_region=numpy.where(((phi-phi_0)%180.)<=dphi)
      r=r[phi_region]
      values=values[phi_region]
      errors=errors[phi_region]
      if not symmetric:
        phi=phi[phi_region]
        r[((phi-phi_0)%360.)>180]*=-1.
    hx=numpy.arange(r.min()-r.min()%dr, r.max()+dr-r.max()%dr, dr)
    hy, ignore=numpy.histogram(r, hx, weights=values)
    hdy, ignore=numpy.histogram(r, hx, weights=errors**2)
    hdy=numpy.sqrt(hdy)
    count, ignore=numpy.histogram(r, hx)
    hy/=count
    hdy/=count
    hx=(hx[:-1]+hx[1:])/2.
    # remove empty bins
    hy=hy[count!=0]
    hdy=hdy[count!=0]
    hx=hx[count!=0]
    output.data.append(PhysicalProperty(new_cols[0][0], new_cols[0][1], hx))
    output.data.append(PhysicalProperty(new_cols[1][0], new_cols[1][1], hy, hdy))
    if self.window.measurement[self.window.index_mess].logz:
      output.logy=True
    if len(output)<3:
      return None
    else:
      return output

  def sort_and_bin(self, data, binning,
                   gauss_weighting=False,
                   sigma_gauss=1e10,
                   bin_distance=None):
    '''
      Sort a dataset and bin the datapoints together. Gaussian weighting is 
      possible and errors are calculated.
      
      :param data: A list of data points consisting of (x0, x1, x2, y, dy, weighting)
      
      :return: Binned dataset
    '''
    from math import sqrt, exp
    data.sort()
    # Start to bin the datapoints
    dat_tmp=[]
    if gauss_weighting:
      def gauss_sum(data_list):
        output=0.
        for i, dat in enumerate(data_list):
          output+=dat*exp(-din[i][-1]**2/(2*sigma_gauss**2))
        return output
    if bin_distance is not None:
      bin_dist_position=int(data[0][0]/bin_distance)
      din=[]
    for i, point in enumerate(data):
      if bin_distance is not None:
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
        if len(din[0])>5:
          dout.append(sqrt(gauss_sum([d[4]**2 for d in din]))/g_sum)
        dout.append(g_sum/len(din))
      else:
        for j in range(4):
          dout.append(sum([d[j] for d in din])/len(din))
        if len(din[0])>5:
          dout.append(sqrt(sum([d[4]**2 for d in din]))/len(din))
        dout.append(sum([d[-1] for d in din])/len(din))
      dat_tmp.append(dout)
    return dat_tmp

  def integrate_around_point(self, x_pos, y_pos, radius, dataset):
    '''
      Integrate the intensities of dataset around the point (x_pos, y_pos) up to
      a distance radius.
      
      :return: The average of the integrated values with their errors.
    '''
    from numpy import sqrt, where, ndarray
    x=dataset.x.view(ndarray)
    y=dataset.y.view(ndarray)
    z=dataset.z.view(ndarray)
    if dataset._yerror>=0:
      dz=dataset.data[dataset.yerror].view(ndarray)
    else:
      dz=dataset.z.error
    distances=sqrt((x-x_pos)**2+(y-y_pos)**2)
    filter_ids=where(distances<=radius)[0]
    if len(filter_ids)>0:
      value=z[filter_ids].mean()
      if dz is not None:
        error=sqrt((dz[filter_ids]**2).sum())/len(filter_ids)
      else:
        error=1.
      return (value, error)
    else:
      return (0., 1.)

def interpolate_and_smooth(dataset, sigma_x, sigma_y, grid_x, grid_y, use_matrix_data_output=False, fill_value=(0., 1.)):
  '''
    Fill a grid with datapoints from another grid, weighting the points with a gaussian up to a distance of
    3*sigma.
    
    :param dataset: MeasurementData object to be used as source_synopsis
    :param sigma_x: Sigma for the gaussian weighting in x direction
    :param sigmy_y: Sigma for the gaussian weighting in y direction
    :param grid_xy: List of (x,y) tuples for the new grid
    
    :return: MeasurementData or HugeMD object with the rebinned data
  '''
  if dataset.zdata<0:
    raise ValueError, 'Dataset needs to be 3 dimensional for interpolation'
  gauss_factor_x=-0.5/sigma_x**2
  gauss_factor_y=-0.5/sigma_y**2
  three_sigma_x=3.*sigma_x
  three_sigma_y=3.*sigma_y
  exp=numpy.exp
  sqrt=numpy.sqrt
  where=numpy.where
  # get the data
  data=dataset.get_filtered_data_matrix()
  x=data[dataset.xdata]
  y=data[dataset.ydata]
  z=data[dataset.zdata]
  z=where(numpy.isinf(z), 0., numpy.nan_to_num(z))
  # interpolate the square of the errors
  if dataset._yerror>=0:
    dzq=data[dataset.yerror]**2
  else:
    dzq=dataset.z.error**2
  dzq=where(numpy.isinf(dzq), numpy.nan_to_num(dzq), 1.)
  #zout=[]
  #dzout=[]
  dims=dataset.dimensions()
  units=dataset.units()
  cols=[(dims[dataset.xdata], units[dataset.xdata]),
        (dims[dataset.ydata], units[dataset.ydata]),
        (dims[dataset.zdata], units[dataset.zdata])]
  if use_matrix_data_output:
    output_data=HugeMD(cols, [], 0, 1,-1, 2)
    output_data.is_matrix_data=True
  else:
    output_data=MeasurementData(cols, [], 0, 1,-1, 2)
  # Go through the new grid point by point and search for datapoints close to the new grid points
  for xi in grid_x:
    distances_x=abs(x-xi)
    indices_x=where(distances_x<three_sigma_x)[0]
    if len(indices_x)==0:
      # fill grid at points not in old grid
      for yi in grid_y:
        output_data.append([xi, yi, (fill_value[0], fill_value[1])])
      continue
    for yi in grid_y:
      distances_y=abs(y[indices_x]-yi)
      sub_indices=where(distances_y<three_sigma_y)[0]
      indices=indices_x[sub_indices]
      if len(indices)==0:
        # fill grid at points not in old grid
        output_data.append([xi, yi, (fill_value[0], fill_value[1])])
        continue
      factors=exp(distances_x[indices]**2*gauss_factor_x+distances_y[sub_indices]**2*gauss_factor_y)
      scale=1./factors.sum()
      zi=(z[indices]*factors).sum()*scale
      dzi=sqrt((dzq[indices]*factors).sum())*scale
      output_data.append([xi, yi, (zi, dzi)])
  return output_data

def rebin_2d(dataset, join_pixels_x, join_pixels_y=None, use_matrix_data_output=False):
  '''
    Rebin data on a regular grid by summing up pixels in x and y direction.
    
    :param dataset: MeasurementData object as source
    :param join_pixels_x: Number of pixels to sum together in x direction
    :param join_pixels_y: Number of pixels to sum together in y direction, if None use x
    
    :return: New MeasurementData object with the rebinned data
  '''
  if join_pixels_y is None:
    join_pixels_y=join_pixels_x
  if dataset.zdata<0:
    raise ValueError, 'Dataset needs to be 3 dimensional for interpolation'
  # get the data
  x=dataset.x
  y=dataset.y
  z=dataset.z
  if dataset._yerror<0:
    if dataset.z.error is None:
      dzq=None
    else:
      dzq=dataset.z.error**2
  else:
    dzq=dataset.data[dataset.yerror]**2
  # create new object
  dims=dataset.dimensions()
  units=dataset.units()
  cols=[(dims[dataset.xdata], units[dataset.xdata]),
        (dims[dataset.ydata], units[dataset.ydata]),
        (dims[dataset.zdata], units[dataset.zdata])]
  if use_matrix_data_output:
    output_data=HugeMD([], [], 0, 1,-1, 2)
    output_data.is_matrix_data=True
  else:
    output_data=MeasurementData(cols, [], 0, 1,-1, 2)
  swapped=False
  try:
    len_x=numpy.where(x==x[0])[0][1]
    if len_x==1:
      tmpy=x
      x=y
      y=tmpy
      tmpy=join_pixels_x
      join_pixels_x=join_pixels_y
      join_pixels_y=tmpy
      len_x=numpy.where(x==x[0])[0][1]
      swapped=True
  except IndexError:
    raise ValueError, "Can only rebin regular grid data"
  if (len(x)%len_x)!=0:
    raise ValueError, "Can only rebin regular grid, no integer number of points for grid width %i found"%len_x
  len_y=len(x)//len_x
  new_len_x=len_x//join_pixels_x
  new_len_y=len_y//join_pixels_y
  # create empty arrays for the new data
  bins, ignore, ignore=numpy.histogram2d(x, y, (new_len_x, new_len_y))
  newz, ignore, ignore=numpy.histogram2d(x, y, (new_len_x, new_len_y),
                                     weights=z)
  newz/=bins
  newz=newz.transpose().flatten()
  if dzq is None:
    newdz=None
  else:
    newdzq, newx, newy=numpy.histogram2d(x, y, (new_len_x, new_len_y),
                                       weights=dzq)
    newdz=numpy.sqrt(newdzq)
    newdz/=bins
    newdz=newdz.transpose().flatten()
  newx, newy=numpy.meshgrid((newx[:-1]+newx[1:])/2., (newy[:-1]+newy[1:])/2.)
  # place the new data in the output object
  if swapped:
    output_data.data.append(PhysicalProperty(cols[1][0], cols[1][1],
                                             newy.flatten()))
    output_data.data.append(PhysicalProperty(cols[0][0], cols[0][1],
                                             newx.flatten()))
  else:
    output_data.data.append(PhysicalProperty(cols[0][0], cols[0][1],
                                             newx.flatten()))
    output_data.data.append(PhysicalProperty(cols[1][0], cols[1][1],
                                             newy.flatten()))
  output_data.data.append(PhysicalProperty(cols[2][0], cols[2][1],
                                           newz,
                                           newdz))
  return output_data

def calculate_savitzky_golay(dataset, window_size=5, order=2, derivative=1):
  '''
    Calculate smoothed dataset with savitzky golay filter up to a maximal derivative.
    
    :param dataset: The dataset to use for the data
    :param window_size: Size of the filter window in points
    :param order: Order of polynomials to be used for the filtering
    :param derivative: The derivative to be calculated
    
    :return: a dataset containing the smoothed data and it's derivatives.
  '''
  if dataset.zdata>=0:
    return None
  units=dataset.units()
  dims=dataset.dimensions()
  xindex=dataset.xdata
  yindex=dataset.ydata
  yerror=dataset.yerror
  newcols=[[dims[xindex], units[xindex]], ['smoothed '+dims[yindex], units[yindex]]]
  derivative=min(order-1, derivative)
  for i in range(1, derivative+1):
    newcols.append([dims[yindex]+("\\047"*i),
            PhysicalUnit(units[yindex])/PhysicalUnit(units[xindex]+'^%i'%i)])
  output=MeasurementData(newcols, [], 0, 1+derivative)
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
  sort_idx=numpy.argsort(x)
  x=x[sort_idx]
  y=y[sort_idx]
  error=error[sort_idx]
  output.data[0].values=x
  # calculate smoothed data and derivatives
  dx=numpy.array([x[1]-x[0]]+(x[1:]-x[:-1]).tolist())
  for i in range(derivative+1):
    output.data[i+1].values=(savitzky_golay(y, window_size, order, i)/dx**i).tolist()
  if derivative==0:
    output.short_info=dataset.short_info+' filtered with moving-window'
  else:
    output.short_info=dataset.short_info+' derivative-%i'%derivative
  output.sample_name=dataset.sample_name
  return output

def calculate_butterworth(dataset, filter_steepness=6, filter_cutoff=0.5, derivative=1):
  '''
    Calculate a smoothed function as spectral estimate with a Butterworth low-pass
    filter in frouier space. This can be used to calculate derivatives.
    
      S. Smith, 
      The Scientist and Engineer’s Guide to Digital Signal Processing, 
      California Technical Publishing, 1997.
    
    :param dataset: MeasurementData object to be used as input
    :param filter_steepness: The steepness of the low pass filter after the cut-off frequency
    :param filter_cutoff: The frequency (as parts from the maximal frequency) where the filter cut-off lies
    :param derivative: Which derivative to calculate with this method.
    
    :return: a dataset containing the derivated data
  '''
  sort_idx=numpy.argsort(dataset.x)
  x=dataset.x[sort_idx].copy()
  y=dataset.y[sort_idx].copy()
  output=MeasurementData(x=0, y=2)
  output.append_column(x)
  # create a dataset with even number of elements.
  if len(x)%2==1:
    x=x.copy()
    x.append(x[-1])
    y.append(y[-1])
    crop_last=True
  else:
    crop_last=False
  # Perform fast fourier transform (for real input)
  F=numpy.fft.rfft(y)
  # filter the higher frequencies with a cutt-off function
  k=numpy.arange(len(y)//2+1)
  k_0=len(y)/2.*filter_cutoff+1.
  F_B=(1./(1.+(k/k_0)**filter_steepness))*F
  # apply inverse fourier transform to calculate smoothed data
  yout=PhysicalProperty(y.dimension, y.unit, numpy.fft.irfft(F_B))
  if crop_last:
    yout=yout[:-1]
  output.append_column(PhysicalProperty(y.dimension, y.unit, yout))
  # Calculate the derivative in fourier space by multiplying with 2πik and transform back to real space
  #deriv=numpy.fft.irfft(((2.j*numpy.pi*k)/x[:len(x)//2+1].view(numpy.ndarray))**derivative * F_B)
  stepk=(1./(x[1:].view(numpy.ndarray)-x[:-1].view(numpy.ndarray)).mean())/len(x)
  deriv=numpy.fft.irfft(((2.j*numpy.pi*k)*stepk)**derivative*F_B)
  if crop_last:
    deriv=deriv[:-1]
  output.append_column(PhysicalProperty(y.dimension+"\\047"*derivative,
                                 y.unit/x.unit**derivative,
                                 deriv))
  output.sample_name=dataset.sample_name
  if derivative==0:
    output.short_info=dataset.short_info+' filtered with spectral-estimate'
  else:
    output.short_info=dataset.short_info+' spectral-estimate derivative-%i'%derivative
  return output

def calculate_discrete_derivative(dataset, points=5):
  '''
    Calculate the derivative of a dataset using step-by-step calculations.
    Not so nice results as the other methods but stable and independent of x-spacing.
  '''
  if not points in [2, 3, 5]:
    raise 'ValueError', 'points need to be 2,3 or 5'
  x=dataset.x.copy()
  y=dataset.y.copy()
  sort_idx=numpy.argsort(x)
  x=x[sort_idx]
  y=y[sort_idx]
  output=MeasurementData()
  output.append_column(x)
  if points==2:
    dy=(y[1:]-y[:-1])/(x[1:]-x[:-1])
    dy=PhysicalProperty(dy.dimension, dy.unit, dy.tolist()+[float(dy[-1])])
    output.append_column(dy)
  elif points==3:
    dy=(y[2:]-y[:-2])/(x[2:]-x[:-2])
    dy=PhysicalProperty(dy.dimension, dy.unit, [float(dy[0])]+dy.tolist()+[float(dy[-1])])
    output.append_column(dy)
  elif points==5:
    dy=(-y[4:]+8*y[3:-1]-8*y[1:-3]+y[:-4])/\
        (3.*(x[4:]-x[:-4]))
    left=float(dy[0])
    right=float(dy[0])
    dy=PhysicalProperty(dy.dimension, dy.unit, [left, left]+dy.tolist()+[right, right])
    output.append_column(dy)
  output.sample_name=dataset.sample_name
  output.short_info=dataset.short_info+' discrete derivative'
  return output

def calculate_integral(dataset):
  '''
    Calculate the integral of a dataset using the trapezoidal rule.
  '''
  x=dataset.x.copy()
  y=dataset.y.copy()
  sort_idx=numpy.argsort(x)
  x=x[sort_idx]
  y=y[sort_idx]
  output=MeasurementData()
  output.append_column(x)
  xa=x.view(numpy.ndarray)
  ya=y.view(numpy.ndarray)
  try:
    # if available use scipy's cumulative trapezoidal integration function
    from scipy.integrate import cumtrapz
  except ImportError:
    inty=[ya[0]*(xa[1]-xa[0])]
    for i in range(1, len(x)):
      inty.append(numpy.trapz(ya[:i], xa[:i]))
  else:
    inty=numpy.append([0], cumtrapz(ya, xa))
  output.append_column(PhysicalProperty(
                                        'int('+y.dimension+')',
                                        y.unit*x.unit,
                                        inty
                                        ))
  output.sample_name=dataset.sample_name
  output.short_info=dataset.short_info+' integrated'
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

  def next(self): #@ReservedAssignment
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
      new_lines.append("%i = %s"%(i, line))
    self.string='\n'.join(new_lines)

def savitzky_golay(y, window_size, order, deriv=0):
  '''
    Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techhniques.

    Notes:
    
      The Savitzky-Golay is a type of low-pass filter, particularly
      suited for smoothing noisy data. The main idea behind this
      approach is to make for each point a least-square fit with a
      polynomial of high order over a odd-sized window centered at
      the point.

      . [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
        Data by Simplified Least Squares Procedures. Analytical
        Chemistry, 1964, 36 (8), pp 1627-1639.
      . [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
        W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
        Cambridge University Press ISBN-13: 9780521880688


    :param y: the values of the time history of the signal (array)
    :param window_size: the length of the window, must be an odd integer number.
    :param order: the order of the polynomial used in the filtering, must be less then `window_size` - 1.
    :param deriv: the order of the derivative to compute (default = 0 means only smoothing)
    
    :return: ys the smoothed signal (or it's n-th derivative).

  '''
  np=numpy
  try:
      window_size=np.abs(np.int(window_size))
      order=np.abs(np.int(order))
  except ValueError:
      raise ValueError("window_size and order have to be of type int")
  if window_size%2!=1:
    window_size-=1
  if window_size<1:
      raise TypeError("window_size size must be a positive odd number")
  if window_size<order+2:
      raise TypeError("window_size is too small for the polynomials order")
  order_range=range(order+1)
  half_window=(window_size-1)//2
  # precompute coefficients
  b=np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
  m=np.linalg.pinv(b).A[deriv]*(-1.)**deriv
  # pad the signal at the extremes with
  # values taken from the signal itself
  firstvals=y[0]-np.abs(y[1:half_window+1][::-1]-y[0])
  lastvals=y[-1]+np.abs(y[-half_window-1:-1][::-1]-y[-1])
  y=np.concatenate((firstvals, y, lastvals))
  return np.convolve(m, y, mode='valid')
