# -*- encoding: utf-8 -*-
'''
  classes for reflectometer sessions and fits with fit.f90
'''
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -import uxd files                                                                             #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -complete GUI control over the fit program                                                    #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import buildin modules
import os
import sys
import math
import subprocess
import time
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# import parameter class for fits
from reflectometer_fit.parameters import FitParameters, LayerParam, MultilayerParam
# importing preferences and data readout
import read_data.reflectometer
import config.reflectometer
from measurement_data_structure import MeasurementData
# import gui functions for active toolkit
from config.gui import toolkit
try:
  GUI=__import__( toolkit+'gui.reflectometer', fromlist=['ReflectometerGUI']).ReflectometerGUI
  ReflectometerFitGUI=__import__( toolkit+'gui.reflectometer_functions', fromlist=['ReflectometerFitGUI']).ReflectometerFitGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class FitList(list):
  '''
    Class to store the fit parameters together with the list of MeasurementData objects.
  '''
  
  def __init__(self, *args):
    list.__init__(self, *args)
    self.fit_object=RefFitParameters() 
    self.fit_object_history=[]
    self.fit_object_future=[]

class ReflectometerSession(GenericSession, GUI, ReflectometerFitGUI):
  '''
    Class to handle reflectometer data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
  '''
  \tReflectometer-Data treatment:
  \t-counts\t\tShow actual counts, not counts/s
  \t-fit [layers] [thicknesses] [est._roughness]
  \t\t\t\tExport measurements for use with fit programm by Emmanuel Kentzinger and create .ent file for it.
  \t\t\t\tlayers is a list of layers with format L1-L2-L3-S or 5[L1_L2]-S, where L,S are the names
  \t\t\t\tof the compounds of the layers and substrate as provided in config.scattering_length_table.py
  \t\t\t\tthicknesses is a list of layer thicknesses with format LT1-LT2-LT3 or [LT1_LT2] in A
  \t\t\t\test._roughness is the estimated overall roughness to begin with
  \t-ref\t\tTry to refine the scaling factor, background and roughnesses.
  '''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('reflectometer (.UXD)','*.[Uu][Xx][Dd]'), ('gziped (.UXD.gz)','*.[Uu][Xx][Dd].gz'), ('All','*'))  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['fit', 'ref']
  #options:
  show_counts=False # dont convert to conts/s
  export_for_fit=False # make the changes needed for the fit program to work
  try_refine=False # try to refine scaling and roughnesses
  logy=True # standard reflectometer view is logarithmic
  x_from=0.005 # fit only x regions between x_from and x_to
  x_to=''
  max_iter=50 # maximal iterations in fit
  max_alambda=10 # maximal power of 10 which alamda should reach in fit.f90
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.RESULT_FILE=config.reflectometer.RESULT_FILE
    self.DATA_COLUMNS=config.reflectometer.DATA_COLUMNS # read data columns from preferences
    self.TRANSFORMATIONS=config.reflectometer.TRANSFORMATIONS # read TRANSFORMATIONS from preferences
    GenericSession.__init__(self, arguments)
    #for key in self.file_data.keys():
    #  self.file_data[key]=FitList(self.file_data[key])
    try:
      self.active_file_data=self.file_data[self.active_file_name]
    except KeyError:
      self.active_file_data=[]
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for reflectometer sessions
    '''
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


  def read_file(self, file_name):
    '''
      function to read data files
    '''
    return read_data.reflectometer.read_data(file_name,self.DATA_COLUMNS)
  
  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to GenericSession counts per second
      corrections and fitting are performed here, too.  
    '''
    datasets=GenericSession.add_file(self, filename, append)
    #refinements=[]
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
        dataset.process_function(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      dataset.short_info=' started at Θ='+str(round(th,4))+' 2Θ='+str(round(twoth,4))+' φ='+str(round(phi,4))
      if self.export_for_fit: # export fit files
        self.export_fit(dataset,  filename)
        simu=read_data.reflectometer.read_simulation(self.TEMP_DIR+'fit_temp.sim')
        simu.number='sim_'+dataset.number
        simu.short_info='simulation'
        simu.sample_name=dataset.sample_name
        #refinements.append(simu)
        dataset.plot_together=[dataset, simu]
    # TODO: GUI selection to show only data or fit
    #if self.export_for_fit: # export fit files
     # self.add_data(refinements, filename+"_simulation")
    return datasets

  def add_data(self, data_list, name, append=True):
    '''
      Function which ither adds file data to the object or replaces
      all data by a new dictionary.
    '''
    if not append:
      self.file_data={}
    self.file_data[name]=FitList(data_list)


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def counts_to_cps(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    for i,unit in enumerate(self.units): 
  # selection of the columns for counts
      if unit=='counts':
        counts_column.append(i)
    for counts in counts_column:
      output_data[counts]=output_data[counts]/self.time_col # calculate the cps
    return output_data

  def call_fit_program(self, file_ent, file_res, file_out, max_iter, exe=None):
    '''
      This function calls the fit.f90 program and if it is not compiled with 
      those settings, will compile it with the number of layres present in 
      the current simulation. For this the maxint parameter in the fit.f90 
      code is replaced by the real number of layers. It does not wait for the 
      program to finish, it only startes the sub process, which is returned.
    '''
    code_file=os.path.join(self.SCRIPT_PATH, config.reflectometer.FIT_PROGRAM_CODE_FILE)
    if not exe:
      exe=os.path.join(self.TEMP_DIR, 'fit.o')
    try:
      code_tmp=open(os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), 'r').read()
    except IOError:
      code_tmp=' '
    # has the program been changed or does it not exist
    if (not os.path.exists(exe)) or \
      ((os.stat(code_file)[8]-os.stat(exe)[8]) > 0) or \
      (not 'maxint='+str(self.active_file_data.fit_object.number_of_layers()+1) in code_tmp):
      code=open(code_file, 'r').read()
      # compile the program with constants suitable for this dataset
      code_tmp=code.replace('maxint=25', 'maxint='+str(self.active_file_data.fit_object.number_of_layers()+1))
      code_tmp=code_tmp.replace('.and.alamda.le.1.0d10', '.and.alamda.le.1.0d'+str(self.max_alambda))
      code_tmp=code_tmp.replace('.or.alamda.gt.1.0d10', '.or.alamda.gt.1.0d'+str(self.max_alambda))
      tmp_file=open(os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), 'w')
      tmp_file.write(code_tmp)
      tmp_file.close()
      print 'Compiling fit program!'
      call_params=[config.reflectometer.FORTRAN_COMPILER, os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), '-o', exe]
      if  config.reflectometer.FORTRAN_COMPILER_OPTIONS!=None:
        call_params.append(config.reflectometer.FORTRAN_COMPILER_OPTIONS)
      if  config.reflectometer.FORTRAN_COMPILER_MARCH!=None:
        call_params.append(config.reflectometer.FORTRAN_COMPILER_MARCH)
      subprocess.call(call_params, shell=False)
      print 'Compiled'
    process = subprocess.Popen([exe, file_ent, file_res, file_out+'.ref', file_out+'.sim', str(max_iter)], 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        cwd=self.TEMP_DIR, 
                        )
    return process
    
  def find_total_reflection(self, dataset):
    '''
      try to find the angle of total reflection by
      searching for a decrease of intensity to 1/3
    '''
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

  def refine_scaling(self, dataset):
    '''
      try to fit the scaling factor before the total reflection angle
    '''
    self.active_file_data.fit_object.fit=1
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', False, ' ', xfrom=0.005,xto=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(scaling=True) # fit only scaling factor
    self.active_file_data.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    self.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',20)
    retcode = self.proc.communicate()
    parameters, errors=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref', self.active_file_data.fit_object)
    self.active_file_data.fit_object.scaling_factor=parameters[self.active_file_data.fit_object.fit_params[0]]
    self.active_file_data.fit_object.fit=0
    return retcode

  def refine_roughnesses(self, dataset):
    '''
      try to fit the layer roughnesses
    '''
    self.active_file_data.fit_object.fit=1
    layer_dict={}
    # create parameter dictionary for every (multi)layer, 3 is the roughness
    for i, layer in enumerate(self.active_file_data.fit_object.layers):
      if not layer.multilayer:
        layer_dict[i]=[3]
      else:
        layer_dict[i]=[[3] for j in range(len(layer.layers))]
    data_lines=dataset.export(self.TEMP_DIR+'fit_temp.res', False, ' ', xfrom=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(layer_params=layer_dict, substrate_params=[2]) # set all roughnesses to be fit
    self.active_file_data.fit_object.number_of_points=data_lines
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    self.proc = self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp',20)
    sec=0.
    while self.proc.poll()==None:
      time.sleep(0.1)
      sec+=0.1
      sys.stdout.write( '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                        'Script running for % 6dsec' % sec)
      sys.stdout.flush()
    retcode = self.proc.communicate()
    parameters, errors=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref',self.active_file_data.fit_object)
    self.active_file_data.fit_object.get_parameters(parameters)
    self.active_file_data.fit_object.fit=0
    return retcode

  def export_fit(self, dataset, input_file_name, export_file_prefix=None):
    '''
      Function to export data for fitting with fit.f90 program.
    '''
    if not export_file_prefix:
      export_file_prefix=self.TEMP_DIR+'fit_temp'
    if self.active_file_data.fit_object.layers==[]:
      #+++++++++++++++++++ create fit parameters object +++++++++++++++++++
      fit_thick=self.fit_thicknesses
      first_split=self.fit_layers.split('-')
      for compound in first_split:
        if compound[-1]==']': # is there a multilayer
          count=int(compound.split('[')[0])
          second_split=compound.split('[')[1].rstrip(']').split('_')
          second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
          self.active_file_data.fit_object.append_multilayer(second_split, map(float, second_thick), [self.fit_est_roughness for i in second_thick], count)
        else: # no multilayer
            if len(fit_thick)>0:
                self.active_file_data.fit_object.append_layer(compound, float(fit_thick.split('-')[0]), self.fit_est_roughness)
            else:
                self.active_file_data.fit_object.append_substrate(compound, self.fit_est_roughness)
        if len(fit_thick.split('-'))>1: # remove first thickness
            fit_thick=fit_thick.split('-',1)[1]
        else:
            fit_thick=''
      #------------------- create fit parameters object -------------------
    self.active_file_data.fit_object.set_fit_constrains() # set constrained parameters for multilayer
      # convert x values from angle to q
    dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])
      # first guess for scaling factor is the maximum intensity
    self.active_file_data.fit_object.scaling_factor=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    self.active_file_data.fit_object.background=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine: 
      print "Try to refine scaling"
      dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'q','Å^{-1}']])    
      self.refine_scaling(dataset)
      print "Try to refine roughnesses"
      self.refine_roughnesses(dataset)
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
      # write data into files with sequence numbers in format ok for fit.f90    
    data_lines=dataset.export(export_file_prefix+'.res',False,' ') 
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.set_fit_parameters(background=True)
    ent_file=open(export_file_prefix+'.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    print "Simulate the measurement"
    self.proc = self.call_fit_program(export_file_prefix+'.ent', 
                                                             export_file_prefix+'.res', 
                                                             export_file_prefix,20)
    retcode = self.proc.communicate()
    #------- create final input file and make a simulation -------

  #---- functions for fitting with fortran program by E. Kentzinger ----

class RefFitParameters(FitParameters):
  '''
    Class to store the parameters of a simulation or fit from the fit.f90 program.
    Mostly just storing different variables for the layers.
  '''
  # parameters for the whole fit
  radiation=[8048.0, 'Cu-K_alpha'] # readiation energy of x-rays
  number_of_points=10 # number of simulated points
  resolution=3.5 # resolution in q in 1e-3 A^-1
  theta_max= 2.3 # angle of total coverage for recalibration
  from config.scattering_length_table import SCATTERING_LENGTH_DENSITIES
  
  def append_layer(self, material, thickness, roughness):
    '''
      append one layer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
      parameters=[thickness] + SL + [roughness]
    except (KeyError, TypeError):
      parameters=[thickness] + [1. for i in range(self.PARAMETER_LENGTH-2)] + [roughness]
      material='Unknown'
      result=False
    layer=RefLayerParam(material, parameters)
    self.layers.append(layer)
    return result

  def append_multilayer(self, materials, thicknesses, roughnesses, repititions, name='Unnamed'):
    '''
      append a multilayer at bottom from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SLs=[self.SCATTERING_LENGTH_DENSITIES[layer] for layer in materials]
    except KeyError:
      return False
    layer_list=[]
    for i, SL in enumerate(SLs):
      layer_list.append(RefLayerParam(materials[i], [thicknesses[i]] + SL + [roughnesses[i]]))
    multilayer=RefMultilayerParam(repititions, name, layer_list)
    self.layers.append(multilayer)
    return True
  
  def append_substrate(self, material, roughness):
    '''
      append substrat from the lookup table defined
      in scattering_length_densities.py
    '''
    try: # if layer not in the table, return False
      SL=self.SCATTERING_LENGTH_DENSITIES[material]
      result=True
    except KeyError:
      material='Unknown'
      SL=[1. for i in range(self.PARAMETER_LENGTH - 2)]
      result=False
    layer=RefLayerParam(material, [0.] + SL + [roughness])
    self.substrate=layer
    return result

  def get_ent_str(self, use_roughness_gradient=True):
    '''
      create a .ent file for fit.f90 script from given parameters
      fit parameters have to be set in advance, see set_fit_parameters/set_fit_constrains
    '''
    ent_string=str(self.radiation[0]) + '\tscattering radiaion energy (' + self.radiation[1] + ')\n'
    ent_string+=str(self.number_of_points) + '\tnumber of datapoints\n\n'
    ent_string+=str(self.number_of_layers() + 1) + '\tnumber of interfaces (number of layers + 1)\n'
    ent_string_layer, layer_index, para_index = self.__get_ent_str_layers__(use_roughness_gradient)
    ent_string+=ent_string_layer
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

  
  def set_fit_parameters(self, layer_params={}, substrate_params=[], background=False, resolution=False, scaling=False):
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
    
  def get_parameters(self, parameters):
    '''
      set layer parameters from existing fit
    '''
    para_index=1
    for i, layer in enumerate(self.layers):
      for j in range(4): # every layer parameter
        if not layer.multilayer==1: # its a single layer
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
  
  def get_errors(self, errors):
    '''
      convert errors dictionary from parameter indices to layer indices
    '''
    para_index=1
    errors_out={}
    for i, layer in enumerate(self.layers):
      for j in range(4): # every layer parameter
        if not layer.multilayer==1: # its a single layer
          if (para_index + j) in self.fit_params:
            errors_out[str(i) + ',' + str(j)]=errors[para_index + j]
        else:
          for k in range(len(layer.layers)): # got through sub layers
            if (para_index + j + k*4) in self.fit_params:
              errors_out[str(i) + ',' + str(k) + ',' + str(j)]=errors[para_index + j + k*4]
      para_index+=len(layer)*4
    for j in range(3):
      if para_index in self.fit_params:
        errors_out['substrate'+str(j)]=errors[para_index]
      para_index+=1
    if para_index in self.fit_params:
      errors_out['background']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['resolution']=errors[para_index]
    para_index+=1
    if para_index in self.fit_params:
      errors_out['scaling']=errors[para_index]
    para_index+=1
    return errors_out
  
  def set_fit_constrains(self):
    '''
      Set fit constrains depending on (multi)layers.
      layer_params is a dictionary with the layer number as index
      Merge custom constrins with multilayer constrains.
    '''
    fit_cons=[]
    con_index=1
    for layer in self.layers:
      if layer.multilayer: # for every multilayer add constrains
        new_con, con_index=layer.get_fit_cons(con_index)
        fit_cons+=new_con
      else:
        con_index+=4
    fit_cons+=self.user_constraints
    fit_cons2=[]
    # remove constrains not importent for the fitted parameters
    for constrain in fit_cons:
      if constrain[0] in self.fit_params:
        fit_cons2.append(constrain)
    # write actual constraints and combine constraints with same indices
    fit_cons3=[]
    for constrain in fit_cons2:
      # go through the list in both directions and collect any lists which contain at
      # least one element with the same value, this way every constrains will be
      # merged without missing any crosscorrelations.
      for constrain2 in fit_cons2:
        if len(set(constrain+constrain2))!=len(set(constrain))+len(set(constrain2)):
          constrain=sorted(list(set(constrain+constrain2)))
      for constrain2 in reversed(fit_cons2):
        if len(set(constrain+constrain2))!=len(set(constrain))+len(set(constrain2)):
          constrain=sorted(list(set(constrain+constrain2)))
      if not constrain in fit_cons3:
        fit_cons3.append(constrain)
    self.constrains=fit_cons3

  def copy(self):
    '''
      create a copy of this object
    '''
    from copy import deepcopy as copy
    new_fit=FitParameters.copy(self, RefFitParameters())
    new_fit.radiation=copy(self.radiation)
    new_fit.number_of_points=self.number_of_points
    new_fit.resolution=self.resolution
    new_fit.theta_max=self.theta_max
    return new_fit

  def read_params_from_file(self, file):
    '''
      read data from .ent file
    '''
    lines=open(file, 'r').readlines()
    lines.reverse()
    self.radiation[0]=float(lines.pop().split()[0])
    lines.pop()
    lines.pop()
    number_of_layers=int(lines.pop().split()[0])
    # read layer data
    self.layers=[]
    for i in range(number_of_layers-1):
      comment=lines.pop()
      if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
        name=comment.split(':', 1)[1].strip('\n').lstrip()
      else:
        name='NoName'
      parameters=[]
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      parameters.append(float(lines.pop().split()[0]))
      layer=RefLayerParam(name=name, parameters_list=parameters)
      self.layers.append(layer)
    # read substrate data
    comment=lines.pop()
    if comment[0]=='#' and len(comment.split(':'))>=2: # if created by this programm, get name
      name=comment.split(':', 1)[1].strip('\n').lstrip()
    else:
      name='NoName'
    parameters=[]
    parameters.append(0)
    parameters.append(float(lines.pop().split()[0]))
    parameters.append(float(lines.pop().split()[0]))
    parameters.append(float(lines.pop().split()[0]))
    self.substrate=RefLayerParam(name=name, parameters_list=parameters)
    # read last parameters
    lines.pop()
    self.background=float(lines.pop().split()[0])
    self.resolution=float(lines.pop().split()[0])
    self.scaling_factor=float(lines.pop().split()[0])
    lines.pop()
    self.theta_max=float(lines.pop().split()[0])
    self.combine_layers(RefMultilayerParam)

class RefLayerParam(LayerParam):
  '''
    class for one layer data
    layer and multilay have the same function to create .ent file text
  '''
  delta=1
  d_over_b=1
  
  def __init__(self, name='NoName', parameters_list=None):
    '''
      class constructor
    '''
    LayerParam.__init__(self, name, parameters_list)
    if parameters_list!=None:
      self.delta=parameters_list[1]
      self.d_over_b=parameters_list[2]
    else:
      self.delta=1
      self.d_over_b=1
  
  def __eq__(self, other):
    '''
      test if two layers have the same parameters
    '''
    return LayerParam.__eq__(self, other) and\
      self.delta==other.delta and\
      self.d_over_b==other.d_over_b
  
  def copy(self):
    '''
      create a copy of this object
    '''
    return RefLayerParam(name=self.name, \
                     parameters_list=[\
                          self.thickness, \
                          self.delta, \
                          self.d_over_b, \
                          self.roughness])


  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params
    '''
    list=[]
    for i in params:
      list.append(param_index + i)
    return list, param_index + 4
  
  def dialog_get_params(self, action, response, thickness, delta, d_over_b, roughness):
    '''
      function to get parameters from the GUI dialog
    '''
    LayerParam.dialog_get_params(self, action, response, thickness, roughness)
    try:
      self.delta=float(delta.get_text())
      self.d_over_b=float(d_over_b.get_text())
    except TypeError:
      None
  
  def set_param(self, index, value):
    '''
      set own parameters by index
    '''
    if index==1: 
      self.delta=value
    elif index==2: 
      self.d_over_b=value
    else:
      LayerParam.set_param(self, index, 3, value)
  
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
    text+=str(self.delta) + '\tdelta *1e6\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=str(self.d_over_b) + '\tdelta/beta\t\t\t\tparameter ' + str(para_index) + '\n'
    para_index+=1
    text+=LayerParam.__get_ent_text_end__(self, layer_index, para_index, add_roughness)
    para_index+=1
    layer_index+=1
    return text, layer_index, para_index
  
class RefMultilayerParam(MultilayerParam):
  '''
    class for multilayer data
  '''
  
  def copy(self):
    return MultilayerParam.copy(self, RefMultilayerParam())
  
  def get_fit_params(self, params, param_index):
    '''
      return a parameter list according to params (list of param lists for multilayer)
    '''
    list=[]
    layers=len(self.layers)
    for j in range(layers):
      for i in params[j]:
        list+=[param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)]
    return list, param_index + len(self) * 4
  
  def get_fit_cons(self, param_index):
    '''
      return a list of constainlists according to multilayers
    '''
    list=[]
    layers=len(self.layers)
    if self.roughness_gradient==0:
      constrain_params=4
    else:
      constrain_params=3
    for j in range(layers): # iterate through layers
      for i in range(constrain_params): # iterate through parameters
        list.append([param_index + i + j * 4 + k * layers * 4 for k in range(self.repititions)])
    return list, param_index + len(self)
