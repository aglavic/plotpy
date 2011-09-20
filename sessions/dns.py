# -*- encoding: utf-8 -*-
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
from glob import glob
exit=sys.exit
# if possible use the numpy functions as they work with complete arrays
from numpy import pi, cos, sin, sqrt, array, where, nan_to_num, maximum, zeros
use_numpy=True

# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
from measurement_data_structure import MeasurementData
# importing data readout
import read_data.dns
import config.dns
# import gui functions for active config.gui.toolkit
import config.gui
try:  
  GUI=__import__( config.gui.toolkit+'gui.dns', fromlist=['DNSGUI']).DNSGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Werner Schweika"]
__license__ = "GPL v3"
__version__ = "0.7.9.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

# functions for evaluation of polarized neutron measurements
def correct_flipping_ratio(flipping_ratio, pp_data, pm_data, 
                           scattering_propability=0.1, convergence_criteria=None):
  '''
    Calculate the selfconsistent solution of the spin-flip/non spin-flip
    scattering with respect to a measured flipping ratio for given measured data.
    As most variables are scaled to sum up as 1. be sure to use floating point numbers
    or arrays of floating point numers.
    
    @param flipping_ratio The flipping ratio for the solution
    @param pp_data non spin-flip data measured
    @param pm_data spin-flip data measured
    @param scattering_propability Propapility for a neutron to get scattered from the sample
    @param convergence_criteria Function to test for convergence
    
    @return non splin-flip, spin-flip data and if the algorithm converged
  '''
  # TODO: revisit for negative values
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
  polarization=flipping_ratio/(1.+flipping_ratio)
  
  for iter in range(ITERATIONS):
    # n-times multiple scattering is represented by a list of length n
    p_multiple_scattering=[polarization]
    m_multiple_scattering=[1.-polarization]
    # calculate the multiple scattered part of the intensity
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
      return nsf_scattering*total, sf_scattering*total, True

  # scale the output by total measured intensity
  return nsf_scattering*total, sf_scattering*total, False


class DNSSession(GUI, GenericSession):
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
\t-bg [bg]\tAdd a file to subtract as background, can be specified multiple times.
\t\t\tThe files used are selected via the helmholz and flipper currents and the
\t\t\tdetector bank position.
\t-bs [scaling]\tScale the background files by a constant factor (e.g. for strong absorbing samples)
\t-fr [scp]\t\tTry to make automatic flipping-ratio correction with the scatteringpropability scp
\t-v\t\tSelect vanadium file from system directory (normally from this reactor cycle)
\t-vana [file]\tUse different Vanadium file for evaluation
\t-setup [folder]\tSet an other system folder for background,vanadium and NiCr files
\t-sample [name]\tSet the name of your sample to be used in every plot(can be changed in GUI)
\t-cz [zipfile]\tGet instrumental background, vanadium and NiCr files from .zip file and use it.
\t\t\tThe files need to be in root directory inside the zip-file.
\t-sep-nonmag\tSeperate scattering for non magnetic samples

\t-fullauto\t\tSet -b, -v, -fr 0. and try to get all fiels settings automatically. If
\t\t\ta setup*.zip file is in the present directory it is used for backgound, vanadium
\t\t\tand flipping ratio correction. If ALWAYS_FULLAUTO option is set in config this
\t\t\toption disables it.

\t-files [prefix] [ooff] [inc] [from] [to] [postfix]
\t\t\tExplicidly give the file name prefix, omega offset, increment, numbers and postfix
\t\t\tfor the files to be used. Can be given multiple times for diefferent prefixes

\tReciprocal lattice settings:
\t\t-dx [d-spacing]\tSet the d-spacing of the measured crystal lattice in x-direction 
\t\t\t\t\t(depends on omega-offset setting and measured sample alignment)
\t\t-dy [d-spacing]\tSet the d-spacing of the measured crystal lattice in y-direction 
\t\t\t\t\t(depends on omega-offset setting and measured sample alignment)
\t\t-nx [name]\tSet the naming of the reciprocal axes in x-direction 
\t\t-ny [name]\tSet the naming of the reciprocal axes in y-direction 

