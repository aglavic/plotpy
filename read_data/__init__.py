# -*- encoding: utf-8 -*-
'''
  Package containing all modules for data file reading.
  This folder containes all files which define functions to read out
  data files for the diverse import modes of plot.py.
'''

from measurement_data_structure import MeasurementData, PhysicalProperty
from numpy import *

#+++++++++++++++++++++++++++++++++++AbstractImportFilter-Class+++++++++++++++++++++++++++++++++++++++++++++++++++#
class OptionSwitch(object):
  '''
    A class to simplify switch settings which can be of different types.
    Can be used e.g. to be an integer in one state or dict in an other.
  '''
  name=""
  _value=None
  value_types=[]
  
  def __init__(self, value, value_types=[float], name=""):
    '''
      Construct a switch object.
    '''
    self.value_types=list(value_types)
    self.value=value
    self.name=name
  
  def _get_switch(self):
    for i, typ in enumerate(self.value_types):
      if type(self.value) is typ:
        return i
    return -1
  
  def _get_value(self):
    return self._value
  
  def _set_value(self, value):
    if not type(value) in self.value_types:
      raise ValueError, "Type needs to be in the value_types list."
    else:
      self._value=value
  
  value=property(_get_value, _set_value)
  switch=property(_get_switch)
  
  def __eq__(self, other):
    if type(other) is not type(self):
      return self.switch==other
    else:
      return (self.value==other.value and self.value_types==other.value_types)
  
  def __repr__(self):
    if type(self.value) in [int, float, str, bool, unicode]:
      value=str(self.value)
    elif hasattr(self.value, '__iter__'):
      value=str(type(self.value).__name__)+"[%i]" % len(self.value)
    else:
      value=type(self.value).__name__
    output='<%s switch=%i value="%s">' % (
                                            self.name, 
                                            self.switch, 
                                            value
                                            )
    return output


