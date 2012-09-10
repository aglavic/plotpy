#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Script module to run the program.
'''

##---add_python_path_here---## # Place holder to add installation directory to python path for non superuser installation.

import sys
import os
import plotpy

if __name__=='__main__':
  if '--profile' in sys.argv:
    # code profiling run
    sys.argv.remove('--profile')
    import cProfile
    cProfile.run('plotpy._run()', os.path.join(os.path.split(__file__)[0], 'plot.py.profile'))
  else:
    plotpy._run()
