# -*- encoding: utf-8 -*-
'''
  Module to create an ipython kernel with access to the running plot.py instance.
'''

from threading import Thread
from IPython.zmq.ipkernel import IPKernelApp

class IPKernelThread(Thread):
  def run(self):
    self.app=IPKernelApp.instance()
    self.app.initialize()
    self.app.start()
