#!/usr/bin/env python
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                       last changes:                                           #
#                                        01.04.2009                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Additional Files: measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   reflectometer_read_data.py - functions for data extraction                  #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   gnuplot_preferences_reflectometer.py - additional settings only for this s. #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                   scattering_length_tables.py - scattering length for fit .ent files          #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert uxd files to .out space(and other)seperated text files, splitted by sequences        #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -send all files to printer after processing (linux commandline printing)                      #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
# -enhance graphical user interface with more options, test for bugs (beta state)               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import reflectometer_read_data
import reflectometer_preferences

'''
  Class to handle reflectometer data sessions
'''
class reflectometer_session(generic_session):
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
Reflectometer-Data treatment:
\t\t-counts\t\tShow actual counts, not counts/s
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  show_counts=False
  #------------------ local variables -----------------

  
  '''
    class constructor expands the generic_session constructor
  '''
  def __init__(self, arguments):
    self.data_columns=reflectometer_preferences.data_columns
    generic_session.__init__(self, arguments)
    
  
  '''
    additional command line arguments for reflectometer sessions
  '''
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        found=False
      elif argument=='-counts':
        show_counts=True
      else:
        found=False
    return (found, last_argument_option)


  '''
    function to read data files
  '''
  def read_file(self, file_name):
    return reflectometer_read_data.read_data(file_name,self.data_columns)
  
  '''
    create a specifig menu for the Reflectometer session
  '''
  def create_menu(self):
    # Create XML for squid menu
    string='''
      <menu action='ReflectometerMenu'>
      
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "ReflectometerMenu", None,                             # name, stock id
                "Reflectometer", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions

  
'''
################### old code, that will be deleted after plot.py works propperly ##############

#How to use this script:
def short_help():
  return """\tUsage: plot_reflectometer_data.py [files] [options]
\tRun plot_reflectometer_data.py --help for more information.
"""

def help_statement():
  return """Script to plot reflectometer measurements.
Usage: plot_reflectometer_data.py [files] [options]
\tOptions:
\t\t--help\t\tPrint this information

Data treatment:
\t\t-counts\tShow actual counts, not counts/s

Sequence settings:
\t\t-a\t\tPlot all sequences in one picture
\t\t-s [a] [b]\tOnly plot sequence a to b (standard is 1 to 10000)
\t\t-s2 [b]\t\tSet last sequence to be plotted
\t\t-i [inc]\tPlot only every inc sequence
\t\t-l\t\tList sequences in file.
\t\t-ls\t\tList selected Sequences.

Output settings:
\t\t-gs\t\tUse gnuplot in script mode, in the case Gnuplot.py is not working (slower)
\t\t-no\t\tDon't output the data to .out files. Does only work without -gs option. (faster for multiple files/sequences)
\t\t-ni\t\tDon't put informational header in output files. (can be helpful for usage with other programs)
\t\t-c\t\tJust convert files, do not plot anything
\t\t-sep [sep]\tUse different seperator for output files (if -gs is given it is ignored)
\t\t-p\t\tSend plots to printer specified in gnuplot_perferences.py
\t\t-fit [layers] [thicknesses] [est._roughness]
\t\t\t\t\tExport measurements for use with fit programm by Emmanuel Kentzinger and create .ent file for it.
\t\t\t\t\tlayers is a list of layers with format L1-L2-L3-S or 5[L1_L2]-S, where L,S are the names
\t\t\t\t\tof the compounds of the layers and substrate as provided in scattering_length_table.py
\t\t\t\t\tthicknesses is a list of layer thicknesses with format LT1-LT2-LT3 or [LT1_LT2] in A
\t\t\t\t\test._roughness is the estimated overall roughness to begin with
\t\t-ref\t\tTry to refine the scaling factor, background and roughnesses.

\t\t-comb\t\tCombine the seqences of all files as if it would be in one file

Plott settings:
\t\t-e\t\tPlot with errorbars
\t\t-logx\t\tLogarithmic x-axes
\t\t-logy\t\tLogarithmic y-axes
\t\t-gui\t\tShow graphs in plotting GUI (experimental, pygtk package needed)

The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in reflectometer_preferences.py."""

