# -*- encoding: utf-8 -*-
'''
 Functions to plot measurements (MeasurementData objects) by gnuplot script.
 These functions are used by the GUI and script mode.
'''

# TODO: remove unnecessary parameters, include session parameters.

# Pleas do not make any changes here unless you know what you are doing.

import os
import sys
exit=sys.exit #@ReservedAssignment
import subprocess
import plot_script.config.gnuplot_preferences as gp
#from time import sleep

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

# gnuplot instances of persistent plots stay open to allow mouse interaction
persistent_plots=0
persistent_plot_instances=[]
#def close_persistents():
#  sys.stdout.write('Close')
#  sys.stdout.flush()
#  for p in persistent_plot_instances:
#    p.stdin.write('quit\n')
#    p.stdin.flush()
#    p.communicate()
#atexit.register(close_persistents)


maps_with_projection=False

# open an instance of gnuplot on first import
gnuplot_instance=None

def check_gnuplot_version(session):
  '''
    Return the version of the installed gnuplot program.
  '''
  script_name=os.path.join(session.TEMP_DIR, 'check_version.gp')
  write_file=open(script_name, 'w')
  write_file.write('''
        print GPVAL_VERSION
        print GPVAL_PATCHLEVEL
        print GPVAL_TERMINALS
      '''
                    )
  write_file.close()
  params=[session.GNUPLOT_COMMAND, script_name]
  try:
    proc=subprocess.Popen(params,
                        shell=gp.EMMULATE_SHELL,
                        creationflags=gp.PROCESS_FLAGS,
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        )
    output=proc.communicate()[0]
    version, patchlevel, terminals=output.splitlines()
    terminals=terminals.strip().split()
    terminals=[t.strip() for t in terminals]
    # set the terminal options according to available terminals
    for term in gp.gui_terminals:
      if term in terminals:
        gp.set_output_terminal_gui=" ".join(
              [term]+gp.gui_terminal_options[term]
                                                             )
        break
    for term in gp.image_terminals:
      if term in terminals:
        gp.set_output_terminal_image=" ".join(
              [term]+gp.image_terminal_options[term]
                                                             )
        break
    return (float(version), float(patchlevel)), terminals
  except:
    return (0., 0.), []

