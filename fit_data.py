#!/usr/bin/env python
''' 
  Module containing a class for nonlinear fitting, 
  a root class for a fit function and several child classes with optimized common fit functions.
  Can in principal be used for any python function which returns floats or an array of floats.
'''

# import mathematic functions and least square fit which uses the Levenberg-Marquardt algorithm.
import numpy
from scipy.optimize import leastsq
from scipy.special import wofz
from math import pi, sqrt
from measurement_data_structure import MeasurementData
# for dialog window import gtk
import gtk

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

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

  def residuals(self, params, y, x, yerror=None):
    '''
      Function used by leastsq to compute the difference between the simulation and data.
      For normal functions this is just the difference between y and simulation(x) but
      can be overwritten e.g. to increase speed or fit to log(x).
      If the dataset has yerror values they are used as weight.
    '''
    # function is called len(x) times, this is just to speed up the lookup procedure
    function=self.fit_function
    if yerror==None: # is error list given?
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=y-function(params, x)
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: y[x.index(x_i)]-function(params, x_i)), x)
      return err
    else:
      # if function is defined for arrays (e.g. numpy) use this functionality
      try:
        err=(y-function(params, x))/yerror
      except TypeError:
        # x and y are lists and the function is only defined for one point.
        err= map((lambda x_i: (y[x.index(x_i)]-function(params, x_i))/yerror[x.index(x_i)]), x)
      return err      
  
  def refine(self,  dataset_x,  dataset_y, dataset_yerror=None):
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
    '''
      Set new parameters and store old ones in history.
    '''
    self.parameters_history=self.parameters
    self.parameters=list(new_params)

  
  def simulate(self, x, interpolate=5):
    '''
      Return simulated y-values for a list of giver x-values.
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
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0]


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
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0, 0]

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
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0, 0]

class FitGaussian(FitFunction):
  '''
    Fit a gaussian function.
  '''
  
  # define class variables.
  name="Gaussian"
  parameters=[1, 0, 1]
  parameter_names=['A', 'x_0', 'sigma']
  fit_function=lambda self, p, x: p[0] * numpy.exp(-0.5*((numpy.array(x) - p[1])/p[2])**2)
  fit_function_text='A*exp(-0.5*(x-x_0)/sigma)'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0, 1]

class FitLorentzian(FitFunction):
  '''
    Fit a lorentz function.
  '''
  
  # define class variables.
  name="Lorentzian"
  parameters=[1, 0, 1]
  parameter_names=['I', 'x_0', 'gamma' ]
  fit_function=lambda self, p, x: p[0] / (1 + ((numpy.array(x)-p[1])/p[2])**2)
  fit_function_text='A/(1 + ((x-x_0)/gamma)^2)'

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0, 1]

class FitVoigt(FitFunction):
  '''
    Fit a voigt function using the representation as real part of the complex error function.
  '''
  
  # define class variables.
  name="Voigt"
  parameters=[1, 0, 1, 1]
  parameter_names=['I', 'x_0', 'gamma', 'sigma']
  fit_function_text='I * Re(w(z))/Re(w(z_0)); w=(x-x_0)/sigma/sqrt(2)'
  sqrt2=numpy.sqrt(2)
  sqrt2pi=numpy.sqrt(2*numpy.pi)

  def __init__(self, initial_parameters):
    '''
      Constructor setting the initial values of the parameters.
    '''
    if len(self.parameters)==len(initial_parameters):
      self.parameters=initial_parameters
    else:
      self.parameters=[1, 0, 1, 1]
  
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
    value=p[0] * wofz(z).real / wofz(z0).real
    return value


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
                       FitLorentzian.name: FitLorentzian
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
      functions.append([FitSum(functions[index_1][0], functions[index_2][0]), True, True])
      functions[index_1][1]=False
      functions[index_2][1]=False
  
  def fit(self):
    '''
      Fit all funcions in the list where the fit parameter is set to True.
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
    for function in self.functions:
      if function[1]:
        function[0].refine(data_x, data_y, data_yerror)

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
      Return a dialog widget for the interaction with this class.
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
      text=gtk.Label(function[0].fit_function_text)
      align_table.attach(text,
                  # X direction #          # Y direction
                  4, 5,                      i*2, i*2+1,
                  gtk.EXPAND,     gtk.EXPAND,
                  0,                         0);
      new_line, entry=self.function_line(function[0], dialog, window)
      entries.append(entry)
      align_table.attach(new_line,
                  # X direction #          # Y direction
                  4, 5,                      i*2+1, i*2+2,
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
    align_table.attach(add_button,
                # X direction #          # Y direction
                0, 1,                      len(self.functions)*2+1, len(self.functions)*2+2,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    sum_button=gtk.Button(label='Combine')
    align_table.attach(sum_button,
                # X direction #          # Y direction
                1, 2,                       len(self.functions)*2+1, len(self.functions)*2+2,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    fit_button=gtk.Button(label='Fit and Replot')
    align_table.attach(fit_button,
                # X direction #          # Y direction
                2, 4,                      len(self.functions)*2, len(self.functions)*2+2,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    align_table.attach(new_function,
                # X direction #          # Y direction
                0, 2,                      len(self.functions)*2, len(self.functions)*2+1,
                gtk.EXPAND,     gtk.EXPAND,
                0,                         0);
    # connect the window signals to the handling methods
    add_button.connect('clicked', self.add_function_dialog, new_function, dialog, window)
    sum_button.connect('clicked', self.combine_dialog, dialog, window)
    fit_button.connect('clicked', self.fit_from_dialog, entries, dialog, window)
    align=gtk.Alignment(0.5, 0.5, 0, 0) # the table is centered in the dialog window
    align.add(align_table)
    return align
  
  def function_line(self, function, dialog, window):
    '''
      Create the widgets for one function and return a table of these.
      The entry widgets are returned in a list to be able to read them.
    '''
    table=gtk.Table(len(function.parameters)*2+1, 1, False)
    entries=[]
    for i, parameter in enumerate(function.parameters):
      text=gtk.Label(function.parameter_names[i])
      entries.append(gtk.Entry())
      entries[i].set_width_chars(8)
      entries[i].set_text("%.6g" % parameter)
      table.attach(text, i*2, i*2+1, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
      table.attach(entries[i], i*2+1, i*2+2, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    del_button=gtk.Button(label='DEL')
    table.attach(del_button, len(function.parameters)*2, len(function.parameters)*2+1, 0, 1, gtk.EXPAND, gtk.EXPAND, 0, 0)
    del_button.connect('clicked', self.del_function_dialog, function, dialog, window)
    return table, entries

  def add_function_dialog(self, action, name, dialog, window):
    '''
      Add a function via dialog access.
      Standart parameters are used.
    '''
    self.add_function(name.get_active_text())
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def del_function_dialog(self, action, function, dialog, window):
    '''
      Delete a function via dialog access.
    '''
    self.del_function(function)
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.fit_dialog(None, size, position)
  
  def fit_from_dialog(self, action, entries, dialog, window):
    '''
      Trigger the fit, simulation and replot functions.
    '''
    # TODO: Go back in history after fit.
    for i, function in enumerate(self.functions):
      for j,  entry in enumerate(entries[i]):
        function[0].parameters[j]=float(entry.get_text().replace(',', '.'))
    self.fit()
    self.simulate()
    size=dialog.get_size()
    position=dialog.get_position()
    dialog.destroy()
    window.replot()
    window.fit_dialog(None, size, position)

  def combine_dialog(self, action, dialog, window):
    '''
      A dialog window to combine two fit functions.
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
    combine_dialog.add_button('Add: a(b)',3)
    combine_dialog.add_button('Cancel',1)
    combine_dialog.show_all()
    result=combine_dialog.run()
    selected=[int(function_1.get_active_text().split(':')[0]), int(function_2.get_active_text().split(':')[0])]
    if result in [2, 3]:
      if result==2:
        self.sum(selected[0], selected[1])
        size=dialog.get_size()
        position=dialog.get_position()
        dialog.destroy()
        window.fit_dialog(None, size, position)
    combine_dialog.destroy()

  #------------------------- methods for GUI dialog ---------------------
