#!/usr/bin/env python
# Changes of gnuplot preferences specific for 4circle Data
# Overrides all settings in gnuplot_preferences.py
plotting_parameters='w lines lw 4'
plotting_parameters_errorbars='w errorbars pt 5 ps 1 lw 4' # plotting with errorbars
settings_3d='set pm3d interpolate 5,5\nset ticslevel 0.05\n'+\
'set palette defined (0 "blue",50 "green", 80 "yellow",150 "red",200 "purple", 255 "black")\n'