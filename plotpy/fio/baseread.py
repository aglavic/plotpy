#-*- coding: utf8 -*-
'''
  Define basic reader classes that should be used for all data readout.
  Each reader supports the open method taking a file name of raw or
  gzip compressed data or a file object with raw or gzip compressed
  data.
  The ReaderProxy object locates all readers defined in the fio package
  and selects the appropriate one using glob patterns.
'''

import os
import sys
from glob import glob
from fnmatch import fnmatch
import gzip
import numpy
from plotpy.message import *
from fileinput import filename
try:
  from cStringIO import StringIO
except ImportError:
  from  StringIO import StringIO
try:
  from multiprocessing import Pool, Queue
  from time import sleep
  import signal
  import atexit
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
  session='generic'

  # additional parameters that can be given to the open function
  # with their default values
  parameters={}

  _data=None
  origin=("", "")
  _max_len_pprint=60
  _messages=None

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

  def open(self, filename, mp_queue=None, **kwds):
    """
      Open a file with this reader. 
      
      Keywords depend on the reader subclass, see the
      parameters attribute for available keywords and
      their default values. 
      
      :param filename: File name to open or open file object to read from
    """
    self._messages=mp_queue
    if mp_queue:
      self._filename=filename
    if type(filename) in [str, unicode]:
      self.origin=os.path.split(os.path.abspath(filename))
    else:
      self.origin=os.path.split(os.path.abspath(filename.name))
    self.info(self.name+'-Reading')
    self._set_params(kwds)
    self._read_file(filename)
    result=self.read()
    if result is None:
      return None
    self.info(self.name+'-Success', progress=100)
    return FileData(result, self.session, self.origin)

  def _read_file(self, filename):
    '''
      Read the raw data from the file.
    '''
    if type(filename) is file:
      if filename.name.endswith('.gz'):
        bindata=StringIO(filename.read())
        self.raw_data=gzip.GzipFile(fileobj=bindata, mode='rb').read()
      else:
        self.raw_data=filename.read()
    elif filename.lower().endswith(".gz"):
      self.raw_data=gzip.open(filename, "rb").read()
    else:
      self.raw_data=open(filename, "rb").read()

  def _set_params(self, kwds):
    '''
      Set object parameters according to keywords and default
      options set in self.parameters dictionary.
    '''
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

  def info(self, text=None, progress=0.):
    if self._messages is None:
      info(text, group='Reading files', item=self.origin[1], progress=progress)
    else:
      self._messages.put([self._filename, ['info', text, self.origin[1], progress]])

  def warn(self, text=None, progress=0.):
    if self._messages is None:
      warn(text, group='Reading files', item=self.origin[1], progress=progress)
    else:
      self._messages.put([self._filename, ['warn', text, self.origin[1], progress]])

  def error(self, text=None, progress=0.):
    if self._messages is None:
      error(text, group='Reading files', item=self.origin[1], progress=progress)
    else:
      self._messages.put([self._filename, ['error', text, self.origin[1], progress]])

  def lines2data(self, lines, sep=" ", dtype=float):
    '''
      Return columns of data from a list of liens.
    '''
    return numpy.array(map(lambda line: numpy.fromstring(line, sep=sep, dtype=dtype),
                           lines), dtype=dtype).transpose()

  def str2data(self, string, sep=" ", dtype=float):
    '''
      Return columns of data from a string consisting of only data
      containing lines.
    '''
    return self.lines2data(string.splitlines(), sep=sep, dtype=dtype)

  def save_lines2data(self, lines, sep=" "):
    raise NotImplementedError, 'Sorry'

class TextReader(Reader):
  """
    Advanced reader class converting raw binary file
    data to unicode and providing simple sting to
    data conversion methods.
  """
  encoding="utf8"

  def _read_file(self, filename):
    Reader._read_file(self, filename)
    self.text_data=unicode(self.raw_data, encoding=self.encoding)

  def read(self):
    raise NotImplementedError, "TextReader can not be used directly, create a subclass defining a read method!"

