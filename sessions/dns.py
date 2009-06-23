#!/usr/bin/env python
'''
  class for DNS data sessions
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

import os
from math import pi, cos, sin, sqrt
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
__version__ = "0.6a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class DNSSession(GenericSession):
  '''
    Class to handle dns data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tDNS-Data treatment:
\t-inc\tinc\tThe default increment between files of the same polarization.
\t-ooff\tooff\tOffset of omega angle for the sample to calculate the right q_x,q_y
\t-vana\tfile\tUse different Vanadium file for evaluation.
\t-files\tprefix ooff inc from to postfix
\t\t\tExplicidly give the file name prefix, omega offset, increment, numbers and postfix
\t\t\tfor the files to be used. Can be given multiple times for diefferent prefixes.
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('All','*'), ('DNS (.d_dat)', '*.d_dat'))

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['inc', 'ooff', 'bg', 'vana', 'files'] 
  file_options={'default': [0, 1, [0, -1], ''],  # (omega_offset, increment, range, postfix)
                } # Dictionary storing specific options for files with the same prefix
  prefixes=[]
  mds_create=False
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      Class constructor which is called with the command line arguments.
      Evaluates the command line arguments, creates a file list and
      starts the data readout procedure.
      In contrast do most sessions this changes the generic constructor
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
    self.try_import_externals()
    names.sort()
    if len(names) > 0:
      self.find_prefixes(names)
    self.prefixes.sort()
    for prefix in self.prefixes:
      self.read_files(prefix)

    if len(self.prefixes) == 0: # show help, if there is no valid file in the list
      print "No valid datafile found!"
      print self.SHORT_HELP
      exit()
    self.active_file_data=self.file_data[self.prefixes[0]]
    self.active_file_name=self.prefixes[0]
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      additional command line arguments for dns sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        if last_argument_option[1]=='inc':
          self.file_options['default'][1]=int(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='ooff':
          self.file_options['default'][0]=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='vana':
          self.vanadium_file=argument
          last_argument_option=[False,'']
        # explicit file setting:
        elif last_argument_option[1]=='files':
          self.file_options[argument]=[]
          self.prefixes.append(argument)
          last_argument_option=[True,'files_1', argument]
        # omega offset
        elif last_argument_option[1]=='files_1':
          self.file_options[last_argument_option[2]].append(float(argument))
          last_argument_option=[True,'files_2', last_argument_option[2]]
        # increment
        elif last_argument_option[1]=='files_2':
          self.file_options[last_argument_option[2]].append(int(argument))
          last_argument_option=[True,'files_3', last_argument_option[2]]
        # from
        elif last_argument_option[1]=='files_3':
          self.file_options[last_argument_option[2]].append([int(argument)])
          last_argument_option=[True,'files_4', last_argument_option[2]]
        # to
        elif last_argument_option[1]=='files_4':
          self.file_options[last_argument_option[2]][2].append(int(argument))
          last_argument_option=[True,'files_5', last_argument_option[2]]
        # postfix
        elif last_argument_option[1]=='files_5':
          self.file_options[last_argument_option[2]].append(argument)
          last_argument_option=[False,'']
        else:
          found=False
#      elif argument=='-no-img':
#        self.import_images=False
#        found=True
      else:
        found=False
    return (found, last_argument_option)


  def read_files(self, prefix):
    '''
      Function to read data files.
    '''
    if prefix in self.file_options:
      omega_offset=self.file_options[prefix][0]
      increment=self.file_options[prefix][1]
      num_range=self.file_options[prefix][2]
      postfix=self.file_options[prefix][3]
    else:
      omega_offset=self.file_options['default'][0]
      increment=self.file_options['default'][1]
      num_range=self.file_options['default'][2]
      postfix=self.file_options['default'][3]
    file_split=prefix.rsplit(os.sep, 1)
    if len(file_split)==1:
      folder='.'
      fileprefix=file_split[0]
    else:
      folder, fileprefix=file_split
    # create a list of all files starting with the fileprefix
    file_list=[file for file in os.listdir(folder) if fileprefix == file[0:len(fileprefix)]]
    if len(file_list)==0:
      return None
    file_list.sort()
    if postfix=='':
      # try to find the postfix
      postfix_index=len(fileprefix)
      while len(file_list[0])>postfix_index and file_list[0][postfix_index].isdigit():
        postfix_index+=1
      postfix=file_list[0][postfix_index:]
    self.file_options[prefix]=[omega_offset, increment, num_range, postfix]
    self.file_data[prefix+'|raw_data']=[]
    for file_name in file_list:
      active_number=int(file_name.rsplit(postfix)[0].split(prefix, 1)[1])
      if (active_number>=num_range[0]) and (active_number<=num_range[1] or num_range[1]==-1):
        dataset=read_data.dns.read_data(os.path.join(folder, file_name))
        dataset.number=str(active_number)
        self.file_data[prefix+'|raw_data'].append(dataset)
    self.create_maps(prefix)
    return None
  
  def create_maps(self, prefix):
    scans=self.file_data[prefix+'|raw_data']
    self.file_data[prefix]=[]
    omega_offset=self.file_options[prefix][0]
    increment=self.file_options[prefix][1]
    num_range=self.file_options[prefix][2]
    postfix=self.file_options[prefix][3]
    def append_to_map(point):
      return [file_number, 
              omega-omega_offset, 
              omega, 
              point[0]*config.dns.DETECTOR_ANGULAR_INCREMENT+config.dns.FIRST_DETECTOR_ANGLE+detector_bank_2T, 
              point[0]
              ]+point[1:]+point[1:]+[0, 0]
    for i, scan in enumerate(scans):
      if i<increment:
        columns=[['Filenumber', ''], ['Omega', '\302\260'], ['OmegaRAW', '\302\260'], 
                 ['2Theta', '\302\260'], ['Detector', '']]+\
                 [[scan.dimensions()[j], scan.units()[j]] for j in range(1, len(scan.units()))]+\
                 [['I_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-1)/2)]+\
                 [['error_%i' % j, 'a.u.'] for j in range(0, (len(scan.units())-1)/2)]+\
                 [['q_x', '\303\205^{-1}'], ['q_y', '\303\205^{-1}']]
        self.file_data[prefix].append(DNSMeasurementData(columns, [], 1, 3, (len(scan.units())-1)/2+5, zdata=5))
        self.file_data[prefix][i].number=str(i)
        self.file_data[prefix][i].dns_info=scan.dns_info
        self.file_data[prefix][i].number_of_channels=(len(scan.units())-1)/2
      data=[point for point in scan]
      file_number=int(scan.number)
      detector_bank_2T=scan.dns_info['detector_bank_2T']
      omega=scan.dns_info['omega']
      map(self.file_data[prefix][i%increment].append, map(append_to_map, data))
    for dnsmap in self.file_data[prefix]:
      dnsmap.calculate_wavevectors()
      dnsmap.make_corrections()

  def find_prefixes(self, names):
    '''
      Try to find prefixes from a list of filenames.
      config.dns.min_prefix_length is used to split different
      sets of files.
    '''
    split_names=[[]]
    tmp_prefix=names[0][0:config.dns.min_prefix_length]
    for name in names:
      if name.startswith(tmp_prefix):
        split_names[-1].append(name)
      else:
        split_names.append([name])
    for snames in split_names:
      prefix=snames[0]
      for name in snames:
        # cut prefix until it is common for every file
        while not name.startswith(prefix):
          prefix=prefix[0:-1]
      self.prefixes.append(prefix)
    

  def create_menu(self):
    '''
      create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='DNS'>
        <menuitem action='SetOmegaOffset' />
        <menuitem action='SetIncrement' />
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
                None ),
            ( "SetIncrement", None,                             # name, stock id
                "Change Increment", None,                    # label, accelerator
                "Change Increment between files with same Polarization",                                   # tooltip
                None ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

class DNSMeasurementData(MeasurementData):
  dns_info={}
  scan_line=4
  scan_line_constant=1
  number_of_channels=1
  vanadium_file=None
  background_file=None
  
  def calculate_wavevectors(self):
    '''
      Calculate the wavevectors from omega, 2Theta and lambda.
    '''
    qx_index=len(self.units())-2
    qy_index=qx_index+1
    lambda_n=self.dns_info['lambda_n']
    two_pi_over_lambda=2*pi/lambda_n
    grad_to_rad=pi/180.
    
    def angle_to_wavevector(point):
      output=point
      output[qx_index]=(cos(-point[1]*grad_to_rad)-\
                cos(-point[1]*grad_to_rad + point[3]*grad_to_rad))*\
                two_pi_over_lambda
      output[qy_index]=(sin(-point[1]*grad_to_rad)-\
                sin(-point[1]*grad_to_rad + point[3]*grad_to_rad))*\
                two_pi_over_lambda
      return output
    
    self.process_funcion(angle_to_wavevector)
    self.xdata=qx_index
    self.ydata=qy_index
  
  def make_corrections(self):
    '''
      Correct the data for background and Vanadium standart.
      The rawdata is not changed only the I column.
    '''
    if not self.background_file is None:
      self.process_funcion(self.correct_background)
    if not self.vanadium_file is None:
      self.process_funcion(self.correct_vanadium)
  
  def correct_background(self, point):
    nc=self.number_of_channels
    for bg_point in self.background_file:
      if bg_point[0] ==  point[4]:
        bg=point[1:]
    for i in range(nc):
      point[i+2*nc+5]=point[i+5]-bg[i]
      point[i+3*nc+5]=sqrt(point[i+nc+5]**2 + bg[i+nc]**2)
    return point
  
  def correct_vanadium(self, point):
    return point
  
  
