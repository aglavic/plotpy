# -*- encoding: utf-8 -*-
'''
  class for squid data sessions
'''
#################################################################################################
#                     Script to plot SQUID-measurements with gnuplot                            #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
# Features at the moment:                                                                       #
# -import mpms and ppms .dat, splitted by sequences                                             #
# -convert units to SI (or any selected)                                                        #
# -remove diamagnetic and paramagnetic contribution                                             #
#  (as constant and calculated from elements and mass)                                          #
# -process raw data files (sequence splitting see config.squid.py)                              #
#                                                                                               #
#################################################################################################

import sys
try:
  import scipy.interpolate
except ImportError:
  # for py2exe fix import problem
  import scipy
  from scipy.misc.common import factorial
  scipy.factorial=factorial
  import scipy.interpolate
import numpy

# import GenericSession, which is the parent class for the SquidSession
from generic import GenericSession
from measurement_data_structure import PhysicalConstant
# importing preferences and data readout
import read_data.squid
import config.squid
import config.diamagnetism_table
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.squid', fromlist=['SquidGUI']).SquidGUI
except ImportError: 
  class GUI: pass


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.9.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SquidSession(GUI, GenericSession):
  '''
    Class to handle squid data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tSQUID-Data treatment:
\t-para [C] [off]\tInclude paramagnetic correction factor (C/(T-off)) [emu*K/Oe]
\t-dia [Chi]\tInclude diamagnetic correction in [10^-9 emu/Oe]

Data columns and unit transformations are defined in config.squid.py.
'''
  # TODO: implement this.
  '''
  \t-dia-calc [e] [m]\tAdd diamagnetic correction of sample containing elements e
  \t\t\t\t with complete mass m in mg. 
  \t\t\t\t e is given for example as 'La_1-Fe_2-O_4','la_1-fe2+_2-o_4' or 'La-Fe_2-O_4'.
  '''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('SQUID/PPMS','*.[Dd][Aa][Tt]', '*.[Rr][Aa][Ww]','*.[Dd][Aa][Tt].gz', '*.[Rr][Aa][Ww].gz'), 
                  ]
  # options:
  dia_mag_correct=0. # diamagnetic correction factor
  dia_calc=[False, '', 0.0] # chemical formular and mass to calculate the correction
  dia_mag_offset=0. # user offset of diamagnetic correction factor
  para=[0, 0] # paramagnetic correction factor and T-offset
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['dia', 'dia-calc', 'para']
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.COLUMNS_MAPPING=config.squid.COLUMNS_MAPPING
    self.MEASUREMENT_TYPES=config.squid.MEASUREMENT_TYPES
    self.TRANSFORMATIONS=config.squid.TRANSFORMATIONS
    GenericSession.__init__(self, arguments)
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='dia':
          self.dia_mag_offset=float(argument)/1e9
          last_argument_option=[False,'']
        elif last_argument_option[1]=='dia-calc':
          self.dia_calc[0]=True
          self.dia_calc[1]=argument
          last_argument_option=[True,'dia-calc2']
        elif last_argument_option[1]=='dia-calc2':
          self.dia_calc[2]=float(argument)/1e3
          last_argument_option=[False,'']
        elif last_argument_option[1]=='para':
          self.para[0]=float(argument)/1e9
          last_argument_option=[True,'para2']
        elif last_argument_option[1]=='para2':
          self.para[1]=float(argument)
          last_argument_option=[False,'']
        else:
          found=False
      #elif argument=='-l':
      #  list_all=True
      #elif argument=='-ls':
      #  list_sequences=True
      #elif argument=='-sc':
      #  select_columns=True
      #elif argument=='-st':
      #  select_type=True
      #elif argument=='-sxy':
      #  select_xy=True
      #elif argument=='-calib-long':
      #  calib_long=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      function to read data files
    '''
    return read_data.squid.read_data(file_name ,self.COLUMNS_MAPPING,self.MEASUREMENT_TYPES)
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to GenericSession dia and paramagnetic
      corrections are performed here, too.
    '''
    datasets=GenericSession.add_file(self, filename, append)
    self.calc_dia()
    # faster lookup
    correct=(self.dia_mag_correct!=0 or self.para[0]!=0)
    for dataset in datasets:
      units=dataset.units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia=dia*1e4
        para=para*1e4
      if 'A·m^2' in units:
        dia=dia/1e3
        para=para/1e3
      if correct:
        dia=PhysicalConstant(dia, 'A·m^2/T')
        para=PhysicalConstant(para, 'K·A·m^2/T')
        self.dia_para_correction(dataset, dia, para)
      # name the dataset
      constant, unit=dataset.unit_trans_one(dataset.type(),config.squid.TRANSFORMATIONS_CONST)      
      if dataset.short_info=='':
        unit=unit or dataset.units()[dataset.type()]
        dataset.short_info='at %d ' % constant + unit # set short info as the value of the constant column
    return datasets


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
  
  def dia_para_correction(self, dataset, dia, para):
    '''
      Calculate dia- and paramagnetic correction for the given dataset.
      A new collumn is created for the corrected data and the old data
      stays unchanged.
    '''
    # TODO: The fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    temp=2
    mag=3
    units=dataset.units()
    dims=dataset.dimensions()
    first=True
    for i, unit in reversed(tuple(enumerate(units))):
      if unit in ['A·m^2', 'emu']:
        mag=i
      if unit in ['K', '°C']:
        temp=i
      if unit in ['T', 'mT', 'Oe', 'kOe']:
        field=i
    for dim in dims:
      if dim.startswith("Corrected"):
        first=False
    if first:
      dataset.append_column(dataset.data[mag])
      dataset.data[-1].dimension="Corrected "+dataset.data[-1].dimension
    def dia_para_calc(point):
      point[-1]= point[mag] + point[field] * ( dia - para / point[temp])
      return point
    dataset.process_function(dia_para_calc)
    dataset.ydata=len(dataset.data)-1

  def calc_dia(self):
    found, elements_dia=self.calc_dia_elements()
    if found:
      self.dia_mag_correct=self.dia_mag_offset + elements_dia
    else:
      print str(elements_dia) + ' not in list.'
      self.dia_mag_correct=self.dia_mag_offset
  
  def calc_dia_elements(self): 
    '''
      Returns the diamagnetic moment of the elements in self.dia_calc[1] with the mass self.dia_calc[2] 
      The format for the elements strin is 'La_1-Fe_2-O_4','la_1-fe2+_2-o_4', 'La-Fe_2-O_4' or 'LaFe2O4'
    '''
    input_string=self.dia_calc[1].lower()
    if input_string is '':
      return True, 0.
    element_dia=config.diamagnetism_table.ELEMENT_DIA
    mol_mass=0
    mol_dia=0
    # split the elements by '_' and '-' or just Capitals
    if '-' in input_string or '_' in input_string:
      split_elements=input_string.split('-')
      elements=[]
      counts=[]
      for string in split_elements:
        elements.append(string.split('_')[0])
        if len(string.split('_'))>1:
          counts.append(int(string.split('_')[1]))
        else:
          counts.append(1)
    else:
      elements=[]
      counts=[]
      j=0
      for i in range(len(input_string)-1):
        if input_string[i+1].isupper():
          elements.append(input_string[j:i+1])
          j=i+1
          counts.append(1)
      elements.append(input_string[j:])
      counts.append(1)
      for j in range(len(elements)):
        elements[j]=elements[j].lower()
        for i in range(len(elements[j])-1):
          if elements[j][i+1].isdigit():
            counts[j]=int(elements[j][i+1:])
            elements[j]=elements[j][:i+1]
            break
    for dia in element_dia:
      if dia[0].lower() in elements:
        mol_mass=mol_mass+dia[1]*counts[elements.index(dia[0].lower())]
        mol_dia=mol_dia+dia[2]*counts[elements.index(dia[0].lower())]
        counts.pop(elements.index(dia[0].lower()))
        elements.remove(dia[0].lower())
    if len(elements)==0: # check if all elements have been found in table
      return True, (mol_dia/mol_mass*self.dia_calc[2]*1e-6)
    else:
      return False, elements

  def do_subtract_dataset(self, dataset, object):
    '''
      Subtract one dataset from another using interpolation.
    '''
    from copy import deepcopy
    interpolate=scipy.interpolate.interp1d
    xdata=numpy.array(dataset.data[dataset.xdata].values)
    ydata=numpy.array(dataset.data[dataset.ydata].values)
    error=numpy.array(dataset.data[dataset.yerror].values)
    x2data=numpy.array(object.data[object.xdata].values)
    y2data=numpy.array(object.data[object.ydata].values)
    error2=numpy.array(object.data[object.yerror].values)
    if x2data[0]>x2data[-1]:
      x2data=numpy.array(list(reversed(x2data.tolist())))
      y2data=numpy.array(list(reversed(y2data.tolist())))
      error2=numpy.array(list(reversed(error2.tolist())))
    func2=interpolate(x2data, y2data, kind='cubic', bounds_error=False, fill_value=0.)
    efunc2=interpolate(x2data, error2, kind='cubic', bounds_error=False, fill_value=0.)
    y2interp=func2(xdata)
    error2interp=efunc2(xdata)
    x2_start=x2data.min()
    x2_stop=x2data.max()
    y2_start=y2data[0]
    y2_stop=y2data[-1]
    e2_start=error2[0]
    e2_stop=error2[-1]
    for i, x in enumerate(xdata):
      if x<x2_start:
        y2interp[i]=y2_start
        error2interp[i]=e2_start
      if x>x2_stop:
        y2interp[i]=y2_stop
        error2interp[i]=e2_stop
    newdata=deepcopy(dataset)
    newdata.data[newdata.ydata].values=(ydata-y2interp).tolist()
    newdata.data[newdata.yerror].values=(numpy.sqrt(error**2+error2interp**2)).tolist()
    newdata.short_info=dataset.short_info+' - '+object.short_info
    return newdata
