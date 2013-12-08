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
import pkgutil
from glob import glob
from fnmatch import fnmatch
from cPickle import dumps, loads
from time import time, sleep
import gzip
import numpy

from plotpy.info import __version__
from plotpy.message import info, warn, error, in_encoding
try:
  from cStringIO import StringIO
except ImportError:
  from  StringIO import StringIO

# multiprocessing imports, only work on python 2.6+
try:
  from multiprocessing import Pool, Queue
  import signal
  import atexit
  USE_MP=False
except ImportError:
  USE_MP=False
READ_MDS=True

class Reader(object):
  """
    Basic class for data file readers. Loads and caches file binary
    data. Files with .gz extensions get automatically unpacked.
    The class has no __init__ method, this should be used for derived
    readers to e.g. import non standard libraries or for setup purpose.
    Strings should always be given as unicode.
    
    A defived class should supply at least the following attributes/methods:
    
      ===================== ============================================
      name                  Identifier for the reader class
      description           Information text on the type of file the 
                            reader supports
      glob_parterns         List of file patterns the reader supports
      session               The default session name for the type
      read(self)            The method to be called when the raw
                            data has been read.               
      ===================== ============================================
    
    Additional class attributes that can be overwritten by children:
    
      ===================== ============================================
      parameters            List of (name, default) tuples of 
                            additional parameters needed by the reader
                            to treat the data.
                            
                            The reader can access each parameter as
                            attribute when *read* is called.
                            E.g. for the item ('param1', 5.3) the reader
                            could use self.param1 to get it's value.
                            The name needs to be a valid python 
                            identifier (no spaces etc.).
                            
                            The type is determined by the default value
                            so it is not possible to supply an float
                            when the default was integer. A tuple of
                            strings can be used to give a selection,
                            where the first parameter is the default.
                            
      parameter_units       Dictionary containing phisical units of 
                            the parameters. Not all parameters need
                            to be available. The special case of unit
                            'file(* .fil)' is used in the GUI to treat
                            a text input as filename with an according
                            dialog. 
      parameter_description Short info text for each parameter, which
                            is shown when the mouse hovers the input.
      store_mds             If set to False the data will not be saved
                            to a .mds file after readout.
      allow_multiread       If set to True the reader must support
                            the readout of multiple files, e.g. to
                            sum up several images.
      ===================== ============================================
  """

  name=u"Reader"
  description=u""
  glob_patterns=[]
  session='generic'

  parameters=[]
  parameter_units={}
  parameter_description={}

  _data=None
  store_mds=True
  origin=("", "")
  _max_len_pprint=60
  _messages=None
  allow_multiread=False

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
      Return a help string for the allowed keywords of an instance.
    '''
    output=''
    for key, value in self.parameters:
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
    self.unread_files=[]
    start=time()
    self._messages=mp_queue
    if isinstance(filename, basestring):
      self._filename=filename
      self.origin=os.path.split(os.path.abspath(filename))
    elif hasattr(filename, '__iter__'):
      self._filename=filename[0]
      if not self.allow_multiread:
        self.warn('%s reader does not support multiple file readouts'%self.__class__.__name__)
        return None
      self.origin=os.path.split(os.path.abspath(filename[0]))
      # set first file for readout
      self.unread_files=filename[1:]
      filename=filename[0]
    else:
      self._filename=filename.name
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
    if readtime>1. and self.store_mds:
      self.info('Storing as .mds for faster readout')
      result.save_snapshot(filename)
    return result

  def _read_file(self, filename):
    '''
      Read the raw data from the file.
    '''
    if hasattr(filename, 'read') and hasattr(filename, 'name'):
      if filename.name.lower().endswith('.gz'):
        bindata=StringIO(filename.read())
        self.raw_data=gzip.GzipFile(fileobj=bindata, mode='rb').read()
      else:
        self.raw_data=filename.read()
    elif filename.lower().endswith(".gz"):
      self.raw_data=gzip.open(filename, "rb").read()
    else:
      self.raw_data=open(filename, "rb").read()

  def next(self):
    '''
      For multifile read the next method reads the next file.
      Intentionally there is no way to iterate over all 
      files as this could lead to readers which access
      the same file data multiple times.
    '''
    if len(self.unread_files)==0:
      raise StopIteration, "unread files list is empty"
    filename=self.unread_files.pop(0)
    self._read_file(filename)
    return filename

  def _check_mds(self, filename, checksum):
    '''
      Check if a corresponding .mds file exists before
      evaluating the file data.
    '''
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
    self.info('Restore from .mds file, to reload from file use -rd option')
    return dumpobj['data']

  def _set_params(self, kwds):
    '''
      Set object parameters according to keywords and default
      options set in self.parameters dictionary.
    '''
    parnames=[item[0] for item in self.parameters]
    for key in kwds.keys():
      if not key in parnames:
        raise ValueError, "%s is not a valid parameter"%key
    for param, default in self.parameters:
      tp=type(default)
      if param in kwds:
        # convert to default type
        parameter=kwds[param]
      else:
        parameter=default
      if tp is tuple:
        if type(parameter) is tuple:
          parameter=parameter[0]
        if type(parameter) is int:
          parameter=default[parameter]
      elif tp is str:
        if not type(parameter) is unicode:
          parameter=unicode(parameter, encoding=in_encoding)
      else:
        # convert to appropriate type
        parameter=tp(parameter)
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
    When read is called the data is available as self.text_data.
    
    See Reader documentation for details.
  """
  encoding="utf8"

  def _read_file(self, filename):
    Reader._read_file(self, filename)
    self.text_data=unicode(self.raw_data, encoding=self.encoding)

  def read(self):
    raise NotImplementedError, "TextReader can not be used directly, create a subclass defining a read method!"

  def _get_filelike(self):
    return StringIO(self.text_data)

  text_file=property(_get_filelike, doc='text data as file like object')

class BinReader(Reader):
  """
    Advanced reader class providing data conversion for
    binary data types.
    When read is called the data is available as self.raw_data,
    and a filelike object as self.raw_file.
    
    See Reader documentation for details.
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
    
    ============== ===================================================
      open(files)  Open the given files with a fitting reader 
                   and return a list of FileData objects.
         patterns  A dictionary with glob patterns as keys and 
                   lists of associated readers as values.
         sessions  As patterns but with session names as keys.
            types  Same as patterns.keys()
    kwds_callback  A function taking (reader, path, name) as input
                   which get's called if a reader supports keyword
                   arguments to return a dictionary of those arguments
                   e.g. to give the user an interface to input these
                   arguments.
    ============== ===================================================
            
    Using object['name.extension'] can be used to get the best 
    fitting reader for the given filename or glob pattern.
    
    This could look as follows in a user script::
    
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
    '''
      Load a list of files by automatically choosing the appropriate
      reader according to the file pattern. Readers with the same
      patterns are tried one after another and increased in
      priority after on successful read attempt. 
    '''
    if USE_MP:
      global _pool_on_load
      _pool_on_load=True
    if not hasattr(files, '__iter__'):
      # input is not a list of files
      files=[files, ]
    elif len(files)==0:
      return []
    results=[]
    for i, filename in enumerate(files):
      if not type(filename) in [str, unicode, file, list]:
        raise ValueError, "Can only read data from file objects, lists or file names"
      if type(filename) is str:
        # encode non unicode names using stdin encoding
        files[i]=unicode(filename, in_encoding)
      if type(filename) is list:
        files[i]=map(os.path.abspath, filename)
    i=0
    while i<len(files):
      filename=files[i]
      i+=1
      if not (type(filename) is file
              or (type(filename) is list and all(map(os.path.exists, filename)))
              or os.path.exists(filename)):
        files.pop(i-1)
        globbed_files=glob(filename)
        if len(globbed_files)==0:
          # check if the string defines a set of files and if
          # this is the case create a list of these files
          multifile=self._check_multifile(filename)
          if not multifile:
            error(u"File %s does not exist"%filename, group=u'Checking Files')
            i-=1
          else:
            files.insert(i-1, multifile)
        else:
          # add files to the list
          for newfile in reversed(sorted(globbed_files)):
            files.insert(i-1, newfile)
          i+=len(globbed_files)-1
    info(None, group=u'Reading files', numitems=len(files))
    first_names=[] # list of string names, first if file list
    for filename in files:
      if type(filename) is file:
        path, name=os.path.split(os.path.abspath(filename.name))
        first_names.append(filename.name)
      elif type(filename) is list:
        path, name=os.path.split(os.path.abspath(filename[0]))
        first_names.append(filename[0])
      else:
        path, name=os.path.split(os.path.abspath(filename))
        first_names.append(filename)
      readers=self._match(name.lower())
      kwds=self._get_kwds(readers[0], path, name)
      if USE_MP:
        # send to worker thread
        results.append(_pool.apply_async(_open, args=(readers[0], filename), kwds=kwds))
      else:
        #try:
        results.append(readers[0].open(filename, **kwds))
        #except Exception, err:
        #  # don't stop on read exceptions
        #  error(err.__class__.__name__+': '+str(err), group=u'Reading files', item=filename)
        #  results.append(None)
        i=1
        while results[-1] is None and i<len(readers):
          kwds=self._get_kwds(readers[0], path, name)
          # if the reader did not succeed, try another
          # who is associated to the same file type
          results[-1]=readers[i].open(filename, **kwds)
          if results[-1] is not None:
            # if this reader could open the file, _promote it
            # to a higher rank
            self._promote(readers[i])
          else:
            i+=1
    if USE_MP:
      fetched_results=[]
      fetched_messages=dict((name, []) for name in first_names)
      for result, name in zip(results, first_names):
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
        for j, firstname, filename, result in zip(range(len(files)),
                                                  first_names, files, results):
          if result is None:
            path, name=os.path.split(os.path.abspath(firstname))
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
    matching_readers.sort(cmp=lambda a, b: cmp(self._prioritys[b], self._prioritys[a]))
    return matching_readers

  def _check_multifile(self, filestring):
    '''
      Generate a list of files from a pattern string if possible.
      There are two types of patterns, - separated and + integer.
      Example:
        file.bla-file5.bla (create a list of files between file.bla
                            and file5.bla)
        file.bla-file3.bla-file5.bla (create a list containing only
                            the three given names)
        file.bla+5         (create a list with file.bla and the 5
                            following files of the same type)
    '''
    # check if name consists of filenames separated
    # by - and if all these files exist
    if filestring.lower().endswith('.gz'):
      psplit=filestring.rsplit('.', 1)[0].rsplit('.', 1)
      postfix=filestring[-3:]
    else:
      psplit=filestring.rsplit('.', 1)
      postfix=''
    if len(psplit)==2:
      postfix=psplit[1]+postfix
      minus_split=psplit[0].split('.%s-'%postfix)
      flist=[os.path.abspath(mfile+'.'+postfix) for mfile in minus_split]
      not_found=False
      for filename in flist:
        if not os.path.exists(filename):
          not_found=True
          break
      if not not_found:
        if len(flist)==2:
          # get all files between the given names
          path, ignore=os.path.split(flist[0])
          glist=glob(os.path.join(path, '*.'+postfix))
          glist.sort()
          start_idx=glist.index(flist[0])
          end_idx=glist.index(flist[1])
          return glist[start_idx:end_idx+1]
        else:
          return flist
    # check if name is an existing file proceded with + and an integer
    # this defines to read this file and the next integer ones
    psplit=filestring.rsplit('+', 1)
    if len(psplit)==2:
      if not (psplit[1].isdigit() and os.path.exists(psplit[0])):
        return None
      path, ignore=os.path.split(psplit[0])
      if psplit[0].lower().endswith('.gz'):
        postfix=psplit[0][:-3].rsplit('.', 1)[1]+psplit[0][-3:]
      else:
        postfix=psplit[0].rsplit('.', 1)[1]
      glist=glob(os.path.join(path, '*.'+postfix))
      glist.sort()
      start_idx=glist.index(psplit[0])
      end_idx=start_idx+int(psplit[1])
      flist=[os.path.abspath(item) for item in glist[start_idx:end_idx+1]]
      return flist
    return None

  def _promote(self, reader, value=1):
    self._prioritys[reader]+=value

  def _get_kwds(self, reader, path, name):
    if reader.parameters==[]:
      return {}
    else:
      if self.kwds_callback is None:
        info(u'''No kwds_callback function defined!
    %s reader can't be customized without parameters.'''%reader.name,
             group=u'Reading files')
        return {}
      return self.kwds_callback(reader, path, name)
