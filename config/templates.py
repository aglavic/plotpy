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
