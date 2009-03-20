#!/usr/bin/env python
#
# Functions to plot measurements by gnuplot script or directly by gnuplot (much faster)
# Last Changes 17.12.2008
#
# To do:
# -clean up the code!
#
# Pleas do not make any changes here unless you know what you are doing.

import os
import subprocess
import globals
import gnuplot_preferences #            File containing variables:
#                                       gnuplot_file_head, gnuplot_file_name,
#                                       remove_from_name(),encoding,set_output_terminal
#                                       output_file_name,x_label,y_label,plot_title,plotting_parameters
#                                       plotting_parameters_errorbars,titles


def gnuplot_plot_script(datasets,file_name_prefix,file_name_postfix, title,names,with_errorbars,output_file=gnuplot_preferences.output_file_name,additional_info='',fit_lorentz=False,add_preferences=''): # # Plot with creating a temporal gnuplot skript and executing gnuplot afterwards. Should be much slower when processing many sequences. Mostly the same function as gnuplot_plot above.
  gp=gnuplot_preferences
  with_errorbars=True

#++++++++++++++ Parameters for the calibration calculation ++++++++++++++++#
  Pd_mass=0.26867 # mass of the used Pd sample
  Pd_Chi=5.25e-6 # Pd susceptibility (in emu/gauss/gramm)
  ini_file='../calibration/calibrat.ini'
  file_handler=open(ini_file,'r')
  line = file_handler.readline()
  old_factor=1.
  squid_long=False
  while (not line.split(']')[0]=='[Squid-Longitudinal'):
    line = file_handler.readline()
  while (not line.split('=')[0]== 'Sq_calibration_factor'):
    line = file_handler.readline()
  old_factor=float(line.split('=')[1])
  file_handler.close()
#-------------- Parameters for the calibration calculation ----------------#
  
  sample_Chi=Pd_Chi*Pd_mass
  
  if globals.debug:
    globals.debug_file.write('call: gnuplot_plot_script('+str(datasets)+','+str(file_name_prefix)+','+str(file_name_postfix)+  ','+  str(title)+ ','+ str(names)+','+ str(with_errorbars)+ ','+ str(output_file)+ ','+ str(additional_info)+ ','+ str(fit_lorentz)+ ','+ str(add_preferences)+')\n')
  sample_name=datasets[0].sample_name
  file_numbers=[dataset.number for dataset in datasets]
  if output_file.rsplit('.',1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
  if with_errorbars|fit_lorentz:
    plotting_param=gp.plotting_parameters_errorbars
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].yerror+1)
  else:
    plotting_param=gp.plotting_parameters
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)
  gnuplot_file_text=gp.gnuplot_file_head+\
  'set term '+terminal+'\n'+\
  'set output "'+output_file+'"\n'+\
  'set xlabel "'+gp.x_label+'"\n'+\
  'set ylabel "'+gp.y_label+'"\n'+\
  datasets[0].plot_options
  for i,dataset in enumerate(datasets):
    gnuplot_file_text+=\
    'f_'+str(i)+'(x)=a_'+str(i)+'*x + b_'+str(i)+'\n'+\
    'a_'+str(i)+'=1.\n'+\
    'b_'+str(i)+'=1e-9\n'+\
    'fit f_'+str(i)+'(x) "'+file_name_prefix+'_'+file_numbers[i]+file_name_postfix+'" using '+\
    str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.yerror+1)+\
    ' via a_'+str(i)+','+'b_'+str(i)+'\n'
  gnuplot_file_text+=\
    'set title sprintf("new calibration factor=\045.6g * \045.6g = \045.6g",'+str(old_factor)+',(a_0/'+str(sample_Chi)+'),'+str(old_factor)+'*(a_0/'+str(sample_Chi)+'))\n'
  if datasets[0].logx:
    gnuplot_file_text=gnuplot_file_text+'set log x\n'
  if datasets[0].logy:
    gnuplot_file_text=gnuplot_file_text+'set log y\n'
  if datasets[0].logz:
    gnuplot_file_text=gnuplot_file_text+'set log z\nset log cb\n'
  splot_add=''
  if datasets[0].zdata>=0:
    plotting_param=gp.plotting_parameters_3d
    gnuplot_file_text=gnuplot_file_text+'set view '+str(datasets[0].view_x)+','+str(datasets[0].view_z)+'\n'+\
    'set zlabel "'+z_label+'"\n'+'set cblabel "'+z_label+'"\n'+\
    settings_3d
    if ((datasets[0].view_x%180)==0)&((datasets[0].view_z%90)==0):
      gnuplot_file_text=gnuplot_file_text+settings_3dmap
    else:
      gnuplot_file_text=gnuplot_file_text+settings_3d
    splot_add='s'
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].zdata+1)
  gnuplot_file_text=gnuplot_file_text+\
  '# now the plotting function\n'+splot_add+\
  'set key inside\n'+\
  'plot "'+file_name_prefix+'_'+file_numbers[0]+file_name_postfix+'" u '+using_cols+" t '' "+ plotting_param+", f_0(x) w lines lw 2 t sprintf('linear fit with parameters: a=\045.6g; b=\045.2g;',a_0,b_0)" 
  gnuplot_file_text=replace_ph(gnuplot_file_text,datasets,file_name_prefix,file_numbers, title,names,sample_name,0,postscript_export,additional_info)
  for i,number in enumerate(file_numbers[1:len(file_numbers)]):
    gnuplot_file_text=gnuplot_file_text+',\\\n"'+file_name_prefix+'_'+number+file_name_postfix+'" u '+using_cols+" t '' "+plotting_param+", f_"+str(i+1)+"(x) w lines lw 2 t sprintf('linear fit with parameters: a=\045.6g; b=\045.2g;',a_"+ str(i+1)+","+"b_"+str(i+1)+') '
    gnuplot_file_text=replace_ph(gnuplot_file_text,datasets,file_name_prefix,file_numbers, title,names,sample_name,file_numbers.index(number),postscript_export,additional_info)
  script_name=globals.temp_dir+replace_ph(gp.gnuplot_file_name,datasets,file_name_prefix,file_numbers, title,names,sample_name,0,postscript_export,additional_info)
  if globals.debug:
    globals.debug_file.write('writing to script file: '+script_name+'\n')
  write_file=open(script_name,'w')
  write_file.write( gnuplot_file_text+'\n' )
  write_file.close()
  retcode = subprocess.call([globals.gnuplot_command, script_name]) # start gnuplot and wait for it to finish
  return gnuplot_file_text#replace_ph(output_file,datasets,file_name_prefix,file_numbers, title,names,sample_name,0,postscript_export,additional_info)

