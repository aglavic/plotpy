# -*- encoding: utf-8 -*-
'''
  Module to create an ipython kernel with access to the running plot.py instance.
'''

from threading import Thread
from IPython.lib.kernel import connect_qtconsole
from IPython.zmq.ipkernel import IPKernelApp

class IPKernelThread(object):
  def __init__(self):
    self.kernel=IPKernelApp()
    self.kernel.initialize(['python', '--gui=gtk'])
    self.konsoles=[]
    self.namespace=self.kernel.shell.user_ns
    self._init_keys=self.namespace.keys()

  def update_ns(self, ns):
    self.namespace.update(ns)

  def new_qtc(self):
    '''
      Run new QT console application.
    '''
    return connect_qtconsole(self.kernel.connection_file, profile=self.kernel.profile)

