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
__version__ = "0.6.1"
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
    return read_data.squid.read_data(file_name,self.COLUMNS_MAPPING,self.MEASUREMENT_TYPES)
  
  def create_menu(self):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    string='''
      <menu action='SquidMenu'>
        <menuitem action='SquidDiaPara'/>
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
            ( "SquidDiaPara", None,                             # name, stock id
                "_Dia-/Paramagnetic Correction...", "<control>d",                    # label, accelerator
                None,                                   # tooltip
                self.dia_para_dialog ),
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
    correct=(self.dia_mag_correct!=0 or self.para[0]!=0)
    for dataset in datasets:
      units=dataset.units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia*=1e4
        para*=1e4
      if 'A·m²' in units:
        dia/=1e3
        para/=1e3
      if correct:
        self.dia_para_correction(dataset, dia, para)
      # name the dataset
      constant, unit=dataset.unit_trans_one(dataset.type(),config.squid.TRANSFORMATIONS_CONST)      
      if dataset.short_info=='':
        unit=unit or dataset.units()[dataset.type()]
        dataset.short_info='at %d ' % constant + unit # set short info as the value of the constant column
    return datasets


  #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  
  def dia_para_dialog(self, action, window):
    '''
      A dialog to enter the diamagnetic and paramagnetic correction.
      Diamagnetic correction can be calculated from a fit to the
      asymptotic behaviour of a MvsH measurement.
    '''
    import gtk
    units=window.measurement[window.index_mess].units()
    dia=self.dia_mag_correct
    para=self.para[0]
    if 'T' in units:
      dia*=1e4
      para*=1e4
    if 'A·m²' in units:
      dia/=1e3
      para/=1e3
    dialog=gtk.Dialog(title="Enter diamagnetic and paramagnetic correction factors:", 
                      parent=window, flags=gtk.DIALOG_DESTROY_WITH_PARENT)
    # create a table with the entries
    table=gtk.Table(4, 4, False)
    top_label=gtk.Label("\nYou can enter a diamgnetic and paramagnetic Correction Factor here,\n"+\
                        "the data will then be correct as: NEWDATA=DATA - PARA * 1/T + DIA.\n\n")
    table.attach(top_label,
                # X direction #          # Y direction
                0, 3,                      0, 1,
                0,                       gtk.FILL|gtk.EXPAND,
                0,                         0)
    label=gtk.Label("Diamagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    dia_entry=gtk.Entry()
    dia_entry.set_text(str(dia))
    table.attach(dia_entry,
                # X direction #          # Y direction
                2, 4,                      1, 2,
                0,                       gtk.FILL,
                0,                         0)
    
    fit_button=gtk.Button("Fit asymptotes")
    table.attach(fit_button,
                # X direction #          # Y direction
                0, 1,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    label=gtk.Label("of MvsH measurement, excluding ±")
    table.attach(label,
                # X direction #          # Y direction
                1, 3,                      2, 3,
                gtk.FILL,                       gtk.FILL,
                0,                         0)
    fit_exclude_regtion=gtk.Entry()
    fit_exclude_regtion.set_width_chars(4)
    fit_exclude_regtion.set_text("1")
    table.attach(fit_exclude_regtion,
                # X direction #          # Y direction
                3, 4,                      2, 3,
                0,                       gtk.FILL,
                0,                         0)
    
    label=gtk.Label("Paramagnetic Correction: ")
    table.attach(label,
                # X direction #          # Y direction
                0, 2,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    para_entry=gtk.Entry()
    para_entry.set_text(str(para))
    table.attach(para_entry,
                # X direction #          # Y direction
                2, 4,                      3, 4,
                0,                       gtk.FILL,
                0,                         0)
    # insert the table and buttons to the dialog
    dialog.vbox.add(table)
    dialog.add_button("OK", 2)
    dialog.add_button("Apply", 1)
    dialog.add_button("Cancel", 0)
    fit_button.connect("clicked", lambda *ignore: dialog.response(3))
    fit_exclude_regtion.connect("activate", lambda *ignore: dialog.response(3))
    dia_entry.connect("activate", lambda *ignore: dialog.response(2))
    para_entry.connect("activate", lambda *ignore: dialog.response(2))
    dialog.show_all()
    dialog.connect("response", self.dia_para_response, window, [dia_entry, para_entry, fit_exclude_regtion])
  
  def dia_para_response(self, dialog, response, window, entries):
    '''
      Evaluate the response of the dialog from dia_para_dialog.
    '''
    if response==0:
      units=window.measurement[window.index_mess].units()
      dia=self.dia_mag_correct
      para=self.para[0]
      if 'T' in units:
        dia*=1e4
        para*=1e4
      if 'A·m²' in units:
        dia/=1e3
        para/=1e3
      self.dia_para_correction(window.measurement[window.index_mess], 
                               dia, para)
      window.replot()      
      dialog.destroy()
      return None
    try:
      dia=float(entries[0].get_text())
    except ValueError:
      dia=0.
      entries[0].set_text("0")
    try:
      para=float(entries[1].get_text())
    except ValueError:
      para=0.
      entries[1].set_text("0")
    try:
      split=float(entries[2].get_text())
    except ValueError:
      split=1.
      entries[2].set_text("1")
    if response==3:
      dataset=window.measurement[window.index_mess]
      if dataset.xdata==1:
        from fit_data import FitDiamagnetism
        # fit after paramagnetic correction
        self.dia_para_correction(dataset, 0. , para)
        fit=FitDiamagnetism(([0, 0, 0, split]))
        fit.refine(dataset.data[1].values, 
                   dataset.data[-1].values, 
                   dataset.data[dataset.yerror].values)
        entries[0].set_text(str(-fit.parameters[0]))
      return None
    if response>0:
      self.dia_para_correction(window.measurement[window.index_mess], dia, para)
      window.replot()
    if response==2:
      # if OK is pressed, apply the corrections and save as global.
      units=window.measurement[window.index_mess].units()
      if 'T' in units:
        dia/=1e4
        para/=1e4
      if 'A·m²' in units:
        dia*=1e3
        para*=1e3      
      self.dia_mag_correct=dia
      self.para[0]=para
      dialog.destroy()
    
  #-------------------------- GUI functions --------------------------------

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
    dims=dataset.dimensions()
    first=True
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
      if 'A·m²' in units:
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
      if 'A·m²' in units:
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
      fit_object=FitSession(data)
      data.fit_object=fit_object
      fit_object.add_function('SQUID RAW-data')
      fit_object.fit()
      fit_object.simulate()
      fit_data=fit_object.functions[0][0].parameters
      extracted_data.append((i, data.get_data(0)[field_index], data.get_data(0)[temp_index], fit_data[0], fit_data[0], fit_data[1], fit_data[2]))
      self.active_file_data.append(extracted_data)
