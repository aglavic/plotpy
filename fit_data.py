#!/usr/bin/env python
''' 
  Module containing a class for nonlinear fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
  Can in principal be used for any python function which returns floats or an array of floats.
'''

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from scipy.optimize import leastsq, fsolve
from scipy.special import wofz
from math import pi, sqrt,  tanh
# for dialog window import gtk
import gtk
# import own modules
from measurement_data_structure import MeasurementData

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class FitFunction:
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
        err=y-function(function_parameters, x)
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: y[x.index(x_i)]-function(function_parameters, x_i)), x)
      return err
    else:
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=(y-function(function_parameters, x))/yerror
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: (y[x.index(x_i)]-function(function_parameters, x_i))/yerror[x.index(x_i)]), x)
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
    cov_out=[]
    for i in range(len(self.parameters)):
      cov_out.append([])
      for j in range(len(self.parameters)):
        if (cov_x is not None) and (i in self.refine_parameters) and (j in self.refine_parameters):
          cov_out[i].append(cov_x[self.refine_parameters.index(i)][self.refine_parameters.index(j)])
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
  
  def history_back(self, action, dialog, window):
    '''
      Set old parameters from the history of parameters and
      set the active parameters as history.
    '''
    active_params=self.parameters
    self.parameters=self.parameters_history
    self.parameters_history=active_params
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)


class FitSum(FitFunction):
  '''
    Fit the Sum of two FitFunctions.
  '''
  
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

  def toggle_refine_parameter(self, action, index):
    '''
      Change the refined parameters in the origin functions.
    '''
    FitFunction.toggle_refine_parameter(self, action, index)
    if index < len(self.origin[0].parameters):
      self.origin[0].toggle_refine_parameter(action, index)
    else:
      self.origin[1].toggle_refine_parameter(action, index-len(self.origin[0].parameters))

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
  fit_function_text='a*x + b'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1, 0]
    FitFunction.__init__(self, initial_parameters)


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

class FitBrillouine(FitFunction):
  '''
    Fit a Brillouine's function for the magnetic behaviour of a ferromagnet
    against temperature.
  '''
  
  # define class variables.
  name="Brillouine"
  parameters=[1.e7, 1., 1., 4.19e16, 1.e-1]
  parameter_names=['lambda', 'S', 'L', 'N', 'B']
  fit_function_text='Parameters (B): lambda; S; L; N'
  muB=9.27e-24 # mu_Bohr
  kB=1.38e-23  # k_Boltzmann

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[1.5e8, 1., 1.,4.19e16, 1.e-1]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(4)
  
  def residuals(self, params, y, x, yerror=None):
    '''
      As the fit with fsolve is quite slow we tell the user about
      the state of the fit.
    '''
    err=FitFunction.residuals(self, params, y, x, yerror=None)
    print "End of iteration %i, chi is now %.6g" % (self.iteration, sum(err))
    self.iteration+=1
    return err
  
  def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
    self.iteration=1
    return FitFunction.refine(self,  dataset_x,  dataset_y, dataset_yerror=None)

  def brillouine(self, p, M, T):
    '''
      Brillouine function which M=...(M) => 0=...(M)-M which
      has to be solved for specific parameters.
    '''
    S=abs(p[1])
    L=abs(p[2])
    J=S+L
    g=1.5+ (S*(S+1.)-L*(L+1.))/(2.*J*(J+1.))
    d=(2.*J+1.)/(2.*J)
    c=g*self.muB*J/self.kB
    Ms=g*J*self.muB*p[3]
    B=p[4]
    return d/tanh(d*c*(p[0]*M/T+B/T))-(d-1)/tanh((d-1)*c*(p[0]*M/T+B/T))-M/Ms
  
  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
#    out=[]
#    for i,  xi in enumerate(x):
#      out.append(fsolve(lambda item: self.brillouine(p, item, xi), 1e-6))
    return fsolve(lambda item: self.brillouine(p, item, x), 1e-6)


