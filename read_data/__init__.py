# -*- encoding: utf-8 -*-
'''
  Package containing all modules for data file reading.
  This folder containes all files which define functions to read out
  data files for the diverse import modes of plot.py.
'''

from numpy import *
import os

from option_types import *
try: # For the use in external programs where no MeasurementData objects are available
  from measurement_data_structure import MeasurementData, PhysicalProperty
  CREATE_MDS=True
except ImportError:
  CREATE_MDS=False

#+++++++++++++++++++++++++++++++++++AbstractImportFilter-Class+++++++++++++++++++++++++++++++++++++++++++++++++++#

class AsciiImportFilter(object):
  '''
    Class for importing data from any ascii source. It contains many options for the data
    readout and a readout method called with a filename or filelike object for import.
    The options can be saved/loaded to/from an dictionary to be stored in configobj instances.
  '''
  file_types=StringList([])
  name='None'
  
  header_lines=0
  header_ignore_comments=False
  header_search=[] # list of tuples (name, search_string, presplit, offset, endsplit, info_type)
  footer_lines=0
  footer_ignore_comments=False
  footer_search=[] # list of tuples (name, search_string, presplit, offset, endsplit, info_type)
  auto_search=None # tuple (left split, name/value splitter, right split)
                 # e.g.  ("\n",":",None) for lines like "Name: value"
  
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
  post_calc_errors=[]    # List of tuples (index, function)
  post_calc_columns=[]   # List of tuples (function, (dimension,unit)/None)
  post_recalc_columns=[] # List of tuples (index, function)
  
  sample_name='file_name'
  short_info='"#%i" % (sequence+1)'
  
  # Storing extracted information for further usage
  _extracted_data={}
  _header_columns=[]
  _file_data=""


  def __init__(self, name, presets=None):
    '''
      Constructor initializing the object.
      
      @param presets Dictionary to load presets from.
    '''
    # Default settings that should work with most ascii files, which use white space separators
    self.file_types=StringList([])
    self.name=str(name)
    self.header_lines=OptionSwitch(None, [(int, 'Fixed number of lines', 0), 
                                          (type(None), 'Search for number')], 
                                          "Header lines") # define how header is extracted
    self.footer_lines=OptionSwitch(0,    [(int, 'Fixed number of lines', 0), 
                                          (type(None), 'Search for number')],
                                          "Footer lines") # define how footer is extracted
    self.split_sequences=OptionSwitch(None, [(type(None), 'No splitting'), 
                                             (str, 'Split by string')], "Split Sequences")
    self.comment_string=OptionSwitch("#", [(str, 'Single string', "#"), 
                                           (StringList, 'List of strings', StringList(['#','%'])), 
                                           (type(None), 'No comments')], 
                                            "Comment Strings") # can be a list to define multiple comment types
    self.columns=OptionSwitch(None, [(type(None), 'Numerated'), 
                                     (PatternList, 'Fixed list', 
                                      PatternList([], [str, str], ['Dimension','Unit'])), 
                                     (FixedList, 'Read from header', 
                                     FixedList(['[info]', 0, 0, ',', '[', ']'], 
                                               ['Search string', 'offset lines', 'offset chars', 
                                               'split string', 'unit start', '/ end'])), 
                                      ], 
                                     "Columns")
    self.post_calc_errors=PatternList([], [int, str], ['Column', 'Function (e.g. "[1]+[2]")'])
    self.post_calc_columns=PatternList([], [str, str, str], ['Function (e.g. "[1]+[2]")', 'Dimension', 'Unit'])
    self.post_recalc_columns=PatternList([], [int, str], ['Column', 'Function (e.g. "[1]+[2]")'])
    self.header_search=PatternList([], [str, str, str, int, str, StrType], 
                                       ['name', 'search string', 'presplit', 'offset', 'endsplit', 'info_type'])
    self.footer_search=PatternList([], [str, str, str, int, str, StrType], 
                                       ['name', 'search string', 'presplit', 'offset', 'endsplit', 'info_type'])
    self.auto_search=OptionSwitch(None, [(FixedList, 'On', FixedList(['\\n', '=', '\\n'], 
                                                                     ['String before', 
                                                                     'Name/Value splitter', 
                                                                     'String after'])), 
                                          (type(None), 'Off')], 
                                          "Auto search") # define how header is extracted
    self.separator=OptionSwitch(None, [(str, 'Characters'), 
                                        (type(None), 'Whitespace')], 
                                        "Column separator") # define how header is extracted
    if presets is not None:
      self.load_presets(presets)
    
  def __repr__(self):
    return '<AsciiImportFilter "%s"(%s)>' % (
                                           self.name, 
                                           ", ".join(self.file_types)
                                           )
  
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
      Load data from a datafile. The stepwise execution allows for better testing
      of the filter settings as the result of each step can be reviewd after stopping
      due to any error. It also allows to read a file only once for test with several
      options.
      
      @param input_file Name of the file or file like object to be read from.
    '''
    self._1clear_all()
    self._2read_lines(input_file)
    self._3get_head_data_foot()
    self._4split_sequences()
    self._5remove_comments()
    self._6collect_metainfo()
    self._7extract_data()
    if CREATE_MDS:
      return self._8create_mds()
    else:
      return self._data_arrays, self._extracted_data
    
  ### The steps performed to extract the data are split to make it possible
  ### to execute them one by one for testing purpose.
  def _1clear_all(self):
    self._extracted_data={}
    self._header_columns=[]
    self._file_data=""
    self._header_lines=[]
    self._data_lines=[]
    self._footer_lines=[]
    self._sequence_headers=[]
    self._splited_data=[]
    self._data_arrays=[]
  
  def _2read_lines(self, input_file):
    '''
      Reads the raw ascii data from a text file, 
      gziped text file or file like object.
    '''
    # test if input_file is a file-like object
    if not type(input_file) is file:
      close_after=True
      if input_file.endswith('.gz'):
        import gzip
        self._extract_file_information(input_file.rsplit('.', 1)[0])
        input_file=gzip.open(input_file, 'r')
      else:
        self._extract_file_information(input_file)
        input_file=open(input_file, 'r')
    else:
      close_after=False
      self._extract_file_information(input_file.name)
    # read the ascii data
    self._file_data=input_file.read()
    if close_after:
      input_file.close()
  
  def _3get_head_data_foot(self):
    # Process the raw lines
    file_lines=self._file_data.splitlines()
    self._header_lines, self._data_lines, self._footer_lines=self._split_head_data_foot(file_lines)
  
  def _4split_sequences(self):
    # split data into different sequences
    header_lines, data_lines, footer_lines=self._header_lines, self._data_lines, self._footer_lines
    if self.split_sequences!=0:
      self._splited_data, self._sequence_headers=self._split_data(data_lines)
    else:
      self._splited_data=[data_lines]
      self._sequence_headers=[[]]

  def _5remove_comments(self):
    # remove comment lines
    header_lines, splitted_data, footer_lines=self._header_lines, self._splited_data, self._footer_lines
    if not self.header_ignore_comments:
      header_lines=self._filter_comments(header_lines)
    if not self.footer_ignore_comments:
      footer_lines=self._filter_comments(footer_lines)
    for i, data_lines in enumerate(splitted_data):
      splitted_data[i]=self._filter_comments(data_lines)
  
  def _6collect_metainfo(self):
    # collect meta info
    self._extract_information(self._header_lines, self.header_search)
    self._extract_information(self._footer_lines, self.footer_search)
    
  def _7extract_data(self):
    '''
      Converts the ascii data into a 2d array of floats.
    '''
    output=[]
    for j, data_lines in enumerate(self._splited_data):
      self._extracted_data['sequence']=j
      data_array=self._extract_data(data_lines)
      output.append(data_array)
    self._data_arrays=output
    return output
  
  def _8create_mds(self):
    output=[]
    for j, data_array in enumerate(self._data_arrays):
      num_columns=len(data_array[0])
      col_indices, dimensions, units, errors=self._get_columns(num_columns, self._header_lines)
      columns=[]
      for i in col_indices:
        columns.append(PhysicalProperty(dimensions[i], units[i], data_array[:, i]))
        if i in errors:
          columns[-1].error=data_array[:, errors[i]]
      self._perform_postcalcs(columns)
      
      dataset=MeasurementData()
      dataset.data=columns
      dataset.number=str(j)
      dataset.info="\n".join(self._header_lines)
      dataset.sample_name=str(eval(self.sample_name, globals(), dict(locals().items()+ self._extracted_data.items())))
      dataset.short_info=str(eval(self.short_info, globals(), dict(locals().items()+ self._extracted_data.items())))
      
      output.append(dataset)
    return output
    
  
  def _split_head_data_foot(self, file_lines):
    '''
      Split the header and footer lines from the data area.
    '''
    head_end=0
    foot_start=len(file_lines)
    # Define header
    if self.header_lines==0:
      head_end=self.header_lines.value
      print head_end
    elif self.header_lines==1:
      sep=self.separator.value
      for i, line in enumerate(file_lines):
        try: 
          float(line.strip().split(sep)[0])
        except ValueError:
          continue
        else:
          head_end=i+1
          break
    else:
      raise NotImplementedError, "not defined for this option: %s" % self.header_lines
    # Define footer
    if self.footer_lines==0:
      foot_start=len(file_lines)-self.footer_lines.value
    elif self.footer_lines==1:
      sep=self.separator.value
      for i, line in reversed(enumerate(file_lines)):
        try: 
          float(line.strip().split(sep)[0])
        except ValueError:
          continue
        else:
          foot_start=i+1
          break
    else:
      raise NotImplementedError, "not defined for this option: %s" % self.footer_lines
    # Create lists
    header_lines=file_lines[0:head_end]
    data_lines=file_lines[head_end:foot_start]
    footer_lines=file_lines[foot_start:]
    return header_lines, data_lines, footer_lines

  def _filter_comments(self, file_lines):
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

  def _split_data(self, data_lines):
    '''
      Split different sequences of one file.
    '''
    return [data_lines]
  
  def _extract_file_information(self, file_name):
    '''
      Fill the information dictionary with file infos.
    '''
    info=self._extracted_data
    info['file_name']=os.path.split(file_name)[1]
    info['file_type']=info['file_name'].rsplit('.', 1)[-1]
    info['file_folder']=os.path.split(os.path.abspath(file_name))[0]
    
  
  def _extract_information(self, info_lines, info_search):
    '''
      Extract defined information from the header,footer.
    '''
    info=self._extracted_data
    # extract header information by searching for custom strings
    for name, search_string, presplit, offset, endsplit, info_type in info_search:
      for i, line in enumerate(info_lines):
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
    if self.auto_search !=1:
      start_split, name_value_split, end_split=map(pystring, self.auto_search.value)
      start=0
      sstring="\n".join(info_lines)
      index=sstring.find(name_value_split, start)
      while index>=0:
        name=sstring[start:index].rsplit(start_split, 1)[1].replace(' ', '_')
        value=sstring[index+1:].split(end_split, 1)[0]
        try:
          value=float(value)
        except ValueError:
          pass
        info[name]=value
        start=index+1
        index=sstring.find(name_value_split, start)
    # use string search to extract column information from the header

  def _extract_data(self, data_lines):
    '''
      Convert the string lines into a floating point data matrix.
    '''
    # Strip empty space befoe and after each line
    if not self.skip_linestripping:
      data_lines=map(str.strip, data_lines)
    # split each line into columns
    sep=self.separator.value
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

  def _get_columns(self, num_columns, header_lines):
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
      # if the units are given as expressions, not strings they will be calculated
      try:
        dimensions=map(lambda dim: 
                       eval(dim, globals(), dict(locals().items()+ self._extracted_data.items())), 
                       dimensions)
      except:
        pass
      try:
        units=map(lambda uni: 
                       eval(uni, globals(), dict(locals().items()+ self._extracted_data.items())), 
                       units)
      except:
        pass
    else:
      # extrac the columns from header
      raise NotImplementedError, "Blub"
    col_indices=range(num_columns)
    errors={}
    for i in reversed(col_indices):
      if i in self.error_cols:
        errors[self.error_cols[i]]=i
        col_indices.remove(i)
    return col_indices, dimensions, units, errors

  def _perform_postcalcs(self, columns):
    '''
      Perform calculations on the columns for e.g. error.
    '''
    error_calcs=self.post_calc_errors
    column_calcs=self.post_calc_columns
    column_recalcs=self.post_recalc_columns
    for index, function in error_calcs:
      function=function.replace('[', 'columns[')
      columns[index].error=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
    for function, dim, unit in column_calcs:
      function=function.replace('[', 'columns[')
      col=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
      if dim is not None and unit is not None:
        col.dimension=dim
        col.dimension=unit
      columns.append(col)
    for index, function in column_recalcs:
      function=function.replace('[', 'columns[')
      columns[index]=eval(function, globals(), dict(locals().items()+ self._extracted_data.items()))
  
#-----------------------------------AbstractImportFilter-Class---------------------------------------------------#

