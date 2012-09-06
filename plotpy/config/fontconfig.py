#-*- coding: utf8 -*-
'''
  Interface to the fontconfig libraray using ctypes
'''

import sys

if sys.platform.startswith('win'):
  font_config=None
else:
  import ctypes
  try:
    font_config=ctypes.cdll.LoadLibrary('libfontconfig.so.1')
  except OSError:
    try:
      font_config=ctypes.cdll.LoadLibrary('libfontconfig.so')
    except OSError:
      font_config=None

class FontConfig(object):
  '''
    Interface to the font_config library.
  '''

  def __init__(self):
    font_config.FcInit()

  def __getitem__(self, key):
    '''
      Return the file from a given font description.
    '''
    key=key.lower()
    if key.split()[-1].isdigit():
      key=" ".join(key.split()[:-1])
    family=key
    face=None
    for item in key.split():
      if item in ['bold', 'italic', 'normal', 'regular']:
        family=key.split(item)[0]
        face=key.split(family)[1]
        break
    return self.match_font(family, face)['file']


  def get_font_folders(self):
    '''
      Return a list of folders where fonts can be found.
    '''
    # get list of folders as pointer
    fl_pointer=font_config.FcConfigGetFontDirs(None)
    return self.resolve_string_list(fl_pointer)

  def match_font(self, font_family, font_face=None):
    '''
      Analyze a font description and return dictionary with font information.
    '''
    # get list of folders as pointer
    if font_face is None:
      font=font_family
    else:
      font=font_family+':'+font_face
    pattern=font_config.FcNameParse(font)
    font_config.FcConfigSubstitute(pattern)
    match=font_config.FcFontMatch(None, pattern)
    output={}
    for key, value in [
                      ('file', 'file'),
                      ('family', 'family'),
                      ('face', 'style'),
                      ('format', 'fontformat'),
                      ('size', 'size'),
                      ]:
      result=font_config.FcPatternFormat(match, "%%{%s}"%value)
      output[key]=ctypes.c_char_p(result).value
    return output

  def resolve_string_list(self, pointer):
    output=[]
    res=ctypes.c_char_p(font_config.FcStrListNext(pointer)).value
    while res is not None:
      output.append(res)
      res=ctypes.c_char_p(font_config.FcStrListNext(pointer)).value
    return output

if font_config is not None:
  fc=FontConfig()
