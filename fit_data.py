# -*- encoding: utf-8 -*-
''' 
  Module containing a class for nonlinear fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
  Can in principal be used for any python function which returns floats or an array of floats.
'''

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from scipy.optimize import leastsq, fsolve
from scipy.special import wofz
from math import pi, sqrt,  tanh, sin, asin
# import own modules
from measurement_data_structure import MeasurementData
# import gui functions for active config.gui.toolkit
import config.gui
try:
  FitSessionGUI=__import__( config.gui.toolkit+'gui.gui_fit_data', fromlist=['FitSessionGUI']).FitSessionGUI
  FitFunctionGUI=__import__( config.gui.toolkit+'gui.gui_fit_data', fromlist=['FitFunctionGUI']).FitFunctionGUI
except ImportError: 
  class FitSessionGUI: pass
  class FitFunctionGUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class FitFunction(FitFunctionGUI):
  '''
    Root class for fittable functions. Parant of all other functions.
  '''
  
  # define class variables, will be overwritten from childs.
  name="Unnamed"
  parameters=[]
  parameter_names=[]
  parameters_history=None
  parameters_covariance=None
  fit_function=lambda self, p, x: 0.
  fit_function_text='f(x)'
  x_from=None
  x_to=None
  is_3d=False
  
  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    self.refine_parameters=range(len(self.parameters))


  def residuals(self, params, y, x, yerror=None):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      @param params Parameters for the function in this iteration
      @param y List of y values measured
      @param x List of x values for the measured points
      @param yerror List of error values for the y values or None if the fit is not weighted
      
      @return Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    if yerror==None: # is error list given?
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=function(function_parameters, x)-y
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: function(function_parameters, x_i)-y[x.index(x_i)]), x)
      return err
    else:
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=(function(function_parameters, x)-y)/yerror
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: (function(function_parameters, x_i)-y[x.index(x_i)])/yerror[x.index(x_i)]), x)
      return err      
  
  def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
    '''
      Do the least square refinement to the given dataset. If the fit converges
      the new parameters are stored.
      
      @param dataset_x list of x values from the dataset
      @param dataset_y list of y values from the dataset
      @param dataset_yerror list of errors from the dataset or None for no weighting
      
      @return The message string of leastsq and the covariance matrix
    '''
    parameters=[self.parameters[i] for i in self.refine_parameters]
    # only refine inside the selected region
    x=[]
    y=[]
    dy=[]
    x_from=self.x_from
    x_to=self.x_to
    for i,x_i in enumerate(dataset_x):
      if ((x_from is None) or (x_i >= x_from)) and\
         ((x_to is None) or (x_i <= x_to)):
        x.append(x_i)
        y.append(dataset_y[i])
        if not dataset_yerror is None:
          dy.append(dataset_yerror[i])
    if dataset_yerror is None:
      fit_args=(y, x)
    else:
      fit_args=(y, x, dy)
    new_params, cov_x, infodict, mesg, ier = leastsq(self.residuals, parameters, args=fit_args, full_output=1)
    # if the fit converged use the new parameters and store the old ones in the history variable.
    cov=cov_x
    if ier in [1, 2, 3, 4]:
      if len(parameters)==1:
        new_function_parameters=list(self.parameters)
        new_function_parameters[self.refine_parameters[0]]=new_params
      else:
        new_function_parameters=[]
        for i in range(len(self.parameters)):
          if i in self.refine_parameters:
            new_function_parameters.append(new_params[self.refine_parameters.index(i)])
          else:
            new_function_parameters.append(self.parameters[i])      
      self.set_parameters(new_function_parameters)
    # calculate the covariance matrix from cov_x, see scipy.optimize.leastsq help for details.
      if (len(y) > len(parameters)) and cov_x is not None:
        if dataset_yerror:
          s_sq = (numpy.array(self.residuals(new_function_parameters, y, x, dy))**2).sum()/\
                                           (len(y)-len(self.refine_parameters))        
          s_sq /= ((1./numpy.array(dy))**2).sum()
        else:
          s_sq = (numpy.array(self.residuals(new_function_parameters, y, x))**2).sum()/\
                                           (len(y)-len(self.refine_parameters))        
        cov = cov_x * s_sq
    cov_out=[]
    for i in range(len(self.parameters)):
      cov_out.append([])
      for j in range(len(self.parameters)):
        if (cov is not None) and (i in self.refine_parameters) and (j in self.refine_parameters):
          cov_out[i].append(cov[self.refine_parameters.index(i)][self.refine_parameters.index(j)])
        else:
          cov_out[i].append(0.)
    return mesg, cov_out

  def set_parameters(self, new_params):
    '''
      Set new parameters and store old ones in history.
      
      @param new_params List of new parameters
    '''
    self.parameters_history=self.parameters
    self.parameters=list(new_params)

  def toggle_refine_parameter(self, action, index):
    '''
      Add or remove a parameter index to the list of refined parameters for the fit.
    '''
    if index in self.refine_parameters:
      self.refine_parameters.remove(index)
    else:
      self.refine_parameters.append(index)
  
  def simulate(self, x, interpolate=5):
    '''
      Calculate the function for the active parameters for x values and some values
      in between.
      
      @param x List of x values to calculate the function for
      @param interpolate Number of points to interpolate in between the x values
    
      @return simulated y-values for a list of giver x-values.
    '''
    xint=[]
    for i, xi in enumerate(x[:-1]):
      for j in range(interpolate):
        xint.append(xi + float(x[i+1]-xi)/interpolate * j)
    try:
      y=list(self.fit_function(self.parameters, xint))
    except TypeError:
      # x is list and the function is only defined for one point.
      y= map((lambda x_i: self.fit_function(self.parameters, x_i)), xint)
    return xint, y
  
  def __call__(self, x):
    '''
      Calling the object returns the y values corresponding to the given x values.
    '''
    x=numpy.array(x)
    try:
      return self.fit_function(self.parameters, x)
    except TypeError:
      return map((lambda x_i: self.fit_function(self.parameters, x_i)), x)

class FitSum(FitFunction):
  '''
    Fit the Sum of two FitFunctions.
  '''
  
  func_len=(None, None)
  
  def __init__(self, func1,  func2):
    '''
      Construct a sum of two functions to use for fit.
      
      @param funci the functions to add together
    '''
    self.name=func1.name + ' + ' + func2.name
    self.parameters=func1.parameters + func2.parameters
    self.parameter_names=[name + '1' for name in func1.parameter_names] + [name + '2' for name in func2.parameter_names]
    self.refine_parameters=func1.refine_parameters + [index + len(func1.parameters) for index in func2.refine_parameters]
    function_text=func1.fit_function_text
    for i in range(len(func1.parameters)):
      function_text=function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    function_text=func2.fit_function_text
    for i in range(len(func2.parameters)):
      function_text=function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' + ' + function_text
    self.func_len = (len(func1.parameters), len(func2.parameters))
    self.origin=(func1, func2)

  def fit_function(self, p, x):
    func1=self.origin[0].fit_function
    func2=self.origin[1].fit_function
    len1, len2=self.func_len
    return func1(p[0:len1], x) + func2(p[len1:], x)
  
  def set_parameters(self, new_params):
    '''
      Set new parameters and pass them to origin functions.
    '''
    FitFunction.set_parameters(self, new_params)
    index=len(self.origin[0].parameters)
    self.origin[0].set_parameters(self.parameters[:index])
    self.origin[1].set_parameters(self.parameters[index:])

  def toggle_refine_parameter(self, action, index):
    '''
      Change the refined parameters in the origin functions.
    '''
    FitFunction.toggle_refine_parameter(self, action, index)
    if index < len(self.origin[0].parameters):
      self.origin[0].toggle_refine_parameter(action, index)
    else:
      self.origin[1].toggle_refine_parameter(action, index-len(self.origin[0].parameters))

