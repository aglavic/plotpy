# -*- encoding: utf-8 -*-
'''
  Generic GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.9.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


 
class GenericGUI:
  def create_menu(self):
    '''
      create a specifig menu for the generic session
    '''
    # Create XML for squid menu
    string=''
    # Create actions for the menu
    actions=(
             )
    return string,  actions
