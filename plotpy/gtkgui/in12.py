# -*- encoding: utf-8 -*-
'''
  IN12 GTK GUI class.
'''


class IN12GUI:
  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string=''#'
      #<menu action='TREFF'>
      #
      #</menu>
    #'''
    # Create actions for the menu
    actions=(
            ("IN12", None, # name, stock id
                "IN12", None, # label, accelerator
                None, # tooltip
                None),
             )
    return string, actions
