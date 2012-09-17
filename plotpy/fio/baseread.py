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
import pkgutil
from glob import glob
from fnmatch import fnmatch
from cPickle import dumps, loads
from time import time, sleep
import gzip
import numpy

from plotpy.info import __version__
from plotpy.message import *
try:
  from cStringIO import StringIO
except ImportError:
  from  StringIO import StringIO

# multiprocessing imports, only work on python 2.6+
try:
  from multiprocessing import Pool, Queue
  import signal
  import atexit
  USE_MP=True
except ImportError:
  USE_MP=False
READ_MDS=True

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
  parameter_units={}

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

  def _get_keywords(self):
    '''
      Return a help string for the allowed keywords of an insance.
    '''
    output=''
    for key, value in sorted(self.parameters.items()):
      output+='%16s: %r'%(key, value)
      if key in self.parameter_units:
        output+=' %s\n'%self.parameter_units[key]
      else:
        output+='\n'
    print output

  pfile=property(_get_pfile)
  keywords=property(_get_keywords, doc='Print information on keywords, only for interactive use')

  def open(self, filename, mp_queue=None, **kwds):
    """
      Open a file with this reader. 
      
      Keywords depend on the reader subclass, see instances.keywords
      attribute for more information.
      
      :param filename: File name to open or open file object to read from
    """
    start=time()
    self._messages=mp_queue
    if mp_queue:
      self._filename=filename
    if isinstance(filename, basestring):
      self.origin=os.path.split(os.path.abspath(filename))
    else:
      self.origin=os.path.split(os.path.abspath(filename.name))
    self.info(self.name+'-Reading')
    self._set_params(kwds)
    self._read_file(filename)
    checksum=hash(self.raw_data)
    result=self._check_mds(filename, checksum)
    if result is not None:
      return result
    result=self.read()
    if result is None:
      return None
    self.info(self.name+'-Success', progress=100)
    result=FileData(result, self.session, self.origin, checksum)
    readtime=time()-start
    if readtime>1.:
      self.info('Storing as .mds for faster readout')
      result.save_snapshot(filename)
    return result

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

  def _check_mds(self, filename, checksum):
    if not READ_MDS:
      return None
    if os.path.exists(filename+'.mds'):
      dumpstr=open(filename+'.mds', 'rb').read()
    elif os.path.exists(filename+'.mds.gz'):
      dumpstr=gzip.open(filename+'.mds.gz', 'rb').read()
    else:
      return None
    try:
      dumpobj=loads(dumpstr)
    except ImportError:
      return None
    if not (type(dumpobj) is dict and 'checksum' in dumpobj):
      return None
    if dumpobj['checksum']!=checksum:
      # file content has changed
      return None
    if dumpobj['version']!=__version__:
      # plotpy version has changed (to make sure corrected reader code is used)
      return None
    self.info('Restore from .mds file, to reload use -rd option')
    return dumpobj['data']

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
  checksum=0

  def __init__(self, items=[], session=None, origin=(u"", u""), checksum=0):
    list.__init__(self, items)
    self.origin=origin
    self.session=session
    self.checksum=checksum

  def __repr__(self):
    return "FileData(items=%s, \n         origin=%s)"%(list.__repr__(self), repr(self.origin))

  def get_approx_size(self):
    '''
      Return the approximate size of all containing datasets.
    '''
    output=0
    for item in self:
      output+=item.get_approx_size()
    return output

  def save_snapshot(self, filename=None, extension='.mds'):
    size=self.get_approx_size()
    if filename is None:
      filename=os.path.join(self.origin)+extension
    else:
      filename+=extension
    if (size/1024**2)>20 and not filename.endswith('.gz'):
      filename+='.gz'
    dumpobj={
            'version': __version__,
            'session': self.session,
            'origin':  self.origin,
            'multiplots': False,
            'data': self,
            'checksum': self.checksum,
             }
    dumpstr=dumps(dumpobj)
    if filename.endswith('.gz'):
      gzip.open(filename, 'wb').write(dumpstr)
    else:
      open(filename, 'wb').write(dumpstr)


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
  '''
    Abstract handling of file readout using all readers available in the plotpy.fio
    package. Can be used to retrieve information on the supported file types,
    get a fitting reader for a given file name/extension or to automatically
    read a list of given files (with optional multiprocessing).
        
    The important attributes/methods are:
      open(files): Open the given files with a fitting reader 
                   and return a list of FileData objects.
         patterns: A dictionary with glob patterns as keys and 
                   lists of associated readers as values.
         sessions: As patterns but with session names as keys.
            types: Same as patterns.keys()
    kwds_callback: A function taking (reader, path, name) as input
                   which get's called if a reader supports keyword
                   arguments to return a dictionary of those arguments
                   e.g. to give the user an interface to input these
                   arguments.
            
    Using object['name.extension'] can be used to get the best 
    fitting reader for the given filename or glob pattern.
    
    This could look as follows in a user script:
      from plotpy.fio import reader
      my_reader=reader['*.my_type']
      for my_files in my_list:
        data=my_reader.open(my_file)
  '''
  kwds_callback=None # callback function that can be used to retrieve keywords for readers

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
    for ignore, name, ispackage in pkgutil.iter_modules([package_dir]):
      if ispackage or name in ["baseread", "basewrite"]:
        continue
      try:
        modi=__import__("plotpy.fio."+name, fromlist=[name])
      except Exception, error:
        warn("Could not import module %s,\n %s: %s"%(name, error.__class__.__name__, error))
        continue
      modules.append(modi)
    readers=[]
    for modi in modules:
      items=[item[1] for item in modi.__dict__.items() if not item[0].startswith("_")]
      readers_i=filter(lambda item: type(item) is type
                                     and item not in [Reader, TextReader, BinReader]
                                     and Reader in recbase(item)
                                     , items)
      readers+=readers_i
    for reader in [Reader, TextReader, BinReader]:
      if reader in readers:
        readers.remove(reader)
    self._set_readers(readers)
    if USE_MP:
      global _pool, _queue
      _queue=Queue()
      _pool=Pool(initializer=_init_worker, initargs=[_queue])
      atexit.register(_cleanup)

  def __repr__(self):
    output=object.__repr__(self)[:-1]
    output+=' with %i connected readers>'%len(self._readers)
    return output

  def __getitem__(self, name):
    '''
      Return the best matching reader for a given file name or glob pattern.
    '''
    readers=self._match(name)
    if len(readers)>0:
      return readers[0]
    else:
      return None

  def _set_readers(self, readers, prioritys=None):
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

  def open(self, files):
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
        path, name=os.path.split(os.path.abspath(filename.name))
      else:
        path, name=os.path.split(os.path.abspath(filename))
      readers=self._match(name.lower())
      kwds=self._get_kwds(readers[0], path, name)
      i=0
      if USE_MP:
        # send to worker thread
        results.append(_pool.apply_async(_open, args=(readers[0], filename), kwds=kwds))
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
            # if this reader could open the file, _promote it
            # to a higher rank
            self._promote(readers[i])
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
        info(u'Some files could not be read, trying alternatives', group=u'Reading files',
             numitems=len([ignore for ignore in results if ignore is None]))
        # the MP variant of changing the reader is quite hackish....
        for j, filename, result in zip(range(len(files)), files, results):
          if result is None:
            path, name=os.path.split(os.path.abspath(filename))
            readers=self._match(name.lower())
            if len(readers)==1:
              continue
            i=0
            while result is None and i<len(readers):
              kwds=self._get_kwds(readers[i], path, name)
              # if the reader did not succeed, try another
              # who is associated to the same file type
              result=readers[i].open(filename, **kwds)
              i+=1
              if result is not None:
                # if this reader could open the file, _promote it
                # to a higher rank
                self._promote(readers[i])
                results[j]=result
    info(u'Finished!', group=u'reset')
    output=filter(lambda item: item is not None, results)
    return output

  def _match(self, name):
    '''
      Find all readers, whos glob pattern matches the
      given file name.
    '''
    matching_readers=[]
    for pattern, readers in self.patterns.items():
      if fnmatch(name, pattern) or fnmatch(name, pattern+'.gz'):
        matching_readers+=readers
    matching_readers.sort(cmp=lambda a, b: cmp(self._prioritys[b],
                                              self._prioritys[a]))
    return matching_readers

  def _promote(self, reader, value=1):
    self._prioritys[reader]+=value

  def _get_kwds(self, reader, path, name):
    if reader.parameters=={} or self.kwds_callback is None:
      return {}
    else:
      return self.kwds_callback(reader, path, name)