# defining globals
global input_file_names


# import from external files and standard python methods
import os
import sys
import math
from measurement_data_structure import *
from measurement_data_plotting import *
from reflectometer_read_data import *
from reflectometer_preferences import *
from gnuplot_preferences import print_command
import plotting_gui
import globals


# define some global variables
globals.own_pid=str(os.getpid())
globals.temp_dir=globals.temp_dir+'plottingscript-'+globals.own_pid+'/'
globals.debug=False
input_file_names=[]
combine_files=False
last_argument_option=[False,'']
show_counts=False
show_logx=False
show_logy=False
seq=[1,10000]
inc=1
single_picture=False
list_sequences=False
list_all=False
gnuplot_script=False
#if not 'Gnuplot' in sys.modules: # If Gnuplot.py is not installed do automatically change to script mode
#  gnuplot_script=True
#  print 'Gnuplot module not installed, switching to script mode!'
plot_data=True
plot_with_errorbars=False
plot_with_GUI=False
export_for_fit=False
try_refine=False
print_plot=False
column_seperator=' '
do_output=True
info_in_file=True

#+++++++++++++++++++++++++++Command-Line parameter processing++++++++++++++++++++++++++#
if len(sys.argv)==1:
  print short_help()

for argument in sys.argv[1:len(sys.argv)]:
  if (argument[0]=='-')|last_argument_option[0]:
      # Cases of arguments:
    if last_argument_option[0]:
      if last_argument_option[1]=='s':
        seq=[int(argument),seq[1]]
        last_argument_option=[True,'s2']
      elif last_argument_option[1]=='s2':
        seq=[seq[0],int(argument)]
        last_argument_option=[False,'']
      elif last_argument_option[1]=='fit':
        export_for_fit=True
        fit_layers=argument
        last_argument_option=[True,'fit2']
      elif last_argument_option[1]=='fit2':
        fit_thicknesses=argument
        last_argument_option=[True,'fit3']
      elif last_argument_option[1]=='fit3':
        fit_est_roughness=float(argument)
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
    elif argument=='-no':
      do_output=False
    elif argument=='-ni':
      info_in_file=False
    elif argument=='-c':
      plot_data=False
    elif argument=='-e':
      plot_with_errorbars=True
    elif argument=='-p':
      print_plot=True
    elif argument=='-gui':
      plot_with_GUI=True
    elif argument=='-comb':
      combine_files=True
    elif argument=='-ref':
      try_refine=True
    elif argument=='-counts':
      show_counts=True
    elif argument=='-logx':
      show_logx=True
    elif argument=='-logy':
      show_logy=True
    elif argument=='-debug':
      globals.debug=True
    elif argument=='--help':
      print help_statement()
    else:
      try:
        ['s','s2','i','gs','no','ni','c','sep','l','e','counts','gui','p','logx','logy','comb','fit','ref','debug'].index(argument[1:len(argument)])
      except ValueError:
        print 'No such option: '+argument+'!\nTry "--help" for usage information!\n'
      else:
        last_argument_option=[True,argument[1:len(argument)]]
  else:
    input_file_names.append(argument)

# creating temporal directory for this process
os.mkdir(globals.temp_dir)

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

if globals.debug:
  globals.debug_file=open('debug.log','w')
  globals.debug_file.write('#debug fiele from plot_4circle_data.py\n')
  globals.debug_file.write('# debug fiele from plot_reflectometer_data.py PID='+globals.own_pid+'\n# temp-directory: '+globals.temp_dir+'\n')

if gnuplot_script:
  column_seperator=' '
#---------------------------Command-Line parameter processing--------------------------#


#+++++++++++++++++++++++++++++++++++++++FUNCTIONS++++++++++++++++++++++++++++++++++++++#
def counts_to_cps(input_data): # Function to make the diamagnetic correction on the dataset
  if globals.debug:
    globals.debug_file.write('call: counts_to_cps('+ str(input_data)+')\n')
  output_data=input_data
  counts_column=[]
  for i,unit in enumerate(units): 