class FitFunction3D(FitFunctionGUI):
  '''
    Root class for fittable functions with x,y and z data. Parant of all other functions.
  '''
  
  # define class variables, will be overwritten from childs.
  name="Unnamed"
  parameters=[]
  parameter_names=[]
  parameters_history=None
  parameters_covariance=None
  fit_function=lambda self, p, x, y: 0.
  fit_function_text='f(x,y)'
  x_from=None
  x_to=None
  y_from=None
  y_to=None
  is_3d=True
  
  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    self.refine_parameters=range(len(self.parameters))


  def residuals(self, params, z, y, x, zerror=None):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      @param params Parameters for the function in this iteration
      @param z List of z values measured
      @param y List of y values for the measured points
      @param x List of x values for the measured points
      @param yerror List of error values for the y values or None if the fit is not weighted
      
      @return Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    if zerror==None: # is error list given?
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=function(function_parameters, x, y)-z
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err=map(lambda x_i, y_i, z_i: function(function_parameters, x_i, y_i)-z_i, zip(x, y, z))
      return err
    else:
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=(function(function_parameters, x, y)-z)/zerror
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i, y_i, z_i, zerror_i: (function(function_parameters, x_i, y_i)-z_i)/zerror_i), zip(x, y, z, zerror))
      return err      
  
  def refine(self,  dataset_x,  dataset_y, dataset_z, dataset_zerror=None):
    '''
      Do the least square refinement to the given dataset. If the fit converges
      the new parameters are stored.
      
      @param dataset_x list of x values from the dataset
      @param dataset_y list of y values from the dataset
      @param dataset_z list of z values from the dataset
      @param dataset_zerror list of errors from the dataset or None for no weighting
      
      @return The message string of leastsq and the covariance matrix
    '''
    parameters=[self.parameters[i] for i in self.refine_parameters]
    x=numpy.array(dataset_x[:])
    y=numpy.array(dataset_y[:])
    z=numpy.array(dataset_z[:])
    if dataset_zerror is not None:
      dz=numpy.array(dataset_zerror[:])
    else:
      dz=None
    # only refine inside the selected region
    x_from=self.x_from
    x_to=self.x_to
    if x_from is None:
      x_from=x.min()
    if x_to is None:
      x_to=x.max()
    y_from=self.y_from
    y_to=self.y_to
    if y_from is None:
      y_from=y.min()
    if y_to is None:
      y_to=y.max()
    filter1=numpy.where((x>=x_from)*(x<=x_to))[0]
    x=x[filter1]
    y=y[filter1]
    z=z[filter1]
    if dz is not None:
      dz=dz[filter1]
    filter2=numpy.where((y>=y_from)*(y<=y_to))[0]
    x=x[filter2]
    y=y[filter2]
    z=z[filter2]
    if dz is not None:
      dz=dz[filter2]
    if dz is None:
      fit_args=(z, y, x)
    else:
      fit_args=(z, y, x, dz)  
    new_params, cov_x, infodict, mesg, ier = leastsq(self.residuals, parameters, args=fit_args, full_output=1)
    # if the fit converged use the new parameters and store the old ones in the history variable.
    cov=cov_x
    if ier in [1, 2, 3, 4]:
      if len(parameters)==1:
        new_function_parameters=list(self.parameters)
        new_function_parameters[self.refine_parameters[0]]=new_params
      else:
        new_function_parameters=[]
        for i in range(len(self.parameters)):
          if i in self.refine_parameters:
            new_function_parameters.append(new_params[self.refine_parameters.index(i)])
          else:
            new_function_parameters.append(self.parameters[i])      
      self.set_parameters(new_function_parameters)
    # calculate the covariance matrix from cov_x, see scipy.optimize.leastsq help for details.
      if (len(z) > len(parameters)) and cov_x is not None:
        if dataset_zerror:
          s_sq = (numpy.array(self.residuals(new_function_parameters, z, y, x, dz))**2).sum()/\
                                           (len(z)-len(self.refine_parameters))        
          s_sq /= ((1./numpy.array(dz))**2).sum()
        else:
          s_sq = (numpy.array(self.residuals(new_function_parameters, z, y, x))**2).sum()/\
                                           (len(z)-len(self.refine_parameters))        
        cov = cov_x * s_sq
    cov_out=[]
    for i in range(len(self.parameters)):
      cov_out.append([])
      for j in range(len(self.parameters)):
        if (cov is not None) and (i in self.refine_parameters) and (j in self.refine_parameters):
          cov_out[i].append(cov[self.refine_parameters.index(i)][self.refine_parameters.index(j)])
        else:
          cov_out[i].append(0.)
    return mesg, cov_out

  def set_parameters(self, new_params):
    '''
      Set new parameters and store old ones in history.
      
      @param new_params List of new parameters
    '''
    self.parameters_history=self.parameters
    self.parameters=list(new_params)

  def toggle_refine_parameter(self, action, index):
    '''
      Add or remove a parameter index to the list of refined parameters for the fit.
    '''
    if index in self.refine_parameters:
      self.refine_parameters.remove(index)
    else:
      self.refine_parameters.append(index)
  
  def simulate(self, y, x):
    '''
      Calculate the function for the active parameters for x values and some values
      in between.
      
      @param x List of x values to calculate the function for
      @param interpolate Number of points to interpolate in between the x values
    
      @return simulated y-values for a list of giver x-values.
    '''
    try:
      x=numpy.array(x[:])
      y=numpy.array(y[:])
    except TypeError:
      pass
    try:
      z=list(self.fit_function(self.parameters, x, y))
    except TypeError:
      # x is list and the function is only defined for one point.
      z= map((lambda x_i, y_i: self.fit_function(self.parameters, x_i, y_i)), zip(x, y))
    return x, y, z
  
  def __call__(self, x, y):
    '''
      Calling the object returns the y values corresponding to the given x values.
    '''
    try:
      x=numpy.array(x[:])
      y=numpy.array(y[:])
    except TypeError:
      pass
    try:
      return self.fit_function(self.parameters, x, y)
    except TypeError:
      return map((lambda x_i, y_i: self.fit_function(self.parameters, x_i, y_i)), zip(x, y))

