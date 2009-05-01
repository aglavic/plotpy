#!/usr/bin/env python
''' 
  Module containing a class for nonlinear fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
  Can in principal be used for any python function which returns floats or an array of floats.
'''

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from scipy.optimize import leastsq
from math import pi, sqrt
from measurement_data_structure import MeasurementData
# for dialog window import gtk
import gtk

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
    # if function is defined for lists (e.g. numpy) use this functionality
    try:
      err=y-function(params, x)
    except TypeError:
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
      self.set_parameters(new_params)
    return mesg

  def set_parameters(self, new_params):
    '''Set new parameters and store old ones in history.'''
    self.parameters_history=self.parameters
    self.parameters=list(new_params)

  
  def simulate(self, x):
    '''
      Return simulated y-values for a list of giver x-values.
    '''
    try:
      y=list(self.fit_function(self.parameters, x))
    except TypeError:
      # x is list and the function is only defined for one point.
      y= map((lambda x_i: function(params, x_i)), x)
    return y


class FitSum(FitFunction):
  '''
    Fit the Sum of two FitFunctions.
  '''
  def __init__(self, func1,  func2):
    '''
      Construct a sum of two functions to use for fit.
    '''
    self.name=func1.name + ' + ' + func2.name
    self.parameters=func1.parameters + func2.parameters
    self.parameter_names=[name + '1' for name in func1.parameter_names] + [name + '2' for name in func2.parameter_names]
    function_text=func1.fit_function_text
    for i in range(len(funct1.parameters)):
      function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    for i in range(len(funct2.parameters)):
      function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' + ' + function_text
    self.fit_function = lambda p, x: \
        func1.fit_function(p[0:len(func1.parameters)], x) + \
        func2.fit_function(p[len(func1.parameters):], x)
    self.origin=(func1, func2)
  
  def set_parameters(self, new_params):
    '''
      Set new parameters and pass them to origin functions.
    '''
    FitFunction.set_parameters(self, new_params)
    index=len(self.origin[0].parameters)
    self.origin[0].set_parameters(self.parameters[:index])
    self.origin[1].set_parameters(self.parameters[index:])

  def simulate(self, x):
    '''
      Return simulated y-values for a list of giver x-values.
    '''
    try:
      y=list(self.fit_function(self.parameters, x))
    except TypeError:
      # x is list and the function is only defined for one point.
      y= map((lambda x_i: function(params, x_i)), x)
    return y

#+++++++++++++++++++++++++++++++++ Define common functions for fits +++++++++++++++++++++++++++++++++

class FitLinear(FitFunction):
  '''
    Fit a linear regression.
  '''
  
  # define class variables.
  name="Linear Regression"
  parameters=[1, 0]
  parameter_names=['a', 'b']
  fit_function=lambda self, p, x: p[0] * numpy.array(x) + p[1]
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
  fit_function=lambda self, p, x: p[0] * numpy.array(x)**2 + p[1] * numpy.array(x) + p[2]
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
  fit_function=lambda self, p, x: p[0] * numpy.exp(p[1] * numpy.array(x)) + p[2]
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
  fit_function=lambda self, p, x: p[0] * numpy.exp(-0.5*((numpy.array(x) - p[1])/p[2])**2) + p[3]
  fit_function_text='f(x)=A*exp(-0.5*(x-x_0)/sigma) + b'

  __init__=FitFunction.__init__

class FitSession:
  '''
    Class used to fit a set of functions to a given measurement_data_structure.
    Provides the interface between the MeasurementData and the FitFunction.
  '''
  
  # class variables
  data=None
  # a dictionary of known fit functions
  available_functions={
                       FitLinear.name: FitLinear, 
                       FitQuadratic.name: FitQuadratic, 
                       FitExponential.name: FitExponential, 
                       FitGaussian.name: FitGaussian
                       }
  
  def __init__(self,  dataset):
    '''
      Constructor creating pointer to the dataset.
    '''
    self.functions=[] # a list of sequences (FitFunction, fit, plot) to be used
    self.data=dataset

  def add_function(self, function_name):
    '''
      Add a function to the list of fitted functions.
    '''
    if function_name in self.available_functions:
      self.functions.append([self.available_functions[function_name]([]), True, True])
      return True
    else:
      return False
  
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
      functions.append([FitSum(functions[index_1][0], functions[index_2][0]), True, True])
      functions[index_1][1]=False
      functions[index_2][1]=False
  
  def fit(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
    '''
    for function in self.functions:
      if function[1]:
        data=self.data.list()
        data_x=[d[0] for d in data]
        data_y=[d[1] for d in data]
        function[0].refine(data_x, data_y)

  def simulate(self):
    '''
      Create MeasurementData objects for every fitfunction.
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
                                              1  # yerror-column
                                              ))
      result=self.result_data[-1]
      if function[2]:
        data_xy=self.data.list()
        data_x=[d[0] for d in data_xy]
        data_y=function[0].simulate(data_x)
        for i in range(len(data_x)):
          result.append((data_x[i], data_y[i]))
        function_text=function[0].fit_function_text
        for i in range(len(function[0].parameters)):
          function_text.replace(function[0].parameter_names[i], str(function[0].parameters[i]))
        result.short_info='fit: ' + function_text
        plot_list.append(result)
    self.data.plot_together=[self.data] + plot_list  

  def get_dialog(self, window, dialog):
    '''
      Return a dialog widget for the interaction with this class.
    '''
    entries=[]
    align_table=gtk.Table(4,len(self.functions)*2+1,False)
    for i, function in enumerate(self.functions):
      text=gtk.Label(function[0].name + ': ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  0, 1,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label(function[0].fit_function_text)
      align_table.attach(text,
                  # X direction #          # Y direction
                  1, 2,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      new_line, entry=self.function_line(function[0])
      entries.append(entry)
      align_table.attach(new_line,
                  # X direction #          # Y direction
                  1, 2,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label('fit')
      align_table.attach(text,
                  # X direction #          # Y direction
                  2, 3,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label('show')
      align_table.attach(text,
                  # X direction #          # Y direction
                  3, 4,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
    # Options for new functions
    new_function=gtk.combo_box_new_text()
    add_button=gtk.Button(label='Add Function')
    for name in self.get_functions():
      new_function.append_text(name)
    align_table.attach(add_button,
                # X direction #          # Y direction
                0, 1,                      len(self.functions)*2, len(self.functions)*2+1,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    align_table.attach(new_function,
                # X direction #          # Y direction
                1, 2,                      len(self.functions)*2, len(self.functions)*2+1,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    add_button.connect('clicked', self.add_function_dialog, new_function, dialog, window)
    return align_table
  
  def function_line(self, function):
    table=gtk.Table(len(function.parameters)*2, 1, False)
    entries=[]
    for i, parameter in enumerate(function.parameters):
      text=gtk.Label(function.parameter_names[i])
      entries.append(gtk.Entry())
      entries[i].set_width_chars(8)
      entries[i].set_text(str(parameter))
      table.attach(text, i*2, i*2+1, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(entries[i], i*2+1, i*2+2, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    return table, entries

  
  
  def add_function_dialog(self, action, name, dialog, window):
    '''
      Add a functio via dialog access.
    '''
    self.add_function(name.get_active_text())
    dialog.destroy()
    window.fit_dialog(None)
