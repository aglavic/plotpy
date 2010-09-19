# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in KWS2 session.
'''

import wx

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7beta6"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class KWS2GUI:
  def create_menu(self, home):
    '''
      create a specifig menu for the IN12 session
    '''
    print 'kws2.py: Entry create_menu: self = ', self
    menu_list = []
    title     = 'IN12'
    menuKWS2  = wx.Menu()
    menu      = [menuKWS2, title]
    menu_list.append(menu)

    return menu_list
