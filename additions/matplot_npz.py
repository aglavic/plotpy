#!/usr/bin/env python
#-*- coding: utf8 -*-
'''
  Example script how to used numpy .npz exported data from plot.py
'''

import sys
from pylab import *
from numpy import load

nextlog=False
for i, name in enumerate(sys.argv[1:]):
  if name=='-log':
    nextlog=True
    continue
  figure(i+1)
  data=load(name)
  dims=data['dimensions'].tolist()
  units=data['units'].tolist()
  x=unicode(data['x'].tolist())
  y=unicode(data['y'].tolist())
  xunit=units[dims.index(x)]
  yunit=units[dims.index(y)]
  xlabel(u"%s [%s]"%(x, xunit))
  ylabel(u"%s [%s]"%(y, yunit))
  if nextlog:
    nextlog=False
    semilogy(data[x], data[y])
  else:
    plot(data[x], data[y])

show()
