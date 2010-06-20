# -*- encoding: utf-8 -*-
'''
  Session expansion class for GUI in squid session.
'''

import wx


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2010"
__credits__ = []
__license__ = "None"
__version__ = "0.7a"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SquidGUI:
  def create_menu(self, home):
    '''
      create a specifig menu for the squid session
    '''
    # Create XML for squid menu
    print 'squid.py: Entry create_menu: self = ', self

#     SQUID Menu

    menu_list = []    
    
    title        = 'SQUID'
    menuSquid    = wx.Menu()
 
    #id = menuSquid.Append( wx.ID_ANY, 'Diamagnetic Correction',
      #                     'Diamagnetic Correction').GetId()
    #act = 'SquidDia'
    #home.Bind( wx.EVT_MENU, id= id,
        #       handler=lambda evt, arg1=act, arg2=home, arg3=self.toggle_correction: arg3( evt, arg1, arg2) )
  
    #id = menuSquid.Append( wx.ID_ANY, 'Paramagnetic Correction',
       #                    'Paramagnetic Correction').GetId()
    #act = 'SquidPara'
    #home.Bind( wx.EVT_MENU, id= id,
      #         handler=lambda evt, arg1=act, arg2=home, arg3=self.toggle_correction: arg3( evt, arg1, arg2) )
 
    #id = menuSquid.Append( wx.ID_ANY, 'Extract magnetic moment',
     #                      'Extract magnetic moment').GetId()
    #act = 'SquidExtractRaw'
    #home.Bind( wx.EVT_MENU, id= id,
     #          handler=lambda evt, arg1=act, arg2=home, arg3=self.calc_moment_from_rawdata: arg3( evt, arg1, arg2) )

    menu = [menuSquid, title]
    print 'menu = ', menu
    menu_list.append(menu) 
    return menu_list


#    string='''
#      <menu action='SquidMenu'>
#        <menuitem action='SquidDia'/>
#        <menuitem action='SquidPara'/>
#        <menuitem action='SquidExtractRaw'/>
#      </menu>
#    '''
#    # Create actions for the menu, functions are invoked with the window as
#    # third parameter to make interactivity with the GUI possible
#    actions=(
#            ( "SquidMenu", None,                             # name, stock id
#                "SQUID", None,                    # label, accelerator
#                None,                                   # tooltip
#                None ),
#            ( "SquidDia", None,                             # name, stock id
#                "Diamagnetic Correction", None,                    # label, accelerator
#                None,                                   # tooltip
#                self.toggle_correction ),
#            ( "SquidPara", None,                             # name, stock id
#                "Paramagnetic Correction", None,                    # label, accelerator
#                None,                                   # tooltip
#                self.toggle_correction ),
#            ( "SquidExtractRaw", None,                             # name, stock id
#                "Extract magnetic moment", None,                    # label, accelerator
#                None,                                   # tooltip
#                self.calc_moment_from_rawdata ),
#             )
#    return string,  actions
    
  
