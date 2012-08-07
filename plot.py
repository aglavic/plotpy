#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Script module to run the program.
'''

##---add_python_path_here---## # Place holder to add installation directory to python path for non superuser installation.

import plot_script
import sys
import os

if __name__=='__main__':
  if '--profile' in sys.argv:
    # code profiling run
    sys.argv.remove('--profile')
    import cProfile
    cProfile.run('plot_script._run()', os.path.join(os.path.split(__file__)[0], 'plot.py.profile'))
  else:
    plot_script._run()