\tShort info settings: 
\t\t-time, -flipper, -monitor
\t\t\tDon't use temperature for the short info but time, flipper or monitor value.'
\t\t-xyz\txyz polarization analysis, implies -inc 6
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('DNS', '*.d_dat', '*.d_dat.gz'), ('D7', '*.d7', '*.d7.gz')]

  TRANSFORMATIONS=[\
  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['inc', 'ooff', 'b', 'bg', 'bs', 'fr', 'v', 'vana', 'files', 
                                                          'sample', 'setup', 'cz', 'time', 'flipper', 'monitor', 
                                                          'powder', 'xyz', 'sep-nonmag', 'split', 'fullauto', 'sum', 
                                                          'dx', 'dy', 'nx', 'ny', 'd7'] 
  file_options={'default': ['', 0, 1, [0, -1], ''],  # (prefix, omega_offset, increment, range, postfix)
                } # Dictionary storing specific options for files with the same prefix
  prefixes=[] # A list of all filenames to be imported
  mds_create=False # DNS data is not stored as .mds files as the import is fast
  FULLAUTO=config.dns.ALWAYS_FULLAUTO
  VANADIUM_FILE=config.dns.VANADIUM_FILE # File name of vanadium file to be used for the correction
  BACKGROUND_FILES=None # File name of a background file to substract
  BACKGROUND_SCALING=1. # Factor to scale the background
  bg_corrected_nicr_data={} # dictionary of background corrected NiCr data
  system_bg={} # dictionary of background data from the system directory
  user_bg={} # dictionary of background data supplied by the user
  system_vana=None # sum of all vanadium files in setup directory
  AUTO_BACKGROUND=False # try to select a background data from system_bg
  AUTO_VANADIUM=False # try to use all vanadium files in setup directory
  CORRECTION_ZIP=None
  CORRECT_FLIPPING=False # try automatic flipping-rato correction
  SCATTERING_PROPABILITY=0.0 # scattering_propability used for automatic flipping-ratio correction
  COMBINE_SAME_OMEGA_TTH=False # sum up files with same omega and tth values
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
  SEPARATE_NONMAG=False
  D7_IMPORT=False
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
    #++++++++++++++++ initialize the session ++++++++++++++++++++++
    if self.FULLAUTO:
      # Initialize full automatic search for appropriate sequences
      if len(names)==0:
        # If noe filenames are supplied, try to get all dns datafiles
        # in the active directory
        names=glob('*.d_dat')+glob('*.d_dat.gz')
      self.initialize_fullauto(names)
      names=[]
    self.os_path_stuff() # create temp folder according to OS
    self.read_vana_bg_nicr_files() # read NiCr files for flipping-ratio correction
    self.try_import_externals()
    self.import_plugins() # search the plugin folder for modules
    if self.BACKGROUND_FILES:
      self.BACKGROUND_FILES.sort()
      print "Reading user set background files %s-%s" % (self.BACKGROUND_FILES[0], self.BACKGROUND_FILES[-1])
      # read all background files supplied by the user with the -bg option
      # every dataset will be corrected by the user bg files and if no
      # fitting user bg file is found the system background files
      for bg_file in self.BACKGROUND_FILES:
        self.read_bg_file(bg_file, self.user_bg)
      for key, value in self.user_bg.items():
        self.user_bg[key]=self.sum_same_tth(value)
    names.sort()
    self.set_transformations()
    config.transformations.known_transformations+=self.TRANSFORMATIONS
    if len(names) > 0:
      self.find_prefixes(names) # try to find the sequences for the remaining file names
    if not self.SPLIT is None:
      self.split_sequences(self.SPLIT) # old way of splitting sequences every SPLIT step
    #++++++++++++++++++++++ read files ++++++++++++++++++++++++++++
    self.prefixes.sort()
    for prefix in self.prefixes:
      # for every measured sequence read the datafiles and create a map/lineplot.
      self.read_files(prefix)
    
    if len(self.prefixes)>0:
      # set the first measurement as active
      self.active_file_data=self.file_data[self.prefixes[0]]
      self.active_file_name=self.prefixes[0]
      self.INIT_COMPLETE=True
    elif self.active_file_data is not None:
      self.INIT_COMPLETE=True
    else:
      self.active_file_data=[]
      self.active_file_name=''
    
    # for gui set fullauto import
    self.FULLAUTO=True
  
  def initialize_fullauto(self, names):
    '''
      Initializing the fullauto session, which tries to set every options
      from the file names and the informations in the datafiles.
      
      @param names List of filenames to be used
    '''
    print "Initializing full automatic session..."
    self.AUTO_BACKGROUND=True
    self.AUTO_VANADIUM=True
    self.CORRECT_FLIPPING=True
    self.SCATTERING_PROPABILITY=0.
    if not self.CORRECTION_ZIP:
      szf=glob('setup*.zip')
      if len(szf)>0:
        self.CORRECTION_ZIP=szf[-1]
        print "\tUsing setup files from %s." % szf[-1]
    self.find_prefixes(names)
    print "\tFound %i continous sequences. Trying to split those by Temperature." % len(self.prefixes)
    self.autosplit_sequences()

  def autosplit_sequences(self):
    '''
      Go through all sequences and try to split them by temperature.
    '''
    new_prefixes=[]
    new_options={'default': self.file_options['default']}
    discarded=[]
    for prefix in self.prefixes:
      splits=[0]
      options=self.file_options[prefix]
      temperatures, currents=self.get_temp_current_infos(options)
      tempi=temperatures[0]
      for i, temp in enumerate(temperatures):
        # Get indices of files which have different temperatures
        if temp-tempi>config.dns.FULLAUTO_TEMP_SENSITIVITY:
          tempi=temp
          splits.append(i)
      splits.append(i+1)
      for i, split in enumerate(splits[:-1]):
        name=glob("%s*%i%s" % (options[0], options[3][0]+split, options[4]))[0]
        # get number of different helmholz, flipper settings
        inc=1
        curi=currents[split]
        for j in range(1, splits[i+1]-split):
          if currents[split+j]==curi:
            break
          else:
            inc+=1
        if (splits[i+1]-split)%inc!=0:
          discard_items=(splits[i+1]-split)%inc
          print "\tFound uncomplete file sequence, discarding last %i files." % discard_items
          new_prefixes.append(name)
          pre=options[0]+"0".join(["" for j in range(
              len(str(options[3][1]))-len(str(splits[i+1]+1)))])
          new_options[name]=[pre, 
                              options[1], 
                              inc, 
                              (split+options[3][0], splits[i+1]+options[3][0]-1-discard_items), 
                              options[4]]
          discarded.append((pre, 
                              options[1], 
                              inc, 
                              (split+options[3][0], splits[i+1]+options[3][0]-1), 
                              options[4]))
        else:
          new_prefixes.append(name)
          pre=options[0]+"0".join(["" for j in range(
              len(str(options[3][1]))-len(str(splits[i+1]+1)))])
          new_options[name]=[pre, 
                              options[1], 
                              inc, 
                              (split+options[3][0], splits[i+1]+options[3][0]-1), 
                              options[4]]
    print "\tSplitted into %i sequences, using %i and discarding %i." % (len(new_prefixes)+len(discarded), len(new_prefixes), len(discarded))
    self.prefixes=new_prefixes
    self.file_options=new_options
    print "... initialization ready, writing options to 'last_fullauto.txt'.\n"
    file_handler=open('last_fullauto.txt', 'w')
    file_handler.write('dnsplot -b -v -fr 0. ')
    if self.CORRECTION_ZIP:
      file_handler.write('-cz %s ' % self.CORRECTION_ZIP)
    for prefix in self.prefixes: 
      values=self.file_options[prefix]
      file_handler.write('\\\n-files %s %.1f %i %i %i %s ' % (
                                                         values[0], values[1], 
                                                         values[2], values[3][0],  
                                                         values[3][1], values[4]
                                                         ))
    file_handler.write('\n')
    for values in discarded: 
      file_handler.write('# -files %s %.1f %i %i %i %s \n' % (
                                                         values[0], values[1], 
                                                         values[2], values[3][0],  
                                                         values[3][1], values[4]
                                                         ))
    file_handler.close()

  def get_temp_current_infos(self, options):
    '''
      Get the temperature and current infos from all files in
      one sequence defined by options.
    '''
    temperatures=[]
    currents=[]
    file_list=glob("%s*%s" % (options[0], options[4]))
    if len(file_list)==0:
      return None
    file_list.sort()
    for file_name in file_list:
      # get integer number of the file, catch errors form wrong file selection
      try:
        active_number=int(file_name.rsplit(options[4])[0].split(options[0], 1)[1])
      except ValueError:
        continue
      if (active_number>=options[3][0]) and (active_number<=options[3][1] or options[3][1]==-1):
        # read the datafile into a MeasurementData object.
        file_handler=open(file_name, 'r')
        # Currents
        currents.append((
                         round(read_data.dns.read_info(file_handler, 'Flipper_precession'), 2), 
                         #round(read_data.dns.read_info(file_handler, 'Flipper_z_compensation'), 2), 
                         round(read_data.dns.read_info(file_handler, 'C_a'), 2), 
                         round(read_data.dns.read_info(file_handler, 'C_b'), 2), 
                         round(read_data.dns.read_info(file_handler, 'C_c'), 2), 
                         round(read_data.dns.read_info(file_handler, 'C_z'), 2)
                         )
                        )
        # Temperature
        temperatures.append(read_data.dns.read_info(file_handler, 'T1'))
    return temperatures, currents

  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
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
          if ',' in argument:
            name_from, name_to=argument.split(',', 1)
            all_names=glob(os.path.join(
                           os.path.split(name_from)[0], 
                           '*'))
            all_names.sort()
            try:
              idx_from=all_names.index(name_from)
              idx_to=all_names.index(name_to)
              if not self.BACKGROUND_FILES:
                self.BACKGROUND_FILES=all_names[idx_from:idx_to+1]
              else:
                self.BACKGROUND_FILES+=all_names[idx_from:idx_to+1]
            except IndexError:
              pass
          else:
            if not self.BACKGROUND_FILES:
              self.BACKGROUND_FILES=[argument]
            else:
              self.BACKGROUND_FILES.append(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='bs':
          self.BACKGROUND_SCALING=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='fr':
          self.CORRECT_FLIPPING=True
          self.SCATTERING_PROPABILITY=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='cz':
          self.CORRECTION_ZIP=argument
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
          self.VANADIUM_FILE=unicode(argument)
          last_argument_option=[False,'']
        # Set sample name:
        elif last_argument_option[1]=='sample':
          self.SAMPLE_NAME=argument
          last_argument_option=[False,'']
        elif last_argument_option[1]=='setup':
          config.dns.SETUP_DIRECTORYS=[argument]
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
      elif argument=='-fullauto':
        self.FULLAUTO=not self.FULLAUTO
      elif argument=='-b':
        self.AUTO_BACKGROUND=True
      elif argument=='-sum':
        self.COMBINE_SAME_OMEGA_TTH=True
      elif argument=='-v':
        self.AUTO_VANADIUM=True
      elif argument=='-d7':
        self.D7_IMPORT=True
        self.read_files=self.read_files_d7
        self.read_vana_bg_nicr_files=self.read_vana_bg_nicr_files_d7
        self.read_bg_file=self.read_bg_file_d7
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
      elif argument=='-sep-nonmag':
        self.SEPARATE_NONMAG=True
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
    if len(filenames) > 0:
      self.find_prefixes(filenames)
    else:
      return False
    # For alter imports also try fullautomode
    if self.FULLAUTO and getattr(self, 'INIT_COMPLETE', False):
      self.autosplit_sequences()      
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
      
      @param file Sequence with the options for the file import
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
  
  def read_files_d7(self, file):
    '''
      Function to read data files for one D7 measurement. 
      The files are split by their prefixes.
      
      @param file Sequence with the options for the file import
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
      i=1
      if (active_number>=num_range[0]) and (active_number<=num_range[1] or num_range[1]==-1):
        # read the datafile into a MeasurementData object.
        datasets=read_data.dns.read_data_d7(os.path.join(folder, file_name))
        if i==1:
          self.file_options[file][2]=len(datasets)
        for dataset in datasets:
          dataset.number=str(i)
          i+=1
        self.file_data[file+'|raw_data']+=datasets
    print "\tRead, creating map."
    self.create_maps(file)
    return None
  
  def get_active_file_info(self):
    '''
      Replacement of generic info function, more specific to dns imports.
    '''
    if self.active_file_name.endswith('|raw_data'):
      return "Raw data file.\n"
    else:
      name=self.active_file_name
      if name in self.file_options:
        opts=self.file_options[name]
        leni=len(str(opts[3][1]))
        return "Data read from files %s-%s.\n\tOmega-Offset: %.2f\n\tNumber of Polarization Channels: %i\n" % (
                              opts[0]+("%%0%ii" % leni) % opts[3][0] + opts[4], 
                              opts[0]+"%i" % opts[3][1] + opts[4], 
                              opts[1], 
                              opts[2]
                              )
      else:
        return "%s: \n" % (self.active_file_name )
  
  def sum_same_omega_tth(self, scans):
    '''
      Find scan files with same omega and tth value and sum them up.
    '''
    from copy import deepcopy
    print '\tSumming up files with same positions [ω,2θ]'
    scandict={}
    for scan in scans:
      key=(scan.dns_info['omega'], scan.dns_info['detector_bank_2T'], 
           scan.dns_info['C_a'], scan.dns_info['C_b'], scan.dns_info['C_c'], 
           scan.dns_info['flipper'], scan.dns_info['flipper_compensation'])
      if key in scandict:
        scandict[key].append(scan)
      else:
        scandict[key]=[scan]
    outscans=[]
    scale=config.dns.SCALE_BY[0]
    for key, value in sorted(scandict.items()):
      if len(value)==1:
        outscans.append(value[0])
      else:
        joint=deepcopy(value[0])
        # unscale the counts
        joint.data[1]*=joint.dns_info[scale]
        # square the errors
        joint.data[2]*=joint.dns_info[scale]
        joint.data[2]**=2
        time=joint.dns_info[scale]
        for add in value[1:]:
          joint.data[1]+=(add.data[1]*add.dns_info[scale])
          joint.data[2]+=(add.data[2]*add.dns_info[scale])**2
          time+=add.dns_info[scale]
          if getattr(joint, 'name', False):
            joint.name+='+'+add.name
        joint.data[1]/=time
        joint.data[2]/=time
        joint.data[2]**=0.5
        outscans.append(joint)
    return outscans

  def sum_same_tth(self, scans):
    '''
      Find scan files with same omega and tth value and sum them up.
    '''
    from copy import deepcopy
    scandict={}
    for scan in scans:
      key=(scan.dns_info['detector_bank_2T'], 
           scan.dns_info['C_a'], scan.dns_info['C_b'], scan.dns_info['C_c'], 
           scan.dns_info['flipper'], scan.dns_info['flipper_compensation'])
      if key in scandict:
        scandict[key].append(scan)
      else:
        scandict[key]=[scan]
    outscans=[]
    for key, value in sorted(scandict.items()):
      if len(value)==1:
        outscans.append(value[0])
      else:
        joint=deepcopy(value[0])
        # square the errors
        joint.data[2]**=2
        for add in value[1:]:
          joint.data[1]+=add.data[1]
          joint.data[2]+=add.data[2]**2
          if getattr(joint, 'name', False):
            joint.name+='+'+add.name
        joint.data[1]/=len(value)
        joint.data[2]/=len(value)
        joint.data[2]**=0.5
        outscans.append(joint)
    return outscans

  def create_maps(self, file):
    '''
      Crates a MeasurementData object which can be used to
      plot color maps or lineplots of the measurement.
      For Powder data it is only shown as 2Theta vs intensity.
      For single crystal it is a map in q_x,q_y. (Or hkl)
      
      @param file Sequence with the options for the file import
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
    if 'detector_angles' in scans[0].dns_info:
      # Functoin used to append data to the object
      def append_to_map(point):
        return [detector_bank_2T, 
                round(omega-omega_offset, 1), 
                round(omega, 1), 
                point[3], 
                point[0], 
                point[1], 
                point[2], 
                point[1], 
                point[2], 
                0, 0, i]
    else:
      # Functoin used to append data to the object
      def append_to_map(point):
        return [detector_bank_2T, 
                round(omega-omega_offset-detector_bank_2T, 1), 
                round(omega-detector_bank_2T, 1), 
                point[0]*config.dns.DETECTOR_ANGULAR_INCREMENT+config.dns.FIRST_DETECTOR_ANGLE-detector_bank_2T, 
                point[0]
                ]+point[1:]+point[1:]+[0, 0, i]
    if self.COMBINE_SAME_OMEGA_TTH:
      scans=self.sum_same_omega_tth(scans)
    # go through every raw data object.
    for i, scan in enumerate(scans):
      if i<increment:
        if self.XYZ_POL:
          channels=['x', 'x', 'y', 'y', 'z', 'z']
          scan.dns_info['pol_channel']=channels[i]
        # Create the objects for every polarization chanel
        if 'detector_angles' in scans[0].dns_info:
          sub=2
        else:
          sub=1
        columns=[['DetectorbankAngle', '°'], ['ω', '°'], ['ω-RAW', '°'], 
                 ['2Θ', '°'], ['Detector', '']]+\
                 [[scan.dimensions()[j], scan.units()[j]] for j in range(1, len(scan.units())+1-sub)]+\
                 [['I_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-sub)/2)]+\
                 [['error_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-sub)/2)]+\
                 [['q_x', 'Å^{-1}'], ['q_y', 'Å^{-1}'], ['Filenumber', '']]
        self.file_data[file].append(DNSMeasurementData(columns, [], 1, 3, (len(scan.units())-sub)/2+5, zdata=5))
        # set some parameters for the object
        active_map=self.file_data[file][i]
        active_map.number=str(i)
        active_map.dns_info=scan.dns_info
        active_map.number_of_channels=(len(scan.units())-1)/2
        active_map.short_info=str(i)+': '+" ".join([info[1](scan.dns_info[info[0]])+info[2] for info in self.SHORT_INFO])
        if 'sample_name' in scan.dns_info:
          active_map.sample_name=scan.dns_info['sample_name']
        else:
          active_map.sample_name=self.SAMPLE_NAME
        active_map.info= "\n".join(map(lambda item: item[0]+': '+str(item[1]),
                                    sorted(scan.dns_info.items())))
      # add the data
      data=[list(point) for point in scan]
      detector_bank_2T=scan.dns_info['detector_bank_2T']
      omega=scan.dns_info['omega']
      map(self.file_data[file][i%increment].append, map(append_to_map, data))
      #append_combine_data()
    # perform calculations
    self.active_file_data=self.file_data[file]
    if self.CORRECT_FLIPPING:
      # assign flipping chanels to nicr-data
      self.correct_flipping_ratio(self.SCATTERING_PROPABILITY)
    for dnsmap in self.active_file_data:
      sys.stdout.write("\tMap %s created, perfoming datatreatment: " % dnsmap.number)
      sys.stdout.flush()
      if self.POWDER_DATA or len(set(dnsmap.data[1].values))==1:
        new=dnsmap.prepare_powder_data()
        self.active_file_data[self.active_file_data.index(dnsmap)]=new
        if dnsmap.flipping_correction:
          # reassign new data for other spin-flip channel
          fc=dnsmap.flipping_correction
          fc[2].flipping_correction=(not fc[0], fc[1], new)
          new.flipping_correction=(fc[0], fc[1], fc[2])
        dnsmap=new
      if self.AUTO_BACKGROUND or self.BACKGROUND_FILES:
        self.find_background_data(dnsmap)
      if self.AUTO_VANADIUM:
        self.find_vanadium_data(dnsmap)
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
      dnsmap.make_corrections()
      sys.stdout.write("\n")
      sys.stdout.flush()
      if self.TRANSFORM_Q:
        dnsmap.unit_trans(self.TRANSFORMATIONS)
    # Seperate scattering for powder data x,y,z polarization analysis
    if self.XYZ_POL and (self.POWDER_DATA or len(set(dnsmap.data[1].values))==1) and self.CORRECT_FLIPPING and len(self.active_file_data)==6:
      self.separate_scattering_xyz(self.active_file_data)
    if self.SEPARATE_NONMAG:
      self.separate_scattering_nonmag(self.active_file_data)

  def separate_scattering_xyz(self, af):
    '''
      Saparate the scattering parts of powderdata with
      xyz polarization analysis.
    '''
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
    af.insert(0, sp_inc)
#      af.insert(0, para_1)
#      af.insert(0, para_2)
    af.insert(0, para)
    af.insert(0, nu_coh)

  def separate_scattering_nonmag(self, af):
    '''
      Separate the scattering parts of sf-, nfs-scattering
      for nonmagnetic samples.
    '''
    # para= <para_1,para_2>
    coherent=af[1] - 0.5 * af[0]
    coherent.short_info='coherent scattering'
    coherent.number='3'
    # sp_inc= 1.5 * (3 * SF_z - SF_x - SF_y)
    sp_inc= 1.5 * af[0]
    sp_inc.short_info='spin incoherent'
    sp_inc.number='4'
    # nu_coh= NSF_z - 0.5 * para - 1/3 * sp_inc
    separated=coherent / sp_inc
    separated.short_info='Separated'
    separated.number='0'
    af.insert(2, coherent)
    af.insert(3, sp_inc)
    af.insert(0, separated)    

  def find_background_data(self, dataset):
    '''
      Try to find a background data with the right flipper and helmholz currents for this dataset.
      The background data is connected to dataset.background_data.
      
      @param dataset a DNSMeasurementData object
    '''
    # get all detectorbank positions
    detectors=list(set(dataset.data[0].values))
    detectors.sort()
    # get the currents
    flip=float(dataset.dns_info['flipper'])
    flip_cmp=float(dataset.dns_info['flipper_compensation'])
    c_a=float(dataset.dns_info['C_a'])
    c_b=float(dataset.dns_info['C_b'])
    c_c=float(dataset.dns_info['C_c'])
    c_z=float(dataset.dns_info['C_z'])
    found=False
    # create a key for the currents and search for it in the
    # background dictionary
    for key in self.user_bg.keys():
      if abs(key[0]-flip)<0.05 and \
         abs(key[1]-flip_cmp)<0.05 and \
         abs(key[2]-c_a)<0.05 and \
         abs(key[3]-c_b)<0.05 and \
         abs(key[4]-c_c)<0.05 and \
         abs(key[5]-c_z)<0.05:
        bg=self.user_bg[key]
        found=True
    if not found:
      for key in self.system_bg.keys():
        if abs(key[0]-flip)<0.05 and \
           abs(key[1]-flip_cmp)<0.05 and \
           abs(key[2]-c_a)<0.05 and \
           abs(key[3]-c_b)<0.05 and \
           abs(key[4]-c_c)<0.05 and \
           abs(key[5]-c_z)<0.05:
          bg=self.system_bg[key]
          found=True
    if found:
      bg.sort(lambda b1, b2: cmp(b1.dns_info['detector_bank_2T'], b2.dns_info['detector_bank_2T']))
      bg_detectors=[b.dns_info['detector_bank_2T'] for b in bg]
      dataset.background_data={}
      # Select the background data with the closest detectorbank position
      if len(bg)==1:
        for angle in detectors:
          dataset.background_data[angle]=bg[0]
      else:
        i=0
        for angle in detectors:
          while bg_detectors[i]<=angle:
            if (i+1)<len(bg):
              i+=1
            else:
              dataset.background_data[angle]=bg[i]
              break
          if bg_detectors[i]>angle:
            if i==0:
              dataset.background_data[angle]=bg[0]
            else:
              if bg_detectors[i]-angle < angle-bg_detectors[i-1]:
                dataset.background_data[angle]=bg[i]
              else:
                dataset.background_data[angle]=bg[i-1]

  def find_vanadium_data(self, dataset):
    '''
      Set vanadium data for this dataset.
      The vanadium data is connected to dataset.vanadium_data.
      
      @param dataset A DNSMeasurementData object
    '''
    dataset.vanadium_data=self.system_vana

  def find_prefixes(self, names):
    '''
      Try to find prefixes from a list of filenames.
      config.dns.min_prefix_length is used to split different
      sets of files. The prefix is stored in self.prefixes and the
      numbers in self.file_options.
      
      @param names A list of file names to process
    '''
    for filename in filter(lambda item: item.endswith('.mds') or item.endswith('.mds.gz')\
                  or item.endswith('.mdd') or item.endswith('.mdd.gz'), names):
      GenericSession.add_file(self, filename)
    if len(names)<2:
      return
    names.sort()
    names=filter(lambda item: item.endswith('.d_dat') or item.endswith('.d_dat.gz')\
                  or item.endswith('.d7') or item.endswith('.d7.gz'), names)
    def split_prefix_postfix(name):
      '''Split a file name for a string prefix,postfix and a number in the middle.'''
      pre_index=max(0, name.rfind(os.sep))
      while not name[pre_index].isdigit():
        pre_index+=1
      post_index=pre_index
      while name[post_index].isdigit():
        post_index+=1
      prefix=name[0:pre_index]
      number=name[pre_index:post_index]
      postfix=name[post_index:]
      return (prefix, number, postfix)
    names_pre_post=map(split_prefix_postfix, names)
    # find number ranges which belong together and store them in a dictionary with prefix as index
    found_prefixes={}
    for prefix, number, postfix in names_pre_post:
      if (prefix, postfix) in found_prefixes:
        if int(found_prefixes[(prefix, postfix)][2])+1==int(number):
          found_prefixes[(prefix, postfix)][2]=number
        else:
          found_prefixes[(prefix+'_%s' % found_prefixes[(prefix, postfix)][1], postfix)]=found_prefixes[(prefix, postfix)]
          found_prefixes[(prefix, postfix)]=[prefix, number, number, postfix]
      else:
        found_prefixes[(prefix, postfix)]=[prefix, number, number, postfix]
    for item in found_prefixes.values():
      i=0
      while item[1][:i]==item[2][:i]:
        i+=1
        if i>len(item[1]):
          print "Sorry, could not get prefixes right, for %s." % (item[0]+item[1]+item[3]+'-'+\
                                                                  item[0]+item[2]+item[3])
          break
      if i>len(item[1]):
        continue
      if len(item[0].rsplit(os.sep, 1))==1:
        add_folder='./'
      else:
        add_folder=''
      self.prefixes.append(add_folder+item[0]+item[1]+item[3])
      self.file_options[add_folder+item[0]+item[1]+item[3]]=[item[0]+item[1][:i-1], 
                                                           self.file_options['default'][1], 
                                                           self.file_options['default'][2], 
                                                           [int(item[1][i-1:]), 
                                                           int(item[2][i-1:])], 
                                                           item[3]]    
  
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
      ['q_x','Å^{-1}',1./d_star_x,0,self.D_NAME_X,'r.l.u.'],\
      ['q_y','Å^{-1}',1/d_star_y,0,self.D_NAME_Y,'r.l.u.'],\
                          ]
  
  def read_vana_bg_nicr_files(self):
    '''
      Read all NiCr, background and vanadium files in the chosen directorys and zipfile and correct NiCr for backgound.
    '''
    directorys=config.dns.SETUP_DIRECTORYS
    # if set, unzip the zipfile with the setup data
    if self.CORRECTION_ZIP:
      import zipfile
      try:
        zf=zipfile.ZipFile(self.CORRECTION_ZIP, 'r')
        directorys.append(os.path.join(self.TEMP_DIR, 'setup'))
        os.mkdir(directorys[-1])
        print "Extracting ziped setup data %s." % self.CORRECTION_ZIP
        for ziped_file in zf.filelist:
          name=os.path.split(ziped_file.filename)[1]
          file=open(os.path.join(directorys[-1], name), 'w')
          file.write(zf.read(ziped_file.filename))
          file.close()
      except IOError:
        print "No zip file %s." % self.CORRECTION_ZIP
    file_list=[]
    # create a list of all files in the setup directorys
    for directory in directorys:
      try:
        dir_list=sorted(os.listdir(directory))
        file_list+=[os.path.join(directory, name) for name in dir_list]
      except OSError:
        pass
    nicr_files=[]
    bg_files=[]
    vana_files=[]
    # filter the file names by the wildcards set in config.dns
    for wildcard in config.dns.NICR_FILE_WILDCARDS:
      nicr_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    for wildcard in config.dns.BACKGROUND_WILDCARDS:
      bg_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    for wildcard in config.dns.VANADIUM_WILDCARDS:
      vana_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    # a dictionary with the detector bank helmholz parameters is used to store the NiCr data
    nicr_data={}
    vana_data=None
    # read all nicr files
    for file_name in nicr_files:
      dataset=read_data.dns.read_data(file_name)
      dataset.name=os.path.split(file_name)[1]
      detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      nicr_data[(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)]=dataset
    # read all background files
    bg_data=self.system_bg
    for bg_file in bg_files:
      self.read_bg_file(bg_file, bg_data)
    self.system_bg=bg_data
    # correct the background of the nicr data
    bg_corrected_data={}
    def subtract_background(point):
      bg=background_data.data
      point[1]-=bg[1]
      point[2]=sqrt(point[2]**2+bg[2]**2)
      return point
    for key, data in nicr_data.items():
      if key[1:] in bg_data:
        background_data_list=bg_data[key[1:]]
        background_data_list.sort(lambda b1, b2: cmp(b1.dns_info['detector_bank_2T'], 
                                                     b2.dns_info['detector_bank_2T']))
        background_data_angles=[b.dns_info['detector_bank_2T'] for b in background_data_list]
        i=0
        angle=data.dns_info['detector_bank_2T']
        while background_data_angles[i]<=angle:
          if i+1<len(background_data_list):
            i+=1
          else:
            break
        if  background_data_angles[i]-angle < angle-background_data_angles[i-1] or i==0:
          background_data=background_data_list[i]
        else:
          background_data=background_data_list[i-1]
        data.process_function(subtract_background)
        data.name+='-'+background_data.name
        bg_corrected_data[key]=data
    self.bg_corrected_nicr_data=bg_corrected_data
    for file_name in vana_files:
      dataset=read_data.dns.read_data(file_name)
      bgs=False
      if vana_data:
        detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
        flip=round(float(dataset.dns_info['flipper']), 2)
        flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
        c_a=round(float(dataset.dns_info['C_a']), 2)
        c_b=round(float(dataset.dns_info['C_b']), 2)
        c_c=round(float(dataset.dns_info['C_c']), 2)
        c_z=round(float(dataset.dns_info['C_z']), 2)
        key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
        vana_data.name+='+'+os.path.split(file_name)[1]
        if key in bg_data:
          detectors=map(lambda bg: round(bg.dns_info['detector_bank_2T'], 0), bg_data[key])
          # subtract backgound from vanadium if suitable is found.
          if detector in detectors:
            backgound_data=bg_data[key][detectors.index(detector)]
            dataset.process_function(subtract_background)
            vana_data.name+='-'+backgound_data.name.replace('+', '-')
            bgs=True
        for i, data in enumerate(dataset):
          vana_data.data[1].values[i]+=data[1]
          vana_data.data[2].values[i]=sqrt((vana_data.data[2].values[i]**2+data[2]**2)/2.)
      else:
        vana_data=dataset
        vana_data.name=os.path.split(file_name)[1]
        detector=round(float(vana_data.dns_info['detector_bank_2T']), 0)
        flip=round(float(vana_data.dns_info['flipper']), 2)
        flip_cmp=round(float(vana_data.dns_info['flipper_compensation']), 2)
        c_a=round(float(vana_data.dns_info['C_a']), 2)
        c_b=round(float(vana_data.dns_info['C_b']), 2)
        c_c=round(float(vana_data.dns_info['C_c']), 2)
        c_z=round(float(vana_data.dns_info['C_z']), 2)
        key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
        if key in bg_data:
          detectors=map(lambda bg: round(bg.dns_info['detector_bank_2T'], 0), bg_data[key])
          # subtract backgound from vanadium if suitable is found.
          if detector in detectors:
            backgound_data=bg_data[key][detectors.index(detector)]
            vana_data.process_function(subtract_background)
            vana_data.name+='-'+backgound_data.name.replace('+', '-')
            bgs=True
      if not bgs and self.AUTO_VANADIUM:
        print "No backgound data for file %s, vanadium correction will not be correct." % file_name
    if vana_data:
      # normalize the vanadium data to stay in the same intensity region
      scale=vana_data.data[1][:].sum()/len(vana_data)
      vana_data.data[1]/=scale
      vana_data.data[2]/=scale
    self.system_vana=vana_data
    if directorys[-1]==os.path.join(self.TEMP_DIR, 'setup'):
      # remove files
      for file_name in os.listdir(directorys[-1]):
        os.remove(os.path.join(directorys[-1], file_name))
      os.rmdir(directorys[-1])      

  def read_vana_bg_nicr_files_d7(self):
    '''
      Read all NiCr, background and vanadium files in the chosen directorys and zipfile and correct NiCr for backgound.
      This is used for d7 datasets.
    '''
    directorys=config.dns.SETUP_DIRECTORYS
    # if set, unzip the zipfile with the setup data
    if self.CORRECTION_ZIP:
      import zipfile
      try:
        zf=zipfile.ZipFile(self.CORRECTION_ZIP, 'r')
        directorys.append(os.path.join(self.TEMP_DIR, 'setup'))
        os.mkdir(directorys[-1])
        print "Extracting ziped setup data %s." % self.CORRECTION_ZIP
        for ziped_file in zf.filelist:
          name=os.path.split(ziped_file.filename)[1]
          file=open(os.path.join(directorys[-1], name), 'w')
          file.write(zf.read(ziped_file.filename))
          file.close()
      except IOError:
        print "No zip file %s." % self.CORRECTION_ZIP
    file_list=[]
    # create a list of all files in the setup directorys
    for directory in directorys:
      try:
        dir_list=sorted(os.listdir(directory))
        file_list+=[os.path.join(directory, name) for name in dir_list]
      except OSError:
        pass
    nicr_files=[]
    bg_files=[]
    vana_files=[]
    # filter the file names by the wildcards set in config.dns
    for wildcard in config.dns.NICR_FILE_WILDCARDS:
      nicr_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    for wildcard in config.dns.BACKGROUND_WILDCARDS:
      bg_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    for wildcard in config.dns.VANADIUM_WILDCARDS:
      vana_files+=sorted(filter(lambda name: os.path.split(name)[1].startswith(wildcard[0]), 
                      filter(lambda name: os.path.split(name)[1].endswith(wildcard[1]), 
                             file_list)))
    # a dictionary with the detector bank helmholz parameters is used to store the NiCr data
    nicr_data={}
    vana_data=None
    # read all nicr files
    for file_name in nicr_files:
      datasets=read_data.dns.read_data_d7(file_name)
      for dataset in datasets:
        dataset.name=os.path.split(file_name)[1]
        detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
        flip=round(float(dataset.dns_info['flipper']), 2)
        flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
        c_a=round(float(dataset.dns_info['C_a']), 2)
        c_b=round(float(dataset.dns_info['C_b']), 2)
        c_c=round(float(dataset.dns_info['C_c']), 2)
        c_z=round(float(dataset.dns_info['C_z']), 2)
        nicr_data[(detector, flip, flip_cmp, c_a, c_b, c_c, c_z)]=dataset
    # read all background files
    bg_data=self.system_bg
    for bg_file in bg_files:
      self.read_bg_file_d7(bg_file, bg_data)
    for key in bg_data.keys():
      bg_data[key]=self.sum_same_tth(bg_data[key])
    self.system_bg=bg_data
    # correct the background of the nicr data
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
      if key[1:] in bg_data:
        background_data_list=bg_data[key[1:]]
        background_data_list.sort(lambda b1, b2: cmp(b1.dns_info['detector_bank_2T'], 
                                                     b2.dns_info['detector_bank_2T']))
        background_data_angles=[b.dns_info['detector_bank_2T'] for b in background_data_list]
        i=0
        angle=data.dns_info['detector_bank_2T']
        while background_data_angles[i]<=angle:
          if i+1<len(background_data_list):
            i+=1
          else:
            break
        if  background_data_angles[i]-angle < angle-background_data_angles[i-1] or i==0:
          background_data=background_data_list[i]
        else:
          background_data=background_data_list[i-1]
        data.process_function(subtract_background)
        data.name+='-'+background_data.name
        bg_corrected_data[key]=data
      elif self.CORRECT_FLIPPING:
        print "No background data for file %s found, flipping ration correction not correct." % data.name
        bg_corrected_data[key]=data        
    self.bg_corrected_nicr_data=bg_corrected_data
    for file_name in vana_files:
      if file_name.endswith('.d7'):
        datasets=read_data.dns.read_data_d7(file_name)
      else:
        datasets=[read_data.dns.read_vana_d7(file_name)]
      for dataset in datasets:
        bgs=False
        if vana_data:
          detector=round(float(dataset.dns_info['detector_bank_2T']), 0)
          flip=round(float(dataset.dns_info['flipper']), 2)
          flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
          c_a=round(float(dataset.dns_info['C_a']), 2)
          c_b=round(float(dataset.dns_info['C_b']), 2)
          c_c=round(float(dataset.dns_info['C_c']), 2)
          c_z=round(float(dataset.dns_info['C_z']), 2)
          key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
          vana_data.name+='+'+os.path.split(file_name)[1]
          if key in bg_data:
            detectors=map(lambda bg: round(bg.dns_info['detector_bank_2T'], 0), bg_data[key])
            # subtract backgound from vanadium if suitable is found.
            if detector in detectors:
              backgound_data=bg_data[key][detectors.index(detector)]
              dataset.process_function(subtract_background)
              vana_data.name+='-'+backgound_data.name.replace('+', '-')
              bgs=True
          for i, data in enumerate(dataset):
            vana_data.data[1].values[i]+=data[1]
            vana_data.data[2].values[i]=sqrt((vana_data.data[2].values[i]**2+data[2]**2)/2.)
        else:
          vana_data=dataset
          vana_data.name=os.path.split(file_name)[1]
          detector=round(float(vana_data.dns_info['detector_bank_2T']), 0)
          flip=round(float(vana_data.dns_info['flipper']), 2)
          flip_cmp=round(float(vana_data.dns_info['flipper_compensation']), 2)
          c_a=round(float(vana_data.dns_info['C_a']), 2)
          c_b=round(float(vana_data.dns_info['C_b']), 2)
          c_c=round(float(vana_data.dns_info['C_c']), 2)
          c_z=round(float(vana_data.dns_info['C_z']), 2)
          key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
          if key in bg_data:
            detectors=map(lambda bg: round(bg.dns_info['detector_bank_2T'], 0), bg_data[key])
            # subtract backgound from vanadium if suitable is found.
            if detector in detectors:
              background_data=bg_data[key][detectors.index(detector)]
              vana_data.process_function(subtract_background)
              vana_data.name+='-'+background_data.name.replace('+', '-')
              bgs=True
        if not bgs and self.AUTO_VANADIUM:
          print "No backgound data for file %s, vanadium correction will not be correct." % file_name
    if vana_data:
      scale=vana_data.data[1][:].sum()/len(vana_data)
      vana_data.data[1]/=scale
      vana_data.data[2]/=scale
    self.system_vana=vana_data
    if directorys[-1]==os.path.join(self.TEMP_DIR, 'setup'):
      # remove files
      for file_name in os.listdir(directorys[-1]):
        os.remove(os.path.join(directorys[-1], file_name))
      os.rmdir(directorys[-1])      

  def read_bg_file(self, bg_file, bg_data):
    '''
      Read one background file and add it to a dictionary.
      The dictionary keys correspond to the flipper and helmholz
      coil currents.
      
      @param bg_file File name to read from
      @param bg_data The dictionary to write to
    '''
    dataset=read_data.dns.read_data(bg_file)
    if dataset=='NULL':
      # if there was a problem in the file return False
      return False
    if self.BACKGROUND_SCALING!=1.:
      def scale_background(point):
        out=[point[0]]
        for pi in point[1:]:
          out.append(pi*self.BACKGROUND_SCALING)
        return out
      dataset.process_function(scale_background)
    dataset.name=os.path.split(bg_file)[1]
    flip=round(float(dataset.dns_info['flipper']), 2)
    flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
    c_a=round(float(dataset.dns_info['C_a']), 2)
    c_b=round(float(dataset.dns_info['C_b']), 2)
    c_c=round(float(dataset.dns_info['C_c']), 2)
    c_z=round(float(dataset.dns_info['C_z']), 2)
    key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
    if key in bg_data:
      bg_data[key].append(dataset)
    else:
      bg_data[key]=[dataset]
    return True
  
  def read_bg_file_d7(self, bg_file, bg_data):
    '''
      Read one background file and add it to a dictionary.
      The dictionary keys correspond to the flipper and helmholz
      coil currents.
      
      @param bg_file File name to read from
      @param bg_data The dictionary to write to
    '''
    datasets=read_data.dns.read_data_d7(bg_file)
    if datasets=='NULL':
      # if there was a problem in the file return False
      return False
    for dataset in datasets:
      if self.BACKGROUND_SCALING!=1.:
        def scale_background(point):
          out=[point[0]]
          for pi in point[1:]:
            out.append(pi*self.BACKGROUND_SCALING)
          return out
        dataset.process_function(scale_background)
      dataset.name=os.path.split(bg_file)[1]
      flip=round(float(dataset.dns_info['flipper']), 2)
      flip_cmp=round(float(dataset.dns_info['flipper_compensation']), 2)
      c_a=round(float(dataset.dns_info['C_a']), 2)
      c_b=round(float(dataset.dns_info['C_b']), 2)
      c_c=round(float(dataset.dns_info['C_c']), 2)
      c_z=round(float(dataset.dns_info['C_z']), 2)
      key=(flip, flip_cmp, c_a, c_b, c_c, c_z)
      if key in bg_data:
        bg_data[key].append(dataset)
      else:
        bg_data[key]=[dataset]
    return True
  
  def correct_flipping_ratio(self, scattering_propability=0.1):
    '''
      This function assigns the right NiCr measurements to the data sequences.
      The flipper and Helmolz currents are used to identify the right data.
      
      @param scattering_propability Propapility of a neutron to get scattered inside the sample (=1-Transmission)
      
      @return If files could be found with the right settings.
    '''
    # search for appropiate standard measurements
    data_nicr={}
    for dataset in self.active_file_data:
      # get the currents
      detector=float(dataset.dns_info['detector_bank_2T'])
      flip=float(dataset.dns_info['flipper'])
      flip_cmp=float(dataset.dns_info['flipper_compensation'])
      c_a=float(dataset.dns_info['C_a'])
      c_b=float(dataset.dns_info['C_b'])
      c_c=float(dataset.dns_info['C_c'])
      c_z=float(dataset.dns_info['C_z'])
      use_key=False
      # create a key for the currents and search for it in the
      # background corrected nicr data dictionary
      for key in self.bg_corrected_nicr_data.keys():
        if abs(key[0]-detector)<1.1 and \
           abs(key[1]-flip)<0.05 and \
           abs(key[2]-flip_cmp)<0.05 and \
           abs(key[3]-c_a)<0.05 and \
           abs(key[4]-c_b)<0.05 and \
           abs(key[5]-c_c)<0.05 and \
           abs(key[6]-c_z)<0.05:
          use_key=key
      if use_key:
        # there have to be two flipper channels
        if not use_key[3:] in data_nicr:
          data_nicr[use_key[3:]]=[(use_key[1:3]==(0., 0.), self.bg_corrected_nicr_data[use_key], dataset)]
        elif len(data_nicr[use_key[3:]])==1:
          data_nicr[use_key[3:]].append((use_key[1:3]==(0., 0.), self.bg_corrected_nicr_data[use_key], dataset))
          # put spin-flip channels first
          data_nicr[use_key[3:]].sort()
          data_nicr[use_key[3:]].reverse()
        else:
          print "To many chanels for %s, skipping." % str(key)
      else:
        print "\tNo NiCr data file found at detector bank=%g for helmholz currents (a,b,c,z):%.2f,%.2f,%.2f,%.2f" % ( 
                                            detector, c_a, c_b, c_c, c_z)
    # calculate flipping-ration from nicr data
    def calc_flipping_ratio(point):
      pp=item[1][1].data
      point[1]/=maximum(nan_to_num(array(pp[1].values)), abs(array(pp[2].values)))
      point[2]*=0.
      return point
    from copy import deepcopy
    data_flippingratio={}
    for key, item in data_nicr.items():
      if len(item)==1:
        print "Lonely channel found, skipping"
        continue
      else:
        flipping_ratio=deepcopy(item[0][1])
        flipping_ratio.process_function(calc_flipping_ratio)
        data_flippingratio[key]=(flipping_ratio, item[0][2], item[1][2])
    for item in data_flippingratio.values():
      # assign nicr to the chanels
      one_first=self.active_file_data.index(item[1])<self.active_file_data.index(item[2])
      item[1].flipping_correction=(not one_first, item[0], item[2])
      item[1].scattering_propability=scattering_propability
      item[2].flipping_correction=(one_first, item[0], item[1])
      item[2].scattering_propability=scattering_propability
  
