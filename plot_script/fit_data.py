# -*- encoding: utf-8 -*-
''' 
  Module containing a class for nonlinear fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
  Can in principal be used for any python function which returns floats or an array of floats.
'''

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from mpfit import mpfit
from math import pi, sin, asin, exp
# import own modules
from measurement_data_structure import MeasurementData, PlotOptions
# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
import parallel
parallel.add_actions([
                      'import numpy',
                      'from mpfit import mpfit',
                      'from math import pi, sqrt,  tanh, sin, asin, exp',
                      'from measurement_data_structure import MeasurementData, PlotOptions',
                      'import config.gui',
                      'import parallel',
                      'from scipy.special import wofz',
                              ])

try:
  FitSessionGUI=__import__('plot_script.'+gui_config.toolkit+'gui.gui_fit_data',
                            fromlist=['FitSessionGUI']).FitSessionGUI
  FitFunctionGUI=__import__('plot_script.'+gui_config.toolkit+'gui.gui_fit_data',
                             fromlist=['FitFunctionGUI']).FitFunctionGUI
except ImportError:
  class FitSessionGUI(object): pass
  class FitFunctionGUI(object): pass

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class ConnectedDict(dict):
  '''
    Dictionary connecting two constrain dictionaries depending on the index.
  '''
  split_index=None
  origin_dicts=None

  def __init__(self, dict1, dict2, split_index):
    dict.__init__(self)
    self.split_index=split_index
    self.origin_dicts=(dict1, dict2)

  def __setitem__(self, index, value):
    if index>=self.split_index:
      if 'tied' in value:
        if '1]' in value['tied']:
          dict.__setitem__(self, index, value)
          return
        value['tied']=value['tied'].replace('2]', ']')
      self.origin_dicts[1][index-self.split_index]=value
    else:
      if 'tied' in value:
        if '2]' in value['tied']:
          dict.__setitem__(self, index, value)
          return
        value['tied']=value['tied'].replace('1]', ']')
      self.origin_dicts[0][index]=value

  def __getitem__(self, index):
    if index>=self.split_index:
      if dict.__contains__(self, index):
        return dict.__getitem__(self, index)
      output=dict(self.origin_dicts[1][index-self.split_index])
      if 'tied' in output:
        output['tied']=output['tied'].replace(']', '2]')
    else:
      if dict.__contains__(self, index):
        return dict.__getitem__(self, index)
      output=dict(self.origin_dicts[0][index])
      if 'tied' in output:
        output['tied']=output['tied'].replace(']', '1]')
    return output

  def items(self):
    combine_dict=dict(self.origin_dicts[0].items())
    for index, item in self.origin_dicts[1].items():
      combine_dict[index+self.split_index]=item
    for index, item in dict.items(self):
      combine_dict[index]=item
    return combine_dict.items()

  def keys(self):
    combine_dict=dict(self.origin_dicts[0].items())
    for index, item in self.origin_dicts[1].items():
      combine_dict[index+self.split_index]=item
    for index, item in dict.items(self):
      combine_dict[index]=item
    return combine_dict.keys()

  def values(self):
    combine_dict=dict(self.origin_dicts[0].items())
    for index, item in self.origin_dicts[1].items():
      combine_dict[index+self.split_index]=item
    for index, item in dict.items(self):
      combine_dict[index]=item
    return combine_dict.values()

  def __contains__(self, index):
    if dict.__contains__(self, index):
      return True
    if index>=self.split_index:
      return (index-self.split_index) in self.origin_dicts[1]
    else:
      return index in self.origin_dicts[0]

