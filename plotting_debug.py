# -*- encoding: utf-8 -*-
'''
  Module to log all interesting events in a debugging session. With the --debug and --logall option even function calls
  are stored in the log file.
  
  CAREFUL: The --logall option can create a huge amount of data, be sure not to reproduce errors rapidly after starting
           the program to let the file size stay at a minimum. (a 1MB log file just after starting the Program is not 
           unlikely)
'''

import logging
import sys, os
from glob import glob

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "None"
__version__ = "0.7.4.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

logger=logging

class RedirectOutput(object):
  '''
    Class to redirect all print statements to the statusbar when useing the GUI.
  '''
  second_output=None

  def __init__(self, obj, connection, connect_on_keyword=[]):
    '''
      Class consturctor.
      
      @param plotting_session A session object derived from GenericSession.
    '''
    self.file_object=obj
    self.connection=connection
    self.connect_on_keyword=connect_on_keyword
    self.buffer=""

  def write(self, string):
    '''
      Add content.
      
      @param string Output string of stdout
    '''
    self.buffer+=string
    if "\n" in string:
      connection=self.connection
      for keyword, connect in self.connect_on_keyword:
        if keyword in self.buffer:
          connection=connect
      connection(self.buffer.replace("\n", ''))
      self.buffer=""
    #self.file_object.write(string)
  
  def flush(self):
    '''
      Show last content line in statusbar.
    '''
    connection=self.connection
    for keyword, connect in self.connect_on_keyword:
      if keyword in self.buffer:
        connection=connect
    connection(self.buffer.replace("\n", ''))
    self.buffer=""
    self.file_object.flush()
  
  def fileno(self):
    return self.file_object.fileno()

class LogFunction(object):
  '''
    A class that can be called as if it would be a function.
    When constructed a function is supplied, for every call to the object
    the function gets called and a line is written to a log file.
    
    Very useful to trace calls to specific functions or even all functions of
    some modules of interest.
  '''
  log_function=True
  
  def __init__(self, function, overwrite_name=None):
    '''
      Construct the module by connecting the function.
      
      @param name Name written in the log for every function call.
      @param function The function to be used.
    '''      
    if overwrite_name:
      self.name=overwrite_name
      logger.debug('Logging %s' % self.name)
    else:
      self.name=function.__name__
      logger.debug('Logging %s' % function.__module__+'.'+function.__name__)
    self.function=function
  
  def __call__(self, *params, **opts):
    '''
      Write a function call with its parameters and options to
      the log file.
    '''
    # use this call to check if an exception has been found
    # this only works if this function is called in the "except" block.
    exc_info=sys.exc_info()[1]
    if exc_info:
      logger.warning('Cought exception %s' % str(exc_info))
    return_value=None
    write_string=self.name + "("
    i=0
    # add parameter information
    for i, param in enumerate(params):
      if i!=0:
        write_string+=", "
      write_string+=repr(param)
    # add optional parameter informations
    for j, item in enumerate(opts.items()):
      if j+i!=0:
        write_string+=", "
      write_string+=item[0] + "=" + repr(item[1])
    # write the function call with maximum of 150 characters 
    if len(write_string)>150:
      write_string=write_string[:150]+'...'
    write_string+=")"
    logger.debug(write_string)
    return self.function(*params, **opts)

def single_call_log(function, class_name):
  def tmpfunc(*params, **options):
    logger.debug(class_name+'('+str(params)+str(options)+')')
    return function(*params, **options)
  return tmpfunc

def create_log_class(old_class):
  '''
    Create a new class where all method calls are logged.
    
    Uses online attribute lookup to create a function which loggs the function inputs.
  '''
  class OutputClass(old_class, object):
    def __getattribute__(self, attribute):
      if 'method' in str(type(old_class.__getattribute__(self, attribute))):
        return single_call_log(old_class.__getattribute__(self, attribute), old_class.__name__+'.'+attribute)
      else:
        return old_class.__getattribute__(self, attribute)
      
  return OutputClass

