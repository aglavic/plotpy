#!/usr/bin/env python
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

# Pleas do not make any changes here unless you know what you are doing.

# import GenericSession, which is the parent class for the SquidSession
from generic import GenericSession
# importing preferences and data readout
import read_data.squid
import config.squid
import config.diamagnetism_table

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6b2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SquidSession(GenericSession):
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
  FILE_WILDCARDS=(('SQUID (.dat/.raw)','*.[Dd][Aa][Tt]', '*.[Rr][Aa][Ww]'), ('All', '*'))
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
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
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
    return read_data.squid.read_data(file_name,self.COLUMNS_MAPPING,self.MEASUREMENT_TYPES)
  
  def create_menu(self):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    string='''
      <menu action='SquidMenu'>
        <menuitem action='SquidDia'/>
        <menuitem action='SquidPara'/>
        <menuitem action='SquidExtractRaw'/>
      </menu>
    '''
    # Create actions for the menu, functions are invoked with the window as
    # third parameter to make interactivity with the GUI possible
    actions=(
            ( "SquidMenu", None,                             # name, stock id
                "SQUID", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SquidDia", None,                             # name, stock id
                "Diamagnetic Correction", None,                    # label, accelerator
                None,                                   # tooltip
                self.toggle_correction ),
            ( "SquidPara", None,                             # name, stock id
                "Paramagnetic Correction", None,                    # label, accelerator
                None,                                   # tooltip
                self.toggle_correction ),
            ( "SquidExtractRaw", None,                             # name, stock id
                "Extract magnetic moment", None,                    # label, accelerator
                None,                                   # tooltip
                self.calc_moment_from_rawdata ),
             )
    return string,  actions
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to GenericSession dia and paramagnetic
      corrections are performed here, too.
    '''
    datasets=GenericSession.add_file(self, filename, append)
    self.calc_dia()
    # faster lookup
    correct_dia=self.dia_mag_correct!=0
    correct_para=self.para[0]!=0
    for dataset in datasets:
      units=dataset.units()
      if 'T' in units:
        self.dia_mag_correct*=1e4
        self.para[0]*=1e4
      if 'A\302\267m\302\262' in units:
        self.dia_mag_correct/=1e3
        self.para[0]/=1e3
      if correct_dia:
        dataset.process_function(self.diamagnetic_correction)
        dataset.dia_corrected=True
      else:
        dataset.dia_corrected=False
      if correct_para:
        dataset.process_function(self.paramagnetic_correction)
        dataset.para_corrected=True
      else:
        dataset.para_corrected=False
      # name the dataset
      constant, unit=dataset.unit_trans_one(dataset.type(),config.squid.TRANSFORMATIONS_CONST)        
      dataset.short_info='at %d ' % constant + unit # set short info as the value of the constant column
      if 'T' in units:
        self.dia_mag_correct/=1e4
        self.para[0]/=1e4
      if 'A\302\267m\302\262' in units:
        self.dia_mag_correct*=1e3
        self.para[0]*=1e3
    return datasets


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
  def diamagnetic_correction(self, input_data):
    '''
      Calculate a diamagnetic correction for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    # TODO: The fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    # TODO: Replace dia and para correction by one function
    # TODO: Fit a dataset to get dia and para factor
    # TODO: Extra colum with corrected data and don't change original data
    # TODO: Graphical interface to change the correction factor.
    field=1
    mag=3
#    for mapping in self.COLUMNS_MAPPING: 
#      # selection of the columns for H and M, only works with right COLUMNS_MAPPING settings in config.squid.py
#      if mapping[2][0]=='H':
#        field=mapping[1]
#      if mapping[2][0]=='M_{rso}':
#        mag=mapping[1]
#      if mapping[2][0]=='M_{ac}':
#        mag=mapping[1]
    output_data[mag]+= output_data[field] * self.dia_mag_correct # calculate the linear correction
    return output_data
  
  def diamagnetic_correction_undo(self, input_data):
    ''' undo the correction '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    mag=3
#    for mapping in self.COLUMNS_MAPPING: 
#      # selection of the columns for H and M, only works with right COLUMNS_MAPPING settings in config.squid.py
#      if mapping[2][0]=='H':
#        field=mapping[1]
#      if mapping[2][0]=='M_{rso}':
#        mag=mapping[1]
#      if mapping[2][0]=='M_{ac}':
#        mag=mapping[1]
    output_data[mag]-= output_data[field] * self.dia_mag_correct # calculate the linear correction
    return output_data

  def paramagnetic_correction(self, input_data):
    '''
      Calculate a paramagnetic correction for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    # The fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    temp=2
    mag=3
