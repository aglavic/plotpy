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
# -process raw data files (sequence splitting see SQUID_preferences.py)                         #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import SQUID_read_data
import SQUID_preferences

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.5.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class squid_session(generic_session):
  '''
    Class to handle squid data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\tSQUID-Data treatment:
\t-para [C] [off]\tInclude paramagnetic correction factor (C/(T-off)) [emu*K/Oe]
\t-dia [Chi]\tInclude diamagnetic correction in [10^-9 emu/Oe]
'''
  # TODO: implement this.
  '''
  \t-dia-calc [e] [m]\tAdd diamagnetic correction of sample containing elements e
  \t\t\t\t with complete mass m in mg. 
  \t\t\t\t e is given for example as 'La_1-Fe_2-O_4','la_1-fe2+_2-o_4' or 'La-Fe_2-O_4'.
  '''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  file_wildcards=(('squid data files','*.dat'), ('squid raw data files', '*.raw'))
  # options:
  dia_mag_correct=0 # diamagnetic correction factor
  dia_calc=[False, '', 0.0]
  para=[0, 0] # paramagnetic correction factor and T-offset
  options=generic_session.options+['dia', 'dia-calc', 'para']
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the generic_session constructor
    '''
    self.columns_mapping=SQUID_preferences.columns_mapping
    self.measurement_types=SQUID_preferences.measurement_types
    self.transformations=SQUID_preferences.transformations
    generic_session.__init__(self, arguments)
    
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='dia':
          self.dia_mag_correct=float(argument)/1e8
          last_argument_option=[False,'']
        elif last_argument_option[1]=='dia-calc':
          self.dia_calc[0]=True
          self.dia_calc[1]=argument
          last_argument_option=[True,'dia-calc2']
        elif last_argument_option[1]=='dia-calc2':
          self.dia_calc[2]=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='para':
          self.para[0]=float(argument)/1e8
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
    return SQUID_read_data.read_data(file_name,self.columns_mapping,self.measurement_types)
  
  def create_menu(self):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    string='''
      <menu action='SquidMenu'>
        <menuitem action='SquidDia'/>
        <menuitem action='SquidPara'/>
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
             )
    return string,  actions
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to generic_session dia and paramagnetic
      corrections are performed here, too.
    '''
    datasets=generic_session.add_file(self, filename, append)
    # faster lookup
    correct_dia=self.dia_mag_correct!=0
    correct_para=self.dia_mag_correct!=0
    for dataset in datasets:
      if correct_dia:
        dataset.process_funcion(self.diamagnetic_correction)
        dataset.dia_corrected=True
      else:
        dataset.dia_corrected=False
      if correct_para:
        dataset.process_funcion(self.paramagnetic_correction)
        dataset.para_corrected=True
      else:
        dataset.para_corrected=False
      # name the dataset
      constant_type=dataset.unit_trans_one(dataset.type(),SQUID_preferences.transformations_const)        
      dataset.short_info='at %d ' % constant_type[0]+constant_type[1] # set short info as the value of the constant column
    return datasets


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
  def diamagnetic_correction(self, input_data):
    '''
      Calculate a diamagnetic correction for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    mag=3
    for mapping in self.columns_mapping: 
      # selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
      if mapping[2][0]=='H':
        field=mapping[1]
      if mapping[2][0]=='M_rso':
        mag=mapping[1]
      if mapping[2][0]=='M_ac':
        mag=mapping[1]
    output_data[mag]=output_data[mag] + output_data[field] * self.dia_mag_correct # calculate the linear correction
    return output_data
  def diamagnetic_correction_undo(self, input_data):
    ''' undo the correction '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    mag=3
    for mapping in self.columns_mapping: 
      # selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
      if mapping[2][0]=='H':
        field=mapping[1]
      if mapping[2][0]=='M_rso':
        mag=mapping[1]
      if mapping[2][0]=='M_ac':
        mag=mapping[1]
    output_data[mag]=output_data[mag] - output_data[field] * self.dia_mag_correct # calculate the linear correction
    return output_data

  def paramagnetic_correction(self, input_data):
    '''
      Calculate a paramagnetic correction for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    temp=2
    mag=3
    for mapping in self.columns_mapping: 
      # selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
      if mapping[2][0]=='H':
        field=mapping[1]
      if mapping[2][0]=='M_rso':
        mag=mapping[1]
      if mapping[2][0]=='M_ac':
        mag=mapping[1]
      if mapping[2][0]=='T':
        temp=mapping[1]
    output_data[mag]=output_data[mag] - output_data[field] * self.para[0] / (output_data[temp]-self.para[1]) # calculate the paramagnetic correction
    return output_data
  def paramagnetic_correction_undo(self, input_data):
    ''' undo the correction '''
    output_data=input_data
    # the fixed columns should be replaced by a dynamic solution, perhaps a child datastructure
    field=1
    temp=2
    mag=3
    for mapping in self.columns_mapping: 
      # selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
      if mapping[2][0]=='H':
        field=mapping[1]
      if mapping[2][0]=='M_rso':
        mag=mapping[1]
      if mapping[2][0]=='M_ac':
        mag=mapping[1]
      if mapping[2][0]=='T':
        temp=mapping[1]
    output_data[mag]=output_data[mag] + output_data[field] * self.para[0] / (output_data[temp]-self.para[1]) # calculate the paramagnetic correction
    return output_data
  
  def toggle_correction(self, action, window):
    '''
      do or undo dia-/paramagnetic correction
    '''
    name=action.get_name()
    for dataset in self.active_file_data:
      if name=='SquidDia':
        if dataset.dia_corrected:
          dataset.process_funcion(self.diamagnetic_correction_undo)
          dataset.dia_corrected=False
        else:
          dataset.process_funcion(self.diamagnetic_correction)
          dataset.dia_corrected=True
      if name=='SquidPara':
        if dataset.para_corrected:
          dataset.process_funcion(self.paramagnetic_correction_undo)
          dataset.para_corrected=False
        else:
          dataset.process_funcion(self.paramagnetic_correction)
          dataset.para_corrected=True
    window.replot()
  
