#-*- coding: utf8 -*-
'''
  Module for file reading and writing. Defines general file reader
  and writer objects which decide, which plugin to use by file
  postfix and text.
  Basic read/write classes are defined in baseread/basewrite module.
  
  For use in external programs the main instance of baseread.ReaderProxy
  is created and can be used as::
    
    from plotpy.fio import reader
    data=reader.open('your_file.name')
'''

from baseread import ReaderProxy


__all__=['reader']


############## Define the global reader instance ###########
reader=ReaderProxy()

