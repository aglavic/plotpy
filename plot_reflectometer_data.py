#!/usr/bin/env python
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                       last changes:                                           #
#                                        01.04.2009                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert uxd files to .out space(and other)seperated text files, splitted by sequences        #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -send all files to printer after processing (linux commandline printing)                      #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import buildin modules
import math
import subprocess
# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import reflectometer_read_data
import reflectometer_preferences

'''
  Class to handle reflectometer data sessions
'''
class reflectometer_session(generic_session):
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\tReflectometer-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
\t-fit [layers] [thicknesses] [est._roughness]
\t\t\t\tExport measurements for use with fit programm by Emmanuel Kentzinger and create .ent file for it.
\t\t\t\tlayers is a list of layers with format L1-L2-L3-S or 5[L1_L2]-S, where L,S are the names
\t\t\t\tof the compounds of the layers and substrate as provided in scattering_length_table.py
\t\t\t\tthicknesses is a list of layer thicknesses with format LT1-LT2-LT3 or [LT1_LT2] in A
\t\t\t\test._roughness is the estimated overall roughness to begin with
\t-ref\t\tTry to refine the scaling factor, background and roughnesses.
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  options=generic_session.options+['fit', 'ref']
  #options:
  show_counts=False
  export_for_fit=False
  try_refine=False
  #------------------ local variables -----------------

  
  '''
    class constructor expands the generic_session constructor
  '''
  def __init__(self, arguments):
    self.data_columns=reflectometer_preferences.data_columns
    self.transformations=reflectometer_preferences.transformations
    generic_session.__init__(self, arguments)
    
  
  '''
    additional command line arguments for reflectometer sessions
  '''
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      if last_argument_option[0]:
        if last_argument_option[1]=='fit':
          self.export_for_fit=True
          self.fit_layers=argument
          last_argument_option=[True,'fit2']
        elif last_argument_option[1]=='fit2':
          self.fit_thicknesses=argument
          last_argument_option=[True,'fit3']
        elif last_argument_option[1]=='fit3':
          self.fit_est_roughness=float(argument)
          last_argument_option=[False,'']
      # Cases of arguments:
      elif argument=='-counts':
        self.show_counts=True
      elif argument=='-ref':
        self.try_refine=True
      else:
        found=False
    return (found, last_argument_option)


  '''
    function to read data files
  '''
  def read_file(self, file_name):
    return reflectometer_read_data.read_data(file_name,self.data_columns)
  
  '''
    create a specifig menu for the Reflectometer session
  '''
  def create_menu(self):
    # Create XML for squid menu
    string='''
      <menu action='ReflectometerMenu'>
      
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "ReflectometerMenu", None,                             # name, stock id
                "Reflectometer", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions
  
  '''
    Add the data of a new file to the session.
    In addition to generic_session counts per secong
    corrections and fiting are performed here, too.  
  '''
  def add_file(self, filename, append=True):
    datasets=generic_session.add_file(self, filename, append)
    refinements=[]
    for dataset in datasets:
      self.time_col=1
      th=0
      twoth=0
      phi=0       
      for line in dataset.info.splitlines():
        strip=line.split('=')
        if strip[0]=='STEPTIME':
          self.time_col=float(strip[1])
        if strip[0]=='THETA':
          th=float(strip[1])
        if strip[0]=='2THETA':
          twoth=float(strip[1])
        if strip[0]=='PHI':
          phi=float(strip[1])
      if not self.show_counts:
        self.units=dataset.units()
        dataset.process_funcion(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      dataset.short_info=' started at Th='+str(round(th,4))+' 2Th='+str(round(twoth,4))+' Phi='+str(round(phi,4))
      if self.export_for_fit: # export fit files
        self.export_fit(dataset,  filename)
        simu=reflectometer_read_data.read_simulation(filename+'_'+dataset.number+'.sim')
        simu.number='1'+dataset.number
        simu.short_info='simulation'
        simu.sample_name=dataset.sample_name
        refinements.append(simu)
        dataset.plot_together.append(simu)
    if self.export_for_fit: # export fit files
      self.add_data(refinements, filename+"_simulation")



  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  '''
    Calculate counts/s for one datapoint.
    This function will be used in process_function() of
    a measurement_data_structure object.
  '''
  def counts_to_cps(self, input_data):
    output_data=input_data
    counts_column=[]
    for i,unit in enumerate(self.units): 
  # selection of the columns for counts
      if unit=='counts':
        counts_column.append(i)
    for counts in counts_column:
      output_data[counts]=output_data[counts]/self.time_col # calculate the linear correction
    return output_data
  
  #++++ functions for fitting with fortran program by E. Kentzinger ++++

  '''
    try to find the angle of total reflection by
    searching for a decrease of intensity to 1/3
  '''
  def find_total_reflection(self, dataset):
    position=0
    max_value=0
    for point in dataset:
      position=point[0]
      if point[0]>0.05:
        if max_value<point[1]:
          max_value=point[1]
        elif max_value>(point[1]*3):
          dataset.index=0
          return position
    return position

  '''
    get fit-parameters back from the file
  '''
  def read_fit_file(self, file_name, fit_object):
    parameters=map(str, fit_object.fit_params)
    result={}
    fit_file=open(file_name,'r')
    test_fit=fit_file.readlines()
    fit_file.close()
    for i,line in enumerate(reversed(test_fit)):
      split=line.split()
      if len(split)>0:
        if split[0] in parameters:
          result[int(split[0])]=float(split[1])
      if len(parameters)==len(result):
          return result
    return None

  '''
    try to fit the scaling factor before the total reflection angle
  '''
  def refine_scaling(self, dataset, fit_object):
    fit_object.fit=1
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=0.005,xto=self.find_total_reflection(dataset))
    fit_object.set_fit_parameters(scaling=True) # fit only scaling factor
    fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(fit_object.get_ent_str()+'\n')
    ent_file.close()
    retcode = subprocess.call(['fit-script', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp','20'])
    fit_object.scaling_factor=self.read_fit_file(self.temp_dir+'fit_temp.ref', fit_object)[fit_object.fit_params[0]]
    fit_object.fit=0
    return retcode

  '''
    try to fit the layer roughnesses
  '''
  def refine_roughnesses(self, dataset, fit_object):
    fit_object.fit=1
    layer_dict={}
    # create parameter dictionary for every (multi)layer, 3 is the roughness
    for i, layer in enumerate(fit_object.layers):
      if len(layer)==1:
        layer_dict[i]=[3]
      else:
        layer_dict[i]=[[3] for j in range(len(layer.layers))]
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=self.find_total_reflection(dataset))
    fit_object.set_fit_parameters(layer_params=layer_dict, substrate_params=[2]) # set all roughnesses to be fit
    fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.temp_dir+'fit_temp.ent', 'w')
    ent_file.write(fit_object.get_ent_str()+'\n')
    ent_file.close()
    retcode = subprocess.call(['fit-script', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp','50'])
    parameters=self.read_fit_file(self.temp_dir+'fit_temp.ref',fit_object)
    fit_object.get_parameters(parameters)
    fit_object.fit=0
    return retcode

  '''
    Function to export data for fitting with fit.f90 program,
    has to be reviewd and integrated within GUI
  '''
  def export_fit(self, dataset, input_file_name): 
    fit_object=fit_parameter()
    #+++++++++++++++++++ create fit parameters object +++++++++++++++++++
    fit_thick=self.fit_thicknesses
    first_split=self.fit_layers.split('-')
    for compound in first_split:
      if compound[-1]==']': # is there a multilayer
        count=int(compound.split('[')[0])
        second_split=compound.split('[')[1].rstrip(']').split('_')
        second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
        fit_object.append_multilayer(second_split, map(float, second_thick), [self.fit_est_roughness for i in second_thick], count)
      else: # no multilayer
          if len(fit_thick)>0:
              fit_object.append_layer(compound, float(fit_thick.split('-')[0]), self.fit_est_roughness)
          else:
              fit_object.append_substrate(compound, self.fit_est_roughness)
      if len(fit_thick.split('-'))>1: # remove first thickness
          fit_thick=fit_thick.split('-',1)[1]
      else:
          fit_thick=''
    #------------------- create fit parameters object -------------------
    fit_object.set_fit_constrains() # set constrained parameters for multilayer
      # convert x values from angle to q
    dataset.unit_trans([['Theta', '\\302\\260', 4*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}'], \
                      ['2 Theta', '\\302\\260', 2*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}']])
      # write data into files with sequence numbers in format ok for fit.f90    
    data_lines=dataset.export(input_file_name+'_'+dataset.number+'.res',False,' ') 
      # first guess for scaling factor is the maximum intensity
    fit_object.scaling_factor=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    fit_object.background=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine: 
      self.refine_scaling(dataset, fit_object)
      self.refine_roughnesses(dataset, fit_object)
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
    fit_object.number_of_points=data_lines
    fit_object.set_fit_parameters(background=True)
    ent_file=open(input_file_name+'_'+dataset.number+'.ent', 'w')
    ent_file.write(fit_object.get_ent_str()+'\n')
    ent_file.close()
    retcode = subprocess.call(['fit-script', input_file_name+'_'+dataset.number+'.res',\
      input_file_name+'_'+dataset.number+'.ent', input_file_name+'_'+dataset.number])
    #------- create final input file and make a simulation -------

  #---- functions for fitting with fortran program by E. Kentzinger ----

'''
  Class to store the parameters of a simulation or fit from the fit.f90 program.
  Mostly just storing different variables for the layers.
