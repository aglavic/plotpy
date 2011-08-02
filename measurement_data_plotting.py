# -*- encoding: utf-8 -*-
'''
 Functions to plot measurements (MeasurementData objects) by gnuplot script.
 These functions are used by the GUI and script mode.
'''

# TODO: remove unnecessary parameters, include session parameters.

# Pleas do not make any changes here unless you know what you are doing.

import os
import sys
exit=sys.exit
import subprocess
from config import gnuplot_preferences
from time import sleep

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.8"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

persistene_plots=0
maps_with_projection=False

# open an instance of gnuplot on first import
gnuplot_instance=None

def check_gnuplot_version(session):
  '''
    Return the version of the installed gnuplot program.
  '''
  script_name=os.path.join(session.TEMP_DIR, 'check_version.gp')
  write_file=open(script_name,'w')
  write_file.write( '''
        print GPVAL_VERSION
        print GPVAL_PATCHLEVEL
      '''
                    )
  write_file.close()
  params=[session.GNUPLOT_COMMAND, script_name]
  try:
    proc = subprocess.Popen(params, 
                        shell=gnuplot_preferences.EMMULATE_SHELL, 
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE, 
                        stdin=subprocess.PIPE, 
                        )
    output = proc.communicate()[1]
    version, patchlevel=output.splitlines()
    return float(version), float(patchlevel)
  except:
    return 0., 0.

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
                        show_persistent=False, 
                        get_xy_ranges=False): 
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
  global gnuplot_instance
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
  for j, dataset in enumerate(datasets):
    for i, attachedset in enumerate(dataset.plot_together):
      if getattr(attachedset, 'is_matrix_data', False):
        file_numbers.append(str(j)+'-'+str(i))
        attachedset.export_matrix(output_file_prefix+str(j)+'-'+str(i)+'.bin')
      else:
        file_numbers.append(str(j)+'-'+str(i))
        attachedset.export(output_file_prefix+str(j)+'-'+str(i)+'.out')
  if datasets[0].zdata>=0 and maps_with_projection:
    # export data of projections
    projections_name=output_file_prefix+file_numbers[0]+'.xy'
    datasets[0].export_projections(projections_name)    
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
  if get_xy_ranges:
    gnuplot_file_text+="""
      print GPVAL_TERM_XMIN
      print GPVAL_TERM_XMAX
      print GPVAL_TERM_YMIN
      print GPVAL_TERM_YMAX
      print GPVAL_X_MIN
      print GPVAL_X_MAX
      print GPVAL_Y_MIN
      print GPVAL_Y_MAX
      """
  if show_persistent:
    write_file=open(script_name,'w')
    write_file.write( gnuplot_file_text+'\n' )
    write_file.close()
    params=[session.GNUPLOT_COMMAND, '-persist', script_name]      
    try:
      proc = subprocess.Popen(params, 
                          shell=gnuplot_preferences.EMMULATE_SHELL, 
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE, 
                          stdin=subprocess.PIPE, 
                          )
    except:
      raise RuntimeError, "\nProblem communicating with Gnuplot, please check your system settings! Gnuplot command used: %s" % session.GNUPLOT_COMMAND
    return '', []
  try:
    gnuplot_instance.stdin.write('reset\n')
  except (IOError, ValueError), error:
    # gnuplot instance closed due to an unknown problem
    gnuplot_instance=None
    raise RuntimeError, "gnuplot instance closed due to unknown problem: %s" % (error)
  gnuplot_instance.stdin.write(gnuplot_file_text)
  gnuplot_instance.stdin.write('\nset output\nprint "|||"\n')
  output=gnuplot_instance.stdout.read(3)
  while output[-3:] != '|||':
    output+=gnuplot_instance.stdout.read(1)
  output=output[:-3].strip()
  if 'line' in output:
    return output, []
  else:
    try:
      return '', map(float, output.splitlines())
    except ValueError:
      return output, []

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
  if '[titles_add]' in string:
    titles_add=replace_ph(session, 
                                    names[number[2]],
                                    datasets, 
                                    file_name_prefix, 
                                    file_numbers, 
                                    title, 
                                    names, 
                                    sample_name, 
                                    number, 
                                    postscript_export, 
                                    additional_info)
  else:
    titles_add=''
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
  replace('[titles_add]',titles_add).\
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
  if output_file_prefix is None:
    output_file_prefix=session.TEMP_DIR+'tmp_data_'
  gp=gnuplot_preferences # define global gnuplot_preferences modul as local gp 
  if not sample_name:
    sample_name=datasets[0].sample_name
  # Get nummerating strings for the datasets
  file_numbers=[]
  inserted=0
  for j, dataset in enumerate(datasets):
    for i, attachedset in enumerate(dataset.plot_together):
      file_numbers.append(str(j)+'-'+str(i))
      if i>0:
        names.insert(j+inserted+1, attachedset.short_info)
        inserted+=1
  # Create global options
  postscript_export, gnuplot_file_text= script_header(show_persistent, datasets, output_file)
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
  # Creat plot/splot lines
  if datasets[0].zdata>=0:
    if maps_with_projection:
      gnuplot_file_text+=script_plotlines_3d_projection(session, datasets, file_name_prefix, output_file_prefix, 
                file_numbers, title, names, sample_name, postscript_export, additional_info, with_errorbars)
    else:
      gnuplot_file_text+=script_plotlines_3d(session, datasets, file_name_prefix, output_file_prefix, file_numbers, 
                     title, names, sample_name, postscript_export, additional_info, with_errorbars)
  else:
    gnuplot_file_text+=script_plotlines(session, datasets, file_name_prefix, output_file_prefix, file_numbers, 
                     title, names, sample_name, postscript_export, additional_info, with_errorbars)
  return gnuplot_file_text

