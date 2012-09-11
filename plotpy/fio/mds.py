'''
  Reader and Writer for the binary plotpy format (mds, mdd)
'''

import os
from cPickle import loads
from baseread import BinReader

class MDSReader(BinReader):
  name=u"Plotpy"
  description=u"Plotpy binary files"
  glob_patterns=[u'*.mds', u'*.mdd']
  session='generic'

  def __init__(self):
    # for compatibility with older versions
    import sys
    sys.modules['plot_script']=sys.modules['plotpy']
    sys.modules['plot_script.measurement_data_structure']=sys.modules['plotpy.mds']

  def read(self):
    dump_obj=loads(self.raw_data)
    if type(dump_obj) is dict:
      # new type snapshot
      if 'multiplots' in dump_obj and dump_obj['multiplots']:
        self.origin='Multiplot'
      else:
        if type(dump_obj['origin']) is basestring:
          self.origin=os.path.split(dump_obj['origin'])
        else:
          self.origin=dump_obj['origin']
      output=dump_obj['data']
      self.session=dump_obj['session']
    else:
      # old type snapshot
      output=dump_obj
      for i, ds in enumerate(output):
        if ds.number=='':
          ds.number="%i"%i
      self.session='generic'
    return output
