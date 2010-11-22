# -*- encoding: utf-8 -*-
'''
 Functions to plot measurements by gnuplot script or directly by gnuplot (faster).
 These functions are used by the GUI and script mode.
'''

# TODO: remove unnecessary parameters, include session parameters.

# Pleas do not make any changes here unless you know what you are doing.

import os
import sys
exit=sys.exit
import subprocess
from config import gnuplot_preferences

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.6.3.2"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

persistene_plots=0

def gnuplot_plot(session, 
                 datasets,
                 file_name_prefix, 
                 title,
                 names,
                 with_errorbars,
                 output_file=gnuplot_preferences.output_file_name,
                 additional_info='',
                 fit_lorentz=False, 
                 sample_name=None):
  '''
    Plotting with direct piping of the data to gnuplot, should work much faster
    Gnuplot.py must by installed and properly working.
    Files are stored in temporary folder set in gnuplot_preferences.
    
    @param session The session object to use
    @param file_name_prefix Prefix of the used data and gnuplot files
    @param title The title of the plot
    @param names The names of the plotted functions
    @param with_errorbars Use errorbars layout when plotting
    @param output_file File name for the output picture_height
    @param additional_info Additional info string for the title
    @param fit_lorentz Is a fit included in this measurement?
    
    @return Gnuplot error message or empty string
  '''
  gp=gnuplot_preferences # short form for gnuplot_preferences
  import Gnuplot
  if not sample_name:
    sample_name=datasets[0].sample_name
  file_numbers=[]
  for j, dataset in enumerate(datasets):
    for i, attachedset in enumerate(dataset.plot_together):
      file_numbers.append(str(j)+'-'+str(i))
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
                            (0, 0, 0),
                            postscript_export,
                            additional_info) 
  gplot=Gnuplot.Gnuplot()
  gnuplot_settings=gp.GNUPLOT_FILE_HEAD+\
  'set term '+terminal+'\n'+\
  'set output "'+output_file+'"\n'+\
  'set encoding '+gp.ENCODING+'\n'+\
  'set xlabel "'+gp.x_label+'"\n'+\
  'set ylabel "'+gp.y_label+'"\n'+\
  'set title "'+gp.plot_title+'"\n'
  if (len(datasets)==1) and (len(datasets[0].plot_together)==1): # if there is only one graph don't show a key
    gnuplot_settings+='unset key\n'
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
                              (0, 0, 0),
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
  if datasets[0].logz and dataset[0].zdata>=0:
    gplot('set log z\nset log cb')
  else:
    gplot('unset log z\nunset log cb')
  if datasets[0].zdata>=0:
    gplot.plotcmd = 'splot'
  else:
    gplot.plotcmd = 'plot'
  gplot._clear_queue()
  for i,dataset in enumerate(datasets):
  #++++++++++++++++++++++++ add each dataset to the plot +++++++++++++
    together_list=[use for use in dataset.plot_together if use!=dataset]
    if with_errorbars:
      datalist=dataset.list_err()
    else:
      datalist=dataset.list()
    if (dataset.zdata>=0): # for 3d-Data we have to create a temporal File
      dataset.export(session.TEMP_DIR+'tmp_data'+str(i)+'.out')
      plot=[Gnuplot.PlotItems.File(session.TEMP_DIR+'tmp_data'+str(i)+'.out',
                                   with_=str(plotting_param.replace('w ','',1)),
                                   title=names[datasets.index(dataset)],
                                   using=str(dataset.xdata+1)+':'+str(dataset.ydata+1)+':'+str(dataset.zdata+1))]
    else:
      plot=[Gnuplot.PlotItems.Data(datalist,
                                   with_=str(plotting_param.replace('w ','',1)),
                                   title=names[datasets.index(dataset)])]
    gplot._add_to_queue(plot)

  #------------------------ add each dataset to the plot --------------
    for j,attachedset in enumerate(together_list):
      #++++++++++++++++++++++++ add attached datasets to the plot +++++++++++++
      datalist=attachedset.list()
      if (attachedset.zdata>=0): # for 3d-Data we have to create a temporal File
        attachedset.export(session.TEMP_DIR+'tmp_data'+str(i)+'-'+str(j)+'.out')
        plot=[Gnuplot.PlotItems.File(session.TEMP_DIR+'tmp_data'+str(i)+'.out',
                                     with_=str(plotting_param.replace('w ','',1)),
                                     title=attachedset.short_info,
                                     using=str(attachedset.xdata+1)+':'+str(attachedset.ydata+1)+':'+str(attachedset.zdata+1))]
      else:
        plot=[Gnuplot.PlotItems.Data(datalist,
                                     with_=str(gp.plotting_parameters).replace('w ','',1),
                                     title=attachedset.short_info)]
      gplot._add_to_queue(plot)
    #------------------------  add attached datasets to the plot --------------
  gplot.refresh()
  gplot.close()
  # read stdout and stderr from gnuplot
  output=(session.gnuplot_output[0].read(), session.gnuplot_output[1].read())
  return output[1] # return the stderror

