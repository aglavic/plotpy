# -*- encoding: utf-8 -*-
'''
  Session for reflectometer data and fits with fit.f90.
'''

# import buildin modules
import os
import sys
import math
import subprocess
import time
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# import parameter class for fits
from reflectometer_fit.reflectometer import * #@UnusedWildImport
# importing preferences and data readout
from plot_script.read_data import reflectometer as read_data
# use own datastructure also for templates
from plot_script.sessions import templates
templates.MeasurementDataClass=read_data.MeasurementData
from plot_script.config import reflectometer as config
from plot_script.config import gnuplot_preferences
# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.reflectometer', fromlist=['ReflectometerGUI']).ReflectometerGUI
except ImportError:
  class GUI: pass
try:
  ReflectometerFitGUI=__import__(gui_config.toolkit+'gui.reflectometer_functions', fromlist=['ReflectometerFitGUI']).ReflectometerFitGUI
except ImportError:
  class ReflectometerFitGUI: pass

if not sys.platform.startswith('win'):
  WindowsError=OSError

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

class FitList(list):
  '''
    Class to store the fit parameters together with the list of MeasurementData objects.
  '''
  fit_inhomogenity_object=None

  def __init__(self, *args):
    list.__init__(self, *args)
    self.fit_object=RefFitParameters()
    self.fit_object_history=[]
    self.fit_object_future=[]

