#!/usr/bin/env python
'''
  class for DNS data sessions and derived MeasurementData object.
'''
#################################################################################################
#                        Script to plot DNS-measurements with gnuplot                           #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import external modules
import os
import sys
# if possible use the numpy functions as they work with complete arrays
try:
  from numpy import pi, cos, sin, sqrt, array
  use_numpy=True
except ImportError:
  from math import pi, cos, sin, sqrt
  use_numpy=False
import gtk

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
from measurement_data_structure import MeasurementData
# importing data readout
import read_data.dns
import config.dns

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = ["Werner Schweika"]
__license__ = "None"
__version__ = "0.6a4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"


# if python version < 2.5 set the sys.exit function as exit
if hex(sys.hexversion)<'0x2050000':
  exit=sys.exit

# functions for evaluation of polarized neutron measurements
def correct_flipping_ratio(flipping_ratio, pp_data, pm_data, 
                           scattering_propability=0.1, convergence_criteria=None):
  '''
    Calculate the selfconsistent solution of the spin-flip/non spin-flip
    scattering with respect to a measured flipping ratio for given measured data.
    As most variables are scaled to sum up as 1. be sure to use floating point numbers
    or arrays of floating point numers.
  '''
  # as the function can be used for numbers and arrays
  # use deepcopy to create new values
  from copy import deepcopy as cp
  # define constants
  ITERATIONS=100
  MULTIPLE_SCATTERING_DEAPTH=10
  # just calculate the power of scattering propability times transmission once
  POW_OF_SCAT_PROP=[(1.-scattering_propability) * scattering_propability**i \
                    for i in range(MULTIPLE_SCATTERING_DEAPTH)]  
  # function for the test of the convergence
  if convergence_criteria is None:
    def test(difference):
      return difference<1e-10
  else:
    test=convergence_criteria
  
  # normalize the data
  total=(pp_data+pm_data)
  p_norm=pp_data/total
  m_norm=pm_data/total
  
  # use the data as starting value
  nsf_scattering=cp(p_norm)
  sf_scattering=1.-nsf_scattering
  
  # calculate polarization from flipping-ratio
  polarization=flipping_ratio/(1+flipping_ratio)
  
  for iter in range(ITERATIONS):
    # n-times multiple scattering is represented by a list of length n
    p_multiple_scattering=[polarization]
    m_multiple_scattering=[1.-polarization]
    # calculate the multiple scattered part part of the intensity
    for i in range(MULTIPLE_SCATTERING_DEAPTH):
      p_multiple_scattering.append(
                                   p_multiple_scattering[i]*nsf_scattering +\
                                   m_multiple_scattering[i]*sf_scattering
                                   )
      m_multiple_scattering.append(
                                   m_multiple_scattering[i]*nsf_scattering +\
                                   p_multiple_scattering[i]*sf_scattering
                                   )
    # calculate the intensity measured for the complete scattering
    up_intensity=p_multiple_scattering[1] * POW_OF_SCAT_PROP[0]
    down_intensity=m_multiple_scattering[1] * POW_OF_SCAT_PROP[0]
    for i in range(1, MULTIPLE_SCATTERING_DEAPTH):
      up_intensity+=p_multiple_scattering[i+1] * POW_OF_SCAT_PROP[i]
      down_intensity+=m_multiple_scattering[i+1] * POW_OF_SCAT_PROP[i]
    
    # calculate difference of measured and simulated scattering
    diff=p_norm-up_intensity  
    nsf_scattering+=diff
    sf_scattering=1.-nsf_scattering
    
    # test if the solution converged
    if test(abs(diff)):
      # scale the output by total measured intensity
      return nsf_scattering*total, sf_scattering*total, True, nsf_scattering, sf_scattering

  # scale the output by total measured intensity
  return nsf_scattering*total, sf_scattering*total, False, nsf_scattering, sf_scattering


