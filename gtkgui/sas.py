# -*- encoding: utf-8 -*-
'''
  IN12 GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.8.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


 
class SASGUI:
  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string=''#'
      #<menu action='SAS'>
      #
      #</menu>
    #'''
    # Create actions for the menu
    actions=(
            ( "SAS", None,                             # name, stock id
                "SAS", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions
