# -*- encoding: utf-8 -*-
'''
 Functions to parallelize some functions of the program using the IPython multiprocessing features.
'''

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

from plot_script.config.parallel import CLIENT_KW, CLUSTER_PLOTPY_DIR
from plot_script.config import user_config
if not 'Parallel' in user_config:
  user_config['Parallel']=CLIENT_KW

import sys
import numpy
from time import sleep
#try:
#  import multiprocessing
#except ImportError:
multiprocessing=None

client=None
dview=None
lview=None

additional_actions=[]

def connect():
  print "Initializing IPython parallel processing..."
  global client, dview, lview
  from IPython.parallel import Client
  from IPython.parallel.error import CompositeError
  try:
    client=Client(**user_config['Parallel'])
  except Exception, error:
    print "Could not connect to cluster:\n  %s - %s"%(type(error).__name__, error)
    return False
  print "\tconnected to controller with %i engines"%len(client.ids)
  dview=client[:]
  lview=client.load_balanced_view()
  # change std. execution method to be blocking
  dview.block=True
  lview.block=True
  # prepare the client with the most common used modules
  print "\tpreparing necessary modules..."
  general=[
            'import numpy',
            'import sys',
            'import os',
            'if not "%s" in sys.path: sys.path.append("%s");'%(CLUSTER_PLOTPY_DIR,
                                                               CLUSTER_PLOTPY_DIR),
            'import plot_script.plugins',
            "user_folder=os.path.join(os.path.expanduser('~'), '.plotting_gui')",
            '''if os.path.exists(user_folder) and os.path.exists(os.path.join(user_folder, 'plugins')) \
and not os.path.join(user_folder, 'plugins') in sys.path: \
sys.path.append(os.path.join(user_folder, 'plugins'));''',
            'import plot_script.fit_data as fit_data',
            ]
  l=0
  sys.stdout.write('\t\t')
  for action in general+additional_actions:
    sys.stdout.write('\b'*l+action)
    sys.stdout.flush()
    l=len(action)
    try:
      dview.execute(action)
    except CompositeError, e:
      print "Encountered an error on the remote machine!"
      e.raise_exception()
  print "\n\tFinished!"
  return True

def disconnect():
  global client, dview, lview
  client=None
  dview=None
  lview=None
  print "Disconnected!"

def add_actions(actions):
  global additional_actions
  if dview is None:
    additional_actions+=actions
  elif not type(dview) is Controller:
    for action in actions:
      if not action in additional_actions:
        additional_actions.append(action)
        dview.execute(action)
  else:
    from IPython.parallel.error import CompositeError
    for action in actions:
      if not action in additional_actions:
        additional_actions.append(action)
        try:
          dview.execute(action)
        except CompositeError, e:
          print "Encountered an error on the remote machine!"
          e.raise_exception()


if multiprocessing is not None:
  # equivalent multiprocessing interface
  manager=multiprocessing.Manager()
  class Worker(multiprocessing.Process):
    '''
      Thread which executes arbitrary code from a never ending main loop.
    '''

    def __init__(self, globals={}, locals={}):
      self.locals=manager.dict(locals)
      self.globals=manager.dict(globals)
      self._options=manager.dict(
                                execute=False,
                                finished=True,
                                stay_alive=True,
                                ex_action='',
                                last_exception=None,
                                  )
      multiprocessing.Process.__init__(self)

    def run(self):
      '''
        Start the threads main loop.
      '''
      while self._options['stay_alive']:
        if self._options['execute']:
          self._do_execution()
          self._options['execute']=False
          self._options['finished']=True
        else:
          sleep(0.001)

    def execute(self, action):
      '''
        Define the next action to be executed.
      '''
      self._options['ex_action']=action
      self._options['finished']=False
      self._options['last_exception']=None
      self._options['execute']=True

    def _do_execution(self):
      try:
        global_dict=dict(self.globals)
        local_dict=dict(self.locals)
        exec self._options['ex_action'] in global_dict, local_dict
        for key, value in global_dict.items():
          if key!='__builtins__':
            self.globals[key]=value
        for key, value in local_dict.items():
          if key!='__builtins__':
            self.locals[key]=value
      except Exception, error:
        self._options['last_exception']=error

  class Controller(object):
    '''
      Worker thread controller object. Should be a replacement for the ipython
      direct view of the multiprocessing facility.
    '''

    def __init__(self, max_threads=multiprocessing.cpu_count(), startup_actions=[]):
      self.max_threads=max_threads
      self.workers=[]
      w0=Worker()
      w0.start()
      for action in startup_actions:
        print action
        w0.execute(action)
        while not w0._finished:
          sleep(0.001)
      self.workers.append(w0)
      for i in range(max_threads-1):
        wi=Worker(w0.globals, w0.locals)
        wi.start()
        self.workers.append(wi)

    def execute(self, action):
      for worker in self.workers:
        worker.execute(action)
      while not all(map(lambda w: w._finished, self.workers)):
        sleep(0.001)
      # check for errors
      for worker in self.workers:
        if worker.last_exception is not None:
          raise worker.last_exception.__class__, worker.last_exception.message

    def __getitem__(self, key):
      output=[]
      for worker in self.workers:
        if key in worker.locals:
          output.append(worker.locals[key])
      return output

    def __setitem__(self, key, value):
      for worker in self.workers:
        worker.locals[key]=value

    def scatter(self, key, value):
      N=len(self.workers)
      L=len(value)
      step=(L+N-1)//N
      for i in range(N):
        self.workers[i].locals[key]=value[i*step:(i+1)*step]

    def gather(self, key):
      output=self.workers[0].locals[key]
      if type(output) is list:
        output=list(output)
        for worker in self.workers[1:]:
          output+=worker.locals[key]
      elif type(output) is numpy.ndarray:
        output=output.copy()
        for worker in self.workers[1:]:
          output=numpy.append(output, worker.locals[key])
      else:
        raise NotImplementedError, 'only list and arrays are supported'
      return output




  def connect_threads():
    global dview
    print "Initializing threadding with %i threads..."%cpu_count() #@UndefinedVariable
    general=[
              'import numpy',
              'import sys',
              'import os',
              'if not "%s" in sys.path: sys.path.append("%s");'%(CLUSTER_PLOTPY_DIR,
                                                                 CLUSTER_PLOTPY_DIR),
              'import plugins',
              "user_folder=os.path.join(os.path.expanduser('~'), '.plotting_gui')",
              '''if os.path.exists(user_folder) and os.path.exists(os.path.join(user_folder, 'plugins')) \
  and not os.path.join(user_folder, 'plugins') in sys.path: \
  sys.path.append(os.path.join(user_folder, 'plugins'));''',
              'import fit_data',
              ]
    dview=Controller(startup_actions=general+additional_actions)
    print "\n\tFinished!"


else:
  class Controller(object):
    pass