#+++++++++++++++++++++++++++++++++ Define common functions for 2d fits +++++++++++++++++++++++++++++++++

class FitLinear(FitFunction):
  '''
    Fit a linear regression.
  '''
  
  # define class variables.
  name="Linear Regression"
  parameters=[1, 0]
  parameter_names=['a', 'b']
  fit_function=lambda self, p, x: p[0] * numpy.array(x) + p[1]
  fit_function_text='a*x + b'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0]
    FitFunction.__init__(self, initial_parameters)

class FitDiamagnetism(FitFunction):
  '''
    Fit two linear functions with the same slope, an offset and a hole around zero.
  '''
  
  # define class variables.
  name="Linear Asymptotes"
  parameters=[0, 0, 0, 1]
  parameter_names=['a', 'b', 'c', 'split']
  fit_function_text='slope=a'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[0, 0, 0, 1]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(3)
  
  def fit_function(self, p, x):
    '''
      Two linear functions with different offsets,
      split left and right from the y-axes.
    '''
    xarray=numpy.array(x)
    # create an array with True at every xposition which is outside the split region
    switch=(xarray<-abs(p[3]))+(xarray>abs(p[3]))
    output=p[0] * xarray + numpy.sign(xarray) * p[1] + p[2]
    return switch*output

class FitQuadratic(FitFunction):
  '''
    Fit a quadratic function.
  '''
  
  # define class variables.
  name="Parabula"
  parameters=[1, 0,  0]
  parameter_names=['a', 'b', 'c']
  fit_function=lambda self, p, x: p[0] * numpy.array(x)**2 + p[1] * numpy.array(x) + p[2]
  fit_function_text='a*x^2 + b*x + c'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 0]
    FitFunction.__init__(self, initial_parameters)

class FitSinus(FitFunction):
  '''
    Fit a sinus function.
  '''
  
  # define class variables.
  name="Sinus"
  parameters=[1., 1.,  0.,  0.]
  parameter_names=['a', 'ω_0','φ_0', 'c']
  fit_function=lambda self, p, x: p[0] * numpy.sin((numpy.array(x) * p[1] - p[2])*numpy.pi/180.) + p[3]
  fit_function_text='a*sin(ω_0·x-φ_0)+c'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1., 1., 0., 0.]
    FitFunction.__init__(self, initial_parameters)

class FitExponential(FitFunction):
  '''
    Fit a exponential function.
  '''
  
  # define class variables.
  name="Exponential"
  parameters=[1, 1, 0]
  parameter_names=['A', 'B', 'C']
  fit_function=lambda self, p, x: p[0] * numpy.exp(p[1] * numpy.array(x)) + p[2]
  fit_function_text='A*exp(B*x) + C'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 1, 0]
    FitFunction.__init__(self, initial_parameters)

class FitOneOverX(FitFunction):
  '''
    Fit a one over x function.
  '''
  
  # define class variables.
  name="1/x"
  parameters=[1, 0, 0]
  parameter_names=['C', 'x_0', 'D']
  fit_function=lambda self, p, x: p[0] * 1 / (numpy.array(x) - p[1]) + p[2]
  fit_function_text='C/(x-x_0) + D'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 0]
    FitFunction.__init__(self, initial_parameters)

class FitGaussian(FitFunction):
  '''
    Fit a gaussian function.
  '''
  
  # define class variables.
  name="Gaussian"
  parameters=[1, 0, 1, 0]
  parameter_names=['A', 'x_0', 'sigma', 'C']
  fit_function=lambda self, p, x: p[0] * numpy.exp(-0.5*((numpy.array(x) - p[1])/p[2])**2) + p[3]
  fit_function_text='A*exp(-0.5*(x-x_0)/sigma)+C'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 1, 0]
    FitFunction.__init__(self, initial_parameters)

class FitLorentzian(FitFunction):
  '''
    Fit a lorentz function.
  '''
  
  # define class variables.
  name="Lorentzian"
  parameters=[1, 0, 1, 0]
  parameter_names=['I', 'x_0', 'gamma', 'C']
  fit_function=lambda self, p, x: p[0] / (1 + ((numpy.array(x)-p[1])/p[2])**2) + p[3]
  fit_function_text='A/(1 + ((x-x_0)/gamma)^2)+C'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 1, 0]
    FitFunction.__init__(self, initial_parameters)

class FitVoigt(FitFunction):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''
  
  # define class variables.
  name="Voigt"
  parameters=[1, 0, 1, 1, 0]
  parameter_names=['I', 'x_0', 'gamma', 'sigma', 'C']
  fit_function_text='I*Re(w(z))/Re(w(z_0))+C; w=(x-x_0)/sigma/sqrt(2)'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 1, 1, 0]
    FitFunction.__init__(self, initial_parameters)
  
  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    x=numpy.float64(numpy.array(x))
    p=numpy.float64(numpy.array(p))
    z=(x - p[1] + (abs(p[2])*1j)) / abs(p[3])/self.sqrt2
    z0=(0. + (abs(p[2])*1j)) / abs(p[3])/self.sqrt2
    value=p[0] * wofz(z).real / wofz(z0).real + p[4]
    return value

class FitCuK(FitFunction):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''
  
  # define class variables.
  name="Cu K-radiation"
  parameters=[1, 0, 0.001, 0.001, 0, 2, 0,99752006]
  parameter_names=['I', 'x_0', 'gamma', 'sigma', 'C', 'K_a1/K_a2', 'x_01/x_02']
  fit_function_text='x_0 ; gamma ; sigma'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 0.001, 0.001, 0, 2, 0.99752006]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(6)
  
  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    x=numpy.float64(numpy.array(x))
    p=numpy.float64(numpy.array(p))
    if p[1]<20:
      p2=p[1]/p[6]
    else:
      # if x0 is larger than 20 assume it is the th angle,
      # for smaller values it doesn't change a lot
      p2=asin( sin(p[1]*pi/180.)/p[6] )/pi*180.
    z=(x - p[1] + (abs(p[2])*1j)) / abs(p[3])/self.sqrt2
    z2=(x - p2 + (abs(p[2])*1j)) / abs(p[3])/self.sqrt2
    z0=(0. + (abs(p[2])*1j)) / abs(p[3])/self.sqrt2
    value=p[0] * wofz(z).real / wofz(z0).real + p[4]
    value2=p[0]/p[5] * wofz(z2).real / wofz(z0).real + p[4]
    return value+value2

