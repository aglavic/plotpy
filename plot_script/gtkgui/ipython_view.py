# -*- coding: utf-8 -*-
"""
Backend to the console plugin.

 author: Eitan Isaacson
 organization: IBM Corporation
 copyright: Copyright (c) 2007 IBM Corporation
 license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
"""
# this file is a modified version of source code from the Accerciser project
# http://live.gnome.org/accerciser
# Added minor changes by Artur Glavic

import gtk
import re
import sys
import os
import pango
from StringIO import StringIO

try:
        import IPython
except Exception, e:
        raise RuntimeError, "Error importing IPython (%s)"%str(e)

from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport

ansi_colors={'0;30': 'Black',
                '0;31': 'Red',
                '0;32': 'Green',
                '0;33': 'Brown',
                '0;34': 'Blue',
                '0;35': 'Purple',
                '0;36': 'Cyan',
                '0;37': 'LightGray',
                '1;30': 'DarkGray',
                '1;31': 'DarkRed',
                '1;32': 'SeaGreen',
                '1;33': 'Blue',
                '1;34': 'LightBlue',
                '1;35': 'MediumPurple',
                '1;36': 'LightCyan',
                '1;37': 'Black'}

class IterableIPShell:
  def __init__(self, argv=None, user_ns=None, user_global_ns=None,
               cin=None, cout=None, cerr=None, input_func=None):
    if input_func:
      IPython.iplib.raw_input_original=input_func
    if cin:
      IPython.Shell.Term.cin=cin
    if cout:
      IPython.Shell.Term.cout=cout
    if cerr:
      IPython.Shell.Term.cerr=cerr

    if argv is None:
      argv=[]

    # This is to get rid of the blockage that occurs during 
    # IPython.Shell.InteractiveShell.user_setup()
    IPython.iplib.raw_input=lambda x: None

    self.term=IPython.genutils.IOTerm(cin=cin, cout=cout, cerr=cerr) #@UndefinedVariable
    os.environ['TERM']='dumb'

    excepthook=sys.excepthook
    self.IP=IPython.Shell.make_IPython(argv, user_ns=user_ns, #@UndefinedVariable
                                         user_global_ns=user_global_ns,
                                         embedded=True,
                                         shell_class=IPython.Shell.InteractiveShell) #@UndefinedVariable
    self.IP.system=lambda cmd: self.shell(self.IP.var_expand(cmd),
                                            header='IPython system call: ',
                                            verbose=self.IP.rc.system_verbose)
    # set right encoding
    self.IP.stdin_encoding='UTF-8'
    sys.excepthook=excepthook
    self.iter_more=0
    self.history_level=0
    self.complete_sep=re.compile('[\s\{\}\[\]\(\)=\'"]')

  def execute(self):
    self.history_level=0
    orig_stdout=sys.stdout
    sys.stdout=IPython.Shell.Term.cout #@UndefinedVariable
    try:
      line=self.IP.raw_input(None, self.iter_more)
      if self.IP.autoindent:
        self.IP.readline_startup_hook(None)
    except KeyboardInterrupt:
      self.IP.write('\nKeyboardInterrupt\n')
      self.IP.resetbuffer()
      # keep cache in sync with the prompt counter:
      self.IP.outputcache.prompt_count-=1

      if self.IP.autoindent:
        self.IP.indent_current_nsp=0
      self.iter_more=0
    except:
      self.IP.showtraceback()
    else:
      self.iter_more=self.IP.push(line)
      if (self.IP.SyntaxTB.last_syntax_error and
          self.IP.rc.autoedit_syntax):
        self.IP.edit_syntax_error()
    if self.iter_more:
      self.prompt=str(self.IP.outputcache.prompt2).strip()
      if self.IP.autoindent:
        self.IP.readline_startup_hook(self.IP.pre_readline)
    else:
      self.prompt=str(self.IP.outputcache.prompt1).strip()
    sys.stdout=orig_stdout

  def historyBack(self):
    self.history_level-=1
    return self._getHistory()

  def historyForward(self):
    self.history_level+=1
    return self._getHistory()

  def _getHistory(self):
    try:
      rv=self.IP.user_ns['In'][self.history_level].strip('\n')
    except IndexError:
      self.history_level=0
      rv=''
    return rv

  def updateNamespace(self, ns_dict):
    self.IP.user_ns.update(ns_dict)

  def complete(self, line):
    split_line=self.complete_sep.split(line)
    possibilities=self.IP.complete(split_line[-1])
    if possibilities:
      common_prefix=reduce(self._commonPrefix, possibilities)
      completed=line[:-len(split_line[-1])]+common_prefix
    else:
      completed=line
    return completed, possibilities

  def _commonPrefix(self, str1, str2):
    for i in range(len(str1)):
      if not str2.startswith(str1[:i+1]):
        return str1[:i]
    return str1

  def shell(self, cmd, verbose=0, debug=0, header=''):
    stat=0
    if verbose or debug: print header+cmd
    # flush stdout so we don't mangle python's buffering
    if not debug:
      input, output=os.popen4(cmd)
      print output.read()
      output.close()
      input.close()