class LogClass:
  '''
    Class that creates instances of other classes with logging possibilities.
  '''
  
  def __init__(self, old_class):
    '''
      Store the old class in this object
    '''
    #self.old_class=old_class
    #self.old_class_functions=[]
    #class_name=old_class.__name__
    #logger.debug('Logging Class %s' % old_class.__module__+'.'+old_class.__name__)
    #logging.disable(logging.INFO)
    #keys=old_class.__dict__.keys()
    #for item in keys:
      #if item.startswith('_'):
        #keys.remove(item)
    #for key in keys:
      #if 'instancemethod' in str(type(getattr(old_class, key))):
        #method=getattr(old_class, key)
        #setattr(old_class, key, LogFunction(method, overwrite_name=class_name+'.'+method.__name__))
      #else:
        #pass
    #logging.disable(None)
  #
  #def __call__(self, *params, **opts):
    #'''
      #Call the class constructor and log the call.
    #'''
    #write_string=self.old_class.__name__+'.__init__(self, '
    ## add parameter information
    #i=0
    #for i, param in enumerate(params):
      #if i!=0:
        #write_string+=", "
      #write_string+=repr(param)
    ## add optional parameter informations
    #for j, item in enumerate(opts.items()):
      #if j+i!=0:
        #write_string+=", "
      #write_string+=item[0] + "=" + repr(item[1])
    ## write the function call
    #write_string+=") -> "
    #new_class=self.old_class(*params, **opts)
    #logger.debug(write_string+repr(new_class))
    #return new_class

class EmptyClass:
  pass

def logon(module):
  '''
   Start logging function calls for all functions of one module.
   
   @param module A module whose function calls should be logged.
  '''
  # get all functions/build-in-function of the module not starting with underscore
  modfunctions=filter(lambda key: type(getattr(module, key)) in [type(logon), type(getattr)] and not key.startswith('_'),
                      module.__dict__.keys())
  modclasses=filter(lambda key: ('class' in str(type(getattr(module, key))) or \
                                "'type'" in str(type(getattr(module, key)))) and not key.startswith('_'),
                      module.__dict__.keys())
  for function_name in modfunctions:
    # get the function
    function=getattr(module, function_name)
    # replace the function by a LogFunction object
    # only replace if the function is originally defined in this module
    if function.__module__==module.__name__:
      setattr(module, function_name, LogFunction( function ))
  for cls_name in modclasses:
    cls=getattr(module, cls_name)
    # replace the class by a LogClass object
    # only replace if the function is originally defined in this module
    if cls.__module__==module.__name__:
      setattr(module, cls_name, create_log_class(cls))

def initialize(log_file, level='INFO', modules=[]):
  '''
    Start logging of all modules of the plot-script.
  '''
  global logger
  if level=='DEBUG':
    level=logging.DEBUG
  else:
    level=logging.INFO
  file_handle=logging.FileHandler(log_file, 'w')
  file_handle.setLevel(level)
  formatter = logging.Formatter("%(asctime)s %(levelname) 8s %(message)s")
  # add formatter to ch
  file_handle.setFormatter(formatter)  
  console_handle=logging.StreamHandler()
  console_handle.setLevel(logging.INFO)
  logger=logging.getLogger('plot')
  logger.setLevel(logging.DEBUG)
  logger.addHandler(console_handle)
  logger.addHandler(file_handle)
  sys.stdout=RedirectOutput(sys.stdout, logger.info)
  sys.stderr=RedirectOutput(sys.stderr, logger.error, connect_on_keyword=[('Warning', logger.warning)])
  if level==logging.DEBUG:
    # In complete debug mode function calls of defined modules get logged, too
    logger.debug("Beginning initialize logging for all modules...")
    sys.exc_clear=LogFunction(sys.exc_clear)
    for module in modules:
      if len(module.split('.'))>1:
        imported_module=__import__(module, globals(), locals(), fromlist=(module.split('.')[-1]))
      else:
        imported_module=__import__(module, globals(), locals())
      logon(imported_module)
    logger.debug("... ready initializing the debug system.")
