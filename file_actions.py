#!/usr/bin/env python
'''
   Module for data treatment and macro processing.
'''

class FileActions:
  '''
    A Class designed to preform simple operations on one dataset and
    to store those in a history for later macro prosession.
  '''
  history=None
  actions=None

  def __init__(self, window):
    '''
      Constructor creating a histroy, the allowed actions
      and connecting the object to the open window.
    '''
    self.history=[]
    self.window=window
    self.actions={
                  'chang filter': self.change_data_filter
                  }

  def activate_action(self, action, *args):
    '''
      Every action performed by this class is stored so
      it can be reused for other sequences.
    '''
    self.history.append((action, args))
    self.actions[action](*args)
    self.reactivate_action(self.history[0])
    return True
  
  def reactivate_action(self, action):
    self.actions[action[0]](*action[1])

  def change_data_filter(self, filters):
    self.window.measurement[self.window.index_mess].filters=filters
