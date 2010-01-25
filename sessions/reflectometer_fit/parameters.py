#!/usr/bin/env python
'''
  Classes for storing parameters for fortran simulation and exporting .ent files 
  used in reflectometer and treff sessions.
'''

from copy import deepcopy

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6.1beta"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


class FitParameters:
  '''
    Parent Class to store the parameters of a simulation or fit from the fit.f90 and pnr_multi program.
    Mostly just storing different variables for the layers and exporting .ent files.
  '''
  # parameters for the whole fit
  background=0 # constant background intensity
  scaling_factor=1 # intensity of total reflection in 1e6
  layers=[] # a list storing all layers/multilayers
  substrate=None # data for the substrate
  # fit specifc parameters
  fit=0
  fit_params=[]
  constrains=[]
  user_constraints=[]
  # constants
  SCATTERING_LENGTH_DENSITIES=None
  PARAMETER_LENGTH=4
  
  def __init__(self):
    '''
      class constructor
    '''
    self.layers=[]
    self.substrate=None
    self.fit_params=[]
    self.constrains=[]
  
  def copy(self, new_fit):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit.background=self.background
    new_fit.scaling_factor=self.scaling_factor
    new_fit.layers=[layer.copy() for layer in self.layers]
    new_fit.substrate=self.substrate.copy()
    new_fit.fit=self.fit
    new_fit.fit_params=copy(self.fit_params)
    new_fit.constrains=copy(self.constrains)
    new_fit.user_constraints=copy(self.user_constraints)
    return new_fit

  def remove_layer(self, layer):
    '''
      Remove a layer ither directly or from a multilayer
      inside. Strings of the object have to be compared,
      as __eq__ is defined in fit_layer only by the settings.
    '''
    if str(layer) in map(str, self.layers): # single layer can be removed directly
      self.layers.remove(layer)
    else: # multilayer layers have to be searched first
      for multilayer in [a_layer for a_layer in self.layers if a_layer.multilayer]:
        if str(layer) in map(str, multilayer.layers):
          multilayer.layers.remove(layer)
  
  def __get_ent_str_layers__(self, use_roughness_gradient=True):
    '''
      Create string for layer part of .ent file for the fit script from given parameters.
      The function has to be used in get_ent_str from derived class.
    '''
    ent_string='#### Begin of layers, first layer '
    # layers and parameters are numbered started with 1
    layer_index=1
    para_index=1
    # add text for every (multi)layer
    for layer in self.layers:
      string,  layer_index, para_index=layer.get_ent_text(layer_index, para_index, use_roughness_gradient=use_roughness_gradient)
      ent_string+=string
    # substrate data
    string,  layer_index, para_index=self.substrate.get_ent_text(layer_index, para_index-1)
    ent_string+='\n'.join([string.splitlines()[0]]+string.splitlines()[2:]) + '\n' # cut the thickness line
    ent_string+='### End of layers.\n'
    return ent_string, layer_index, para_index
  
  def __get_ent_str_substrate__(self, layer_index, para_index):
    '''
      Create string for substrate part of .ent file for the fit script from given parameters.
      The function has to be used in get_ent_str from derived class.
    '''
    ent_string='### Substrate'
    return ent_string

  def __get_ent_str_fit__(self):
    '''
      Create string for fit part of .ent file for the fit script from given parameters.
      The function has to be used in get_ent_str from derived class.
    '''
    ent_string='#### fit specific parameters:\n'
    ent_string+=str(self.fit) + '\t1: fit; 0: simulation\n'
    ent_string+='\n' + str(len(self.fit_params)) + '\t\tNumber of parameters to be fitted\n'
    ent_string+=' '.join([str(param) for param in self.fit_params]) + '\t\tindices of parameters\n'
    ent_string+=str(len(self.constrains)) + '\t\tnumber of constrains\n'
    for constrain in self.constrains:
      ent_string+=str(len(constrain)) + '\t\tnumber of parameters to be kept equal\n'
      ent_string+=' '.join([str(param) for param in constrain]) + '\t\tindices of those parameters\n'
    return ent_string

  
  def number_of_layers(self):
    '''
      calculate the number of layers in the file as the layer list can
      contain multilayer elements
    '''
    return sum(map(len, self.layers))
  
  def combine_layers(self, MultilayerClass):
    '''
      Function which tries to combine layers with the same parameters
      to a multilayer object. This needs a lot of list processing
      but essentially, it creates a list of periodically equal
      layers and changes these in the layers list to multilayers.
    '''
    candidates=[]
    for i, layer in enumerate(self.layers):
      for candidate in candidates:
        if i<candidate[1]:
          if i-candidate[0]+candidate[1]<len(self.layers) and\
            i-candidate[0]-candidate[1]>=0:
            if layer!=self.layers[i-candidate[0]+candidate[1]] and\
              layer!=self.layers[i-candidate[0]-candidate[1]]:
              candidates.remove(candidate)
      for j, layer2 in enumerate(self.layers[i+1:]):
        if layer==layer2:
          candidates.append([i, j+i+1])
    remove=[]
    # first delete all candidates, which have larger distances
    for i, candidate in enumerate(candidates):
      for candidate2 in candidates[i+1:]:
        if candidate2[0]==candidate[0] and not candidate2 in remove:
          remove.append(candidate2)
    for remover in remove:
      candidates.remove(remover)
    remove=[]
    # now combine followup repititions
    for i, candidate in enumerate(candidates):
      for candidate2 in candidates[i+1:]:
        if candidate2[0]==candidate[-1] and not candidate2 in remove:
          candidate.append(candidate2[1])
          remove.append(candidate2)
    for remover in remove:
      candidates.remove(remover)
    # now we have lists of layers with the same settings, 
    # we have to check, if the multilayer contains parts with equal settings
    # e.g. [lay0, lay1, lay0, lay2]
    ml_list=[]
    ml=[]
    for i, candidate in enumerate(candidates):
      if candidate in ml:
        continue
      ml=[candidate]
      for j,  candidate2 in enumerate(candidates[i+1:]):
        if min(candidate2) < max(candidate):
          ml.append(candidate2)
      ml_list.append(ml)
    multilayer_list=[]
    # creating a list the multilayers with all indices and the number of sublayers
    for ml in ml_list:
      add_ml=[]
      number_of_layers=max([m[1] - m[0] for m in ml])
      number_of_repititions=min([(m[-1] - m[0])/number_of_layers+1 for m in ml])
      for ml_i in ml:
        add_ml+=ml_i
      add_ml.sort()
      if add_ml==range(add_ml[0],add_ml[-1]+1):
        multilayer_list.append((add_ml, number_of_layers, number_of_repititions))
    # now we have lists of layers which are inside a multilayer and 
    # the number of layers in those multilayer,
    # we only have to create the multilayers and delete them
    multilayers=[]
    remove_layers=[]
    start_indices=[]
    for ml in multilayer_list:
      remove_layers+=map(lambda m: self.layers[m], ml[0])
      multilayers.append([ml[2], 
                          [self.layers[ml[0][0]+i] for i in range(ml[1])]]) # [repititions, layers]
      start_indices.append(ml[0][0])
    new_layers=[]
    i=0
    while self.layers!=[]:
      if not self.layers[0] in remove_layers:
        new_layers.append(self.layers.pop(0))
      elif len(start_indices)>0 and i==start_indices[0]:
        start_indices.pop(0)
        new=multilayers.pop(0)
        new_multilayer=MultilayerClass(new[0], layer_list=new[1])
        new_layers.append(new_multilayer)
        self.layers.pop(0)
      else:
        self.layers.pop(0)
      i+=1
    self.layers=new_layers


