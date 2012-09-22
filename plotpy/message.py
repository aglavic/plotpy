'''
  Module to provide a general message system for command line and GUI
  usage.
  Messages are one of information, warning and error and can be grouped
  into global groups and item messages. For example:
    When reading a bunch of files (10) the reader would call:
      info(None, group='Reading files', numitems=10)
      for item in items:
        info('Reading...', group='Reading files', item=item)
  Each item could call info again to update the progress or show additional
  information using the same group and item argument.
'''

import sys

if sys.stdin.encoding is None:
  in_encoding='utf8'
else:
  in_encoding=sys.stdin.encoding
if sys.stdout.encoding is None:
  out_encoding='utf8'
else:
  out_encoding=sys.stdout.encoding

__all__=['info', 'warn', 'error', 'in_encoding', 'out_encoding']

class PlotpyError(Exception):
  pass

class PlotpyWarning(Warning):
  pass

class DefaultMessenger(object):
  '''
    The default messenger does not show any progress information
    and directly prints to stdout or raises a Warning/Error.
  '''
  last_message=None
  encoding=out_encoding

  def format_message(self, message, group, item):
    if item is not None:
      if message is None:
        message=item
      else:
        message=item+' - '+message
    if group is not None and group!='reset':
      if message is None:
        message=group
      else:
        message=group+' - '+message
    return message.encode(out_encoding)

  def info(self, message, group=None, item=None, numitems=1, progress=None):
    output=self.format_message(message, group, item)
    if output==self.last_message:
      pass
    else:
      self.last_message=output
      print output

  def warn(self, message, group=None, item=None, numitems=1, progress=None):
    raise PlotpyWarning, self.format_message(message, group, item)

  def error(self, message, group=None, item=None, numitems=1, progress=None):
    raise PlotpyError, self.format_message(message, group, item)

class NiceMessenger(object):
  '''
    Messenger which does not raise any errors and goups output
    according to the group and item scheme. Progress is
    indicated independent of output as last line in the 
    console.
  '''
  active_group=None
  active_item=None
  last_message=None
  numitems=1
  item_count=0
  encoding=out_encoding

  def _write(self, message=None, group=None, item=None, numitems=1, progress=None):
    self.clear_line()
    if group is None:
      self.active_group=None
      self.active_item=None
      if not message==self.last_message and message is not None:
        sys.stdout.write(message+'\n')
      self.progress(progress)
    elif group=='reset':
      self.active_group=None
      self.active_item=None
      if not message==self.last_message and message is not None:
        sys.stdout.write(message+'\n')
      self.progress(progress)
    else:
      if item is None:
        if group==self.active_group:
          if not message==self.last_message and message is not None:
            sys.stdout.write('    '+message+'\n')
          self.progress(progress)
        else:
          self.active_group=group
          self.numitems=numitems
          self.item_count=0
          sys.stdout.write(group+':\n')
          if not message==self.last_message and message is not None:
            sys.stdout.write('    '+message+'\n')
          self.progress(progress)
      elif item==self.active_item:
        if not message==self.last_message and message is not None:
          sys.stdout.write('        '+message+'\n')
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(None)
      else:
        self.active_item=item
        self.item_count+=1
        sys.stdout.write('    '+item+'\n')
        if not message==self.last_message and message is not None:
          sys.stdout.write('        '+message+'\n')
        if progress is not None:
          self.progress(100.*float(self.item_count-1)/self.numitems+progress/float(self.numitems))
        else:
          self.progress(100.*float(self.item_count-1)/self.numitems)
    self.last_message=message
    sys.stdout.flush()

  def info(self, message, group=None, item=None, numitems=1, progress=None):
    self._write(message, group, item, numitems, progress)

  def warn(self, message, group=None, item=None, numitems=1, progress=None):
    message='\033[0;35mWARNING\033[0m '+message
    self._write(message, group, item, numitems, progress)

  def error(self, message, group=None, item=None, numitems=1, progress=None):
    message='\033[0;31mERROR\033[0m '+message
    self._write(message, group, item, numitems, progress)

  def cline_progress(self, progress):
    # return string with progress indicator and percentage
    preclen=int(progress/100.*50)
    progline='='*preclen
    resline=' '*(50-preclen)
    combline=progline+resline
    prec='%3i%%'%(progress)
    output='['+combline[:23]+prec+combline[26:]+']'
    return output

  def progress(self, progress):
    if progress is not None:
      sys.stdout.write(self.cline_progress(progress))

  def clear_line(self):
    sys.stdout.write('\r'+' '*60+'\r')
    sys.stdout.flush()

messenger=DefaultMessenger()

def info(message, group=None, item=None, numitems=1, progress=None):
  messenger.info(message, group=group, item=item, numitems=numitems, progress=progress)

def warn(message, group=None, item=None, numitems=1, progress=None):
  messenger.warn(message, group=group, item=item, numitems=numitems, progress=progress)

def error(message, group=None, item=None, numitems=1, progress=None):
  messenger.error(message, group=group, item=item, numitems=numitems, progress=progress)


if __name__=='__main__':
  from time import sleep
  messenger=NiceMessenger()
  info('', group='Startgruppe', numitems=2, progress=0)
  sleep(1)
  info('Message 1', group='Startgruppe', item='erste', progress=None)
  sleep(1)
  for i in range(15, 100):
    info('Message 2', group='Startgruppe', item='erste', progress=i)
    sleep(0.1)
  warn('Message 1', group='Startgruppe', item='zweite', progress=None)
  sleep(1)
  for i in range(100):
    warn('Message 2', group='Startgruppe', item='zweite', progress=i)
    sleep(0.1)
  info('Start', group='Neue Gruppe', numitems=1, progress=5)
  sleep(1)
  info('Message 1', group='Neue Gruppe', item='erste', progress=50)
  sleep(1)
  error('Message 2', group='Neue Gruppe', item='erste', progress=60)
  sleep(1)
  error('Message 3', group='Neue Gruppe', item='erste', progress=70)
  sleep(1)
  info('Message 4', group='Neue Gruppe', item='erste', progress=80)
  sleep(1)
  sys.stdout.write('\n')
