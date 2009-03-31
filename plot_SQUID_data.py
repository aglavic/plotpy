#!/usr/bin/env python
#################################################################################################
#                     Script to plot SQUID-measurements with gnuplot                            #
#                                       last changes:                                           #
#                                        22.03.2008                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Additional Files: measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   SQUID_read_data.py - functions for data extraction                          #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   gnuplot_preferences_SQID.py - additional settings only for this script      #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert SQUID .dat files to .out space(and other)seperated text files, splitted by sequences #
# -plot every sequence as extra picture or in one graph (MvsT or MvsH is found by const. H/T)   #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -select columns to be plotted                                                                 #
# -convert units to SI (or any selected)                                                        #
# -remove diamagnetic contribution (as constant and calculated from elements and mass)          #
# -process raw data files (sequence splitting see SQUID_preferences.py)                         #
# -send all files to printer after processing (linux commandline printing)                      #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
# -process raw data more user freindly than in SQUID (select point directly?)                   #
# -combine plots on one page or other graphical enhancements (ideas are welcome)                #
# -enhance graphical user interface with more options, test for bugs (beta state)               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import SQUID_read_data
import SQUID_preferences

'''
  Class to handle squid data sessions
'''
class squid_session(generic_session):
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
SQUID-Data treatment:
\t\t-para [C]\tInclude paramagnetic correction factor (C/T) [emu*K/Oe]
\t\t-dia [Chi]\tInclude diamagnetic correction in [10^-9 emu/Oe]
\t\t-dia-calc [e] [m]\tAdd diamagnetic correction of sample containing elements e
\t\t\t\t\t with complete mass m in mg. 
\t\t\t\t\t e is given for example as 'La_1-Fe_2-O_4','la_1-fe2+_2-o_4' or 'La-Fe_2-O_4'.
\t\t-no-trans\tdon't make a unit transformation
'''

  
  '''
    class constructor expands the generic_session constructor
  '''
  def __init__(self, arguments):
    self.columns_mapping=SQUID_preferences.columns_mapping
    self.measurement_types=SQUID_preferences.measurement_types
    generic_session.__init__(self, arguments)
    
  '''
    function to read data files
  '''
  def read_file(self, file_name):
    return SQUID_read_data.read_data(file_name,self.columns_mapping,self.measurement_types)
  
'''
################### old code, that will be deleted after plot.py works propperly ##############

#How to use this script:
def short_help():
    return """\tUsage: plot_SQUID_data.py [files] [options]
\tRun plot_SQUID_data.py --help for more information.
"""

def help_statement():
    return """Script to plot SQID data of MvsT and MvsH measurements.
Usage: plot_SQUID_data.py [files] [options]
\tOptions:
\t\t--help\t\tPrint this information

Data treatment:
\t\t-para [C]\tInclude paramagnetic correction factor (C/T) [emu*K/Oe]
\t\t-dia [Chi]\tInclude diamagnetic correction in [10^-9 emu/Oe]
\t\t-dia-calc [e] [m]\tAdd diamagnetic correction of sample containing elements e
\t\t\t\t\t with complete mass m in mg. 
\t\t\t\t\t e is given for example as 'La_1-Fe_2-O_4','la_1-fe2+_2-o_4' or 'La-Fe_2-O_4'.
\t\t-no-trans\tdon't make a unit transformation

Sequence settings:
\t\t-a\t\tPlot all sequences in one picture
\t\t-s [a] [b]\tOnly plot sequence a to b (standard is 1 to 10000)
\t\t-s2 [b]\t\tSet last sequence to be plotted
\t\t-i [inc]\tPlot only every inc sequence
\t\t-l\t\tList sequences in file.
\t\t-ls\t\tList selected Sequences.

Output settings:
\t\t-gs\t\tUse gnuplot in script mode, in the case Gnuplot.py is not working (slower)
\t\t-o\t\tOutput the data to .out files for later use in other programms.
\t\t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
\t\t-c\t\tJust convert files, do not plot anything
\t\t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
\t\t-p\t\tSend plots to printer specified in gnuplot_perferences.py

Plott settings:
\t\t-sc\t\tSelect columns different from SQUID_preferences.py settings
\t\t-st\t\tSelect measurement typs different from SQUID_preferences.py settings
\t\t-sxy\t\tSelect other x-,y- and dy- columns to plot
\t\t-e\t\tPlot with errorbars
\t\t-gui\t\tShow graphs in plotting GUI (experimental, pygtk package needed)

\t\t-calib-long\tCalibrate the longitudinal SQUID factor.

The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in SQUID_preferences.py."""