class FitFunction(FitFunctionGUI):
  '''
    Root class for fittable functions. Parant of all other functions.
  '''
  # define class variables, will be overwritten from childs.
  name="Unnamed"
  parameters=[]
  parameter_names=[]
  parameter_description={} # tooltip for parameters
  parameters_history=None
  parameters_covariance=None
  fit_function=lambda self, p, x: 0.
  fit_function_text='f(x)'
  last_fit_output=None
  x_from=None
  x_to=None
  is_3d=False
  fit_logarithmic=False
  constrains=None
  max_iter=200. # maximum numer of iterations for fitting (should be lowered for slow functions)

  def __init__(self, initial_parameters=[]):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      # Use supplied parameters
      self.parameters=map(numpy.float64, initial_parameters)
    elif len(initial_parameters)==0:
      # Use std parameters
      self.parameters=map(numpy.float64, self.parameters)
    else:
      # Make sure a wrong number of parameters doesn't get silently ignored
      raise ValueError, "Wrong number of parameters, got %i need %i"%(len(initial_parameters), len(self.parameters))
    # As default all parameters get fitted
    self.refine_parameters=range(len(self.parameters))
    if self.constrains is not None:
      self.constrains=dict(self.constrains)
    self._plot_options=PlotOptions()

  def residuals(self, params, y, x, yerror=None):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      :param params: Parameters for the function in this iteration
      :param y: List of y values measured
      :param x: List of x values for the measured points
      :param yerror: List of error values for the y values or None if the fit is not weighted
      
      :return: Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    # in some circumstances a single parameter can lead to one entry arrays as paramter, so we fix this
    function_parameters=map(numpy.float64, function_parameters)
    if yerror==None: # is error list given?
      err=function(function_parameters, x)-y
    else:
      err=(function(function_parameters, x)-y)/yerror
    return err

  def residuals_log(self, params, y, x, yerror=None):
    '''
      Function used by leastsq to compute the difference between the logarithms of the simulation and data.
      For normal functions this is just the difference between log(y) and log(simulation(x)) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      :param params: Parameters for the function in this iteration
      :param y: List of y values measured
      :param x: List of x values for the measured points
      :param yerror: List of error values for the y values or None if the fit is not weighted
      
      :return: Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    remove_negative=numpy.where(y>0.)
    x=numpy.array(x[remove_negative], dtype=numpy.float64, copy=False)
    y=numpy.array(y[remove_negative], dtype=numpy.float64, copy=False)
    if yerror is not None:
      yerror=numpy.array(yerror[remove_negative], dtype=numpy.float64, copy=False)
      yerror=numpy.where((numpy.isinf(yerror))+(numpy.isnan(yerror))+(yerror<=0.), 1., yerror)
      # use error propagation for log(yi)
      propagated_error=yerror/y
      err=(numpy.log10(function(function_parameters, x))-numpy.log10(y))/propagated_error
    else:
      err=numpy.log10(function(function_parameters, x))-numpy.log10(y)
    return err

  def refine(self, dataset_x, dataset_y, dataset_yerror=None, progress_bar_update=None):
    '''
      Do the least square refinement to the given dataset. If the fit converges
      the new parameters are stored.
      
      :param dataset_x: list of x values from the dataset
      :param dataset_y: list of y values from the dataset
      :param dataset_yerror: list of errors from the dataset or None for no weighting
      
      :return: The message string of leastsq and the covariance matrix
    '''
    parameters=[self.parameters[i] for i in self.refine_parameters]
    # only refine inside the selected region
    x=numpy.array(dataset_x, dtype=numpy.float64, copy=False)
    y=numpy.array(dataset_y, dtype=numpy.float64, copy=False)
    if dataset_yerror is not None:
      dy=numpy.array(dataset_yerror, dtype=numpy.float64, copy=False)
    else:
      dy=None
    x_from=self.x_from
    x_to=self.x_to
    if x_from is None:
      x_from=x.min()
    if x_to is None:
      x_to=x.max()
    filter_indices=numpy.where((x>=x_from)*(x<=x_to))[0]
    x=x[filter_indices]
    y=y[filter_indices]
    if dy is not None:
      dy=dy[filter_indices]
    # remove errors which are zero
    if dy is not None:
      zero_elements=numpy.where(dy==0.)[0]
      non_zero_elements=numpy.where(dy!=0.)[0]
      if len(zero_elements)==0:
        pass
      elif len(non_zero_elements)==0:
        dy=None
      else:
        # Zero elements are replaced by minimal other errors
        dy[zero_elements]+=numpy.abs(dy[non_zero_elements]).min()
    if self.fit_logarithmic:
      residuals=self.residuals_log
    else:
      residuals=self.residuals
    return self.refine_mpfit(residuals, parameters, x, y, dy, progress_bar_update)

  def refine_mpfit(self, residuals, parameters, x, y, dy, progress_bar_update=None):
    '''
      Refine the function using a constrained fit with the 
      Sequential Least SQuares Programming algorithm.
      
      The constrains can be boundaries, equalitiy and inequality fuctions.
      progress_bar_update can be an optional function, which is called after each iteration.
    '''
    constrains=self.constrains
    def function(p, fjac=None, x=None, y=None, dy=None):
      return [0, residuals(p, y, x, dy)]
    function_keywords={'x':x, 'y': y, 'dy': dy}
    # define constrains
    if constrains is None:
      parinfo=None
    else:
      parinfo=[]
      # Define constrains of the fit for each parameter
      for i in range(len(parameters)):
        parinfo.append({'limited':[0, 0], 'limits':[0., 0.]})
        if self.refine_parameters[i] in constrains:
          constrains_i=constrains[self.refine_parameters[i]]
          parinfo_i=parinfo[i]
          if 'bounds' in constrains_i:
            for j in [0, 1]:
              if constrains_i['bounds'][j] is not None:
                parinfo_i['limited'][j]=1
                parinfo_i['limits'][j]=constrains_i['bounds'][j]
                if j==0 and parameters[i]<constrains_i['bounds'][j] or j==1 and parameters[i]>constrains_i['bounds'][j]:
                  parameters[i]=constrains_i['bounds'][j]
          if 'tied' in constrains_i:
            expression=constrains_i['tied']
            for j, pj in enumerate(self.refine_parameters):
              name=self.parameter_names[pj]
              expression=expression.replace('[%s]'%name, 'p[%i]'%j)
            test=expression.replace('p[', '').replace(']', '').replace(' ', '').replace('.', '')\
                .replace('*', '').replace('-', '').replace('/', '').replace('+', '')
            if not test.isdigit() and test!='':
              raise ValueError, 'Wrong syntax in constrains.'
            parinfo_i['tied']=expression
    if progress_bar_update is not None:
      def iterfunct(myfunct, p, iteration, fnorm, functkw=None,
                  parinfo=None, quiet=0, dof=None):
        # perform custom iteration update   
        return progress_bar_update(step_add=float(iteration)/self.max_iter, info='Iteration %i    χ²=%.6e'%(iteration, fnorm))
    else:
      iterfunct=None
    # parallel version
    if parallel.dview is not None:
      dview=parallel.dview
      function_keywords={}
      dview.scatter('x', x)
      dview.scatter('y', y)
      if dy is None:
        dview.execute('dy=None')
      else:
        dview.scatter('dy', dy)
      dview['self']=self
      if self.fit_logarithmic:
        def function(p, fjac=None, x=None, y=None, dy=None):
          dview['p']=p
          dview.execute('err=self.residuals_log(p,y,x,dy)')
          return [0, dview.gather('err')]
      else:
        def function(p, fjac=None, x=None, y=None, dy=None):
          dview['p']=p
          dview.execute('err=self.residuals(p,y,x,dy)')
          return [0, dview.gather('err')]
    # call the fit routine
    result=mpfit(function, xall=parameters, functkw=function_keywords,
                 parinfo=parinfo,
                 maxiter=self.max_iter, iterfunct=iterfunct,
                 fastnorm=1, # faster computation of Chi², can be less stable
                 quiet=1
                 )
    # evaluate the fit result
    if result.status==-1:
      # The fit was stopped by the user, treat as if the maximum iterations were reached
      result.status=5
    self.last_fit_output=result
    if progress_bar_update is not None:
      progress_bar_update(step_add=1.)
    if result.status>0:
      # set the new parameters
      new_params=result.params
      new_function_parameters=[]
      for i in range(len(self.parameters)):
        if i in self.refine_parameters:
          new_function_parameters.append(new_params[self.refine_parameters.index(i)])
        else:
          new_function_parameters.append(self.parameters[i])
      self.set_parameters(new_function_parameters)
    # covariance matrix for all parameters
    cov=result.covar
    cov_out=[]
    for i in range(len(self.parameters)):
      cov_out.append([])
      for j in range(len(self.parameters)):
        if (cov is not None) and (i in self.refine_parameters) and (j in self.refine_parameters):
          cov_out[i].append(cov[self.refine_parameters.index(i)][self.refine_parameters.index(j)])
        else:
          cov_out[i].append(0.)
    mesg=result.errmsg
    if parallel.dview is not None:
      # free memory on remote processes
      dview.execute('del(x);del(y);del(err);del(dy)')
    return mesg, cov_out

  def set_parameters(self, new_params):
    '''
      Set new parameters and store old ones in history.
      
      :param new_params: List of new parameters
    '''
    self.parameters_history=self.parameters
    self.parameters=map(numpy.float64, new_params)

  def toggle_refine_parameter(self, action, index):
    '''
      Add or remove a parameter index to the list of refined parameters for the fit.
    '''
    if index in self.refine_parameters:
      self.refine_parameters.remove(index)
    else:
      self.refine_parameters.append(index)

  def simulate(self, x, interpolate=5, inside_fitrange=False):
    '''
      Calculate the function for the active parameters for x values and some values
      in between.
      
      :param x: List of x values to calculate the function for
      :param interpolate: Number of points to interpolate in between the x values
      :param inside_fitrange: Only simulate points inside the x-constrains of the fit
    
      :return: simulated y-values for a list of giver x-values.
    '''
    if parallel.dview is not None:
      return self.simulate_mp(x, interpolate=5, inside_fitrange=False)
    x=numpy.array(x, dtype=numpy.float64, copy=False)
    if inside_fitrange:
      x_from=self.x_from
      x_to=self.x_to
      if x_from is None:
        x_from=x.min()
      if x_to is None:
        x_to=x.max()
      filter_indices=numpy.where((x>=x_from)*(x<=x_to))[0]
      x=x[filter_indices]
    if interpolate>1:
      # Add interpolation points to x
      xint=[]
      dx=(x[1:]-x[:-1])/interpolate
      for j in range(interpolate):
        xint.append(x[:-1]+dx*j)
      xint=numpy.array(xint, dtype=numpy.float64).transpose().flatten()
      xint=numpy.append(xint, x[-1])
    else:
      xint=x
    try:
      y=self.fit_function(self.parameters, numpy.array(xint, dtype=numpy.float64, copy=False))
    except TypeError, error:
      raise ValueError, "Could not execute function with numpy array: "+str(error)
    return xint, y

  def simulate_mp(self, x, interpolate=5, inside_fitrange=False):
    '''
      Multiprocessing version of simulate.
    '''
    dview=parallel.dview
    x=numpy.array(x, dtype=numpy.float64, copy=False)
    if inside_fitrange:
      x_from=self.x_from
      x_to=self.x_to
      if x_from is None:
        x_from=x.min()
      if x_to is None:
        x_to=x.max()
      filter_indices=numpy.where((x>=x_from)*(x<=x_to))[0]
      x=x[filter_indices]
    if interpolate>1:
      # Add interpolation points to x
      xint=[]
      dx=(x[1:]-x[:-1])/interpolate
      for j in range(interpolate):
        xint.append(x[:-1]+dx*j)
      xint=numpy.array(xint, dtype=numpy.float64).transpose().flatten()
      xint=numpy.append(xint, x[-1])
    else:
      xint=x
    dview.scatter('xint', xint)
    dview['self']=self
    dview.execute('y=self.fit_function(self.parameters, numpy.array(xint, dtype=numpy.float64, copy=False))')
    y=dview.gather('y')
    return xint, y

  def __call__(self, x):
    '''
      Calling the object returns the y values corresponding to the given x values.
    '''
    return self.simulate(x, interpolate=1)[1] # return y values

  def __add__(self, other):
    '''
      Define the addition of two FitFunction objects.
    '''
    return FitSum(self, other)

  def __mul__(self, other):
    '''
      Define the multiplication of two FitFunction objects.
    '''
    return FitMultiply(self, other)

  def _get_function_text(self):
    function_text=self.fit_function_text
    for i in range(len(self.parameters)):
      pname=self.parameter_names[i]
      while '['+pname in function_text:
        start_idx=function_text.index('['+pname)
        end_idx=function_text[start_idx:].index(']')+start_idx
        replacement=function_text[start_idx:end_idx+1]
        if abs(self.parameters[i])!=0.:
          pow_10=numpy.log10(abs(self.parameters[i]))
        else:
          pow_10=0
        try:
          digits=int(replacement.split('|')[1].rstrip(']'))
        except:
          digits=4
        pow_10i=int(pow_10)
        if pow_10i>(digits-1):
          function_text=function_text.replace(replacement, ("%%.%if·10^{%%i}"%(digits-1))%\
                                                (self.parameters[i]/10.**pow_10i, pow_10i))
        elif pow_10<0:
          if pow_10i==pow_10:
            pow_10i+=1
          function_text=function_text.replace(replacement, ("%%.%if·10^{%%i}"%(digits-1))%\
                                                (self.parameters[i]/10.**(pow_10i-1), (pow_10i-1)))
        else:
          function_text=function_text.replace(replacement, ("%%.%if"%(digits-1-pow_10i))%(self.parameters[i]))
    return function_text

  def __repr__(self):
    output="<"+self.__class__.__name__+"  "
    for i in range((len(self.parameters)+3)//4):
      if i>0:
        output+="\n "+" "*len(self.__class__.__name__)+"  "
      output+=" ".join([u"%-10.10s"%name for name in self.parameter_names[i*4:(i+1)*4]])
      output+="\n "+" "*len(self.__class__.__name__)+" "
      output+=" ".join([u"% .3e"%value for value in self.parameters[i*4:(i+1)*4]])
    output+=" >"
    return output

  fit_function_text_eval=property(_get_function_text)

class FitSum(FitFunction):
  '''
    Fit the Sum of two FitFunctions.
  '''

  func_len=(None, None)

  def __init__(self, func1, func2):
    '''
      Construct a sum of two functions to use for fit.
      
      :param funci: the functions to add together
    '''
    self.name=func1.name+' + '+func2.name
    self.parameters=func1.parameters+func2.parameters
    self.parameter_names=[name+'1' for name in func1.parameter_names]+[name+'2' for name in func2.parameter_names]
    self.refine_parameters=func1.refine_parameters+[index+len(func1.parameters) for index in func2.refine_parameters]
    function_text=func1.fit_function_text
    for i in range(len(func1.parameters)):
      function_text=function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    function_text=func2.fit_function_text
    for i in range(len(func2.parameters)):
      function_text=function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' + '+function_text
    self.func_len=(len(func1.parameters), len(func2.parameters))
    self.origin=(func1, func2)
    if func1.constrains is None:
      func1.constrains={}
    if func2.constrains is None:
      func2.constrains={}
    self.constrains=ConnectedDict(func1.constrains, func2.constrains, len(func1.parameters))
    self._plot_options=PlotOptions()

  def fit_function(self, p, x):
    '''
      Combine the functions by adding their values together.
    '''
    func1=self.origin[0].fit_function
    func2=self.origin[1].fit_function
    len1, ignore=self.func_len
    return func1(p[0:len1], x)+func2(p[len1:], x)

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
    if index<len(self.origin[0].parameters):
      self.origin[0].toggle_refine_parameter(action, index)
    else:
      self.origin[1].toggle_refine_parameter(action, index-len(self.origin[0].parameters))

class FitMultiply(FitFunction):
  '''
    Fit the Multiplication of two FitFunctions.
  '''

  func_len=(None, None)

  def __init__(self, func1, func2):
    '''
      Construct a sum of two functions to use for fit.
      
      :param funci: the functions to add together
    '''
    self.name=func1.name+' * '+func2.name
    self.parameters=func1.parameters+func2.parameters
    self.parameter_names=[name+'1' for name in func1.parameter_names]+[name+'2' for name in func2.parameter_names]
    self.refine_parameters=func1.refine_parameters+[index+len(func1.parameters) for index in func2.refine_parameters]
    function_text=func1.fit_function_text
    for i in range(len(func1.parameters)):
      function_text=function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    function_text=func2.fit_function_text
    for i in range(len(func2.parameters)):
      function_text=function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' * '+function_text
    self.func_len=(len(func1.parameters), len(func2.parameters))
    self.origin=(func1, func2)
    if func1.constrains is None:
      func1.constrains={}
    if func2.constrains is None:
      func2.constrains={}
    self.constrains=ConnectedDict(func1.constrains, func2.constrains, len(func1.parameters))
    self._plot_options=PlotOptions()

  def fit_function(self, p, x):
    '''
      Combine the functions by adding their values together.
    '''
    func1=self.origin[0].fit_function
    func2=self.origin[1].fit_function
    len1, ignore=self.func_len
    return func1(p[0:len1], x)*func2(p[len1:], x)

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
    if index<len(self.origin[0].parameters):
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
  parameter_description={}
  fit_function=lambda self, p, x, y: 0.
  fit_function_text='f(x,y)'
  last_fit_output=None
  x_from=None
  x_to=None
  y_from=None
  y_to=None
  is_3d=True
  fit_logarithmic=False
  constrains=None
  max_iter=200. # maximum numer of iterations for fitting (should be lowered for slow functions)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      # Use supplied parameters
      self.parameters=map(numpy.float64, initial_parameters)
    elif len(initial_parameters)==0:
      # Use std parameters
      self.parameters=map(numpy.float64, self.parameters)
    else:
      # Make sure a wrong number of parameters doesn't get silently ignored
      raise ValueError, "Wrong number of parameters, got %i need %i"%(len(initial_parameters), len(self.parameters))
    self.refine_parameters=range(len(self.parameters))
    if self.constrains is not None:
      self.constrains=dict(self.constrains)
    self._plot_options=PlotOptions()


  def residuals(self, params, z, y, x, zerror=None):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      :param params: Parameters for the function in this iteration
      :param z: List of z values measured
      :param y: List of y values for the measured points
      :param x: List of x values for the measured points
      :param yerror: List of error values for the y values or None if the fit is not weighted
      
      :return: Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    if zerror is None: # is error list given?
      err=function(function_parameters, x, y)-z
    else:
      err=(function(function_parameters, x, y)-z)/zerror
    return err

  def residuals_log(self, params, z, y, x, zerror=None):
    '''
      Function used by leastsq to compute the difference between the logarithms of the simulation and data.
      For normal functions this is just the difference between log(y) and log(simulation(x)) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
      
      :param params: Parameters for the function in this iteration
      :param y: List of y values measured
      :param x: List of x values for the measured points
      :param yerror: List of error values for the y values or None if the fit is not weighted
      
      :return: Residuals (meaning the value to be minimized) of the fit function and the measured data
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    function_parameters=[]
    for i in range(len(self.parameters)):
      if i in self.refine_parameters:
        function_parameters.append(params[self.refine_parameters.index(i)])
      else:
        function_parameters.append(self.parameters[i])
    remove_negative=numpy.where(z>0.)
    x=x[remove_negative]
    y=y[remove_negative]
    z=z[remove_negative]
    if zerror is not None:
      zerror=zerror[remove_negative]
      zerror=numpy.where((numpy.isinf(zerror))+(numpy.isnan(zerror))+(zerror<=0.), 1., zerror)
      # use error propagation for log(yi)
      propagated_error=zerror/z
      err=(numpy.log10(function(function_parameters, x, y))-numpy.log10(z))/propagated_error
    else:
      err=numpy.log10(function(function_parameters, x, y))-numpy.log10(z)
    return err

  def refine(self, dataset_x, dataset_y, dataset_z, dataset_zerror=None, progress_bar_update=None):
    '''
      Do the least square refinement to the given dataset. If the fit converges
      the new parameters are stored.
      
      :param dataset_x: list of x values from the dataset
      :param dataset_y: list of y values from the dataset
      :param dataset_z: list of z values from the dataset
      :param dataset_zerror: list of errors from the dataset or None for no weighting
      
      :return: The message string of leastsq and the covariance matrix
    '''
    parameters=[self.parameters[i] for i in self.refine_parameters]
    x=numpy.array(dataset_x, dtype=numpy.float64, copy=False)
    y=numpy.array(dataset_y, dtype=numpy.float64, copy=False)
    z=numpy.array(dataset_z, dtype=numpy.float64, copy=False)
    if dataset_zerror is not None:
      dz=numpy.array(dataset_zerror, dtype=numpy.float64, copy=False)
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
#    if dz is None:
#      fit_args=(z, y, x)
#    else:
#      fit_args=(z, y, x, dz)
    # remove errors which are zero
    if dz is not None:
      zero_elements=numpy.where(dz==0.)[0]
      non_zero_elements=numpy.where(dz!=0.)[0]
      dz[zero_elements]+=numpy.abs(dz[non_zero_elements]).min()
    if self.fit_logarithmic:
      residuals=self.residuals_log
    else:
      residuals=self.residuals
    return self.refine_mpfit(residuals, parameters, x, y, z, dz, progress_bar_update)

  def refine_mpfit(self, residuals, parameters, x, y, z, dz, progress_bar_update=None):
    '''
      Refine the function using a constrained fit with the 
      Sequential Least SQuares Programming algorithm.
      
      The constrains can be boundaries, equalitiy and inequality fuctions.
    '''
    constrains=self.constrains
    def function(p, fjac=None, x=None, y=None, z=None, dz=None):
      return [0, residuals(p, z, y, x, dz)]
    function_keywords={'x':x, 'y': y, 'z':z, 'dz': dz}
    # define constrains
    if constrains is None:
      parinfo=None
    else:
      parinfo=[]
      for i in range(len(parameters)):
        parinfo.append({'limited':[0, 0], 'limits':[0., 0.]})
        if self.refine_parameters[i] in constrains:
          constrains_i=constrains[self.refine_parameters[i]]
          parinfo_i=parinfo[i]
          if 'bounds' in constrains_i:
            for j in [0, 1]:
              if constrains_i['bounds'][j] is not None:
                parinfo_i['limited'][j]=1
                parinfo_i['limits'][j]=constrains_i['bounds'][j]
                if j==0 and parameters[i]<constrains_i['bounds'][j] or j==1 and parameters[i]>constrains_i['bounds'][j]:
                  parameters[i]=constrains_i['bounds'][j]
          if 'tied' in constrains_i:
            expression=constrains_i['tied']
            for j, pj in enumerate(self.refine_parameters):
              name=self.parameter_names[pj]
              expression=expression.replace('[%s]'%name, 'p[%i]'%j)
            test=expression.replace('p[', '').replace(']', '').replace(' ', '').replace('.', '')\
                .replace('*', '').replace('-', '').replace('/', '').replace('+', '')
            if not test.isdigit() and test!='':
              raise ValueError, 'Wrong syntax in constrains.'
            parinfo_i['tied']=expression
    if progress_bar_update is not None:
      def iterfunct(myfunct, p, iteration, fnorm, functkw=None,
                  parinfo=None, quiet=0, dof=None):
        # perform custom iteration update   
        return progress_bar_update(step_add=float(iteration)/self.max_iter,
                            info='Iteration %i    Chi²=%4f'%(iteration, fnorm))
    else:
      iterfunct=None
    # parallel version
    if parallel.dview is not None:
      dview=parallel.dview
      function_keywords={}
      dview.scatter('x', x)
      dview.scatter('y', y)
      dview.scatter('z', z)
      if dz is None:
        dview.execute('dz=None')
      else:
        dview.scatter('dz', dz)
      dview['self']=self
      if self.fit_logarithmic:
        def function(p, fjac=None, x=None, y=None, z=None, dz=None):
          dview['p']=p
          dview.execute('err=self.residuals_log(p,z,y,x,dz)')
          return [0, dview.gather('err')]
      else:
        def function(p, fjac=None, x=None, y=None, z=None, dz=None):
          dview['p']=p
          dview.execute('err=self.residuals(p,z,y,x,dz)')
          return [0, dview.gather('err')]
    # call the fit routine
    result=mpfit(function, xall=parameters, functkw=function_keywords,
                 parinfo=parinfo,
                 maxiter=self.max_iter, iterfunct=iterfunct,
                 fastnorm=1, # faster computation of Chi², can be less stable
                 quiet=1
                 )
    if result.status==-1:
      result.status=5
    self.last_fit_output=result
    if progress_bar_update is not None:
      progress_bar_update(step_add=1.)
    if result.status>0:
      # set the new parameters
      new_params=result.params
      new_function_parameters=[]
      for i in range(len(self.parameters)):
        if i in self.refine_parameters:
          new_function_parameters.append(new_params[self.refine_parameters.index(i)])
        else:
          new_function_parameters.append(self.parameters[i])
      self.set_parameters(new_function_parameters)
    # covariance matrix for all parameters
    cov=result.covar
    cov_out=[]
    for i in range(len(self.parameters)):
      cov_out.append([])
      for j in range(len(self.parameters)):
        if (cov is not None) and (i in self.refine_parameters) and (j in self.refine_parameters):
          cov_out[i].append(cov[self.refine_parameters.index(i)][self.refine_parameters.index(j)])
        else:
          cov_out[i].append(0.)
    mesg=result.errmsg
    if parallel.dview is not None:
      # free memory on remote processes
      dview.execute('del(x);del(y);del(z);del(err);del(dz)')
    return mesg, cov_out

  def set_parameters(self, new_params):
    '''
      Set new parameters and store old ones in history.
      
      :param new_params: List of new parameters
    '''
    self.parameters_history=self.parameters
    self.parameters=map(numpy.float64, new_params)

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
      
      :param x: List of x values to calculate the function for
      :param interpolate: Number of points to interpolate in between the x values
    
      :return: simulated y-values for a list of giver x-values.
    '''
    if parallel.dview is not None:
      return self.simulate_mp(y, x)
    try:
      x=numpy.array(x, dtype=numpy.float64, copy=False)
      y=numpy.array(y, dtype=numpy.float64, copy=False)
    except TypeError:
      raise TypeError, "Input needs to be a number or iterable not %s/%s"%(type(x), type(y))
    try:
      z=self.fit_function(self.parameters, x, y)
    except TypeError:
      raise TypeError, "Fit functions need to be defined for numpy arrays!"
    return x, y, z

  def simulate_mp(self, y, x):
    '''
      Multiprocessing version of simulate.
    '''
    dview=parallel.dview
    x=numpy.array(x, dtype=numpy.float64, copy=False)
    y=numpy.array(y, dtype=numpy.float64, copy=False)
    dview.scatter('x', x)
    dview.scatter('y', y)
    dview['self']=self
    dview.execute('z=self.fit_function(self.parameters, x, y)')
    z=dview.gather('z')
    return x, y, z

  def __call__(self, x, y):
    '''
      Calling the object returns the z values corresponding to the given x and y values.
    '''
    return self.simulate(y, x)[2] # return z values

  def __add__(self, other):
    '''
      Define the addition of two FitFunction objects.
    '''
    return FitSum3D(self, other)

  def __mul__(self, other):
    '''
      Define the multiplication of two FitFunction objects.
    '''
    return FitMultiply3D(self, other)

  def _get_function_text(self):
    function_text=self.fit_function_text
    for i in range(len(self.parameters)):
      pname=self.parameter_names[i]
      while '['+pname in function_text:
        start_idx=function_text.index('['+pname)
        end_idx=function_text[start_idx:].index(']')+start_idx
        replacement=function_text[start_idx:end_idx+1]
        if abs(self.parameters[i])!=0.:
          pow_10=numpy.log10(abs(self.parameters[i]))
        else:
          pow_10=0
        try:
          digits=int(replacement.split('|')[1].rstrip(']'))
        except:
          digits=4
        pow_10i=int(pow_10)
        if pow_10i>(digits-1):
          function_text=function_text.replace(replacement, ("%%.%if·10^{%%i}"%(digits-1))%\
                                                (self.parameters[i]/10.**pow_10i, pow_10i))
        elif pow_10<0:
          if pow_10i==pow_10:
            pow_10i+=1
          function_text=function_text.replace(replacement, ("%%.%if·10^{%%i}"%(digits-1))%\
                                                (self.parameters[i]/10.**(pow_10i-1), (pow_10i-1)))
        else:
          function_text=function_text.replace(replacement, ("%%.%if"%(digits-1-pow_10i))%(self.parameters[i]))
    return function_text

  def __repr__(self):
    output="<"+self.__class__.__name__+"  "
    for i in range((len(self.parameters)+3)//4):
      if i>0:
        output+="\n "+" "*len(self.__class__.__name__)+"  "
      output+=" ".join([u"%-10.10s"%name for name in self.parameter_names[i*4:(i+1)*4]])
      output+="\n "+" "*len(self.__class__.__name__)+" "
      output+=" ".join([u"% .3e"%value for value in self.parameters[i*4:(i+1)*4]])
    output+=" >"
    return output

  fit_function_text_eval=property(_get_function_text)

class FitSum3D(FitFunction3D):
  '''
    Fit the Sum of two FitFunctions3D.
  '''

  func_len=(None, None)

  def __init__(self, func1, func2):
    '''
      Construct a sum of two functions to use for fit.
      
      :param funci: the functions to add together
    '''
    self.name=func1.name+' + '+func2.name
    self.parameters=func1.parameters+func2.parameters
    self.parameter_names=[name+'1' for name in func1.parameter_names]+[name+'2' for name in func2.parameter_names]
    self.refine_parameters=func1.refine_parameters+[index+len(func1.parameters) for index in func2.refine_parameters]
    function_text=func1.fit_function_text
    for i in range(len(func1.parameters)):
      function_text=function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    function_text=func2.fit_function_text
    for i in range(len(func2.parameters)):
      function_text=function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' + '+function_text
    self.func_len=(len(func1.parameters), len(func2.parameters))
    self.origin=(func1, func2)
    if func1.constrains is None:
      func1.constrains={}
    if func2.constrains is None:
      func2.constrains={}
    self.constrains=ConnectedDict(func1.constrains, func2.constrains, len(func1.parameters))
    self._plot_options=PlotOptions()

  def fit_function(self, p, x, y):
    '''
      Combine the functions by adding their values together.
    '''
    func1=self.origin[0].fit_function
    func2=self.origin[1].fit_function
    len1, ignore=self.func_len
    return func1(p[0:len1], x, y)+func2(p[len1:], x, y)

  def set_parameters(self, new_params):
    '''
      Set new parameters and pass them to origin functions.
    '''
    FitFunction3D.set_parameters(self, new_params)
    index=len(self.origin[0].parameters)
    self.origin[0].set_parameters(self.parameters[:index])
    self.origin[1].set_parameters(self.parameters[index:])

  def toggle_refine_parameter(self, action, index):
    '''
      Change the refined parameters in the origin functions.
    '''
    FitFunction3D.toggle_refine_parameter(self, action, index)
    if index<len(self.origin[0].parameters):
      self.origin[0].toggle_refine_parameter(action, index)
    else:
      self.origin[1].toggle_refine_parameter(action, index-len(self.origin[0].parameters))

class FitMultiply3D(FitFunction3D):
  '''
    Fit the Multiplication of two FitFunctions3D.
  '''

  func_len=(None, None)

  def __init__(self, func1, func2):
    '''
      Construct a sum of two functions to use for fit.
      
      :param funci: the functions to add together
    '''
    self.name=func1.name+' * '+func2.name
    self.parameters=func1.parameters+func2.parameters
    self.parameter_names=[name+'1' for name in func1.parameter_names]+[name+'2' for name in func2.parameter_names]
    self.refine_parameters=func1.refine_parameters+[index+len(func1.parameters) for index in func2.refine_parameters]
    function_text=func1.fit_function_text
    for i in range(len(func1.parameters)):
      function_text=function_text.replace(func1.parameter_names[i], func1.parameter_names[i]+'1')
    self.fit_function_text=function_text
    function_text=func2.fit_function_text
    for i in range(len(func2.parameters)):
      function_text=function_text.replace(func2.parameter_names[i], func2.parameter_names[i]+'2')
    self.fit_function_text+=' * '+function_text
    self.func_len=(len(func1.parameters), len(func2.parameters))
    self.origin=(func1, func2)
    if func1.constrains is None:
      func1.constrains={}
    if func2.constrains is None:
      func2.constrains={}
    self.constrains=ConnectedDict(func1.constrains, func2.constrains, len(func1.parameters))
    self._plot_options=PlotOptions()

  def fit_function(self, p, x, y):
    '''
      Combine the functions by adding their values together.
    '''
    func1=self.origin[0].fit_function
    func2=self.origin[1].fit_function
    len1, ignore=self.func_len
    return func1(p[0:len1], x, y)*func2(p[len1:], x, y)

  def set_parameters(self, new_params):
    '''
      Set new parameters and pass them to origin functions.
    '''
    FitFunction3D.set_parameters(self, new_params)
    index=len(self.origin[0].parameters)
    self.origin[0].set_parameters(self.parameters[:index])
    self.origin[1].set_parameters(self.parameters[index:])

  def toggle_refine_parameter(self, action, index):
    '''
      Change the refined parameters in the origin functions.
    '''
    FitFunction3D.toggle_refine_parameter(self, action, index)
    if index<len(self.origin[0].parameters):
      self.origin[0].toggle_refine_parameter(action, index)
    else:
      self.origin[1].toggle_refine_parameter(action, index-len(self.origin[0].parameters))

#+++++++++++++++++++++++++++++++++ Define common functions for 2d fits +++++++++++++++++++++++++++++++++

class FitLinear(FitFunction):
  '''
    Fit a linear regression.
  '''

  # define class variables.
  name="Linear Regression"
  parameters=[1, 0]
  parameter_names=['a', 'b']
  parameter_description={'a': 'Slope', 'b': 'Offset'}
  fit_function=lambda self, p, x: p[0]*numpy.array(x)+p[1]
  fit_function_text='[a]·x + [b]'



class ThetaCorrection(FitFunction):
  '''
    Fit a function to peak positions to get a reciprocal lattice parameter and Θ-offset.
  '''

  # define class variables.
  name="Peak Positions"
  parameters=[3., 0.]
  parameter_names=['a*', 'Θ_0']
  parameter_description={'a*': 'Reciprocal Lattice Vector'}
  fit_function_text='a^*=[a*|6] [y-unit]    Θ_0=[Θ_0] °'
  lambda_factor=1.540/(4.*numpy.pi) # Cu-k_alpha prefactor

  def fit_function(self, p, x):
    '''
      Fit a function to the peak positions.
    '''
    a_star=p[0]
    theta0=p[1]/180.*numpy.pi
    # theoretical q positions q=h·a*
    q_theo=x*a_star
    th_theo=numpy.arctan(q_theo*self.lambda_factor)
    q_mess=q_theo+numpy.cos(th_theo)*numpy.sin(theta0)/self.lambda_factor
    return q_mess

class FitDiamagnetism(FitFunction):
  '''
    Fit two linear functions with the same slope, an offset and a hole around zero.
  '''

  # define class variables.
  name="Linear Asymptotes"
  parameters=[0, 0, 0, 1]
  parameter_names=['a', 'b', 'c', 'split']
  parameter_description={'a': 'Slope',
                         'b': 'Offset of left to right part',
                         'c': 'Constant offset value',
                         'split': 'Ignored region around 0'}
  fit_function_text='slope=[a]'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(3)

  def fit_function(self, p, x):
    '''
      Two linear functions with different offsets,
      split left and right from the y-axes.
    '''
    # create an array with True at every xposition which is outside the split region
    switch=(x<-abs(p[3]))+(x>abs(p[3]))
    output=numpy.where(switch, p[0]*x+numpy.sign(x)*p[1]+p[2], 0.)
    return switch*output

class FitQuadratic(FitFunction):
  '''
    Fit a quadratic function.
  '''

  # define class variables.
  name="Parabula"
  parameters=[1, 0, 0]
  parameter_names=['a', 'b', 'c']
  parameter_description={
                         'a': 'Coefficient of x²',
                         'b': 'Coefficient of x',
                         'c': 'Offset'
                         }
  fit_function=lambda self, p, x: p[0]*numpy.array(x)**2+p[1]*numpy.array(x)+p[2]
  fit_function_text='[a]·x^2 + [b]·x + [c]'

class FitPolynomialPowerlaw(FitFunction):
  '''
    Fit a quartic polynomial logarithmic function.
  '''

  # define class variables.
  name="Powerlaw with Polynom"
  parameters=[0., 0., 1., 0., 0.]
  parameter_names=['a', 'b', 'c', 'd', 'e']
  fit_function_text='exp([a]·x^4 + [b]·x^3 + [c]·x^2 + [d]·x + [e])'

  def fit_function(self, p, x):
    x=numpy.array(x)
    return 10.**(p[0]*x**4+p[1]*x**3+p[2]*x**2+p[3]*x+p[4])

  residuals=FitFunction.residuals_log

class FitSinus(FitFunction):
  '''
    Fit a sinus function.
  '''

  # define class variables.
  name="Sinus"
  parameters=[1., 1., 0., 0.]
  parameter_names=['a', 'ω0', 'φ0', 'c']
  parameter_description={'a': 'Prefactor',
                         'ω0': 'Frequency',
                         'φ0': 'Phase',
                         'c': 'Offset'}
  fit_function=lambda self, p, x: p[0]*numpy.sin((numpy.array(x)*p[1]-p[2])*numpy.pi/180.)+p[3]
  fit_function_text='[a]·sin([ω0|3]·x-[φ0|2])+[c]'

  def refine(self, dataset_x, dataset_y, dataset_yerror=None, progress_bar_update=None):
    '''
      Refine the function for given x and y data and set the φ0 value
      to be between -180° and 180°.
    '''
    output=FitFunction.refine(self, dataset_x, dataset_y, dataset_yerror)
    self.parameters[2]=(self.parameters[2]+180.)%360.-180.
    return output

class FitExponential(FitFunction):
  '''
    Fit a exponential function.
  '''

  # define class variables.
  name="Exponential"
  parameters=[1, 1, 0]
  parameter_names=['A', 'B', 'C']
  parameter_description={
                         'A': 'Prefactor',
                         'B': 'Exponential prefactor',
                         'C': 'Offset'
                         }
  fit_function=lambda self, p, x: p[0]*numpy.exp(p[1]*numpy.array(x))+p[2]
  fit_function_text='[A]·exp([B]·x) + [C]'

class FitOneOverX(FitFunction):
  '''
    Fit a one over x function.
  '''

  # define class variables.
  name="1/x"
  parameters=[1, 0, 0]
  parameter_names=['C', 'x0', 'D']
  parameter_description={
                         'C': 'Scaling',
                         'x0': 'x-offset',
                         'D': 'Offset'
                         }
  fit_function=lambda self, p, x: p[0]*1/(numpy.array(x)-p[1])+p[2]
  fit_function_text='[C]/(x-[x0|2]) + [D]'

class FitGaussian(FitFunction):
  '''
    Fit a gaussian function.
  '''

  # define class variables.
  name="Gaussian"
  parameters=[1, 0, 1, 0]
  parameter_names=['I', 'x0', 'σ', 'C']
  parameter_description={'I': 'Scaling',
                         'x0': 'Peak Position',
                         'σ': 'Variance',
                         'C':'Offset'}
  fit_function=lambda self, p, x: p[0]*numpy.exp(-0.5*((x-p[1])/p[2])**2)+p[3]
  fit_function_text='Gaussian: I=[I] x_0=[x0] σ=[σ|2]'

class FitLorentzian(FitFunction):
  '''
    Fit a lorentz function.
  '''

  # define class variables.
  name="Lorentzian"
  parameters=[1, 0, 1, 0]
  parameter_names=['I', 'x0', 'γ', 'C']
  parameter_description={'I': 'Scaling',
                        'x0': 'Peak Position',
                        'γ': 'Half Width Half Maximum',
                        'C':'Offset'}
  fit_function=lambda self, p, x: p[0]/(1+((numpy.array(x)-p[1])/p[2])**2)+p[3]
  fit_function_text='Lorentzian: I=[I] x_0=[x0] γ=[γ|2]'

class FitLorentzianAsymmetric(FitFunction):
  '''
    Fit a asymmetric lorentz function.
  '''

  # define class variables.
  name="Asymmetric Lorentzian"
  parameters=[1, 0, 1, 0, 0]
  parameter_names=['I', 'x0', 'γ', 'C', 'ν']
  parameter_description={'I': 'Scaling',
                        'x0': 'Peak Position',
                        'γ': 'Half Width Half Maximum',
                        'C':'Offset',
                        'ν': 'Asymmetry'}
  fit_function_text='Asymmetric Lorentzian: I=[I] x_0=[x0] γ=[γ|2]'

  def fit_function(self, p, x):
    I=p[0]
    x0=p[1]
    gamma=p[2]
    C=p[3]
    nu=p[4]
    gamma_asym=2.*gamma/(1+numpy.exp(nu*(x-x0)))
    L=I/(1+((x-x0)/gamma_asym)**2)+C
    return L

class FitVoigtAsymmetric(FitFunction):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''

  # define class variables.
  name="AsymmetricVoigt"
  parameters=[1, 0, 0.01, 0.01, 0, 0, 0]
  parameter_names=['I', 'x0', 'γ', 'σ', 'C', 'ν_γ', 'ν_σ']
  parameter_description={'I': 'Scaling',
                         'x0': 'Peak Position',
                         'σ': 'Gaussian Variance',
                         'γ': 'HWHM Lorentzian',
                         'C':'Offset',
                         'ν_γ': 'Asymmetry Lorentzian',
                         'ν_σ': 'Asymmetry Gaussian',
                         }
  fit_function_text='Asymmetric Voigt: I=[I] x_0=[x0] σ=[σ|2] γ=[γ|2]'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters=[]):
    '''
      Initialize and import scipy function.
    '''
    FitFunction.__init__(self, initial_parameters)

  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    from scipy.special import wofz
    I=p[0]
    x0=p[1]
    gamma=p[2]
    sigma=p[3]
    C=p[4]
    nu_gamma=p[5]
    nu_sigma=p[6]
    gamma_asym=2.*gamma/(1+numpy.exp(nu_gamma*(x-x0)))
    sigma_asym=2.*sigma/(1+numpy.exp(nu_sigma*(x-x0)))
    z=(x-x0+(abs(gamma_asym)*1j))/abs(sigma_asym)/self.sqrt2
    z0=(0.+(abs(gamma_asym)*1j))/abs(sigma_asym)/self.sqrt2
    value=I*wofz(z).real/wofz(z0).real+C
    return value

class FitVoigt(FitFunction):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''

  # define class variables.
  name="Voigt"
  parameters=[1, 0, 1, 1, 0]
  parameter_names=['I', 'x0', 'γ', 'σ', 'C']
  parameter_description={'I': 'Scaling',
                         'x0': 'Peak Position',
                         'σ': 'Gaussian Variance',
                         'γ': 'HWHM Lorentzian',
                         'C':'Offset'}
  fit_function_text='Voigt: I=[I] x_0=[x0] σ=[σ|2] γ=[γ|2]'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters=[]):
    '''
      Initialize and import scipy function.
    '''
    FitFunction.__init__(self, initial_parameters)


  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    from scipy.special import wofz
    x=numpy.float64(numpy.array(x))
    p=numpy.float64(numpy.array(p))
    z=(x-p[1]+(abs(p[2])*1j))/abs(p[3])/self.sqrt2
    z0=(0.+(abs(p[2])*1j))/abs(p[3])/self.sqrt2
    value=p[0]*wofz(z).real/wofz(z0).real+p[4]
    return value

class FitOffspecular(FitFunction):
  '''
    Fit the offspecular diffuse scattering from roughness.
  '''

  # define class variables.
  name="Offspecular"
  parameters=[1., 500., 0.3, 1.54, 2., 0., 0., 100., 0.01, 0.3]
  parameter_names=['I', 'ζ', 'H', 'λ', '2Θ', 'θ-offset', 'C',
                   'I-spec', 'σ-spec', 'αi-max']
  parameter_description={'I': 'Scaling of Off-specular part',
                         'ζ': 'Roughness correlation length',
                         'H': 'Hurst parameter defining the fractal dimension 0<H<1',
                         'λ': 'Used Wavelength',
                         '2Θ': 'Used 2Θ value',
                         'θ-offset': 'Miss-alignment of θ',
                         'C':'Offset',
                         'I-spec': 'Specular intensity',
                         'σ-spec': 'Width of the specular region',
                         'αi-max': 'Angle where the full beam is reflected by the sample',
                         }
  fit_function_text='Offspecular: I=[I] ζ=[ζ|2] H=[H|3]'

  def __init__(self, initial_parameters=[]):
    '''
      Initialize and import scipy function.
    '''
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=[0, 1, 5, 6, 7, 8]


  def fit_function(self, p, x):
    '''
      Return the Offspecular profile of th.
    '''
    pi=numpy.pi
    cos=numpy.cos
    I0=p[0]
    xi=p[1]
    H=p[2]
    lamda=p[3]
    tth=p[4]/180.*pi
    th_offset=p[5]/180.*pi
    C=p[6]

    I_spec=p[7]
    sigma_spec=p[8]/180.*pi
    ai_max=p[9]/180.*pi

    alpha_i=x/180.*pi
    alpha_f=tth-alpha_i
    Qx=2.*pi/lamda*(cos(alpha_f)-cos(alpha_i))
    Sxy=(1.+Qx**2*xi**2)**(-1.-H)
    Sspec=numpy.exp(-0.5*(tth/2.-alpha_i+th_offset)**2/sigma_spec**2)
    I=I0*abs(Sxy)**2+I_spec*Sspec
    return numpy.minimum(1., alpha_i/ai_max)*I+C

class FitCuK(FitFunction):
  '''
    Simulate Cu-Kα radiation for fitting θ-2θ scans of x-ray diffraction as douple
    peak (α1,α2) with two coupled voigt profiles.
  '''

  # define class variables.
  name="Cu K-radiation"
  parameters=[1000, 0, 0.00125, 0.001, 0, 2, 0.99752006]
  parameter_names=['I', 'x0', 'γ', 'σ', 'C', 'K_a1/K_a2', 'x01/x02']
  parameter_description={'I': 'Scaling', 'x0': 'Peak Position', 'σ': 'Gaussian Variance',
                          'γ': 'Lorentzian HWHM of each Peak',
                          'K_a1/K_a2': 'Intensity Ration of K_α1 to K_α2',
                          'x01/x02': 'Relative Peak position of K_α1 and K_α2',
                          'C':'Offset'}
  fit_function_text='K_α: I=[I] [y-unit]   x_0=[x0] [x-unit]   σ=[σ|2] [x-unit]'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=[0, 1, 3, 4]

  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    from scipy.special import wofz
    x=numpy.float64(numpy.array(x))
    p=numpy.float64(numpy.array(p))
    if p[1]<20:
      p2=p[1]/p[6]
    else:
      # if x0 is larger than 20 assume it is the th angle,
      # for smaller values it doesn't change a lot
      p2=asin(sin(p[1]*pi/180.)/p[6])/pi*180.
    z=(x-p[1]+(abs(p[2])*1j))/abs(p[3])/self.sqrt2
    z2=(x-p2+(abs(p[2])*1j))/abs(p[3])/self.sqrt2
    z0=(0.+(abs(p[2])*1j))/abs(p[3])/self.sqrt2
    value=p[0]*wofz(z).real/wofz(z0).real+p[4]
    value2=p[0]/p[5]*wofz(z2).real/wofz(z0).real+p[4]
    return value+value2


class FitCrystalLayer(FitFunction):
  '''
    Simulate diffraction from a crystal layer with finite size and roughness.
  '''

  # define class variables.
  name="CrystalLayer"
  parameters=[1., 100., 5., 2., 3.]
  parameter_description={'I': 'Scaling', 'd': 'Film Thickness',
                         'a': 'Film Crystal Parameter',
                          'σ': 'Roughness', 'h':'r.l.u.'}
  parameter_names=['I', 'd', 'a', 'h', 'σ']

  fit_function_text='d=[d] a=[a] σ=[σ|2]'

  def fit_function(self, p, x):
    '''
      Return the Voigt profile of x.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    x=numpy.array(x)
    I=p[0]
    d_0=p[1]
    a=p[2]
    h=p[3]
    sigma=p[4]
    a_star=2.*numpy.pi/a
    #d_star=2.*np.pi/d
    x_0=h*a_star
    if sigma!=0:
      d_range=numpy.linspace(d_0-3*sigma, d_0+3*sigma, 30)
      scalings=numpy.exp(-0.5*((d_range-d_0)/sigma)**2)
      scalings/=scalings.sum()
      A=numpy.zeros_like(x)
      for d, scaling in zip(d_range, scalings):
        A+=scaling*self.amplitude(x, x_0, d, a)
    else:
      A=self.amplitude(x, x_0, d_0, a)
    I_sim=A**2
    I_sim=I_sim/I_sim.max()
    result=I*I_sim
    return result

  def amplitude(self, x, x_0, d, a):
    '''
      Return the aplitude of a scattered wave on a crystal layer.
    '''
    sin=numpy.sin
    return sin(d/2.*(x-x_0))/(x-x_0)#sin(a/2.*(x-x_0))

