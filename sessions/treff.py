# -*- encoding: utf-8 -*-
'''
  class for treff data sessions
'''
#################################################################################################
#                      Script to plot TREFF-measurements with gnuplot                           #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# TODO: Check for fortran-compiler to be installed

# import buildin modules
import os
import sys
import math, numpy
import subprocess
import time
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
# import parameter class for fits
from reflectometer_fit.parameters import FitParameters, LayerParam, MultilayerParam
from measurement_data_structure import MeasurementData
# importing data readout
import read_data.treff
import read_data.treff_addon1
import config.treff
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.treff', fromlist=['TreffGUI']).TreffGUI
except ImportError: 
  class GUI: pass
try:
  ReflectometerFitGUI=__import__( config.gui.toolkit+'gui.reflectometer_functions', fromlist=['ReflectometerFitGUI']).ReflectometerFitGUI
except ImportError: 
  class ReflectometerFitGUI: pass


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = ["Ulrich Ruecker", "Emmanuel Kentzinger", "Paul Zakalek"]
__license__ = "None"
__version__ = "0.7beta7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

class FitList(list):
  '''
    Class to store the fit parameters together with the list of MeasurementData objects.
  '''
  
  def __init__(self, *args):
    list.__init__(self, *args)
    self.fit_object=TreffFitParameters() 
    self.fit_object_history=[]
    self.fit_object_future=[]
    self.fit_datasets=[None, None, None, None] # a list of datasets used for fit [++,--,+-,-+]
 

def calc_intensities(R, P):
  '''
    Calculate intensities from given reflectivity channels R and given polarizations P.
    
    @param R Dictionary of ++, --, +-, -+ reflectivities (arrays)
    @param P Dictionary of polarizer,flipper1,flipper2,analyzer polarization component efficiencies (scalars)
  '''
  I={}
  # calculate up-up intensity
  I['++']=R['++'] * (P['polarizer']*P['flipper1']*P['analyzer']                             +\
                    (1.-P['polarizer'])*(1.-P['flipper1'])*P['analyzer'])                   +\
          R['--'] * ((1.-P['polarizer'])*P['flipper1']*(1.-P['analyzer'])                   +\
                    P['polarizer']*(1.-P['flipper1'])*(1.-P['analyzer']))                   +\
          R['+-'] * (P['polarizer']*P['flipper1']*(1.-P['analyzer'])                        +\
                    (1.-P['polarizer'])*(1.-P['flipper1'])*(1.-P['analyzer']))              +\
          R['-+'] * ((1.-P['polarizer'])*P['flipper1']*P['analyzer']                        +\
                    P['polarizer']*(1.-P['flipper1'])*P['analyzer'])
  # calculate down-down intensity
  I['--']=R['--'] * (P['polarizer']*P['flipper2']*P['analyzer']                             +\
                    P['polarizer']*(1.-P['flipper2'])*(1.-P['analyzer']))                   +\
          R['++'] * ((1.-P['polarizer'])*P['flipper2']*(1.-P['analyzer'])                   +\
                    (1.-P['polarizer'])*(1.-P['flipper2'])*P['analyzer'])                   +\
          R['-+'] * (P['polarizer']*P['flipper2']*(1.-P['analyzer'])                        +\
                    P['polarizer']*(1.-P['flipper2'])*P['analyzer'])                        +\
          R['+-'] * ((1.-P['polarizer'])*P['flipper2']*P['analyzer']                        +\
                    (1.-P['polarizer'])*(1.-P['flipper2'])*(1.-P['analyzer']))
  # calculate up-down intensity
  I['+-']=R['+-'] * (P['polarizer']*P['flipper1']*P['flipper2']*P['analyzer']               +\
                    (1.-P['polarizer'])*(1.-P['flipper1'])*P['flipper2']*P['analyzer'])     +\
          R['-+'] * ((1.-P['polarizer'])*P['flipper1']*P['flipper2']*(1.-P['analyzer'])     +\
                    P['polarizer']*(1.-P['flipper1'])*P['flipper2']*(1.-P['analyzer'])      +\
                    (1.-P['polarizer'])*P['flipper1']*(1.-P['flipper2'])*P['analyzer']      +\
                    P['polarizer']*(1.-P['flipper1'])*(1.-P['flipper2'])*P['analyzer'])     +\
          R['++'] * (P['polarizer']*P['flipper1']*P['flipper2']*(1.-P['analyzer'])          +\
                    P['polarizer']*P['flipper1']*(1.-P['flipper2'])*P['analyzer'])          +\
          R['--'] * ((1.-P['polarizer'])*P['flipper1']*P['flipper2']*P['analyzer']          +\
                    P['polarizer']*(1.-P['flipper1'])*P['flipper2']*P['analyzer']) # + O((1-p)^3) + (1-P)^4
  # calculate down-up intensity
  I['-+']=R['-+'] * (P['polarizer']*P['analyzer'])                                          +\
          R['+-'] * ((1.-P['polarizer'])*(1.-P['analyzer']))                                +\
          R['--'] * (P['polarizer']*(1.-P['analyzer']))                                     +\
          R['++'] * ((1.-P['polarizer'])*P['analyzer'])
  # normalize intensities for output
  scale_by=1./sum(I.values())
  for key in I.keys():
    I[key]*=scale_by
  return I

