# -*- encoding: utf-8 -*-
'''
  Own dialogs for the GUI using the wxWidgets toolkit.
'''

__version__    = "0.7.4.1"

import wx
import sys

class MyMessageDialog( wx.Dialog ):
  '''
    Eigener Message Dialog
  '''
 
  def __init__(self, parent, title):
     wx.Dialog.__init__(self, parent, size=(450,150), title=title,
                        style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.STAY_ON_TOP )

     bs       = wx.BoxSizer(wx.VERTICAL)
     self.SetSizer( bs )
     msgsizer = wx.BoxSizer( wx.HORIZONTAL )
     if sys.platform == 'darwin':
        artID = wx.ART_HELP
     else:
        artID = wx.ART_QUESTION

     bitmap = wx.StaticBitmap( self, id=wx.ID_ANY, 
                               bitmap=wx.ArtProvider.GetBitmap(artID, wx.ART_OTHER) )
     text = wx.StaticText( self, wx.ID_ANY, 
                           'You are starting the GUI the first time,\n do you want to search for updates automatically?')
     msgsizer.Add( bitmap, 0, wx.ALL, 3 )
     msgsizer.Add( text,   0, wx.ALL|wx.EXPAND, 3 )

     butsizer = wx.BoxSizer( wx.HORIZONTAL )
     b1 = wx.Button(self, id=wx.ID_HIGHEST+1, label='Yes, only Stable' )
     b2 = wx.Button(self, id=wx.ID_HIGHEST+2, label='Yes, all Versions' )
     b3 = wx.Button(self, id=wx.ID_HIGHEST+3, label='No' )
     butsizer.Add( b1, 0, wx.ALL|wx.EXPAND, 10)
     butsizer.Add( b2, 0, wx.ALL|wx.EXPAND, 10)
     butsizer.Add( b3, 0, wx.ALL, 10)


     bs.Add( msgsizer, 0 , wx.ALL|wx.EXPAND, 10)
     bs.Add( butsizer, 0 , wx.ALL|wx.EXPAND, 10)

     b1.Bind(wx.EVT_BUTTON, self.OnButClicked )
     b2.Bind(wx.EVT_BUTTON, self.OnButClicked )
     b3.Bind(wx.EVT_BUTTON, self.OnButClicked )

  def OnButClicked(self, event):
    print 'Entry OnButClicked'
    id = event.GetId()
    print 'event id = ',id
    ret = 0
    if id == wx.ID_HIGHEST+1:
       ret = 1
    elif id == wx.ID_HIGHEST+2:
       ret = 2
    self.EndModal( ret )

  
if __name__ == '__main__':
  app   = wx.App(False)
  dlg = MyMessageDialog(None, 'MyMessageDialog')
  ret = dlg.ShowModal()
  print 'ret = ',ret
  dlg.Destroy()

  app.MainLoop()
