# -*- encoding: utf-8 -*-
'''
  classes for treff sessions and fits with fit.f90
'''

from parameters import FitParameters, LayerParam, MultilayerParam


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7.3.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class TreffFitParameters(FitParameters):
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  wavelength=[4.73, 0.03] # wavelength and delta-wavelength of neutrons
  input_file_names=['', '', '', '']
  number_of_points=[10, 0, 0, 0] # number of simulated points from the 4 polarization chanels
  slits=[4.0, 4.0] # first and second slit opening before sample
  sample_length=10.0 # length of sample in the beam
  distances=[2270.0, 450.0] # distance between sample and first,last slit.
  polarization_parameters=[0.973, 0.951, 1.0, 1.0] # polarizer-/analyzer efficiency/first-/second flipper efficiency
  alambda_first=0.0001 # alambda parameter for first fit step
  ntest=1 # number of times chi has to be not improvable before the fit stops (I think)
  PARAMETER_LENGTH=7
  simulate_all_channels=False
  from config.scattering_length_table import NEUTRON_SCATTERING_LENGTH_DENSITIES
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.NEUTRON_SCATTERING_LENGTH_DENSITIES[material]
      result=True
      parameters=[thickness] + SL + [90., 90, roughness]
    except (KeyError, TypeError):
      parameters=[thickness] + [1. for i in range(self.PARAMETER_LENGTH-4)] + [90., 90., roughness]
      material='Unknown'
      result=False
    layer=TreffLayerParam(material, parameters)
    self.layers.append(layer)
    return result

  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.NEUTRON_SCATTERING_LENGTH_DENSITIES[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(TreffLayerParam(materials[i], [thicknesses[i]] + SL + [90., 90., roughnesses[i]]))
    multilayer=TreffMultilayerParam(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.NEUTRON_SCATTERING_LENGTH_DENSITIES[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1. for i in range(self.PARAMETER_LENGTH - 4)]
      result=False
    layer=TreffLayerParam(material, [0.] + SL + [90., 90., roughness])
    self.substrate=layer
    return result

  def get_ent_str(self, use_multilayer=False, use_roughness_gradient=True):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.slits[0]) + '\tfirst slit opening (mm)\n'
    ent_string+=str(self.slits[1]) + '\tsecond slit opening (mm)\n'
    ent_string+=str(self.sample_length) + '\tsample length (mm)\n'
    ent_string+=str(self.distances[0]) + '\tdistance from first slit to sample (mm)\n'
    ent_string+=str(self.distances[1]) + '\tdistance from second slit to sample (mm)\n'
    
    ent_string+='#+++ File names for the 4 polarization directions (++,--,+-,-+) +++\n'
    for i, name in enumerate(self.input_file_names):
      ent_string+=name + '\n' + str(self.number_of_points[i]) + '\t number of points used from this file\n'
    
    ent_string+='#------ \n'
    ent_string+=str(self.wavelength[0]) + '\twavelength of the neutrons (Angstrom)\n'
    ent_string+=str(self.wavelength[1]) + '\twidth of the wavelength (Angstrom)\n'
    
    ent_string+='#+++++  Begin of layer parameters +++++\n'
    if use_multilayer and any(map(lambda item: item.multilayer, self.layers)):
      string, layer_index, para_index=self.__get_ent_str_with_multilayer__()
      ent_string+=string
    else:      
      ent_string+='0\tnumber of layers on top of the (unused) multilayer\n'
      ent_string+='# blank\n'
      ent_string+='0\tnumber of layers in the unicell of the multilayer\n'
      ent_string+='# blank\n'
      ent_string+='0\tnumber of repititions of those unicells in the multilayer\n'
      ent_string+='# blank\n'
      
      ent_string+=str(self.number_of_layers()) + '\tnumber of layers below the (unused) multilayer\n'
      ent_string_layer, layer_index, para_index = self.__get_ent_str_layers__(use_roughness_gradient)
      ent_string+=ent_string_layer
    
    # more global parameters
    ent_string+=str(round(self.scaling_factor, 4)) + '\tscaling factor \t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(round(self.background, 4)) + '\tbackground\t\t\t\tparametar ' + str(para_index) + '\n'
    para_index+=1
    ent_string+='#### Polarization parameters\n'
    ent_string+=str(self.polarization_parameters[0]) + '\tpolarizer efficiency\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[1]) + '\tanalyzer efficiency\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[2]) + '\tfirst flipper efficiency\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    ent_string+=str(self.polarization_parameters[3]) + '\tsecond flipper efficiency\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    
    # create constrains as needed for pnr_multi ( degrees of freedom etc. )
    fit_parameters=list(self.fit_params)
    constrains_list=map(list, self.constrains)
    constrain_to_list=[]
    for constrain in constrains_list:
      constrain.sort()
      constrain_to_list.append(constrain.pop(0))
      for con in constrain:
        try:
          fit_parameters.remove(con)
        except ValueError:
          continue
    # fit specific parameters
    ent_string+='#### fit specific parameters:\n'
    ent_string+=str(self.fit) + '\t1: fit; 0: simulation\n'
    ent_string+='\n' + str(len(fit_parameters)) + '\t\tNumber of parameters to be fitted\n'
    ent_string+=' '.join([str(param) for param in fit_parameters]) + '\t\tindices of parameters\n'
    ent_string+='\n' + str(len(self.constrains)) + '\t\tnumber of constraints\n'
    for i, constrain in enumerate(constrains_list):
      ent_string+='1\ttype of contraint; 1: of type b=c=...=a  2: of type b+a=cste\n'
      ent_string+=str(constrain_to_list[i]) + '\tparameter with respect to which the equality relation has to be set\n'
      ent_string+=str(len(constrain)) + '\t\tnumber of parameters to be kept equal\n'
      ent_string+=' '.join([str(param) for param in constrain]) + '\t\tindices of those parameters\n'
    ent_string+='### Parameters for the fit algorithm:\n'
    ent_string+=str(self.alambda_first) + '\talambda_first, correspons to first step size in fit algorithm\n'
    ent_string+=str(self.ntest) + '\tntest, the number of times chi could not be improved before fit stops\n'
    return ent_string

  def __get_ent_str_with_multilayer__(self):
    '''
      Create string for layer part of .ent file for the fit script from given parameters.
      This function uses the multilayer functionality of pnr_multi.
    '''
    layer_list=[]
    for layer in self.layers:
      if layer.multilayer:
        layer_top=layer_list
        layer_list=[]
        multilayer=layer
      else:
        layer_list.append(layer)
    layer_bottom=layer_list
    
    # layers and parameters are numbered started with 1
    layer_index=1
    para_index=1
    ent_string=''
    ent_string+='%i\tnumber of layers on top of the (unused) multilayer\n' % len(layer_top)
    ent_string+='#### Begin of layers above, first layer '
    # add text for every top_layer
    for layer in layer_top:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    ent_string+='## End of layers above\n'
    ent_string+='%i\tnumber of layers in the unicell of the multilayer\n' % len(multilayer.layers)
    ent_string+='#### Begin of layers in multilayer '
    for layer in multilayer.layers:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string
    ent_string+='## End of layers in multilayer\n'
    ent_string+='%i\tnumber of repititions of those unicells in the multilayer\n' % multilayer.repititions
    ent_string+='\n'
    ent_string+='%i\tnumber of layers below the (unused) multilayer\n' % len(layer_bottom)
    ent_string+='#### Begin of layers below, first layer '
    # add text for every top_layer
    for layer in layer_bottom:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index)
      ent_string+=string    
    # substrate data
    string,  layer_index, para_index=self.substrate.get_ent_text(layer_index, para_index-1)
    ent_string+='\n'.join([string.splitlines()[0]]+string.splitlines()[2:]) + '\n' # cut the thickness line
    ent_string+='### End of layers.\n'
    return ent_string, layer_index, para_index
  
  def set_fit_parameters(self, layer_params={}, substrate_params=[], background=False, 
                         polarizer_efficiancy=False, analyzer_efficiancy=False, 
                         flipper0_efficiancy=False, flipper1_efficiancy=False, 
                         scaling=False):
    '''
      set fit parameters depending on (multi)layers
      layer_params is a dictionary with the layer number as index
    '''
    fit_params=[]
    para_index=1
    for i, layer in enumerate(self.layers):
      if i in layer_params:
        new_paras, para_index=layer.get_fit_params(layer_params[i], para_index)
        fit_params+=new_paras
      else:
        para_index+=len(layer)*7
    for param in substrate_params:
      fit_params.append(para_index + param)
    para_index+=6
    if scaling:
      fit_params.append(para_index)
    para_index+=1
    if background:
      fit_params.append(para_index)
    para_index+=1
    if polarizer_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if analyzer_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if flipper0_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    if flipper1_efficiancy:
      fit_params.append(para_index)
    para_index+=1
    fit_params.sort()
    self.fit_params=fit_params
    
  def get_parameters(self, parameters):
    '''
      set layer parameters from existing fit
    '''
    para_index=1
    for i, layer in enumerate(self.layers):
      for j in range(7): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            layer.set_param(j, parameters[para_index + j])
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*7) in self.fit_params:
              layer.layers[k].set_param(j, parameters[para_index + j + k*7])
      para_index+=len(layer)*7
    for j in range(6):
      if para_index in self.fit_params:
        self.substrate.set_param(j+1, parameters[para_index])
      para_index+=1
    if para_index in self.fit_params:
      self.scaling_factor=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.background=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[0]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[1]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[2]=parameters[para_index]
    para_index+=1
    if para_index in self.fit_params:
      self.polarization_parameters[3]=parameters[para_index]
    para_index+=1
  
  def get_errors(self, errors):
    '''
      convert errors dictionary from parameter indices to layer indices
    '''
    para_index=1
    errors_out={}
    for i, layer in enumerate(self.layers):
      for j in range(7): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            errors_out[str(i) + ',' + str(j)]=errors[para_index + j]
        else:
          for k in range(len(layer.layers)): # go through sub layers
            if (para_index + j + k*7) in self.fit_params:
              errors_out[str(i) + ',' + str(k) + ',' + str(j)]=errors[para_index + j + k*7]
      para_index+=len(layer)*7
    for j in range(6):
      if para_index in self.fit_params:
        errors_out['substrate'+str(j)]=errors[para_index]
      para_index+=1
    if para_index in self.fit_params:
      errors_out['scaling']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['background']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['polarizer_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['analyzer_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['flipper0_efficiancy']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['flipper1_efficiancy']=errors[para_index]
    para_index+=1
    return errors_out
  
  def set_fit_constrains(self):
    '''
      set fit constrains depending on (multi)layers
      layer_params is a dictionary with the layer number as index
    '''
    fit_cons=[]
    con_index=1
    for layer in self.layers:
      if layer.multilayer: # for every multilayer add constrains
        new_con, con_index=layer.get_fit_cons(con_index)
        fit_cons+=new_con
      else:
        con_index+=7
    fit_cons+=self.user_constraints
    self.constrains=[]
    # remove constrains not importent for the fitted parameters
    for constrain in fit_cons:
      if constrain[0] in self.fit_params:
        self.constrains.append(constrain)
    # combine constraints which overlap
    fit_cons=self.constrains
    remove=[]
    for constrain in fit_cons:
      if constrain in remove:
        continue
      for constrain_2 in [cons for cons in fit_cons if not cons is constrain]:
        if any(map(lambda con: con in constrain, constrain_2)) and not constrain_2 in remove:
          cmb=constrain+constrain_2
          cmb=dict.fromkeys(cmb).keys()
          cmb.sort()
          self.constrains.append(cmb)
          remove.append(constrain)
          remove.append(constrain_2)
    for rmv in remove:
      self.constrains.remove(rmv)

  def copy(self):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit=FitParameters.copy(self, TreffFitParameters())
    new_fit.wavelength=copy(self.wavelength)
    new_fit.input_file_names=copy(self.input_file_names)
    new_fit.slits=copy(self.slits)
    new_fit.sample_length=self.sample_length
    new_fit.distances=copy(self.distances)
    new_fit.polarization_parameters=copy(self.polarization_parameters)
    new_fit.alambda_first=self.alambda_first
    new_fit.ntest=self.ntest
    return new_fit

  def read_params_from_file(self, file):
    '''
      read data from .ent file
    '''
    lines=open(file, 'r').readlines()
    lines.reverse()
    for i, line in enumerate(lines):
      if line[0]!='#':
        lines[i]=line.replace('d', 'e') # replace power of ten in fortran 'd' by float 'e'
    # Geometry parameters
    self.slits[0]=float(lines.pop().split()[0])
    self.slits[1]=float(lines.pop().split()[0])
    self.sample_length=float(lines.pop().split()[0])
    self.distances[0]=float(lines.pop().split()[0])
    self.distances[1]=float(lines.pop().split()[0])
    # skip file names
    for i in range(10):
      lines.pop()
    self.wavelength[0]=float(lines.pop().split()[0])
    self.wavelength[1]=float(lines.pop().split()[0])
    lines.pop()
    # read top layers data
    number_of_layers_top=int(lines.pop().split()[0])
    self.layers=[]
    for i in range(number_of_layers_top):
      layer = self.read_layer_params_from_file(lines)
      self.layers.append(layer)
    # read multi layers data
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      multi_name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      multi_name='NoName'
    number_of_layers_multi=int(lines.pop().split()[0])
    if number_of_layers_multi>0:
      layers_in_multi=[]
      for i in range(number_of_layers_multi):
        layer = self.read_layer_params_from_file(lines)
        layers_in_multi.append(layer)
      lines.pop()
      repititions_of_multi=int(lines.pop().split()[0])
      self.layers.append(TreffMultilayerParam(repititions=repititions_of_multi, 
                                              name=multi_name, 
                                              layer_list=layers_in_multi))
    else:
      lines.pop()
      lines.pop()
    lines.pop()
    # read bottom layers data
    number_of_layers_bottom=int(lines.pop().split()[0])
    for i in range(number_of_layers_bottom):
      layer = self.read_layer_params_from_file(lines)
      self.layers.append(layer)
    # read substrate data
    self.substrate=self.read_layer_params_from_file(lines, substrate=True)
    # read last parameters
    lines.pop()
    self.scaling_factor=float(lines.pop().split()[0])
    self.background=float(lines.pop().split()[0])
    lines.pop()
    self.polarization_parameters[0]=float(lines.pop().split()[0])
    self.polarization_parameters[1]=float(lines.pop().split()[0])
    self.polarization_parameters[2]=float(lines.pop().split()[0])
    self.polarization_parameters[3]=float(lines.pop().split()[0])
    self.combine_layers(TreffMultilayerParam)

  def read_layer_params_from_file(self, lines, substrate=False):
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      name='NoName'
    parameters=[]
    for i in range(7):
      if i==0 and substrate:
        parameters.append(0.)
      else:
        parameters.append(float(lines.pop().split()[0]))
    layer=TreffLayerParam(name=name, parameters_list=parameters)
    return layer

  def read_params_from_X_file(self,name):
    '''
      Convert Parameters from x-ray .ent file to neutrons and import it
      for usage with this fit.
    '''
    import sessions.reflectometer

    ### reading X-ray data
    x_ray_fitdata=sessions.reflectometer.RefFitParameters()
    x_ray_fitdata.read_params_from_file(name)

    ### instument settings
    self.slits[0]=4.
    self.slits[1]=2.
    self.sample_length=10.
    self.distances[0]=2270.
    self.distances[1]=450.
    self.wavelength[0]=4.73
    self.wavelength[1]=0.03
    self.layers=[]
  
    ### null multilayer above
    #layers_in_multi=[]
    #repititions_of_multi = 0
    #self.layers.append(sessions.treff.TreffMultilayerParam(0, name="NoName", layer_list=layers_in_multi))
    
    def get_layer_parameter(layer):
        name=layer.name
        parameters=[]
        parameters.append(layer.thickness)
        if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
          parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
        else:
          parameters.append(1)
          parameters.append(1)
          parameters.append(1)
        parameters.append(90)
        parameters.append(90)
        parameters.append(layer.roughness)
        return TreffLayerParam(name, parameters_list=parameters)
    
    for i, layer in enumerate(x_ray_fitdata.layers):
      ### multilayer
      if layer.multilayer:
        multilayer=TreffMultilayerParam(layer.repititions, layer.name, )
        for sub_layer in layer.layers:
          multilayer.layers.append(get_layer_parameter(sub_layer))
        self.layers.append(multilayer)
#          for k in range(len(x_ray_fitdata.layers[1].layers)):
#            name=x_ray_fitdata.layers[i].layers[k].name
#            parameters=[]
#            parameters.append(x_ray_fitdata.layers[i].layers[k].thickness)
#            if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
#              parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
#            else:
#              parameters.append(1)
#              parameters.append(1)
#              parameters.append(1)
#            parameters.append(90)
#            parameters.append(90)
#            parameters.append(x_ray_fitdata.layers[i].layers[k].roughness)
#            layer=sessions.treff.TreffLayerParam(name, parameters_list=parameters)
#            self.layers.append(layer)
      else:
        ### single layer
        self.layers.append(get_layer_parameter(layer))
  
    ### substrate
    name=x_ray_fitdata.substrate.name
    parameters=[]
    parameters.append(0)
    if name in self.NEUTRON_SCATTERING_LENGTH_DENSITIES:
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][0])
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][1])
      parameters.append(self.NEUTRON_SCATTERING_LENGTH_DENSITIES[name][2])
    else:
      parameters.append(1)
      parameters.append(1)
      parameters.append(1)
    parameters.append(90)
    parameters.append(90)
    parameters.append(x_ray_fitdata.substrate.roughness)
    self.substrate=TreffLayerParam(name=x_ray_fitdata.substrate.name, parameters_list=parameters)
  
   
    ### global parameters
    self.scaling_factor=0.4
    self.background=2
    self.polarization_parameters[0]=0.973
    self.polarization_parameters[1]=0.951
    self.polarization_parameters[2]=1.0
    self.polarization_parameters[3]=1.0