class FitRelaxingCrystalLayer(FitFunction):
  '''
    Simulate diffraction from a crystal layer with relaxing lattice constant from top to bottom.
    In contrast to FitCrystalLayer this uses a purly numeric approach with sum of scattering layers.
    The strain is released with a exponential decaying function
  '''
  # define class variables.
  name="RelaxingCrystalLayer"
  parameters=[4.e5, 146., 6., 0., 5.76, 5.858, 200., 5.1765, 0.165, 0.0005, 0.5, 0.99752006, 1.]
  parameter_names=['I', # intensity (scaling factor)
                   'd', # layer thickness
                   'σ_layer', # layer roughness
                   'σ_substrate', # layer roughness
                   'a_bottom', # lattice parameter at the substrate interface
                   'a_infinity', # lattice parameter of bulk
                   'ε', # strain relaxation length of the lattice parameter
                   'a_substrate', # 
                   'scaling_substrate', # 
                   'μ', # absorption coefficient 
                   'I-Kα2', 'λ-Kα2', # Relative intensity and wavelength of Cu-Kα2
                   'BG', # Background
                   ]
  fit_function_text='d=[d] σ_{layer}=[σ_layer|2] a_{bottom}=[a_bottom|3] a_{inf}=[a_infinity|3]'

  def __init__(self, initial_parameters=[]):
    '''
      Constructor.
    '''
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(10)

  def fit_function(self, p, q):
    q=numpy.array(q, dtype=numpy.float64, copy=False)
    I_0=p[0]
    d=p[1]
    sigma_l=p[2]
    sigma_s=p[3]
    a_bottom=p[4]
    a_inf=p[5]
    epsilon=p[6]
    a_substrate=p[7]
    scaling_substrate=p[8]
    mu=p[9]
    I_alpha2=p[10]
    lambda_alpha2=p[11]
    background=p[12]
    if I_alpha2!=0:
      q=numpy.append(q, q*lambda_alpha2)
    # calculate some constants
    pi=numpy.pi
    ignore, plain_positions=self.get_strained_plains(a_bottom, a_inf, epsilon, d+3*sigma_l)
    # calculate scattering amplitude up to d-3sigma
    fixed_planes=plain_positions[numpy.where(plain_positions<d-3*sigma_l)]
    A=self.get_amplitude(fixed_planes, q, mu).sum(axis=0)
    # calculate the sum of amplitudes for the rough region
    if sigma_l!=0:
      roughness_planes=plain_positions[numpy.where(plain_positions>=d-3*sigma_l)]
      # caluclate gaussian scaling distribution
      scaling_factors=numpy.exp(-0.5*((roughness_planes-d)/sigma_l)**2)
      scaling_factors/=scaling_factors.sum()
      A_max_planes=self.get_amplitude(roughness_planes, q, mu)
      for i in range(len(scaling_factors)):
        # add amplitudes layer by layer
        A+=scaling_factors[i]*A_max_planes[:i+1].sum(axis=0)
    # substrate roughness is accounted for by multiplying the amplitudes with different offset phases
    A*=numpy.sqrt(I_0)*self.calculate_substrate_roughness(q, sigma_s)
    if a_substrate!=0:
      A_substrate=self.get_substrate_amplitude(q, a_substrate, mu)
      I=numpy.abs(A+numpy.sqrt(scaling_substrate)*A_substrate)**2
    else:
      I=numpy.abs(A)**2
    if I_alpha2!=0:
      items=len(q)/2
      I=(I[:items]+I_alpha2*I[items:])/(1.+I_alpha2)
    return I+background

  def get_strained_plains(self, a_bottom, a_inf, epsilon, d):
    '''
      Return an array of plane distances, exponentially decaying.
      The distances have to be calculated iteratively.
    '''
    plain_distances=[a_bottom]
    plain_positions=[0.]
    i=1
    a_dif=a_bottom-a_inf
    # until the layersize is reached, add a new plain.
    while (plain_positions[-1]<d):
      plain_distances.append(a_dif*exp(-plain_positions[-1]/epsilon)+a_inf)
      plain_positions.append(plain_positions[-1]+plain_distances[-1])
      i+=1
    return numpy.array(plain_distances), numpy.array(plain_positions)

  def get_amplitude(self, plane_positions, q, mu):
    '''
      Return the scattering amplitude from a set of layers.
      Uses a matrix of equal columns to compute for all q position at once.
    '''
    if len(plane_positions)>1:
      plane_multiplication_matrix, ignore=numpy.meshgrid(plane_positions, q)
      A=(numpy.exp(-mu*plane_positions)*numpy.exp(1j*q*plane_multiplication_matrix.transpose()).transpose()).transpose()
    elif len(plane_positions)==1:
      A=numpy.array([numpy.exp(1j*q*plane_positions[0])])
    else:
      return 0
    return A

  def calculate_substrate_roughness(self, q, sigma):
    '''
      Calculate a sum of amplitudes with different offset phases.
      As the phase factore e^{iqd} averedged over gaussian distributed
      offsets d is the fourier transform of the gaussian distribution
      this is again a simple gaussian function in q.
    '''
    if sigma!=0:
      #offsets=numpy.meshgrid(numpy.linspace(-3.*sigma, 3.*sigma, 31), q)[0]
      #offset_phases=numpy.exp(1j*q*offsets.transpose())
      #offset_factors=numpy.exp(-0.5*numpy.linspace(-3., 3., 31)**2)
      #offset_factors/=offset_factors.sum()
      #P=(offset_factors*offset_phases.transpose()).sum(axis=1)
      #prefactor=1./numpy.sqrt(numpy.pi*2.*sigma**2)
      P=numpy.exp(-(q*sigma)**2/2.)
    else:
      P=1.
    return P

  def get_substrate_amplitude(self, q, a_substrate, mu):
    '''
      Calculate the scattering amplitude of the substrate with a attenuation length of mu.
      As the real space structure is the product of the heaveside step function (u{x}), an exponential
      decay and the crystal structure the amplitude can be calculated as the convolution of
      delta functions with the fourier transform of the u{x}*exp(-ax)->F(q)=1./[sqrt(2π)·(a+iq)]
    '''
    a_star=2.*numpy.pi/a_substrate
    A_substrate=numpy.zeros_like(q).astype(numpy.complex)
    for i in range(1, 20):
      q_i=a_star*i
      #if q_i<=q.max() and q_i >= q.min():
      A_substrate+=1./(mu+1j*(q-q_i))
      #  print q_i
    return A_substrate


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
  parameters=[10, 1., 2.71, 1., 2.71 , 1., 3.01, 10. , 0.5, 1., 0.5, 2., 1.0, 0.01, 0.2, 6.]
  parameter_names=['M', 'I-A', 'x_0-A', 'I-B', 'x_0-B', 'I-subs.', 'x_0-subs.',
                    'D_{xA+(1-x)B}', 'x', 'δ_AB', 'σ_AB', 'ω_AB', 'a*', 'sigma', 'C', 'F_select']
  fit_function_text='(params)'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    self.parameters=[10, 1., 2.71, 1., 2.71 , 1., 3.01, 10. , 0.5, 1., 0.5, 2., 1.0, 0.01, 0.2, 6.]
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=[]
    self._parameter_dictionary={}
    self.rebuild_param_dictionary(self.parameters)

  def rebuild_param_dictionary(self, p):
    '''
      Create a dictionary of the parameters for better readability of all funcions.
      
      :param p: List of parameters to be used
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
      
      :param p: Parameters for the function
      :param q: Reciprocal lattice vector q
      
      :return: The calculated intensities for the selected structure factor + background
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
      
      :param I: Calculated intensity to convolute
      :param q: Reciprocal lattice vector q
      
      :return: Convoluted intensity
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
      
      :param q: Reciprocal lattice vector q
      :param I: Scaling factor
      :param q0: Position of the corresponding bragg peak
      :param t_j: Thickness of the layer
      
      :return: structure factor for this layer at the origin position.
    '''
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
      
      :param q: Reciprocal lattice vector q
      :param I: Scaling factor
      :param q0: Position of the corresponding bragg peak
      :param t_j: Thickness of the layer
      
      :return: structure factor for this layer at the origin position.
    '''
    d=(numpy.pi*2./q0)
    planes=int(t_j/d)
    F_layer=numpy.zeros_like(q)
    for i in range(planes):
      F_layer+=numpy.exp(1j*q*i*d)
    return numpy.sqrt(I)*F_layer#*numpy.exp(1j*q*(t_j/d-planes)*0.5)

  def calc_F_layer(self, q, I, q0, t_j):
    '''
      Calculate the structurefactor by summing up all unit cells in the region.
      
      :param q: Reciprocal lattice vector q
      :param I: Scaling factor
      :param q0: Position of the corresponding bragg peak
      :param t_j: Thickness of the layer
      
      :return: structure factor for this layer at the origin position.
    '''
    d=(numpy.pi*2./q0)
    planes=int(t_j/d)
    F_layer=(1.-numpy.exp(1j*q*(planes+1)*d))/(1.-numpy.exp(1j*q*d))
    return numpy.sqrt(I)*F_layer


  def calc_F_substrat(self, q):
    '''
      Calculate the structure factor of the substrate (crystal truncation rod at substrate peak position.
      
      :param q: Reciprocal lattice vector q
      
      :return: structure factor for the substrate
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

      :param q: Reciprocal lattice vector q
      
      :return: the complete Intensity of the multilayer without the substrate
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

      :param q: Reciprocal lattice vector q
      
      :return: the complete structure factor of the multilayer (without substrate)
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

      :param q: Reciprocal lattice vector q
      
      :return: the complete structure factor of the multilayer (without substrate)
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

      :param q: Reciprocal lattice vector q
      
      :return: the complete Intensity of the multilayer without the substrate
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
#    d_A=(numpy.pi*2./params['q0_A'])
#    d_B=(numpy.pi*2./params['q0_B'])
    # roughness parameter
    c=1./params['σ_AB']
#    a_avg=params['δ_AB']
    LAMBDA=t_A+t_B
    I=M*(abs(A)**2+abs(B)**2+2.*abs(A*B)*exp(-q**2/(4.*c**2))*cos(q*LAMBDA/2.))

    for m in range(1, M):
      I+=2.*(M-m)*((abs(A)**2+abs(B)**2)*exp(-2.*m*q**2/(4.*c**2))*cos(2.*m*q*LAMBDA/2.)+\
                    abs(A*B)*exp(-(2.*m+1)*q**2/(4.*c**2))*cos((2.*m+1)*q*LAMBDA/2.)+\
                    abs(A*B)*exp(-(2.*m-1)*q**2/(4.*c**2))*cos((2.*m-1)*q*LAMBDA/2.))

    return I

  def calc_I_ML_roughness(self, q):
    '''
      Calculate the structure factor for a superlattice including fluctuations and of the interface 
      distance roughness using eq(7)-eq(10) from E.E.Fullerton et al., PRB 45, No. 16 (1992).

      :param q: Reciprocal lattice vector q
      
      :return: the complete Intensity of the multilayer without the substrate
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
    I_1=2.*((exp(-psi)*Phi_B_avg*F_A_avg/(T_A*T_B)+\
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
      
      :return: offset position for every layer
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
      
      :return: deviation of thickness from -3ω to +3ω as numpy array
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
      
      :return: the propability for the jth deviation
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
      self.fit_function_text="%iXml: dA=%.2fÅ dB=%.2fÅ dS=%.2fÅ => tA=%iuc (+%.2g Å) tB=%iuc (+%.2g Å)"%(
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
      self.fit_function_text=self.fit_function_text.replace('(params)', "%iXml: dA=%.2fÅ dB=%.2fÅ dS=%.2fÅ => tA=%iuc (+%.2g Å) tB=%iuc (+%.2g Å)"%(
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

class FitInterpolation(FitFunction):
  '''
    Fit a spline interpolation to up to 6 points.
  '''

  # define class variables.
  name="Background Spline Interpolation"
  parameters=[0., 1., 1., 1., 2., 1., 3., 1., 0., 0., 0., 0.]
  parameter_names=['x_1', 'y_1', 'x_2', 'y_2', 'x_3', 'y_3', 'x_4', 'y_4', 'x_5', 'y_5', 'x_6', 'y_6']
  parameter_description=dict([('x_%i'%i, 'x-position of node %i'%i) for i in range(1, 7)]+\
                             [('y_%i'%i, 'y-value of node %i'%i) for i in range(1, 7)])
  fit_function_text='Spline'

  constrains={
              1: {'bounds': [0., None], 'tied': ''},
              3: {'bounds': [0., None], 'tied': ''},
              5: {'bounds': [0., None], 'tied': ''},
              7: {'bounds': [0., None], 'tied': ''},
              9: {'bounds': [0., None], 'tied': ''},
              11: {'bounds': [0., None], 'tied': ''},
              }

  def __init__(self, initial_parameters=[], method='cubic'):
    FitFunction.__init__(self, initial_parameters)
    from scipy.interpolate import interp1d
    self.interp=interp1d
    self.method=method
    self.refine_parameters=[i*2+1 for i in range(4)]

  def fit_function(self, p, x):
    '''
      Spline interpolate the different points.
    '''
    px=[p[i*2] for i in range(6)]
    py=[p[i*2+1] for i in range(6)]
    method=self.method
    for i in range(3, 6):
      if px[i]<=px[i-1]:
        px=px[:i]
        py=py[:i]
        if i==3 and method=='cubic':
          method='linear'
        break
    func=self.interp(numpy.array(px), numpy.array(py), kind=method, bounds_error=False, fill_value=0.)
    return func(x)

class FitSQUIDSignal(FitFunction):
  '''
    Fit three gaussians to SQUID raw data to calculate magnetic moments.
  '''
  prefactor=numpy.sqrt(2.*numpy.pi)
  #from config.squid import squid_coil_distance, squid_factor

  # define class variables.
  name="SQUID RAW-data"
  parameters=[1., 3., 1., 0., 0.]
  parameter_names=['Moment', 'x_0', 'sigma', 'off', 'incr']
  fit_function=lambda self, p, x: p[4]*numpy.array(x)-p[0]/(p[2]*self.squid_factor*self.prefactor)*(\
                                          numpy.exp(-0.5*((numpy.array(x)-p[1]+self.squid_coil_distance)/p[2])**2)\
                                          +numpy.exp(-0.5*((numpy.array(x)-p[1]-self.squid_coil_distance)/p[2])**2)\
                                          -2.* numpy.exp(-0.5*((numpy.array(x)-p[1])/p[2])**2) \
                                          )+p[3]
  fit_function_text='M=[Moment] ; pos=[x_0] ; s = [sigma]'

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
  parameter_names=['N', 'J', 'g', 'H', 'lambda', 'StartValue']
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
    print "End of function call %i, chi is now %.6g"%(self.iteration, sum(err))
    self.iteration+=1
    return err

  def refine(self, dataset_x, dataset_y, dataset_yerror=None, progress_bar_update=None):
    self.iteration=1
    return FitFunction.refine(self, dataset_x, dataset_y, dataset_yerror=None)

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
    from scipy.optimize import fsolve
    T=numpy.array(T)
    M=numpy.array([p[5] for ignore in range(len(T))])
    M, _info, _ier, mesg=fsolve(lambda Mi: Mi-self.brillouine(p, Mi, T), M, full_output=True)
    self.last_mesg=mesg
    return M

def B_J(p, x):
  '''
    Brillouine function of x.
  '''
  J=p[1]
  coth=lambda x: 1./numpy.tanh(x)
  return numpy.nan_to_num((2.*J+1.)/(2.*J)*coth((2.*J+1.)/(2.*J)*x)-1./(2.*J)*coth(1./(2.*J)*x))

class FitBrillouineB(FitFunction):
  '''
    Fit a Brillouine's function for the magnetic behaviour of a paramagnet
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
    FitFunction.__init__(self, initial_parameters)
    self.refine_parameters=range(4)

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
    Fit a Brillouine's function for the magnetic behaviour of a paramagnet
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



class FitNanoparticleZFC(FitFunction):
  '''
    Fit zero field cooled curves of Nanoparticles.
  '''
  # define class variables.
  name="NanoparticleZFC"
  parameters=[1.5e-5, 1., 1e9, 0.05, 10., 0.05, 0.]
  parameter_names=['3M_S²VB/kB', 'T/t', 'f_0', 'K_eff', 'r', 'δr', 'C']
  fit_function_text='Nanoparticle M_{ZFC}: K_{eff}=[K_eff|2] δr=[δr|2]'
  k_B=0.08617341 #meV∕K
  measured_M_FC=None

  def M(self, M_0, tau, t):
    return M_0*numpy.exp(-t/tau)

  def tau(self, E_B, T):
    return 1./(self.f_0*numpy.exp(-E_B/(self.k_B*T)))

  def M_ZFC(self, M_FC, T, T_per_t, E_B):
    M_out=[self.M_start]
    for i, M_FC_i in enumerate(M_FC):
      T_i=T[i]
      if i>0:
        delta_t=(T_i-T[i-1])/T_per_t
      else:
        delta_t=(T[1]-T[0])/T_per_t
      M_div=M_FC_i-M_out[-1]
      tau_i=self.tau(E_B, T_i)
      M_div_next=self.M(M_div, tau_i, delta_t)
      M_out.append(M_FC_i-M_div_next)
    return numpy.array(M_out[1:])

  def M_ZFC_dispersion(self, M_FC, T, T_per_t, K_eff, r, delta_r):
    M_ZFC_out=numpy.zeros_like(M_FC)
    delta_r_range=numpy.arange(-3.*delta_r, 3.*delta_r, delta_r/9.)
    P=P_i=numpy.exp(-0.5*(delta_r_range/delta_r)**2)
    P/=P.sum()
    for delta_r_i, P_i in zip(delta_r_range, P):
      r_i=r+delta_r_i
      E_B=K_eff*4./3.*numpy.pi*r_i**3
      M_ZFC_out+=P_i*self.M_ZFC(M_FC, T, T_per_t, E_B)
    return M_ZFC_out

  def fit_function(self, p, x):
    sort_idx=numpy.argsort(x)
    resort_idx=numpy.argsort(sort_idx)
    T=x[sort_idx]
    if self.measured_M_FC is None:
      M_FC=p[0]/T
    else:
      M_FC=self.measured_M_FC(T)
    T_per_t=p[1]/60.
    self.f_0=p[2]
    K_eff=p[3]
    r=p[4]
    delta_r=p[5]
    self.M_start=p[6]
    return self.M_ZFC_dispersion(M_FC, T, T_per_t, K_eff, r, delta_r)[resort_idx]

class FitNanoparticleZFC2(FitFunction):
  '''
    Fit zero field cooled curves of Nanoparticles.
  '''
  # define class variables.
  name="NanoparticleZFC2"
  parameters=[50., 10., 0.05, 0.]
  parameter_names=['T_B', 'r', 'δr', 'H_offset/H']
  fit_function_text='Nanoparticle M_{ZFC}: T_{Block}=[T_B|3] δr=[δr|2]'
  k_B=0.08617341 #meV∕K
  measured_M_FC=None

  def fit_function(self, p, x):
    '''
      Calculate the ZFC curve of a nanoparticle distribution.
    '''
    sort_idx=numpy.argsort(x)
    resort_idx=numpy.argsort(sort_idx)
    T=x[sort_idx]
    T_B=p[0]
    r=p[1]
    delta_r=p[2]
    H_factor=p[3]
    delta_r_array=numpy.arange(-3.*delta_r, 3.*delta_r, delta_r/numpy.float64(len(T)))
    r_array=r+delta_r_array
    V_array=4./3.*numpy.pi*r_array**3
    P_array=numpy.exp(-0.5*(delta_r_array/delta_r)**2)
    P_array/=P_array.sum()
    V_L_factor=T/T_B*(4./3.*numpy.pi*r**3)
    FC=self.measured_M_FC(T)
    FC_2=H_factor*FC
    M_ZFC=numpy.zeros_like(FC)
    for V_i, P_i in zip(V_array, P_array):
      M_ZFC+=P_i*numpy.where(V_i<=V_L_factor, FC, FC_2)
    return M_ZFC[resort_idx]

#--------------------------------- Define common functions for 2d fits ---------------------------------

#+++++++++++++++++++++++++++++++++ Define common functions for 3d fits +++++++++++++++++++++++++++++++++
class FitGaussian3D(FitFunction3D):
  '''
    Fit a gaussian function of x and y.
  '''

  # define class variables.
  name="Gaussian"
  parameters=[1., 0., 0., 0.1, 0.1, 0., 0.]
  parameter_names=['I', 'x_0', 'y_0', 'σ_x', 'σ_y', 'tilt', 'C']
  fit_function_text='Gaussian'
  parameter_description={'I': 'Scaling',
                         'x_0': 'Peak x-Position',
                         'y_0': 'Peak y-Position',
                         'σ_x': 'Variance in x-direction',
                         'σ_y': 'Variance in x-direction',
                         'tilt': 'Tilting angle of the data x-axis to the function x-axis',
                         'C':'Offset'}
  constrains={
              4: {'bounds': [None, None], 'tied': '[σ_x]'},
              #5: {'bounds': [-180., 180.], 'tied': ''},
              6: {'bounds': [0., None], 'tied': ''}
              }

  def __init__(self, initial_parameters=[]):
    FitFunction3D.__init__(self, initial_parameters)
    self.refine_parameters=[0, 1, 2, 3, 4, 6]

  def fit_function(self, p, x, y):
    A=p[0]
    x0=p[1]
    y0=p[2]
    sx=p[3]
    sy=p[4]
    p[5]=p[5]%180
    tilt=p[5]/180.*numpy.pi
    tb=numpy.sin(tilt)
    ta=numpy.cos(tilt)
    C=p[6]
    xdist=(numpy.array(x)-x0)
    ydist=(numpy.array(y)-y0)
    xdif=xdist*ta-ydist*tb
    ydif=xdist*tb+ydist*ta
    exp=numpy.exp
    return A*exp(-0.5*((xdif/sx)**2+((ydif/sy)**2)))+C

class FitPsdVoigt3D(FitFunction3D):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''

  # define class variables.
  name="Psd. Voigt"
  parameters=[1, 0, 0, 0.01, 0.01, 0.01, 0.01, 0., 0.5, 0.]
  parameter_names=['I', 'x_0', 'y_0', 'γ_x', 'γ_y', 'σ_x', 'σ_y', 'tilt', 'eta', 'C']
  parameter_description={'I': 'Scaling',
                         'x_0': 'Peak x-Position',
                         'y_0': 'Peak y-Position',
                         'σ_x': 'Gauss variance in x-direction',
                         'σ_y': 'Gauss variance in x-direction',
                         'γ_x': 'Lorentz HWHM in x-direction',
                         'γ_y': 'Lorentz HWHM in x-direction',
                         'tilt': 'Tilting angle of the data x-axis to the function x-axis',
                         'eta': 'Relative intensity of Lorentz',
                         'C':'Offset'}
  fit_function_text='Pseudo Voigt'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)
  constrains={
              4: {'bounds': [None, None], 'tied': '[γ_x]'},
              #7: {'bounds': [-180., 180.], 'tied': ''},
              8: {'bounds': [0., 1.], 'tied': ''},
              9: {'bounds': [0., None], 'tied': ''}
              }

  def fit_function(self, p, x, y):
    '''
      Return the 2d Voigt profile of x and y.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    I=p[0]
    x0=p[1]
    y0=p[2]
    gammax=p[3]
    gammay=p[4]
    sx=p[5]
    sy=p[6]
    p[7]=p[7]%180
    tilt=p[7]*numpy.pi/180.
    tb=numpy.sin(tilt)
    ta=numpy.cos(tilt)
    xdist=(numpy.array(x)-x0)
    ydist=(numpy.array(y)-y0)
    xdif=numpy.abs(xdist*ta-ydist*tb)
    ydif=numpy.abs(ydist*ta+xdist*tb)
    eta=p[8]
    c=p[9]
    G=numpy.exp(-numpy.log(2)*((xdif/sx)**2+(ydif/sy)**2))
    L=1./(1.+(xdif**2/gammax**2+ydif**2/gammay**2))
    value=I*((1.-eta)*G+eta*L)+c
    return value

class FitCuK3D(FitPsdVoigt3D):
  '''
    Simulate x-ray reciprocal space meshes measured with CuK radiation including 
    a measured wavelength distribution for the Bremsberg and other characteristic
    radiations.
  '''
  # define class variables.
  name="Mesh with Cu-Kα"
  fit_function_text='X-Ray simulation'

  def radiaion(self, x):
    '''
      Return the intensity of the x-ray radiaion for a wavelength 
    '''
    return numpy.where((x<1.2)*(x>0.5), 1., 0.)

  def fit_function(self, p, x, y):
    import scipy.signal
    import scipy.interpolate
    steps=int(numpy.sqrt(len(x)))
    region=[x.min(), x.max(), y.min(), y.max()]
    # Create a quadratic grid for the function simulation
    # this is needed to use the generic convolution function
    region_min=min([region[0], region[2]])
    region_max=max([region[1], region[3]])
    #region_length=region_max-region_min
    x_sim=numpy.linspace(region_min, region_max, steps)
    y_sim=numpy.linspace(region_min, region_max, steps)
    X_sim, Y_sim=numpy.meshgrid(x_sim, y_sim)
    Z_real=FitPsdVoigt3D.fit_function(self, p, X_sim, Y_sim)
    x_wave=numpy.linspace(region_min/p[1], region_max/p[1], steps)
    y_wave=numpy.linspace(region_min/p[2], region_max/p[2], steps)
    X_wave, Y_wave=numpy.meshgrid(x_wave, y_wave)
    Z_wave=numpy.zeros_like(Z_real)
    Z_wave=numpy.where(X_wave==Y_wave, self.radiaion(X_wave), Z_wave)
    Z_conv=scipy.signal.convolve2d(Z_real, Z_wave, mode='same')
    outf=scipy.interpolate.Rbf(X_sim.flatten(), Y_sim.flatten(), Z_conv.flatten(), function='linear')
    return outf(x, y)

class FitLorentzian3D(FitFunction3D):
  '''
    Fit a Lorentz function in x and y.
  '''

  # define class variables.
  name="Lorentzian"
  parameters=[1, 0, 0, 0.01, 0.01, 0., 0.]
  parameter_names=['I', 'x_0', 'y_0', 'γ_x', 'γ_y', 'tilt', 'C']
  parameter_description={'I': 'Scaling',
                         'x_0': 'Peak x-Position',
                         'y_0': 'Peak y-Position',
                         'γ_x': 'HWHM in x-direction',
                         'γ_y': 'HWHM in y-direction',
                         'tilt': 'Tilting angle of the data x-axis to the function x-axis',
                         'C':'Offset'}
  fit_function_text='Lorentzian'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)
  constrains={
              4: {'bounds': [None, None], 'tied': '[γ_x]'},
              #5: {'bounds': [-180., 180.], 'tied': ''},
              6: {'bounds': [0., None], 'tied': ''}
              }

  def fit_function(self, p, x, y):
    '''
      Return the 2d Voigt profile of x and y.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    x=numpy.array(x, copy=False, dtype=numpy.float64)
    y=numpy.array(y, copy=False, dtype=numpy.float64)
    p[5]=p[5]%180
    p=numpy.array(p, dtype=numpy.float64)
    I=p[0]
    x0=p[1]
    y0=p[2]
    gamma_x=p[3]
    gamma_y=p[4]
    tilt=p[5]*numpy.pi/180.
    ta=numpy.cos(tilt)
    tb=numpy.sin(tilt)
    xdist=(x-x0)
    ydist=(y-y0)
    xdif=numpy.abs(xdist*ta-ydist*tb)
    ydif=numpy.abs(ydist*ta+xdist*tb)
    c=p[6]
    L=1./(1.+(xdif/gamma_x)**2+(ydif/gamma_y)**2)
    value=I*L+c
    return value

