# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in 4circle session.
'''

import wx

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.4"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class CircleGUI:
  def create_menu(self, home):
    '''
      create a specifig menu for the 4circle session
    '''

    print 'circle.py: Entry create_menu: self = ', self

#     circle Menu

    menu_list = []  

    title = '4 Circle'
    menu4Circle = wx.Menu() 

    menu = [menu4Circle, title] 
    print  'menu = ', menu
    menu_list.append(menu)

    return menu_list


#    string='''
#      <menu action='4CircleMenu'>
#      
#      </menu>
#    '''
#    # Create actions for the menu
#    actions=(
#            ( "4CircleMenu", None,                             # name, stock id
#                "4 Circle", None,                    # label, accelerator
#                None,                                   # tooltip
#                None ),
#             )
#    return string,  actions