def gnuplot_plot_script(session,
                        datasets,
                        file_name_prefix,
                        file_name_postfix,
                        title,
                        names,
                        with_errorbars,
                        output_file=gp.output_file_name,
                        additional_info='',
                        fit_lorentz=False,
                        sample_name=None,
                        show_persistent=False,
                        get_xy_ranges=False):
  '''
    Function to plot with an additional data and gnuplot file and calling to the gnuplot program.
    Files are stored in temporary folder set in gp.
    
    :param session: The session object to use
    :param file_name_prefix: Prefix of the used data and gnuplot files
    :param title: The title of the plot
    :param names: The names of the plotted functions
    :param with_errorbars: Use errorbars layout when plotting
    :param output_file: File name for the output picture_height
    :param additional_info: Additional info string for the title
    :param fit_lorentz: Is a fit included in this measurement?
    
    :return: Gnuplot error message or empty string
  '''
  global gnuplot_instance
  file_numbers=[]
  if show_persistent:
    global persistent_plots
    tmp_name='tmp_data_p-%i_'%persistent_plots
    persistent_plots+=1
    output_file_prefix=session.TEMP_DIR+tmp_name
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
  #if output_file is None:
  #  postscript_export=False
  #elif output_file.rsplit('.', 1)[1]=='ps':
  #  postscript_export=True
  #else:
  #  postscript_export=False
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
    #write_file=open(script_name, 'w')
    #write_file.write(gnuplot_file_text+'\n')
    #write_file.close()
    #params=
    try:
      persistent=subprocess.Popen([session.GNUPLOT_COMMAND],
                          shell=gp.EMMULATE_SHELL,
                          creationflags=gp.PROCESS_FLAGS,
                          stderr=subprocess.STDOUT,
                          stdout=subprocess.PIPE,
                          stdin=subprocess.PIPE,
                          )
      persistent.stdin.write(gnuplot_file_text+'\n')
      persistent.stdin.flush()
      persistent_plot_instances.append(persistent)
    except:
      raise RuntimeError, "\nProblem communicating with Gnuplot, please check your system settings! Gnuplot command used: %s"%session.GNUPLOT_COMMAND
    return '', []
  try:
    gnuplot_instance.stdin.write('reset\n')
  except (IOError, ValueError), error:
    # gnuplot instance closed due to an unknown problem
    gnuplot_instance=None
    raise RuntimeError, "gnuplot instance closed due to unknown problem: %s"%(error)
  gnuplot_instance.stdin.write(gnuplot_file_text)
  gnuplot_instance.stdin.write('\nset output\nprint "|||"\n')
  output=gnuplot_instance.stdout.read(3)
  while output[-3:]!='|||':
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
    
    :return: The altered string
  '''
  datanr=number[0]
  withnr=number[1]
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
  replace('[font]', gp.FONT_DESCRIPTION).\
  replace('[font-file]', gp.FONT_FILE).\
  replace('[font-path]', gp.FONT_PATH).\
  replace('[width]', session.picture_width).\
  replace('[height]', session.picture_height).\
  replace('[font-size]', str(int(session.font_size/1000.*int(session.picture_height)))).\
  replace('[small-font-size]', str(int(session.font_size/1500.*int(session.picture_height)))).\
  replace('[name]', file_name_prefix).\
  replace('[sample]', sample_name).\
  replace('[nr]', datasets[datanr].number).\
  replace('[add_info]', additional_info).\
  replace('[info]', datasets[datanr].plot_together[withnr].info.replace('\n', '\n#')).\
  replace('[x-unit]', datasets[datanr].plot_together[withnr].xunit()).\
  replace('[x-dim]', datasets[datanr].plot_together[withnr].xdim()).\
  replace('[y-unit]', datasets[datanr].plot_together[withnr].yunit()).\
  replace('[y-dim]', datasets[datanr].plot_together[withnr].ydim()).\
  replace('[z-unit]', datasets[datanr].plot_together[withnr].zunit()).\
  replace('[z-dim]', datasets[datanr].plot_together[withnr].zdim()).\
  replace('[title_add]', title).\
  replace('[titles_add]', titles_add).\
  replace('[const_unit]', datasets[datanr].plot_together[withnr].units()[datasets[datanr].plot_together[withnr].type()]).\
  replace('[const_dim]', datasets[datanr].plot_together[withnr].dimensions()[datasets[datanr].plot_together[withnr].type()]).\
  replace('[const_value]', str(datasets[datanr].plot_together[withnr].last()[datasets[datanr].plot_together[withnr].type()]))
# translations for postscript export (special characters other than in png export)
# should be enlongated with other characters
  if postscript_export: # see gp.py for this function
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
                       output_file=gp.output_file_name,
                       additional_info='',
                       fit_lorentz=False,
                       output_file_prefix=None,
                       sample_name=None,
                       show_persistent=False
                       ):
  '''
      Create a script for the gnuplot program.
      
      :return: The text of the script
  '''
  if output_file_prefix is None:
    output_file_prefix=session.TEMP_DIR+'tmp_data_'
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
  postscript_export, gnuplot_file_text=script_header(show_persistent, datasets, output_file)
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
  if datasets[0].plot_options.with_errorbars is not None:
    if datasets[0].plot_options.with_errorbars and (datasets[0].yerror>=0 or datasets[0].y.error is not None):
        plotting_param=gp.plotting_parameters_errorbars
        using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)+':'+str(datasets[0].yerror+1)
    else:
      plotting_param=gp.plotting_parameters
      using_cols=str(datasets[0].xdata+1)+':'+str(datasets[0].ydata+1)
  elif with_errorbars and (datasets[0].yerror>=0 or datasets[0].y.error is not None):
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
      if datasets[i].plot_options.with_errorbars is not None:
        if datasets[i].plot_options.with_errorbars and (datasets[i].yerror>=0 or datasets[i].y.error is not None):
            plotting_param=gp.plotting_parameters_errorbars
            using_cols=str(datasets[i].xdata+1)+':'+str(datasets[i].ydata+1)+':'+str(datasets[i].yerror+1)
        else:
          plotting_param=gp.plotting_parameters
          using_cols=str(datasets[i].xdata+1)+':'+str(datasets[i].ydata+1)
      elif with_errorbars and (datasets[i].yerror>=0 or datasets[i].y.error is not None):
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
      plotting_param=gp.plotting_parameters
      using_cols_woerror=str(datasets[i].plot_together[j].xdata+1)+':'+\
                          str(datasets[i].plot_together[j].ydata+1)
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
          '.out" u '+using_cols_woerror+' t "'+gp.titles+'" '+\
          (datasets[i].plot_together[j].plot_options.special_plot_parameters or plotting_param)
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
    number="%i-%i"%(i, j)
    using_cols_woerror=str(datasets[i].plot_together[j].xdata+1)+':'+\
                        str(datasets[i].plot_together[j].ydata+1)+':'+\
                        str(datasets[i].plot_together[j].zdata+1)
    if getattr(datasets[i], 'is_matrix_data', False):
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
        '.bin"  binary format="%float" u 1:2:3 t "'+gp.titles+'" '+\
          (datasets[i].plot_options.special_plot_parameters or plotting_param)
    else:
      gnuplot_file_text+=',\\\n"'+output_file_prefix+number+\
        '.out" u '+using_cols_woerror+' t "'+gp.titles+'" '+\
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
  plotting_param=gp.plotting_parameters_3d
  output_file_prefix=os.path.normpath(output_file_prefix)
  cols=int(log((len(datasets[0].plot_together))+1, 2))
  rows=(len(datasets[0].plot_together)-1)//cols+1
  gnuplot_file_text='# now the plotting functions in multiplot layout\n'+\
                    'set multiplot layout %i,%i\n'%(cols, rows)+\
                    'unset key\n'
  for i, subdata in enumerate(datasets[0].plot_together):
    # Subplot title
    title=subdata.sample_name
    if subdata.plot_options.short_info_in_title:
      title+=' '+subdata.short_info
    gnuplot_file_text+='set title "%s"\n'%(title)
    gnuplot_file_text+='set zlabel "'+gp.z_label+'"\n'+'set cblabel "'+gp.z_label+'"\n'
    gnuplot_file_text+=subdata.plot_options
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

  dataset=datasets[0]
  output_file_prefix=os.path.normpath(output_file_prefix)
  projections_name=output_file_prefix+file_numbers[0]+'.xy'

  title=dataset.sample_name
  if dataset.plot_options.short_info_in_title:
    title+=dataset.short_info
  gnuplot_file_text+='set multiplot title "%s"\n'%(title)
  if dataset.logz:
    gnuplot_file_text+='set log x2\n'
    gnuplot_file_text+='set format x2 "10^{%L}\n'
  if dataset.logy:
    gnuplot_file_text+='set log y\n'
  x_range=list(dataset.plot_options._xrange)
  y_range=list(dataset.plot_options._yrange)
  if x_range[0] is None:
    x_range[0]=dataset.x.min()
  if x_range[1] is None:
    x_range[1]=dataset.x.max()
  if y_range[0] is None:
    y_range[0]=dataset.y.min()
  if y_range[1] is None:
    y_range[1]=dataset.y.max()
  z_range=dataset.plot_options._zrange
  if z_range[1] is None:
    z_range=(z_range[0], float(dataset.z.max()))
  gnuplot_file_text+="set autoscale x\n"
  gnuplot_file_text+=("set x2range [:]#[%s:%s]\n"%(z_range[0], z_range[1])).replace("None", "")
  gnuplot_file_text+='set yrange [%f:%f]\n'%(y_range[0], y_range[1])
  gnuplot_file_text+='unset xtics\n'
  gnuplot_file_text+='set x2tics rotate by -90 offset 0,1.4\n'
  gnuplot_file_text+='unset xlabel\n'
  gnuplot_file_text+='set lmargin at screen 0.15\nset rmargin at screen 0.3\n'
  gnuplot_file_text+='set bmargin at screen 0.3\nset tmargin at screen 0.85\n'
  gnuplot_file_text+='plot "%s" u 4:3 axes x2y1 w lines\n'%projections_name
  if dataset.logz:
    gnuplot_file_text+='unset log x\n'
    gnuplot_file_text+='set log y\n'
    gnuplot_file_text+='set format y "10^{%L}\n'
  else:
    gnuplot_file_text+='unset log y\n'
  if dataset.logx:
    gnuplot_file_text+='set log x\n'
  else:
    gnuplot_file_text+='unset log x\n'
  gnuplot_file_text+='set xrange [%f:%f]\n'%(x_range[0], x_range[1])
  gnuplot_file_text+='set autoscale y\n'
  gnuplot_file_text+=("set yrange [:]#[%s:%s]\n"%(z_range[0], z_range[1])).replace("None", "")
  #gnuplot_file_text+='unset ytics\n'
  gnuplot_file_text+='unset x2tics\n'
  gnuplot_file_text+='set xtics\n'
  gnuplot_file_text+='set xlabel "%s"\n'%gp.x_label
  gnuplot_file_text+='unset ylabel\n'
  gnuplot_file_text+='set lmargin at screen 0.3\nset rmargin at screen 0.8\n'
  gnuplot_file_text+='set bmargin at screen 0.15\nset tmargin at screen 0.3\n'
  gnuplot_file_text+='plot "%s" u 1:2 w lines\n'%projections_name
  if dataset.logz:
    gnuplot_file_text+='unset log y\n'
  if dataset.logy:
    gnuplot_file_text+='set log y\n'
  gnuplot_file_text+='set xrange [%f:%f]\n'%(x_range[0], x_range[1])
  gnuplot_file_text+='set yrange [%f:%f]\n'%(y_range[0], y_range[1])
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
  if show_persistent or output_file is None:
    postscript_export=True
    terminal=gp.set_output_terminal_gui
  elif output_file.rsplit('.', 1)[1]=='ps':
    postscript_export=True
    terminal=gp.set_output_terminal_ps
  else:
    postscript_export=False
    terminal=gp.set_output_terminal_image
    if not 'crop' in terminal:
      # crop option is not reset by restor
      terminal+=' nocrop'
  gnuplot_file_text=gp.GNUPLOT_FILE_HEAD+\
                    'set term '+terminal+'\n'
  if not show_persistent and output_file is not None:
    gnuplot_file_text+='set output "'+output_file+'"\n'
  if datasets[0].plot_options.is_polar:
    gnuplot_file_text+='set xlabel "'+gp.y_label+'"\n'+\
                     'set ylabel "'+gp.y_label+'"\n'+\
                     'set title "'+gp.plot_title+'"\n'
    if datasets[0].x.unit=='°':
      gnuplot_file_text+='set angle degree\n'
  else:
    gnuplot_file_text+='set xlabel "'+gp.x_label+'"\n'+\
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
  return 'plot "%s" binary format="%%float" u 1:2:3 w image\n'%(file_name,)

def postscript_replace(string):
  '''
    Replace special characters when using Postscript export instead of png.
  '''
  for from_char, to_char in gp.postscript_characters:
    string=string.replace(from_char, to_char)
  return string


def further_replacement(string):
  '''
    String replacements done last, for example when an Item has empty unit replace [] with nothing.
  '''
  return string.replace('[]', '')
