# -*- encoding: utf-8 -*-
'''
  Implementation of a template framework to make it possible for the user to import any ascii column data.
'''

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

import os

from plot_script import measurement_data_structure
import numpy as np
MeasurementDataClass=measurement_data_structure.MeasurementData

class DataImportTemplate(object):
  '''
    Class framework to import ascii data files with different settings defined in user templates.
    Can be used for any filetype instead of the normal import framework.
  '''
  name='Unnamed'
  wildcards=[]

  def __init__(self, template_name):
    '''
      Create a template import object, which can be used to import a specific type of file.
    '''
    # check if template file exists:
    try:
      template_file=open(template_name, 'r')
      template_code=compile(template_file.read(), os.path.split(template_name)[1], 'exec')
      template_file.close()
      self.compile_template(template_code)
      self.MeasurementData=MeasurementDataClass
    except IOError:
      raise IOError, "Template file %s not found"%template_name
    except SyntaxError:
      raise SyntaxError, "Error in Template syntax"

  def compile_template(self, template_code):
    '''
      Evaluate all settings in the template and add them to this object.
      
      :param template_code: Code object returned by compile function
      
      :return: If evaluation was successful.
    '''
    # run the code, which defines some local variables
    exec(template_code)
    # check if all needed variables are set in template
    # UndefinedVariables should be defined in the template
    try:
      general #@UndefinedVariable
      header #@UndefinedVariable
      columns #@UndefinedVariable
      splitting #@UndefinedVariable
      footer #@UndefinedVariable
    except NameError, error_text:
      raise SyntaxError, "Compiling template failed, not all needed variables are defined: %s"%error_text
    # go through the local variables and set options accordingly.

    ## General
    if 'name' in general: #@UndefinedVariable
      self.name=general['name'] #@UndefinedVariable
    if 'comments' in general: #@UndefinedVariable
      self.comments=general['comments'] #@UndefinedVariable
    else:
      self.comments=[]
    if 'split string' in general: #@UndefinedVariable
      self.split_string=general['split string'] #@UndefinedVariable
    else:
      self.split_string=None
    if 'sample' in general: #@UndefinedVariable
      self.sample=general['sample'] #@UndefinedVariable
    else:
      self.sample=''
    if 'short info' in general: #@UndefinedVariable
      self.short_info=general['short info'] #@UndefinedVariable
    else:
      self.short_info=''
    if 'info' in general: #@UndefinedVariable
      self.info=general['info'] #@UndefinedVariable
    else:
      self.info='<header>'

    ## Header
    if 'length' in header: #@UndefinedVariable
      self.header_fixed_length=True
      self.header_length=int(header['length']) #@UndefinedVariable
    else:
      self.header_fixed_length=False
    self.header_use_comment=('use comment' in header and header['use comment']) #@UndefinedVariable
    self.header_use_number_search=('use number search' in header and header['use number search']) #@UndefinedVariable
    if 'search keyword' in header: #@UndefinedVariable
      self.header_keyword_search=header['search keyword'] #@UndefinedVariable
    else:
      self.header_keyword_search=None

    ## Columns
    if 'columns' in columns: #@UndefinedVariable
      self.columns_fixed=True
      self.columns=columns['columns'] #@UndefinedVariable
    else:
      self.columns_fixed=False
    if 'from header' in columns: #@UndefinedVariable
      self.columns_from_header=columns['from header'] #@UndefinedVariable
      if 'header column splitting' in columns: #@UndefinedVariable
        self.columns_header_splitting=columns['header column splitting'] #@UndefinedVariable
      else:
        self.columns_header_splitting=None
    else:
      self.columns_from_header=None
    if 'columns map' in columns: #@UndefinedVariable
      self.columns_map=columns['columns map'] #@UndefinedVariable
    else:
      self.columns_map=None
    if 'ignore' in columns: #@UndefinedVariable
      self.columns_ignore=columns['ignore'] #@UndefinedVariable
    else:
      self.columns_ignore=[]
    if 'column from function' in columns: #@UndefinedVariable
      self.columns_from_function=columns['column from function'] #@UndefinedVariable
    else:
      self.columns_from_function=[]
    if 'plot columns' in columns: #@UndefinedVariable
      self.columns_plot_map=columns['plot columns'] #@UndefinedVariable
    else:
      self.columns_plot_map=None
    self.ignore_comment=('ignore comment' in columns and columns['ignore comment']) #@UndefinedVariable

    ## Sequence splitting
    self.splitting_use_comment=('use comment' in splitting and splitting['use comment']) #@UndefinedVariable
    self.splitting_use_empty=('use empty' in splitting and splitting['use empty']) #@UndefinedVariable
    if 'use string' in splitting: #@UndefinedVariable
      self.splitting_strings=splitting['use string'] #@UndefinedVariable
    else:
      self.splitting_strings=None
    if 'read new columns' in splitting: #@UndefinedVariable
      self.columns_from_splitting=splitting['read new columns'] #@UndefinedVariable
    else:
      self.columns_from_splitting=None

    ## Footer
    if 'length' in footer: #@UndefinedVariable
      self.footer_fixed_length=True
      self.footer_length=footer['length'] #@UndefinedVariable
    else:
      self.footer_fixed_length=False
    self.footer_use_comment=('use comment' in footer and footer['use comment']) #@UndefinedVariable
    self.footer_use_number_search=('use number search' in footer and footer['use number search']) #@UndefinedVariable
    if 'search keyword' in footer: #@UndefinedVariable
      self.footer_keyword_search=footer['search keyword'] #@UndefinedVariable
    else:
      self.footer_keyword_search=None

    ## Search patterns for string replacement
    if 'search pattern' in header: #@UndefinedVariable
      self.header_search_patterns=header['search pattern'] #@UndefinedVariable
    else:
      self.header_search_patterns={}
    if 'search pattern' in splitting: #@UndefinedVariable
      self.splitting_search_patterns=splitting['search pattern'] #@UndefinedVariable
    else:
      self.splitting_search_patterns={}
    if 'search pattern' in footer: #@UndefinedVariable
      self.footer_search_patterns=footer['search pattern'] #@UndefinedVariable
    else:
      self.footer_search_patterns={}

    ## Define wildcards to use for this template
    try:
      self.wildcards=type_info['wildcards'] #@UndefinedVariable
    except (NameError, KeyError):
      self.wildcards=['*']
    return True

  #++++++++++++++++++++++ Reading methods +++++++++++++++++++++++++++

  def __call__(self, file_name):
    '''
      Function directly called to import data.
      
      :param file_name: Input file name to read the data from
      
      :return: A list of MeasurementData or derived objects
    '''
    if not os.path.exists(file_name):
      print "File %s not found"%file_name
      return 'NULL'
    self.replacements={}
    self.number=0
    data_lines=open(file_name, 'r').read().splitlines()
    # read the file header and footer
    header=self.read_header(data_lines)
    footer=self.read_footer(data_lines)
    # determine the data sequences and get lines in between the sequences
    data_sequences, split_lines=self.get_sequences(data_lines)
    output=[]
    # initialize the replacement strings found in the header and footer
    self.init_initial=True
    self.init_replacements(header, self.header_search_patterns)
    self.init_replacements(footer, self.footer_search_patterns)
    self.init_new_sequence(header)
    for sequence, split_line in zip(data_sequences, split_lines):
      if len(self.dimensions)<2 or len(sequence)<2:
        if len(split_line)!=0:
          # update any replacements which could come from the inter sequence lines
          # if applicable also change the columns for the next dataset
          self.init_new_sequence(split_line)
          self.init_replacements(split_line, self.splitting_search_patterns)
        continue
      # create a data object
      dataset=self.new_dataset()
      # read the datalines of one sequence
      self.read_data(sequence, dataset)
      if len(split_line)!=0:
        # update any replacements which could come from the inter sequence lines
        # if applicable also change the columns for the next dataset
        self.init_new_sequence(split_line)
        self.init_replacements(split_line, self.splitting_search_patterns)
      output.append(dataset)
      self.number+=0
    return output

  def read_header(self, lines):
    '''
      Get the header size and read needed information from this header.
      Defines the region to start looking for data.
      
      :param lines: Lines from the input file
      
      :return: Part of lines which belogs to the header
    '''
    if not self.header_fixed_length:
      self.header_length=0
      if self.header_use_comment:
        # search for first line which doesn't start with a comment
        for i, line in enumerate(lines):
          ls=line.strip()
          if not ls[0] in self.comments and ls!='':
            if i>self.header_length:
              self.header_length=i
            break
      if self.header_keyword_search:
        # search for the first line containing a keyword
        kw, offset=self.header_keyword_search
        joined="\n".join(lines)
        if kw in joined:
          i=len(joined.split(kw)[0].splitlines())+offset
          if i>self.header_length:
            self.header_length=i
      if self.header_use_number_search:
        # search for the first line starting with a number
        for i, line in enumerate(lines):
          if line.strip()=='':
            continue
          first=line.split(self.split_string)[0]
          try:
            float(first)
            if i>self.header_length:
              self.header_length=i
            break
          except ValueError:
            continue
    if self.header_length==len(lines):
      raise IndexError, 'Header expands to hole file length'
    header=lines[:self.header_length]
    self.replacements['header']="\n".join(header)
    return header

  def read_footer(self, lines):
    '''
      Get the footer size and read needed information from this footer.
      Defines the region to end looking for data.
      
      :param lines: Lines from the input file
      
      :return: Part of lines which belogs to the footer
    '''
    if not self.footer_fixed_length:
      self.footer_length=0
      if self.footer_use_comment:
        # search for first line which doesn't start with a comment
        for i, line in enumerate(reversed(lines)):
          ls=line.strip()
          if not ls[0] in self.comments and ls!='':
            if i>self.footer_length:
              self.footer_length=i
            break
      if self.footer_keyword_search:
        # search for the first line containing a keyword
        kw, offset=self.footer_keyword_search
        joined="\n".join(reversed(lines))
        if kw in joined:
          i=len(joined.split(kw)[0].splitlines())-offset
          if i>self.footer_length:
            self.footer_length=i
      if self.footer_use_number_search:
        # search for the first line starting with a number
        for i, line in enumerate(reversed(lines)):
          if line.strip()=='':
            continue
          first=line.split(self.split_string)[0]
          try:
            float(first)
            if i>self.footer_length:
              self.footer_length=i
            break
          except ValueError:
            continue
    if (self.footer_length+self.header_length)==len(lines):
      raise IndexError, 'Footer+Header expands to the hole file length'
    return lines[-self.footer_length-1:]

  def read_data(self, lines, dataset):
    '''
      Read data from input lines and append it to a dataset object.
      
      :param lines: Lines of the file to be used as data
      :param dataset: MeasurementData or derived object
    '''
    # remove empty lines
    lines=map(lambda line: line.strip(), lines)
    lines=filter(lambda line: line!='', lines)
    # remove comment lines
    if not self.ignore_comment:
      lines=filter(lambda line: line.strip()[0] not in self.comments, lines)
    splitted_input=map(lambda line: line.split(self.split_string), lines)
    splitted_lines=np.array(splitted_input).transpose().tolist()
    for i in reversed(self.ignore):
      splitted_lines.pop(i)
    def to_float(item):
      # return float of input or 0. if conversion is not possible
      try:
        return float(item)
      except ValueError:
        return 0.
    # calculate float values for every column entry and crop the columns of interest
    data_cols=map(lambda column: map(to_float, column), splitted_lines)[:len(self.units)-len(self.columns_from_function)]
    data_cols+=self.calculate_columns_from_function(data_cols)
    # fill data object with read values
    for i, col in enumerate(data_cols):
      dataset.data[i].values=col
    # make sure all data objects are filled
    while i<len(dataset.data)-1:
      i+=1
      dataset.data[i].values=list(dataset.data[i-1].values)

  def calculate_columns_from_function(self, data_cols):
    '''
      Calculate new column values from imported columns from functions given in the template.
      
      :param data_cols: the columns of the already read data.
      
      :return: List of new columns that have been created
    '''
    data_arrays=map(np.array, data_cols)
    output=[]
    for function, ignore, ignore in self.columns_from_function:
      function=self.replace(function)
      # replace the dimensions in the function by the internal variable for this
      for i, dim in enumerate(self.dimensions):
        function=function.replace('[%s]'%dim, 'data_arrays[%i]'%i)
      try:
        new_col=eval(function)
        data_arrays.append(new_col)
        output.append(new_col.tolist())
      except SyntaxError:
        print "Syntax error in function %s"%function
        output.append((data_arrays[0]*0.).tolist())
    return output

  def get_sequences(self, lines):
    '''
      Extract measured sequences and inter sequence lines.
      
      :param lines: Lines from the input file
      
      :return: List of sequence lines containing data, List of inter sequence lines
    '''
    if self.footer_length>0:
      relevant_lines=lines[self.header_length:-self.footer_length]
    else:
      relevant_lines=lines[self.header_length:]
    sequences=[[]]
    inter_sequences=[]
    if self.splitting_use_empty:
      search=True
      def start_interregion(line):
        return line.strip()==''
      def end_interregion(line):
        return line.strip()!='', False
    elif self.splitting_use_comment:
      search=True
      comments=self.comments
      def start_interregion(line):
        return line.strip()[0] in comments
      def end_interregion(line):
        return line.strip()[0] not in comments, False
    elif self.splitting_strings:
      search=True
      split_start=self.splitting_strings[0]
      split_end=self.splitting_strings[1]
      def start_interregion(line):
        return split_start in line
      def end_interregion(line):
        return split_end in line, True
    else:
      search=False
      sequences=[relevant_lines]
      inter_sequences=[[]]
    if search:
      inter_active=False
      for line in relevant_lines:
        if not inter_active:
          if start_interregion(line):
            inter_active=True
            inter_sequences.append([])
            inter_sequences[-1].append(line)
          else:
            sequences[-1].append(line)
        else:
          if end_interregion(line)[0] and not end_interregion(line)[1]:
            inter_active=False
            sequences.append([])
            sequences[-1].append(line)
          elif end_interregion(line)[0]:
            inter_active=False
            sequences.append([])
            inter_sequences[-1].append(line)
          else:
            inter_sequences[-1].append(line)
    if len(inter_sequences)<len(sequences):
      inter_sequences.append([])
    return sequences, inter_sequences

  def init_replacements(self, lines, split_patterns):
    '''
      Search for patterns in the input lines and add the result to the objects
      patterns dictionary.
    '''
    replacements=self.replacements
    joint_string="\n".join(lines)
    for key, pattern, forward, split_string, offset in split_patterns:
      if pattern in joint_string:
        if forward:
          try:
            if not '\n' in split_string:
              result=joint_string.split(pattern, 1)[1].splitlines()[0].strip().split(split_string)[offset]
            else:
              result=joint_string.split(pattern, 1)[1].split(split_string)[offset]
          except IndexError:
            continue
        else:
          try:
            if not '\n' in split_string:
              result=joint_string.rsplit(pattern, 1)[0].splitlines()[-1].strip().split(split_string)[-offset-1]
            else:
              result=joint_string.rsplit(pattern, 1)[0].split(split_string)[-offset-1]
          except IndexError:
            continue
        replacements[key]=result

  def init_new_sequence(self, lines):
    '''
      Make changes for the next read sequence according to header/intersequence lines.
      Defines the columns to be imported.
      
      :param lines: Header/intersequence lines to be used for the initialization
    '''
    self.ignore=list(self.columns_ignore)
    if not self.columns_fixed:
      # Get the columns to be used
      if (self.init_initial and self.columns_from_header):
        line=lines[self.columns_from_header[0]]
        splitted_line=line.split((self.columns_from_header[1] or self.split_string))
        columns=splitted_line[self.columns_from_header[2]:self.columns_from_header[3]]
      elif self.columns_from_splitting:
        line=lines[self.columns_from_splitting[0]]
        splitted_line=line.split(self.columns_from_splitting[1] or self.split_string)
        columns=splitted_line[self.columns_from_splitting[2]:self.columns_from_splitting[3]]
      if self.columns_header_splitting:
        # Split the string read as columns to dimension and unit
        chs=self.columns_header_splitting
        self.columns=[column.lstrip(chs[0]).rstrip(chs[2]).split(chs[1]) for column in columns]
      elif self.columns_map:
        # use a dictionary to map columns to given dimensions and units
        # columns not found in the map are ignored
        maping=self.columns_map
        self.columns=[]
        for i, column in enumerate(columns):
          if column in maping:
            self.columns.append(maping[column])
          else:
            self.columns.append((column, ''))
            self.ignore.append(i)
            self.ignore.sort()
      else:
        self.columns=[(column, '') for column in columns]
    for i, column in enumerate(self.columns):
      if len(column)==1:
        self.columns[i]=(column[0], '')
    # define units and dimensions and replace placeholders
    dimensions=[self.replace(column[0]) for column in self.columns]
    units=[self.replace(column[1]) for column in self.columns]
    # add columns calculated from functions
    for ignore, dimension, unit  in self.columns_from_function:
      for i, dim in enumerate(dimensions):
        unit=unit.replace('[%s]'%dim, units[i])
      dimensions.append(self.replace(dimension))
      units.append(self.replace(unit))
    for i in reversed(self.ignore):
      dimensions.pop(i)
      units.pop(i)
    if self.columns_plot_map:
      # define which columns should be plotted agains each other
      pm=self.columns_plot_map
      self.x=0
      self.y=1
      self.error=2
      self.z=-1
      for i, dimension in enumerate(dimensions):
        if dimension in map(self.replace, pm['x']):
          self.x=i
        if dimension in map(self.replace, pm['y']):
          self.y=i
        if dimension in map(self.replace, pm['error']):
          self.error=i
        if ('z' in pm) and dimension in map(self.replace, pm['z']):
          self.z=i

    self.dimensions=dimensions
    self.units=units
    self.init_initial=False

  def new_dataset(self):
    '''
      Create a new data object from the active column and replacement settings.
      
      :return: MeasurementData or derived object
    '''
    dataset=self.MeasurementData(zip(self.dimensions, self.units), (), self.x, self.y, self.error, self.z)
    dataset.sample_name=self.replace(self.sample)
    dataset.short_info=self.replace(self.short_info)
    dataset.info=self.replace(self.info)
    dataset.number=str(self.number)
    return dataset

  def replace(self, string):
    '''
      Replace placeholders in string by the settings read from the input file.
      
      :return: changed string
    '''
    # Find tags starting with < and ending with >
    tags=map(lambda item: item.split('>')[0],
             filter(lambda item: '>' in item,
                    string.split('<')))
    # remove double entries
    tags=list(set(tags))
    splitted_tags=[]
    for tag in tags:
      if '|' in tag:
        splitted_tags.append(tag.split('|'))
      else:
        splitted_tags.append(['', tag, ''])
    for i, splittag in enumerate(splitted_tags):
      # every tag is replaced by the according value, if it doesn't exist
      # the tag is removed from the string
      if splittag[1] in self.replacements:
        string=string.replace('<'+tags[i]+'>', splittag[0]+self.replacements[splittag[1]]+splittag[2])
      else:
        string=string.replace('<'+tags[i]+'>', '')
    return string
