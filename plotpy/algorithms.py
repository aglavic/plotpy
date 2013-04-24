#-*- coding: utf-8 -*-
'''
  General support algorithms used in data treatment.
'''

import numpy
from .macros import macro
from .mds import PhysicalProperty, MeasurementData, PhysicalUnit

@macro
def interpolate_and_smooth(data, sigma_x, sigma_y, grid_x, grid_y, use_matrix_data_output=False, fill_value=(0., 1.)):
  '''
    Fill a grid with datapoints from another grid, weighting the points with a gaussian up to a distance of
    3*sigma.
    
    :param data: MeasurementData object to be used as source_synopsis
    :param sigma_x: Sigma for the gaussian weighting in x direction
    :param sigmy_y: Sigma for the gaussian weighting in y direction
    :param grid_xy: List of (x,y) tuples for the new grid
    
    :return: MeasurementData or HugeMD object with the rebinned data
  '''
  if data.zdata<0:
    raise ValueError, 'data needs to be 3 dimensional for interpolation'
  gauss_factor_x=-0.5/sigma_x**2
  gauss_factor_y=-0.5/sigma_y**2
  three_sigma_x=3.*sigma_x
  three_sigma_y=3.*sigma_y
  exp=numpy.exp
  sqrt=numpy.sqrt
  where=numpy.where
  # get the data
  data=data.get_filtered_data_matrix()
  x=data[data.xdata]
  y=data[data.ydata]
  z=data[data.zdata]
  z=where(numpy.isinf(z), 0., numpy.nan_to_num(z))
  # interpolate the square of the errors
  if data._yerror>=0:
    dzq=data[data.yerror]**2
  else:
    dzq=data.z.error**2
  dzq=where(numpy.isinf(dzq), numpy.nan_to_num(dzq), 1.)
  #zout=[]
  #dzout=[]
  dims=data.dimensions()
  units=data.units()
  cols=[(dims[data.xdata], units[data.xdata]),
        (dims[data.ydata], units[data.ydata]),
        (dims[data.zdata], units[data.zdata])]
  if use_matrix_data_output:
    output_data=MeasurementData(cols, [], 0, 1,-1, 2)
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

@macro
def rebin_2d(data, join_pixels_x, join_pixels_y=None, use_matrix_data_output=False):
  '''
    Rebin data on a regular grid by summing up pixels in x and y direction.
    
    :param data: MeasurementData object as source
    :param join_pixels_x: Number of pixels to sum together in x direction
    :param join_pixels_y: Number of pixels to sum together in y direction, if None use x
    
    :return: New MeasurementData object with the rebinned data
  '''
  if join_pixels_y is None:
    join_pixels_y=join_pixels_x
  if data.zdata<0:
    raise ValueError, 'data needs to be 3 dimensional for interpolation'
  # get the data
  x=data.x
  y=data.y
  z=data.z
  if data._yerror<0:
    if data.z.error is None:
      dzq=None
    else:
      dzq=data.z.error**2
  else:
    dzq=data.data[data.yerror]**2
  # create new object
  dims=data.dimensions()
  units=data.units()
  cols=[(dims[data.xdata], units[data.xdata]),
        (dims[data.ydata], units[data.ydata]),
        (dims[data.zdata], units[data.zdata])]
  if use_matrix_data_output:
    output_data=MeasurementData([], [], 0, 1,-1, 2)
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

@macro
def savitzky_golay(data, window_size=5, order=2, derivative=1):
  '''
    Calculate smoothed data with savitzky golay filter up to a maximal derivative.
    
    :param data: The data to use for the data
    :param window_size: Size of the filter window in points
    :param order: Order of polynomials to be used for the filtering
    :param derivative: The derivative to be calculated
    
    :return: a data containing the smoothed data and it's derivatives.
  '''
  if data.zdata>=0:
    return None
  units=data.units()
  dims=data.dimensions()
  xindex=data.xdata
  yindex=data.ydata
  yerror=data.yerror
  newcols=[[dims[xindex], units[xindex]], ['smoothed '+dims[yindex], units[yindex]]]
  derivative=min(order-1, derivative)
  for i in range(1, derivative+1):
    newcols.append([dims[yindex]+("\\047"*i),
            PhysicalUnit(units[yindex])/(PhysicalUnit(units[xindex])**i)])
  output=MeasurementData(newcols, [], 0, 1+derivative)
  xlist=[]
  ylist=[]
  elist=[]
  # get only points which are not filtered
  for point in data:
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
    output.data[i+1].values=(_savitzky_golay(y, window_size, order, i)/dx**i).tolist()
  if derivative==0:
    output.short_info=data.short_info+' filtered with moving-window'
  else:
    output.short_info=data.short_info+' derivative-%i'%derivative
  output.sample_name=data.sample_name
  return output

@macro
def butterworth(data, filter_steepness=6, filter_cutoff=0.5, derivative=1):
  '''
    Calculate a smoothed function as spectral estimate with a Butterworth low-pass
    filter in Fourier space. This can be used to calculate derivatives.
    
      S. Smith, 
      The Scientist and Engineer’s Guide to Digital Signal Processing, 
      California Technical Publishing, 1997.
    
    :param data: MeasurementData object to be used as input
    :param filter_steepness: The steepness of the low pass filter after the cut-off frequency
    :param filter_cutoff: The frequency (as parts from the maximal frequency) where the filter cut-off lies
    :param derivative: Which derivative to calculate with this method.
    
    :return: a data containing the derivated data
  '''
  sort_idx=numpy.argsort(data.x)
  x=data.x[sort_idx].copy()
  y=data.y[sort_idx].copy()
  output=MeasurementData(x=0, y=2)
  output.append_column(x)
  # create a data with even number of elements.
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
  output.sample_name=data.sample_name
  if derivative==0:
    output.short_info=data.short_info+' filtered with spectral-estimate'
  else:
    output.short_info=data.short_info+' spectral-estimate derivative-%i'%derivative
  return output

@macro
def discrete_derivative(data, points=5):
  '''
    Calculate the derivative of a data using step-by-step calculations.
    Not so nice results as the other methods but stable and independent of x-spacing.
  '''
  if not points in [2, 3, 5]:
    raise 'ValueError', 'points need to be 2,3 or 5'
  x=data.x.copy()
  y=data.y.copy()
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
  output.sample_name=data.sample_name
  output.short_info=data.short_info+' discrete derivative'
  return output

@macro
def integrate(data):
  '''
    Calculate the integral of a data using the trapezoidal rule.
  '''
  x=data.x.copy()
  y=data.y.copy()
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
  output.sample_name=data.sample_name
  output.short_info=data.short_info+' integrated'
  return output

  #-------- Functions not directly called as actions ------

def _savitzky_golay(y, window_size, order, deriv=0):
  '''
    Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.

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