class BinReader(Reader):
  """
    Advanced reader class providing data conversion for
    binary data types.
  """

  def read(self):
    raise NotImplementedError, "BinReader can not be used directly, create a subclass defining a read method!"

  def _get_filelike(self):
    return StringIO(self.raw_data)

  raw_file=property(_get_filelike, doc='raw data as file like object')

class FileData(list):
  """
    Result from reading a file with a Reader derived class.
    The origin attribute stores the files path and name
    where the data was read from.
  """
  def __init__(self, items=[], session=None, origin=(u"", u"")):
    list.__init__(self, items)
    self.origin=origin
    self.session=session

  def __repr__(self):
    return "FileData(items=%s, \n         origin=%s)"%(list.__repr__(self), repr(self.origin))

# Multiprocessing helper functions
def _open(reader, filename, **kwds):
  return reader.open(filename, mp_queue=_open.q, **kwds)

_pool_on_load=False
def _cleanup():
  if _pool_on_load:
    # kill busy child processes on exit
    _pool.terminate()
  else:
    # close non-busy pool
    _pool.close()
  _pool.join()

def _init_worker(q):
  # make child processes ignore keyboard interrupt
  signal.signal(signal.SIGINT, signal.SIG_IGN)
  # store the given Queue object for use in _open function
  _open.q=q

