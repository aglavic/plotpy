# -*- encoding: utf-8 -*-
'''
  Package containing all modules for data file reading.
  This folder containes all files which define functions to read out
  data files for the diverse import modes of plot.py.
'''

from numpy import *
import os

from plot_script.option_types import *

try: # For the use in external programs where no MeasurementData objects are available
  from plot_script.measurement_data_structure import MeasurementData, PhysicalProperty
  CREATE_MDS=True
except ImportError:
  CREATE_MDS=False
  config=None

defined_filters=[]

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
  header_search=[]  # list of tuples (name, search_string, presplit, offset, endsplit, info_type)
  footer_lines=0
  footer_ignore_comments=False
  footer_search=[]  # list of tuples (name, search_string, presplit, offset, endsplit, info_type)
  auto_search=None  # tuple (left split, name/value splitter, right split)
                    # e.g.  ("\n",":",None) for lines like "Name: value"
  split_sequences=None
  comment_string="#"
  columns=None
  error_cols={}

  separator=None

  # options to enamle fast readout on cost of stability
  disable_datacheck=False # don't check if all data lines contain float values
  skip_colcheck=False     # don't check if each line has the same number of columns
                          # ignored if disable_datacheck is True
  skip_linestripping=False# don't strip empty strings from each line

  # define the columns to plot
  select_x=0
  select_y=1
  select_z=-1

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
      
      :param presets: Dictionary to load presets from.
    '''
    # Default settings that should work with most ascii files, which use white space separators
    self.file_types=StringList([])
    self.name=str(name)
    self.header_lines=OptionSwitch(None, [(int, 'Fixed number of lines', 0),
                                          (type(None), 'Search for number')],
                                          "Header lines") # define how header is extracted
    self.footer_lines=OptionSwitch(0, [(int, 'Fixed number of lines', 0),
                                          (type(None), 'Search for number')],
                                          "Footer lines") # define how footer is extracted
    self.split_sequences=OptionSwitch(None, [(type(None), 'No splitting'),
                                             (str, 'Split by string')], "Split Sequences")
    self.comment_string=OptionSwitch("#", [(str, 'Single string', "#"),
                                           (StringList, 'List of strings', StringList(['#', '%'])),
                                           (type(None), 'No comments')],
                                            "Comment Strings") # can be a list to define multiple comment types
    self.columns=OptionSwitch(None, [(type(None), 'Numerated'),
                                     (PatternList, 'Fixed list',
                                      PatternList([], [str, str], ['Dimension', 'Unit'])),
                                     (FixedList, 'Read from header',
                                     FixedList(['[info]', 0, 0, ',', '[', ']'],
                                               ['Search string', 'offset lines', 'offset chars',
                                               'split string', 'unit start', '/ end'])),
                                      ],
                                     "Columns")
    self.select_x=OptionSwitch(0, [(int, 'Column index', 0),
                                    (StringList, 'Column names', StringList([]))],
                                    "x-column") # define x-column
    self.select_y=OptionSwitch(1, [(int, 'Column index', 1),
                                   (StringList, 'Column names', StringList([]))],
                                          "y-column") # define x-column
    self.select_z=OptionSwitch(-1, [(int, 'Column index',-1),
                                    (StringList, 'Column names', StringList([]))],
                                          "z-column") # define x-column
    self.post_calc_errors=PatternList([], [str, str], ['Column', 'Function (e.g. "[1]+[2]")'])
    self.post_calc_columns=PatternList([], [str, str, str], ['Function (e.g. "[1]+[2]")', 'Dimension', 'Unit'])
    self.post_recalc_columns=PatternList([], [str, str], ['Column', 'Function (e.g. "[1]+[2]")'])
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
      self.set_presets(presets)

  def __repr__(self):
    return '<AsciiImportFilter "%s"(%s)>'%(
                                           self.name,
                                           ", ".join(self.file_types)
                                           )

  # items to be used for preset load and save
  _dict_items=[
                            'sample_name',
                            'short_info',
                            'file_types',
                            'name',
                            'post_calc_errors',
                            'post_calc_columns',
                            'post_recalc_columns',
                            'header_search',
                            'footer_search',

                            'header_lines',
                            'footer_lines',
                            'split_sequences',
                            'comment_string',
                            'columns',
                            'select_x',
                            'select_y',
                            'select_z',
                            'auto_search',
                            'separator',

                               ]


  def set_presets(self, preset):
    '''
      Load preset options from a dictionary.
    '''
    #dict_items=self._dict_items
    for input_type, value in preset.items():
      old_item=getattr(self, input_type)
      etype=type(old_item)
      if type(value) is etype:
        setattr(self, input_type, etype(value))
      elif hasattr(old_item, 'from_dict'):
        old_item.from_dict(value)
      else:
        setattr(self, input_type, value)

  def get_presets(self):
    '''
      Save preset options to a dictionary.
    '''
    output={}
    for std_type in self._dict_items:
      item=getattr(self, std_type)
      if hasattr(item, 'to_dict'):
        output[std_type]=item.to_dict()
      else:
        output[std_type]=item
    return output

  def read_data(self, input_file):
    '''
      Load data from a datafile. The stepwise execution allows for better testing
      of the filter settings as the result of each step can be reviewd after stopping
      due to any error. It also allows to read a file only once for test with several
      options.
      
      :param input_file: Name of the file or file like object to be read from.
    '''
    print "Trying to import ASCII (%s) '%s'."%(self.name, input_file)
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

  def simulate_readout(self, input_file=None,
                       step_function=None,
                       report=None):
    '''
      Read a file using step by step try/except blocks.
      The data is not returned but a report is created and returned,
      which can be used to analyze any error or to check if the options
      lead to the correct import.
    '''
    steps=8.
    if step_function is None:
      # if no function is given ignore any call
      def step_function(fraction, step): pass
    if report is None:
      report=self._create_report
    step_function(0., '')
    if input_file is not None:
      self._1clear_all()
      step_function(1/steps, 'Reading file text')
      try:
        self._2read_lines(input_file)
      except Exception, error:
        return report(2, error)
      step_function(2/steps, 'Identify header/data/footer lines')
    try:
      self._3get_head_data_foot()
    except Exception, error:
      return report(3, error)
    step_function(3/steps, 'Splitting sequences')
    try:
      self._4split_sequences()
    except Exception, error:
      return report(4, error)
    step_function(4/steps, 'Remove comment lines')
    try:
      self._5remove_comments()
    except Exception, error:
      return report(5, error)
    step_function(5/steps, 'Extracting meta-info')
    try:
      self._6collect_metainfo()
    except Exception, error:
      return report(6, error)
    step_function(6/steps, 'Extracting data')
    try:
      self._7extract_data()
    except Exception, error:
      return report(7, error)
    if CREATE_MDS:
      step_function(7/steps, 'Creating MeasurementData objects')
      try:
        result=self._8create_mds()
      except Exception, error:
        return report(8, error)
    step_function(8/steps, 'Finished')
    return report(8, None, result)

  def _create_report(self, step, error, result=None):
    if error is None:
      output="Readout successfull.\n\n"
    else:
      output="Error encountered in step %i:\n"%(step)
      output+="\t%s: %s\n\n"%(type(error).__name__, error.message)
    output+="    Header/Data/Footer:   %i/%i/%i Lines\n"%(len(self._header_lines),
                                                           len(self._data_lines),
                                                           len(self._footer_lines))
    output+="        Data Sequences:   %i\n"%(len(self._splited_data))
    if len(self._data_arrays)>0:
      output+="   First Sequence Data:   %i/%i Lines/Columns"%(len(self._data_arrays[0]),
                                                                 len(self._data_arrays[0][0]))
    elif len(self._splited_data)>0:
      output+="   Sequence first line: \n%s"%self._splited_data[0][0].replace('\n', '\\n').replace('\t', '\\t')
    if error is None:
      output+="\n\tFirst extracted dataset:"
      output+="\n\t\tObject: "+result[0].__repr__()
      output+="\n\t\tSample Name: "+result[0].sample_name
      output+="\n\t\tInfo: "+result[0].short_info
      output+="\n\t\tColumns:\n\t\t\t Dimensions: "+", ".join(result[0].dimensions())
      output+="\n\t\t\t Units: "+", ".join(result[0].units())
    output+="\n\tExtracted metainfo:\n"
    output+="\n".join(["% 40s: '%s' (%s)"%("'"+str(item[0])+"'", item[1],
                       type(item[1]).__name__) for item in sorted(self._extracted_data.items())])
    return output

  def _return_report_data(self, step, error, result=None):
    output={'Step': step,
            'Error': error }

    output['header']=len(self._header_lines)
    output['footer']=len(self._footer_lines)
    output['data']=len(self._data_lines)
    output['sequences']=len(self._splited_data)
    if len(self._data_arrays)>0:
      output['first_lines']=len(self._data_arrays[0])
      output['first_cols']=len(self._data_arrays[0][0])
    else:
      output['first_lines']=0
      output['first_cols']=0
    output['metainfo']=self._extracted_data
    return output

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
    ignore, data_lines, ignore=self._header_lines, self._data_lines, self._footer_lines
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
    for data_lines in self._splited_data:
      data_array=self._extract_data(data_lines)
      output.append(data_array)
    self._data_arrays=output
    return output

  def _8create_mds(self):
    output=[]
    for j, data_array in enumerate(self._data_arrays):
      self._extracted_data['sequence']=j
      num_columns=len(data_array[0])
      col_indices, dimensions, units, errors=self._get_columns(num_columns, self._header_lines+self._sequence_headers[j])
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
      dataset.sample_name=str(eval(self.sample_name, globals(), dict(locals().items()+self._extracted_data.items())))
      dataset.short_info=str(eval(self.short_info, globals(), dict(locals().items()+self._extracted_data.items())))

      # define the x,y and z columns
      dimensions=dataset.dimensions()
      if self.select_x==0:
        dataset.xdata=self.select_x.value
      else:
        for col_name in self.select_x.value:
          if col_name in dimensions:
            dataset.xdata=dimensions.index(col_name)
            break
      if self.select_y==0:
        dataset.ydata=self.select_y.value
      else:
        for col_name in self.select_y.value:
          if col_name in dimensions:
            dataset.ydata=dimensions.index(col_name)
            break
      if self.select_z==0:
        dataset.zdata=self.select_z.value
      else:
        for col_name in self.select_z.value:
          if col_name in dimensions:
            dataset.zdata=dimensions.index(col_name)
            break

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
    elif self.header_lines==1:
      sep=self.separator.value
      for i, line in enumerate(file_lines):
        try:
          float(line.strip().split(sep)[0])
        except (ValueError, IndexError):
          continue
        else:
          head_end=i
          break
    else:
      raise NotImplementedError, "not defined for this option: %s"%self.header_lines
    # Define footer
    if self.footer_lines==0:
      foot_start=len(file_lines)-self.footer_lines.value
    elif self.footer_lines==1:
      sep=self.separator.value
      for i, line in reversed(enumerate(file_lines)):
        try:
          float(line.strip().split(sep)[0])
        except (ValueError, IndexError):
          continue
        else:
          foot_start=i
          break
    else:
      raise NotImplementedError, "not defined for this option: %s"%self.footer_lines
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
      if ls=="":
        continue
      if comment==0:
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
    output=[]
    headers=[]
    if self.split_sequences==1: # split by string
      splitstring=self.split_sequences.value
      istart=0
      for i, line in enumerate(data_lines):
        if splitstring in line:
          sequence_lines=data_lines[istart:i]
          header, data, foot=self._split_head_data_foot(sequence_lines)
          output.append(data)
          headers.append(header+foot)
          istart=i+1
      header, data, foot=self._split_head_data_foot(data_lines[istart:])
      output.append(data)
      headers.append(header+foot)
    return output, headers

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
      for line in info_lines:
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
    if self.auto_search!=1:
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
    for i, line in enumerate(split_data):
      if data_lines[i].strip()=="":
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
      dimensions=["Col_%02i"%i for i in range(num_columns)]
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
                       eval(dim, globals(), dict(locals().items()+self._extracted_data.items())),
                       dimensions)
      except:
        pass
      try:
        units=map(lambda uni:
                       eval(uni, globals(), dict(locals().items()+self._extracted_data.items())),
                       units)
      except:
        pass
    elif self.columns==2:
      # search for a key string and define columns from the following characters
      keystr, line_offset, char_offset, split_str, unit_start, unit_end=self.columns.value
      for i, line in enumerate(header_lines):
        if keystr in line:
          colstr=header_lines[i+line_offset][char_offset:]
          cols=colstr.split(split_str)
          dims, units=[], []
          for col in cols:
            scol=col.split(unit_start)
            dims.append(scol[0])
            if len(scol)>1:
              units.append(scol[1].split(unit_end)[0])
            else:
              units.append('')
      num_columns=min(num_columns, len(dims))
      dimensions=dims[:num_columns]
      units=units[:num_columns]
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
      function=self._turn_name_to_index(function, columns)
      index=self._str_to_column_index(index, columns)
      columns[index].error=eval(function, globals(), dict(locals().items()+self._extracted_data.items()))
    for function, dim, unit in column_calcs:
      function=self._turn_name_to_index(function, columns)
      col=eval(function, globals(), dict(locals().items()+self._extracted_data.items()))
      if dim is not None and unit is not None:
        col.unit=dim
        col.dimension=unit
      columns.append(col)
    for index, function in column_recalcs:
      function=self._turn_name_to_index(function, columns)
      index=self._str_to_column_index(index, columns)
      columns[index]=eval(function, globals(), dict(locals().items()+self._extracted_data.items()))

  def _turn_name_to_index(self, code, columns):
    '''
      Change column names in a code snipet to column indices.
    '''
    names=[column.dimension for column in columns]
    for i, name in enumerate(names):
      code=code.replace('[%s]'%name, '[%i]'%i)
      code=code.replace('[%i]'%i, 'columns[%i]'%i)
    return code

  def _str_to_column_index(self, index, columns):
    '''
      Change index string or name to the column index.
    '''
    try:
      return int(index)
    except ValueError:
      names=[column.dimension for column in columns]
      for i, name in enumerate(names):
        if name==index:
          return i

#-----------------------------------AbstractImportFilter-Class---------------------------------------------------#

def append_filter(filter_):
  '''
    Add a filter_ to the list of known import filters.
  '''
  if filter_ in defined_filters:
    return
  defined_filters.append(filter_)
  if config is not None:
    config[filter_.name]=filter_.get_presets()
    config.write()

try:
  from configobj import ConfigObj
  config=ConfigObj(os.path.expanduser('~')+'/.plotting_gui/ascii_importer.ini', unrepr=True, indent_type='\t')
  for name, presets in config.items():
    defined_filters.append(AsciiImportFilter(name, presets=presets))
except ImportError:
  config=None