def script_plotlines(session, datasets, file_name_prefix, output_file_prefix, file_numbers, 
                     title, names, sample_name, postscript_export, additional_info, with_errorbars):
  '''
    Plot lines for 2d plots. (x vs. y)
  '''
  gnuplot_file_text=''
  gp=gnuplot_preferences
  if with_errorbars and (datasets[0].yerror>=0 or datasets[0].y.error is not None):
    plotting_param=gp.plotting_parameters_errorbars
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].yerror+1)
  else:
    plotting_param=gp.plotting_parameters
    using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)
  output_file_prefix=os.path.normpath(output_file_prefix)
  gnuplot_file_text+='# now the plotting function\n'+\
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
      if with_errorbars and (datasets[i].yerror>=0 or datasets[i].y.error is not None):
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
                          str(datasets[i].plot_together[j].ydata+1)
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

def script_plotlines_3d(session, datasets, file_name_prefix, output_file_prefix, file_numbers, 
                     title, names, sample_name, postscript_export, additional_info, with_errorbars):
  '''
    Plot lines for 3d plots. (x,y vs. z)
  '''
  gnuplot_file_text=''
  gp=gnuplot_preferences  
  plotting_param=gp.plotting_parameters_3d
  gnuplot_file_text+='set view '+str(datasets[0].view_x)+','+str(datasets[0].view_z)+'\n'+\
      'set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
  if ((datasets[0].view_x%180)==0)&((datasets[0].view_z%90)==0):
    gnuplot_file_text+=gp.settings_3dmap
  else:
    gnuplot_file_text+=gp.settings_3d
  first_index=datasets[0].plot_together_zindex
  if first_index==-1:
    return gnuplot_file_text+script_plotlines_multiplot_3d(session, datasets, file_name_prefix, output_file_prefix, 
                      file_numbers, title, names, sample_name, postscript_export, additional_info, with_errorbars)
  using_cols=str(datasets[0].plot_together[first_index].xdata+1)+':'+\
              str(datasets[0].plot_together[first_index].ydata+1)+':'+\
              str(datasets[0].plot_together[first_index].zdata+1)
  output_file_prefix=os.path.normpath(output_file_prefix)
  if getattr(datasets[0], 'is_matrix_data', False):
    gnuplot_file_text+='# now the plotting function\n'+\
        'plot "'+output_file_prefix+file_numbers[first_index]+'.bin" binary format="%float" u 1:2:3 w image t "'+gp.titles+'" '
  else:
    gnuplot_file_text+='# now the plotting function\n'+\
        'splot "'+output_file_prefix+file_numbers[first_index]+'.out" u '+using_cols+\
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
                             (0, first_index, 0),
                             postscript_export,
                             additional_info)
  for i in range(len(datasets))[1:]:
    j=datasets[i].plot_together_zindex
    number="%i-%i" % (i, j)
    using_cols_woerror=str(datasets[i].plot_together[j].xdata+1)+':'+\
                        str(datasets[i].plot_together[j].ydata+1)+':'+\
                        str(datasets[i].plot_together[j].zdata+1)
    if getattr(datasets[i], 'is_matrix_data', False):
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
        '.bin"  binary format="%float" u 1:2:3 t "' + gp.titles + '" ' + \
          (datasets[i].plot_options.special_plot_parameters or plotting_param)
    else:
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
        '.out" u ' + using_cols_woerror + ' t "' + gp.titles + '" ' + \
          (datasets[i].plot_options.special_plot_parameters or plotting_param)
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