class FitSuperlattice(FitFunction):
  '''
    Fit a bragg reflex from a multilayer. Formulas are taken from:
      "Structural refinement of superlattices from x-ray diffraction",
      Eric E. Fullerton, Ivan K. Schuller, H.Vanderstraeten and Y.Bruynseraede
      Physical Review B, Volume 45, Number 16 (1992)
      
      With additions from related publications, referenced in the paper mentioned above.
  '''
  
  # define class variables.
  name="Superlattice"
  parameters=[10, 1., 2.71, 1., 2.71 , 1., 3.01,10. , 0.5, 1.,  0.5, 2., 1.0, 0.01, 0.2, 6.]
  parameter_names=['M', 'I-A','x_0-A', 'I-B', 'x_0-B', 'I-subs.', 'x_0-subs.', 
                    'D_{xA+(1-x)B}', 'x', 'δ_AB', 'σ_AB', 'ω_AB','a*', 'sigma', 'C', 'F_select']
  fit_function_text='(params)'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[10, 1., 2.71, 1., 2.71 , 1., 3.01,10. , 0.5, 1.,  0.5, 2., 1.0, 0.01, 0.2, 6.]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=[]
    self._parameter_dictionary={}
    self.rebuild_param_dictionary(self.parameters)
  
  def rebuild_param_dictionary(self, p):
    '''
      Create a dictionary of the parameters for better readability of all funcions.
      
      @param p List of parameters to be used
    '''
    params=self._parameter_dictionary
    # reciprocal lattice parameter
    params['a*']=p[12]
    # number of bilayers M
    params['M']=int(p[0])
    # structure peak parameters of both layers and substrat
    params['q0_A']=p[2]*p[12]
    params['q0_B']=p[4]*p[12]
    params['I_A']=p[1]
    params['I_B']=p[3]
    params['q0_substrat']=p[6]*p[12]
    params['I_substrat']=p[5]
    # thickness of both layers (including δ)
    params['t_A']=p[7]*min(abs(p[8]), 1.)
    params['t_B']=p[7]*min(abs(1-p[8]), 1.)
    # lattice parameters
    d_A=(numpy.pi*2./params['q0_A'])
    d_B=(numpy.pi*2./params['q0_B'])
    # distance δ of two planes (The given layer thickness and the offset because of only integer lattice planes) 
    # and distance fluctuation σ and size fluctuation (e.g. roughness) ω
    params['δ_AB']=(d_A+d_B)/2.
    params['σ_AB']=p[10]
    params['ω_AB']=p[11]
    # Background intensity
    params['resolution']=p[13]*p[12]
    params['BG']=p[14]
    # select which structurefactor to return
    self.output_select=p[15]
  
  def fit_function(self, p, q):
    '''
      Calculate the intensities of the multilayer at reciprocal lattice positions q.
      The user can select which parts of the structure factor should be plotted by changing the
      F_select parameter. A negativ parameter means no convolution with the resolution function.
      
      @param p Parameters for the function
      @param q Reciprocal lattice vector q
      
      @return The calculated intensities for the selected structure factor + background
    '''
    self.rebuild_param_dictionary(p)
    params=self._parameter_dictionary
    q=params['a*']*numpy.array(q, dtype=numpy.complex64)
    if self.output_select==0:
      I=abs(self.calc_F_substrat(q))**2
    elif abs(self.output_select)==1:
      I=abs(self.calc_F_layer(q, params['I_A'], params['q0_A'], params['t_A']-params['δ_AB']))**2*params['M']**2
    elif abs(self.output_select)==2:
      I=abs(self.calc_F_layer(q, params['I_B'], params['q0_B'], params['t_B']-params['δ_AB']))**2*params['M']**2
    elif abs(self.output_select)==3:
      F_SL=self.calc_F_bilayer(q)
      I=abs(F_SL)**2
    elif abs(self.output_select)==4:
      F_SL=self.calc_F_ML(q)
      I=abs(F_SL)**2
    elif abs(self.output_select)==5:
      F_SL=self.calc_F_ML(q)
      I=abs(F_SL+self.calc_F_substrat(q))**2
    elif abs(self.output_select)==6:
      F_SL=self.calc_F_ML_roughness(q)
      I=abs(F_SL+self.calc_F_substrat(q))**2
    elif abs(self.output_select)==7:
      I=self.calc_I_ML_fluctuation(q)+abs(self.calc_F_substrat(q))**2
    elif abs(self.output_select)==8:
      I=self.calc_I_ML_roughness(q)+abs(self.calc_F_substrat(q))**2
    else:
      I=q*0.+1.
    if self.output_select>=0:
      I=self.convolute_with_resolutions(I, q)
    return numpy.float64(I+params['BG'])
  
  def convolute_with_resolutions(self, I, q):
    '''
      Convolute the calculated intensity with the resolution function.
      
      @param I Calculated intensity to convolute
      @param q Reciprocal lattice vector q
      
      @return Convoluted intensity
    '''    
    params=self._parameter_dictionary
    sigma_res=params['resolution']
    q_center=numpy.linspace(-((q.max()-q.min())/2.), (q.max()-q.min())/2., len(q))
    resolution=numpy.exp(-0.5*(q_center/sigma_res)**2)
    resolution/=resolution.sum()
    output=numpy.convolve(I, resolution, 'same')
    return output
  
  ###################################### Calculate structue factors #########################################
  
  # slit function approach
  def calc_F_layer__(self, q, I, q0, t_j):
    '''
      Calculate the structure factor function for one layer. This is the structure factor
      of a crystal with the thickness t_j at the bragg peak q0.
      
      @param q Reciprocal lattice vector q
      @param I Scaling factor
      @param q0 Position of the corresponding bragg peak
      @param t_j Thickness of the layer
      
      @return structure factor for this layer at the origin position.
    '''
    params=self._parameter_dictionary
    # parameter for (q-q0)*width/2
    t=(q-q0)*0.5*t_j*numpy.pi
    # intensity scaling
    I_layer=numpy.sqrt(I)*t_j
    # Structure factor
    F_layer=I_layer*numpy.sin(t)/t
    # exchange NaN by Intensity
    NaNs=numpy.isnan(F_layer)
    F_layer=numpy.nan_to_num(F_layer)+I_layer*NaNs
    return F_layer
  
  # structure factor approach
  def calc_F_layer_(self, q, I, q0, t_j):
    '''
      Calculate the structurefactor by summing up all unit cells in the region.
      
      @param q Reciprocal lattice vector q
      @param I Scaling factor
      @param q0 Position of the corresponding bragg peak
      @param t_j Thickness of the layer
      
      @return structure factor for this layer at the origin position.
    '''
    params=self._parameter_dictionary
    d=(numpy.pi*2./q0)
    planes=int(t_j/d)
    F_layer=numpy.zeros_like(q)
    for i in range(planes):
      F_layer+=numpy.exp(1j*q*i*d)
    return numpy.sqrt(I)*F_layer#*numpy.exp(1j*q*(t_j/d-planes)*0.5)
  
  def calc_F_layer(self, q, I, q0, t_j):
    '''
      Calculate the structurefactor by summing up all unit cells in the region.
      
      @param q Reciprocal lattice vector q
      @param I Scaling factor
      @param q0 Position of the corresponding bragg peak
      @param t_j Thickness of the layer
      
      @return structure factor for this layer at the origin position.
    '''
    params=self._parameter_dictionary
    d=(numpy.pi*2./q0)
    planes=int(t_j/d)
    F_layer=(1.-numpy.exp(1j*q*(planes+1)*d))/(1.-numpy.exp(1j*q*d))
    return numpy.sqrt(I)*F_layer
  

  def calc_F_substrat(self, q):
    '''
      Calculate the structure factor of the substrate (crystal truncation rod at substrate peak position.
      
      @param q Reciprocal lattice vector q
      
      @return structure factor for the substrate
    '''
    params=self._parameter_dictionary
    F_substrate=1j/(q-params['q0_substrat'])
    F_substrate=numpy.nan_to_num(F_substrate)
    # set the integrated intensity to I_substrate
    F_substrate*=numpy.sqrt(params['I_substrat']/(abs(F_substrate)**2).sum())
    return F_substrate
  
  def calc_F_bilayer(self, q):
    '''
      Calculate the structure factor for a bilayer

      @param q Reciprocal lattice vector q
      
      @return the complete Intensity of the multilayer without the substrate
    '''
    # get relevant parameters
    params=self._parameter_dictionary
    # parameters for the interface distances
    return self.calc_F_layer(q, params['I_A'], params['q0_A'], params['t_A']-params['δ_AB'])+\
               numpy.exp(1j*q*(params['t_A']+params['δ_AB']))*self.calc_F_layer(q, params['I_B'], params['q0_B'], params['t_B']-params['δ_AB'])


  def calc_F_ML(self, q):
    '''
      Calculate the structure factor for a superlattice without any roughness
      using eq(3) from PRB paper.

      @param q Reciprocal lattice vector q
      
      @return the complete structure factor of the multilayer (without substrate)
    '''
    exp=numpy.exp
    # get relevant parameters
    params=self._parameter_dictionary
    M=params['M']
    F_AB=self.calc_F_bilayer(q)
    x=self.calc_xj()
    iq=1j*q
    #F_SLi=map(lambda item: exp(iq*item), x)
    #F_SL=sum(F_SLi)
    F_SL=(1.-exp(iq*(M+1)*x[1]))/(1.-exp(iq*x[1]))
    return F_SL*F_AB
  
  def calc_F_ML_roughness(self, q):
    '''
      Calculate the avaraged structure factor for the multilayer with thickness variations.

      @param q Reciprocal lattice vector q
      
      @return the complete structure factor of the multilayer (without substrate)
    '''
    # get relevant parameters
    params=self._parameter_dictionary
    # calculate t_j's for the discrete avarage because of roughness
    t_deltaj=self.calc_tj()
    t_A0=params['t_A']
    t_B0=params['t_B']
    t_A=t_A0+t_deltaj[0]
    t_B=t_B0+t_deltaj[1]
    # propability for every distance
    P=self.calc_Pj(t_deltaj[0])
    params['t_A']=t_A[0]
    params['t_B']=t_B[0]
    F_ML_roughness=P[0]*self.calc_F_ML(q)
    for j, P_j in enumerate(P[1:]):
      params['t_A']=t_A[j+1]
      params['t_B']=t_B[j+1]
      F_ML_roughness+=P_j*self.calc_F_ML(q)
    params['t_A']=t_A0
    params['t_B']=t_B0
    return F_ML_roughness
  
  ############# additional function for more complicated approach including roughness ##############
  
  
  
  def calc_I_ML_fluctuation(self, q):
    '''
      Calculate the structure factor for a superlattice including fluctuations
      of the interface distance using eq(1) from J.-P. Locquet et al., PRB 38, No. 5 (1988).

      @param q Reciprocal lattice vector q
      
      @return the complete Intensity of the multilayer without the substrate
    '''
    # get relevant parameters
    params=self._parameter_dictionary
    exp=numpy.exp
    cos=numpy.cos
    M=params['M']
    # structure factors of the layers
    A=self.calc_F_layer(q, params['I_A'], params['q0_A'], params['t_A']-params['δ_AB'])
    B=self.calc_F_layer(q, params['I_B'], params['q0_B'], params['t_B']-params['δ_AB'])
    t_A=params['t_A']
    t_B=params['t_B']
    # crystal lattice parameters
    d_A=(numpy.pi*2./params['q0_A'])
    d_B=(numpy.pi*2./params['q0_B'])
    # roughness parameter
    c=1./params['σ_AB']
    a_avg=params['δ_AB']
    LAMBDA=t_A+t_B
    I=M*(abs(A)**2+abs(B)**2+2.*abs(A*B)*exp(-q**2/(4.*c**2))*cos(q*LAMBDA/2.))
    
    for m in range(1, M):
      I+=2.*(M-m) * ( (abs(A)**2+abs(B)**2)*exp(-2.*m*q**2/(4.*c**2))*cos(2.*m*q*LAMBDA/2.) +\
                    abs(A*B)*exp( -(2.*m+1)*q**2/(4.*c**2) )*cos((2.*m+1)*q*LAMBDA/2.) +\
                    abs(A*B)*exp(-(2.*m-1)*q**2/(4.*c**2))*cos((2.*m-1)*q*LAMBDA/2.)   )
    
    return I

  def calc_I_ML_roughness(self, q):
    '''
      Calculate the structure factor for a superlattice including fluctuations and of the interface 
      distance roughness using eq(7)-eq(10) from E.E.Fullerton et al., PRB 45, No. 16 (1992).

      @param q Reciprocal lattice vector q
      
      @return the complete Intensity of the multilayer without the substrate
    '''
    # get relevant parameters
    params=self._parameter_dictionary
    exp=numpy.exp
    M=params['M']
    # parameters for the interface distances
    a_avg=params['δ_AB']
    psi=1j*q*a_avg-q**2/(params['σ_AB']*2.)
    # calculate t_j's for the discrete avarage because of roughness
    t_deltaj=self.calc_tj()
    t_A=params['t_A']+t_deltaj[0]
    t_B=params['t_B']+t_deltaj[1]
    # propability for every distance
    P_A=self.calc_Pj(t_deltaj[0])
    P_B=self.calc_Pj(t_deltaj[1])
    #calculate avarages (I is F·F*)
    I_A_avg=0.
    I_B_avg=0.
    F_A_avg=0.
    F_B_avg=0.
    Phi_A_avg=0.
    Phi_B_avg=0.
    T_A=0.
    T_B=0.
    for j, P_Aj in enumerate(P_A):
      F_Aj=self.calc_F_layer(q, params['I_A'], params['q0_A'], t_A[j]-params['δ_AB'])
      F_A_avg+=P_Aj*F_Aj
      Phi_A_avg+=P_Aj*exp(1j*q*(t_A[j]-params['δ_AB']))*F_Aj.conjugate()
      I_A_avg+=P_Aj*F_Aj*F_Aj.conjugate()
      T_A+=P_Aj*exp(1j*q*(t_A[j]-params['δ_AB']))
    for j, P_Bj in enumerate(P_B):
      F_Bj=self.calc_F_layer(q, params['I_B'], params['q0_B'], t_B[j]-params['δ_AB'])
      F_B_avg+=P_Bj*F_Bj
      Phi_B_avg+=P_Bj*exp(1j*q*(t_B[j]-params['δ_AB']))*F_Bj.conjugate()
      I_B_avg+=P_Bj*F_Bj*F_Bj.conjugate()
      T_B+=P_Bj*exp(1j*q*(t_B[j]-params['δ_AB']))
    # calculate the Intensity (eq(7) in paper)
    # there can still be an imaginary part becaus of calculation errors 
    I_0=abs(M*(I_A_avg+2.*(exp(psi)*abs(Phi_A_avg*F_B_avg)).real+I_B_avg))
    I_1=  2.*((exp(-psi)*Phi_B_avg*F_A_avg/(T_A*T_B)+\
               Phi_B_avg*F_A_avg/T_A+\
               Phi_B_avg*F_B_avg/T_B+\
               exp(psi)*Phi_A_avg*F_B_avg)*\
        ((M-(M+1)*exp(2*psi)*T_A*T_B+\
          (exp(2*psi)*T_A*T_B)**(M+1))/(1.-exp(2.*psi)*T_A*T_B)-M)).real
    return I_0+I_1

  
  ######################################## calculate parameters ######################################
  
  def calc_xj(self):
    '''
      Calculate xoffset of bilayer.
      
      @return offset position for every layer
    '''
    params=self._parameter_dictionary
    x=[]
    x.append(0.)
    for j in range(params['M']-1):
      x.append(x[j]+params['t_A']+params['t_B'])
    return x
  
  def calc_tj(self):
    '''
      Calculate deviation of thickness as discrete gaussians.
      
      @return deviation of thickness from -3ω to +3ω as numpy array
    '''
    params=self._parameter_dictionary
    # avarage dspacing
    dA=(numpy.pi*2./params['q0_A'])
    dB=(numpy.pi*2./params['q0_B'])
    # 3*omega in integer d/2 values
    three_omega_A=(4.*params['ω_AB'])-(4.*params['ω_AB']%dA)
    three_omega_B=(4.*params['ω_AB'])-(4.*params['ω_AB']%dB)
    t_deltaj_A=numpy.linspace(-three_omega_A, three_omega_A, 2.*three_omega_A/dA+1)
    t_deltaj_B=numpy.linspace(-three_omega_B, three_omega_B, 2.*three_omega_B/dB+1)
    return t_deltaj_A, t_deltaj_B
  
  def calc_Pj(self, tj):
    '''
      Calculate the propability for every thickness fluctuation tj.
      
      @return the propability for the jth deviation
    '''
    params=self._parameter_dictionary
    omega=params['ω_AB']
    P_j=numpy.exp(-tj**2/(2.*omega**2))
    P_j/=P_j.sum()
    return P_j
  
  #################################### changed derived functions ######################################
  
  def simulate(self, x, interpolate=5):
    output=FitFunction.simulate(self, x, interpolate)
    params=self._parameter_dictionary
    if "Å" in self.fit_function_text:
      self.fit_function_text="%iXml: dA=%.2fÅ dB=%.2fÅ dS=%.2fÅ => tA=%iuc (+%.2g Å) tB=%iuc (+%.2g Å)" % (
                    params['M'], 
                    (numpy.pi*2./params['q0_A']), 
                    (numpy.pi*2./params['q0_B']), 
                    (numpy.pi*2./params['q0_substrat']), 
                    int(params['t_A']/(numpy.pi*2./params['q0_A'])), 
                    (params['t_A']/(numpy.pi*2./params['q0_A'])-int(params['t_A']/(numpy.pi*2./params['q0_A'])))*(numpy.pi*2./params['q0_A']),
                    int(params['t_B']/(numpy.pi*2./params['q0_B'])), 
                    (params['t_B']/(numpy.pi*2./params['q0_B'])-int(params['t_B']/(numpy.pi*2./params['q0_B'])))*(numpy.pi*2./params['q0_B'])
                                                                                  )
    else:
      self.fit_function_text=self.fit_function_text.replace('(params)', "%iXml: dA=%.2fÅ dB=%.2fÅ dS=%.2fÅ => tA=%iuc (+%.2g Å) tB=%iuc (+%.2g Å)" % (
                    params['M'], 
                    (numpy.pi*2./params['q0_A']), 
                    (numpy.pi*2./params['q0_B']), 
                    (numpy.pi*2./params['q0_substrat']), 
                    int(params['t_A']/(numpy.pi*2./params['q0_A'])), 
                    (params['t_A']/(numpy.pi*2./params['q0_A'])-int(params['t_A']/(numpy.pi*2./params['q0_A'])))*(numpy.pi*2./params['q0_A']),
                    int(params['t_B']/(numpy.pi*2./params['q0_B'])), 
                    (params['t_B']/(numpy.pi*2./params['q0_B'])-int(params['t_B']/(numpy.pi*2./params['q0_B'])))*(numpy.pi*2./params['q0_B'])
                                                                                  ))
    return output
    