def replace_ph(string,datasets,file_name_prefix,file_numbers, title,names,sample_name,number,postscript_export=False,additional_info=''): # replace place holders in string
  gp=gnuplot_preferences
  if globals.debug:
    globals.debug_file.write('call: replace_ph('+ str(string)+ ',' + str(datasets)+ ','+ str(file_name_prefix)+ ','+ str(file_numbers)+ ','+ str(title)+ ','+ str(names)+ ','+ str(sample_name)+ ','+ str(number)+ ','+ str(postscript_export)+ ','+ str(additional_info)+')\n')
  string=string.\
  replace('[name]',file_name_prefix).\
  replace('[name-rmv]',gp.remove_from_name(file_name_prefix)).\
  replace('[sample]',sample_name).\
  replace('[nr]',file_numbers[number]).\
  replace('[add_info]',additional_info).\
  replace('[info]',datasets[number].info.replace('\n','\n#')).\
  replace('[x-unit]',datasets[number].xunit()).\
  replace('[x-dim]',datasets[number].xdim()).\
  replace('[y-unit]',datasets[number].yunit()).\
  replace('[y-dim]',datasets[number].ydim()).\
  replace('[z-unit]',datasets[number].zunit()).\
  replace('[z-dim]',datasets[number].zdim()).\
  replace('[title_add]',title).\
  replace('[titles_add]',names[number]).\
  replace('[const_unit]',datasets[number].units()[datasets[number].type()]).\
  replace('[const_dim]',datasets[number].dimensions()[datasets[number].type()]).\
  replace('[const_value]',str(datasets[number].last()[datasets[number].type()]))
# translations for postscript export (special characters other than in png export)
# should be enlongated with other characters
  if postscript_export: # see gnuplot_preferences.py for this function
    string=postscript_replace(string)
  string=gp.further_replacement(string)
  string=globals.replace_systemdependent(string)
  return string 
 