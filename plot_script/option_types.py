# -*- encoding: utf-8 -*-
'''
  Types used to stor option information for different other classes.
  The main purpose is to make the code more readable and automate
  the creation of option dialogs.
'''

def pystring(string):
  '''
    Change entry \\n to \n etc.
  '''
  return string.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')

class Selection(object):
  '''
    A list of string items from which one can be selected. The object can be compared
    with integer or string values to check, which item is selected.
  '''

  _selection=None
  items=[]
  name=""

  def __init__(self, items, selection, name=""):
    '''
      Constructor.
    '''
    self.name=name
    self.items=items
    self._selection=selection

  def _get_selection(self):
    return self._selection, self.items[self._selection]

  def _set_selection(self, selection):
    if selection in self.items:
      self._selection=self.items.index(selection)
    elif (type(selection) is int and selection<len(self.items) and selection>=0):
      self._selection=selection

  selection=property(_get_selection, _set_selection)

  def __repr__(self):
    output="<%s ["%self.name
    for i, item in enumerate(self.items):
      if i==self._selection:
        output+='*'
      output+=item
      if i==self._selection:
        output+='*'
      if i<(len(self.items)-1):
        output+=','
    output+="]>"
    return output

  def __str__(self):
    return self.name+'="'+self.selection[1]+'"'

  def __eq__(self, other):
    '''
      Compare the object with a int or string.
    '''
    if type(other) is int:
      return self._selection==other
    else:
      return self.items[self._selection]==other

  def __ne__(self, other):
    '''
      Compare the object with a int or string.
    '''
    return not self==other

  def __gt__(self, other):
    '''
      Compare the object with an integer.
    '''
    return self._selection>other

  def __lt__(self, other):
    '''
      Compare the object with an integer.
    '''
    return self._selection<other

  def __ge__(self, other):
    '''
      Compare the object with an integer.
    '''
    return self._selection>=other

  def __le__(self, other):
    '''
      Compare the object with an integer.
    '''
    return self._selection<=other

  def to_dict(self):
    '''
      Define how this can be stored in a dictionary.
    '''
    return {
            'selection': self.selection
            }

  def from_dict(self, in_dict):
    '''
      Define how this is restored from a dictionary.
    '''
    self.selection=in_dict['selection']


class FixedList(list):
  def __init__(self, items, entry_names):
    list.__init__(self, items)
    self.entry_names=entry_names

  def append(self, item):
    raise IndexError, "cannot append to FixedList objects"

  def to_dict(self):
    '''
      Define how this can be stored in a dictionary.
    '''
    return {
            'values': list(self)
            }

  def from_dict(self, in_dict):
    '''
      Define how this is restored from a dictionary.
    '''
    self[:]=in_dict['values']


class MultiSelection(object):
  '''
    A list of string items from which several can be selected. The object can be compared
    with integer or string values to check, which item is selected.
  '''

  _selection=[]
  items=[]
  name=""

  def __init__(self, items, selection, name=""):
    '''
      Constructor.
    '''
    self.name=name
    self.items=items
    self._selection=set(map(items.index, selection))

  def _get_selection(self):
    return self._selection, map(self.items.__getitem__, self._selection)

  def _set_selection(self, selection):
    if selection in self.items:
      self._selection.add(self.items.index(selection))
    elif hasattr(selection, '__iter__'):
      if type(selection[0]) is int:
        self._selection=set(selection)
      else:
        self._selection=set(map(self.items.index, selection))

  selection=property(_get_selection, _set_selection)

  def select(self, item, activate=True):
    '''
      Add or remove an object to the selection.
    '''
    if activate:
      if type(item) is int:
        if item<0 or item>=len(self.items):
          raise IndexError, "not in list"
        self._selection.add(item)
      else:
        if not item in self.items:
          raise IndexError, "not in list"
        self._selection.add(self.items.index(item))
    else:
      if type(item) is int:
        if item in self._selection:
          self._selection.remove(self.items.index(item))
      else:
        if self.items.index(item) in self._selection:
          self._selection.remove(self.items.index(item))

  def __repr__(self):
    output="<%s ["%self.name
    for i, item in enumerate(self.items):
      if i in self._selection:
        output+='*'
      output+=item
      if i in self._selection:
        output+='*'
      if i<(len(self.items)-1):
        output+=','
    output+="]>"
    return output

  def __str__(self):
    return self.name+'="'+self.selection[1]+'"'

  def __contains__(self, other):
    '''
      Check if object is selecte.
    '''
    if type(other) is int:
      if other<0 or other>=len(self.items):
        raise IndexError, "cannot be selected"
      return other in self._selection
    else:
      if other in self.items:
        return self.items.index(other) in self._selection
      else:
        raise IndexError, "not in item list"


class StringList(list):
  '''
    A list that only accepts string entries.
  '''
  name=""

  def __init__(self, input_, name=""):
    input_=map(str, input_)
    self.name=name
    list.__init__(self, input_)

  def append(self, item):
    list.append(self, str(item))

  def __setitem__(self, i, item):
    list.__setitem__(self, i, str(item))

  def __setslice__(self, i, j, slice_):
    list.__setslice__(self, i, j, map(str, slice_))

  def to_dict(self):
    '''
      Define how this can be stored in a dictionary.
    '''
    return {
            'values': list(self)
            }

  def from_dict(self, in_dict):
    '''
      Define how this is restored from a dictionary.
    '''
    self[:]=in_dict['values']