# selection of the columns for H and M, only works with right data_columns settings in reflectometer_preferences.py
    if unit=='counts':
      counts_column.append(i)
  for counts in counts_column:
    output_data[counts]=output_data[counts]/time_col # calculate the linear correction
  return output_data

def create_ent_file(array,points,ent_file_name,\
  back_ground=0,resolution=3.5,scaling_factor=10,theta_max=2.3,fit=0,fit_params=[1,2],constrains=[]\
  ): # creates an entrance file for fit.f90 script
  from scattering_length_table import scattering_length_densities
  ent_file=open(ent_file_name,'w')
  ent_file.write('8048.0\tscattering radiaion energy (Cu-Ka)\n'+\
    str(points)+'\tnumber of datapoints\n'+\
    '\n'+str(len(array))+'\tnumber of interfaces (number of layers + 1)\n'+\
    '#### Begin of layers, first layer:')
  i=1
  for j,layer in enumerate(array):
    try:
      SL=scattering_length_densities[layer[0]]
    except KeyError:
      print layer[0]+' not found in database. Please edit scattering_length_table.py'
      SL=[10,1]
      ent_file.write(' Not in Table')
    ent_file.write(' '+str(j)+': '+layer[0]+'\n')
    if not layer[1]==None:
      ent_file.write(str(layer[1])+'\tlayer thickness (in A)\t\t\tparameter '+str(i)+'\n')
      i=i+1
    ent_file.write(str(SL[0])+'\tdelta *1e6\t\t\t\tparameter '+str(i)+'\n')
    i=i+1
    ent_file.write(str(SL[1])+'\tdelta/beta\t\t\t\tparameter '+str(i)+'\n')
    i=i+1
    ent_file.write(str(layer[2])+'\tlayer roughness (in A)\t\t\tparameter '+str(i)+'\n')
    i=i+1
    ent_file.write('#')
  ent_file.write('### End of layers.\n'+\
    str(round(back_ground,4))+'\tbackground\t\t\t\tparametar '+str(i)+'\n')
  i=i+1
  ent_file.write(str(resolution)+'\tresolution in q (sigma, in 1e-3 A^-1)\tparameter '+str(i)+'\n')
  i=i+1
  ent_file.write(str(round(scaling_factor,4))+'\tscaling factor *1e-6\t\t\tparameter '+str(i)+'\n')
  ent_file.write('\n'+str(theta_max)+'\ttheta_max (in deg) for recalibration\n\n'+\
    str(fit)+'\t1: fit; 0: simulation\n\n')
  ent_file.write(str(len(fit_params))+'\t\tNumber of parameters to be fitted\n'+str(fit_params).strip('[').strip(']').replace(',',' ')+'\t\tindices of parameters\n'+str(len(constrains))+'\t\tnumber of constrains\n')
  for constrain in constrains:
    ent_file.write(str(len(constrain))+'\t\tnumber of parameters to be kept equal\n'+\
    str(constrain).strip('[').strip(']').replace(',',' ')+'\t\tindices of those parameters\n')
  ent_file.close()

def find_total_reflection(dataset): # find angle of total reflection from decay to 1/3 of maximum
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

def read_fit_file(file_name,parameters): # load results of fit file
  result={}
  fit_file=open(file_name,'r')
  test_fit=fit_file.readlines()
  fit_file.close()
  for i,line in enumerate(reversed(test_fit)):
    split=line.split()
    if len(split)>0:
      if split[0] in parameters:
        result[split[0]]=float(split[1])
    if len(parameters)==len(result):
        return result
  return None