class ReaderProxy(object):

  def __init__(self):
    ############## Import all fio submodules to search for Readers ###########
    package_dir=os.path.split(os.path.abspath(__file__))[0]
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
        modi=name.rsplit(".py", 1)[0]
        if not (modi in modules or modi.startswith("_")
                or modi in ["baseread", "basewrite"]):
          modules.append(modi)
    modules.sort()
    readers=[]
    for module in modules:
      try:
        modi=__import__("plotpy.fio."+module, fromlist=[module])
      except Exception, error:
        warn("Could not import module %s,\n %s: %s"%(module, error.__class__.__name__, error))
        continue
      items=[item[1] for item in modi.__dict__.items() if not item[0].startswith("_")]
      readers_i=filter(lambda item: type(item) is type
                                     and item not in [Reader, TextReader, BinReader]
                                     and Reader in recbase(item)
                                     , items)
      readers+=readers_i
    for reader in [Reader, TextReader, BinReader]:
      if reader in readers:
        readers.remove(reader)
    self.set_readers(readers)
    if USE_MP:
      global _pool, _queue
      _queue=Queue()
      _pool=Pool(initializer=_init_worker, initargs=[_queue])
      atexit.register(_cleanup)

  def set_readers(self, readers, prioritys=None):
    '''
      Collect information from reader classes.
    '''
    if prioritys is None:
      prioritys=[getattr(reader, 'priority', 5) for reader in readers]
    priority_dict={}
    instances=[]
    for i, reader in enumerate(readers):
      try:
        instances.append(reader())
      except Exception, error:
        warn('%s could not be initialized:\n%s: %s'%(reader.name,
                                                      error.__class__.__name__,
                                                      str(error)),
              group='Initializing Readers')
      else:
        priority_dict[instances[-1]]=prioritys[i]
    self._prioritys=priority_dict
    self._readers=instances
    self.patterns={}
    for reader in instances:
      for pattern in reader.glob_patterns:
        if pattern in self.patterns:
          self.patterns[pattern].append(reader)
        else:
          self.patterns[pattern]=[reader]

  def _get_types(self):
    glob_list=self.patterns.keys()
    glob_list.sort()
    return glob_list

  def _get_by_session(self):
    outdict={}
    for reader in self._readers:
      if reader.session in outdict:
        outdict[reader.session].append(reader)
      else:
        outdict[reader.session]=[reader]
    return outdict

  types=property(_get_types)
  sessions=property(_get_by_session)

  def open(self, files, **kwds):
    if USE_MP:
      global _pool_on_load
      _pool_on_load=True
    if not type(files) in [list, tuple]:
      # input is not a list of files
      files=[files, ]
    elif len(files)==0:
      return []
    results=[]
    for i, filename in enumerate(files):
      if not type(filename) in [str, unicode, file]:
        raise ValueError, "Can only read data from file objects or file names"
      if type(filename) is str:
        # encode non unicode names using stdin encoding
        files[i]=unicode(filename, sys.stdin.encoding)
    i=0
    while i<len(files):
      filename=files[i]
      i+=1
      if not (type(filename) is file or os.path.exists(filename)):
        files.pop(i-1)
        globbed_files=glob(filename)
        if len(globbed_files)==0:
          error(u"File %s does not exist"%filename, group=u'Checking Files')
          i-=1
        else:
          # add files to the list
          for newfile in reversed(sorted(globbed_files)):
            files.insert(i-1, newfile)
          i+=len(globbed_files)-1
    info(None, group=u'Reading files', numitems=len(files))
    for filename in files:
      if type(filename) is file:
        ignore, name=os.path.split(os.path.abspath(filename.name))
      else:
        ignore, name=os.path.split(os.path.abspath(filename))
      readers=self.match(name.lower())
      i=0
      if USE_MP:
        # send to worker thread
        results.append(_pool.apply_async(_open, args=(readers[i], filename), kwds=kwds))
      else:
        #try:
        results.append(readers[i].open(filename, **kwds))
        #except Exception, err:
        #  # don't stop on read exceptions
        #  error(err.__class__.__name__+': '+str(err), group=u'Reading files', item=filename)
        #  results.append(None)
        i+=1
        while results[-1] is None and i<len(readers):
          # if the reader did not succeed, try another
          # who is associated to the same file type
          results[-1]=readers[i].open(filename, **kwds)
          if results[-1] is not None:
            # if this reader could open the file, promote it
            # to a higher rank
            self.promote(readers[i])
    if USE_MP:
      fetched_results=[]
      fetched_messages=dict((name, []) for name in files)
      for result, name in zip(results, files):
        # To prevent multiple processes to send messages in arbitrary order
        # they are collected within the process and printed out when retrieving the data.
        while not result.ready():
          # read communication channel and make sure only info from current
          # process is transmitted
          if not _queue.empty():
            item=_queue.get()
            fetched_messages[item[0]].append(item[1])
          if fetched_messages[name]!=[]:
            message=fetched_messages[name].pop(0)
            if message[0]=='info':
              info(message[1], group=u'Reading files', item=message[2], progress=message[3])
            elif message[0]=='warn':
              warn(message[1], group=u'Reading files', item=message[2], progress=message[3])
            else:
              error(message[1], group=u'Reading files', item=message[2], progress=message[3])
          else:
            sleep(0.001) # make sure parent process is not consuming too much resources
        while not _queue.empty():
          item=_queue.get()
          fetched_messages[item[0]].append(item[1])
        for message in fetched_messages[name]:
          if message[0]=='info':
            info(message[1], group=u'Reading files', item=message[2], progress=message[3])
          elif message[0]=='warn':
            warn(message[1], group=u'Reading files', item=message[2], progress=message[3])
          else:
            error(message[1], group=u'Reading files', item=message[2], progress=message[3])
        try:
          data=result.get()
        except Exception, err:
          # don't stop on read exceptions
          error(err.__class__.__name__+': '+str(err), group=u'Reading files', item=filename)
          data=None
        fetched_results.append(data)
      results=fetched_results
      _pool_on_load=False
      if None in results:
        # the MP variant of changing the reader is quite hackish....
        demote_readers=set()
        missed_files=[]
        for filename, result in zip(files, results):
          if result is None:
            missed_files.append(filename)
            ignore, name=os.path.split(os.path.abspath(filename))
            demote_readers.add(self.match(name.lower())[0])
        for reader in demote_readers:
          self.demote(reader)
        info(u'Retry other reader', group=u'reset')
        return filter(lambda item: item is not None, results)+self.open(missed_files)
    info(u'Finished!', group=u'reset')
    output=filter(lambda item: item is not None, results)
    return output

  def match(self, name):
    matching_readers=[]
    for pattern, readers in self.patterns.items():
      if fnmatch(name, pattern) or fnmatch(name, pattern+'.gz'):
        matching_readers+=readers
    matching_readers.sort(cmp=lambda a, b: cmp(self._prioritys[b],
                                              self._prioritys[a]))
    return matching_readers

  def promote(self, reader, value=1):
    self._prioritys[reader]+=value

  def demote(self, reader, value=1):
    self._prioritys[reader]-=value

