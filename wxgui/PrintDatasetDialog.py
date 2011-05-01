# -*- encoding: utf-8 -*-
#!/usr/local/bin/python

import wx

__author__     = "Artur Glavic"
__copyright__  = "Copyright 2008-2011"
__credits__ = ['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika', 
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
__license__    = "None"
__version__    = "0.7.5.2"
__maintainer__ = "Artur Glavic"
__email__      = "a.glavic@fz-juelich.de"
__status__     = "Development"

class PrintDatasetDialog( wx.Printout ):
#
#     provide at least:
#              GetPageInfo
#              HasPage
#              OnPrintPage
#
#     andere Methoden koennen auch ueberschrieben werden, falls noetig
#
      
      def __init__(self, datasets, main_window, resolution=300, title='Test PrintDatasetDialog', multiplot=False):

          print 'Entry PrintDataset __init__'
          print 'len(datasets) = ', len(datasets)
          self.datasets      = datasets
          self.use_multiplot = multiplot
          self.main_window   = main_window
          self.width         = resolution*11.66
          self.session       = self.main_window.active_session

          wx.Printout.__init__(self, title )
          
#     Defaults
          self.minPage  = 1
          self.maxPage  = 1
          self.pageFrom = 1    # not currently used by wxWidgets
          self.pageTo   = 1    # not currently used by wxWidgets
  
          self.prt_dc = None
          print 'Return from MyPrintout __init__'
          
      def OnPreparePrinting(self):
          '''
           Prepare Printing
           Calculate the number of pages corresponding to the number of datasets
          '''
          print 'Entry PrintDatasetDialog::OnPreparePrinting'
          
#     Hier die Anzahl der Seiten berechnen
          if self.use_multiplot:
            n_pages = 1
          else:
            n_pages = len(self.datasets)
          self.minPage  = 1
          self.maxPage  = n_pages
          self.pageFrom = 1
          self.pageTo   = self.maxPage
          
#         DC holen
          self.prt_dc = self.GetDC()
           

       
      def GetPageInfo( self):
          print 'Entry PrintDatasetDialog::GetPageInfo'
#         returns (minPage, maxPage, pageFrom, pageTo) or False     
          return (self.minPage, self.maxPage, self.pageFrom, self.pageTo )

      def HasPage( self, page ):
          print 'Entry PrintDatasetDialog::HasPage: page = ', page
          return (page >= self.minPage and page <= self.maxPage)
    
      def OnPrintPage( self, page ):
          print 'Entry PrintDatasetDialog::OnPrintPage: page = ',page
#     in dieser Methode wird gedruckt

          filename = self.session.TEMP_DIR+'plot_temp.png'
          if self.use_multiplot:
                self.multiplot(self.datasets)   # noch dummy routine
          else:
                dataset = self.datasets[page-1]
                self.plot(dataset)

          print 'Entry PrintDatasetDialog::OnPrintPage: filename = ',filename

          dc_size = self.prt_dc.GetSize()
          print 'dc_size        = ', dc_size
          print 'dc_size width  = ', dc_size.GetWidth()
          print 'dc_size height = ', dc_size.GetHeight()
#          
          img = wx.Image( filename, wx.BITMAP_TYPE_PNG )
          print 'image width    = ',img.GetWidth()
          print 'image height   = ',img.GetHeight()

#         Berechne Skalierungsfaktor
          dc_w       = dc_size.GetWidth()
          dc_h       = dc_size.GetHeight()
          img_w      = img.GetWidth()
          img_h      = img.GetHeight()
          rotated    = False
          if img_w > img_h:
             print 'image width > image height: rotate image'
#            Drehe das Bild um 90 Grad
             img     = img.Rotate90( True )
             hlp     = img_w 
             img_w   = img_h 
             img_h   = hlp
             rotated = True
                 
          scaleX     = float(dc_w) / img_w
          scaleY     = float(dc_h) / img_h
          print 'scaleX, scaleY = ',scaleX,', ',scaleY
          actual_scale = min(scaleX, scaleY)
          
#         Berechne Position im DC
          posX       = (dc_w - (img_w*actual_scale)) /2.0
          posY       = (dc_h - (img_h*actual_scale)) /2.0
          print 'posX, posY = ',posX,', ',posY

          self.prt_dc.SetUserScale( scaleX, scaleY )
          self.prt_dc.SetDeviceOrigin( 0, 10 )

          bmp = img.ConvertToBitmap()
          self.prt_dc.DrawBitmap( bmp, 0, 10, False )

#         Draw Text ( Filename )
          self.prt_dc.SetDeviceOrigin( 0.0, 0.0 )
          text_scaleX = 1.5
          text_scaleY = 1.5
          self.prt_dc.SetUserScale( text_scaleX, text_scaleY )
          if rotated:
            text_xpos = dc_size[0]/text_scaleX
            angle     = -90.
          else:
            text_xpos = 0
            angle     = 0.0
            
          self.prt_dc.DrawRotatedText('Seite %d/%d: File %s'%(page,self.maxPage, filename) , text_xpos, 0, angle)
#         Die Schrift ist unterschiedlich gross (MAC oder Linux)      
#          

          return True    # oder False --> Abbruch des Printings
    
    
      def multiplot( self, dataset_list ):
          '''
            Method to create one multiplot in print quality
          '''

          print 'PrintDatasetDialog.py Entry multiplot'
          session                = self.main_window.active_session
          session.picture_width  = str(int(self.width))
          session.picture_height = str(int(self.width/1.414))
          window                 = self.main_window
          window.plot( session,
                       [item[0] for item in dataset_list],
                       dataset_list[0][1],
                       dataset_list.title,
                       [item[0].short_info for item in dataset_list],
                       errorbars,
                       output_file = session.TEMP_DIR+'plot_temp.png',
                       fit_lorentz = False,
                       sample_name = dataset_list.sample_name)


      def plot( self, dataset):
          '''
           Method to create one plot in print quality
          '''
          print 'PrintdDatasetDialog.py: Entry plot'
          session                = self.main_window.active_session
          session.picture_width  = str(int(self.width))
          session.picture_height = str(int(self.width/1.414))
          window                 = self.main_window

          window.plot( session,
                       [dataset],
                       session.active_file_name,
                       dataset.short_info,
                       [object.short_info for object in dataset.plot_together],
                       main_window.errorbars, 
                       output_file = session.TEMP_DIR+'plot_temp.png',
                       fit_lorentz = False)



          
    


import main_window
