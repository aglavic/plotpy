#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Plotpy package for data plotting and analyzing for different instruments.
  
  Subpackages and modules:
  
    ========== === =============================================
    Name       P/M Description
    ========== === =============================================
    config     P   Configurational parameters for many modules
    fio        P   Datafile input and output functionality.
                   Can be used by external projects to read
                   datafiles (from plotpy.fio import reader)
    gtkgui     P   Graphical user interface modules
    plugins    P   Plugin facility autoloading available modules
    sessions   P   Modules for the dfferent experimental types
    configobj  M   A configuration writer with .ini format
    fitdata    M   Fit function framework and set of default
                   functions
    mds        M   Measurement data structure classes used
                   to store and process data.
    message    M   Plotpy message facility used for GUI and
                   command line.
    peakfinder M   Continous wavelet transform peakfinder 
                   routine, can be used as stand alone module.
    plotting   M   Functions to communicate with gnuplot  
    ========== === =============================================
    
  The program is started using the _run function.
'''

from info import __author__, __copyright__, __license__, __version__, __maintainer__, __email__

def _run(argv=None):
  from initialize import run
  run(argv)
