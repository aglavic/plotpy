#!/usr/bin/env python
'''
 Functions to plot measurements by gnuplot script or directly by gnuplot (faster).
 These functions are used by the GUI and script mode.
'''

# TODO: remove unnecessary parameters, include session parameters.

# Pleas do not make any changes here unless you know what you are doing.

import os
import subprocess
import globals
import gnuplot_preferences

def gnuplot_plot(session, 
                 datasets,
                 file_name_prefix, 
                 title,
                 names,
                 with_errorbars,
                 output_file=gnuplot_preferences.output_file_name,
                 additional_info='',
                 fit_lorentz=False,
                 add_preferences=''):
  '''
    Plotting with direct piping of the data to gnuplot, should work much faster
    Gnuplot.py must by installed and properly working.
    files are stored in temporary folder set in gnuplot_preferences
  '''
  gp=gnuplot_preferences # short form for gnuplot_preferences
  import Gnuplot
  sample_name=datasets[0].sample_name
  file_numbers=[dataset.number for dataset in datasets]
  if output_file.rsplit('.',1)[1]=='ps': # Determine which terminal to use depending on filename suffix
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
  if with_errorbars|fit_lorentz: # Design of plot changed when using errorbars
    plotting_param=str(gp.plotting_parameters_errorbars)
  else:
    plotting_param=str(gp.plotting_parameters)
  # replace place holders
  plotting_param=replace_ph(session, 
                            plotting_param,
                            datasets,
                            file_name_prefix,
                            file_numbers, 
                            title,
                            names,
                            sample_name,
                            0,
                            postscript_export,
                            additional_info) 
  gplot=Gnuplot.Gnuplot() # if term is x11 the plot will not close
  gnuplot_settings=gp.gnuplot_file_head+\
  'set term '+terminal+'\n'+\
  'set output "'+output_file+'"\n'+\
  'set encoding '+gp.encoding+'\n'+\
  'set xlabel "'+gp.x_label+'"\n'+\
  'set ylabel "'+gp.y_label+'"\n'+\
  'set title "'+gp.plot_title+'"\n'
  if len(datasets)==1: # if there is only one graph don't show a key
    gnuplot_settings+='unset key\n'
  if fit_lorentz: # setting functions and startingparameters for lorentz fitting
    for i,dataset in enumerate(datasets):
      gnuplot_settings=gnuplot_settings+\
            'f_'+str(i)+'(x)=I_'+str(i)+' * (abs(eta_'+str(i)+')/ ( 1 + ((x - x0_'+str(i)+\
            ')/sigma_'+str(i)+')**2) + abs(1-eta_'+str(i)+')*exp((-log(2))*((2*x-2*x0_'+str(i)+\
            ')/sigma_'+str(i)+')**2)) + BG_'+str(i)+'\n'+\
            'I_'+str(i)+'='+str(dataset.max()[1])+'\n'+\
            'x0_'+str(i)+'='+str(dataset.max()[0])+'\n'+\
            'sigma_'+str(i)+'='+str(abs(dataset.max()[0]-dataset.min()[0])/4)+'\n'+\
            'eta_'+str(i)+'=1\n'+\
            'BG_'+str(i)+'='+str(dataset.min()[1])+'\n'
  if datasets[0].zdata>=0: # plotting in 3D?
    gnuplot_settings=gnuplot_settings+'set view '+str(datasets[0].view_x)+','+str(datasets[0].view_z)+'\n'+\
            'set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
    if ((datasets[0].view_x%180)==0)&((datasets[0].view_z%90)==0):
      gnuplot_settings=gnuplot_settings+gp.settings_3dmap
    else:
      gnuplot_settings=gnuplot_settings+gp.settings_3d
    plotting_param=str(gp.plotting_parameters_3d)
  # replacing placeholders
  gnuplot_settings=replace_ph(session, 
                              gnuplot_settings+datasets[0].plot_options,
                              datasets,
                              file_name_prefix,
                              file_numbers, 
                              title,
                              names,
                              sample_name,
                              0,
                              postscript_export,
                              additional_info) 
  # Manually mimic the Gnuplot plot function to use multiple plots, which is not easyly possible otherwise.
  gplot(gnuplot_settings)
  if datasets[0].logx:
    gplot('set log x')
  else:
    gplot('unset log x')
  if datasets[0].logy:
    gplot('set log y')
  else:
    gplot('unset log y')
  if datasets[0].logz:
    gplot('set log z\nset log cb')
  else:
    gplot('unset log z\nunset log cb')
  if datasets[0].zdata>=0:
    gplot.plotcmd = 'splot'
  else:
    gplot.plotcmd = 'plot'
  gplot._clear_queue()
  for i,dataset in enumerate(datasets):
    if with_errorbars:
      datalist=dataset.list_err()
    else:
      datalist=dataset.list()
    if (dataset.zdata>=0): # for 3d-Data we have to create a temporal File
      dataset.export(globals.temp_dir+'tmp_data'+str(i)+'.out')
      plot=[Gnuplot.PlotItems.File(globals.temp_dir+'tmp_data'+str(i)+'.out',
                                   with_=str(plotting_param.replace('w ','',1)),
                                   title=names[datasets.index(dataset)],
                                   using=str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.zdata+1))]
    elif fit_lorentz: # for fitting a temporal File is needed, too
      dataset.export(globals.temp_dir+'tmp_data'+str(i)+'.out')
      plot=[Gnuplot.PlotItems.File(globals.temp_dir+'tmp_data'+str(i)+'.out',
                                   with_=str(plotting_param.replace('w ','',1)),
                                   title=names[datasets.index(dataset)],
                                   using=str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.yerror+1))]
      # start gnuplot fitting of one dataset
      gp('fit f_'+str(i)+'(x) "'+globals.temp_dir+'tmp_data'+str(i)+'.out" using '+\
          str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.yerror+1)+\
          ' via I_'+str(i)+','+'x0_'+str(i)+','+'sigma_'+str(i)+','+'BG_'+str(i)+',eta_'+str(i)+'\n')
      plot2=Gnuplot.PlotItems.Func('f_'+str(i)+'(x)',with_=str(gp.plotting_parameters_fit.replace('w ','',1)))
      function_title="'psd. Voigt fit: x0=\045.4g; FWHM=\045.3g; I=\045.0g; eta=\045.2g',x0_"+\
          str(i)+","+"abs(sigma_"+str(i)+"*2),"+"I_"+str(i)+","+"eta_"+str(i)
      plot2.set_string_option('title',function_title, 'notitle', 'title sprintf(\045s)')
      plot.append(plot2)
    else:
      plot=[Gnuplot.PlotItems.Data(datalist,
                                   with_=str(plotting_param.replace('w ','',1)),
                                   title=names[datasets.index(dataset)])]
    gplot._add_to_queue(plot)
  gplot.refresh()
  gplot.close()
  # read stdout and stderr from gnuplot
  output=(session.gnuplot_output[0].read(), session.gnuplot_output[1].read())
  return unicode(output[1]) # return the stderror