def script_plotlines_multiplot_3d(session, datasets, file_name_prefix, output_file_prefix, 
                    file_numbers, title, names, sample_name, postscript_export, additional_info, with_errorbars):
  '''
    Plot lines for 3d plots as multiplot layout (data, fit, data-fit, log(data)-log(fit)). (x,y vs. z)
  '''
  from math import log
  gp=gnuplot_preferences
  plotting_param=gp.plotting_parameters_3d
  output_file_prefix=os.path.normpath(output_file_prefix)
  cols=int(log((len(datasets[0].plot_together))+1, 2))
  rows=(len(datasets[0].plot_together)-1)//cols+1
  gnuplot_file_text='# now the plotting functions in multiplot layout\n'+\
                    'set multiplot layout %i,%i\n' % (cols, rows)+\
                    'unset key\n'
  for i, subdata in enumerate(datasets[0].plot_together):
    # Subplot title
    gnuplot_file_text+='set title "%s"\n' % (subdata.sample_name+' '+subdata.short_info)
    gnuplot_file_text+='set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
    gnuplot_file_text=replace_ph(session, 
                             gnuplot_file_text,
                             datasets,
                             file_name_prefix, 
                             file_numbers, 
                             title,
                             names,
                             sample_name,
                             (0, i, i),
                             postscript_export,
                             additional_info)
    using_cols=str(subdata.xdata+1)+':'+\
              str(subdata.ydata+1)+':'+\
              str(subdata.zdata+1)
    # Matrix binary or column exported data?
    if getattr(datasets[0], 'is_matrix_data', False):
      gnuplot_file_text+='# now the plotting function\n'+\
          'plot "'+output_file_prefix+file_numbers[i]+'.bin" binary format="%float" u 1:2:3 w image t "'+gp.titles+'"\n'
    else:
      gnuplot_file_text+='splot "'+output_file_prefix+file_numbers[i]+'.out" u '+using_cols+\
                  datasets[0].plot_options.special_using_parameters+\
                  ' t "'+gp.titles+'" '+\
                  (datasets[0].plot_options.special_plot_parameters or plotting_param)+'\n'
    gnuplot_file_text=replace_ph(session, 
                             gnuplot_file_text,
                             datasets,
                             file_name_prefix, 
                             file_numbers, 
                             title,
                             names,
                             sample_name,
                             (0, i, i),
                             postscript_export,
                             additional_info)
  return gnuplot_file_text+'unset multiplot\n'
    