def refine_scaling(layers,SF,BG,constrain_array): # refine the scaling factor within the region of total reflection
  data_lines=dataset.export('/var/tmp/fit_temp.res',False,' ',xfrom=0.005,xto=find_total_reflection(dataset))
  create_ent_file(layers,data_lines,'/var/tmp/fit_temp.ent',back_ground=BG,scaling_factor=SF,\
    constrains=constrain_array,fit=1,fit_params=[len(layers)*4+2])
  retcode = subprocess.call(['fit-script', '/var/tmp/fit_temp.res', '/var/tmp/fit_temp.ent', '/var/tmp/fit_temp','20'])
  scaling_factor=read_fit_file('/var/tmp/fit_temp.ref',[str(len(layers)*4+2)])[str(len(layers)*4+2)]
  return scaling_factor

def refine_roughnesses(layers,SF,BG,constrain_array): # refine the roughnesses and background after the angle of total reflection
  fit_p=[i*4+4 for i in range(len(layers))]
  fit_p.append(len(layers)*4-1)
  fit_p.sort()
  data_lines=dataset.export('/var/tmp/fit_temp.res',False,' ',xfrom=find_total_reflection(dataset))
  create_ent_file(layers,data_lines,'/var/tmp/fit_temp.ent',back_ground=BG,scaling_factor=SF,\
    constrains=constrain_array,fit=1,fit_params=fit_p)
  retcode = subprocess.call(['fit-script', '/var/tmp/fit_temp.res', '/var/tmp/fit_temp.ent', '/var/tmp/fit_temp','50'])
  fit_p=map(str,fit_p)
  parameters=read_fit_file('/var/tmp/fit_temp.ref',fit_p)
  for i,layer in enumerate(layers):
    if i<len(layers)-1:
      layer[2]=abs(parameters[str(i*4+4)])
    else:
      layer[2]=abs(parameters[str(i*4+3)])
  BG=parameters[str(len(layers)*4)]
  return [layers,BG]

def export_fit(dataset): # Function to export data for fitting with fit.f90 program
  fit_thick=fit_thicknesses
  if globals.debug:
    globals.debug_file.write('call: export_for_fit()\n')
  # create array of layers
  first_split=fit_layers.split('-')
  layer_array=[]
  constrain_array=[]
  layer_index=1
  for compound in first_split:
    if compound[-1]==']': # is there a multilayer
      count=int(compound.split('[')[0])
      second_split=compound.split('[')[1].rstrip(']').split('_')
      second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
      for j in range(len(second_split)):
        constrain_array.append([])
        for i in range(count): # repeat every layer in multilayer
            for j,multi_compound in enumerate(second_split):
                constrain_array[-1-j].append((layer_index-1)*4+1) # every layer of same kind will have the same height
                layer_array.append([multi_compound,float(second_thick[j]),fit_est_roughness])
                layer_index=layer_index+1
    else: # no multilayer
        if len(fit_thick)>0:
            layer_array.append([compound,float(fit_thick.split('-')[0]),fit_est_roughness])
        else:
            layer_array.append([compound,None,fit_est_roughness])
        layer_index=layer_index+1
    if len(fit_thick.split('-'))>1: # remove first thickness
        fit_thick=fit_thick.split('-',1)[1]
    else:
        fit_thick=''
  dataset.unit_trans([['Theta','\\302\\260',4*math.pi/1.54/180*math.pi,0,'q','A^{-1}'],['2 Theta','\\302\\260',2*math.pi/1.54/180*math.pi,0,'q','A^{-1}']])
  data_lines=dataset.export(input_file_name+'_'+dataset.number+'.res',False,' ') # write data into files with sequence numbers in format ok for fit.f90    
  scaling_fac=(dataset.max(xstart=0.005)[1]/1e5)
  back_gr=dataset.min()[1]
  if try_refine: # Try to refine the scaling factorn, background and roughnesses
    scaling_fac=refine_scaling(layer_array,scaling_fac,back_gr,constrain_array)
    result=refine_roughnesses(layer_array,scaling_fac,back_gr,constrain_array)
    layer_array=result[0]
    back_gr=result[1]
  # create final input file and make a simulation
  create_ent_file(layer_array,data_lines,input_file_name+'_'+dataset.number+'.ent',back_ground=back_gr,\
    scaling_factor=scaling_fac,constrains=constrain_array)
  retcode = subprocess.call(['fit-script', input_file_name+'_'+dataset.number+'.res',\
    input_file_name+'_'+dataset.number+'.ent', input_file_name+'_'+dataset.number])
  
