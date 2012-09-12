#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
  Plot-script package for data plotting and analyzing for different instruments.
  
  The data model is based on the following hierarchy:
  
    =================  ===  ====================================================
    GUI-Interface      <->         session-Object
                                        session.file_data
    gnuplot-Interface  <->  MeasurementData-Object (mds)
                            MeasurementData.data
                            PhysicalProperty-Objects (mds)
    =================  ===  ====================================================
  
    As top level the session-object (which is different for each instrument) handles the
    data readout and storage. The active session object stores the data read from each file in
    a dictionary. The dictionary key is the input file name and the value as a list of 
    MeasurementData object. The MeasurementData object stands for one Measurement/Scan and stores
    plot specific information and the measured data as PhysicalProperty-Objects (derived from numpy.ndarray).
'''

from info import __author__, __copyright__, __license__, __version__, __maintainer__, __email__

def _run(argv=None):
  from initialize import run
  run(argv)