class FitSQUIDSignal(FitFunction):
  '''
    Fit three gaussians to SQUID raw data to calculate magnetic moments.
  '''
  prefactor=numpy.sqrt(2.*numpy.pi)
  from config.squid import squid_coil_distance, squid_factor
  
  # define class variables.
  name="SQUID RAW-data"
  parameters=[1., 3., 1., 0., 0.]
  parameter_names=['Moment', 'x_0', 'sigma', 'off', 'incr']
  fit_function=lambda self, p, x: p[4] * numpy.array(x) - p[0]/(p[2]*self.squid_factor*self.prefactor) * ( \
                                          numpy.exp(-0.5*((numpy.array(x) - p[1] + self.squid_coil_distance)/p[2])**2)\
                                          + numpy.exp(-0.5*((numpy.array(x) - p[1] - self.squid_coil_distance)/p[2])**2)\
                                          - 2.* numpy.exp(-0.5*((numpy.array(x) - p[1])/p[2])**2) \
                                          )+ p[3]
  fit_function_text='M=Moment ; pos=x_0 ; s = sigma'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1., 3., 1., 0., 0.]
    FitFunction.__init__(self, initial_parameters)

class FitFerromagnetic(FitFunction):
  '''
    Fit a Brillouine's function for the magnetic behaviour of a ferromagnet
    against temperature.
  '''
  
  # define class variables.
  name="Ferromagnetic Orderparameter"
  parameters=[1.e16, 1., 2., 0.1, 1., 1e-5]
  parameter_names=['N', 'J', 'g', 'H', 'lambda',  'StartValue']
  fit_function_text='Parameters: N, J, g, H, lambda, StartValue'
  muB=9.27e-24 # [A·m²] mu_Bohr
  kB=1.38e-20  # [gm²/Ks²] k_Boltzmann

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1.e16, 1., 2., 0.1, 1., 1e-5]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=[0, 1, 2]
  
  def simulate(self, x, ignore=None):
    return FitFunction.simulate(self, x, interpolate=1)
  
  def residuals(self, params, y, x, yerror=None):
    '''
      As the fit with fsolve is quite slow we tell the user about
      the state of the fit.
    '''
    err=FitFunction.residuals(self, params, y, x, yerror=None)
    print "End of function call %i, chi is now %.6g" % (self.iteration, sum(err))
    self.iteration+=1
    return err
  
  def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
    self.iteration=1
    return FitFunction.refine(self,  dataset_x,  dataset_y, dataset_yerror=None)

  def brillouine(self, p, M, T):
    '''
      Brillouine function whith M=Ms*B_J(y) which
      has to be solved for specific parameters.
    '''
    N=p[0]
    J=p[1]
    g=p[2]
    B=p[3]/1.2566e-3
    lambda_M=p[4]*M
    muB=self.muB
    kB=self.kB
    Ms=N*g*muB*J
    y=(g*muB*J*(B+lambda_M))/(kB*T)
    return Ms*B_J(p, y)

  def fit_function(self, p, T):
    '''
      Return the brillouine function of T.
    '''
    T=numpy.array(T)
    M=numpy.array([p[5] for i in range(len(T))])
    M, info, ier, mesg=fsolve(lambda Mi: Mi-self.brillouine(p, Mi, T), M, full_output=True)
    self.last_mesg=mesg
    return M

