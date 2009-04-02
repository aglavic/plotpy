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
    create a .ent file for fit.f90 script from given parameters
  '''
  def create_ent_file(self, array, points, ent_file_name, back_ground=0, resolution=3.5, \
                      scaling_factor=10, theta_max=2.3, fit=0, fit_params=[1], constrains=[]):
    from scattering_length_table import scattering_length_densities
    ent_file=open(ent_file_name,'w')
    ent_file.write('8048.0\tscattering radiaion energy (Cu-Ka)\n'+\
      str(points)+'\tnumber of datapoints\n'+\
      '\n'+str(len(array))+'\tnumber of interfaces (number of layers + 1)\n'+\
      '#### Begin of layers, first layer:')
    i=1
    for j,layer in enumerate(array):
      try:
        SL=scattering_length_densities[layer[0]]
      except KeyError:
        print layer[0]+' not found in database. Please edit scattering_length_table.py'
        SL=[10,1]
        ent_file.write(' Not in Table')
      ent_file.write(' '+str(j)+': '+layer[0]+'\n')
      if not layer[1]==None:
        ent_file.write(str(layer[1])+'\tlayer thickness (in A)\t\t\tparameter '+str(i)+'\n')
        i=i+1
      ent_file.write(str(SL[0])+'\tdelta *1e6\t\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write(str(SL[1])+'\tdelta/beta\t\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write(str(layer[2])+'\tlayer roughness (in A)\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write('#')
    ent_file.write('### End of layers.\n'+\
      str(round(back_ground,4))+'\tbackground\t\t\t\tparametar '+str(i)+'\n')
    i=i+1
    ent_file.write(str(resolution)+'\tresolution in q (sigma, in 1e-3 A^-1)\tparameter '+str(i)+'\n')
    i=i+1
    ent_file.write(str(round(scaling_factor,4))+'\tscaling factor *1e-6\t\t\tparameter '+str(i)+'\n')
    ent_file.write('\n'+str(theta_max)+'\ttheta_max (in deg) for recalibration\n\n'+\
      str(fit)+'\t1: fit; 0: simulation\n\n')
    ent_file.write(str(len(fit_params))+'\t\tNumber of parameters to be fitted\n'+str(fit_params).strip('[').strip(']').replace(',',' ')+'\t\tindices of parameters\n'+str(len(constrains))+'\t\tnumber of constrains\n')
    for constrain in constrains:
      ent_file.write(str(len(constrain))+'\t\tnumber of parameters to be kept equal\n'+\
      str(constrain).strip('[').strip(']').replace(',',' ')+'\t\tindices of those parameters\n')
    ent_file.close()

  '''
    try to find the angle of total reflection by
    searching for a decrease of intensity to 1/3
  '''
  def find_total_reflection(self, dataset): # find angle of total reflection from decay to 1/3 of maximum
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
  def read_fit_file(self, file_name, parameters): # load results of fit file
    result={}
    fit_file=open(file_name,'r')
    test_fit=fit_file.readlines()
    fit_file.close()
    for i,line in enumerate(reversed(test_fit)):
      split=line.split()
      if len(split)>0:
        if split[0] in parameters:
          result[split[0]]=float(split[1])
      if len(parameters)==len(result):
          return result
    return None

  '''
    try to fit the scaling factor before the total reflection angle
  '''
  def refine_scaling(self, dataset, layers,SF,BG,constrain_array): # refine the scaling factor within the region of total reflection
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=0.005,xto=self.find_total_reflection(dataset))
    self.create_ent_file(layers,data_lines,self.temp_dir+'fit_temp.ent', back_ground=BG, scaling_factor=SF,\
      constrains=constrain_array, fit=1,fit_params=[len(layers)*4+2])
    retcode = subprocess.call(['fit-script', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp','20'])
    scaling_factor=self.read_fit_file(self.temp_dir+'fit_temp.ref', [str(len(layers)*4+2)])[str(len(layers)*4+2)]
    return scaling_factor

  '''
    try to fit the layer roughnesses
  '''
  def refine_roughnesses(self, dataset, layers,SF,BG,constrain_array): # refine the roughnesses and background after the angle of total reflection
    fit_p=[i*4+4 for i in range(len(layers)-1)]
    fit_p.append(len(layers)*4-1)
    fit_p.sort()
    data_lines=dataset.export(self.temp_dir+'fit_temp.res', False, ' ', xfrom=self.find_total_reflection(dataset))
    self.create_ent_file(layers,data_lines,self.temp_dir+'fit_temp.ent',back_ground=BG,scaling_factor=SF,\
      constrains=constrain_array,fit=1,fit_params=fit_p)
    retcode = subprocess.call(['fit-script', self.temp_dir+'fit_temp.res', self.temp_dir+'fit_temp.ent', self.temp_dir+'fit_temp','50'])
    fit_p=map(str,fit_p)
    parameters=self.read_fit_file(self.temp_dir+'fit_temp.ref',fit_p)
    for i,layer in enumerate(layers):
      if i<len(layers)-1:
        layer[2]=abs(parameters[str(i*4+4)])
      else:
        layer[2]=abs(parameters[str(i*4+3)])
    #BG=parameters[str(len(layers)*4)]
    return [layers,BG]

  '''
    Function to export data for fitting with fit.f90 program,
    has to be reviewd and integrated within GUI
  '''
  def export_fit(self, dataset, input_file_name): 
    fit_thick=self.fit_thicknesses
    #+++++++++++++++++++ create array of layers +++++++++++++++++++
    first_split=self.fit_layers.split('-')
    layer_array=[]
    constrain_array=[]
    layer_index=1
    for compound in first_split:
      if compound[-1]==']': # is there a multilayer
        count=int(compound.split('[')[0])
        second_split=compound.split('[')[1].rstrip(']').split('_')
        second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
        for j in range(len(second_split)):
          constrain_array.append([])
        for i in range(count): # repeat every layer in multilayer
          for j,multi_compound in enumerate(second_split):
            constrain_array[-1-j].append((layer_index-1)*4+1) # every layer of same kind will have the same height
            layer_array.append([multi_compound,float(second_thick[j]),self.fit_est_roughness])
            layer_index=layer_index+1
      else: # no multilayer
          if len(fit_thick)>0:
              layer_array.append([compound,float(fit_thick.split('-')[0]),self.fit_est_roughness])
          else:
              layer_array.append([compound,None,self.fit_est_roughness])
          layer_index=layer_index+1
      if len(fit_thick.split('-'))>1: # remove first thickness
          fit_thick=fit_thick.split('-',1)[1]
      else:
          fit_thick=''
    #------------------- create array of layers -------------------
      # convert x values from angle to q
    dataset.unit_trans([['Theta', '\\302\\260', 4*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}'], \
                      ['2 Theta', '\\302\\260', 2*math.pi/1.54/180*math.pi, 0, 'q','A^{-1}']])
      # write data into files with sequence numbers in format ok for fit.f90    
    data_lines=dataset.export(input_file_name+'_'+dataset.number+'.res',False,' ') 
      # first guess for scaling factor is the maximum intensity
    scaling_fac=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    back_gr=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine: 
      scaling_fac=self.refine_scaling(dataset, layer_array,scaling_fac,back_gr,constrain_array)
      result=self.refine_roughnesses(dataset, layer_array,scaling_fac,back_gr,constrain_array)
      layer_array=result[0]
      back_gr=result[1]
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
    fit_p=[i*4+1 for i in range(len(layer_array)-1)]
    self.create_ent_file(layer_array, data_lines, input_file_name+'_'+dataset.number+'.ent', back_ground=back_gr,\
                          scaling_factor=scaling_fac, constrains=constrain_array,  fit_params=fit_p)
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
  radiaion=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
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
      SL=scattering_length_densities[material]
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
      SLs=[scattering_length_densities[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(Sls):
      layer_list.append(fit_layer(material[i], [thicknesses[i], SL[0], SL[1], roughnesses[i]]))
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
      SL=scattering_length_densities[material]
    except KeyError:
      return False
    layer=fit_layer(material, [None, SL[0], SL[1], roughness])
    self.substrate=layer
    return True
    
  '''
    create a .ent file for fit.f90 script from given parameters
    fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
  '''
  def create_ent_file(self, ent_file_name):
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.numer_of_layers()) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string+='#### Begin of layers, first layer '
    # layers and parameters are numbered started with 1
    leyer_index=1
    para_index=1
    # add text for every (multi)layer
    for layer in self.layers:
      string,  leyer_index,  para_index=layer.get_ent_text(leyer_index, para_index)
      ent_string+=string
    # substrate data
    string,  leyer_index,  para_index=self.substrate.get_ent_text(leyer_index, para_index-1)
    ent_string+='\n'.join(string.splitlines()[0]+string.splitlines()[2:])+'\n' # cut the thickness line
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
    # write the string into .ent file
    ent_file=open(ent_file_name,'w')
    ent_file.write(ent_string)
    ent_file.close()
  
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
      fit_params.append(param_index + param)
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
    self.fit_params=fit_params
      

  '''
    calculate the number of layers in the file as the layer list can
    contain multilayer elements
  '''
  def number_of_layers(self):
    i=0
    for layer in self.layers:
      i+=len(leyer)
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
    Function to get the text lines for the .ent file.
    Returns the text string and the parameter index increased
    by the number of parameters for the layer.
  '''
  def get_ent_text(self, leyer_index, para_index):
    text='# ' + str(leyer_index) + ': ' + self.name + '\n' # Name comment
    text+=str(self.thickness) + '\tlayer thickness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.roughness) + '\tlayer roughness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    leyer_index+=1
    return text, leyer_index, para_index
  
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
  def __init__(self, repititions=1, name='NoName', leyer_list=None):
    self.repititions=repititions
    self.name=name
    if leyer_list!=None:
      self.leyers=leyer_list
  
  '''
    length of the object is length of the leyers list * repititions
  '''
  def __len__(self):
    return len(self.leyers) * self.repititions

  '''
    return a parameter list according to params (list of param lists for multilayer)
  '''
  def get_fit_params(self, params, param_index):
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[i]:
        list+=[param_index + i + j * 4 + k * layer * 4 for k in range(self.repititions)]
    return list, param_index + len(self)
  

  '''
    Function to get the text lines for the .ent file.
    Returns the text string and the parameter index increased
    by the number of parameters for the layers.
  '''
  def get_ent_text(self, leyer_index, para_index):
    text='# Begin of multilay ' + self.name
    for i in range(self.repititions): # repead all leyers
      for leyer in self.leyers: # add text for every layer
        str, leyer_index, para_index = leyer.get_ent_text(leyer_index, para_index)
        text+=str
    return text
  