class ConsoleView(gtk.TextView):
  def __init__(self):
    gtk.TextView.__init__(self)
    self.modify_font(pango.FontDescription('Mono'))
    self.set_cursor_visible(True)
    self.text_buffer=self.get_buffer()
    self.mark=self.text_buffer.create_mark('scroll_mark',
                                             self.text_buffer.get_end_iter(),
                                             False)
    for code in ansi_colors:
      self.text_buffer.create_tag(code,
                                  foreground=ansi_colors[code],
                                  weight=700)
    self.text_buffer.create_tag('0')
    self.text_buffer.create_tag('notouch', editable=False)
    self.color_pat=re.compile('\x01?\x1b\[(.*?)m\x02?')
    self.line_start=\
                self.text_buffer.create_mark('line_start',
                        self.text_buffer.get_end_iter(), True
                )
    self.connect('key-press-event', self._onKeypress)
    self.last_cursor_pos=0

  def write(self, text, editable=False):
    segments=self.color_pat.split(text)
    segment=segments.pop(0)
    start_mark=self.text_buffer.create_mark(None,
                                              self.text_buffer.get_end_iter(),
                                              True)
    self.text_buffer.insert(self.text_buffer.get_end_iter(), segment)

    if segments:
      ansi_tags=self.color_pat.findall(text)
      for tag in ansi_tags:
        i=segments.index(tag)
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(),
                                             segments[i+1], tag)
        segments.pop(i)
    if not editable:
      self.text_buffer.apply_tag_by_name('notouch',
                                         self.text_buffer.get_iter_at_mark(start_mark),
                                         self.text_buffer.get_end_iter())
    self.text_buffer.delete_mark(start_mark)
    self.scroll_mark_onscreen(self.mark)

  def showPrompt(self, prompt):
    self.write(prompt)
    self.text_buffer.move_mark(self.line_start, self.text_buffer.get_end_iter())

  def changeLine(self, text):
    iter=self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.delete(self.text_buffer.get_iter_at_mark(self.line_start), iter)
    self.write(text, True)

  def getCurrentLine(self):
    rv=self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.line_start),
                                    self.text_buffer.get_end_iter(), False)
    return unicode(rv)

  def showReturned(self, text):
    iter=self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.apply_tag_by_name('notouch',
                                       self.text_buffer.get_iter_at_mark(self.line_start),
                                       iter)
    self.write('\n'+text)
    if text:
      self.write('\n')
    self.showPrompt(self.prompt)
    self.text_buffer.move_mark(self.line_start, self.text_buffer.get_end_iter())
    self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

  def _onKeypress(self, obj, event):
    if not event.string:
      return
    insert_mark=self.text_buffer.get_insert()
    insert_iter=self.text_buffer.get_iter_at_mark(insert_mark)
    selection_mark=self.text_buffer.get_selection_bound()
    selection_iter=self.text_buffer.get_iter_at_mark(selection_mark)
    start_iter=self.text_buffer.get_iter_at_mark(self.line_start)
    if start_iter.compare(insert_iter)<=0 and \
          start_iter.compare(selection_iter)<=0:
      return
    elif start_iter.compare(insert_iter)>0 and \
          start_iter.compare(selection_iter)>0:
      self.text_buffer.place_cursor(start_iter)
    elif insert_iter.compare(selection_iter)<0:
      self.text_buffer.move_mark(insert_mark, start_iter)
    elif insert_iter.compare(selection_iter)>0:
      self.text_buffer.move_mark(selection_mark, start_iter)