'''
class fit_parameter():
  # parameters for the whole fit
  radiation=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
  number_of_points=10 # number of simulated points
  background=0 # constant background intensity
  resolution=3.5 # resolution in q in 1e-3 A^-1
  scaling_factor=1 # intensity of total reflection in 1e6
  theta_max= 2.3 # angle of total coverage for recalibration
  layers=[] # a list storing all layers/multilayers
  substrate=None # data for the substrate
  # fit specifc parameters
  fit=0
  fit_params=[1]
  constrains=[]
  
  '''
    class constructor
  '''
  def __init__(self):
    # lookup the scattering length density table
    from scattering_length_table import scattering_length_densities
    self.scattering_length_densities=scattering_length_densities
  
  '''
    append one layer at bottom from the lookup table defined
    in scattering_length_densities.py
  '''
  def append_layer(self, material, thickness, roughness):
    try: # if layer not in the table, return False
      SL=self.scattering_length_densities[material]
    except KeyError:
      return False
    layer=fit_layer(material, [thickness, SL[0], SL[1], roughness])
    self.layers.append(layer)
    return True
  
  
  '''
    append a multilayer at bottom from the lookup table defined
    in scattering_length_densities.py
  '''
  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    try: # if layer not in the table, return False
      SLs=[self.scattering_length_densities[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(fit_layer(materials[i], [thicknesses[i], SL[0], SL[1], roughnesses[i]]))
    multilayer=fit_multilayer(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
    None
  
  '''
    append substrat from the lookup table defined
    in scattering_length_densities.py
  '''
  def append_substrate(self, material, roughness):
    try: # if layer not in the table, return False
      SL=self.scattering_length_densities[material]
    except KeyError:
      return False
    layer=fit_layer(material, [None, SL[0], SL[1], roughness])
    self.substrate=layer
    return True
    
  '''
    create a .ent file for fit.f90 script from given parameters
    fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
  '''
  def get_ent_str(self):
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.number_of_layers() + 1) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string+='#### Begin of layers, first layer '
    # layers and parameters are numbered started with 1
    layer_index=1
    para_index=1
    # add text for every (multi)layer
    for layer in self.layers:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    # substrate data
    string,  layer_index, para_index=self.substrate.get_ent_text(layer_index, para_index-1)
    ent_string+='\n'.join([string.splitlines()[0]]+string.splitlines()[2:]) + '\n' # cut the thickness line
    ent_string+='### End of layers.\n'
    # more global parameters
    ent_string+=str(round(self.background, 4)) + '\tbackground\t\t\t\tparametar ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.resolution) + '\tresolution in q (sigma, in 1e-3 A^-1)\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(round(self.scaling_factor, 4)) + '\tscaling factor *1e6\t\t\tparameter ' + str(para_index) + '\n'
    ent_string+='\n' + str(self.theta_max) + '\ttheta_max (in deg) for recalibration\n'
    # fit specific parameters
    ent_string+='#### fit specific parameters:\n'
    ent_string+=str(self.fit) + '\t1: fit; 0: simulation\n'
    ent_string+='\n' + str(len(self.fit_params)) + '\t\tNumber of parameters to be fitted\n'
    ent_string+=' '.join([str(param) for param in self.fit_params]) + '\t\tindices of parameters\n'
    ent_string+=str(len(self.constrains)) + '\t\tnumber of constrains\n'
    for constrain in self.constrains:
      ent_string+=str(len(constrain)) + '\t\tnumber of parameters to be kept equal\n'
      ent_string+=' '.join([str(param) for param in constrain]) + '\t\tindices of those parameters\n'
    return ent_string

  
  '''
    set fit parameters depending on (multi)layers
    layer_params is a dictionary with the layer number as index
  '''
  def set_fit_parameters(self, layer_params={}, substrate_params=[], background=False, resolution=False, scaling=False):
    fit_params=[]
    para_index=1
    for i, layer in enumerate(self.layers):
      if i in layer_params:
        new_paras, para_index=layer.get_fit_params(layer_params[i], para_index)
        fit_params+=new_paras
      else:
        para_index+=len(layer)*4
    for param in substrate_params:
      fit_params.append(para_index + param)
    para_index+=3
    if background:
      fit_params.append(para_index)
    para_index+=1
    if resolution:
      fit_params.append(para_index)
    para_index+=1
    if scaling:
      fit_params.append(para_index)
    para_index+=1
    fit_params.sort()
    self.fit_params=fit_params
    
  '''
    set layer parameters from existing fit
  '''
  def get_parameters(self, parameters):
    para_index=1
    for i, layer in enumerate(self.layers):
      for j in range(4): # every layer parameter
        if len(layer)==1: # its a single layer
          if (para_index + j) in self.fit_params:
            layer.set_param(j, parameters[para_index + j])
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*4) in self.fit_params:
              layer.layers[k].set_param(j, parameters[para_index + j + k*4])
      para_index+=len(layer)*4
    for j in range(3):
      if para_index in self.fit_params:
        self.substrate.set_param(j+1, parameters[para_index])
      para_index+=1
    if para_index in self.fit_params:
      self.background=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.resolution=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.scaling_factor=parameters[para_index]
    para_index+=1
  
  '''
    set fit constrains depending on (multi)layers
    layer_params is a dictionary with the layer number as index
  '''
  def set_fit_constrains(self):
    fit_cons=[]
    con_index=1
    for layer in self.layers:
      if len(layer)>1: # for every multilayer add constrains
        new_con, con_index=layer.get_fit_cons(con_index)
        fit_cons+=new_con
      else:
        con_index+=4
    self.constrains=fit_cons
      

  '''
    calculate the number of layers in the file as the layer list can
    contain multilayer elements
  '''
  def number_of_layers(self):
    i=0
    for layer in self.layers:
      i+=len(layer)
    return i

'''
  class for one layer data
  layer and multilay have the same function to create .ent file text
