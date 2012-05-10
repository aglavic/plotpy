# -*- encoding: utf-8 -*-
'''
  Module to log all interesting events in a debugging session. With the 
  --debug and --logmodules or --logall option even function calls are stored 
  in the log file. Single functions can be recorded using decorators.
  
  CAREFUL: The --logall option can create a huge amount of data, be sure 
  not to reproduce errors rapidly after starting the program to let the 
  file size stay at a minimum. (a 1MB log file just after starting the 
  Program is not unlikely)
           
  Example of the decorator usage:
  ::
  
    # logging for debug
    from decorators import log_call, log_input, log_output, log_both
    @log_call
    def some_function(some_bla):
      ...
       .
      ...
      return whatever

'''

import logging
import warnings
import sys
from types import FunctionType, BuiltinFunctionType
import decorators
from decorators import log_call, log_input, log_output, log_both

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

logger=logging

class RedirectOutput(object):
  '''
    Class to redirect all print statements to the logger.
  '''

  def __init__(self, obj, connection, connect_on_keyword=[]):
    '''
      Class consturctor.
      
      :param plotting_session: A session object derived from GenericSession.
    '''
    self.file_object=obj
    self.connection=connection
    self.connect_on_keyword=connect_on_keyword
    self.buffer=""

  def write(self, string):
    '''
      Add content.
      
      :param string: Output string of stdout
    '''
    self.buffer+=string
    if "\n" in string:
      connection=self.connection
      for keyword, connect in self.connect_on_keyword:
        if keyword in self.buffer:
          connection=connect
      connection(self.buffer)
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
    connection(self.buffer)
    self.buffer=""
    self.file_object.flush()

  def fileno(self):
    return self.file_object.fileno()


def logon(module, log_decorator=log_call):
  '''
   Start logging function calls for all functions of one module.
   
   :param module: A module whose function calls should be logged.
  '''
  module_dict=module.__dict__
  # get all functions/build-in-function of the module not starting with underscore
  modfunctions=filter(lambda key: type(module_dict[key]) in [FunctionType, BuiltinFunctionType] and not \
                                  key.startswith('_'), module_dict.keys())
  modclasses=filter(lambda key: ('class' in str(type(getattr(module, key))) or \
                                "'type'" in str(type(getattr(module, key)))) and not key.startswith('_'),
                      module_dict.keys())
  for function_name in modfunctions:
    # get the function
    function=module_dict[function_name]
    # replace the function by a decorated version
    # only replace if the function is originally defined in this module
    if function.__module__==module.__name__:
      module_dict[function_name]=log_decorator(function)
      # store real function as private
      module_dict['_'+function_name]=function
  for cls_name in modclasses:
    # get the class
    cls=module_dict[cls_name]
    if cls.__module__==module.__name__:
      clsdict=cls.__dict__
      # create decorated methods for the class
      clsfunctions=filter(lambda key: type(clsdict[key]) in [FunctionType], clsdict.keys())
      for func_name in clsfunctions:
        setattr(cls, func_name, log_decorator(getattr(cls, func_name)))


def numpy_error_handler(type_, flag):
  logger.warning("Numpy floating point error (%s), with flag %s"%(type_, flag))

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
  formatter=logging.Formatter("%(asctime)s %(levelname) 8s %(message)s")
  # add formatter to ch
  file_handle.setFormatter(formatter)
  console_handle=logging.StreamHandler()
  console_handle.setLevel(logging.INFO)
  logger=logging.getLogger() # get the root logger
  logger.setLevel(logging.DEBUG)
  logger.addHandler(console_handle)
  logger.addHandler(file_handle)
  sys.stdout=RedirectOutput(sys.stdout, logger.info)
  sys.stderr=RedirectOutput(sys.stderr, logger.error, connect_on_keyword=[('Warning', logger.warning)])
  try:
    import numpy
  except:
    pass
  else:
    # log numpy errors as warnings
    numpy.seterrcall(numpy_error_handler)
    numpy.seterr(all='call')
  # redirect warnigs to the logger
  warnings.resetwarnings()
  warnings.simplefilter('always')
  try:
    logging.captureWarnings(True)
  except AttributeError:
    pass
  if level==logging.DEBUG:
    # In complete debug mode function calls of defined modules get logged, too
    logger.debug("Beginning initialize logging for all modules...")
    #sys.exc_clear=log_call(sys.exc_clear)
    for module in modules:
      if module.startswith('*'):
        if module.endswith('*'):
          module=module.strip('*')
          log_decorator=log_both
        else:
          module=module.strip('*')
          log_decorator=log_input
      elif module.endswith('*'):
        module=module.strip('*')
        log_decorator=log_output
      else:
        log_decorator=log_call
      if len(module.split('.'))>1:
        imported_module=__import__(module, globals(), locals(),
                                   fromlist=(module.split('.')[-1]))
      else:
        imported_module=__import__(module, globals(), locals())
      logger.debug('    logging moduel %s'%imported_module.__name__)
      logon(imported_module, log_decorator=log_decorator)
    logger.debug("... ready initializing the debug system.")
    decorators.logger=logger