# defining globals
global input_file_names

# import from external files and standard python methods
import os
import sys
import math
from measurement_data_structure import *
import measurement_data_plotting
from SQUID_read_data import *
from SQUID_preferences import *
from gnuplot_preferences import print_command
import plotting_gui
import globals


# define some global variables
globals.own_pid=str(os.getpid())
globals.temp_dir=globals.temp_dir+'plottingscript-'+globals.own_pid+os.sep
globals.debug=False
input_file_names=[]
last_argument_option=[False,'']
dia_calc=[False,'',0]
para=0
seq=[1,10000]
inc=1
single_picture=False
list_sequences=False
list_all=False
gnuplot_script=False
plot_data=True
plot_with_errorbars=False
plot_with_GUI=False
print_plot=False
column_seperator=' '
do_output=False
info_in_file=True
select_columns=False
select_type=False
select_xy=False
unit_transformation=True
calib_long=False

#+++++++++++++++++++++++++++Command-Line parameter processing++++++++++++++++++++++++++#
if len(sys.argv)==1:
  print short_help()

for argument in sys.argv[1:len(sys.argv)]:
  if (argument[0]=='-')|last_argument_option[0]:
      # Cases of arguments:
    if last_argument_option[0]:
      if last_argument_option[1]=='dia':
	dia_mag_correct=float(argument)
	last_argument_option=[False,'']
      elif last_argument_option[1]=='dia-calc':
	dia_calc[0]=True
	dia_calc[1]=argument
	last_argument_option=[True,'dia-calc2']
      elif last_argument_option[1]=='dia-calc2':
	dia_calc[2]=float(argument)
	last_argument_option=[False,'']
      elif last_argument_option[1]=='para':
	para=float(argument)
	last_argument_option=[False,'']
      elif last_argument_option[1]=='s':
	seq=[int(argument),seq[1]]
	last_argument_option=[True,'s2']
      elif last_argument_option[1]=='s2':
	seq=[seq[0],int(argument)]
	last_argument_option=[False,'']
      elif last_argument_option[1]=='i':
	inc=int(argument)
	last_argument_option=[False,'']
      elif last_argument_option[1]=='sep':
	column_seperator=str(argument)
	last_argument_option=[False,'']
      else:
	input_file_names.append(argument)
	last_argument_option=[False,'']
    elif argument=='-a':
      single_picture=True
    elif argument=='-l':
      list_all=True
    elif argument=='-ls':
      list_sequences=True
    elif argument=='-gs':
      gnuplot_script=True
    elif argument=='-o':
      do_output=True
    elif argument=='-ni':
      info_in_file=False
    elif argument=='-c':
      plot_data=False
    elif argument=='-sc':
      select_columns=True
    elif argument=='-st':
      select_type=True
    elif argument=='-sxy':
      select_xy=True
    elif argument=='-e':
      plot_with_errorbars=True
    elif argument=='-p':
      print_plot=True
    elif argument=='-gui':
      plot_with_GUI=True
    elif argument=='-no-trans':
      unit_transformation=False
    elif argument=='-calib-long':
      calib_long=True
    elif argument=='-debug':
      globals.debug=True
    elif argument=='--help':
      print help_statement()
    else:
      try:
	['dia','para','s','s2','i','gs','o','ni','c','sep','l','sc','st','sxy','e','dia-calc','gui','p','cali_reg','debug'].index(argument[1:len(argument)])
      except ValueError:
	print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
      else:
	last_argument_option=[True,argument[1:len(argument)]]
  else:
    input_file_names.append(argument)

# creating temporal directory for this process
os.mkdir(globals.temp_dir)

if calib_long:
  import calib_long
  measurement_data_plotting.gnuplot_plot_script=calib_long.gnuplot_plot_script
  gnuplot_script=True
  unit_transformation=False
  print "Calibration for longitudinal SQUID factor started!"

if (not gnuplot_script):
  try:
    import Gnuplot
  except ImportError:
    print "Gnuplot.py not available, falling back to script mode!"
    gnuplot_script=True

if plot_with_GUI:
  try:
    import gtk
  except ImportError:
    print "You have to install pygtk to run gin GUI-mode, falling back to command-line mode!"
    plot_with_GUI=False