'''
class fit_layer():
  name=''
  thickness=1
  delta=1
  d_over_b=1
  roughness=1
  
  '''
    class constructor
  '''
  def __init__(self, name='NoName', parameters_list=None):
    self.name=name
    if parameters_list!=None:
      self.thickness=parameters_list[0]
      self.delta=parameters_list[1]
      self.d_over_b=parameters_list[2]
      self.roughness=parameters_list[3]
  
  '''
    length is just one layer, see multilayers
  '''
  def __len__(self):
    return 1
  
  '''
    return a parameter list according to params
  '''
  def get_fit_params(self, params, param_index):
    list=[]
    for i in params:
      list.append(param_index + i)
    return list, param_index + 4
  
  '''
    set own parameters by index
  '''
  def set_param(self, index, value):
    if index==0: 
      self.thickness=value
    elif index==1: 
      self.delta=value
    elif index==2: 
      self.d_over_b=value
    elif index==3: 
      self.roughness=value
  
  '''
    Function to get the text lines for the .ent file.
    Returns the text string and the parameter index increased
    by the number of parameters for the layer.
  '''
  def get_ent_text(self, layer_index, para_index):
    text='# ' + str(layer_index) + ': ' + self.name + '\n' # Name comment
    text+=str(self.thickness) + '\tlayer thickness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.roughness) + '\tlayer roughness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
'''
  class for multilayer data
