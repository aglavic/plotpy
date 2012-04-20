#-*- coding: utf8 -*-
'''
  Module to locate available fonts.
'''

import os
from glob import glob
from subprocess import Popen, PIPE


FONT_TYPES=['ttf', ]

class FontControl(dict):
  '''
    Hold the paths of all fonts that can be found on the system and
    the font name as keys.
  '''

  def __init__(self):
    dict.__init__(self)
    self.locate_fonts()

  def locate_fonts(self):
    # search for X11 fonts
    try:
      paths=self.get_x11_font_paths()
    except:
      paths=[]
    paths+=['/usr/share/fonts', '/usr/local/share/fonts']
    paths=self.filter_paths(paths)
    paths=self.search_fonts(paths)
    # sort for number of fonts and if arial is installed
    for path, fonts in paths:
      for font in fonts:
        if font.rsplit('.', 1)[1] in FONT_TYPES:
          fname=font.rsplit('.', 1)[0]
          fname=os.path.split(fname)[1]
          self[fname]=path

  def get_x11_font_paths(self):
    proc=Popen(['xset', '-q'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    output=proc.communicate()
    next_line=False
    for line in output[0].splitlines():
      if 'Font' in line:
        next_line=True
        continue
      if next_line:
        items=line.split(',')
        items=map(lambda item: item.strip(), items)
        return items

  def filter_paths(self, items):
    for item in reversed(items):
      if not os.path.exists(item):
        items.remove(item)
    return items

  def search_fonts(self, paths):
    output=[]
    for fpath in paths:
      items=glob(os.path.join(fpath, '*'))
      dirs=filter(os.path.isdir, items)
      output+=self.search_fonts(dirs)
      fonts=filter(self.filter_fonts, items)
      if len(fonts)>0:
        output.append([fpath, fonts])
    return output

  def filter_fonts(self, name):
    try:
      ftype=name.rsplit('.', 1)[1]
    except IndexError:
      return False
    return ftype in FONT_TYPES
