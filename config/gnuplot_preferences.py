#!/usr/bin/env python
''' 
 Variables for gnuplot options to be used by plot commands.
'''

from sys import prefix
from os.path import join as join_path

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2009"
__credits__ = []
__license__ = "None"
__version__ = "0.6a4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# place holders:
#
# [name] - name of input file
# [name-rmv] - name without suffix (replacement set in remove_from_name)
# [sample] - sample name as described in input file
# [script-path] - path of the python scripts root directory
# [font-size] - selected font size / 1000 * height (for export 1200)
# [nr] - number of sequence plotted
# [info] - header information of input file
# [add_info] - short string for special plot types as 'multi'
# [x-unit] - unit of x-dataset
# [y-unit] - unit of y-dataset
# [z-unit] - unit of z-dataset
# [x-dim] - dimention of x-dataset
# [y-dim] - dimension of y-dataset
# [z-dim] - dimension of z-dataset
# [title_add] - title addition set in function call
# [titles_add] - titles addition set in function call for diff24erent plots
# [const_unit] - first constant data unit
# [const_dim] - first constant data dimension
# [const_value] - first constant data value

#header information printed in gnuplot.tmp file, not really important
GNUPLOT_FILE_HEAD='#Gnuplot inputfile to plot the data of plot.py\n#[info]\n'
gnuplot_file_name='gnuplot.tmp'
# Linux printing command (works properly with .ps, problems with png with wrong size)
PRINT_COMMAND="lpr -P IFF17c4 -J \'plot_SQUID_data.py output\'  "
# Command for script mode to accress gnuplot
GNUPLOT_COMMAND="gnuplot"

def remove_from_name(name):
  '''
    Set suffix replacement.
  '''
  output=name.replace('.dat','').replace('.raw','')
  return output

# character encoding in gnuplot
ENCODING='iso_8859_1'
# set the terminal options for the gnuplot output (postscript could need other labels)
set_output_terminal_png='png enhanced size [width],[height] font "'+join_path('[script-path]', 'config', 'fonts',  'Arial.ttf')+'" [font-size]' #transparent
# used is determined by file name
set_output_terminal_ps='postscript landscape enhanced colour "Arial" [font-size] solid lw 2'

# set output file name, the postfix has to be chosen consistant to the 'set term' statement
output_file_name='[name]_[add_info][nr].png'
#output_file_name='[name]_[nr].ps'

# labels for x,y and z axis
x_label='[x-dim] [[x-unit]]'
y_label='[y-dim] [[y-unit]]'
z_label='[z-dim] [[z-unit]]'
# title for the whole picture
plot_title='[sample] [title_add]'
# parameters for the courve
plotting_parameters='w lines lw 2' # plotting x-y
plotting_parameters_errorbars='w errorbars pt 5 ps 0.5 lw 2' # plotting with errorbars
plotting_parameters_3d='w pm3d' # plotting 3d
plotting_parameters_fit='w lines lw 3'
settings_3d=\
'''set style line 100 lt 6 lw 2
set pm3d hidden3d 100
set ticslevel 0.05
set palette defined (0 "blue",50 "green", 100 "yellow",200 "red",255 "purple")
'''
settings_3dmap=\
'''set pm3d map interpolate 5,5
set ticslevel 0.05
set palette defined (0 "blue",50 "green", 80 "yellow",150 "red",200 "purple", 255 "black")
set size square
'''
defined_color_patterns={
                        'Default': 'defined (0 "blue",50 "green", 80 "yellow",150 "red",200 "purple", 255 "black")', 
                        'Black to Red': 'defined (0 "black",50 "purple", 80 "blue",150 "green",200 "yellow", 255 "red")', 
                        'Grey Scale': 'gray', 
                        'BGYR': 'defined (0 "blue",85 "green", 170 "yellow",255 "red")', 
                        'Black to Yellow': 'defined (0 "black",85 "blue", 170 "red",255 "yellow")', 
                        'Gnuplot std.': 'color', 
                        'Rainbow': 'rgbformulae 22,13,-31', 
                        'Hot': 'rgbformulae 21,22,23', 
                        'Color, gray printable': 'rgbformulae 31,32,33', 
                        }
# title for a curve
titles='[titles_add]'

def postscript_replace(string):
  '''
    Replace special characters when using Postscript export instead of png.
  '''
  # TODO: Add common characters for replacement.
  return string.replace('\\316\\274','{/Symbol m}').\
  replace('\\302\\267','\\267').\
  replace('\\302\\260','\\260')

def further_replacement(string):
  '''
    String replacements done last, for example when an Item has empty unit replace [] with nothing.
  '''
  return string.replace('[]','')