class AbstractImportFilter(object):
  '''
    Class for importing data from any ascii source. It contains many options for the data
    readout and a readout method called with a filename or filelike object for import.
    The options can be saved/loaded to/from an dictionary to be stored in configobj instances.
  '''
  file_types=[]
  name='None'
  
  header_lines=0
  header_ignore_comments=False
  header_search=[]
  footer_lines=0
  
  split_sequences=None
  comment_string="#"
  columns=None
  error_cols={}
  
  separator=None
  
  # options to enamle fast readout on cost of stability
  disable_datacheck=True # don't check if all data lines contain float values
  skip_colcheck=False    # don't check if each line has the same number of columns
                         # ignored if disable_datacheck is True
  skip_linestripping=False# don't strip empty strings from each line
  
  # Define calculations to be performed after data readout
  post_calc_errors=[]
  post_calc_columns=[]
  post_recalc_columns=[]
  
  # Storing extracted information for further usage
  _extracted_data={}
  _header_columns=[]


  def __init__(self, name, presets=None):
    '''
      Constructor initializing the object.
      
      @param presets Dictionary to load presets from.
    '''
    if presets is not None:
      self.load_presets(presets)
    else:
      self.file_types=[]
      self.name=name
      self.header_lines=OptionSwitch(None, [int, type(None), 
                                    str], "Header Lines") # None is auto search for first data line
      self.footer_lines=OptionSwitch(0, [int, dict], "Footer Lines") # how many lines should be seen as footer
      self.split_sequences=OptionSwitch(None, [type(None), str], "Split Sequences")
      self.comment_string=OptionSwitch("#", [str, list, type(None)], 
                                        "Comment Strings") # can be a list to define multiple comment types
      self.columns=OptionSwitch(None, [type(None), list, dict], "Columns")
      self.post_calc_errors=[]
      self.post_calc_columns=[]
      self.post_recalc_columns=[]  
      self.header_search=[]
    
  def load_presets(self, preset):
    '''
      Load preset options from a dictionary.
    '''
    pass
  
  def save_presets(self, preset):
    '''
      Save preset options to a dictionary.
    '''
    output={}
    return output
  
  def read_data(self, input_file):
    '''
      Load data from a datafile.
      
      @param input_file Name of the file or file like object to be read from.
    '''
    self._extracted_data={}
    self._header_columns=[]
    if not type(input_file) is file:
      if input_file.endswith('.gz'):
        import gzip
        input_file=gzip.open(input_file, 'r')
      else:
        input_file=open(input_file, 'r')
    file_data=input_file.read()
    input_file.close()
    file_lines=file_data.splitlines()
    header_lines, data_lines, footer_lines=self.split_head_data_foot(file_lines)
    if not self.header_ignore_comments:
      header_lines=self.filter_comments(header_lines)
    data_lines=self.filter_comments(data_lines)
    if self.split_sequences!=0:
      split_data=self.split_data(data_lines)
    else:
      split_data=[data_lines]
    self.extract_header_information(header_lines)
    
    output=[]
    for j, data_lines in enumerate(split_data):
      data_array=self.extract_data(data_lines)
    
      num_columns=len(data_array[0])
      col_indices, dimensions, units, errors=self.get_columns(num_columns, header_lines)
      columns=[]
      for i in col_indices:
        columns.append(PhysicalProperty(dimensions[i], units[i], data_array[:, i]))
        if i in errors:
          columns[-1].error=data_array[:, errors[i]]
      self.perform_postcalcs(columns)
      dataset=MeasurementData()
      dataset.data=columns
      dataset.number=str(j)
      dataset.info="\n".join(header_lines)
      output.append(dataset)
    return output
    
  
  def split_head_data_foot(self, file_lines):
    '''
      Split the header and footer lines from the data area.
    '''
    head_end=0
    foot_start=len(file_lines)
    if self.header_lines==0:
      head_end=self.header_lines.value
      print head_end
    elif self.header_lines==2:
      if self.header_lines.value=='Number Search':
        sep=self.separator
        for i, line in enumerate(file_lines):
          try: 
            float(line.strip().split(sep)[0])
          except ValueError:
            continue
          else:
            head_end=i+1
            break
      else:
        raise NotImplementedError, "Bla"
    if self.footer_lines==0:
      foot_start=len(file_lines)-self.footer_lines.value
    else:
      raise NotImplementedError, "Bla"
    header_lines=file_lines[0:head_end]
    data_lines=file_lines[head_end:foot_start]
    footer_lines=file_lines[foot_start:]
    return header_lines, data_lines, footer_lines

  def filter_comments(self, file_lines):
    '''
      Remove comment lines from the data.
    '''
    output_lines=[]
    comment=self.comment_string
    if comment==2:
      return file_lines
    for line in file_lines:
      ls=line.strip()
      if comment==1:
        if ls.startswith(comment.value):
          continue
      else:
        for com in comment.value:
          if ls.startswith(com):
            continue
      output_lines.append(line)
    return output_lines

  def split_data(self, data_lines):
    '''
      Split different sequences of one file.
    '''
    return [data_lines]
  
  def extract_header_information(self, header_lines):
    '''
      Extract defined information from the header.
    '''
    info=self._extracted_data
    # extract header information by searching for custom strings
    for name, search_string, presplit, offset, endsplit, info_type in self.header_search:
      for i, line in enumerate(header_lines):
        try:
          idx=line.index(search_string)
        except ValueError:
          continue
        else:
          value=line[idx:].split(presplit, 1)[1][offset:].split(endsplit, 1)[0]
          try:
            info[name]=info_type(value)
          except:
            pass
          break
    # use string search to extract column information from the header

  def extract_data(self, data_lines):
    '''
      Convert the string lines into a floating point data matrix.
    '''
    # Strip empty space befoe and after each line
    if not self.skip_linestripping:
      data_lines=map(str.strip, data_lines)
    # split each line into columns
    sep=self.separator
    split_data=map(lambda line: line.split(sep), data_lines)
    if self.disable_datacheck: # fast conversion without checking each line
      data=array(split_data, dtype=float32)
      return data
    # Check data line by line
    data=[]
    for line in split_data:
      if line.strip()=="":
        # skip empty lines
        continue
      try:
        dline=map(float, line)
      except ValueError:
        continue
      else:
        data.append(dline)
    if self.skip_colcheck:
      return array(split_data, dtype=float32)
    # remove lines which do not have correct columns.
    line_len=len(data[0])
    for i in reversed(range(len(data))):
      if len(data[i])!=line_len:
        data.pop(i)
    return array(split_data, dtype=float32)

  def get_columns(self, num_columns, header_lines):
    '''
      Return the dimension and unit names of the columns.
    '''
    if self.columns==0:
      # Nothing defined
      dimensions=["Col_%02i" % i for i in range(num_columns)]
      units=["" for i in range(num_columns)]
    elif self.columns==1:
      # Columns defined as list of (dimensions,unit) tuples
      cols=self.columns.value
      num_columns=min(num_columns, len(cols))
      dimensions=[cols[i][0] for i in range(num_columns)]
      units=[cols[i][1] for i in range(num_columns)]
    else:
      raise NotImplementedError, "Blub"
    col_indices=range(num_columns)
    errors={}
    for i in reversed(col_indices):
      if i in self.error_cols:
        errors[self.error_cols[i]]=i
        col_indices.remove(i)
    return col_indices, dimensions, units, errors

  def perform_postcalcs(self, columns):
    '''
      Perform calculations on the columns for e.g. error.
    '''
    error_calcs=self.post_calc_errors
    column_calcs=self.post_calc_columns
    column_recalcs=self.post_recalc_columns
    for index, function in error_calcs:
      function=function.replace('[', 'columns[')
      columns[index].error=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
    for function, dimunit in column_calcs:
      function=function.replace('[', 'columns[')
      col=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
      if dimunit is not None:
        col.dimension=dimunit[0]
        col.dimension=dimunit[1]
      columns.append(col)
    for index, function in column_recalcs:
      function=function.replace('[', 'columns[')
      columns[index]=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
  
#-----------------------------------AbstractImportFilter-Class---------------------------------------------------#

