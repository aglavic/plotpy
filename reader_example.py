# -*- encoding: utf-8 -*-
'''
  Example module for file reader classes. Such a module needs only
  to be placed in the plotpy/fio folder to be automatically recognized.
  Each reader class has to be derived from TextReader or BinReader
  defined in plotpy.fio.baseread.
'''

# This will be the typical imports needed.
# Only use buildin python modules and numpy
# here. Other dependencies should be imported
# in the __init__ method of each class to
# ensure compatibility.
import numpy
from baseread import TextReader, BinReader
from plotpy.mds import MeasurementData, PhysicalProperty


class TextExample(TextReader):
  '''
    This is an example of a file type, which uses a text
    base data structure. The file will be automatically
    parsed to unicode, if no encoding attribute is defined,
    utf8 is assumed.
  '''
  # some general parameters of the reader
  name=u"Test" # name shown on e.g. readout
  description=u"Test import filter"
  glob_patterns=[u'*.txt'] # list of glob patterns supported
  session='squid' # session associated with this file type
  encoding='iso-8859-1' # encoding of the files
  
  def __init__(self):
    # if you want to use non buildin modules
    # you can import them here
    global scipy
    import scipy

  def read(self):
    # This is the main method called after readout 
    # for file parsing. The raw_data and text_data
    # attributes are set to the file content already.
    # This should return ither None if the readout
    # failed or a list of MeasurementData objects
    # containing the data.
    input_data=self.text_data
    
    # it is a good practice to check the file type
    # to make a quick abbort possible
    # (and switch to another reader if possible)
    if not '[my header text]' in input_data:
      # use the self.info/self.warn/self.error methods
      # to give the user informations.
      self.warn('Not the right file header')
      return None
    
    # not the data can be treated in sub-methods
    output=self.read_sequences()
    return output

  def read_sequences(self):
    # An example of a file type which includes several sequences
    # which always start with the "[Start]" keyword
    input_data=self.text_data
    items=input_data.split('[Start]')
    header=items[0]
    data=items[1:]
    header_info=self.read_header(header)
    output=[]
    for i, sec in enumerate(data):
      # update the progress bar without a text
      self.info(progress=float(i)/(len(data)+1.))
      output.append(self.read_sequence(header_info, sec))
      output[-1].short_info="#%i"%i
    return output
  
  def read_header(self, header):
    # progress header string ....
    #
    #...
    return something
  
  def read_sequence(header_info, sec):
    # The sequence is a comma separated
    # data, which is parsed in this method
    # and returned as MeasurementData object.
    
    # remove blank lines and line-breaks
    sec=sec.strip()
    # Convert the data string to a numpy array
    # of columns.
    # If the string was first split into
    # a list of lines using text_data.splitlines()
    # you can use list2data
    cols=self.str2data(sec, sep=',')
    # new data object using columns 3 and 5 as x/y
    output=MeasurementData(x=3, y=5)
    for col,info in zip(cols[:len(cols)/2], header_info['columns']):
      output.data.append(PhysicalProperty(info[0], info[1], col))
    for i,col in enumerate(cols[len(cols)/2:]):
      output.data[i].error=col
    output.sample_name=header_info['sample']
    return output