def gnuplot_plot_script(session,  
                        datasets,
                        file_name_prefix, 
                        file_name_postfix, 
                        title,
                        names,
                        with_errorbars,output_file=gnuplot_preferences.output_file_name,
                        additional_info='',
                        fit_lorentz=False,
                        add_preferences=''): 
  '''
      Function to plot with an additional data and gnuplot file and calling to the gnuplot program.
      Files are stored in temporary folder set in gnuplot_preferences.
  '''
  gp=gnuplot_preferences # short form for gnuplot_preferences
  for dataset in datasets:
    dataset.export(session.temp_dir+'tmp_data_'+dataset.number+'.out')
  sample_name=datasets[0].sample_name
  file_numbers=[dataset.number for dataset in datasets]
  if output_file.rsplit('.',1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
  script_name=session.temp_dir+replace_ph(session, 
                                          gp.gnuplot_file_name,
                                          datasets,
                                          file_name_prefix, 
                                          file_numbers, 
                                          title,
                                          names,
                                          sample_name,
                                          0,
                                          postscript_export,
                                          additional_info)
  gnuplot_file_text=create_plot_script(session, 
                                       datasets,
                                       file_name_prefix, 
                                       file_name_postfix, 
                                       title,
                                       names,
                                       with_errorbars,
                                       output_file,
                                       additional_info,
                                       fit_lorentz,
                                       add_preferences)
  write_file=open(script_name,'w')
  write_file.write( gnuplot_file_text+'\n' )
  write_file.close()
  proc = subprocess.Popen([session.gnuplot_command, script_name], 
                      shell=False, 
                      stderr=subprocess.PIPE,
                      stdout=subprocess.PIPE, 
                      )
  output = proc.communicate()
  return output[0]+output[1] # return the standard error output

def replace_ph(session, 
               string,
               datasets,
               file_name_prefix, 
               file_numbers, 
               title,
               names,
               sample_name,
               number,
               postscript_export=False,
               additional_info=''):
  '''
    Replace place holders in a string.
  '''
  gp=gnuplot_preferences
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
    string=gnuplot_preferences.postscript_replace(string)
  string=gp.further_replacement(string)
  string=session.replace_systemdependent(string)
  return string 
 
def create_plot_script(session, 
                       datasets,
                       file_name_prefix,
                       file_name_postfix, 
                       title,
                       names,
                       with_errorbars,
                       output_file=gnuplot_preferences.output_file_name,
                       additional_info='',
                       fit_lorentz=False,
                       add_preferences=''):
  '''
      function to create a script for the gnuplot program to read
  '''
  gp=gnuplot_preferences # define global gnuplot_preferences modul as local gp 
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
                    'set title "'+gp.plot_title+'"\n'
  if len(datasets)==1: # if there is only one graph don't show a key
    gnuplot_file_text+='unset key\n'
  gnuplot_file_text+=datasets[0].plot_options
  if fit_lorentz: # define pseudo Voigt Function to be fitted ( f=eta*f_lorentz+(a-eta)*f_gauss )
      for i,dataset in enumerate(datasets):
          gnuplot_file_text=gnuplot_file_text+\
            'f_'+str(i)+'(x)=I_'+str(i)+' * (abs(eta_'+str(i)+')/ ( 1 + ((x - x0_'+str(i)+\
            ')/sigma_'+str(i)+')**2) + abs(1-eta_'+str(i)+')*exp((-log(2))*((2*x-2*x0_'+str(i)+\
            ')/sigma_'+str(i)+')**2)) + BG_'+str(i)+'\n'+\
            'I_'+str(i)+'='+str(dataset.max()[1])+'\n'+\
            'x0_'+str(i)+'='+str(dataset.max()[0])+'\n'+\
            'sigma_'+str(i)+'='+str(abs(dataset.max()[0]-dataset.min()[0])/4)+'\n'+\
            'eta_'+str(i)+'=1\n'+\
            'BG_'+str(i)+'='+str(dataset.min()[1])+'\n'+\
            'fit f_'+str(i)+'(x) "'+file_name_prefix+'_'+file_numbers[i]+file_name_postfix+'" using '+\
            str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.yerror+1)+\
            ' via I_'+str(i)+','+'x0_'+str(i)+','+'sigma_'+str(i)+','+'BG_'+str(i)+',eta_'+str(i)+'\n'
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
          'plot "'+session.temp_dir+'tmp_data_'+datasets[0].number+'.out" u '+using_cols+' t "'+gp.titles+'" '+plotting_param
  gnuplot_file_text=replace_ph(session, 
                               gnuplot_file_text,
                               datasets,
                               file_name_prefix, 
                               file_numbers, 
                               title,
                               names,
                               sample_name,
                               0,
                               postscript_export,
                               additional_info)
  if fit_lorentz:
      gnuplot_file_text=gnuplot_file_text+',f_'+str(0)+'(x) '+gp.plotting_parameters_fit+\
          " title sprintf('psd. Voigt fit: x0=\045.4g; FWHM=\045.3g; I=\045.0g; eta=\045.2g',x0_"+\
          str(i)+","+"abs(sigma_"+str(i)+"*2),"+"I_"+str(i)+","+"eta_"+str(i)+')'
  for number in file_numbers[1:len(file_numbers)]:
      gnuplot_file_text=gnuplot_file_text+',\\\n"'+session.temp_dir+'tmp_data_'+number+\
          '.out" u '+using_cols+' t "'+gp.titles+'" '+plotting_param
      gnuplot_file_text=replace_ph(session, 
                                   gnuplot_file_text,
                                   datasets,
                                   file_name_prefix,
                                   file_numbers, 
                                   title,
                                   names,
                                   sample_name,
                                   file_numbers.index(number),
                                   postscript_export,
                                   additional_info)
      if fit_lorentz:
          gnuplot_file_text=gnuplot_file_text+',f_'+str(i)+'(x) '+\
              gp.plotting_parameters_fit+' title=\'x0=\045g; sigma=\045g; intensity=\045g; background=\045g\',x0_'+\
              str(i)+","+"sigma_"+str(i)+","+"I_"+str(i)+","+"BG_"+str(i)
  return gnuplot_file_text

 