'''
class fit_multilayer():
  name=''
  layers=[] # a list of fit_layers
  repititions=1 # number of times these layers will be repeated
  
  '''
    class constructor
  '''
  def __init__(self, repititions=1, name='NoName', layer_list=None):
    self.repititions=repititions
    self.name=name
    if layer_list!=None:
      self.layers=layer_list
  
  '''
    length of the object is length of the layers list * repititions
  '''
  def __len__(self):
    return len(self.layers) * self.repititions

  '''
    return a parameter list according to params (list of param lists for multilayer)
  '''
  def get_fit_params(self, params, param_index):
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[j]:
        list+=[param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)]
    return list, param_index + len(self) * 4
  
  '''
    return a list of constainlists according to multilayers
  '''
  def get_fit_cons(self, param_index):
    list=[]
    layers=len(self.layers)
    for j in range(layers): # iterate through layers
      for i in range(4): # iterate through parameters
        list.append([param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)])
    return list, param_index + len(self)
  

  '''
    Function to get the text lines for the .ent file.
    Returns the text string and the parameter index increased
    by the number of parameters for the layers.
  '''
  def get_ent_text(self, layer_index, para_index):
    text='# Begin of multilay ' + self.name
    for i in range(self.repititions): # repead all layers
      for layer in self.layers: # add text for every layer
        string, layer_index, para_index = layer.get_ent_text(layer_index, para_index)
        text+=string
    return text,  layer_index,  para_index
  