class IPythonView(ConsoleView, IterableIPShell):
  propagate_key_parent=None # a window to which unhandles keys are propagated

  def __init__(self, intro_text=""):
    ConsoleView.__init__(self)
    self.cout=StringIO()
    IterableIPShell.__init__(self, cout=self.cout, cerr=self.cout,
                             input_func=self.raw_input)
    self.connect('key_press_event', self.keyPress)
    self.execute()
    self.cout.truncate(0)
    self.showPrompt(intro_text+self.prompt)
    self.interrupt=False

  def raw_input(self, prompt=''):
    if self.interrupt:
      self.interrupt=False
      raise KeyboardInterrupt
    line=self.getCurrentLine()
    return line

  def keyPress(self, widget, event):
    if event.state&gtk.gdk.CONTROL_MASK and event.keyval==99:
      self.interrupt=True
      self._processLine()
      return True
    elif event.keyval==gtk.keysyms.Return:
      self._processLine()
      return True
    elif event.keyval==gtk.keysyms.Up:
      self.changeLine(self.historyBack())
      return True
    elif event.keyval==gtk.keysyms.Down:
      self.changeLine(self.historyForward())
      return True
    elif event.keyval==gtk.keysyms.Tab:
      if not self.getCurrentLine().strip():
        return False
      completed, possibilities=self.complete(self.getCurrentLine())
      if len(possibilities)>1:
        slice=self.getCurrentLine()
        self.write('\n')
        for symbol in possibilities:
          self.write(symbol+'\n')
        self.showPrompt(self.prompt)
      self.changeLine(completed or slice)
      return True
    elif (event.state&gtk.gdk.CONTROL_MASK or \
          event.state&gtk.gdk.MOD1_MASK) and self.propagate_key_parent is not None:
      # propagate any <control>+Key and <alt>+Key to the main window.
      self.propagate_key_parent.emit('key_press_event', event)

  def externalExecute(self, command):
    '''
      Run command inside the shell and show it in the dialog.
    '''
    self.write(command)
    self._processLine()
    #self.prompt=str(self.IP.outputcache.prompt1).strip()
    #self.showReturned(str(self.IP.outputcache._))

  def _processLine(self):
    self.history_pos=0
    self.execute()
    rv=self.cout.getvalue()
    if rv: rv=rv.strip('\n')
    self.showReturned(rv)
    self.cout.truncate(0)

class MenuWrapper(object):
  '''
    Class to provide GUI menu access as attributes of a interactive object.
    Every attribute of this object should be hidden for the user.
  '''
  __menu_root__=None

  def __init__(self, menu_root):
    '''
      Constructor just connecting the base menu.
    '''
    self.__menu_root__=menu_root

  def __get_dict__(self):
    '''
      Interactively creates the objects __dict__ dictionary to contain only the
      menu names. If a menu has a submenu, it will be connected to another MenuWrapper.
      If the menu is just connected to an action the attribute will be assigned to be
      the activation function of this action. In this way the user in the ipython console
      will get all menus when typing menu. + <TAB> and can activate the menu action by
      calling it with e.g. menu.submenu().
    '''
    menu_items=self.__menu_root__.get_children()
    # remove seperators
    menu_items=filter(lambda item: type(item) in [gtk.ImageMenuItem, gtk.MenuItem], menu_items)
    dict={}
    for item in menu_items:
      name=item.get_label().replace('_', '').replace('.', '').replace('/', '').replace(' ', '_').replace('-', '_')
      if name=='Empty':
        continue
      submenu=item.get_submenu()
      if submenu is not None:
        # Create submenu wrapper
        dict[name]=MenuWrapper(item.get_submenu())
      else:
        dict[name]=item.activate
    for key, value in dict.items():
      setattr(self, key, value)
    return dict

  # connect __dict__ to the __get_dict__ function
  __dict__=property(__get_dict__)

  def __getattribute__(self, name):
    # if used before first accessing the __dict__
    if name.startswith('_'):
      return object.__getattribute__(self, name)
    else:
      return self.__dict__[name]


