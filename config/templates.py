# -*- encoding: utf-8 -*-
'''
 Some general settings for the template framework
'''

__author__ = "Artur Glavic"
__credits__ = []
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__
__status__ = "Development"

import os

# Path for the template file
TEMPLATE_DIRECTORY=os.path.expanduser(os.path.join('~','.plotting_gui','templates'))

if not os.path.exists(TEMPLATE_DIRECTORY):
  os.makedirs(TEMPLATE_DIRECTORY)
  print "Copying default templates to user folder"
  from glob import glob
  abspath=os.path.abspath(os.path.split(__file__)[0])
  defpath=os.path.join(abspath,'default_templates')
  deftemps=glob(os.path.join(defpath, '*.py'))
  for deftemp in deftemps:
    sourcedata=open(deftemp, 'r').read()
    dest=os.path.join(TEMPLATE_DIRECTORY, os.path.split(deftemp)[1])
    open(dest, 'w').write(sourcedata)