def B_J(p, x):
  '''
    Brillouine function of x.
  '''
  J=p[1]
  coth=lambda x: 1./numpy.tanh(x)
  return numpy.nan_to_num((2.*J+1.)/(2.*J)*coth((2.*J+1.)/(2.*J)*x) - 1./(2.*J)*coth(1./(2.*J)*x) )

class FitBrillouineB(FitFunction):
  '''
    Fit a Brillouine's function for the magnetic behaviour of a ferromagnet
    against field.
  '''
  
  # define class variables.
  name="Brillouine(B)"
  parameters=[1e16, 2, 2, 300]
  parameter_names=['N', 'J', 'g', 'T']
  fit_function_text='Parameters (B): N; g; J; T'
  muB=9.27e-24 # [A·m²] mu_Bohr
  kB=1.38e-20  # [gm²/Ks²] k_Boltzmann

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1e16, 2, 2, 300]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(4)
  
  #def simulate(self, x, ignore=None):
  #  return FitFunction.simulate(self, x, interpolate=1)
  
  #def residuals(self, params, y, x, yerror=None):
  #  '''
  #    As the fit with fsolve is quite slow we tell the user about
  #    the state of the fit.
  #  '''
  #  err=FitFunction.residuals(self, params, y, x, yerror=None)
  #  print "End of function call %i, chi is now %.6g" % (self.iteration, sum(err))
  #  self.iteration+=1
  #  return err
  
  #def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
  #  self.iteration=1
  #  return FitFunction.refine(self,  dataset_x,  dataset_y, dataset_yerror=None)

  def brillouine(self, p, B):
    '''
      Brillouine function of B.
    '''
    N=p[0]
    J=p[1]
    g=p[2]
    T=p[3]
    muB=self.muB
    kB=self.kB
    x=(g*muB*J*B)/(kB*T)
    return N*g*muB*J*B_J(p, x)
  
  def fit_function(self, p, B):
    '''
      Return the brillouine function of B.
    '''