class PatternList(list):
  '''
    A list containing list items with specified types.
  '''
  name=""
  _pattern=None
  _description=None

  def __init__(self, input_, pattern, description=None, name=""):
    self.name=name
    self._pattern=pattern
    filtered_input=[]
    for item in input_:
      filtered_input.append([patterni(item[i]) for i, patterni in enumerate(pattern)])
    list.__init__(self, filtered_input)
    if description is None:
      description=[item.__name__ for item in pattern]
    self._description=description

  # read only attributes
  def _get_pattern(self):
    return self._pattern
  def _get_description(self):
    return self._description
  pattern=property(_get_pattern)
  description=property(_get_description)

  def __repr__(self):
    '''
      A string representation of the content of the list.
    '''
    output="<PatternList   "
    output+=", ".join(self._description)+"\n"
    for i, item in enumerate(self):
      output+="               ["
      output+=", ".join(map(str, item))
      output+="]"
      if i<(len(self)-1):
        output+="\n"
    output+=">"
    return output

  def __str__(self):
    return list.__repr__(self)

  def append(self, item):
    list.append(self, [patterni(item[idx]) for idx, patterni in enumerate(self._pattern)])

  def __setitem__(self, i, item):
    list.__setitem__(self, i, [patterni(item[idx]) for idx, patterni in enumerate(self._pattern)])

  def __setslice__(self, i, j, slice_):
    filtered_slice=[]
    for item in slice_:
      filtered_slice.append([patterni(item[idx]) for idx, patterni in enumerate(self._pattern)])
    list.__setslice__(self, i, j, filtered_slice)

  def to_dict(self):
    '''
      Define how this can be stored in a dictionary.
    '''
    values=list(self)
    for value in values:
      for i, item in enumerate(value):
        if type(item) is type:
          value[i]=item.__name__
    return {
            'values': values
            }

  def from_dict(self, in_dict):
    '''
      Define how this is restored from a dictionary.
    '''
    self[:]=in_dict['values']


class StrType(type):
  def __new__(cls, input_=""):
    if type(input_) is type:
      return str
    input_=input_.lstrip('<type').rstrip('>')
    if input_=="":
      return str
    if input_.lower() in ['integer', 'int']:
      return int
    elif input_.lower() in ['double', 'float', 'floating point', 'single']:
      return float
    else:
      return str

class OptionSwitch(object):
  '''
    A class to simplify switch settings which can be of different types.
    Can be used e.g. to be an integer in one state or dict in an other.
  '''
  name=""
  _value=None
  value_types=[]
  value_name=[]
  value_defaults=[]

  def __init__(self, value, value_types_names=[(float, 'value')], name=""):
    '''
      Construct a switch object.
    '''
    self.value_types=[]
    self.value_names=[]
    self.value_defaults=[]
    for item in value_types_names:
      self.value_types.append(item[0])
      if len(item)>1:
        self.value_names.append(item[1])
      else:
        self.value_names.append("")
      if len(item)>2:
        self.value_defaults.append(item[2])
      else:
        self.value_defaults.append(None)
    self.value=value
    self.name=name

  def items(self):
    '''
      Return list of value active, value types, names and defaults.
    '''
    return zip([i==self for i in range(len(self.value_types))],
                                           self.value_names,
                                           self.value_types,
                                           self.value_defaults)

  def _get_switch(self):
    for i, typ in enumerate(self.value_types):
      if type(self.value) is typ or (typ is StrType and type(self.value) is type):
        return i
    return-1

  def _get_value(self):
    return self._value

  def _set_value(self, value):
    if not (type(value) in self.value_types or (type(value) is type and StrType in self.value_types)):
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

  def __ne__(self, other):
    if type(other) is not type(self):
      return self.switch!=other
    else:
      return (self.value!=other.value or self.value_types!=other.value_types)

  def __repr__(self):
    if type(self.value) in [int, float, str, bool, unicode]:
      value=str(self.value)
    elif type(self.value)  is type:
      value=self.value.__name__
    elif hasattr(self.value, '__iter__'):
      value=str(type(self.value).__name__)+"[%i]"%len(self.value)
    else:
      value=type(self.value).__name__
    output='<%s switch=%i value="%s">'%(
                                            self.name,
                                            self.switch,
                                            value
                                            )
    return output


  def to_dict(self):
    '''
      Define how the object is stored in a dictionary.
    '''
    value=self.value
    if hasattr(value, 'to_dict'):
      value=value.to_dict()
    return {
            'selection': self.switch,
            'value': value,
            }

  def from_dict(self, in_dict):
    '''
      Define how the object is restored from a dicitonary.
    '''
    if self.switch==in_dict['selection']:
      if hasattr(self.value, 'from_dict'):
        self.value.from_dict(in_dict['value'])
      else:
        self.value=in_dict['value']
    else:
      switch=in_dict['selection']
      if self.value_defaults[switch] is None:
        self.value=in_dict['value']
      else:
        self.value=self.value_defaults[switch]
        if hasattr(self.value, 'from_dict'):
          self.value.from_dict(in_dict['value'])
        else:
          self.value=in_dict['value']