def script_plotlines_3d_projection(session, datasets, file_name_prefix, output_file_prefix, file_numbers, 
                     title, names, sample_name, postscript_export, additional_info, with_errorbars):
  '''
    Plot lines for 3d plots with projections on the axes. (x,y vs. z)
  '''
  gnuplot_file_text='unset title\n'
  gp=gnuplot_preferences

  dataset=datasets[0]
  output_file_prefix=os.path.normpath(output_file_prefix)
  projections_name=output_file_prefix+file_numbers[0]+'.xy'
  
  gnuplot_file_text+='set multiplot title "%s"\n' % (dataset.sample_name + dataset.short_info)
  if dataset.logz:
    gnuplot_file_text+='set log x2\n'
    gnuplot_file_text+='set format x2 "10^{%L}\n'
  xrange=list(dataset.plot_options._xrange)
  yrange=list(dataset.plot_options._yrange)
  if xrange[0] is None:
    xrange[0]=dataset.x.min()
  if xrange[1] is None:
    xrange[1]=dataset.x.max()
  if yrange[0] is None:
    yrange[0]=dataset.y.min()
  if yrange[1] is None:
    yrange[1]=dataset.y.max()
  zrange=dataset.plot_options._zrange
  if zrange[1] is None:
    zrange=(zrange[0], float(dataset.z.max()))
  gnuplot_file_text+="set autoscale x\n"
  gnuplot_file_text+= ("set x2range [%s:%s]\n" % (zrange[0], zrange[1] )).replace("None", "")
  gnuplot_file_text+='set yrange [%f:%f]\n' % (yrange[0], yrange[1])
  gnuplot_file_text+='unset xtics\n'
  gnuplot_file_text+='set x2tics rotate by -90 offset 0,1.4\n'
  gnuplot_file_text+='unset xlabel\n'
  gnuplot_file_text+='set lmargin at screen 0.15\nset rmargin at screen 0.3\n'
  gnuplot_file_text+='set bmargin at screen 0.3\nset tmargin at screen 0.85\n'
  gnuplot_file_text+='plot "%s" u 4:3 axes x2y1 w lines\n' % projections_name
  if dataset.logz:
    gnuplot_file_text+='unset log x\n'
    gnuplot_file_text+='set log y\n'
    gnuplot_file_text+='set format y "10^{%L}\n'
  gnuplot_file_text+='set xrange [%f:%f]\n' % (xrange[0], xrange[1])
  gnuplot_file_text+='set autoscale y\n'
  gnuplot_file_text+=("set yrange [%s:%s]\n" % (zrange[0], zrange[1] )).replace("None", "")
  #gnuplot_file_text+='unset ytics\n'
  gnuplot_file_text+='unset x2tics\n'
  gnuplot_file_text+='set xtics\n'
  gnuplot_file_text+='set xlabel "%s"\n' % gp.x_label
  gnuplot_file_text+='unset ylabel\n'
  gnuplot_file_text+='set lmargin at screen 0.3\nset rmargin at screen 0.8\n'
  gnuplot_file_text+='set bmargin at screen 0.15\nset tmargin at screen 0.3\n'
  gnuplot_file_text+='plot "%s" u 1:2 w lines\n' % projections_name
  if dataset.logz:
    gnuplot_file_text+='unset log y\n'
  
  gnuplot_file_text+='set xrange [%f:%f]\n' % (xrange[0], xrange[1])
  gnuplot_file_text+='set yrange [%f:%f]\n' % (yrange[0], yrange[1])
  gnuplot_file_text+='unset xtics\n'
  gnuplot_file_text+='unset ytics\n'
  gnuplot_file_text+='unset xtics\n'
  gnuplot_file_text+='unset xlabel\n'
  gnuplot_file_text+='set lmargin at screen 0.3\nset rmargin at screen 0.8\n'
  gnuplot_file_text+='set bmargin at screen 0.3\nset tmargin at screen 0.85\n'
  plotting_param=gp.plotting_parameters_3d
  gnuplot_file_text+='set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
  gnuplot_file_text+=gp.settings_3dmap.replace('set size square', '')
  using_cols=str(datasets[0].xdata+1)+':'+\
              str(datasets[0].ydata+1)+':'+\
              str(datasets[0].zdata+1)
  if getattr(datasets[0], 'is_matrix_data', False):
    gnuplot_file_text+='# now the plotting function\n'+\
        'plot "'+output_file_prefix+file_numbers[0]+'.bin" binary format="%float" u 1:2:3 w image t "'+gp.titles+'" '
  else:
    gnuplot_file_text+='# now the plotting function\n'+\
        'splot "'+output_file_prefix+file_numbers[0]+'.out" u '+using_cols+\
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
  return gnuplot_file_text+'\nunset multiplot'

def script_header(show_persistent, datasets, output_file):
  '''
    Create the header of the script with global settings.
  '''
  gp=gnuplot_preferences
  if show_persistent:
    postscript_export=True
    terminal=gp.set_output_terminal_wxt
  elif output_file.rsplit('.',1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_png
    if not 'crop' in terminal:
      terminal+=' nocrop'
  gnuplot_file_text=gp.GNUPLOT_FILE_HEAD+\
                    'set term '+terminal+'\n'
  if not show_persistent:
    gnuplot_file_text+='set output "'+output_file+'"\n'
  if datasets[0].plot_options.is_polar:
    gnuplot_file_text+='set encoding '+gp.ENCODING+'\n'+\
                     'set xlabel "'+gp.y_label+'"\n'+\
                     'set ylabel "'+gp.y_label+'"\n'+\
                     'set title "'+gp.plot_title+'"\n'
    if datasets[0].x.unit == '°':
      gnuplot_file_text+='set angle degree\n'
  else:
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
  return postscript_export, gnuplot_file_text


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
      if with_errorbars and (dataset.yerror>=0 or dataset.y.error is not None):
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