class FitVoigt3D(FitFunction3D):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''

  # define class variables.
  name="Voigt"
  parameters=[1, 0, 0, 0.01, 0.01, 0.01, 0.01, 0.]
  parameter_names=['I', 'x_0', 'y_0', 'γ_x', 'γ_y', 'σ_x', 'σ_y', 'C']
  parameter_description={'I': 'Scaling',
                         'x_0': 'Peak x-Position',
                         'y_0': 'Peak y-Position',
                         'σ_x': 'Gauss variance in x-direction',
                         'σ_y': 'Gauss variance in x-direction',
                         'γ_x': 'Lorentz HWHM in x-direction',
                         'γ_y': 'Lorentz HWHM in x-direction',
                         'C':'Offset'}
  fit_function_text='Voigt'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    FitFunction3D.__init__(self, initial_parameters)

  def fit_function(self, p, x, y):
    '''
      Return the 2d Voigt profile of x and y.
      It is calculated using the complex error function,
      see Wikipedia articel on Voigt-profile for the details.
    '''
    from scipy import signal
    if x[1]!=x[0]:
      numx=list(x)[1:].index(x[0])+1
      numy=len(x)//numx
    else:
      numy=list(y)[1:].index(y[0])+1
      numx=len(y)//numy
    x=numpy.array(x).reshape(numy, numx)
    y=numpy.array(y).reshape(numy, numx)
    I=p[0]
    x0=p[1]
    y0=p[2]
    gamma_x=p[3]
    gamma_y=p[4]
    sigma_x=p[5]
    sigma_y=p[6]
    #xdist=x-x0
    #ydist=y-y0
    c=p[7]
    L=1./(1.+((x-x0)/gamma_x)**2+((y-y0)/gamma_y)**2)
    G=numpy.exp(-0.5*(((x-x.mean())/sigma_x)**2+((y-y.mean())/sigma_y)**2))
    # normalize Gaussian
    G/=G.sum()
    # convolute gauss and Lorentzian part using fft method
    V=signal.fftconvolve(L, G, mode='same')
    # normalize convolution
    V/=V.max()
    value=I*V+c
    return value.flatten()