if globals.debug: # if debuging write importent info into debug.log
  globals.debug_file
  globals.debug_file=open('debug.log','w')
  globals.debug_file.write('# debug fiele from plot_SQUID_data.py PID='+globals.own_pid+'\n# temp-directory: '+globals.temp_dir+'\n')

if gnuplot_script:
  column_seperator=' '
#---------------------------Command-Line parameter processing--------------------------#


#+++++++++++++++++++++++++++++++++++++++FUNCTIONS++++++++++++++++++++++++++++++++++++++#
def diamagnetic_correction(input_data): # Function to make the diamagnetic correction on the dataset
  if globals.debug:
    globals.debug_file.write('call: diamagnetic_correction('+str(input_data)+')\n')
  output_data=input_data
  field=1
  mag=3
  for mapping in columns_mapping: 
# selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
    if mapping[2][0]=='H':
      field=mapping[1]
    if mapping[2][0]=='M_rso':
      mag=mapping[1]
    if mapping[2][0]=='M_ac':
      mag=mapping[1]
  output_data[mag]=output_data[mag]+output_data[field]*dia_mag_correct # calculate the linear correction
  return output_data

def paramagnetic_correction(input_data): # Function to make the paramagentic correction with the dataset
  if globals.debug:
    globals.debug_file.write('call: paramagnettic_correction('+str(input_data)+')\n')
  output_data=input_data
  field=1
  temp=2
  mag=3
  for mapping in columns_mapping: 
# selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
    if mapping[2][0]=='H':
      field=mapping[1]
    if mapping[2][0]=='M_rso':
      mag=mapping[1]
    if mapping[2][0]=='M_ac':
      mag=mapping[1]
    if mapping[2][0]=='T':
      temp=mapping[1]
  output_data[mag]=output_data[mag]-output_data[field]*para/output_data[temp] # calculate the paramagnetic correction
  return output_data

def select_new_columns(file_name): # command line input for selection of any column found in datafile
  if globals.debug:
    globals.debug_file.write('call: select_new_columns('+str(file_name)+')\n')
  print 'Columns: '
  cols=get_columns(file_name)
  for i,col in enumerate(cols):
    print i,col   # Print all columns
  selected='Selected:'
  max_map=0
  for mapping in columns_mapping:
    if mapping[0] in cols:
      selected=selected+'  '+str(mapping[1]+1)+'-'+mapping[0]
      max_map=max(max_map,mapping[1])
  print selected # Print relevant columns from SQUID_preferences.py file
  add_map=raw_input('Add(positive)/Remove(negativ) Column (enter for exit): ')
  if add_map=='':
    return False
  elif int(add_map)>0: # add column
    print cols[int(add_map)]
    dim=raw_input('Dimension: ')
    unit=raw_input('Unit: ')
    columns_mapping.append([cols[int(add_map)],max_map+1,[dim,unit]])
    return True
  elif int(add_map)<0: # remove column
    number=abs(int(add_map))-1
    for mapping in columns_mapping:
      if number==mapping[1]:
	if mapping[0] in cols:
	  remove=mapping
      elif number<mapping[1]:
	mapping[1]=mapping[1]-1
    columns_mapping.remove(remove)
    for ty in measurement_types:
      for ty_0 in ty[0]:
	if number<ty_0[0]:
	  ty_0[0]=ty_0[0]-1
      if number<ty[1]:
	ty[1]=ty[1]-1
      if number<ty[2]:
	ty[2]=ty[2]-1
      if number<ty[3]:
	ty[3]=ty[3]-1
    return True
  else:
    return False
  