class fit_function:
  '''
    Abstract class for gnuplot fitting with the above functions. 
    Creates fit function and parameters and collects fitted Data as well. 
    (in the future, still under development)
  '''
  # lists of all function parameters, their names and startup values, is set in __init__
  par_names=[]
  par_identifyer=[]
  par_start_values=[]
  # definition of the function to be fitted and the corresponding columns in the data file
  function=''
  data_columns=[]
  
  #+++++++++++++++++ constructor of the Class. ++++++++++++++++++++++++++++
  def __init__(self,parameters,function,columns): 
    '''
      Class constructor, creating the function for the fit.
    '''
    # parameters is a list of [name,identifyer,startvalue]
    #first check if the input is reasonable
    if (not ((len(columns)==3)&(type(columns) is list)))|\
        (not type(function) is str)|\
        (not self.test_columns(columns)):
      return None
    # initialise the class variables
    self.par_names=[param[0] for param in parameters]
    self.par_identifyer=[param[1] for param in parameters]
    self.par_start_values=[param[3] for param in parmeters]
    self.data_columns=columns
    self.function=self.test_function(function)
  #----------------- constructor of the Class. ----------------------------

  #++++++++++++++ help functions for the constructor+++++++++++++++++++++++
  def test_columns(self,columns): 
    '''
      Test if columns is a list of integers.
    '''
    if not type(columns) is list:
      return False
    for number in columns:
      if not type(number) is int:
        return False
    return True

  def test_function(self,function): 
    '''
      Test if the function only contains x, parameter identifyers or gnuplot functions.
    '''
    start_string=function
     # remove identifyers
    for ident in par_identifyer:
      function=function.replace(ident,'')
    # remove brackets
    function=function.replace('(','').\
    replace(')','').\
    replace('+','').\
    replace('-','').\
    replace('/','').\
    replace('*','').\
    replace('log','').\
    replace('exp','').\
    replace('abs','').\
    replace('asinh','').\
    replace('acosh','').\
    replace('asin','').\
    replace('acos','').\
    replace('sin','').\
    replace('cos','').\
    replace('atanh','').\
    replace('atan','').\
    replace('tan','').\
    replace('erf','').\
    replace('int','').\
    replace('norm','').\
    replace('rand','').\
    replace('sgn','').\
    replace('sqrt','').\
    replace('1','').replace('2','').replace('3','').replace('4','').replace('5','').replace('6','').\
    replace('7','').replace('8','').replace('9','').replace('0','')
    if function=='x': # if the function is set correct it should now only contain x
      return start_string
    else:
      return '1'
  #-------------- help functions for the constructor ----------------------

  #+++++++++++++ functions for gnuplot string creation ++++++++++++++++++++
  def get_function(self,i): 
    '''
      Return a string which defines the function in gnuplot.
    '''
    function_str='# Defining the function '+str(i)+'\n'
    function_str=function_str+'f_'+str(i)+'(x)='
    indexed_function=self.function
    for identifyer in self.par_identifyer: # add an index to every identifyer
      indexed_fundtion=indexed_function.replace(identifyer,identifyer+'_'+str(i))
    function_str=function_str+indexed_function+'\n'
    return function_str
  
  def get_params_start(self,i): 
    '''
      Retrun a string which defines the startup values in gnuplot.
    '''
    params_start='# Defining the startup values for function '+str(i)+'\n'
    for j,identifyer in enumerate(self.par_identifyer): # add an index to every identifyer and define start value
      params_start=params_start+identifyer+'_'+str(i)+'='+str(self.par_start_values[j])+'\n'
    return params_start
    
  def get_fit_string(self,i,file_name):
    '''
      Return the gnuplot call to fit the function.
    '''
    fit_string='# Fit the parameters of the function '+str(i)+'\n'
    fit_string=fit_string+'fit f_'+str(i)+'(x) "'+file_name+'" using '+str(self.columns[0])+':'+str(self.columns[1])+':'+str(self.columns[2])+' via '
    for identifyer in self.par_identifyer: # add an index to every identifyer for the via
      fit_string=fit_string+identifyer+'_'+str(i)
      if not identifyer==self.par_identifyer[-1]:
        fit_string=fit_string+','
      else:
        fit_string=fit_string+'\n'
    return fit_string


  #------------- functions for gnuplot string creation --------------------