class TreffLayerParam(LayerParam):
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  scatter_density_Nb=1.
  scatter_density_Nb2=0.
  scatter_density_Np=0.
  theta=90.
  phi=90.
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    LayerParam.__init__(self, name, parameters_list)
    if parameters_list!=None:
      self.scatter_density_Nb=parameters_list[1]
      self.scatter_density_Nb2=parameters_list[2]
      self.scatter_density_Np=parameters_list[3]
      self.theta=parameters_list[4]
      self.phi=parameters_list[5]
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return LayerParam.__eq__(self, other) and\
      self.scatter_density_Nb==other.scatter_density_Nb and\
      self.scatter_density_Nb2==other.scatter_density_Nb2 and\
      self.scatter_density_Np==other.scatter_density_Np and\
      self.theta==other.theta and\
      self.phi==other.phi
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return TreffLayerParam(name=self.name, \
                     parameters_list=[\
                          self.thickness, \
                          self.scatter_density_Nb, \
                          self.scatter_density_Nb2, \
                          self.scatter_density_Np, \
                          self.theta, \
                          self.phi, \
                          self.roughness])

  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params
    '''
    list=[]
    for i in params:
      list.append(param_index + i)
    return list, param_index + 7
  
  def dialog_get_params(self, action, response, thickness, scatter_density_Nb, 
                        scatter_density_Nb2, scatter_density_Np, theta, phi, roughness):
    '''
      function to get parameters from the GUI dialog
    '''
    LayerParam.dialog_get_params(self, action, response, thickness, roughness)
    try:
      self.scatter_density_Nb=float(scatter_density_Nb.get_text())
      self.scatter_density_Nb2=float(scatter_density_Nb2.get_text())
      self.scatter_density_Np=float(scatter_density_Np.get_text())
      self.theta=float(theta.get_text())
      self.phi=float(phi.get_text())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==1: 
      self.scatter_density_Nb=value
    elif index==2: 
      self.scatter_density_Nb2=value
    elif index==3: 
      self.scatter_density_Np=value
    elif index==4: 
      self.theta=value
    elif index==5: 
      self.phi=value
    else:
      LayerParam.set_param(self, index, 6, value)
  
  def get_ent_text(self, layer_index, para_index, add_roughness=0., use_roughness_gradient=True):
    '''
      Function to get the text lines for the .ent file.
      Returns the text string and the parameter index increased
      by the number of parameters for the layer.
    '''
    if not use_roughness_gradient:
      add_roughness=0.
    text=LayerParam.__get_ent_text_start__(self, layer_index, para_index)
    para_index+=1
    text+=str(self.scatter_density_Nb) + '\treal part Nb\', - (A**-2)*1e6\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.scatter_density_Nb2) + ' imaginary part Nb\'\' of nuclear and\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.scatter_density_Np) + '\tmagnetic scat. len. dens. Np \t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.theta) + '\ttheta [deg.] (0 on z, 90 on x-y plane)\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.phi) + '\tphi [deg.]  (0 on x, 90 on y)\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=LayerParam.__get_ent_text_end__(self, layer_index, para_index, add_roughness)
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class TreffMultilayerParam(MultilayerParam):
  '''
    class for multilayer data
  '''
  
  def copy(self):
    return MultilayerParam.copy(self, TreffMultilayerParam())
  
  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params (list of param lists for multilayer)
    '''
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[j]:
        list+=[param_index + i + j * 7 + k * layers * 7 for k in range(self.repititions)]
    return list, param_index + len(self) * 7
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    if self.roughness_gradient==0:
      constrain_params=7
    else:
      constrain_params=6
    for j in range(layers): # iterate through layers
      for i in range(constrain_params): # iterate through parameters
        list.append([param_index + i + j * 7 + k * layers * 7 for k in range(self.repititions)])
    return list, param_index + len(self)
