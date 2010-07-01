#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Dummy module to run the program.
'''

import sys, os
##---add_python_path_here---## # Place holder to add installation directory to python path for non superuser installation.

try:
  import plot_script
except ImportError:
  import __init__ as plot_script

if __name__=='__main__':
  plot_script._run()