def seperate_scattering(datasets, P):
  '''
    Try to calculate the true reflectivity channels from the polarization components and the measured data.
    
    @param datasets A list of MeasurementData objects for ++, --, +- and -+ channel
    @param P Dictionary of polarizer,flipper1,flipper2,analyzer polarization component efficiencies
  '''
  from copy import deepcopy
  maximum_iterations=100
  stop_iteration_at=1e-10
  I={}
  min_length=min(map(len, datasets))
  if datasets[0].zdata<0:
    I['++']=numpy.array(datasets[0].data[datasets[0].ydata].values[:min_length])
    I['--']=numpy.array(datasets[1].data[datasets[0].ydata].values[:min_length])
    I['+-']=numpy.array(datasets[2].data[datasets[0].ydata].values[:min_length])
    I['-+']=numpy.array(datasets[3].data[datasets[0].ydata].values[:min_length])
  else:
    I['++']=numpy.maximum(numpy.array(datasets[0].data[datasets[0].zdata].values[:min_length]), 1e-8)
    I['--']=numpy.maximum(numpy.array(datasets[1].data[datasets[0].zdata].values[:min_length]), 1e-8)
    I['+-']=numpy.maximum(numpy.array(datasets[2].data[datasets[0].zdata].values[:min_length]), 1e-8)
    I['-+']=numpy.maximum(numpy.array(datasets[3].data[datasets[0].zdata].values[:min_length]), 1e-8)
  normalization_factor=sum(I.values())
  for key in I.keys():
    I[key]/=normalization_factor
  R=deepcopy(I)
  
  for i in range(maximum_iterations):
    I_neu=calc_intensities(R, P)
    I_div={}
    sum_of_divs=0.
    for key in I.keys():
      I_div[key]=I[key]-I_neu[key]
      R[key]+=I_div[key]
      sum_of_divs+=numpy.abs(I_div[key]).sum()
    print "Iteration %i: Sum of I_div=%.8f" % (i+1, sum_of_divs)
    if (sum_of_divs < stop_iteration_at):
      break
  output=[]
  output.append(R['++']*normalization_factor)
  output.append(R['--']*normalization_factor)
  output.append(R['+-']*normalization_factor)
  output.append(R['-+']*normalization_factor)
  return output

