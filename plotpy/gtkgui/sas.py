# -*- encoding: utf-8 -*-
'''
  SAS GTK GUI class.
'''

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