#--------------------------------- Define common functions for 3d fits ---------------------------------

class FitSession(FitSessionGUI):
  '''
    Class used to fit a set of functions to a given measurement_data_structure.
    Provides the interface between the MeasurementData and the FitFunction.
  '''

  # class variables
  data=None
  # a dictionary of known fit functions for 2d datasets
  available_functions_2d={
                       FitLinear.name: FitLinear,
                       FitInterpolation.name: FitInterpolation,
                       #FitDiamagnetism.name: FitDiamagnetism, 
                       FitQuadratic.name: FitQuadratic,
                       FitSinus.name: FitSinus,
                       FitExponential.name: FitExponential,
                       FitGaussian.name: FitGaussian,
                       FitVoigt.name: FitVoigt,
                       FitOneOverX.name: FitOneOverX,
                       FitLorentzian.name: FitLorentzian,
                       FitVoigtAsymmetric.name: FitVoigtAsymmetric,
                       FitSQUIDSignal.name: FitSQUIDSignal,
                       FitBrillouineB.name: FitBrillouineB,
                       FitBrillouineT.name: FitBrillouineT,
                       FitFerromagnetic.name: FitFerromagnetic,
                       FitCuK.name: FitCuK,
                       FitPolynomialPowerlaw.name: FitPolynomialPowerlaw,
                       FitCrystalLayer.name: FitCrystalLayer,
                       FitRelaxingCrystalLayer.name: FitRelaxingCrystalLayer,
                       FitOffspecular.name: FitOffspecular,
                       #FitNanoparticleZFC.name: FitNanoparticleZFC, 
                       #FitNanoparticleZFC2.name: FitNanoparticleZFC2, 
                       }
  # known fit functions for 3d datasets
  available_functions_3d={
                       FitGaussian3D.name: FitGaussian3D,
                       FitPsdVoigt3D.name: FitPsdVoigt3D,
                       #FitCuK3D.name: FitCuK3D, 
                       FitVoigt3D.name: FitVoigt3D,
                       FitLorentzian3D.name: FitLorentzian3D,
                          }
  progress_bar=None

  def __init__(self, dataset):
    '''
      Constructor creating pointer to the dataset.
      
      :param dataset: A MeasurementData object
    '''
    self.functions=[] # a list of sequences (FitFunction, fit, plot, ignore errors) to be used
    self.data=dataset
    if dataset.zdata<0:
      self.data_is_3d=False
      self.available_functions=self.available_functions_2d
    else:
      self.data_is_3d=True
      self.available_functions=self.available_functions_3d
      self.fit=self.fit3d
      self.simulate=self.simulate3d
    self.show_covariance=False

  def __getstate__(self):
    '''
      Used to pickle the fit object, as the object has instance methods.
    '''
    dict_out=dict(self.__dict__)
    if self.data_is_3d:
      del(dict_out['fit'])
      del(dict_out['simulate'])
    return dict_out

  def __setstate__(self, dict_in):
    '''
      Reconstruct the object from dict.
    '''
    self.__dict__=dict_in
    if self.data_is_3d:
      self.fit=self.fit3d
      self.simulate=self.simulate3d

  def __getitem__(self, item):
    '''
      Return the fit object at position item.
      
      :return: FitData object or derived class
    '''
    return self.functions[item][0]

  def add_function(self, function_name):
    '''
      Add a function to the list of fitted functions.
    '''
    if function_name in self.available_functions:
      self.functions.append([self.available_functions[function_name]([]), True, True, False])
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
    funcs=self.available_functions.items()
    funcs=[l[0] for l in funcs]
    funcs.sort()
    return funcs

  def sum(self, index_1, index_2): #@ReservedAssignment
    '''
      Create a sum of the functions with index 1 and 2.
      Function 1 and 2 are set not to be fitted.
    '''
    functions=self.functions
    if (index_1<len(functions)) and (index_2<len(functions)):
      if functions[index_1][0].is_3d:
        Sum=FitSum3D
        functions[index_1][2]=False
        functions[index_2][2]=False
      else:
          Sum=FitSum
      functions.append([Sum(functions[index_1][0], functions[index_2][0]), True, True, False])
      functions[index_1][1]=False
      functions[index_2][1]=False

  def multiply(self, index_1, index_2):
    '''
      Create a multiplication of the functions with index 1 and 2.
      Function 1 and 2 are set not to be fitted.
    '''
    functions=self.functions
    if (index_1<len(functions)) and (index_2<len(functions)):
      if functions[index_1][0].is_3d:
        Mul=FitMultiply3D
        functions[index_1][2]=False
        functions[index_2][2]=False
      else:
          Mul=FitMultiply
      functions.append([Mul(functions[index_1][0], functions[index_2][0]), True, True, False])
      functions[index_1][1]=False
      functions[index_2][1]=False

  def fit(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
      
      :return: The covariance matrices of the fits or [[None]]
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
    for i, function in enumerate(self.functions):
      pgu=None
      self._stop_refinement=False
      if self.progress_bar is not None:
        self.update_progress(item=[i+1, len(self.functions)])
        pgu=self.update_progress
      if function[1]:
        if not function[3]:
          _mesg, cov_out=function[0].refine(data_x, data_y, data_yerror, progress_bar_update=pgu)
        else:
          _mesg, cov_out=function[0].refine(data_x, data_y, None, progress_bar_update=pgu)
        covariance_matices.append(cov_out)
      else:
        covariance_matices.append([[None]])
    return covariance_matices

  def fit3d(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
      
      :return: The covariance matrices of the fits or [[None]]
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
    for i, function in enumerate(self.functions):
      pgu=None
      self._stop_refinement=False
      if self.progress_bar is not None:
        self.update_progress(item=[i+1, len(self.functions)])
        pgu=self.update_progress
      if function[1]:
        if not function[3]:
          _mesg, cov_out=function[0].refine(data_x, data_y, data_z, data_zerror, progress_bar_update=pgu)
        else:
          _mesg, cov_out=function[0].refine(data_x, data_y, data_z, None, progress_bar_update=pgu)
        covariance_matices.append(cov_out)
      else:
        covariance_matices.append([[None]])
    return covariance_matices

  def simulate3d(self):
    '''
      Create MeasurementData objects for every FitFunction.
    '''
    self.result_data=[]
    data=self.data
    dimensions=data.dimensions()
    units=data.units()
    column_1=(dimensions[self.data.xdata], units[self.data.xdata])
    column_2=(dimensions[self.data.ydata], units[self.data.ydata])
    column_3=(dimensions[self.data.zdata], units[self.data.zdata])
    plot_list=[]
    if len(self.functions)>1 and \
        all([self.functions[0][0].__class__ is function[0].__class__ for function in self.functions]):
      fit=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
      fit.data[0]=data.x.copy()
      fit.data[1]=data.y.copy()
      fit.data[2]=numpy.zeros_like(data.z)
      function_text=function[0].fit_function_text
      fit.short_info=function_text
      if any([function[1] for function in self.functions]):
        div=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
        logdiv=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
        div.data[0]=data.x
        div.data[1]=data.y
        div.data[2]=data.z.copy()
        logdiv.data[0]=data.x
        logdiv.data[1]=data.y
        logdiv.data[2]=numpy.log10(data.z)
        div.plot_options=data.plot_options
        logdiv.plot_options=data.plot_options
        div.short_info='data-%s'%function_text
        logdiv.short_info='log(data)-log(%s)'%function_text
      fit.plot_options=data.plot_options
      for function in self.functions:
        fd=function[0](data.x, data.y)
        fit.z+=fd
        if any([function[1] for function in self.functions]):
          div.z-=fd
          logdiv.z-=numpy.log10(fd)
      if any([function[1] for function in self.functions]):
        logdiv.z=10.**logdiv.z
        plot_list=[fit, div, logdiv]
      else:
        plot_list=[fit]
      if getattr(data, 'is_matrix_data', False):
        fit.is_matrix_data=True
        div.is_matrix_data=True
        logdiv.is_matrix_data=True
    else:
      for function in self.functions:
        fit=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
        div=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
        logdiv=data.__class__([column_1, column_2, column_3], # columns
                                                [], # const_columns
                                                0, # x-column
                                                1, # y-column
                                                -1, # yerror-column
                                                2   # z-column
                                                )
        self.result_data.append(fit)
        fit.plot_options=data.plot_options
        div.plot_options=data.plot_options
        logdiv.plot_options=data.plot_options
        _result=self.result_data[-1]
        if function[2]:
          fit.data[0]=data.x
          fit.data[1]=data.y
          div.data[0]=data.x
          div.data[1]=data.y
          logdiv.data[0]=data.x
          logdiv.data[1]=data.y
          fd=function[0](data.x, data.y)
          fit.data[2].values=fd
          div.data[2].values=data.z-fd
          logdiv.data[2].values=10.**(numpy.log10(data.z)-numpy.log10(fd))
          function_text=function[0].fit_function_text_eval
          fit.short_info=function_text
          div.short_info='data-%s'%function_text
          logdiv.short_info='log(data)-log(%s)'%function_text
          plot_list.append(fit)
          if function[1]:
            # show differences only when fitting
            plot_list.append(div)
            plot_list.append(logdiv)
    self.data.plot_together=[self.data]+plot_list
    if len(plot_list)>0:
      self.data.plot_together_zindex=-1

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
        # only interpolate if the number of points isn't too large
        use_interpolate=min(5, 5000/len(data_x))
        fit_x, fit_y=function[0].simulate(data_x, inside_fitrange=getattr(self, 'restrict_to_region', False),
                                          interpolate=use_interpolate)
        for i in range(len(fit_x)):
          result.append((fit_x[i], fit_y[i]))
        function_text=function[0].fit_function_text_eval
        result.short_info=function_text
        result.plot_options=function[0]._plot_options
        plot_list.append(result)
    self.data.plot_together=[self.data]+plot_list

def register_class(function_class):
  '''
    Convenience method to add a new FitFunction derived class to the list of fittables.
  '''
  if function_class.is_3d:
    FitSession.available_functions_3d[function_class.name]=function_class
  else:
    FitSession.available_functions_2d[function_class.name]=function_class

def register_function(function, function_parameter_names=None, function_parameter_default=None, function_name=None):
  '''
    Convenience method to add a new fittable function.
    
    :param function: The function to be fitted as f(p,x) or f(p,x,y) with p as list of parameters
    :param function_parameter_names: Names of the parameters supplied to the function as p
    :param function_parameter_default: Default values of the parameters when the function is first created
    :param function_name: Name of the function
  '''
  import inspect
  numargs=len(inspect.getargspec(function)[0])
  if function_parameter_names is None:
    if function_parameter_default is not None:
      function_parameter_names=["P%02i"%i for i in range(len(function_parameter_default))]
    else:
      # try to guess parameter numbers
      if numargs==2:
        position=[1.]
      else:
        position=[1., 1.]
      for i in range(99):
        try:
          _out=function(*([range(i)]+position))
          function_parameter_names=["P%02i"%i for i in range(i)]
          break
        except IndexError:
          continue
  if function_parameter_default is None:
    function_parameter_default=[0. for i in range(len(function_parameter_names))]
  if function_name is None:
    function_name=function.__name__
  if numargs==2:
    class function_class(FitFunction):
      '''
        User defined FitFunction subclass named: %s
      '''%function_name
      name=function_name
      fit_function_text=function_name+":"+" ".join(["%s=[%s]"%(param, param) for param in function_parameter_names])
      parameters=list(function_parameter_default)
      parameter_names=list(function_parameter_names)

      def fit_function(self, p, x):
        return function(p, x)
  else:
    class function_class(FitFunction3D):
      '''
        User defined FitFunction3D subclass named: %s
      '''%function_name
      name=function_name
      fit_function_text=function_name+":"+" ".join(["%s=[%s]"%(param, param) for param in function_parameter_names])
      parameters=list(function_parameter_default)
      parameter_names=list(function_parameter_names)

      def fit_function(self, p, x, y):
        return function(p, x, y)
  register_class(function_class)