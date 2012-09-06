# -*- encoding: utf-8 -*-
'''
  IN12 GTK GUI class.
'''

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport

#----------------------- importing modules --------------------------


__author__="Artur Glavic"
__credits__=[]
__status__="Production"



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
            ("SAS", None, # name, stock id
                "SAS", None, # label, accelerator
                None, # tooltip
                None),
             )
    return string, actions