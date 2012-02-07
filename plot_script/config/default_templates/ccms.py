# -*- encoding: utf-8 -*-
'''
  Datafile import template for the CCMS system.
'''
## General settings for the file
general={
	 'name': 'CCMS',
         ## A list of leading characters which will not be used for data lines.
         'comments': ['#'],
         'split string': None, 
         'sample': '', 
         'short info': '', 
         }
## Defining the file header
header={
        'length': 1, 
        }
## Defining the data columns
columns={
         'from header': (0, None, None, None),
         'header column splitting': ("", '_(', ")'"), 
         ## Define columns to use for x,y,z and error column.
         'plot columns': {
                          'x': [],#'T_sample'], 
                          'y': ['moment'], 
                          #'z': [], 
                          'error': []
                          }, 
         }
## Defining sequence splitting
splitting={
           'use empty': True, 
          }
## Defining the file footer, if nothing is specified there will be no footer
footer={
        }
## Define how the applicability of thes template can be checked
type_info={
           'wildcards': ['*.dat'],
            # Not jet implemented
            }

#------------------------------------ End of Template settings -----------------------------------
