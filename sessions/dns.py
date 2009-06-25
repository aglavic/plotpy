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
except InputError:
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
\t-bg\tbg\tFile to be substracted as background.
\t-vana\tfile\tUse different Vanadium file for evaluation.
\t-samplet\tname\tSet the name of your sample to be used in every plot(can be changed in GUI).
\t-files\tprefix ooff inc from to postfix
\t\t\tExplicidly give the file name prefix, omega offset, increment, numbers and postfix
\t\t\tfor the files to be used. Can be given multiple times for diefferent prefixes.

\tShort info settings: 
\t\t-time, -flipper, -monitor
\t\t\tDon't use temperature for the short info but time, flipper or monitor value.'
\t\t-xyz\txyz polarization analysis, implies -inc 6
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=(('All','*'), ('DNS (.d_dat)', '*.d_dat'))

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+['inc', 'ooff', 'bg', 'vana', 'files', 'sample', 'time', 'flipper', 'monitor', 'powder', 'xyz'] 
  file_options={'default': ['', 0, 1, [0, -1], ''],  # (prefix, omega_offset, increment, range, postfix)
                } # Dictionary storing specific options for files with the same prefix
  prefixes=[]
  mds_create=False
  VANADIUM_FILE=None#config.dns.VANADIUM_FILE
  BACKGROUND_FILE=None#"/home/glavic/Daten/DNS/TbMnO3-81958/ag340378tbmn.d_dat"
  SHORT_INFO=[('temperature', lambda temp: 'at T='+str(temp), 'K')]
  SAMPLE_NAME=''
  POWDER_DATA=False
  ONLY_IMPORT_MULTIFILE=True
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
          self.file_options['default'][2]=int(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='ooff':
          self.file_options['default'][1]=float(argument)
          last_argument_option=[False,'']
        elif last_argument_option[1]=='bg':
          self.BACKGROUND_FILE=argument
          last_argument_option=[False,'']
        elif last_argument_option[1]=='vana':
          self.VANADIUM_FILE=argument
          last_argument_option=[False,'']
        # Set sample name:
        elif last_argument_option[1]=='sample':
          self.SAMPLE_NAME=argument
          last_argument_option=[False,'']
        # explicit file setting:
        elif last_argument_option[1]=='files':
          new_options=[]
          new_options.append(argument)
          last_argument_option=[True,'files_1', new_options]
        # omega offset
        elif last_argument_option[1]=='files_1':
          last_argument_option[2].append(float(argument))
          last_argument_option=[True,'files_2', last_argument_option[2]]
        # increment
        elif last_argument_option[1]=='files_2':
          last_argument_option[2].append(int(argument))
          last_argument_option=[True,'files_3', last_argument_option[2]]
        # from
        elif last_argument_option[1]=='files_3':
          last_argument_option[2].append([int(argument)])
          last_argument_option=[True,'files_4', last_argument_option[2]]
        # to
        elif last_argument_option[1]=='files_4':
          last_argument_option[2][3].append(int(argument))
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
          first_file=sorted([file for file in os.listdir(directory) if file.startswith(file_prefix) and file.endswith(file_postfix)])[0]
          self.prefixes.append(first_file)
          self.file_options[first_file]=last_argument_option[2]
          last_argument_option=[False,'']
        else:
          found=False
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
        self.file_options['default'][2]=6
        def flipper_on(current):
          if current > 0.1:
            return "flipper on"
          else:
            return "flipper off"
        self.SHORT_INFO=[('flipper', flipper_on, ''), 
                         ('C_a', lambda I: 'C_a='+str(I), 'A'), 
                         ('C_b', lambda I: 'C_b='+str(I), 'A'), 
                         ('C_c', lambda I: 'C_c='+str(I), 'A')]
      else:
        found=False
    return (found, last_argument_option)

  def add_file(self, filenames, append=True):
    '''
      In contrast to other sessions this is only called
      from the gui to add new files.
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
      Function to read data files. 
      The files are split by their prefixes.
    '''
    prefix=self.file_options[file][0]
    omega_offset=self.file_options[file][1]
    increment=self.file_options[file][2]
    num_range=self.file_options[file][3]
    postfix=self.file_options[file][4]
    file_split=prefix.rsplit(os.sep, 1)
    if len(file_split)==1:
      folder='.'
      fileprefix=file_split[0]
    else:
      folder, fileprefix=file_split
    # create a list of all files starting with the fileprefix
    file_list=[lfile for lfile in os.listdir(folder) if lfile.startswith(fileprefix) and lfile.endswith('.d_dat')]
    if len(file_list)==0:
      return None
    file_list.sort()
    self.file_data[file+'|raw_data']=[]
    print "Reading files %s{num}%s with num from %i to %i." % (prefix, postfix, num_range[0], num_range[1])
    for file_name in file_list:
      try:
        active_number=int(os.path.join(folder, file_name).rsplit(postfix)[0].split(prefix, 1)[1])
      except ValueError:
        continue
      if (active_number>=num_range[0]) and (active_number<=num_range[1] or num_range[1]==-1):
        dataset=read_data.dns.read_data(os.path.join(folder, file_name))
        dataset.number=str(active_number)
        self.file_data[file+'|raw_data'].append(dataset)
    print "\tRead, creating map."
    self.create_maps(file)
    return None
  
  def create_maps(self, file):
    '''
      Crates a 3d MeasurementData object which can be used to
      plot color maps of the measurement.
      For Powder data it is only shown as 2Theta vs intensity.
    '''
    scans=self.file_data[file+'|raw_data']
    self.file_data[file]=[]
    prefix=self.file_options[file][0]
    omega_offset=self.file_options[file][1]
    increment=self.file_options[file][2]
    num_range=self.file_options[file][3]
    postfix=self.file_options[file][4]
    def append_to_map(point):
      return [file_number, 
              omega-omega_offset-detector_bank_2T, 
              omega-detector_bank_2T, 
              point[0]*config.dns.DETECTOR_ANGULAR_INCREMENT+config.dns.FIRST_DETECTOR_ANGLE-detector_bank_2T, 
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
        self.file_data[file].append(DNSMeasurementData(columns, [], 1, 3, (len(scan.units())-1)/2+5, zdata=5))
        active_map=self.file_data[file][i]
        active_map.number=str(i)
        active_map.dns_info=scan.dns_info
        active_map.number_of_channels=(len(scan.units())-1)/2
        active_map.short_info=" ".join([info[1](scan.dns_info[info[0]])+info[2] for info in self.SHORT_INFO])
        active_map.sample_name=self.SAMPLE_NAME
        active_map.info= "\n".join(map(lambda item: item[0]+': '+str(item[1]),
                                    sorted(scan.dns_info.items())))
      data=[point for point in scan]
      file_number=int(scan.number)
      detector_bank_2T=scan.dns_info['detector_bank_2T']
      omega=scan.dns_info['omega']
      map(self.file_data[file][i%increment].append, map(append_to_map, data))
    for dnsmap in self.file_data[file]:
      sys.stdout.write("\tMap %s created, perfoming datatreatment: " % dnsmap.number)
      sys.stdout.flush()
      if not self.BACKGROUND_FILE is None:
        dnsmap.background_data=read_data.dns.read_data(self.BACKGROUND_FILE)
      if not self.VANADIUM_FILE is None:
        dnsmap.vanadium_data=read_data.dns.read_data(self.VANADIUM_FILE)
      sys.stdout.write("calculate wavevectors, ")
      sys.stdout.flush()
      dnsmap.calculate_wavevectors()
      dnsmap.make_corrections()
      sys.stdout.write("\n")
      sys.stdout.flush()
      if self.POWDER_DATA:
        # for powder data show 1d plot 2Theta vs intensity
        dnsmap.sort(3)
        dnsmap.zdata=-1
        dnsmap.xdata=3
        dnsmap.ydata=5

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
      self.prefixes.append(item[1][0]+item[1][1]+item[1][3])
      self.file_options[item[1][0]+item[1][1]+item[1][3]]=[item[1][0]+item[1][1][:i-1], 
                                                           self.file_options['default'][1], 
                                                           self.file_options['default'][2], 
                                                           [int(item[1][1][i-1:]), 
                                                           int(item[1][2][i-1:])], 
                                                           item[1][3]]    

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
                self.change_omega_offset ),
            ( "SetIncrement", None,                             # name, stock id
                "Change Increment", None,                    # label, accelerator
                "Change Increment between files with same Polarization",                                   # tooltip
                self.change_increment ),
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
      if len(name.split("|raw_data", 1))==1:
        print "Plotting '" + name + "' sequences."
        self.plot_active()
  
  
  
  #++++++++++++++++++++++++++ GUI functions ++++++++++++++++++++++++++++++++
  def change_omega_offset(self, action, window):
    '''
      A dialog to change the omega offset of the active map.
      If no map is active at the moment it does nothing.
    '''
    if not self.active_file_name in self.file_options:
      return None
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
    result=ooff_dialog.run()
    while result > 1:
      ooff=float(input_filed.get_text())
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      window.replot()
      result=ooff_dialog.run()
    if result==1:
      ooff=float(input_filed.get_text())
      self.file_options[self.active_file_name][1]=ooff
      self.active_file_data[window.index_mess].change_omega_offset(ooff)
      window.replot()
    ooff_dialog.destroy()

  def change_increment(self, action, window):
    '''
      Change the increments between files of the same polarization
      chanel. New maps are created after this change.
    '''
    if not self.active_file_name in self.file_options:
      return None
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
    result=inc_dialog.run()
    if result==1:
      inc=int(input_filed.get_text())
      self.file_options[self.active_file_name][2]=inc
      self.create_maps(self.active_file_name)
      object=self.file_data[self.active_file_name]
      window.change_active_file_object((self.active_file_name, object))
    inc_dialog.destroy()


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
  background_data=None
  
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
  
  def change_omega_offset(self, omega_offset):
    '''
      Recalculate omega and q_x, q_y for a new offset value.
    '''
    def calc_omega(point):
      point[1]=point[2]-omega_offset
      return point
    self.process_funcion(calc_omega)
    self.calculate_wavevectors()
  
  def make_corrections(self):
    '''
      Correct the data for background and Vanadium standart.
      The rawdata is not changed only the I column.
    '''
    changed=False
    if not self.background_data is None:
      sys.stdout.write("background substractoin, ")
      sys.stdout.flush()
      self.process_funcion(self.correct_background)
      changed=True
    else:
      self.process_funcion(self.copy_intensities)
    if not self.vanadium_data is None:
      sys.stdout.write("vanadium correction, ")
      sys.stdout.flush()
      self.process_funcion(self.correct_vanadium)
      changed=True
    if changed:
      self.zdata=self.number_of_channels*2+5
      self.yerror=self.number_of_channels*3+5
  
  def copy_intensities(self, point):
    '''
      Just compy the raw intensity measured to another column.
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
      vn_indices=map(lambda detector: vn_lists[0].index(detector), point[4])
      # create a list of arrays with the corresponding intensities
      vn=array(map(lambda index: vn_lists[1][index], vn_indices))
      errvn=array(map(lambda index: vn_lists[2][index], vn_indices))
      for i in range(nc):
        point[i+2*nc+5]/=vn
        point[i+3*nc+5]=self.error_propagation_quotient([point[i+2*nc+5], point[i+3*nc+5]],[vn, errvn])
      return point
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
    #--------- calculations for use with single points -------------
  
  def error_propagation_quotient(self,xdata,ydata): 
    '''
      Calculate the propagated error for x/y.
    '''
    return sqrt((xdata[1]**2)/abs(ydata[0]) + abs(xdata[0])/(ydata[0]**2) * (ydata[1]**2))
  
