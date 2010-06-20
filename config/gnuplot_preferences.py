# -*- encoding: utf-8 -*-
''' 
 Variables for gnuplot options to be used by plot commands.
'''

from sys import prefix, platform
from os.path import exists, split
from os.path import join as join_path

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"

#
# place holders:
#
# [name] - name of input file
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
PRINT_COMMAND="lpr -P IFF17c4 -J \'plot.py-output\' %s"
# Command for script mode to accress gnuplot
GNUPLOT_COMMAND="gnuplot"

# font path for export
if exists('/usr/share/fonts/truetype/msttcorefonts'):
  ## - DEBIAN - ## 
  FONT_PATH='/usr/share/fonts/truetype/msttcorefonts'
elif exists('C:\\WINDOWS\\Fonts'):
  FONT_PATH='C:\\WINDOWS\\Fonts'
else:
  try:
    # try to get the font path from the pygame module
    from pygame.font import match_font
    file_path=match_font('arial')
    if file_path:
      FONT_PATH=split(file_path)[0]
    else:
      FONT_PATH=join_path('[script-path]', 'config', 'fonts')
  except ImportError:
    # if there is no pygame module installed, use the fonts from this program
    FONT_PATH=join_path('[script-path]', 'config', 'fonts')


# character encoding in gnuplot
ENCODING='iso_8859_1'
# set the terminal options for the gnuplot output (postscript could need other labels)
set_output_terminal_png='png enhanced size [width],[height] font "'+join_path('[font-path]',  'Arial.ttf')+\
                          '" [font-size] lw 2' #transparent
# used is determined by file name
set_output_terminal_ps='postscript landscape enhanced colour "Arial" 16 solid lw 2'

# terminal for external gnuplot window
if "linux" in platform:
  set_output_terminal_wxt='wxt enhanced font "'+join_path('[font-path]',  'Arial.ttf')+\
                          '" 16'
else:
  set_output_terminal_wxt='windows enhanced font "'+join_path('[font-path]',  'Arial.ttf')+\
                          '" 16'

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
plotting_parameters='w lines lw 1.5' # plotting x-y
plotting_parameters_errorbars='w errorbars pt 5 ps 0.5 lw 1.5' # plotting with errorbars
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

postscript_characters= [ 
          ('µ','{/Symbol m}'), 
          ('°','\\260'), 
          ('·','\\267'), 
          ('²','\\262'), 
          ('α','{/Symbol a}'), 
          ('β','{/Symbol b}'), 
          ('γ','{/Symbol g}'), 
          ('Γ','{/Symbol G}'), 
          ('δ','{/Symbol d}'), 
          ('φ','{/Symbol f}'), 
          ('χ','{/Symbol c}'), 
          ('π','{/Symbol p}'), 
          ('σ','{/Symbol s}'), 
          ('ω','{/Symbol w}'), 
          ('Σ','{/Symbol S}'), 
          ('Δ','{/Symbol D}'), 
          ('Ω','{/Symbol W}'), 
          ('Θ','{/Symbol Q}'), 
          ('Å','A'), 
]