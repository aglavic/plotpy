# -*- encoding: utf-8 -*-
'''
  Module to create an ipython kernel with access to the running plot.py instance.
'''

import sys
import gobject
from IPython.lib.kernel import connect_qtconsole
from IPython.zmq.ipkernel import IPKernelApp

class IPKernelGTK(IPKernelApp):
  _is_active=False

  def __init__(self, **user_ns):
    """
      Create an ipython kernel instance and put it's main iteration function into
      a GTK timer to be run regularily. This way it can interact with the program
      without blocking it.
    """
    # reset to normal stderr and stdout for proper redirection
    self.old_stderr=sys.stderr
    self.old_stdout=sys.stdout
    sys.stderr=sys.__stderr__
    sys.stdout=sys.__stdout__

    IPKernelApp.__init__(self)
    self._is_active=True
    self.initialize([])
    self.kernel.user_ns.update(user_ns)
    self.shell.prompt_manager.in_template
    self.konsoles=[]
    self.kernel.eventloop=lambda ignore: None
    IPKernelApp.start(self)
    gobject.timeout_add(int(self.kernel._poll_interval*1000),
                            self.do_one_iteration)

  def do_one_iteration(self):
    # needs to return True for GTK not to unregister it.
    self.kernel.do_one_iteration()
    return self._is_active

  def update_ns(self, ns):
    self.shell.user_ns.update(ns)

  def new_qtc(self):
    '''
      Run new QT console application.
    '''
    self.konsoles.append(connect_qtconsole(self.connection_file, profile=self.profile,
                                           argv=[]))

  def cleanup_consoles(self):
    for c in self.konsoles:
      try:
        c.kill()
      except:
        pass

  def close(self):
    self.cleanup_consoles()
    sys.stderr=self.old_stderr
    sys.stdout=self.old_stdout
