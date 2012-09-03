#-*- coding: utf8 -*-
from baseread import TextReader, BinReader

class Test1(TextReader):
  glob_patterns=["*.txt","*.dat"]
  parameters={"erste": 12.41,
              "zweite": "def"}
  
  def read(self):
    return ["abc"]

class Test2(BinReader):
  glob_patterns=["*.tif","*.dat"]

  def read(self):
    return ["abc"]
