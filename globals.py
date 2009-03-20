#!/usr/bin/env python
# Variables used as globals for all modules (.py files) of the plotting script collection.
# Usage does not change this file!
# Pleas do not make any changes here unless you know what you are doing.
import os

global debug
global debug_file
global own_pid
global temp_dir

debug=False
debug_file=None
own_pid=""
# starting with global temp directory, subdir added during execution depending on process ID (own_pid)
if (os.getenv("TEMP")==None):
  # Linux case
  temp_dir="/tmp/"
# name of the gnuplot command under linux
  gnuplot_command="gnuplot"
  def replace_systemdependent(string):
    return string
else:
  # Windows case
  temp_dir=os.getenv("TEMP")+'\\'
# name of the gnuplot command under windows
  gnuplot_command="pgnuplot"
  def replace_systemdependent(string): # replace backthlash by double backthlash for gnuplot under windows
    return string.replace('\\','\\\\').replace('\\\\\n','\\\n')