class LayerParam:
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  multilayer=False
  name=''
  thickness=1
  roughness=1
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    self.name=name
    if parameters_list!=None:
      self.thickness=parameters_list[0]
      self.roughness=parameters_list[-1]
    else:
      self.name=''
  
  def __len__(self):
    '''
      length is just one layer, see multilayers
    '''
    return 1
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return not other.multilayer and\
      self.thickness==other.thickness and\
      self.roughness==other.roughness
  
  def __ne__(self, other):
    return not self.__eq__(other)
  
  def dialog_get_params(self, action, response, thickness, roughness):
    '''
      function to get parameters from the GUI dialog
    '''
    try:
      self.thickness=float(thickness.get_text())
      self.roughness=float(roughness.get_text())
    except TypeError:
      None
  
  def set_param(self, index, rough_index, value):
    '''
      set own parameters by index
    '''
    if index==0: 
      self.thickness=value
    elif index==rough_index: 
      self.roughness=value
  
  def __get_ent_text_start__(self, layer_index, para_index):
    '''
      Function to get the start text lines of a layer  for the .ent file.
    '''
    text='# ' + str(layer_index) + ': ' + self.name + '\n' # Name comment
    text+=str(self.thickness) + '\tlayer thickness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    return text
  
  def __get_ent_text_end__(self, layer_index, para_index, add_roughness=0.):
    '''
      Function to get the end text lines of a layer for the .ent file.
    '''
    text=str(self.roughness + add_roughness) + '\tlayer roughness (in A)\t\t\tparameter ' + str(para_index) + '\n'
    return text
  
class MultilayerParam:
  '''
    class for multilayer data
  '''
  name=''
  repititions=1 # number of times these layers will be repeated
  multilayer=True
  roughness_gradient=0. # roughness increase from bottom to top layer
  layers=[] # list of layers that should be repeted.
  
  def __init__(self, repititions=2, name='NoName', layer_list=None):
    '''
      class constructor
    '''
    self.repititions=repititions
    self.name=name
    if layer_list!=None:
      self.layers=layer_list
    else:
      self.layers=[]
  
  def __len__(self):
    '''
      length of the object is length of the layers list * repititions
    '''
    return len(self.layers) * self.repititions

  def __eq__(self, other):
    '''
      For multilayers allways return false
    '''
    return False
  
  def copy(self, new_multilayer):
    '''
      create a copy of this object
    '''
    new_multilayer.name=str(self.name)
    new_multilayer.repititions=self.repititions
    new_multilayer.layers=[layer.copy() for layer in self.layers]
    return new_multilayer

  def dialog_get_params(self, action, response, repititions, roughness_gradient):
    '''
      function to get parameters from the GUI dialog
    '''
    try:
      self.repititions=int(repititions.get_text())
      self.roughness_gradient=float(roughness_gradient.get_text())
    except ValueError:
      None
  
  def get_ent_text(self, layer_index, para_index,  use_roughness_gradient=True):
    '''
      Function to get the text lines for the .ent file.
      Returns the text string and the parameter index increased
      by the number of parameters for the layers.
    '''
    text='# Begin of multilay ' + self.name + ' RoughnessGradient=' + str(self.roughness_gradient)
    if self.repititions>1:
      for i in range(self.repititions): # repead all layers
        for layer in self.layers: # add text for every layer
          string, layer_index, para_index = layer.get_ent_text(layer_index, 
                                                               para_index, 
                                                               add_roughness=float(self.repititions-i-1)/(self.repititions-1)* self.roughness_gradient, use_roughness_gradient=use_roughness_gradient)
          text+=string
    else:
      for i in range(self.repititions): # repead all layers
        for layer in self.layers: # add text for every layer
          string, layer_index, para_index = layer.get_ent_text(layer_index, para_index, use_roughness_gradient=use_roughness_gradient)
          text+=string
    return text,  layer_index,  para_index