#    for mapping in self.COLUMNS_MAPPING: 
#      # selection of the columns for H and M, only works with right COLUMNS_MAPPING settings in config.squid.py
#      if mapping[2][0]=='H':
#        field=mapping[1]
#      if mapping[2][0]=='M_{rso}':
#        mag=mapping[1]
#      if mapping[2][0]=='M_{ac}':
#        mag=mapping[1]
#      if mapping[2][0]=='T':
#        temp=mapping[1]
    output_data[mag]-= output_data[field] * self.para[0] / (output_data[temp]-self.para[1]) # calculate the paramagnetic correction
    return output_data
  
  def paramagnetic_correction_undo(self, input_data):
    ''' undo the correction '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    temp=2
    mag=3
#    for mapping in self.COLUMNS_MAPPING: 
#      # selection of the columns for H and M, only works with right COLUMNS_MAPPING settings in config.squid.py
#      if mapping[2][0]=='H':
#        field=mapping[1]
#      if mapping[2][0]=='M_{rso}':
#        mag=mapping[1]
#      if mapping[2][0]=='M_{ac}':
#        mag=mapping[1]
#      if mapping[2][0]=='T':
#        temp=mapping[1]
    output_data[mag]+= output_data[field] * self.para[0] / (output_data[temp]-self.para[1]) # calculate the paramagnetic correction
    return output_data
  
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
    input_string=self.dia_calc[1]
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

  def toggle_correction(self, action, window):
    '''
      do or undo dia-/paramagnetic correction
    '''
    name=action.get_name()
    for dataset in self.active_file_data:
      units=dataset.units()
      if 'T' in units:
        self.dia_mag_correct*=1e4
        self.para[0]*=1e4
      if 'A\302\267m\302\262' in units:
        self.dia_mag_correct/=1e3
        self.para[0]/=1e3
      if name=='SquidDia':
        if dataset.dia_corrected:
          dataset.process_function(self.diamagnetic_correction_undo)
          dataset.dia_corrected=False
        else:
          dataset.process_function(self.diamagnetic_correction)
          dataset.dia_corrected=True
      if name=='SquidPara':
        if dataset.para_corrected:
          dataset.process_function(self.paramagnetic_correction_undo)
          dataset.para_corrected=False
        else:
          dataset.process_function(self.paramagnetic_correction)
          dataset.para_corrected=True
      units=dataset.units()
      if 'T' in units:
        self.dia_mag_correct/=1e4
        self.para[0]/=1e4
      if 'A\302\267m\302\262' in units:
        self.dia_mag_correct*=1e3
        self.para[0]*=1e3
    window.replot()
  
  def calc_moment_from_rawdata(self, action, window, start_point=None, end_point=None):
    '''
      Try to fit the SQUID signal to retrieve the magnetic moment of a sample,
      in the future this will be extendet to use different sample shape functions.
    '''
    # check if this is a squid raw data file
    dims=self.active_file_data[0].dimensions()
    units=self.active_file_data[0].units()
    if not 'V_{SC-long}' in dims or\
        not ('H' in dims or '\xce\xbc_0\xc2\xb7H' in dims) or\
        not 'T' in dims or\
        not self.ALLOW_FIT:
      return False
    from fit_data import FitSession
    try:
      field_index=dims.index('\xce\xbc_0\xc2\xb7H')
    except ValueError:
      field_index=dims.index('H')
    field_unit=units[field_index]
    temp_index=dims.index('T')
    temp_unit=units[temp_index]
    v_index=dims.index('V_{SC-long}')
    from measurement_data_structure import MeasurementData      
    # select a data subset
    raw_data=self.active_file_data[start_point:end_point]
    # create object for extracted data
    extracted_data=MeasurementData([['Point', 'No.'], 
                                    [dims[field_index], field_unit], 
                                    ['T', temp_unit], 
                                    ['M_{fit}', 'emu'], 
                                    ['dM_{fit}', 'emu'], 
                                    ['Sample Pos._{fit}', 'cm'], 
                                    ['sigma_{fit}', 'cm'], 
                                    ],[],2,3,4)
    extracted_data.short_info='Magnetization data extracted via fitting'
    for i, data in enumerate(raw_data):
      if i%50 == 0:
        print "Extracting datapoint No: %i" %i
      data.ydata=v_index
      data.dydata=v_index
      fit_object=FitSession(data, window.file_actions)
      data.fit_object=fit_object
      fit_object.add_function('SQUID RAW-data')
      fit_object.fit()
      fit_object.simulate()
      fit_data=fit_object.functions[0][0].parameters
      extracted_data.append((i, data.get_data(0)[field_index], data.get_data(0)[temp_index], fit_data[0], fit_data[0], fit_data[1], fit_data[2]))
      self.active_file_data.append(extracted_data)