def gnuplot_plot_script(session,  
                        datasets,
                        file_name_prefix, 
                        file_name_postfix, 
                        title,
                        names,
                        with_errorbars,
                        output_file=gnuplot_preferences.output_file_name,
                        additional_info='',
                        fit_lorentz=False, 
                        sample_name=None, 
                        show_persistent=False): 
  '''
    Function to plot with an additional data and gnuplot file and calling to the gnuplot program.
    Files are stored in temporary folder set in gnuplot_preferences.
    
    @param session The session object to use
    @param file_name_prefix Prefix of the used data and gnuplot files
    @param title The title of the plot
    @param names The names of the plotted functions
    @param with_errorbars Use errorbars layout when plotting
    @param output_file File name for the output picture_height
    @param additional_info Additional info string for the title
    @param fit_lorentz Is a fit included in this measurement?
    
    @return Gnuplot error message or empty string
  '''
  gp=gnuplot_preferences # short form for gnuplot_preferences
  file_numbers=[]
  if show_persistent:
    global persistene_plots
    tmp_name='tmp_data_p-%i_' % persistene_plots
    persistene_plots+=1
    output_file_prefix=session.TEMP_DIR+tmp_name
    postscript_export=True
  else:
    tmp_name='tmp_data_'
    output_file_prefix=session.TEMP_DIR+tmp_name
  if len(datasets)==1 and getattr(datasets[0], 'is_matrix_data', False):
    datasets[0].export_matrix(output_file_prefix+str(0)+'-'+str(0)+'.bin')
  else:
    for j, dataset in enumerate(datasets):
      for i, attachedset in enumerate(dataset.plot_together):
        file_numbers.append(str(j)+'-'+str(i))
        attachedset.export(output_file_prefix+str(j)+'-'+str(i)+'.out')
  if not sample_name:
    sample_name=datasets[0].sample_name
  if output_file.rsplit('.',1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
  script_name=session.TEMP_DIR+replace_ph(session, 
                                          gp.gnuplot_file_name,
                                          datasets,
                                          file_name_prefix, 
                                          file_numbers, 
                                          title,
                                          names,
                                          sample_name,
                                          (0, 0, 0),
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
                                       output_file_prefix=output_file_prefix, 
                                       sample_name=sample_name, 
                                       show_persistent=show_persistent)
  write_file=open(script_name,'w')
  write_file.write( gnuplot_file_text+'\n' )
  write_file.close()
  try:
    if show_persistent:
      params=[session.GNUPLOT_COMMAND, '-persist', script_name]      
    else:
      params=[session.GNUPLOT_COMMAND, script_name]
    proc = subprocess.Popen(params, 
                        shell=False, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        stdin=subprocess.PIPE, 
                        )
    if show_persistent:
      output=('', '')
    else:
      output = proc.communicate()
  except:
    raise RuntimeError, "\nProblem communicating with Gnuplot, please check your system settings! Gnuplot command used: %s" % session.GNUPLOT_COMMAND
  try:
    # on older version of python this doesn't work
    proc.stdin.close()
  except:
    pass
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
    
    @return The altered string
  '''
  datanr=number[0]
  withnr=number[1]
  gp=gnuplot_preferences
  string=string.\
  replace('[font-path]',gp.FONT_PATH).\
  replace('[width]',session.picture_width).\
  replace('[height]',session.picture_height).\
  replace('[font-size]',str(int(session.font_size/1000.*int(session.picture_height)))).\
  replace('[name]',file_name_prefix).\
  replace('[sample]',sample_name).\
  replace('[nr]',datasets[datanr].number).\
  replace('[add_info]',additional_info).\
  replace('[info]',datasets[datanr].plot_together[withnr].info.replace('\n','\n#')).\
  replace('[x-unit]',datasets[datanr].plot_together[withnr].xunit()).\
  replace('[x-dim]',datasets[datanr].plot_together[withnr].xdim()).\
  replace('[y-unit]',datasets[datanr].plot_together[withnr].yunit()).\
  replace('[y-dim]',datasets[datanr].plot_together[withnr].ydim()).\
  replace('[z-unit]',datasets[datanr].plot_together[withnr].zunit()).\
  replace('[z-dim]',datasets[datanr].plot_together[withnr].zdim()).\
  replace('[title_add]',title).\
  replace('[titles_add]',names[number[2]]).\
  replace('[const_unit]',datasets[datanr].plot_together[withnr].units()[datasets[datanr].plot_together[withnr].type()]).\
  replace('[const_dim]',datasets[datanr].plot_together[withnr].dimensions()[datasets[datanr].plot_together[withnr].type()]).\
  replace('[const_value]',str(datasets[datanr].plot_together[withnr].last()[datasets[datanr].plot_together[withnr].type()]))
# translations for postscript export (special characters other than in png export)
# should be enlongated with other characters
  if postscript_export: # see gnuplot_preferences.py for this function
    string=postscript_replace(string)
  string=further_replacement(string)
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
                       output_file_prefix=None, 
                       sample_name=None, 
                       show_persistent=False
                       ):
  '''
      Create a script for the gnuplot program.
      
      @return The text of the script
  '''
  # TODO: Check for all functionalities compared with no script mode.
  # Ceck for unused code.
  if output_file_prefix is None:
    output_file_prefix=session.TEMP_DIR+'tmp_data_'
  gp=gnuplot_preferences # define global gnuplot_preferences modul as local gp 
  if not sample_name:
    sample_name=datasets[0].sample_name
  file_numbers=[]
  inserted=0
  for j, dataset in enumerate(datasets):
    for i, attachedset in enumerate(dataset.plot_together):
      file_numbers.append(str(j)+'-'+str(i))
      if i>0:
        names.insert(j+inserted+1, attachedset.short_info)
        inserted+=1
  if show_persistent:
    postscript_export=True
    terminal=gp.set_output_terminal_wxt
  elif output_file.rsplit('.',1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
  if with_errorbars and datasets[0].yerror is not None:
    plotting_param=gp.plotting_parameters_errorbars
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].yerror+1)
  else:
    plotting_param=gp.plotting_parameters
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)
  gnuplot_file_text=gp.GNUPLOT_FILE_HEAD+\
                    'set term '+terminal+'\n'
  if not show_persistent:
    gnuplot_file_text+='set output "'+output_file+'"\n'
  gnuplot_file_text+='set encoding '+gp.ENCODING+'\n'+\
                     'set xlabel "'+gp.x_label+'"\n'+\
                     'set ylabel "'+gp.y_label+'"\n'+\
                     'set title "'+gp.plot_title+'"\n'
  if (len(datasets)==1) and (len(datasets[0].plot_together)==1): # if there is only one graph don't show a key
    gnuplot_file_text+='unset key\n'
  gnuplot_file_text+=datasets[0].plot_options
  if datasets[0].logx:
    gnuplot_file_text=gnuplot_file_text+'set log x\n'
  if datasets[0].logy:
    gnuplot_file_text=gnuplot_file_text+'set log y\n'
  if datasets[0].logz and datasets[0].zdata>=0:
    gnuplot_file_text=gnuplot_file_text+'set log z\nset log cb\n'
  splot_add=datasets[0].plot_options.splot
  if datasets[0].zdata>=0:
    plotting_param=gp.plotting_parameters_3d
    gnuplot_file_text+='set view '+str(datasets[0].view_x)+','+str(datasets[0].view_z)+'\n'+\
        'set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
    if ((datasets[0].view_x%180)==0)&((datasets[0].view_z%90)==0):
      gnuplot_file_text+=gp.settings_3dmap
    else:
      gnuplot_file_text+=gp.settings_3d
    splot_add='s'
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].zdata+1)
  output_file_prefix=os.path.normpath(output_file_prefix)
  if len(datasets)==1 and getattr(datasets[0], 'is_matrix_data', False):
    return replace_ph(session, 
                       gnuplot_file_text+plot_matrix(datasets[0], output_file_prefix+file_numbers[0]+'.bin'),
                       datasets,
                       file_name_prefix,
                       file_numbers, 
                       title,
                       names,
                       sample_name,
                       (0, 0, 0),
                       postscript_export,
                       additional_info)
  gnuplot_file_text+='# now the plotting function\n'+splot_add+\
        'plot "'+output_file_prefix+file_numbers[0]+'.out" u '+using_cols+\
                datasets[0].plot_options.special_using_parameters+\
                ' t "'+gp.titles+'" '+\
                (datasets[0].plot_options.special_plot_parameters or plotting_param)
  gnuplot_file_text=replace_ph(session, 
                             gnuplot_file_text,
                             datasets,
                             file_name_prefix, 
                             file_numbers, 
                             title,
                             names,
                             sample_name,
                             (0, 0, 0),
                             postscript_export,
                             additional_info)
  for number in file_numbers[1:]:
    i, j=(int(number.split('-')[0]), int(number.split('-')[1]))
    if j==0:
      if datasets[0].zdata>=0:
        using_cols=str(datasets[i].xdata+1)+':'+str(datasets[i].ydata+1)+':'+str(datasets[i].zdata+1)
      elif with_errorbars and datasets[i].yerror is not None:
        plotting_param=gp.plotting_parameters_errorbars
        using_cols=str(datasets[i].xdata+1)+':'+str(datasets[i].ydata+1)+':'+str(datasets[i].yerror+1)
      else:
        plotting_param=gp.plotting_parameters
        using_cols=str(datasets[i].xdata+1)+':'+str(datasets[i].ydata+1)
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
          '.out" u '+using_cols+\
          datasets[i].plot_options.special_using_parameters+\
          ' t "'+gp.titles+'" '+(datasets[i].plot_options.special_plot_parameters or plotting_param)
      gnuplot_file_text=replace_ph(session, 
                                   gnuplot_file_text,
                                   datasets,
                                   file_name_prefix,
                                   file_numbers, 
                                   title,
                                   names,
                                   sample_name,
                                   (int(number.split('-')[0]), 0, file_numbers.index(number)),
                                   postscript_export,
                                   additional_info)
    else:
      using_cols_woerror=str(datasets[i].plot_together[j].xdata+1)+':'+\
                          str(datasets[i].plot_together[j].ydata+1)#+':'+\
                          #str(datasets[i].plot_together[j].yerror+1)
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
          '.out" u ' + using_cols_woerror + ' t "' + gp.titles + '" ' + gp.plotting_parameters
      gnuplot_file_text=replace_ph(session, 
                                   gnuplot_file_text,
                                   datasets,
                                   file_name_prefix,
                                   file_numbers, 
                                   title,
                                   names,
                                   sample_name,
                                   (i, j, file_numbers.index(number)),
                                   postscript_export,
                                   additional_info)
  return gnuplot_file_text

def plot_matrix(dataset, file_name):
  return 'plot "%s" binary format="%%float" u 1:2:3 w image\n' % (file_name, )

def postscript_replace(string):
  '''
    Replace special characters when using Postscript export instead of png.
  '''
  for from_char, to_char in gnuplot_preferences.postscript_characters:
    string=string.replace(from_char, to_char)
  return string


def further_replacement(string):
  '''
    String replacements done last, for example when an Item has empty unit replace [] with nothing.
  '''
  return string.replace('[]','')

def mpl_plot(session,  
            datasets,
            file_name_prefix, 
            title,
            names,
            with_errorbars,
            output_file=gnuplot_preferences.output_file_name,
            additional_info='',
            fit_lorentz=False, 
            sample_name=None, 
            show_persistent=False): 
  '''
    Plot the data using a matplotlib plotting object.
  '''
  from matplotlib import pyplot
  from matplotlib import mlab
  import matplotlib.colors
  import numpy
  gp=gnuplot_preferences
  # delete plotting area
  plot=session.mpl_plot
  figure=session.mpl_widget.figure
  figure.set_axes([figure.axes[0]])
  figure.subplots_adjust()
  plot.clear()
  # define global plot options
  def prereplace(string):
    return replace_ph(session, 
                     string,
                     datasets,
                     file_name_prefix, 
                     range(len(datasets)), 
                     title,
                     names,
                     first.sample_name,
                     (0, 0, 0))
  first=datasets[0]
  ix=first.xdata
  iy=first.ydata
  global_options=datasets[0].plot_options
  if not getattr(global_options, 'colormap', False):
    cmap={
            'red': [
                    (0., 0., 0.), 
                    (0.2, 0., 0.), 
                    (0.4, 1., 1.), 
                    (0.6, 1., 1.), 
                    (0.8, 0.5, 0.5), 
                    (1.0, 0., 0.), 
                    ], 
          'green': [
                    (0., 0., 0.), 
                    (0.2, 1., 1.), 
                    (0.4, 1., 1.), 
                    (0.6, 0., 0.), 
                    (0.8, 0., 0.), 
                    (1.0, 0., 0.), 
                    ], 
           'blue': [
                    (0., 1., 1.), 
                    (0.2, 0., 0.), 
                    (0.4, 0., 0.), 
                    (0.6, 0., 0.), 
                    (0.8, 0.5, 0.5), 
                    (1.0, 0., 0.), 
                    ]         
          }
    colormap=matplotlib.colors.LinearSegmentedColormap('default', cmap, N=512)
    pyplot.register_cmap(name='default', cmap=colormap)
    global_options.colormap='default'
  plot.set_xlabel("$"+prereplace(gp.x_label).replace('Å','A')+"$")
  plot.set_ylabel("$"+prereplace(gp.y_label).replace('Å','A')+"$")
  plot.set_title(prereplace(gp.plot_title))
  if first.logx:
    plot.set_xscale('log')
  else:
    plot.set_xscale('linear')
  if first.logy:
    plot.set_yscale('log')
  else:
    plot.set_yscale('linear')
  
  zplot=False
  # plot the datasets
  for dataset in datasets:
    data=dataset.get_filtered_data_matrix()
    x=data[dataset.xdata]
    y=data[dataset.ydata]
    label=dataset.short_info
    if dataset.zdata<0:
      if with_errorbars:
        dy=data[dataset.yerror]
        plot.errorbar(x, y, yerr=dy, label=label)
      else:
        plot.plot(x, y, label=label)
      # plot additional data e.g. fits
      for adddata in dataset.plot_together[1:]:
        data=adddata.get_filtered_data_matrix()
        x=data[adddata.xdata]
        y=data[adddata.ydata]
        plot.plot(x, y, label=label)   
    # 3d Plot
    else:
      zplot=True
      z=data[dataset.zdata]
      try:
        len_x=x[1:].tolist().index(x[0])+1
        if len_x==1:
          len_y=y[1:].tolist().index(y[0])+1
          len_x=len(x)//len_y
        else:
          len_y=len(x)//len_x
        if len_x<100 or len_y <100:
          raise RuntimeError, "Only to get in the except block."
        x=x.reshape(len_x, len_y)
        y=y.reshape(len_x, len_y)
        z=z.reshape(len_x, len_y)
      except:
        xi=numpy.linspace(x.min(), x.max(), max(min(numpy.sqrt(len(z))*2, 1000), numpy.sqrt(len(z)), 200))
        yi=numpy.linspace(y.min(), y.max(), max(min(numpy.sqrt(len(z))*2, 1000), numpy.sqrt(len(z)), 200))
        X, Y=numpy.meshgrid(xi, yi)
        Z=mlab.griddata(x, y, z, X, Y)   
        x=X
        y=Y
        z=Z
      if first.logz:
        if global_options.zrange[0]>0:
          z=numpy.maximum(z, global_options.zrange[0])
        z=mlab.ma.masked_where(z<=0, z)
        norm=matplotlib.colors.LogNorm()
      else:
        norm=None
      pm=plot.pcolormesh(x, y, z, 
                      vmin=global_options.zrange[0], vmax=global_options.zrange[1], 
                      norm=norm,
                      cmap = pyplot.get_cmap(global_options.colormap)
                      )
  
  # options which need to be set after plotting
  if len(datasets)>1:
    plot.legend()
  plot.set_xlim(global_options.xrange[0], global_options.xrange[1])
  plot.set_ylim(global_options.yrange[0], global_options.yrange[1])
  plot.set_ylim(global_options.yrange[0], global_options.yrange[1])
  if zplot:
    figure.colorbar(pm)

  # redraw image
  session.mpl_widget.draw_idle()
  return ""