def plot_this_measurement(): # does the plotting of one files sequences
  if globals.debug:
    globals.debug_file.write('call: plot_this_measurement()\n')
  if print_plot:
    print_queue=[]
  if single_picture:
    single_pictures.append([[],measurement[0].type()])
  for dataset in measurement: # process every sequence in the measurement
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
    globals.debug_file.write('call: plot('+ str(datasets)+ ','+ str(file_name_prefix)+ ','+ str(title)+ ','+ str(names)+ ','+ str(with_errorbars)+ ')\n')
  if len(datasets)>1:
    add_info='multi_'
  else:
    add_info=''
  if gnuplot_script:
    output=gnuplot_plot_script(datasets,file_name_prefix, '.out', title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_reflectometer')
    return output
  else:
    return gnuplot_plot(datasets,file_name_prefix, title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_reflectometer')

#---------------------------------------FUNCTIONS--------------------------------------#


#++++++++++++++++++++++++++++++++++++++MAIN SCRIPT+++++++++++++++++++++++++++++++++++++#
measurement=[]
refinements=[]
for input_file_name in input_file_names: # process every file given in the command line (inc. wild cards)
  print 'Processing: '+input_file_name
  single_pictures=[]
  if combine_files:
    measurement=read_data(input_file_name,data_columns,measurement)
  else:
    measurement=read_data(input_file_name,data_columns,[]) # read data from file
    if measurement=='NULL': # if there had been reading errors or wrong file types skip this file
      continue
  remove=[]
  if (not combine_files) | (input_file_names.index(input_file_name)==len(input_file_names)-1):
    for i,dataset in enumerate(measurement): # processing transformations,functions and selecting right measurements
      dataset.unit_trans(transformations) # transfrom data to right units
      time_col=1
      th=0
      twoth=0
      phi=0       
      for line in dataset.info.splitlines():
        strip=line.split('=')
        if strip[0]=='STEPTIME':
          time_col=float(strip[1])
        if strip[0]=='THETA':
          th=float(strip[1])
        if strip[0]=='2THETA':
          twoth=float(strip[1])
        if strip[0]=='PHI':
          phi=float(strip[1])
      if not show_counts:
        units=dataset.units()
        dataset.process_funcion(counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      if show_logx:
        dataset.logx=True
      if show_logy:
        dataset.logy=True
      dataset.number='000000'.replace('0','',6-len(str(len(measurement)+1))+len(str(i+1)))+str(i+1) # set number string depending on the length of the last number
      dataset.short_info=' started at Th='+str(round(th,4))+' 2Th='+str(round(twoth,4))+' Phi='+str(round(phi,4))
      if list_all:
        print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),\
        dataset.short_info
      if ((i+1>=seq[0])&(i+1<=seq[1])&(((i+1-seq[0]) % inc) == 0)): # Sequence selected?
        if list_sequences:
          print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),\
          dataset.short_info
        if do_output | gnuplot_script:
          dataset.export(input_file_name+'_'+dataset.number+'.out',info_in_file,column_seperator) # write data into files with sequence numbers      
        if export_for_fit: # export fit files
          export_fit(dataset)
          simu=read_simulation(input_file_name+'_'+dataset.number+'.sim')
          simu.number='1'+dataset.number
          simu.short_info='simulation'
          refinements.append(simu)
      else:
        remove.append(dataset)
    for dataset in remove:
      measurement.remove(dataset)
    for dataset in refinements:
      measurement.append(dataset)

    if not plot_with_GUI:
      plot_this_measurement()
    else:
      plotting_gui.ApplicationMainWindow(measurement,input_file_name,script=gnuplot_script,script_suf='.out',preferences_file='gnuplot_preferences_reflectometer')
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
