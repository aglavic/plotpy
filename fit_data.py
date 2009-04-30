#!/usr/bin/env python
''' 
  Module containing a class for complex fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
'''

# TODO: use numpy functions for faster fitting.

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from scipy.optimize import leastsq
from math import pi, sqrt

class FitSession:
  '''
    Class used to fit a set of functions to a given measurement_data_structure.
  '''
  def __init__(self):
    None

class FitFunction:
  '''
    Root class for fittable functions. Parant of all other functions.
  '''
  
  # define class variables, will be overwritten from childs.
  name="Unnamed"
  parameters=[]
  parameter_names=[]
  fit_function=lambda self, p, x: 0.
  fit_function_text='f(x)'
  
  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters

  def residuals(self, params, y, x):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    # x and y are lists and the function is only defined for one point.
    err= map((lambda x_i: y[x.index(x_i)]-function(params, x_i)), x)
    return err
  
  def refine(self,  dataset_x,  dataset_y):
    '''
      Do the least square refinement to the given dataset. If the fit converges
      the new parameters are stored.
      Returns the message string of leastsq.
    '''
    new_params, cov_x, infodict, mesg, ier = leastsq(self.residuals, self.parameters, args=(dataset_y, dataset_x), full_output=1)
    # if the fit converged use the new parameters and store the old ones in the history variable.
    if ier in [1, 2, 3, 4]:
      self.parameters_history=self.parameters
      self.parameters=new_params
    return mesg


#+++++++++++++++++++++++++++++++++ Define common functions for fits +++++++++++++++++++++++++++++++++

class FitLinear(FitFunction):
  '''
    Fit a linear regression.
  '''
  
  # define class variables.
  name="Linear Regression"
  parameters=[1, 0]
  parameter_names=['a', 'b']
  fit_function=lambda self, p, x: p[0] * x + p[1]
  fit_function_text='f(x)=a*x + b'

  __init__=FitFunction.__init__

class FitQuadratic(FitFunction):
  '''
    Fit a quadratic function.
  '''
  
  # define class variables.
  name="Parabula"
  parameters=[1, 0,  0]
  parameter_names=['a', 'b', 'c']
  fit_function=lambda self, p, x: p[0] * x**2 + p[1] * x + p[2]
  fit_function_text='f(x)=a*x**2 + b*x + c'

  __init__=FitFunction.__init__

class FitExponential(FitFunction):
  '''
    Fit a exponential function.
  '''
  
  # define class variables.
  name="Exponential"
  parameters=[1, 1, 0]
  parameter_names=['A', 'B', 'C']
  fit_function=lambda self, p, x: p[0] * numpy.exp(p[1] * x) + p[2]
  fit_function_text='f(x)=A*exp(B*x) + C'

  __init__=FitFunction.__init__

class FitGaussian(FitFunction):
  '''
    Fit a gaussian function.
  '''
  
  # define class variables.
  name="Gaussian"
  parameters=[1, 0, 1, 0]
  parameter_names=['A', 'x_0', 'sigma', 'b']
  fit_function=lambda self, p, x: p[0] * numpy.exp(-0.5*(x - p[1])/p[2]) + p[3]
  fit_function_text='f(x)=A*exp(-0.5*(x-x_0)/sigma) + b'

  __init__=FitFunction.__init__
