# -*- encoding: utf-8 -*-
'''
  Generic file readout for ASCII data.
'''

import os
import gzip
import numpy

from measurement_data_structure import MeasurementData, PhysicalProperty

__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"


class GenericFileReader(object):
  '''
    Object used to read ASCII files using specific setting.
    Can be used to tune the readout settings without rereading
    the file text again.
    The data readout is focused on readability and to be general,
    not on speed.
  '''

  # global options for the readout
  header_lines=None             # default is auto
  sequence_splitting=None       # read just one sequence
  column_seperator=None         # Split on whitespace
  comment_characters='#;!'      # lines starting with one of these characters 
                                # are ignored for data readout, in header they are used
  column_names=None             # List of names for each column or None
  column_units=None

  def __init__(self, **opts):
    '''
      Create a new file reader with optional supplied settings.
    '''
    for general_setting in [
                'header_lines',
                'sequence_splitting',
                'column_seperator',
                'comment_characters',
                'column_names',
                'column_units',
                            ]:
      if general_setting in opts:
        setattr(self, general_setting, opts[general_setting])
    self.file_text=''
    self.header=''
    self.data=''

  def read_file_data(self, file_object):
    '''
      Read the data of a textfile, gziped textfile or open filelike object.
    '''
    if type(object) in [str, unicode]:
      if not os.path.exists(file_object):
        return False
      if object.endswith('.gz'):
        self.file_text=gzip.open(object, 'r').read()
      else:
        self.file_text=open(object, 'r').read()
    else:
      self.file_text=file_object.read()
    return True

  def split_header(self):
    '''
      Split the current data into header and data part.
    '''
    text_lines=self.file_text.splitlines()
    header_lines=self.header_lines
    if header_lines is None:
      comment_characters=self.comment_characters
      split_by=self.column_seperator
      # autodetect header lines.
      for i, line in enumerate(text_lines):
        if line.strip()[0] in comment_characters:
          continue
        try:
          float(line.split(split_by)[0])
        except ValueError:
          continue
        else:
          self.header=text_lines[:i]
          self.data=text_lines[i:]
          return True
    else:
      # use defined number of lines
      self.header=text_lines[:header_lines]
      self.data=text_lines[header_lines:]
      return True

  def get_data(self):
    '''
      Extract columns from the data.
    '''
    data_lines=map(self.get_data_line, self.data)
    data_lines=filter(lambda line: line is not None, data_lines)
    return numpy.array(data_lines)