class FitWrapper(object):
  '''
    Class to provide easy fit from the IPython console.
  '''
  __fit_root__=None
  __session_root__=None
  __window_root__=None

  def __init__(self, main_window, active_session):
    '''
      Constructor just connecting the base menu.
    '''
    from plot_script.fit_data import FitSession
    self.__fit_root__=FitSession
    self.__window_root__=main_window
    self.__session_root__=active_session

  def __get_dict__(self):
    '''
      Interactively creates the objects __dict__ dictionary to contain only the
      fit function names. Calling a function creates a fit and fits it.
    '''
    # remove seperators
    dataset=self.__session_root__.active_file_data[self.__window_root__.index_mess]
    if dataset.zdata<0:
      items=sorted(self.__fit_root__.available_functions_2d.items())
    else:
      items=sorted(self.__fit_root__.available_functions_3d.items())
    dict=FitSubWrapper(self.__fit_root__,
                               self.__window_root__,
                               self.__session_root__,
                               items).__dict__
    for key, value in dict.items():
      setattr(self, key, value)
    return dict

  # connect __dict__ to the __get_dict__ function
  __dict__=property(__get_dict__)

  def __getattribute__(self, name):
    if name.startswith('_'):
      return object.__getattribute__(self, name)
    else:
      return self.__dict__[name]

class FitSubWrapper(object):
  '''
    Class to provide easy fit from the IPython console.
  '''
  __fit_root__=None
  __session_root__=None
  __window_root__=None
  __items_root__=None

  def __init__(self, fit_session, main_window, active_session, items):
    '''
      Constructor just connecting the base menu.
    '''
    self.__fit_root__=fit_session
    self.__window_root__=main_window
    self.__session_root__=active_session
    self.__items_root__=items

  def __get_dict__(self):
    '''
      Interactively creates the objects __dict__ dictionary to contain only the
      fit function names. Calling a function creates a fit and fits it.
    '''
    dict={
          }
    for name, fit_class in self.__items_root__:
      name=name.replace('_', '').replace('.', '').replace('/', '').replace(' ', '_').replace('-', '_')
      dict[name]=FitCaller(self, fit_class)
    for key, value in dict.items():
      setattr(self, key, value)
    return dict

  # connect __dict__ to the __get_dict__ function
  __dict__=property(__get_dict__)

  def __getattribute__(self, name):
    if name.startswith('_'):
      return object.__getattribute__(self, name)
    else:
      return self.__dict__[name]


class FitCaller(object):
  '''
    A class to create a specific fit object for the current dataset.
    
    FitCallser.parameters is a list of (name,value) tuples for the default parameters.
  '''

  def __init__(self, parent, fit_class):
    self.__parent__=parent
    self.__fit_class__=fit_class
    self.parameters=zip(fit_class.parameter_names, fit_class.parameters)

  def __call__(self, params=None, dataset=None):
    if dataset is None:
      dataset=self.__parent__.__session_root__.active_file_data[self.__parent__.__window_root__.index_mess]
    if dataset.fit_object is None:
      dataset.fit_object=self.__parent__.__fit_root__(dataset)
    if params is None:
      params=self.__fit_class__.parameters
    fit=self.__fit_class__(params)
    dataset.fit_object.functions.append([fit, True, True, False, False])
    dataset.fit_object.fit()
    dataset.fit_object.simulate()
    return fit.parameters