def select_new_type(file_name): # command line input for measurement types
  if globals.debug:
    globals.debug_file.write('call: select_new_type('+str(file_name)+')\n')
  cols=get_columns(file_name)
  col_used=[]
  for mapping in columns_mapping:
    if mapping[0] in cols:
      col_used.append([mapping[1],mapping[0]])
  col_used.sort(lambda x, y: cmp(x[0], y[0]))
  for ty in measurement_types: # print all types
    const_str=''
    const_div=''
    for ty_i in ty[0]:
      const_str=const_str+'\t'+col_used[ty_i[0]][1]
      const_div=const_div+'\t\t'+str(ty_i[1])
    print 'Typ '+str(measurement_types.index(ty))+'\nConstants: '+const_str+'\nMax.diviation:'+const_div+\
    '\nX: '+col_used[ty[1]][1]+'\tY: '+col_used[ty[2]][1]+'\tdY: '+col_used[ty[3]][1]+'\nPlot options: '+ty[4]
  add_ty=raw_input('Remove type (Number),Add type (a),exit (enter): ')
  if add_ty=='':
    return False
  elif add_ty=='a':
    selected=''
    for mapping in columns_mapping:
      if mapping[0] in cols:
	selected=selected+'  '+str(mapping[1])+'-'+mapping[0]
    print selected
    const=[]
    const_col=raw_input('Add Constant column (enter to proceed): ')
    while not const_col=='':
      const_div=raw_input('Max. diviation: ')
      const.append([int(const_col),float(const_div)])
      const_col=raw_input('Constant column: ')
    x=int(raw_input('X column: '))
    y=int(raw_input('Y column: '))
    dy=int(raw_input('delta Y column: '))
    plot_opt=raw_input('Additional plot options: ')
    measurement_types.append([const,x,y,dy,plot_opt]) # add new type
    return True
  elif int(add_ty)>=0:
    del measurement_types[int(add_ty)]
    return True
  else:
    return False

def select_new_xy(dataset): # command line selection of other columns to be plotted
  if globals.debug:
    globals.debug_file.write('call: select_new_xy('+str(dataset)+')\n')
  print 'Columns:\n'
  dim=''
  for i,col in enumerate(dataset.dimensions()):
    dim=dim+'\t'+str(i)+'-'+col
  print dim
  print 'Selected:\tx: '+str(dataset.xdata)+'\ty: '+str(dataset.ydata)+'\tdy: '+str(dataset.yerror)
  x_new=raw_input('New x column: ')
  if not x_new=='':
    y_new=raw_input('New y column: ')
    dy_new=raw_input('New dy column: ')
    dataset.xdata=int(x_new)
    dataset.ydata=int(y_new)
    dataset.yerror=int(dy_new)
    return True
  return False

def calc_dia_elements(input_string): 
  # Returns the diamagnetic moment and mass of one mol of the elements in input_string
  if globals.debug:
    globals.debug_file.write('call: calc_dia_elements('+str(input_string)+')\n')
  input_string=input_string.lower()
  from diamagnetism_table import element_dia # read table from file
  mol_mass=0
  mol_dia=0
  split_elements=input_string.split('-')
  elements=[]
  counts=[]
  for string in split_elements:
    elements.append(string.split('_')[0])
    if len(string.split('_'))>1:
      counts.append(int(string.split('_')[1]))
    else:
      counts.append(1)
  for dia in element_dia:
    if dia[0].lower() in elements:
      mol_mass=mol_mass+dia[1]*counts[elements.index(dia[0].lower())]
      mol_dia=mol_dia+dia[2]*counts[elements.index(dia[0].lower())]
      counts.pop(elements.index(dia[0].lower()))
      elements.remove(dia[0].lower())
  if len(elements)==0: # check if all elements have been found in table
    return [True,mol_mass,mol_dia]
  else:
    return [False,elements]

def plot_this_measurement(): # does the plotting of one files sequences
  if globals.debug:
    globals.debug_file.write('call: plot_this_measurement()\n')
  if print_plot:
    print_queue=[]
  if single_picture:
    single_pictures.append([[],measurement[0].type()])
  for dataset in measurement: # process every sequence in the measurement
    if select_xy:
      select_new_xy(dataset)
    if single_picture: # if the "plot all in one" option is enabled put all measurements of one type together
      if dataset.type()==single_pictures[-1][1]:
	single_pictures[-1][0].append(dataset)
      else:
	single_pictures.append([[dataset],dataset.type()])
    elif plot_data:
      actual_output=plot([dataset],input_file_name,dataset.short_info,[''],plot_with_errorbars)
      if print_plot:
	print_queue.append(actual_output) # append every plot to the queue schaduled for printing

  if plot_data:
    for picture in single_pictures:
      actual_output=plot(picture[0], input_file_name, '',[dataset.short_info for dataset in picture[0]],plot_with_errorbars)
      if print_plot:
	print_queue.append(actual_output) # append every plot to the queue schaduled for printing
  if print_plot:
    print_command_string=print_command
    for plot_file in print_queue:
      print_command_string=print_command_string+' '+plot_file
    os.popen2(print_command_string) # print the queue
    