class ReflectometerSession(GUI, ReflectometerFitGUI, GenericSession):
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
  FILE_WILDCARDS=[('D8 reflectometer', '*.[Uu][Xx][Dd]', '*.[Uu][Xx][Dd].gz', '*.raw'), ('Philips X\'Pert', '*.txt', '*.xrdml')]
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
    self.RESULT_FILE=config.RESULT_FILE
    self.DATA_COLUMNS=config.DATA_COLUMNS # read data columns from preferences
    self.TRANSFORMATIONS=config.TRANSFORMATIONS # read TRANSFORMATIONS from preferences
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
          last_argument_option=[True, 'fit2']
        elif last_argument_option[1]=='fit2':
          self.fit_thicknesses=argument
          last_argument_option=[True, 'fit3']
        elif last_argument_option[1]=='fit3':
          self.fit_est_roughness=float(argument)
          last_argument_option=[False, '']
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
    return read_data.read_data(file_name , self.DATA_COLUMNS)

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
      for line in dataset.info.splitlines():
        strip=line.split('=')
        if strip[0]=='STEPTIME':
          self.time_col=float(strip[1])
        #if strip[0]=='THETA':
        #  th=float(strip[1])
        #if strip[0]=='2THETA':
        #  twoth=float(strip[1])
        #if strip[0]=='PHI':
        #  phi=float(strip[1])
      if not self.show_counts:
        self.units=dataset.units()
        dataset.process_function(self.counts_to_cps)
        dataset.unit_trans([['counts', 1, 0, 'counts/s']])
      #dataset.short_info=' started at Θ='+str(round(th,4))+' 2Θ='+str(round(twoth,4))+' φ='+str(round(phi,4))
      if self.export_for_fit: # export fit files
        self.export_fit(dataset, filename)
        simu=read_data.read_simulation(self.TEMP_DIR+'fit_temp.sim')
        simu.number='sim_'+dataset.number
        simu.short_info='simulation'
        simu.sample_name=dataset.sample_name
        #refinements.append(simu)
        dataset.plot_together=[dataset, simu]
    # TODO: GUI selection to show only data or fit
    #if self.export_for_fit: # export fit files
    #  self.add_data(refinements, filename+"_simulation")
    return datasets

  def add_data(self, data_list, name, append=True):
    '''
      Function which ither adds file data to the object or replaces
      all data by a new dictionary.
    '''
    if not append:
      self.file_data={}
    self.file_data[name]=FitList(data_list)

  def fourier_analysis(self, dataset, theta_c,
                         lambda_x=1.54, interpolation_type='linear'):
    '''
      Apply the fourier transform calculus found in 
      
        K.Sakurai et. all, Jpn. J. Appl. Phys. Vol 31 (1992) pp. L113-L115
        
      to the dataset to get thickness components of the measured sample.
      
      The dataset is expressed as a function of sqrt(Θ²-Θc²)/λ and is than normalized
      to a avaridge attenuation (polynomial fit to log of data). The result is then
      fourier transformed using the FFT algorithm.
      
      :param dataset: MeasurementData object of reflectivity data
      :param theta_c: Angle of total external reflection
      :param lambda_x: x-ray wavelength
      
      :return: new MeasurementData object of transformed data.
    '''
    import numpy as np
    from scipy.interpolate import interp1d
    from plot_script.measurement_data_structure import MeasurementData, PhysicalProperty
    from plot_script.fit_data import FitPowerlaw
    dataset.unit_trans([['Q', 'Å^{-1}', lambda_x/4./np.pi**2*180., 0., 'Θ', '°'],
                        ['2Θ', '°', 0.5, 0., 'Θ', '°']])
    region=np.where(dataset.x>theta_c)
    # Change x to sqrt(Θ²-Θc²)/λ and interpolate it to even spaced data
    x_uneven=(np.sqrt(dataset.x[region]**2-theta_c**2)%'rad')/lambda_x
    x=np.linspace(x_uneven.min(), x_uneven.max(), len(x_uneven))
    y_uneven=dataset.y[region]
    f=interp1d(x_uneven, y_uneven, kind=interpolation_type, copy=False)
    y=f(x)
    # normalize by a powerlaw fit to the logarithmic data
    fit=FitPowerlaw([1.,-0.001,-4., y.min()])
    fit.refine_parameters=range(3)
    fit.refine(x, y)
    fit.refine_parameters=range(4)
    fit.refine(x, y)
    # remove background
    #y-=fit.parameters[3]
    #fit.parameters[3]=0.
    y/=fit(x)
    y-=y.mean()
    # Calculate the Fourier transform of the logarithmic data
    fft_result=np.fft.rfft(y)[1:]
    fft_y=np.abs(fft_result)
    fft_x=np.linspace(1./(2.*x.max()), 1./(2.*x.max())*len(fft_y), len(fft_y))
    fft_phi=np.angle(fft_result)
    out=MeasurementData()
    out.append_column(PhysicalProperty('d-spacing', 'Å', fft_x))
    out.append_column(PhysicalProperty('Amplitude', 'a.u.', fft_y))
    out.append_column(PhysicalProperty('phase', 'rad', fft_phi))
    out.logx=True

    #out=MeasurementData()
    #out.append_column(PhysicalProperty('x', '', x))
    #out.append_column(PhysicalProperty('y_{scaled}', '', y))
    #out.append_column(PhysicalProperty('y_{interp}', '', f(x)))

    out.sample_name=dataset.sample_name
    out.short_info='Fourier Analysis with Θ_c=%g%s'%(theta_c, dataset.x.unit)
    #out2=MeasurementData()
    #out2.append_column( PhysicalProperty('d-spacing', 'Å', x) )
    #out2.append_column( PhysicalProperty('Intensity', 'a.u.', y) )
    return out#, out2

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def counts_to_cps(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    for i, unit in enumerate(self.units[:len(input_data)]):
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
    code_file=os.path.join(self.SCRIPT_PATH, config.FIT_PROGRAM_CODE_FILE)
    if not exe:
      exe=os.path.join(self.TEMP_DIR, 'fit.o')
    try:
      code_tmp=open(os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), 'r').read()
    except IOError:
      code_tmp=' '
    # has the program been changed or does it not exist
    if (not os.path.exists(exe)) or \
      ((os.stat(code_file)[8]-os.stat(exe)[8])>0) or \
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
      callopts=dict(
                      stderr=subprocess.PIPE,
                      stdout=subprocess.PIPE,
                      stdin=subprocess.PIPE,
                     )

      call_params=[config.FORTRAN_COMPILER, os.path.join(self.TEMP_DIR, 'fit_tmp.f90'), '-o', exe]
      if  config.FORTRAN_COMPILER_OPTIONS!=None:
        call_params.append(config.FORTRAN_COMPILER_OPTIONS)
      if  config.FORTRAN_COMPILER_MARCH!=None:
        call_params.append(config.FORTRAN_COMPILER_MARCH)
      if sys.argv[0].endswith('.exe'):
        # fix gfortran error when binary folder is not the first in path
        call_params[0]=os.path.join(self.SCRIPT_PATH, '..', 'gfortran', 'bin', 'gfortran.exe')
        tmpenv=dict(os.environ)
        tmpenv['PATH']=os.path.join(self.SCRIPT_PATH, '..', 'gfortran', 'bin',)
        callopts['env']=tmpenv
      try:
        proc=subprocess.Popen(call_params, shell=gnuplot_preferences.EMMULATE_SHELL,
                      creationflags=gnuplot_preferences.PROCESS_FLAGS,
                      **callopts
                      )
        result=proc.communicate()
      except (OSError, WindowsError), error:
        raise RuntimeError, "Problem calling the fortran compile '%s': %s"%(config.FORTRAN_COMPILER, error)
      if result!=('', ''):
        raise RuntimeError, "Problem compiling fortran program: %s"%(result[0]+result[1])
      else:
        print 'Compiled'
    process=subprocess.Popen([exe, file_ent, file_res, file_out+'.ref', file_out+'.sim', str(max_iter)],
                        shell=gnuplot_preferences.EMMULATE_SHELL,
                        creationflags=gnuplot_preferences.PROCESS_FLAGS,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE,
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
    dataset.export(self.TEMP_DIR+'fit_temp.res', False,
                   only_fitted_columns=True, xfrom=0.005,
                   xto=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(scaling=True) # fit only scaling factor
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    self.proc=self.call_fit_program(self.TEMP_DIR+'fit_temp.ent',
                                    self.TEMP_DIR+'fit_temp.res',
                                    self.TEMP_DIR+'fit_temp', 20)
    retcode=self.proc.communicate()
    parameters, ignore=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref',
                                          self.active_file_data.fit_object)
    self.active_file_data.fit_object.scaling_factor=parameters[
                              self.active_file_data.fit_object.fit_params[0]]
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
        layer_dict[i]=[[3] for ignore in range(len(layer.layers))]
    dataset.export(self.TEMP_DIR+'fit_temp.res',
                   print_info=False, only_fitted_columns=True,
                   xfrom=self.find_total_reflection(dataset))
    self.active_file_data.fit_object.set_fit_parameters(layer_params=layer_dict, substrate_params=[2]) # set all roughnesses to be fit
    # create the .ent file
    ent_file=open(self.TEMP_DIR+'fit_temp.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    self.proc=self.call_fit_program(self.TEMP_DIR+'fit_temp.ent', self.TEMP_DIR+'fit_temp.res', self.TEMP_DIR+'fit_temp', 20)
    sec=0.
    while self.proc.poll()==None:
      time.sleep(0.1)
      sec+=0.1
      sys.stdout.write('\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b'+\
                        'Script running for % 6dsec'%sec)
      sys.stdout.flush()
    retcode=self.proc.communicate()
    parameters, ignore=self.read_fit_file(self.TEMP_DIR+'fit_temp.ref', self.active_file_data.fit_object)
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
          self.active_file_data.fit_object.append_multilayer(second_split, map(float, second_thick),
                                                             [self.fit_est_roughness for ignore in second_thick], count)
        else: # no multilayer
            if len(fit_thick)>0:
                self.active_file_data.fit_object.append_layer(compound, float(fit_thick.split('-')[0]),
                                                              self.fit_est_roughness)
            else:
                self.active_file_data.fit_object.append_substrate(compound, self.fit_est_roughness)
        if len(fit_thick.split('-'))>1: # remove first thickness
            fit_thick=fit_thick.split('-', 1)[1]
        else:
            fit_thick=''
      #------------------- create fit parameters object -------------------
    self.active_file_data.fit_object.set_fit_constrains() # set constrained parameters for multilayer
      # convert x values from angle to q
    dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'Q', 'Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'Q', 'Å^{-1}']])
      # first guess for scaling factor is the maximum intensity
    self.active_file_data.fit_object.scaling_factor=(dataset.max(xstart=0.005)[1]/1e5)
      # first guess for the background is the minimum intensity
    self.active_file_data.fit_object.background=dataset.min()[1]
    #+++++ Try to refine the scaling factorn and roughnesses +++++
    if self.try_refine:
      print "Try to refine scaling"
      dataset.unit_trans([['Θ', '°', 4*math.pi/1.54/180*math.pi, 0, 'Q', 'Å^{-1}'], \
                      ['2Θ', '°', 2*math.pi/1.54/180*math.pi, 0, 'Q', 'Å^{-1}']])
      self.refine_scaling(dataset)
      print "Try to refine roughnesses"
      self.refine_roughnesses(dataset)
    #----- Try to refine the scaling factorn and roughnesses -----
    #+++++++ create final input file and make a simulation +++++++
      # write data into files with sequence numbers in format ok for fit.f90    
    dataset.export(export_file_prefix+'.res', print_info=False, only_fitted_columns=True)
    self.active_file_data.fit_object.set_fit_parameters(background=True)
    ent_file=open(export_file_prefix+'.ent', 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str()+'\n')
    ent_file.close()
    print "Simulate the measurement"
    self.proc=self.call_fit_program(export_file_prefix+'.ent',
                                                             export_file_prefix+'.res',
                                                             export_file_prefix, 20)
    self.proc.communicate()
    #------- create final input file and make a simulation -------

  #---- functions for fitting with fortran program by E. Kentzinger ----
