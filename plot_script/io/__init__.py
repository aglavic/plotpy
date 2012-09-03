#-*- coding: utf8 -*-
'''
  Module for file reading and writing. Defines general file reader
  and writer objects which decide, which plugin to use by file
  postfix and text.
  Basic read/write classes are defined in baseread/basewrite module.
'''

import os
from baseread import ReaderProxy, Reader, TextReader, BinReader

package_dir=os.path.split(os.path.abspath(__file__))[0]

__all__=['reader']


############## Import all submodules to search for Readers ###########
def recbase(check_class):
  '''
    Find bases of a class recursively.
  '''
  output=[]
  for item in check_class.__bases__:
    if item is not object:
      output+=recbase(item)
  return output+[check_class]

modules=[]
for name in os.listdir(package_dir):
  if name.endswith(".py") or name.endswith(".pyc") or name.endswith(".pyo"):
    modi=name.rsplit(".py",1)[0]
    if not (modi in modules or modi.startswith("_") 
            or modi in ["baseread", "basewrite"]):
      modules.append(modi)
modules.sort()
readers=[]
for module in modules:
  try:
    modi=__import__("io."+module, fromlist=[module], level=1)
  except Exception, error:
    print "Could not import module %s, %s: %s"%(module, error.__class__.__name__, error)
    continue
  items=[item[1] for item in modi.__dict__.items() if not item[0].startswith("_")]
  readers_i=filter(lambda item: Reader in recbase(item), items)
  readers+=readers_i
for reader in [Reader, TextReader, BinReader]:
  if reader in readers:
    readers.remove(reader)

############## Define the global reader instance ###########
reader=ReaderProxy(readers)