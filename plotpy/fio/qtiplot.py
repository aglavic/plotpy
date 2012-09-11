#-*- coding: utf8 -*-
'''
  Import for QtiPlot project files. Reads the data of all tables.
'''

import numpy
from baseread import TextReader
from plotpy.mds import MeasurementData, PhysicalProperty

class QtiReader(TextReader):
  name=u"QtiPlot"
  description=u"QtiPlot project files"
  glob_patterns=[u'*.qti']
  session='generic'

  def read(self):
    '''
      Read data from one input file if the header is correct.
    '''
    file_text=self.text_data
    if not file_text.startswith('QtiPlot'):
      self.warn("Wrong file type, header does not start with QtiPlot")
      return None
    # extract all tables
    tables=file_text.split('<table>')[1:]
    tables=[table.split('</table>')[0] for table in tables]
    output=[]
    for index, table in enumerate(tables):
      output.append(self.process_tables(table, index))
    return output

  def process_tables(self, table, index):
    '''
      Read the data of one table using the header to define column names.
    '''
    header, data=table.split('<data>')
    data=data.strip().split('</data>')[0]
    header_info=self.process_header(header)
    # split data by lines and columns
    data_lines=data.splitlines()
    data_items=map(lambda line: line.split('\t'), data_lines)
    # convert to numbers
    data=[map(self.float_convert, line) for line in data_items]
    data=numpy.array(data).transpose()
    column_names=header_info['columns']
    cols=[PhysicalProperty(column_names[i], '', data[i+1]) for i in range(len(data)-1)]
    output=MeasurementData()
    output.data=cols
    output.ydata=header_info['y-index']
    output.zdata=header_info['z-index']
    output.sample_name=self.origin[1].rsplit('.qti', 1)[0]
    output.short_info=header_info['name']
    output.number=str(index)
    return output

  def process_header(self, header):
    '''
      Read column and name information from the header of one table.
    '''
    output={}
    header_lines=header.strip().splitlines()
    output['name']=header_lines[0].split()[0]
    for line in header_lines:
      if line.startswith('header'):
        cols=line.split('\t')[1:]
        col_names=[col.split('[')[0] for col in cols]
        col_types=[col.split('[')[1][0] for col in cols]
        output['columns']=col_names
        output['col-types']=col_types
        output['y-index']=col_types.index('Y')
        if 'Z' in col_types:
          output['z-index']=col_types.index('Z')
        else:
          output['z-index']=-1
    return output

  def float_convert(self, item):
    '''
      Convert a string to float if possible, otherwise return 0.
    '''
    try:
      return float(item)
    except ValueError:
      if ':' in item:
        try:
          h, m, s=item.split(':')
          return 3600.*float(h)+60.*float(m)+float(s)
        except:
          return 0.
      else:
        return 0.

