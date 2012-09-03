#-*- coding: utf8 -*-
'''
  Define basic reader classes that should be used for all data readout.
'''

import os
from glob import glob
from fnmatch import fnmatch
import gzip
#try:
  #from cStringIO import StringIO
#except ImportError:
  #from  StringIO import StringIO
try:
  from multiprocessing import Pool
  USE_MP=True
except ImportError:
  USE_MP=False


class Reader(object):
  """
    Basic class for data file readers. Loads and caches file binary
    data. Files with .gz extenstion get automatically unpacked.
  """

  name=u"Reader"
  description=u""
  glob_patterns=[]

  # additional parameters that can be given to the open function
  # with their default values
  parameters={}

  _data=None
  origin=("", "")
  _max_len_pprint=60

  def __repr__(self):
    return u"<%s for %s>"%(self.__class__.__name__, ";".join(self.glob_patterns))

  def _get_pfile(self):
    """
      Return nice representation of filename cropping folder if it is too long.
    """
    path, name=self.origin
    fullname=os.path.join(path, name)
    if len(fullname)>self._max_len_pprint:
      return "...%s"%fullname[len(fullname)-self._max_len_pprint-3:]
    else:
      return fullname

  pfile=property(_get_pfile)

  def open(self, file, **kwds):
    """
      Open a file with this reader. File can be a file like
      object, gzip compresst or normal datafile.
      
      Keywords depend on the reader subclass, see the
      parameters attribute for available keywords and
      their default values. 
    """
    self.origin=os.path.split(os.path.abspath(file))
    print "Reading", self.pfile, "with %s"%self.__class__.__name__
    self._set_params(kwds)
    self._read_file(file)
    result=self.read()
    if result is None:
      return None
    return FileData(result, self.origin)

  def _read_file(self, file):
    if hasattr(file, "read"):
      self._data=file.read()
    elif file.lower().endswith(".gz"):
      self._data=gzip.open(file, "rb").read()
    else:
      self._data=open(file, "rb").read()

  def _set_params(self, kwds):
    for key in kwds.keys():
      if not key in self.parameters:
        raise ValueError, "%s is not a valid parameter"%key
    for param, default in self.parameters.items():
      if param in kwds:
        # convert to default type
        parameter=type(default)(kwds[param])
      else:
        parameter=default
      setattr(self, param, parameter)

  def read(self):
    raise NotImplementedError, "Reader can not be used directly, create a subclass defining a read method!"

  def check(self):
    return True

class TextReader(Reader):
  """
    Advanced reader class converting raw binary file
    data to unicode and provinding simple sting to
    data conversion methods.
  """
  encoding="utf8"

  def _read_file(self, file):
    if hasattr(file, "read"):
      raw_data=file.read()
    elif file.lower().endswith(".gz"):
      raw_data=gzip.open(file, "rb").read()
    else:
      raw_data=open(file, "rb").read()
    self._data=unicode(raw_data, encoding=self.encoding)

  def read(self):
    raise NotImplementedError, "TextReader can not be used directly, create a subclass defining a read method!"


class BinReader(Reader):
  """
    Advanced reader class providing data conversion for
    binary data types.
  """

  def read(self):
    raise NotImplementedError, "BinReader can not be used directly, create a subclass defining a read method!"

class FileData(list):
  """
    Result from reading a file with a Reader derived class.
  """
  def __init__(self, items=[], origin=("", "")):
    list.__init__(self, items)
    self.origin=origin

  def __repr__(self):
    return "FileData(items=%s, \n         origin=%s)"%(list.__repr__(self), repr(self.origin))

def _open(file, **kwds):
  print file

class ReaderProxy(object):

  def __init__(self, readers):
    self.set_readers(readers)
    if USE_MP:
      self._pool=Pool()

  def set_readers(self, readers, prioritys=None):
    if prioritys is None:
      prioritys=[5 for ignore in readers]
    priority_dict={}
    readers=[reader() for reader in readers]
    for i, reader in enumerate(readers):
      priority_dict[reader]=prioritys[i]
    self._prioritys=priority_dict
    self._readers=readers
    self.patterns={}
    for reader in readers:
      for pattern in reader.glob_patterns:
        if pattern in self.patterns:
          self.patterns[pattern].append(reader)
        else:
          self.patterns[pattern]=[reader]

  def open(self, files, **kwds):
    if not hasattr(files, "__iter__"):
      # input is not a list of files
      files=[files, ]
    results=[]
    for file in files:
      path, name=os.path.split(os.path.abspath(file))
      if not os.path.exists(file):
        raise IOError, "File %s does not exist"%file
      reader=self.match(name.lower())[0]
      results.append(reader.open(file))
    return results

  def match(self, name):
    matching_readers=[]
    for pattern, readers in self.patterns.items():
      if fnmatch(name, pattern):
        matching_readers+=readers
    matching_readers.sort(cmp=lambda a, b: cmp(self._prioritys[b],
                                              self._prioritys[a]))
    return matching_readers
