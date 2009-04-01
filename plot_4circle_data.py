#!/usr/bin/env python
#################################################################################################
#                     Script to plot 4Circle-measurements with gnuplot                          #
#                                       last changes:                                           #
#                                        01.04.2009                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Additional Files: measurement_data_structure.py - classes storing the measured data           #
#                   measurement_data_plotting.py - plotting functions                           #
#                   circle_read_data.py - functions for data extraction                         #
#                   gnuplot_preferences.py - settings for gnuplot output                        #
#                   gnuplot_preferences_4circle.py - additional settings only for this script   #
#                   plotting_gui.py - plotting in graphical user interface (pygtk dependency!)  #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert spec .spec files to .out space(and other)seperated text files, splitted by sequences #
# -plot every sequence as extra picture or in one graph                                         # 
#    (h,k,l,phi,th,chi scan/mesh found by const. columns)                                       #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -select columns to be plotted                                                                 #
# -convert to counts/s                                                                          #
# -send all files to printer after processing (linux commandline printing)                      #
# -plot meshes in 3d                                                                            #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
# -enhance graphical user interface with more options, test for bugs (beta state)               #
# -add command line parameter for lorentz fit                                                   #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.


# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import circle_read_data
import circle_preferences

'''
  Class to handle 4 circle data sessions
'''
class circle_session(generic_session):
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\t4 CIRCLE-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  show_counts=False
  #------------------ local variables -----------------

  
  '''
    class constructor expands the generic_session constructor
  '''
  def __init__(self, arguments):
    self.columns_mapping=circle_preferences.columns_mapping
    self.measurement_types=circle_preferences.measurement_types
    self.transformations=circle_preferences.transformations
    generic_session.__init__(self, arguments)
    
  
  '''
    additional command line arguments for squid sessions
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
    return circle_read_data.read_data(file_name,self.columns_mapping,self.measurement_types)
  
  '''
    create a specifig menu for the 4circle session
  '''
  def create_menu(self):
    # Create XML for squid menu
    string='''
      <menu action='4CircleMenu'>
      
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "4CircleMenu", None,                             # name, stock id
                "4 Circle", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions

  