class DNSSession(GenericSession):
  '''
    Class to handle dns data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tDNS-Data treatment:
\t-inc [inc]\tThe default increment between files of the same polarization
\t-split [s]\tSplit the files into measurements every s files
\t-ooff [ooff]\tOffset of omega angle for the sample to calculate the right q_x,q_y

\t-powder\t\tEvaluate as powder data
\t-b\t\tSelect background file from system directory (normally from this reactor cycle)
\t-bg [bg]\tFile to be substracted as background
\t-fr [scp]\t\tTry to make automatic flipping-ratio correction with the scatteringpropability scp
\t-v\t\tSelect vanadium file from system directory (normally from this reactor cycle)
\t-vana [file]\tUse different Vanadium file for evaluation
\t-system [folder]\tSet an other system folder for background,vanadium and NiCr files
\t-setup [name]\tSet the name of your sample to be used in every plot(can be changed in GUI)

\t-files [prefix] [ooff] [inc] [from] [to] [postfix]
\t\t\tExplicidly give the file name prefix, omega offset, increment, numbers and postfix
\t\t\tfor the files to be used. Can be given multiple times for diefferent prefixes

\tShort info settings: 
\t\t-time, -flipper, -monitor
\t\t\tDon't use temperature for the short info but time, flipper or monitor value.'
\t\t-xyz\txyz polarization analysis, implies -inc 6
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('All','*'), ('DNS (.d_dat)', '*.d_dat'))

  TRANSFORMATIONS=[\
  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['inc', 'ooff', 'b', 'bg', 'fr', 'v', 'vana', 'files', 'sample', 'setup', 'time', 'flipper', 'monitor', 'powder', 'xyz', 'split', 'dx', 'dy', 'nx', 'ny'] 
  file_options={'default': ['', 0, 1, [0, -1], ''],  # (prefix, omega_offset, increment, range, postfix)
                } # Dictionary storing specific options for files with the same prefix
  prefixes=[] # A list of all filenames to be imported
  mds_create=False # DNS data is not stored as .mds files as the import is fast
  VANADIUM_FILE=config.dns.VANADIUM_FILE # File name of vanadium file to be used for the correction
  BACKGROUND_FILE=None # File name of a background file to substract
  bg_corrected_nicr_data={} # dictionary of background corrected NiCr data
  system_bg={} # dictionary of background data from the system directory
  system_vana={} # dictionary of vanadium data from the system directory
  AUTO_BACKGROUND=False # try to select a background data from system_bg
  AUTO_VANADIUM=False # try to select a background data from system_bg
  CORRECT_FLIPPING=False # try automatic flipping-rato correction
  SCATTERING_PROPABILITY=0.1 # scattering_propability used for automatic flipping-ratio correction
  SHORT_INFO=[('temperature', lambda temp: 'at T='+str(temp), 'K')] # For the plots this is used to creat the short info
  SAMPLE_NAME='' # Name of the Sample for the data objects
  POWDER_DATA=False # If powder data is to be evaluated this is True.
  SPLIT=None # Integer number of files that belong to one measured sequence.
  ONLY_IMPORT_MULTIFILE=True # This is for the GUI open dialog.
  # to transform to reciprocal latice units the d_spacing is needed.
  D_SPACING_X=1.
  D_SPACING_Y=1.
  D_NAME_X='d_x'
  D_NAME_Y='d_y'
  TRANSFORM_Q=False
  XYZ_POL=False
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      Class constructor which is called with the command line arguments.
      Evaluates the command line arguments, creates a file list and
      starts the data readout procedure.
      In contrast to the most sessions this changes the generic constructor
      as the data is collected from a bunch of files corresponding to one measurement.
      
      @param arguments The command line arguments passed to the constructor.
    '''
    #++++++++++++++++ evaluate command line +++++++++++++++++++++++
    names=self.read_arguments(arguments) # get names and set options
    if names==None: # read_arguments returns none, if help option is set
      print self.LONG_HELP + self.SPECIFIC_HELP + self.LONG_HELP_END
      exit()
    elif (len(self.prefixes) < 1) and (len(names)<1): # show help, if there is no file in the list
      print self.SHORT_HELP
      exit()
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    self.os_path_stuff() # create temp folder according to OS
    self.read_vana_bg_nicr_files() # read NiCr files for flipping-ratio correction
    self.try_import_externals()
    names.sort()
    self.set_transformations()
    config.transformations.known_transformations+=self.TRANSFORMATIONS
    if len(names) > 1:
      self.find_prefixes(names)
    if not self.SPLIT is None:
      self.split_sequences(self.SPLIT)
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    self.prefixes.sort()
    for prefix in self.prefixes:
      # for every measured sequence read the datafiles and create a map/lineplot.
      self.read_files(prefix)

    if len(self.prefixes) == 0: # show help, if there is no valid file in the list
      print "No valid datafile found!"
      print self.SHORT_HELP
      exit()
    # set the first measurement as active
    self.active_file_data=self.file_data[self.prefixes[0]]
    self.active_file_name=self.prefixes[0]
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      Additional command line arguments for dns sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='inc':
          self.file_options['default'][2]=int(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='ooff':
          self.file_options['default'][1]=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='split':
          self.SPLIT=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='bg':
          self.BACKGROUND_FILE=argument
          last_argument_option=[False,'']
        elif last_argument_option[1]=='fr':
          self.CORRECT_FLIPPING=True
          self.SCATTERING_PROPABILITY=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='dx':
          self.D_SPACING_X=float(argument)
          self.TRANSFORM_Q=True
          last_argument_option=[False,'']
        elif last_argument_option[1]=='dy':
          self.D_SPACING_Y=float(argument)
          self.TRANSFORM_Q=True
          last_argument_option=[False,'']
        elif last_argument_option[1]=='nx':
          self.D_NAME_X=argument
          self.TRANSFORM_Q=True
          last_argument_option=[False,'']
        elif last_argument_option[1]=='ny':
          self.D_NAME_Y=argument
          self.TRANSFORM_Q=True
          last_argument_option=[False,'']
        elif last_argument_option[1]=='vana':
          self.VANADIUM_FILE=argument
          last_argument_option=[False,'']
        # Set sample name:
        elif last_argument_option[1]=='sample':
          self.SAMPLE_NAME=argument
          last_argument_option=[False,'']
        elif last_argument_option[1]=='setup':
          config.dns.SETUP_DIRECTORY=argument
          last_argument_option=[False,'']
        #+++++++++++++++ explicit file setting +++++++++++++++++++++++++++
        # Enty checking is quite extensive as there are many options which could
        # be given worng by the user.
        elif last_argument_option[1]=='files':
          new_options=[]
          new_options.append(argument)
          last_argument_option=[True,'files_1', new_options]
        # omega offset
        elif last_argument_option[1]=='files_1':
          try:
            last_argument_option[2].append(float(argument))
          except ValueError:
            print "Check your Syntax! Omega offset has to be a number, got '%s'.\nSyntax for -files: [prefix] [ooff] [inc] [from] [to] [postfix]" % argument
            exit()
          last_argument_option=[True,'files_2', last_argument_option[2]]
        # increment
        elif last_argument_option[1]=='files_2':
          try:
            last_argument_option[2].append(int(argument))
          except ValueError:
            print "Check your Syntax! Increment has to be integer, got '%s'.\nSyntax for -files: [prefix] [ooff] [inc] [from] [to] [postfix]" % argument
            exit()            
          last_argument_option=[True,'files_3', last_argument_option[2]]
        # from
        elif last_argument_option[1]=='files_3':
          try:
            last_argument_option[2].append([int(argument)])
          except ValueError:
            print "Check your Syntax! From has to be integer, got '%s'.\nSyntax for -files: [prefix] [ooff] [inc] [from] [to] [postfix]" % argument
            exit()            
          last_argument_option=[True,'files_4', last_argument_option[2]]
        # to
        elif last_argument_option[1]=='files_4':
          try:
            last_argument_option[2][3].append(int(argument))
          except ValueError:
            print "Check your Syntax! To has to be integer, got '%s'.\nSyntax for -files: [prefix] [ooff] [inc] [from] [to] [postfix]" % argument
            exit()            
          last_argument_option=[True,'files_5', last_argument_option[2]]
        # postfix
        elif last_argument_option[1]=='files_5':
          last_argument_option[2].append(argument)
          split=last_argument_option[2][0].rsplit(os.sep, 1)
          if len(split)==2:
            directory=split[0]
            file_prefix=split[1]
          else:
            directory='.'
            file_prefix=split[0]
          file_postfix=str(last_argument_option[2][3][0])+last_argument_option[2][4]
          try:
            first_file=sorted([file for file in os.listdir(directory) \
                               if file.startswith(file_prefix) and file.endswith(file_postfix)])[0]
          except IndexError:
            erg=last_argument_option[2]
            print """No file found for the -files options:
            Pefix='%s'
            Omega offset='%g'
            Increment='%i'
            From,To='%i','%i'
            Postfix='%s' """ % (erg[0], erg[1], erg[2], erg[3][0], erg[3][1], erg[4])
            exit()
          self.prefixes.append(directory+os.sep+first_file)
          self.file_options[directory+os.sep+first_file]=last_argument_option[2]
          last_argument_option=[False,'']
        else:
          found=False
        #--------------- explicit file setting ---------------------------
      elif argument=='-b':
        self.AUTO_BACKGROUND=True
      elif argument=='-v':
        self.AUTO_VANADIUM=True
      elif argument=='-time':
        self.SHORT_INFO=[('time', lambda time: 'with t='+str(time), 's')]
      elif argument=='-powder':
        self.POWDER_DATA=True
      elif argument=='-monitor':
        self.SHORT_INFO=[('monitor', lambda monitor: 'with monitor='+str(monitor), 'counts')]
      elif argument=='-flipper':
        def flipper_on(current):
          if current > 0.1:
            return "spin-flip"
          else:
            return "non spin-flip"
        self.SHORT_INFO=[('flipper', flipper_on, '')]
      elif argument=='-xyz':
        self.XYZ_POL=True
        self.file_options['default'][2]=6
        def flipper_on(current):
          if current > 0.1:
            return "spin-flip"
          else:
            return "non spin-flip"
        self.SHORT_INFO=[('pol_channel', lambda P: str(P)+'-', ''), 
                          ('flipper', flipper_on, '')]
      else:
        found=False
    return (found, last_argument_option)

  def add_file(self, filenames, append=True):
    '''
      In contrast to other sessions this is only called
      from the gui to add new files.
      Works as if the filenames had been given via commandline.
    '''
    filenames.sort()
    if len(filenames) > 1:
      self.find_prefixes(filenames)
    else:
      return False
    self.prefixes.sort()
    new_prefixes=[pf for pf in self.prefixes if not pf in self.file_data]
    if len(new_prefixes)>0:
      for prefix in new_prefixes:
        self.read_files(prefix)
      self.change_active(name=new_prefixes[0])
      return True
    else:
      return False
  
  def read_files(self, file):
    '''
      Function to read data files for one measurement. 
      The files are split by their prefixes.
    '''
    # read the options for this sequence of files
    prefix=self.file_options[file][0]
    omega_offset=self.file_options[file][1]
    increment=self.file_options[file][2]
    num_range=self.file_options[file][3]
    postfix=self.file_options[file][4]
    # split folder and filename of prefix
    file_split=prefix.rsplit(os.sep, 1)
    if len(file_split)==1:
      folder='.'
      fileprefix=file_split[0]
    else:
      folder, fileprefix=file_split
    # create a list of all files starting with the fileprefix and ending with postfix
    file_list=[lfile for lfile in os.listdir(folder) if lfile.startswith(fileprefix) and lfile.endswith(postfix)]
    if len(file_list)==0:
      return None
    file_list.sort()
    # Read the raw data
    self.file_data[file+'|raw_data']=[]
    print "Reading files %s{num}%s with num from %i to %i." % (prefix, postfix, num_range[0], num_range[1])
    for file_name in file_list:
      # get integer number of the file, catch errors form wrong file selection
      try:
        active_number=int(os.path.join(folder, file_name).rsplit(postfix)[0].split(prefix, 1)[1])
      except ValueError:
        continue
      if (active_number>=num_range[0]) and (active_number<=num_range[1] or num_range[1]==-1):
        # read the datafile into a MeasurementData object.
        dataset=read_data.dns.read_data(os.path.join(folder, file_name))
        dataset.number=str(active_number)
        self.file_data[file+'|raw_data'].append(dataset)
    print "\tRead, creating map."
    self.create_maps(file)
    return None
  
  def create_maps(self, file):
    '''
      Crates a MeasurementData object which can be used to
      plot color maps or lineplots of the measurement.
      For Powder data it is only shown as 2Theta vs intensity.
      For single crystal it is a map in q_x,q_y.
    '''
    # select the raw data for this measurement
    scans=self.file_data[file+'|raw_data']
    self.file_data[file]=[]
    # read the options for this sequence of files
    prefix=self.file_options[file][0]
    omega_offset=self.file_options[file][1]
    increment=self.file_options[file][2]
    num_range=self.file_options[file][3]
    postfix=self.file_options[file][4]
    # Functoin used to append data to the object
    def append_to_map(point):
      return [file_number, 
              round(omega-omega_offset-detector_bank_2T, 1), 
              round(omega-detector_bank_2T, 1), 
              point[0]*config.dns.DETECTOR_ANGULAR_INCREMENT+config.dns.FIRST_DETECTOR_ANGLE-detector_bank_2T, 
              point[0]
              ]+point[1:]+point[1:]+[0, 0]
    # go through every raw data object.
    for i, scan in enumerate(scans):
      if i<increment:
        if self.XYZ_POL:
          channels=['x', 'x', 'y', 'y', 'z', 'z']
          scan.dns_info['pol_channel']=channels[i]
        # Create the objects for every polarization chanel
        columns=[['Filenumber', ''], ['Omega', '\302\260'], ['OmegaRAW', '\302\260'], 
                 ['2Theta', '\302\260'], ['Detector', '']]+\
                 [[scan.dimensions()[j], scan.units()[j]] for j in range(1, len(scan.units()))]+\
                 [['I_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-1)/2)]+\
                 [['error_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-1)/2)]+\
                 [['q_x', '\303\205^{-1}'], ['q_y', '\303\205^{-1}']]
        self.file_data[file].append(DNSMeasurementData(columns, [], 1, 3, (len(scan.units())-1)/2+5, zdata=5))
        # set some parameters for the object
        active_map=self.file_data[file][i]
        active_map.number=str(i)
        active_map.dns_info=scan.dns_info
        active_map.number_of_channels=(len(scan.units())-1)/2
        active_map.short_info=" ".join([info[1](scan.dns_info[info[0]])+info[2] for info in self.SHORT_INFO])
        active_map.sample_name=self.SAMPLE_NAME
        active_map.info= "\n".join(map(lambda item: item[0]+': '+str(item[1]),
                                    sorted(scan.dns_info.items())))
      # add the data
      data=[point for point in scan]
      file_number=int(scan.number)
      detector_bank_2T=scan.dns_info['detector_bank_2T']
      omega=scan.dns_info['omega']
      map(self.file_data[file][i%increment].append, map(append_to_map, data))
    # perform calculations
    self.active_file_data=self.file_data[file]
    if self.CORRECT_FLIPPING:
      # assign flipping chanels to nicr-data
      self.correct_flipping_ratio(self.SCATTERING_PROPABILITY)
    for dnsmap in self.active_file_data:
      sys.stdout.write("\tMap %s created, perfoming datatreatment: " % dnsmap.number)
      sys.stdout.flush()
      if self.AUTO_BACKGROUND:
        self.find_background_data(dnsmap)
      if self.AUTO_VANADIUM:
        self.find_vanadium_data(dnsmap)
      if self.BACKGROUND_FILE:
        dnsmap.background_data=read_data.dns.read_data(self.BACKGROUND_FILE)
      if self.VANADIUM_FILE:
        vana_data=read_data.dns.read_data(self.VANADIUM_FILE, print_comments=False)
        if vana_data!='NULL':
          dnsmap.vanadium_data=vana_data
        else:
          # when the file is not raw data read vanadium_data from a 2th file
          vana_data=GenericSession.read_file(self, self.VANADIUM_FILE)[0]
          vana_data.sort(0)
          # to make it possible to correct for this data, round the 2Theta value
          dnsmap.vanadium_data=vana_data
          dnsmap.vanadium_correct_by_detector=False
        # normalize vanadium data to stay at about counts/s
        max_p=max(vana_data.data[1].values)
        min_p=min(vana_data.data[1].values)
        cen_p=(max_p-min_p)/2.+min_p
        vana_data.process_function(lambda point: [point[0], point[1]/cen_p, point[2]/cen_p])
      sys.stdout.write("calculate wavevectors, ")
      sys.stdout.flush()
      dnsmap.calculate_wavevectors()
      if self.POWDER_DATA:
        new=dnsmap.prepare_powder_data()
        self.active_file_data[self.active_file_data.index(dnsmap)]=new
        if new.flipping_correction:
          # reassign new data for other spin-flip channel
          fc=new.flipping_correction
          fc[2].flipping_correction=(not fc[0], dnsmap.flipping_correction[1], new)
          dnsmap=new
      dnsmap.make_corrections()
      sys.stdout.write("\n")
      sys.stdout.flush()
      if self.TRANSFORM_Q:
        dnsmap.unit_trans(self.TRANSFORMATIONS)
    # Seperate scattering for powder data x,y,z polarization analysis
    if self.XYZ_POL and self.POWDER_DATA and self.CORRECT_FLIPPING:
      af=self.active_file_data
      # para_1= 2 * (SF_x + SF_y - 2 * SF_z)
      para_1=2.*(af[0]+af[2]-2.*af[4])
      para_1.short_info='para_1'
      para_1.number='0'
      # para_2= -2 * (NSF_x + NSF_y - 2 * NSF_z)
      para_2=-2.*(af[1]+af[3]-2.*af[5])
      para_2.short_info='para_2'
      para_2.number='0'
      # para= <para_1,para_2>
      para=0.5 * para_1 + 0.5 * para_2
      para.short_info='paramagnetic'
      para.number='0'
      # sp_inc= 1.5 * (3 * SF_z - SF_x - SF_y)
      sp_inc=1.5*(3.*af[4]-af[0]-af[2])
      sp_inc.short_info='spin incoherent'
      sp_inc.number='0'
      # nu_coh= NSF_z - 0.5 * para - 1/3 * sp_inc
      nu_coh=af[5]-0.5*para-1./3.*sp_inc
      nu_coh.short_info='nuclear coherent'
      nu_coh.number='0'
      self.active_file_data.insert(0, sp_inc)