def plot(datasets,file_name_prefix, title,names,with_errorbars): # plot direct or via script
  if globals.debug:
    globals.debug_file.write('call: plot('+str(datasets)+','+str(file_name_prefix)+','+str(title)+','+str(names)+','+str(with_errorbars)+')\n')
  if len(datasets)>1:
    add_info='multi_'
  else:
    add_info=''
  if gnuplot_script:
    output=measurement_data_plotting.gnuplot_plot_script(datasets,file_name_prefix, '.out', title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_SQUID')
    return output
  else:
    return measurement_data_plotting.gnuplot_plot(datasets,file_name_prefix, title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_SQUID')

#---------------------------------------FUNCTIONS--------------------------------------#


#++++++++++++++++++++++++++++++++++++++MAIN SCRIPT+++++++++++++++++++++++++++++++++++++#
if dia_calc[0]: # calculate diamagnetic correction from element table
  dia_mass_mol=calc_dia_elements(dia_calc[1])
  if dia_mass_mol[0]:
    dia_mag_correct=dia_mag_correct+dia_calc[2]/dia_mass_mol[1]*dia_mass_mol[2]
    print 'Applying diamagnetic correction of '+str(dia_mag_correct)
  else:
    print str(dia_mass_mol[1])+' not in list.'
dia_mag_correct=dia_mag_correct/1e8
para=para/1e8
for input_file_name in input_file_names: # process every file given in the command line (inc. wild cards)
  print 'Processing: '+input_file_name
  if globals.debug:
    globals.debug_file.write('Processing: '+input_file_name+'\n')
  if select_columns: # start select columns dialog until it exits with False
    while select_new_columns(input_file_name):
      continue
  if select_type: # start select type dialog until it exits with False
    while select_new_type(input_file_name):
      continue
  single_pictures=[]
  measurement=read_data(input_file_name,columns_mapping,measurement_types) # read data from file
  if measurement=='NULL': # if there had been reading errors or wrong file types skip this file
    continue
  else:
    remove=[]
    for i,dataset in enumerate(measurement): # processing transformations,functions and selecting right measurements
      dataset.number='000000'.replace('0','',6-len(str(len(measurement)+1))+len(str(i+1)))+str(i+1) # set number string depending on the length of the last number
      if unit_transformation: # Calculate a new SQUID longitudinal regression Factor
	dataset.unit_trans(transformations) # transfrom data to right units
	dataset.process_funcion(diamagnetic_correction) # make diamagnetic corrections
	dataset.process_funcion(paramagnetic_correction) # make paramagnetic corrections
      constant_type=dataset.unit_trans_one(dataset.type(),transformations_const)	
      dataset.short_info='at %d ' % constant_type[0]+constant_type[1] # set short info as the value of the constant column
      if list_all:
	print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),'at %d ' % constant_type[0]+constant_type[1],\
	'after %d' % (dataset.data[0].values[0]- measurement[0].data[0].values[0]) +dataset.data[0].unit
      if ((i+1>=seq[0])&(i+1<=seq[1])&(((i+1-seq[0]) % inc) == 0)): # Sequence selected?
	if list_sequences:
	  print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),'at %d ' % constant_type[0]+constant_type[1],\
	  'after %d' % (dataset.data[0].values[0]- measurement[0].data[0].values[0]) +dataset.data[0].unit
	if do_output:
	  dataset.export(input_file_name+'_'+dataset.number+'.out',info_in_file,column_seperator) # write data into files with sequence numbers      
      else:
	remove.append(dataset)
    for dataset in remove:
      measurement.remove(dataset)

    if not plot_with_GUI:
      plot_this_measurement()
    else:
      test_plugin=gtk.Label()
      #test_plugin.set_markup(' Test: ')
      plotting_gui.ApplicationMainWindow(measurement,input_file_name,script=gnuplot_script,script_suf='.out',preferences_file='gnuplot_preferences_SQUID',plugin_widget=test_plugin)
      gtk.main()

#--------------------------------------MAIN SCRIPT--------------------------------------#
if globals.debug:
  globals.debug_file.write('#exit program.\n')
  globals.debug_file.close()
else:
  for file_name in os.listdir(globals.temp_dir):
    os.remove(globals.temp_dir+file_name)
  os.rmdir(globals.temp_dir)
'''