#    out=[]
#    for i,  xi in enumerate(x):
#      out.append(fsolve(lambda item: self.brillouine(p, item, xi), 1e-6))
    return self.brillouine(p, numpy.array(B)/1.2566e-3)

class FitBrillouineT(FitFunction):
  '''
    Fit a Brillouine's function for the magnetic behaviour of a ferromagnet
    against field.
  '''
  
  # define class variables.
  name="Brillouine(T)"
  parameters=[1e16, 2, 2, 0.1, 0.]
  parameter_names=['N', 'J', 'g', 'B', 'D']
  fit_function_text='Parameters (T): N; g; J; B'
  muB=9.27e-24 # [A·m²] mu_Bohr
  kB=1.38e-20  # [gm²/Ks²] k_Boltzmann

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1e16, 2, 2, 0.1, 0.]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(5)
  
  #def simulate(self, x, ignore=None):
  #  return FitFunction.simulate(self, x, interpolate=1)
  
  #def residuals(self, params, y, x, yerror=None):
  #  '''
  #    As the fit with fsolve is quite slow we tell the user about
  #    the state of the fit.
  #  '''
  #  err=FitFunction.residuals(self, params, y, x, yerror=None)
  #  print "End of function call %i, chi is now %.6g" % (self.iteration, sum(err))
  #  self.iteration+=1
  #  return err
  
  #def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
  #  self.iteration=1
  #  return FitFunction.refine(self,  dataset_x,  dataset_y, dataset_yerror=None)

  def brillouine(self, p, T):
    '''
      Brillouine function of B.
    '''
    N=p[0]
    J=p[1]
    g=p[2]
    B=p[3]/1.2566e-3
    muB=self.muB
    kB=self.kB
    x=(g*muB*J*B)/(kB*T)
    return N*g*muB*J*B_J(p, x)
  
  def fit_function(self, p, T):
    '''
      Return the brillouine function of B.
    '''
    return self.brillouine(p, numpy.array(T))+p[4]


#--------------------------------- Define common functions for 2d fits ---------------------------------

#+++++++++++++++++++++++++++++++++ Define common functions for 3d fits +++++++++++++++++++++++++++++++++
class FitGaussian3D(FitFunction3D):
  '''
    Fit a gaussian function of x and y.
  '''
  
  # define class variables.
  name="Gaussian"
  parameters=[1., 0., 0., 0.1, 0.1, 0., 0.]
  parameter_names=['A', 'x_0', 'y_0', 'sigma_x', 'sigma_y', 'tilt', 'C']
  fit_function_text='A*exp(-0.5*(x-x_0)/sigma)+C'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1., 0., 0., 0.1, 0.1, 0., 0.]
    FitFunction3D.__init__(self, initial_parameters)
  
  def fit_function(self, p, x, y):
    A=p[0]
    x0=p[1]
    y0=p[2]
    sx=p[3]
    sy=p[4]
    tb=numpy.sin(p[5])
    ta=numpy.cos(p[5])
    C=p[6]
    xdist=(numpy.array(x)-x0)
    ydist=(numpy.array(y)-y0)
    xdif=xdist*ta-ydist*tb
    ydif=xdist*tb+ydist*ta
    exp=numpy.exp
    return A * exp(-0.5*((xdif/sx)**2+((ydif/sy)**2))) + C