#--------------------------------- Define common functions for fits ---------------------------------

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
                       FitGaussian.name: FitGaussian, 
                       FitVoigt.name: FitVoigt, 
                       FitOneOverX.name: FitOneOverX, 
                       FitLorentzian.name: FitLorentzian, 
                       FitSQUIDSignal.name: FitSQUIDSignal, 
                       FitBrillouine.name: FitBrillouine
                       }
  
  def __init__(self,  dataset, file_actions=None):
    '''
      Constructor creating pointer to the dataset.
      
      @param dataset A MeasurementData object
      @param file_actions FileActions object to use      
    '''
    self.functions=[] # a list of sequences (FitFunction, fit, plot, ignore errors) to be used
    self.data=dataset
    self.show_covariance=False
    if file_actions:
      # connect the functions to the file_actions object
      file_actions.actions['add_function']=self.add_function
      file_actions.actions['sum_up_functions']=self.sum
      file_actions.actions['set_function_parameters']=self.set_function_parameters
      file_actions.actions['fit_functions']=self.fit
      file_actions.actions['simmulate_functions']=self.simulate
      self.file_actions=file_actions


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


  #+++++++++++++++++++++++++ methods for GUI dialog ++++++++++++++++++++
  def get_dialog(self, window, dialog):
    '''
      Create a aligned table widget for the interaction with this class.
      
      @param window The parent Window for the dialog
      @param dialog The dialog the table will be appendet to
      
      @return A widget object for the Dialog and a list of action widgets inside the table
    '''
    def set_function_param(action, function, index):
      '''
        Toggle a setting in the functions list. 
        Called when check button is pressed.
      '''
      function[index]=not function[index]
    
    entries=[]
    align_table=gtk.Table(5,len(self.functions)*2+2,False)
    for i, function in enumerate(self.functions):
      #+++++++ create a row for every function in the list +++++++
      text=gtk.Label(function[0].name + ': ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  0, 2,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      if function[0].parameters_history is not None:
        back_button=gtk.Button(label='Undo')
        align_table.attach(back_button,
                    # X direction #          # Y direction
                    0, 2,                      i*2+1, i*2+2,
                    gtk.EXPAND,     gtk.EXPAND,
                    0,                         0);
        back_button.connect('clicked', function[0].history_back, dialog, window)
      text=gtk.Entry()
      text.set_text(function[0].fit_function_text)
      text.set_width_chars(40)
      align_table.attach(text,
                  # X direction #          # Y direction
                  4, 5,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_errors=gtk.CheckButton(label="ignore errors")
      toggle_errors.set_active(function[3])
      toggle_errors.connect('toggled', set_function_param, function, 3)
      align_table.attach(toggle_errors,
                  # X direction #          # Y direction
                  5, 6,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      new_line, entry=self.function_line(function[0], dialog, window)
      entries.append(entry+[text, toggle_errors])
      align_table.attach(new_line,
                  # X direction #          # Y direction
                  4, 6,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label(' fit ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  2, 3,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_fit=gtk.CheckButton()
      toggle_fit.set_active(function[1])
      toggle_fit.connect('toggled', set_function_param, function, 1)
      align_table.attach(toggle_fit,
                  # X direction #          # Y direction
                  2, 3,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      text=gtk.Label(' show ')
      align_table.attach(text,
                  # X direction #          # Y direction
                  3, 4,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      toggle_show=gtk.CheckButton()
      toggle_show.set_active(function[2])
      toggle_show.connect('toggled', set_function_param, function, 2)
      align_table.attach(toggle_show,
                  # X direction #          # Y direction
                  3, 4,                      i*2+1, i*2+2,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      #------- create a row for every function in the list -------
    # Options for new functions
    new_function=gtk.combo_box_new_text()
    add_button=gtk.Button(label='Add Function')
    map(new_function.append_text, self.get_functions())
    sum_button=gtk.Button(label='Combine')
    fit_button=gtk.Button(label='Fit and Replot')
    # connect the window signals to the handling methods
    add_button.connect('clicked', self.add_function_dialog, new_function, dialog, window)
    sum_button.connect('clicked', self.combine_dialog, dialog, window)
    fit_button.connect('clicked', self.fit_from_dialog, entries, dialog, window)
    align=gtk.Alignment(0.5, 0.5, 0, 0) # the table is centered in the dialog window
    align.add(align_table)
    def toggle_show_covariance(action, self):
      self.show_covariance=not self.show_covariance
    toggle_covariance=gtk.CheckButton(label='show errors')
    toggle_covariance.set_active(self.show_covariance)
    toggle_covariance.connect('toggled', toggle_show_covariance, self)
    return align, [toggle_covariance, new_function, add_button, sum_button, fit_button]
  
  def function_line(self, function, dialog, window):
    '''
      Create the widgets for one function and return a table of those.
      The entry widgets are returned in a list to be able to read them.
      
      @param function The FitFunction object for this line
      @param dialog The dialog widget this line will be added to
      @param window The parent window for the dialog
      
      @return A table widget for this function line and a list of entry widgets.
    '''
    table=gtk.Table(15, (len(function.parameters)*3+3)//12+1, False)
    entries=[]
    for i, parameter in enumerate(function.parameters):
      # Test,Toggle and Entry for every parameter of the funciton
      text=gtk.Label(function.parameter_names[i])
      toggle=gtk.CheckButton()
      toggle.set_active(i in function.refine_parameters)
      toggle.connect('toggled', function.toggle_refine_parameter, i)
      entries.append(gtk.Entry())
      entries[i].set_width_chars(8)
      entries[i].set_text("%.6g" % parameter)
      table.attach(toggle, i*3%12, (i*3%12)+1, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(text, (i*3%12)+1, (i*3%12)+2, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(entries[i], (i*3%12)+2, (i*3%12)+3, i*3//12, i*3//12+1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    # Button to delete the function
    del_button=gtk.Button(label='DEL')
    table.attach(del_button, 12, 13, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    del_button.connect('clicked', self.del_function_dialog, function, dialog, window)
    entries.append(gtk.Entry())
    entries[len(function.parameters)].set_width_chars(8)
    # entries for the x range this function is fitted in
    if function.x_from is not None:
      entries[len(function.parameters)].set_text("%.6g" % function.x_from)
    else:
      entries[len(function.parameters)].set_text("{from}")      
    table.attach(entries[len(function.parameters)], 13, 14, 0, 1, 
                             gtk.EXPAND, gtk.EXPAND, 0, 0)
    entries.append(gtk.Entry())
    entries[len(function.parameters)+1].set_width_chars(8)
    if function.x_to is not None:
      entries[len(function.parameters)+1].set_text("%.6g" % function.x_to)
    else:
      entries[len(function.parameters)+1].set_text("{to}")
    table.attach(entries[len(function.parameters)+1], 14,15, 0, 1, 
                             gtk.EXPAND, gtk.EXPAND, 0, 0)
    return table, entries

  def add_function_dialog(self, action, name, dialog, window):
    '''
      Add a function via dialog access.
      Standart parameters are used.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    self.file_actions.activate_action('add_function', name.get_active_text())
    #self.add_function(name.get_active_text())
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def del_function_dialog(self, action, function, dialog, window):
    '''
      Delete a function via dialog access.
      
      @param name Entry for the name of the function to be added
      @param dialog Dialog to recreate with the new function
      @param window Paranet window for the dialog
    '''
    self.del_function(function)
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def set_function_parameters(self, func_index, values):
    '''
      Set the parameters of one functio object in the list.
    
      @param func_index List index of the function to be altered
      @param values List of values for the parameters to be set
    '''
    for j, value in enumerate(values[0:-4]):
      self.functions[func_index][0].parameters[j]=value
    self.functions[func_index][0].x_from=values[-3]
    self.functions[func_index][0].x_to=values[-2]
    self.functions[func_index][0].fit_function_text=values[-1]
  
  def fit_from_dialog(self, action, entries, dialog, window):
    '''
      Trigger the fit, simulation and replot functions.
      
      @param entries Entry widgets from the dialog to get the function parameters from
      @param dialog Fit dialog widget
      @param window Parent window of the dialog.destroy
    '''
    def get_entry_values(entry, if_not=0):
      '''
        Help function to evaluate the entry boxes. Skippes entries with no numbers
        and converts ',' to '.'.
      '''
      try: 
        return float(entry.get_text().replace(',', '.'))
      except ValueError:
        return if_not
    for i, function in enumerate(self.functions):
      # Set all function parameters according to the entries
      values=[]
      for entry in entries[i][:-4]:
        values.append(get_entry_values(entry))
      values.append(get_entry_values(entries[i][-4], if_not=None))
      values.append(get_entry_values(entries[i][-3], if_not=None))
      values.append(entries[i][-2].get_text())
      self.file_actions.activate_action('set_function_parameters', i, values)
    covariance_matices=self.file_actions.activate_action('fit_functions')
    self.file_actions.activate_action('simmulate_functions')
    # save the geometry of the fit dialog and replot the data+fit
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.replot()
    if self.show_covariance:
      # Show the estimated errors of the fit parameters
      text='Esitmated errors from covariance matrices:'
      for i, function in enumerate(self.functions):
        if function[1]:
          text+='\n\n%s:' % function[0].name
          for j, pj in enumerate(function[0].parameter_names):
            text+='\n%s = %g +/- %g' % (pj, function[0].parameters[j], sqrt(covariance_matices[i][j][j]))
      info_dialog=gtk.MessageDialog(parent=window, flags=gtk.DIALOG_DESTROY_WITH_PARENT, 
                                    type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, message_format=text)
      info_dialog.run()
      info_dialog.destroy()
    # recreate the fit dialog with the new parameters 
    window.fit_dialog(None, size, position)

  def combine_dialog(self, action, dialog, window):
    '''
      A dialog window to combine two fit functions e.g. sum them up.
    '''
    # TODO: Make a(b) working.
    if len(self.functions)<2:
      return False
    function_1=gtk.combo_box_new_text()
    for i, function in enumerate(self.functions):
      function_1.append_text(str(i)+': '+function[0].name)
    function_2=gtk.combo_box_new_text()
    for i, function in enumerate(self.functions):
      function_2.append_text(str(i)+': '+function[0].name)
    combine_dialog=gtk.Dialog(title='Fit...')
    combine_dialog.set_default_size(400,150)
    combine_dialog.vbox.add(function_1)
    combine_dialog.vbox.add(function_2)
    combine_dialog.add_button('Add: a + b',2)
    #combine_dialog.add_button('Add: a(b)',3)
    combine_dialog.add_button('Cancel',1)
    combine_dialog.show_all()
    result=combine_dialog.run()
    selected=[int(function_1.get_active_text().split(':')[0]), int(function_2.get_active_text().split(':')[0])]
    if result in [2, 3]:
      if result==2:
        self.file_actions.activate_action('sum_up_functions', selected[0], selected[1])
        size=dialog.get_size()
        position=dialog.get_position()
        dialog.destroy()
        window.fit_dialog(None, size, position)
    combine_dialog.destroy()

  #------------------------- methods for GUI dialog ---------------------