class DNSMeasurementData(MeasurementData):
  '''
    Class derived from MeasurementData to be more suitable for DNS measurements.
    Datatreatment is done here and additional data treatment functions should
    be put here, too.
    
  Doc of MeasurementData:
  '''
  try:
    __doc__+=MeasurementData.__doc__
  except:
    pass
  SPLIT_SENSITIVITY=0.01
  dns_info={}
  scan_line=1
  scan_line_constant=3
  number_of_channels=1
  vanadium_data=None
  vanadium_correct_by_detector=True
  background_data=None
  # if a flipping correction is made this is a list of
  # [SF-Chanel?, nicr-data, other_DNSMeasurement]
  flipping_correction=None 
  scattering_propability=0.1
  
  def get_info(self):
    '''
      Replacement of the general get_info function.
    '''
    outstring=""
    if self.background_data is not None:
      outstring+="Background files used for detector bank positions:\n"
      for key, value in sorted(self.background_data.items()):
        outstring+="\t%.2f:\t%s\n" % (key, value.name)
    if self.vanadium_data is not None:
      outstring+="Vanadium files used for detector sensitivity correctio:\n"
      names=self.vanadium_data.name.split('+')
      for i, name in enumerate(names):
        outstring+="\t%s" % (name)
        if (i%5)==4 and i!=(len(names)-1):
          outstring+="\n"
      outstring+="\n"
    if self.flipping_correction is not None:
      outstring+="Flippng ratio correction has been made with:\n"
      outstring+="\tScattering propability: %.1f%%\n" % (self.scattering_propability*100.)
      outstring+="\tFile used: %s\n" % self.flipping_correction[1].name
    outstring+="\n\nHeader information read from first file:\n"
    outstring+=self.info
    return outstring
  
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
    if self.zdata>0:
      qx_index=len(self.units())-3
      qy_index=qx_index+1
      lambda_n=self.dns_info['lambda_n']
      two_pi_over_lambda=2.*pi/lambda_n
      grad_to_rad=1.#pi/180.
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
      self.data[qx_index].unit='Å^{-1}'
      self.data[qy_index].unit='Å^{-1}'
      self.data[qx_index].dimension='q_x'
      self.data[qy_index].dimension='q_y'
      self.xdata=qx_index
      self.ydata=qy_index
    else:
      # Powderdata
      q_index=len(self.units())-3
      d_index=q_index+1
      lambda_n=self.dns_info['lambda_n']
      two_pi_over_lambda=2.*pi/lambda_n
      grad_to_rad=pi/180.
      # calculation of the wavevector, also works with arrays
      def angle_to_wavevector(point):
        output=point
        output[q_index]=sin(0.5*point[3]*grad_to_rad)*2.*two_pi_over_lambda
        output[d_index]=2.*pi/output[q_index]
        return output    
      self.process_function(angle_to_wavevector)
      self.data[q_index].unit='Å^{-1}'
      self.data[d_index].unit='Å'
      self.data[q_index].dimension='q'
      self.data[d_index].dimension='d'
      self.xdata=q_index
  
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
      sys.stdout.write("background subtraction, ")
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
    try:
      converged=self.make_flipping_correction([self.flipping_correction[1], self, other], self.scattering_propability)
    except ValueError:
      sys.stdout.write("different data length")
      sys.stdout.flush()      
    if not self.vanadium_data is None:
      sys.stdout.write("up-vanadium, ")
      sys.stdout.flush()
      self.process_function(self.correct_vanadium)
    if not other.vanadium_data is None:
      sys.stdout.write("down-vanadium, ")
      sys.stdout.flush()
      other.process_function(other.correct_vanadium)
    if self.zdata>-1:
      if self.dns_info['flipper']==0.:
        self.data[7].dimension='I_0^+'
        other.data[7].dimension='I_0^-'
      else:
        self.data[7].dimension='I_0^-'
        other.data[7].dimension='I_0^+'
      self.zdata=self.number_of_channels*2+5
      self.yerror=self.number_of_channels*3+5
      other.zdata=other.number_of_channels*2+5
      other.yerror=other.number_of_channels*3+5
    else:
      if self.dns_info['flipper']==0.:
        self.data[7].dimension='I_0^+'
        other.data[7].dimension='I_0^-'
      else:
        self.data[7].dimension='I_0^-'
        other.data[7].dimension='I_0^+'
      self.ydata=self.number_of_channels*2+5
      self.yerror=self.number_of_channels*3+5
      other.ydata=other.number_of_channels*2+5
      other.yerror=other.number_of_channels*3+5
  
  def make_flipping_correction(self, item, scattering_propability):
    '''
      Calculate the flipping ratio correction for all intensity chanels.
      
      @param item Sequence of NiCr-data, self and other DNSMeasurementData object
      @param scattering_propability Propability of a neutron to scatter in the sample
      
      @return If all corrections converged
    '''
    nc=self.number_of_channels
    converged=True
    for i in range(nc):
      yindex=i+nc*2+5
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
        p_data, m_data, conv = correct_flipping_ratio(nicr_data, pp_data, pm_data, 
                                                                             scattering_propability, test)
        converged=converged and conv
      else:
        p_data=[]
        m_data=[]
        for i in range(len(pp_data)):
          p, m, conv = correct_flipping_ratio(nicr_data[i], pp_data[i], pm_data[i], scattering_propability)
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
      point[i+2*nc+5]=point[i+5][:]
      point[i+3*nc+5]=point[i+nc+5][:]
      point[i+2*nc+5].dimension='I_%i' % i
      point[i+3*nc+5].dimension='Error_%i' % i
    return point
  
  if use_numpy:
    #++++++++++++ calculations for use with arrays +++++++++++++++++
    def correct_background(self, point):
      '''
        Subtract background from the intensity data and calculate new
        error for these values.
        
        @param point List of arrays for all columns
        
        @return Changed list of arrays
      '''
      nc=self.number_of_channels
      # find the background for the right detectors
      # create a list of all columns in the background files
      background_data=self.background_data
      detector_positions=point[0]
      detectors=point[4]
      #bg_items=[background_data[det_pos] for det_pos in detector_positions]
      bg=[zeros(len(detector_positions)) for i in range(nc*2)]
      for key, value in background_data.items():
        first_det=value.data[0][0]
        indices=where(detector_positions==key)[0]
        detector_indices=(detectors[indices]-first_det).astype(int)
        for i in range(nc*2):
          bg[i][indices]=value.data[i+1][detector_indices]
      #  print indices
      #  bg_items[indices]=background_data[key]
      #if 'detector_angles' in background_data.values()[0].dns_info:
      #  bg_columns=[[] , []]
      #else:
      #  bg_columns=[[] for i in range(len(background_data.values()[0].data)-1)]
      #for i, detector in enumerate(detectors):
      #  bg_data=bg_items[i].data
      #  for j, column in enumerate(bg_columns):
      #    column.append(bg_data[j+1].values[bg_data[0].values.index(detector)])
      #bg=map(array, bg_columns)
      for i in range(nc):
        point[i+2*nc+5]=point[i+5]-bg[i]
        point[i+3*nc+5]=sqrt(point[i+nc+5]**2 + bg[i+nc]**2)
        point[i+2*nc+5].dimension='I_%i' % i
        point[i+3*nc+5].dimension='Error_%i' % i
      return point
    
    def correct_vanadium(self, point):
      '''
        Devide the intensity by the counts measured with vanadium for the
        same detector bank.
        
        @param point List of arrays for all columns
        
        @return Changed list of arrays
      '''
      nc=self.number_of_channels
      # find the background for the right detector
      # create a list of all columns in the background file
      vn_list=self.vanadium_data.data
      # search the indices for the detectors
      if self.vanadium_correct_by_detector:
        # the detector minus the first detector name is the index
        vn_indices=(point[4]-vn_list[0][0]).astype(int)
      else:
        # get indices for tth values
        vn_indices=array(map(lambda tth: vn_lists[0].index([item for item in vn_lists[0] if item<=tth][-1]), point[3])).astype(int)
      # create a list of arrays with the corresponding intensities
      vn=vn_list[1][vn_indices]
      errvn=vn_list[2][vn_indices]
      for i in range(nc):
        point[i+2*nc+5]/=vn
        point[i+3*nc+5]=self.error_propagation_quotient([point[i+2*nc+5], point[i+3*nc+5]],[vn, errvn])
      return point
  
    def __add__(self, other):
      '''
        Defines how two objects of this class should be add with '+'.
      '''
      if len(self) != len(other):
        raise ValueError, 'Can only add datasets with the same length.'
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
      '''
        Defines how two objects of this class should be subtracted with '-'.
      '''
      if len(self) != len(other):
        raise ValueError, 'Can only subtract datasets with the same length.'
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
    
    def __mul__(self, other):
      '''
        Multiply the data by data of a different dataset.
      '''
      if len(self) != len(other):
        raise ValueError, 'Can only multiply datasets with the same length.'
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        result.data[i+5].values=list(array(self.data[i+5].values)*array(other.data[i+5].values))
        result.data[i+nc+5].values=list(sqrt((array(self.data[i+nc+5].values)*array(other.data[i+5].values))**2 \
                                          + (array(other.data[i+nc+5].values)*array(self.data[i+5].values))**2))
        result.data[i+2*nc+5].values=list(array(self.data[i+2*nc+5].values)*array(other.data[i+2*nc+5].values))
        result.data[i+3*nc+5].values=list(sqrt((array(self.data[i+3*nc+5].values)*array(other.data[i+2*nc+5].values))**2\
                                             +(array(other.data[i+3*nc+5].values)*array(self.data[i+2*nc+5].values))**2))
      return result      
    
    def __div__(self, other):
      '''
        Divide the data by data of a different dataset.
      '''
      if len(self) != len(other):
        raise ValueError, 'Can only divide datasets with the same length.'
      # create a new instance of the class
      from copy import deepcopy
      result=deepcopy(self)
      nc=self.number_of_channels
      for i in range(nc):
        result.data[i+5].values=list(array(self.data[i+5].values)/array(other.data[i+5].values))
        result.data[i+nc+5].values=list(sqrt((array(self.data[i+nc+5].values)/array(other.data[i+5].values))**2 \
                                          + (array(other.data[i+nc+5].values)*array(self.data[i+5].values)\
                                                                            /array(other.data[i+5].values)**2)**2))
        result.data[i+2*nc+5].values=list(array(self.data[i+2*nc+5].values)/array(other.data[i+2*nc+5].values))
        result.data[i+3*nc+5].values=list(sqrt((array(self.data[i+3*nc+5].values)/array(other.data[i+2*nc+5].values))**2\
                                             +(array(other.data[i+3*nc+5].values)*array(self.data[i+2*nc+5].values)\
                                                                                /array(other.data[i+2*nc+5].values)**2)**2))
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
        
        @param point A list of column entries
        
        @return Altered list of column entries
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
        
        @param point A list of column entries
        
        @return Altered list of column entries
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
      '''
        Defines how two objects of this class should be add with '+'.
      '''
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
      '''
        Defines how two objects of this class should be subtracted with '-'.
      '''
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
  