class FitVoigt3D(FitFunction3D):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''
  
  # define class variables.
  name="Psd. Voigt"
  parameters=[1, 0, 0, 0.01, 0.01, 0.01, 0., 0.5, 0.]
  parameter_names=['I', 'x_0', 'y_0', 'gamma', 'sigma_x', 'sigma_y', 'tilt', 'eta','C']
  fit_function_text='I*Re(w(z))/Re(w(z_0))+C; w=(x-x_0)/sigma/sqrt(2)'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0, 0, 0.01, 0.01, 0.01, 0., 0.5, 0]
    FitFunction3D.__init__(self, initial_parameters)
  
  def fit_function(self, p, x, y):
    '''
      Return the 2d Voigt profile of x and y.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    x=numpy.float64(numpy.array(x))
    y=numpy.float64(numpy.array(y))
    p=numpy.float64(numpy.array(p))
    I=p[0]
    x0=p[1]
    y0=p[2]
    gamma=p[3]
    sx=p[4]
    sy=p[5]
    tb=numpy.sin(p[6])
    ta=numpy.cos(p[6])
    xdist=(numpy.array(x)-x0)
    ydist=(numpy.array(y)-y0)
    xdif=numpy.abs(xdist*ta-ydist*tb)
    ydif=numpy.abs(ydist*ta+xdist*tb)
    eta=p [7]
    c=p[8]
    G=numpy.exp(-numpy.log(2)*((xdif/sx)**2+(ydif/sy)**2))
    L=1./(1.+(xdif**2+ydif**2)/gamma**2)
    value = I * ((1.-eta)*G+eta*L) + c
    return value
#--------------------------------- Define common functions for 3d fits ---------------------------------

class FitSession(FitSessionGUI):
  '''
    Class used to fit a set of functions to a given measurement_data_structure.
    Provides the interface between the MeasurementData and the FitFunction.
  '''
  
  # class variables
  data=None
  # a dictionary of known fit functions
  available_functions_2d={
                       FitLinear.name: FitLinear, 
                       #FitDiamagnetism.name: FitDiamagnetism, 
                       FitQuadratic.name: FitQuadratic, 
                       FitSinus.name: FitSinus, 
                       FitExponential.name: FitExponential, 
                       FitGaussian.name: FitGaussian, 
                       FitVoigt.name: FitVoigt, 
                       FitOneOverX.name: FitOneOverX, 
                       FitLorentzian.name: FitLorentzian, 
                       FitSQUIDSignal.name: FitSQUIDSignal, 
                       FitBrillouineB.name: FitBrillouineB, 
                       FitBrillouineT.name: FitBrillouineT, 
                       FitFerromagnetic.name: FitFerromagnetic, 
                       FitCuK.name: FitCuK, 
                       }
  available_functions_3d={
                       FitGaussian3D.name: FitGaussian3D, 
                       FitVoigt3D.name: FitVoigt3D, 
                          }
  
  def __init__(self,  dataset):
    '''
      Constructor creating pointer to the dataset.
      
      @param dataset A MeasurementData object
    '''
    self.functions=[] # a list of sequences (FitFunction, fit, plot, ignore errors) to be used
    self.data=dataset
    if dataset.zdata<0:
      self.available_functions=self.available_functions_2d
    else:
      self.available_functions=self.available_functions_3d
      self.fit=self.fit3d
      self.simulate=self.simulate3d
    self.show_covariance=False

  def __getitem__(self, item):
    '''
      Return the fit object at position item.
      
      @return FitData object or derived class
    '''
    return self.functions[item][0]

  def add_function(self, function_name):
    '''
      Add a function to the list of fitted functions.
    '''
    if function_name in self.available_functions:
      self.functions.append([self.available_functions[function_name]([]), True, True,  False])
      return True
    else:
      return False
  
  def del_function(self, function_obj):
    '''
      Delete a function to the list of fitted functions.
    '''
    self.functions=[func for func in self.functions if func[0]!=function_obj]
  
  def get_functions(self):
    '''
      Return a list of the available functions.
    '''
    list=self.available_functions.items()
    list=[l[0] for l in list]
    list.sort()
    return list

  def sum(self, index_1, index_2):
    '''
      Create a sum of the functions with index 1 and 2.
      Function 1 and 2 are set not to be fitted.
    '''
    functions=self.functions
    if (index_1 < len(functions)) and (index_2 < len(functions)):
      functions.append([FitSum(functions[index_1][0], functions[index_2][0]), True, True, False])
      functions[index_1][1]=False
      functions[index_2][1]=False
  
  def fit(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
      
      @return The covariance matrices of the fits or [[None]]
    '''
    if (self.data.yerror>=0) and (self.data.yerror!=self.data.ydata)\
        and (self.data.yerror!=self.data.xdata):
      data=self.data.list_err()
      data_x=[d[0] for d in data]
      data_y=[d[1] for d in data]
      data_yerror=[d[2] for d in data]
    else:
      data=self.data.list()
      data_x=[d[0] for d in data]
      data_y=[d[1] for d in data]
      data_yerror=None
    covariance_matices=[]
    for function in self.functions:
      if function[1]:
        if not function[3]:
          mesg, cov_out=function[0].refine(data_x, data_y, data_yerror)
        else:
          mesg, cov_out=function[0].refine(data_x, data_y, None)
        covariance_matices.append(cov_out)
      else:
        covariance_matices.append([[None]])
    return covariance_matices

  def fit3d(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
      
      @return The covariance matrices of the fits or [[None]]
    '''
    if (self.data.yerror>=0) and (self.data.yerror!=self.data.zdata)\
        and (self.data.yerror!=self.data.xdata) and (self.data.yerror!=self.data.ydata):
      data=self.data.list_err()
      data_x=[d[0] for d in data]
      data_y=[d[1] for d in data]
      data_z=[d[2] for d in data]
      data_zerror=[d[3] for d in data]
    else:
      data=self.data.list()
      data_x=[d[0] for d in data]
      data_y=[d[1] for d in data]
      data_z=[d[2] for d in data]
      data_zerror=None
    covariance_matices=[]
    for function in self.functions:
      if function[1]:
        if not function[3]:
          mesg, cov_out=function[0].refine(data_x, data_y, data_z, data_zerror)
        else:
          mesg, cov_out=function[0].refine(data_x, data_y, data_z, None)
        covariance_matices.append(cov_out)
      else:
        covariance_matices.append([[None]])
    return covariance_matices

  def simulate3d(self):
    '''
      Create MeasurementData objects for every FitFunction.
    '''
    pass

  def simulate(self):
    '''
      Create MeasurementData objects for every FitFunction.
    '''
    self.result_data=[]
    dimensions=self.data.dimensions()
    units=self.data.units()
    column_1=(dimensions[self.data.xdata], units[self.data.xdata])
    column_2=(dimensions[self.data.ydata], units[self.data.ydata])
    plot_list=[]
    for function in self.functions:
      self.result_data.append(MeasurementData([column_1, column_2], # columns
                                              [], # const_columns
                                              0, # x-column
                                              1, # y-column
                                              -1  # yerror-column
                                              ))
      result=self.result_data[-1]
      if function[2]:
        data_xy=self.data.list()
        data_x=[d[0] for d in data_xy]
        fit_x, fit_y=function[0].simulate(data_x)
        for i in range(len(fit_x)):
          result.append((fit_x[i], fit_y[i]))
        function_text=function[0].fit_function_text
        for i in range(len(function[0].parameters)):
          function_text=function_text.replace(function[0].parameter_names[i], "%.6g" % function[0].parameters[i], 2)
        result.short_info='fit: ' + function_text
        plot_list.append(result)
    self.data.plot_together=[self.data] + plot_list  
