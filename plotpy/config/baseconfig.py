# -*- coding: utf-8 -*-
'''
  Basis of the configuration system. The :class:`ConfigProxy` object
  combines module parameter with temporary and user changeable
  configuration file options. When used in other modules
  this facility is completely hidden to the API. 
'''

import os
import atexit
from plotpy.message import error
from plotpy.configobj import ConfigObj, ConfigObjError


class ConfigProxy(object):
  '''
  Handling of configuration options with temporal and fixed storage to .ini files
  in the used folder.
  Each configuration has it's own ConfigHolder object for access but one .ini file
  can hold several configurations.
  '''

  default_storage='general'
  config_path=''
  configs={}
  storages={}

  def __init__(self, config_path):
    self.configs={}
    self.storages={}
    self.tmp_storages={}
    self.config_path=config_path
    # store .ini files on interpreter exit
    atexit.register(self.store)

  def add_config(self, name, items, storage=''):
    '''
    Crate a new dictionary connected to a storage config file.
    
    :returns: The corresponding :class:`ConfigHolder` object.
    '''
    if storage=='':
      storage=self.default_storage
    if storage is None:
      storage='_temp'
      if not '_temp' in self.storages:
        self.tmp_storages[storage]={}
        # use the exact same dictionary object
        self.storages[storage]=self.tmp_storages[storage]
    elif not storage in self.storages:
      sfile=os.path.join(self.config_path, storage+'.ini')
      try:
        self.storages[storage]=ConfigObj(
                                        infile=sfile,
                                        unrepr=True,
                                        encoding='utf8',
                                        indent_type='    ',
                                        )
      except ConfigObjError:
        error("Could not parse configfile %s, using temporary config.\nFix or delete the file!"%sfile)
        self.storages[storage]={}
      self.tmp_storages[storage]={}
    self.configs[name]=storage
    if name in self.storages[storage]:
      # update additional options from config
      for key, value in items.items():
        if not key in self.storages[storage][name]:
          self.storages[storage][name][key]=value
    else:
      self.storages[storage][name]=dict(items)
    self.tmp_storages[storage][name]={}
    return self[name]

  def store(self):
    """store configuration data into .ini files."""
    for item in self.storages.values():
      if not hasattr(item, 'write'):
        continue
      # remove constants for storage
      for config in item.values():
        for key in config.keys():
          if key==key.upper():
            del(config[key])
      # only write to ConfigObj items
        item.write()

  def __getitem__(self, name):
    if isinstance(name, basestring):
      if name in self.configs:
        return ConfigHolder(self, name)
      raise KeyError, "%s is no known configuration"%name
    else:
      raise KeyError, "Only strings are allowed as keys"

  def get_config_item(self, config, item):
    """Called by :class:`ConfigHolder` to retreive an item"""
    if not config in self.configs:
      raise KeyError, "%s is no known configuration"%config
    storage=self.configs[config]
    if item in self.tmp_storages[storage][config]:
      # if value has been stored temporarily, return it
      return self.tmp_storages[storage][config][item]
    return self.storages[storage][config][item]

  def set_config_item(self, config, item, value, temporary=False):
    """Called by :class:`ConfigHolder` to set an item value"""
    if not config in self.configs:
      raise KeyError, "%s is no known configuration"%config
    storage=self.configs[config]
    if temporary:
      # if value has been stored temporarily, return it
      self.tmp_storages[storage][config][item]=value
    else:
      self.storages[storage][config][item]=value

  def get_config_keys(self, config):
    """Called by :class:`ConfigHolder` to get the keys for it's config"""
    if not config in self.configs:
      raise KeyError, "%s is no known configuration"%config
    storage=self.configs[config]
    return self.storages[storage][config].keys()

  def keys(self):
    """Return the available configurations"""
    keys=self.configs.keys()
    keys.sort()
    return keys

  def values(self):
    return [self[key] for key in self.keys()]

  def items(self):
    return [(key, self[key]) for key in self.keys()]

  def __len__(self):
    return len(self.keys())

  def __repr__(self):
    output=self.__class__.__name__
    output+='(storages=%i, configs=%i)'%(len(self.storages), len(self))
    return output



class ConfigHolder(object):
  '''
  Dictionary like object connected to the a :class:`ConfigProxy` reading
  and writing values directly to that object.
  Each key can also be accessed as attribute of the object.
  
  To store items temporarily, the object supports a "temp"
  attribute, which itself is a ConfigHolder object. 
  '''

  def __init__(self, proxy, name, storetmp=False):
    self._proxy=proxy
    self._name=name
    self._storetmp=storetmp

  def _get_tmporary(self):
    return ConfigHolder(self._proxy, self._name, storetmp=True)

  temp=property(_get_tmporary,
          doc="A representation of this :class:`ConfigHolder` which stores items only for this session.")

  def __getattribute__(self, name):
    if name.startswith('_') or name in dir(ConfigHolder):
      return object.__getattribute__(self, name)
    else:
      return self._proxy.get_config_item(self._name, name)

  def __setattr__(self, name, value):
    if name.startswith('_') or name in dir(ConfigHolder):
      object.__setattr__(self, name, value)
    else:
      if name==name.upper():
        raise ValueError, "%s is a constant and thus cannot be altered"%name
      self._proxy.set_config_item(self._name, name, value,
                                  temporary=self._storetmp)

  def __getitem__(self, name):
    return self.__getattribute__(name)

  def __setitem__(self, name, value):
    return self.__setattr__(name, value)

  def __contains__(self, other):
    return other in self.keys()

  def keys(self):
    return self._proxy.get_config_keys(self._name)

  def values(self):
    return [self[key] for key in self.keys()]

  def items(self):
    return [(key, self[key]) for key in self.keys()]

  def __repr__(self):
    output=self.__class__.__name__+'('
    spacer='\n'+' '*len(output)
    output+=repr(dict(self.items())).replace('\n', spacer)
    output+=' )'
    return output

  def __dir__(self):
    return self.__dict__.keys()+self.keys()