#      self.active_file_data.insert(0, para_1)
#      self.active_file_data.insert(0, para_2)
      self.active_file_data.insert(0, para)
      self.active_file_data.insert(0, nu_coh)

  def find_background_data(self, dataset):
    '''
      Try to find a background data data with the right currents for this dataset.
    '''
    detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
    # get the currents
    flip=round(float(dataset.dns_info['flipper']), 2)
    flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
    c_a=round(float(dataset.dns_info['C_a']), 2)
    c_b=round(float(dataset.dns_info['C_b']), 2)
    c_c=round(float(dataset.dns_info['C_c']), 2)
    c_z=round(float(dataset.dns_info['C_z']), 2)
    # create a key for the currents and search for it in the
    # background dictionary
    key=(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)
    if not key in self.system_bg:
      # search for near setting
      for i in range(-2, 3):
        key=(detector+i, flip, flip_cmp, c_a, c_b, c_c, c_z)
        if key in self.system_bg:
          break
    if key in self.system_bg: 
      dataset.background_data=self.system_bg[key]

  def find_vanadium_data(self, dataset):
    '''
      Try to find a background data data with the right currents for this dataset.
    '''
    # get the currents
    flip=round(float(dataset.dns_info['flipper']), 2)
    flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
    c_a=round(float(dataset.dns_info['C_a']), 2)
    c_b=round(float(dataset.dns_info['C_b']), 2)
    c_c=round(float(dataset.dns_info['C_c']), 2)
    c_z=round(float(dataset.dns_info['C_z']), 2)
    # create a key for the currents and search for it in the
    # background dictionary
    key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
    if key in self.system_vana: 
      dataset.vanadium_data=self.system_vana[key]

  def find_prefixes(self, names):
    '''
      Try to find prefixes from a list of filenames.
      config.dns.min_prefix_length is used to split different
      sets of files.
    '''
    names.sort()
    def split_prefix_postfix(name):
      pre_index=max(0, name.rfind(os.sep))
      post_index=len(name)
      while not name[pre_index].isdigit():
        pre_index+=1
      while not name[post_index-1].isdigit():
        post_index-=1
      prefix=name[0:pre_index]
      number=name[pre_index:post_index]
      postfix=name[post_index:]
      return (prefix, number, postfix)
    names_pre_post=map(split_prefix_postfix, names)
    found_prefixes={}
    for prefix, number, postfix in names_pre_post:
      if prefix in found_prefixes:
        if int(found_prefixes[prefix][2])+1==int(number):
          found_prefixes[prefix][2]=number
        else:
          found_prefixes[prefix+'_%s' % found_prefixes[prefix][1]]=found_prefixes[prefix]
          found_prefixes[prefix]=[prefix, number, number, postfix]
      else:
        found_prefixes[prefix]=[prefix, number, number, postfix]
    for item in found_prefixes.items():
      i=0
      while item[1][1][:i]==item[1][2][:i]:
        i+=1
        if i>len(item[1][1]):
          print "Sorry, could not get prefixes right, try -files option."
          exit()
      if len(item[1][0].rsplit(os.sep, 1))==1:
        add_folder='./'
      else:
        add_folder=''
      self.prefixes.append(add_folder+item[1][0]+item[1][1]+item[1][3])
      self.file_options[add_folder+item[1][0]+item[1][1]+item[1][3]]=[item[1][0]+item[1][1][:i-1], 
                                                           self.file_options['default'][1], 
                                                           self.file_options['default'][2], 
                                                           [int(item[1][1][i-1:]), 
                                                           int(item[1][2][i-1:])], 
                                                           item[1][3]]    
  
  def split_sequences(self, length):
    '''
      Split the file_options and prefixes at every 
      [length] number.
    '''
    for file in self.prefixes:
      options=self.file_options[file]
      # Create a list of all files.
      file_split=options[0].rsplit(os.sep, 1)
      if len(file_split)==1:
        folder='.'
        fileprefix=file_split[0]
      else:
        folder, fileprefix=file_split
      file_list=[lfile for lfile in os.listdir(folder) if lfile.startswith(fileprefix) and lfile.endswith(options[4])]
      file_list.sort()
      if options[3][1]==-1:
        options[3][1]=int(file_list[-1].split(fileprefix, 1)[1].rsplit(options[4], 1)[0])
      options[3][0]=max(int(file_list[0].split(fileprefix, 1)[1].rsplit(options[4], 1)[0])
                        , options[3][0])
      if options[3][1]-options[3][0]>length:
        new_options=[options[0:3]+[ [int(options[3][0]+i*length), int(min(options[3][0]+(i+1)*length-1, options[3][1]))] ]+[options[4]] for i in range(int((options[3][1]-options[3][0])/length +1))]
        file_dict={}
        def put_in_dict(name):
          file_dict[int(name.split(fileprefix, 1)[1].rsplit(options[4], 1)[0])] = name
        map(put_in_dict, file_list)
        self.file_options[folder+os.sep+file_dict[new_options[0][3][0]]]=new_options[0]
        for new_option in new_options[1:]:
          self.prefixes.append(folder+os.sep+file_dict[new_option[3][0]])
          self.file_options[folder+os.sep+file_dict[new_option[3][0]]]=new_option    

  def create_menu(self):
    '''
      Create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='DNS'>
        <menuitem action='SetOmegaOffset' />
        <menuitem action='SetIncrement' />
        <menuitem action='SetDSpacing' />
        <menuitem action='SeperateScattering' />
        <menuitem action='SeperatePreset' />
        <separator name='dns1' />
        <menuitem action='ReloadActive' />
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "DNS", None,                             # name, stock id
                "DNS", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SetOmegaOffset", None,                             # name, stock id
                "Omega Offset...", None,                    # label, accelerator
                None,                                   # tooltip
                self.change_omega_offset ),
            ( "SetDSpacing", None,                             # name, stock id
                "d-spacing...", None,                    # label, accelerator
                None,                                   # tooltip
                self.change_d_spacing ),
            ( "SetIncrement", None,                             # name, stock id
                "Change Increment", None,                    # label, accelerator
                "Change Increment between files with same Polarization",                                   # tooltip
                self.change_increment ),
            ( "CorrectFlipping", None,                             # name, stock id
                "Correct for flipping-ratio", None,                    # label, accelerator
                "Correct scattering for the finite flipping-ratio.",                                   # tooltip
                self.correct_flipping_dialog ),
            ( "SeperateScattering", None,                             # name, stock id
                "Seperate Scattering", None,                    # label, accelerator
                "Calculate seperated scattering parts from polarization directions.",                                   # tooltip
                self.seperate_scattering ),
            ( "SeperatePreset", None,                             # name, stock id
                "Seperate from Preset", None,                    # label, accelerator
                "Calculate seperated scattering parts from polarization directions from presets.",               # tooltip
                self.seperate_scattering_preset ),
            ( "ReloadActive", None,                             # name, stock id
                "Reload Active Measurement", 'F5',                    # label, accelerator
                None,               # tooltip
                self.reload_active_measurement ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
  def plot_all(self):
    '''
      Plot everything selected from all files.
      This overwrites the generic method to remove the
      raw date from beeing ploted.
    '''
    for name in self:
      if not name.endswith("|raw_data"):
        print "Plotting '" + name + "' sequences."
        print self.plot_active()
  
  def set_transformations(self):
    '''
      Set the transformation options from q_x to dx*,dy* 
      from the dx,dy values given on command line.
    '''
    d_star_x=2.*pi/self.D_SPACING_X
    d_star_y=2.*pi/self.D_SPACING_Y
    self.TRANSFORMATIONS=[\
      ['q_x','\303\205^{-1}',1./d_star_x,0,self.D_NAME_X,'r.l.u.'],\
      ['q_y','\303\205^{-1}',1/d_star_y,0,self.D_NAME_Y,'r.l.u.'],\
                          ]
  
  def read_vana_bg_nicr_files(self):
    '''
      Read all NiCr files in the chosen directory and correct the backgound.
    '''
    directory=config.dns.SETUP_DIRECTORY
    try:
      file_list=sorted(os.listdir(directory))
    except OSError:
      file_list=[]
    nicr_files=sorted(filter(lambda name: name.startswith(config.dns.NICR_FILE_WILDCARD[0]), 
                      filter(lambda name: name.endswith(config.dns.NICR_FILE_WILDCARD[1]), 
                             file_list)))
    bg_files=sorted(filter(lambda name: name.startswith(config.dns.BACKGROUND_WILDCARD[0]), 
                      filter(lambda name: name.endswith(config.dns.BACKGROUND_WILDCARD[1]), 
                             file_list)))
    vana_files=sorted(filter(lambda name: name.startswith(config.dns.VANADIUM_WILDCARD[0]), 
                      filter(lambda name: name.endswith(config.dns.VANADIUM_WILDCARD[1]), 
                             file_list)))
    # dictionaries with the helmholz parameters are used to store the data
    nicr_data={}
    bg_data={}
    vana_data={}
    for file_name in nicr_files:
      dataset=read_data.dns.read_data(os.path.join(directory, file_name))
      detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      nicr_data[(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)]=dataset
    for file_name in bg_files:
      dataset=read_data.dns.read_data(os.path.join(directory, file_name))
      detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      bg_data[(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)]=dataset
    self.system_bg=bg_data
    for file_name in vana_files:
      dataset=read_data.dns.read_data(os.path.join(directory, file_name))
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      vana_data[(flip, flip_cmp, c_a, c_b, c_c, c_z)]=dataset
    self.system_vana=vana_data
    # correct the background
    bg_corrected_data={}
    if use_numpy:
      def subtract_background(point):
        bg=background_data.data
        point[1]-=array(bg[1].values)
        point[2]=sqrt(point[2]**2+array(bg[2].values)**2)
        return point
    else:
      def subtract_background(point):
        index=background_data.data[0].values.index(point[0])
        bg=background_data.get_data(index)
        point[1]-=bg[1]
        point[2]=sqrt(point[2]**2+bg[2]**2)
        return point      
    for key, data in nicr_data.items():
      if key in bg_data:
        background_data=bg_data[key]
        data.process_function(subtract_background)
        bg_corrected_data[key]=data
    self.bg_corrected_nicr_data=bg_corrected_data
  
  def correct_flipping_ratio(self, scattering_propability=0.1):
    '''
      This function assigns the right NiCr measurements to the data sequences.
      The flipper and Helmolz currents are used to identify the right data.process_function
      
      @return If files could be found with the right settings.
    '''
    # search for appropiate standard measurements
    data_nicr={}
    for dataset in self.active_file_data:
      # get the currents
      detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      # create a key for the currents and search for it in the
      # background corrected nicr data dictionary
      key=(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)
      if not key in self.bg_corrected_nicr_data:
        # search for near setting
        for i in range(-2, 3):
          key=(detector+i, flip, flip_cmp, c_a, c_b, c_c, c_z)
          if key in self.bg_corrected_nicr_data:
            break
      if key in self.bg_corrected_nicr_data:
        # there have to be two flipper channels
        if not key[3:] in data_nicr:
          data_nicr[key[3:]]=[(key[1:3]==(0., 0.), self.bg_corrected_nicr_data[key], dataset)]
        elif len(data_nicr[key[3:]])==1:
          data_nicr[key[3:]].append((key[1:3]==(0., 0.), self.bg_corrected_nicr_data[key], dataset))
          # put spin-flip channels first
          data_nicr[key[3:]].sort()
          data_nicr[key[3:]].reverse()
        else:
          print "To many chanels for %s, skipping." % key
      else:
        print "NiCr for detector: %g; currents:%i,%i,%i,%i not Found!" %( key[0], key[3], key[4], key[5], key[6] )
    # calculate flipping-ration from nicr data
    if use_numpy:
      def calc_flipping_ratio(point):
        pp=item[1][1].data
        point[1]/=array(pp[1].values)
        point[2]*=0.
        return point
    else:
      def calc_flipping_ratio(point):
        index=item[1][1].data[0].values.index(point[0])
        pp=item[1][1].get_data(index)
        point[1]/=pp[1]
        point[2]=0.
        return point      
    data_flippingratio={}
    for key, item in data_nicr.items():
      if len(item)==1:
        print "Lonely channel found, skipping"
        continue
      else:
        flipping_ratio=item[0][1]
        flipping_ratio.process_function(calc_flipping_ratio)
        data_flippingratio[key]=(flipping_ratio, item[0][2], item[1][2])
    for item in data_flippingratio.values():
      # assign nicr to the chanels
      item[1].flipping_correction=(True, item[0], item[2])
      item[1].scattering_propability=scattering_propability
      item[2].flipping_correction=(False, item[0], item[1])
      item[2].scattering_propability=scattering_propability
  
  #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  def correct_flipping_dialog(self, action, window):
    scattering_propability=0.1
    self.correct_flipping_ratio(scattering_propability)
    window.replot()
  
  def change_omega_offset(self, action, window):
    '''
      A dialog to change the omega offset of the active map.
      If no map is active at the moment it does nothing.
    '''
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for ooff input +++++
    ooff_dialog=gtk.Dialog(title='Change omega offset:')
    ooff_dialog.set_default_size(100,50)
    ooff_dialog.add_button('OK', 1)
    ooff_dialog.add_button('Apply', 2)
    ooff_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,1,False)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text(str(self.file_options[self.active_file_name][1]))
    input_filed.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    up_button=gtk.Button("+")
    down_button=gtk.Button("-")
    table.attach(up_button,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                         0,
                0,                         0);
    table.attach(down_button,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                0,                         0,
                0,                         0);
    def toggle_up(*ignore):
      input_filed.set_text(str((float(input_filed.get_text())+10)%360))
      ooff_dialog.response(2)
    def toggle_down(*ignore):
      input_filed.set_text(str((float(input_filed.get_text())-10)%360))
      ooff_dialog.response(2)
    up_button.connect('clicked', toggle_up)
    down_button.connect('clicked', toggle_down)
    ooff_dialog.vbox.add(table)
    ooff_dialog.show_all()
    #----- Create a dialog window for ooff input -----
    # wait for user response
    result=ooff_dialog.run()
    while result > 1:
      # response is Apply
      ooff=float(input_filed.get_text())
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      if self.TRANSFORM_Q:
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
      window.replot()
      result=ooff_dialog.run()
    if result==1:
      # response is OK
      ooff=float(input_filed.get_text())
      self.file_options[self.active_file_name][1]=ooff
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      window.replot()
    ooff_dialog.destroy()

  def change_d_spacing(self, action, window):
    '''
      A dialog to change the d-spacing of the plots.
    '''
    #+++++ Create a dialog window for ooff input +++++
    ds_dialog=gtk.Dialog(title='Set d-spacing for x and y directions:')
    ds_dialog.set_default_size(100,100)
    ds_dialog.add_button('OK', 1)
    ds_dialog.add_button('Apply', 2)
    ds_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,3,False)
    label=gtk.Label()
    label.set_text('Direction')
    table.attach(label, 0,1, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('label')
    table.attach(label, 1,2, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('d-spacing')
    table.attach(label, 2,3, 0,1,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('x')
    table.attach(label, 0,1, 1,2,  gtk.EXPAND|gtk.FILL,0, 0,0);
    label=gtk.Label()
    label.set_text('y')
    table.attach(label, 0,1, 2,3,  gtk.EXPAND|gtk.FILL,0, 0,0);
    input_filed_nx=gtk.Entry()
    input_filed_nx.set_width_chars(4)
    input_filed_nx.set_text(self.D_NAME_X)
    input_filed_nx.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed_nx,
                # X direction #          # Y direction
                1, 2,                      1, 2,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_ny=gtk.Entry()
    input_filed_ny.set_width_chars(4)
    input_filed_ny.set_text(self.D_NAME_Y)
    input_filed_ny.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed_ny,
                # X direction #          # Y direction
                1, 2,                      2, 3,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_dx=gtk.Entry()
    input_filed_dx.set_width_chars(4)
    input_filed_dx.set_text(str(self.D_SPACING_X))
    input_filed_dx.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed_dx,
                # X direction #          # Y direction
                2, 3,                      1, 2,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    input_filed_dy=gtk.Entry()
    input_filed_dy.set_width_chars(4)
    input_filed_dy.set_text(str(self.D_SPACING_Y))
    input_filed_dy.connect('activate', lambda *ignore: ooff_dialog.response(2))
    table.attach(input_filed_dy,
                # X direction #          # Y direction
                2, 3,                      2, 3,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);

    ds_dialog.vbox.add(table)
    ds_dialog.show_all()
    #----- Create a dialog window for ooff input -----
    # wait for user response
    result=ds_dialog.run()
    while result > 0:
      try:
        # response is Apply
        self.D_NAME_X=input_filed_nx.get_text()
        self.D_NAME_Y=input_filed_ny.get_text()
        self.D_SPACING_X=float(input_filed_dx.get_text())
        self.D_SPACING_Y=float(input_filed_dy.get_text())
        self.set_transformations()
        self.active_file_data[window.index_mess].calculate_wavevectors()
        self.active_file_data[window.index_mess].unit_trans(self.TRANSFORMATIONS)
        window.replot()
        if result==1:
          break
        result=ds_dialog.run()
      except ValueError:
        result=ds_dialog.run()
        if result==1:
          break
    ds_dialog.destroy()

  def change_increment(self, action, window):
    '''
      Change the increments between files of the same polarization
      chanel. New maps are created after this change.
    '''
    if not self.active_file_name in self.file_options:
      return None
    #+++++ Create a dialog window for increment input +++++
    inc_dialog=gtk.Dialog(title='Change increment for same polarization:')
    inc_dialog.set_default_size(100,50)
    inc_dialog.add_button('OK', 1)
    inc_dialog.add_button('Cancle', 0)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text(str(self.file_options[self.active_file_name][2]))
    input_filed.show()
    input_filed.connect('activate', lambda *ignore: inc_dialog.response(1))
    inc_dialog.vbox.add(input_filed)
    #----- Create a dialog window for increment input -----
    result=inc_dialog.run()
    if result==1:
      # Answer is OK
      inc=int(input_filed.get_text())
      self.file_options[self.active_file_name][2]=inc
      self.create_maps(self.active_file_name)
      object=self.file_data[self.active_file_name]
      window.change_active_file_object((self.active_file_name, object))
    inc_dialog.destroy()
  
  def seperate_scattering_preset(self, action, window):
    '''
      A selection dialog to choose a preset for seperate_scattering.
    '''
    keys=sorted(config.dns.SEPERATION_PRESETS.keys())
    preset_box=gtk.combo_box_new_text()
    preset_box.append_text(keys[0])
    for key in keys[1:]:
      preset_box.append_text(key)
    preset_dialog=gtk.Dialog(title='Add polarization:')
    preset_dialog.set_default_size(100,50)
    preset_dialog.add_button('OK', 1)
    preset_dialog.add_button('Cancle', 0)
    preset_dialog.vbox.add(preset_box)
    preset_dialog.show_all()
    result=preset_dialog.run()
    key=keys[preset_box.get_active()]
    preset_dialog.destroy()
    if result==1:
      self.seperate_scattering(action, window, config.dns.SEPERATION_PRESETS[key])
  
  def seperate_scattering(self, action, window, preset=None):
    '''
      Add or substract measured polarizations from each other
      to calculate e.g. coherent magnetic scattering.
    '''
    if not self.active_file_name in self.file_options:
      return None
    # build a list of DNSMeasurementData objects in active_file_data for the polarizations
    polarization_list=[(object, self.active_file_name) for object in self.active_file_data if "dns_info" in dir(object)]
    for name, file_data_tmp in sorted(self.file_data.items()):
      polarization_list+=[(object, name) for object in file_data_tmp if (("dns_info" in dir(object)) and not (('|raw_data' in name)or (self.active_file_name is name)))]
    combine_list=[]
    def add_object():
      add_dialog=gtk.Dialog(title='Add polarization:')
      add_dialog.set_default_size(100,50)
      add_dialog.add_button('OK', 1)
      add_dialog.add_button('Cancle', 0)
      align_table=gtk.Table(4,1,False)
      label=gtk.Label('+/-')
      align_table.attach(label, 0,1, 0, 1, 0,0, 0,0);
      sign=gtk.CheckButton()
      align_table.attach(sign, 1,2, 0, 1, 0,0, 0,0);
      multiplier=gtk.Entry()
      multiplier.set_text('1')
      align_table.attach(multiplier, 2,3, 0, 1, 0,0, 0,0);
      object_box=gtk.combo_box_new_text()
      object_box.append_text('0-('+polarization_list[0][0].short_info+')')
      for i, object in enumerate(polarization_list[1:]):
        object_box.append_text(str(i+1)+'-('+object[0].short_info+','+object[1]+')')
      object_box.set_active(0)
      align_table.attach(object_box, 3,4, 0,1, gtk.EXPAND|gtk.FILL,0, 0,0)
      add_dialog.vbox.add(align_table)
      add_dialog.show_all()
      result=add_dialog.run()
      if result==1:
        if sign.get_active():
          sign='-'
        else:
          sign='+'
        combine_list.append( (object_box.get_active(), sign, float(multiplier.get_text())) )
        label=gtk.Label(sign+multiplier.get_text()+'*'+object_box.get_active_text())
        label.show()
        function_table.attach(label, len(combine_list)-1,len(combine_list), 0,1, 0,0, 0,0)
      add_dialog.destroy()
    combine_dialog=gtk.Dialog(title='Combination of polarizations:')
    combine_dialog.set_default_size(100,50)
    combine_dialog.add_button('Add', 2)
    combine_dialog.add_button('OK', 1)
    combine_dialog.add_button('Cancle', 0)
    table=gtk.Table(3,1,False)
    input_filed=gtk.Entry()
    input_filed.set_width_chars(4)
    input_filed.set_text('Result')
    table.attach(input_filed,
                # X direction #          # Y direction
                0, 1,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    label=gtk.Label(" = ")
    table.attach(label,
                # X direction #          # Y direction
                1, 2,                      0, 1,
                0,                         0,
                0,                         0);
    function_table=gtk.Table(1,1,False)
    table.attach(function_table,
                # X direction #          # Y direction
                2, 3,                      0, 1,
                gtk.EXPAND | gtk.FILL,     0,
                0,                         0);
    combine_dialog.vbox.add(table)
    combine_dialog.show_all()
    # if a preset is used create the right list and show the function
    if preset is None:
      add_object()
    else:
      combine_list=preset
      for i, item in enumerate(combine_list):
        try:
          label=gtk.Label(item[1]+str(item[2])+'*'+str(i)+'-('+polarization_list[item[0]][0].short_info+')')
          label.show()
          function_table.attach(label, i,i+1, 0,1, 0,0, 0,0)        
        except IndexError:
          combine_dialog.destroy()
          return None
    result=combine_dialog.run()
    while result>1:
      add_object()
      result=combine_dialog.run()
    if result==1:
      self.calculate_combination(combine_list, polarization_list, input_filed.get_text())
    combine_dialog.destroy()
  
  def calculate_combination(self, combine_list, polarization_list, title):
    '''
      Calculate a combination of polarization directions as
      set in the combine_list.
    '''
    if combine_list[0][1] == '+':
      result=combine_list[0][2]*polarization_list[combine_list[0][0]][0]
    else:
      result=-1.*combine_list[0][2]*polarization_list[combine_list[0][0]][0]
    for object, sign, multiplier in combine_list[1:]:
      if sign == '+':
        result=result+multiplier*polarization_list[object][0]
      else:
        result=result-multiplier*polarization_list[object][0]
      if result is None:
        message=gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE, 
                                  message_format='You can only combine polarizations with the same number of measured points!')
        message.run()
        message.destroy()
        return None
    result.short_info=title
    result.number=str(len(polarization_list))
    self.active_file_data.append(result)

  def reload_active_measurement(self, action, window):
    '''
      Reload the measurement active in the GUI.
    '''
    self.read_files(self.active_file_name.rsplit('|raw_data')[0])
    window.change_active_file_object((self.active_file_name, self.file_data[self.active_file_name]))

class DNSMeasurementData(MeasurementData):
  '''
    Class derived from MeasurementData to be more suitable for DNS measurements.
    Datatreatment is done here and additional data treatment functions should
    be put here, too.
  '''

  dns_info={}
  scan_line=3
  scan_line_constant=1
  number_of_channels=1
  vanadium_data=None
  vanadium_correct_by_detector=True
  background_data=None
  # if a flipping correction is made this is a list of
  # [SF-Chanel?, nicr-data, other_DNSMeasurement]
  flipping_correction=None 
  scattering_propability=0.1
  
  def prepare_powder_data(self):
    '''
      Change settings for own dataset to be used as powderdata.
      This includes 1d plot of 2Theta vs. Intensity and
      avaridge over points with same 2Theta value.
    '''
    sys.stdout.write("combine same 2Theta, ")
    sys.stdout.flush()
    from copy import deepcopy
    self.sort(3)
    self.ydata=self.zdata
    self.zdata=-1
    self.xdata=3
    # create new object with empty data
    new=deepcopy(self)
    for i in range(len(new.data)):
      new.data[i].values=[]
    nc=self.number_of_channels
    new.number_of_points=0
    for point in self:
      if point[3] in new.data[3].values:
        index=new.data[3].values.index(point[3])
        for i in range(nc):
          new.data[i+5].values[index]=(new.data[i+5].values[index]+point[i+5])/2.
          new.data[nc+i+5].values[index]=sqrt((new.data[nc+i+5].values[index]**2+point[nc+i+5]**2)/2.)
          new.data[nc*2+5].values[index]=(new.data[nc*2+5].values[index]+point[nc*2+5])/2.
          new.data[nc*3+5].values[index]=sqrt((new.data[nc*3+5].values[index]**2+point[nc*3+5]**2)/2.)
      else:
        new.append(point)
    return new
  
  def calculate_wavevectors(self):
    '''
      Calculate the wavevectors from omega, 2Theta and lambda.
    '''
    qx_index=len(self.units())-2
    qy_index=qx_index+1
    lambda_n=self.dns_info['lambda_n']
    two_pi_over_lambda=2*pi/lambda_n
    grad_to_rad=pi/180.
    # calculation of the wavevector, also works with arrays
    def angle_to_wavevector(point):
      output=point
      output[qx_index]=(cos(-point[1]*grad_to_rad)-\
                cos(-point[1]*grad_to_rad + point[3]*grad_to_rad))*\
                two_pi_over_lambda
      output[qy_index]=(sin(-point[1]*grad_to_rad)-\
                sin(-point[1]*grad_to_rad + point[3]*grad_to_rad))*\
                two_pi_over_lambda
      return output    
    self.process_function(angle_to_wavevector)
    self.data[qx_index].unit='\303\205^{-1}'
    self.data[qy_index].unit='\303\205^{-1}'
    self.data[qx_index].dimension='q_x'
    self.data[qy_index].dimension='q_y'
    self.xdata=qx_index
    self.ydata=qy_index
  
  def change_omega_offset(self, omega_offset):
    '''
      Recalculate omega and q_x, q_y for a new offset value.
    '''
    def calc_omega(point):
      point[1]=point[2]-omega_offset
      return point
    self.process_function(calc_omega)
    self.calculate_wavevectors()
  
  def make_corrections(self):
    '''
      Correct the data for background and Vanadium standard.
      The rawdata is not changed only the I column.
    '''
    if self.flipping_correction:
      if self.flipping_correction[0]:
        return self.make_combined_corrections(self.flipping_correction[2])
      else:
        sys.stdout.write("Skpped till other flipper chanel.")
        sys.stdout.flush()
        return None
    changed=False
    if not self.background_data is None:
      sys.stdout.write("background substractoin, ")
      sys.stdout.flush()
      self.process_function(self.correct_background)
      changed=True
    else:
      self.process_function(self.copy_intensities)
    if not self.vanadium_data is None:
      sys.stdout.write("vanadium correction, ")
      sys.stdout.flush()
      self.process_function(self.correct_vanadium)
      changed=True
    if changed:
      if self.zdata>-1:
        self.zdata=self.number_of_channels*2+5
        self.yerror=self.number_of_channels*3+5
      else:
        self.ydata=self.number_of_channels*2+5
        self.yerror=self.number_of_channels*3+5
  
  def make_combined_corrections(self, other):
    '''
      Correct two datasets for background, flipping-ratio and Vanadium standard.
      The rawdata is not changed only the I column.
    '''
    changed=False
    if not self.background_data is None:
      sys.stdout.write("up-background, ")
      sys.stdout.flush()
      self.process_function(self.correct_background)
    else:
      self.process_function(self.copy_intensities)
    if not other.background_data is None:
      sys.stdout.write("down-background, ")
      sys.stdout.flush()
      other.process_function(other.correct_background)
    else:
      other.process_function(other.copy_intensities)
    sys.stdout.write("flipping-ratio: ")
    sys.stdout.flush()
    converged=self.make_flipping_correction([self.flipping_correction[1], self, other], self.scattering_propability)
    if not self.vanadium_data is None:
      sys.stdout.write("up-vanadium, ")
      sys.stdout.flush()
      self.process_function(self.correct_vanadium)
    if not other.vanadium_data is None:
      sys.stdout.write("down-vanadium, ")
      sys.stdout.flush()
      other.process_function(other.correct_vanadium)
    if self.zdata>-1:
      self.data[7].dimension='I_0^+'
      other.data[7].dimension='I_0^-'
      self.zdata=self.number_of_channels*2+5
      self.yerror=self.number_of_channels*3+5
      other.zdata=other.number_of_channels*2+5
      other.yerror=other.number_of_channels*3+5
    else:
      self.data[7].dimension='I_0^+'
      other.data[7].dimension='I_0^-'
      self.ydata=self.number_of_channels*2+5
      self.yerror=self.number_of_channels*3+5
      other.ydata=other.number_of_channels*2+5
      other.yerror=other.number_of_channels*3+5
  
  def make_flipping_correction(self, item, scattering_propability):
    yindex=self.number_of_channels*2+5
    nicr_x=item[0].data[0].values
    nicr_y=item[0].data[1].values
    pp_data_x=item[2].data[4].values
    pp_data=item[2].data[yindex].values
    pm_data=item[1].data[yindex].values
    nicr_data=[nicr_y[nicr_x.index(detector)] for detector in pp_data_x]
    if use_numpy:
      nicr_data=array(nicr_data)
      pp_data=array(pp_data)
      pm_data=array(pm_data)
      def test(difference):
        return all(difference<1e-10)
      p_data, m_data, converged, p_ratio, m_ratio = correct_flipping_ratio(nicr_data, pp_data, pm_data, 
                                                                           scattering_propability, test)
    else:
      p_data=[]
      m_data=[]
      converged=True
      for i in range(len(pp_data)):
        p, m, conv , pr, mr= correct_flipping_ratio(nicr_data[i], pp_data[i], pm_data[i], scattering_propability)
        p_data.append(p)
        m_data.append(m)
        converged=converged and conv
    sys.stdout.write("%s, " % converged)
    sys.stdout.flush()
    item[2].data[yindex].values=list(p_data)
    item[1].data[yindex].values=list(m_data) 
    return converged
  
  def copy_intensities(self, point):
    '''
      Just copy the raw intensity measured to another column.
    '''
    nc=self.number_of_channels
    for i in range(nc):
      point[i+2*nc+5]=point[i+5]
      point[i+3*nc+5]=point[i+nc+5]
    return point
  
  if use_numpy:
    #++++++++++++ calculations for use with arrays +++++++++++++++++
    def correct_background(self, point):
      '''
        Subtract background from the intensity data and calculate new
        error for these values.
      '''
      nc=self.number_of_channels
      # find the background for the right detectors
      # create a list of all columns in the background file
      bg_lists=map(lambda column: column.values, self.background_data.data)
      # search the indices for the detectors
      bg_indices=map(lambda detector: bg_lists[0].index(detector), point[4])
      # create a list of arrays with the corresponding intensities
      bg=map(lambda column: array(map(lambda index: column[index], bg_indices)), bg_lists[1:])
      for i in range(nc):
        point[i+2*nc+5]=point[i+5]-bg[i]
        point[i+3*nc+5]=sqrt(point[i+nc+5]**2 + bg[i+nc]**2)
      return point
    
    def correct_vanadium(self, point):
      '''
        Devide the intensity by the counts measured with vanadium for the
        same detector bank.
      '''
      nc=self.number_of_channels
      # find the background for the right detector
      # create a list of all columns in the background file
      vn_lists=map(lambda column: column.values, self.vanadium_data.data)
      # search the indices for the detectors
      if self.vanadium_correct_by_detector:
        vn_indices=map(lambda detector: vn_lists[0].index(detector), point[4])
      else:
        vn_indices=map(lambda tth: vn_lists[0].index([item for item in vn_lists[0] if item<=tth][-1]), point[3])        
      # create a list of arrays with the corresponding intensities
      vn=array(map(lambda index: vn_lists[1][index], vn_indices))
      errvn=array(map(lambda index: vn_lists[2][index], vn_indices))
      for i in range(nc):
        point[i+2*nc+5]/=vn
        point[i+3*nc+5]=self.error_propagation_quotient([point[i+2*nc+5], point[i+3*nc+5]],[vn, errvn])
      return point
  
    def __add__(self, other):
      if len(self) != len(other):
        return None
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        result.data[i+5].values=list(array(self.data[i+5].values)+array(other.data[i+5].values))
        result.data[i+nc+5].values=list(sqrt(array(self.data[i+nc+5].values)**2+array(other.data[i+nc+5].values)**2))
        result.data[i+2*nc+5].values=list(array(self.data[i+2*nc+5].values)+array(other.data[i+2*nc+5].values))
        result.data[i+3*nc+5].values=list(sqrt(array(self.data[i+3*nc+5].values)**2+array(other.data[i+3*nc+5].values)**2))
      return result
    
    def __sub__(self, other):
      if len(self) != len(other):
        return None
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        result.data[i+5].values=list(array(self.data[i+5].values)-array(other.data[i+5].values))
        result.data[i+nc+5].values=list(sqrt(array(self.data[i+nc+5].values)**2+array(other.data[i+nc+5].values)**2))
        result.data[i+2*nc+5].values=list(array(self.data[i+2*nc+5].values)-array(other.data[i+2*nc+5].values))
        result.data[i+3*nc+5].values=list(sqrt(array(self.data[i+3*nc+5].values)**2+array(other.data[i+3*nc+5].values)**2))
      return result
    
    def __rmul__(self, other):
      '''
        Multiply the data by a constant factor.
      '''
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      if other==1:
        return result
      nc=self.number_of_channels
      for i in range(4*nc):
        result.data[i+5].values=list(array(self.data[i+5].values)*other)
      return result      
    #------------ calculations for use with arrays -----------------
  else:
    #+++++++++ calculations for use with single points +++++++++++++
    def correct_background(self, point):
      '''
        Subtract background from the intensity data and calculate new
        error for these values.
      '''
      nc=self.number_of_channels
      # find the background for the right detector
      for bg_point in self.background_data:
        if bg_point[0] ==  point[4]:
          bg=bg_point[1:]
          break
      for i in range(nc):
        point[i+2*nc+5]=point[i+5]-bg[i]
        point[i+3*nc+5]=sqrt(point[i+nc+5]**2 + bg[i+nc]**2)
      return point
    
    def correct_vanadium(self, point):
      '''
        Devide the intensity by the counts measured with vanadium for the
        same detector bank.
      '''
      nc=self.number_of_channels
      # find the background for the right detector
      for vn_point in self.vanadium_data:
        if vn_point[0] ==  point[4]:
          vn=vn_point[1]
          errvn=vn_point[2]
          break
      for i in range(nc):
        point[i+2*nc+5]/=vn
        point[i+3*nc+5]=self.error_propagation_quotient([point[i+2*nc+5], point[i+3*nc+5]],[vn, errvn])
      return point

    def __add__(self, other):
      if len(self) != len(other):
        return None
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        for j in range(len(self)):
          result.data[i+5].values[j]=self.data[i+5].values[j]+other.data[i+5].values[j]
          result.data[i+nc+5].values[j]=sqrt(self.data[i+nc+5].values[j]**2+other.data[i+nc+5].values[j]**2)
          result.data[i+2*nc+5].values[j]=self.data[i+2*nc+5].values[j]+other.data[i+2*nc+5].values[j]
          result.data[i+3*nc+5].values[j]=sqrt(self.data[i+3*nc+5].values[j]**2+other.data[i+3*nc+5].values[j]**2)
      return result
    
    def __sub__(self, other):
      if len(self) != len(other):
        return None
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        for j in range(len(self)):
          result.data[i+5].values[j]=self.data[i+5].values[j]-other.data[i+5].values[j]
          result.data[i+nc+5].values[j]=sqrt(self.data[i+nc+5].values[j]**2+other.data[i+nc+5].values[j]**2)
          result.data[i+2*nc+5].values[j]=self.data[i+2*nc+5].values[j]-other.data[i+2*nc+5].values[j]
          result.data[i+3*nc+5].values[j]=sqrt(self.data[i+3*nc+5].values[j]**2+other.data[i+3*nc+5].values[j]**2)
      return result
    
    def __rmul__(self, other):
      '''
        Multiply the data by a constant factor.
      '''
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      if other==1:
        return result
      nc=self.number_of_channels
      for i in range(4*nc):
        for j in range(len(self)):
          result.data[i+5].values[j]=self.data[i+5].values[j]*other
      return result      
    #--------- calculations for use with single points -------------

  def error_propagation_quotient(self,xdata,ydata): 
    '''
      Calculate the propagated error for x/y.
    '''
    return sqrt(xdata[1]**2/ydata[0]**2 + xdata[0]**2/ydata[0]**4 * ydata[1]**2)
  