'''
################### old code, that will be deleted after plot.py works propperly ##############

#How to use this script:
def short_help():
  return """\tUsage: plot_4circle_data.py [files] [options]
\tRun plot_4circle_data.py --help for more information.
"""

def help_statement():
  return """Script to plot 4Circle data of MvsT and MvsH measurements.
Usage: plot_4circle_data.py [files] [options]
\tOptions:
\t\t--help\t\tPrint this information

Data treatment:
\t\t-counts\t\tShow actual counts, not counts/s

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
\t\t-comb\t\tCombine the seqences of all files as if it would be in one file

Plott settings:
\t\t-sxy\t\tSelect other x-,y- and dy- columns to plot
\t\t-e\t\tPlot with errorbars
\t\t-logx\t\tLogarithmic x-axes
\t\t-logy\t\tLogarithmic y-axes
\t\t-gui\t\tShow graphs in plotting GUI (experimental, pygtk package needed)

The gnuplot graph parameters are set in the gnuplot_preferences.py file, if you want to change them.
Data columns and unit transformations are defined in circle_preferences.py."""

# defining globals
global input_file_names


# import from external files and standard python methods
import os
import sys
import math
from measurement_data_structure import *
from measurement_data_plotting import *
from circle_read_data import *
from circle_preferences import *
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
#if not ('Gnuplot' in sys.modules): # If Gnuplot.py is not installed do automatically change to script mode
#  gnuplot_script=True
#  print 'Gnuplot module not installed, switching to script mode!'
plot_data=True
plot_with_errorbars=False
plot_with_GUI=False
print_plot=False
column_seperator=' '
do_output=True
info_in_file=True
select_xy=False

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
    elif argument=='-sxy':
      select_xy=True
    elif argument=='-e':
      plot_with_errorbars=True
    elif argument=='-p':
      print_plot=True
    elif argument=='-comb':
      combine_files=True
    elif argument=='-gui':
      plot_with_GUI=True
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
        ['s','s2','i','gs','no','ni','c','sep','l','sxy','e','counts','gui','p','logx','logy','comb','debug'].index(argument[1:len(argument)])
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
  globals.debug_file.write('# debug fiele from plot_4circle_data.py PID='+globals.own_pid+'\n# temp-directory: '+globals.temp_dir+'\n')


if gnuplot_script:
  column_seperator=' '
#---------------------------Command-Line parameter processing--------------------------#


#+++++++++++++++++++++++++++++++++++++++FUNCTIONS++++++++++++++++++++++++++++++++++++++#
def counts_to_cps(input_data): # Function to make the diamagnetic correction on the dataset
  if globals.debug:
    globals.debug_file.write('call: counts_to_cps('+str(input_data)+')\n')
  output_data=input_data
  counts_column=[]
  seconds=3
  for i,unit in enumerate(units): 
# selection of the columns for H and M, only works with right columns_mapping settings in SQUID_preferences.py
    if unit=='counts':
      counts_column.append(i)
    if unit=='s':
      seconds=i
  for counts in counts_column:
    output_data[counts]=output_data[counts]/output_data[seconds] # calculate the linear correction
  return output_data
  
def select_new_xy(dataset): # command line selection of other columns to be plotted
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
    globals.debug_file.write('call: plot('+ str(datasets)+','+ str(file_name_prefix)+','+ str(title)+','+ str(names)+','+ str(with_errorbars)+','+')\n')
  if len(datasets)>1:
    add_info='multi_'
  else:
    add_info=''
  if gnuplot_script:
    output=gnuplot_plot_script(datasets,file_name_prefix, '.out', title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_4circle')
    return output
  else:
    return gnuplot_plot(datasets,file_name_prefix, title,names,with_errorbars,additional_info=add_info,add_preferences='gnuplot_preferences_4circle')

#---------------------------------------FUNCTIONS--------------------------------------#


#++++++++++++++++++++++++++++++++++++++MAIN SCRIPT+++++++++++++++++++++++++++++++++++++#
measurement=[]
for input_file_name in input_file_names: # process every file given in the command line (inc. wild cards)
  print 'Processing: '+input_file_name
  single_pictures=[]
  if combine_files:
    measurement=read_data(input_file_name,columns_mapping,measurement_types,measurement)
  else:
    measurement=read_data(input_file_name,columns_mapping,measurement_types) # read data from file
    if measurement=='NULL': # if there had been reading errors or wrong file types skip this file
      continue
  remove=[]
  if (not combine_files) | (input_file_names.index(input_file_name)==len(input_file_names)-1):
    for i,dataset in enumerate(measurement): # processing transformations,functions and selecting right measurements
      dataset.unit_trans(transformations) # transfrom data to right units
      if not show_counts:
        units=dataset.units()
        dataset.process_funcion(counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      if show_logx:
        dataset.logx=True
      if show_logy:
        dataset.logy=True
      dataset.number='000000'.replace('0','',6-len(str(len(measurement)+1))+len(str(i+1)))+str(i+1) # set number string depending on the length of the last number
      hkl=[str(round(dataset.data[0].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
      str(round(dataset.data[1].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
      str(round(dataset.data[2].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0')] # h,k,l information from middle of the Scan with 2 post point digits but with trailing 0 striped
      if (dataset.xdata==0)&(dataset.zdata==-1):
        dataset.short_info='h,'+hkl[1] +','+hkl[2] +' scan'  # set short info as the value of the constant column
      elif (dataset.xdata==1)&(dataset.zdata==-1):
        dataset.short_info=hkl[0] +',k,'+hkl[2] +' scan'  # set short info as the value of the constant column
      elif (dataset.xdata==2)&(dataset.zdata==-1):
        dataset.short_info=+hkl[0] +','+hkl[1] +',l scan'  # set short info as the value of the constant column
      elif dataset.zdata>=0:
        dataset.short_info=dataset.xdim()+dataset.ydim()+' mesh at '+hkl[0]+ ','+hkl[1]+ ','+ hkl[2]   # set short info as the value of the constant column
      else:
        dataset.short_info=dataset.xdim()+' scan at '+hkl[0] +','+ hkl[1]+ ','+hkl[2]   # set short info as the value of the constant column
      if list_all:
        print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),\
        dataset.short_info
      if ((i+1>=seq[0])&(i+1<=seq[1])&(((i+1-seq[0]) % inc) == 0)): # Sequence selected?
        if list_sequences:
          print dataset.number+':',dataset.ydim()+' vs '+dataset.xdim(),\
          dataset.short_info
        if do_output | gnuplot_script:
          dataset.export(input_file_name+'_'+dataset.number+'.out',info_in_file,column_seperator) # write data into files with sequence numbers      
      else:
        remove.append(dataset)
    for dataset in remove:
      measurement.remove(dataset)

    if not plot_with_GUI:
      plot_this_measurement()
    else:
      plotting_gui.ApplicationMainWindow(measurement,input_file_name,script=gnuplot_script,script_suf='.out',preferences_file='gnuplot_preferences_4circle')
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