class TreffSession(GUI, ReflectometerFitGUI, GenericSession):
  '''
    Class to handle treff data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tTREFF-Data treatment:
\t-no-img\t\tOnly import the detector window data, not the 2d-maps.
\t-dimg\t\tCreate plots for all detector images. (resource consuming)
\t-gisans\t\tEvaluate data as GISANS measurement. Adds some evaluation functions to the TREFF menu.
\t\t\tNo αi-αf map or plot is created. This option implies -dimg and -maria.
\t-bin [i]\t\tIn GISANS mode rebin the detector image by a factor of i (e.g. 2x2 pixels together)

\t-maria\t\tForce read as maria file type, otherwise the datatype is set according to the file header

\t-add [file] [join]\tAdd data of file to that of the last given filename.
\t\t\tjoin can be -1,0 and 1, meaning get data from both, or only first/second dataset
\t\t\tif there is a conflict.
\t-sim\t\tRun a simulation mode to use without data
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('TREFF/MARIA', '*[!{.?}][!{.??}][!{.???}][!{.????}][!{.??.????}][!.]','*.zip'), ('All','*'))  
  TRANSFORMATIONS=[\
                  ['mrad',1/config.treff.GRAD_TO_MRAD,0,'°'],
                  ['detector', 'mrad', 1., 0, '2Θ', 'mrad'], 
                  ['detector', 'rad', 1., 0, '2Θ', 'rad'], 
                  ['detector', '°', 1., 0, '2Θ', '°'], 
                  ['omega', 'mrad', 1., 0, 'Θ', 'mrad'], 
                  ['omega', 'rad', 1., 0, 'Θ', 'rad'], 
                  ['omega', '°', 1., 0, 'Θ', '°'], 
                  ]  
  import_images=True
  import_detector_images=False
  x_from=5 # fit only x regions between x_from and x_to
  x_to=''
  max_iter=50 # maximal iterations in fit
  max_hr=5000 # Parameter in fit_pnr_multi
  max_alambda=10 # maximal power of 10 which alamda should reach in fit.f90
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['no-img', 'add', 'ft1', 'maria', 'dimg', 'sim', 'bin']
  MARIA=False
  replot=None 
  add_to_files={}
  add_simdata=False
  gisans=False
  rebinning=None
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    self.read_data=read_data.treff.read_data    
    self.RESULT_FILE=config.treff.RESULT_FILE
    GenericSession.__init__(self, arguments)
    if self.add_simdata:
      from copy import deepcopy
      simdata=read_data.treff.MeasurementDataTREFF([['Θ', 'mrad'], 
                             ['2DWindow', 'counts'], 
                             ['DetectorTotal', 'counts'], 
                             ['error','counts'], 
                             ['errorTotal','counts'], 
                             ['Intensity','counts/Monitor'], 
                             ['error(monitor)','counts/Monitor'], 
                             ['Intensity(time)', 'counts/s'], 
                             ['error(time)','counts/s']], 
                            [], 0, 5, 6)
      simdata.append([0, 1e6, 1e6, 1e3, 1e3, 1, 1e-3, 1, 1e-3])
      simdata.append([100, 0.1, 1, 0.01, 0.1, 1e-7, 1e-8, 1e-7, 1e-8])
      simdata.sample_name='Simulation'
      simdata.short_info='++'
      simdata.logy=True
      spp=simdata
      smm=deepcopy(simdata)
      smm.short_info='--'
      spm=deepcopy(simdata)
      spm.short_info='+-'
      smp=deepcopy(simdata)
      smp.short_info='-+'
      self.file_data['simulation']=[spp, smm, spm, smp]
      self.active_file_data=self.file_data['simulation']
      self.active_file_name='simulation'
    self.file_actions_addon['extract_specular_reflectivity']=self.do_extract_specular_reflectivity
    for key in self.file_data.keys():
      self.file_data[key]=FitList(self.file_data[key])
      if key=='simulation':
        self.file_data[key].fit_datasets=[ds for ds in self.file_data[key]]
    try:
      self.active_file_data=self.file_data[self.active_file_name]
    except KeyError:
      self.active_file_data=[]
  
  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='add':
          if len(input_file_names)>0:
            if input_file_names[-1] in self.add_to_files:
              self.read_directly=True
              self.add_to_files[input_file_names[-1]].append(argument)
            else:
              self.add_to_files[input_file_names[-1]]=[argument]
          last_argument_option=[False,'']            
        elif last_argument_option[1]=='bin':
          self.rebinning=int(argument)
          last_argument_option=[False,'']            
        else:
          found=False
      elif argument=='-ft1':
        self.read_data=read_data.treff_addon1.read_data
        self.mds_create=False
      elif argument=='-maria':
        self.maria=True
        self.read_data=read_data.treff.read_data_maria
      elif argument=='-gisans':
        print "Entering GISANS mode!"
        self.maria=True
        self.read_data=read_data.treff.read_data_maria
        self.import_detector_images=True
        self.gisans=True
        self.mds_create=False
        self.read_directly=True
      elif argument=='-no-img':
        self.import_images=False
        found=True
      elif argument=='-dimg':
        self.import_detector_images=True
        found=True
        self.mds_create=False
        self.read_directly=True
      elif argument=='-sim':
        self.add_simdata=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    data=self.read_data(file_name, self.SCRIPT_PATH, self.import_images, self.import_detector_images)
    if self.import_detector_images:
      data, detector_images=data
      self.file_data[file_name+'_imgs']=[]
      i=0
      if self.rebinning:
        print "\tRebinning detector images %ix%i" % (self.rebinning, self.rebinning)
      for channel_images in detector_images:
        for image in channel_images:
          image.number=str(i)
          i+=1
          if self.rebinning:
            from gtkgui.file_actions import rebin_2d
            rebinned=rebin_2d(image, self.rebinning)
            rebinned.short_info=image.short_info
            rebinned.sample_name=image.sample_name
            rebinned.logz=image.logz
            rebinned.plot_options=image.plot_options
            image=rebinned
          self.file_data[file_name+'_imgs'].append(image)
      if (len(detector_images[0])==1) or self.gisans:
        # if only one detector image is taken per channel, don't use αi-αf map and plot
        data=self.file_data[file_name+'_imgs']
        del(self.file_data[file_name+'_imgs'])
    if file_name in self.add_to_files:
      for name in self.add_to_files[file_name]:
        print "Trying to import for adding '%s'" % name
        add_data=self.read_data(name, self.SCRIPT_PATH, self.import_images, self.import_detector_images)
        for i, dataset in enumerate(data):
          print "Adding dataset %i from '%s'" %(i, name)
          data[i]=dataset.join(add_data[i])
    if data=='NULL':
      return data
    return FitList(data)

  def add_data(self, data_list, name, append=True):
    '''
      Function which ither adds file data to the object or replaces
      all data by a new dictionary.
    '''
    if not append:
      self.file_data={}
    self.file_data[name]=FitList(data_list)

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def do_extract_specular_reflectivity(self, file_actions, line_width, weighting, sigma, binning, center_position_offset=(0., 0.)):
    '''
      Function to extract the true specular reflectivity from an intensity map. It is appended to the
      file_actions dictionary to make it useable in a makro.
      The specular and two off-specular lines next to it are extracted and the off-specular ones
      are subtracted from the specular to account for the roughness scattering in the specular line.
      The distance of the two off-specular cuts is 2 times the line width of the specular line, this
      way we are quite close to the specular line without counting anything twice.
      
      @return At the moment True, should be if the extraction was successfull.
    '''
    # Extract the two lines
    specular=file_actions.create_cross_section(1.0, center_position_offset[0], 1.0, center_position_offset[1], 
                                                      line_width, 1, gauss_weighting=weighting, 
                                                      sigma_gauss=sigma, bin_distance=binning)
    off_spec1=file_actions.create_cross_section(1.0, 1.4142*line_width+center_position_offset[0], 
                                                1.0, -1.4142*line_width+center_position_offset[1], 
                                                line_width, 1, gauss_weighting=False, 
                                                sigma_gauss=1., bin_distance=binning)
    off_spec2=file_actions.create_cross_section(1.0, -1.4142*line_width+center_position_offset[0], 
                                                1.0, 1.4142*line_width+center_position_offset[1], 
                                                line_width, 1, gauss_weighting=False, 
                                                sigma_gauss=1., bin_distance=binning)
    # Create a new object for the stored data
    new_cols=[('2Θ', specular.units()[0]), 
              ('Specular Intensity', 'a.u.'), 
              ("True Specular Intensity", 'a.u.'), 
              ('Specular Error', 'a.u.'), 
              ('True Specular Error', 'a.u.'), 
              ('Off-Specular Intensity', 'a.u.'), 
              ]
    true_specular=MeasurementData(new_cols, 
                           [], 
                           0, 
                           2, 
                           4,
                           )
    off_spec1_xes=map(lambda angle:round(angle, 4), off_spec1.data[0].values)
    off_spec2_xes=map(lambda angle:round(angle, 4), off_spec2.data[0].values)
    # Go through all points and try to subtract the off-specular part,
    # if no off-specular point is present at the specific angle the specular intensity ist taken
    for point in specular:
      x=round(point[0], 4)
      if x not in off_spec1_xes and\
         x not in off_spec2_xes:
        true_specular.append([
                              x, 
                              point[3], 
                              point[3], 
                              point[4], 
                              point[4], 
                              0.
                              ])
      else:
        yo=[]
        dy2=[]
        if x in off_spec1_xes:
          index=off_spec1_xes.index(x)
          yo.append(-off_spec1.data[3].values[index])
          dy2.append(off_spec1.data[4].values[index])
        if x in off_spec2_xes:
          index=off_spec2_xes.index(x)
          yo.append(-off_spec2.data[3].values[index])
          dy2.append(off_spec2.data[4].values[index])
        y=sum(yo)/len(yo)+point[3]
        if y<=0:
          continue
        dy=math.sqrt((sum(dy2)/len(dy2))**2+point[4]**2)
        true_specular.append([
                              x, 
                              point[3], 
                              y, 
                              point[4], 
                              dy, 
                              -sum(yo)/len(yo)
                              ])
    # add the object to the active_file_data list
    active_data=self.active_file_data[file_actions.window.index_mess]
    true_specular.number=str(len(self.active_file_data)-1)
    true_specular.short_info='%s - Specular cut' % active_data.short_info
    true_specular.sample_name=active_data.sample_name
    true_specular.info=active_data.info
    true_specular.logy=True
    self.active_file_data.append(true_specular)
    file_actions.window.index_mess=len(self.active_file_data)-1
    return True
  
  def export_data_and_entfile(self, folder, file_name, datafile_prefix='fit_temp_', 
                              use_multilayer=False, use_roughness_gradient=True):
    '''
      Export measured data for fit program and the corresponding .ent file.
    '''
    names=config.treff.REF_FILE_ENDINGS
    output_names=config.treff.FIT_OUTPUT_FILES
    # convert x values from grad to mrad and 2Theta to Theta
    data_lines=[]
    for i, dataset in enumerate(self.active_file_data.fit_datasets):
      # if the channel dataset is None use 0 points.
      if dataset:
        dataset.unit_trans([['°', math.pi/180.*1000., 0, 'mrad'], 
                            ['rad', 1000., 0, 'mrad']])    
        dataset.unit_trans([['2Θ', 'mrad', 0.5, 0, 'Θ', 'mrad']])    
        data_lines.append(dataset.export(os.path.join(folder, datafile_prefix+names[i]+'.ref'), 
                                         False, ' ', 
                                         xfrom=self.x_from, xto=self.x_to, 
                                         only_fitted_columns=True))
      elif not self.active_file_data.fit_object.simulate_all_channels and not i==0:
        data_lines.append(0)
      else:
        ref_file=open(os.path.join(folder, datafile_prefix+names[i]+'.ref'), 'w')
        ref_file.write('1 1 1\n150 1 1\n')
        ref_file.close()
        data_lines.append(2)
    self.active_file_data.fit_object.number_of_points=data_lines
    self.active_file_data.fit_object.input_file_names=[os.path.join(folder, datafile_prefix+names[i]+'.ref') for i in range(4)]
    self.active_file_data.fit_object.set_fit_constrains()
    # create the .ent file
    ent_file=open(os.path.join(folder, file_name), 'w')
    ent_file.write(self.active_file_data.fit_object.get_ent_str(use_multilayer=use_multilayer, use_roughness_gradient=use_roughness_gradient)+'\n')
    ent_file.close()


  def call_fit_program(self, file_ent, force_compile=False):
    '''
      This function calls the fit_pnr program and if it is not compiled with 
      those settings, will compile it. It does not wait for the 
      program to finish, it only startes the sub process, which is returned.
    '''
    code_path=os.path.join(self.SCRIPT_PATH, 'config', 'fit', 'pnr_multi')
    code_file=os.path.join(self.TEMP_DIR, 'pnr.f90')
    exe=os.path.join(self.TEMP_DIR, 'pnr.o')
    subcode_files=map(lambda name: os.path.join(code_path, name), config.treff.PROGRAM_FILES)
    # has the program been changed or does it not exist
    if force_compile or (not os.path.exists(exe)) or \
      any(map(lambda name: (os.stat(name)[8]-os.stat(exe)[8]) > 0, subcode_files)):
      code=''
      for subcode_file in subcode_files:
        code+=open(subcode_file, 'r').read()
      code=code.replace("parameter(maxlay=400,map=7*maxlay+12,ndatap=1000,max_hr=5000,np_conv=500,pdq=0.02d0)", 
                        "parameter(maxlay=400,map=7*maxlay+12,ndatap=1000,max_hr=%i,np_conv=500,pdq=0.02d0)" % \
                   self.max_hr
                   )
      open(code_file, 'w').write(code)
      print 'Compiling fit program!'
      call_params=[config.treff.FORTRAN_COMPILER, code_file, '-o', exe]
      if  config.treff.FORTRAN_COMPILER_OPTIONS!=None:
        call_params.append(config.treff.FORTRAN_COMPILER_OPTIONS)
      if  config.treff.FORTRAN_COMPILER_MARCH!=None:
        call_params.append(config.treff.FORTRAN_COMPILER_MARCH)
      subprocess.call(call_params, shell=False)
      print 'Compiled'
    process = subprocess.Popen([exe + ' ' + file_ent + ' ' + str(self.max_iter)], 
                        shell=True, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        cwd=self.TEMP_DIR
                        )
    return process

  def smooth_dataset(self, dataset, kernel_size, kernel_size_y=None):
    '''
      Smoothe a dataset using the convolution with a gaussian kernel function.
      At the moment only for detector images (rectangular, equally spaced lattice)
    '''
    x=dataset.data[dataset.xdata][:]
    y=dataset.data[dataset.ydata][:]
    I=dataset.data[dataset.zdata][:].reshape(numpy.sqrt(len(x)), numpy.sqrt(len(x)))
    Ismooth=blur_image(I, kernel_size, kernel_size_y)
    dataset.data[dataset.zdata].values=Ismooth.flatten().tolist()

def gauss_kern(size, size_y=None):
  """ 
    Function from scipy cookbook (www.scipy.org/Cookbook/SiognalSmooth)
    Returns a normalized 2D gauss kernel array for convolutions 
  """
  if size_y is None:
    size_y=size
  x, y = numpy.mgrid[-size:size+1, -size_y:size_y+1]
  g = numpy.exp(-(x**2/float(size)+y**2/float(size_y)))
  return g / g.sum()

def blur_image(I, n, n_y=None) :
  """ 
    Function from scipy cookbook (www.scipy.org/Cookbook/SiognalSmooth)
    blurs the image by convolving with a gaussian kernel of typical
    size n.
  """
  from scipy import signal
  g = gauss_kern(n, n_y)
  improc = signal.convolve(I,g, mode='same')
  return improc

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
