# -*- encoding: utf-8 -*-
'''
  Datafile import template pattern to make it possible for the user to import any ascii column data.
'''

#++++++++++++++++++++++++++++++++++++ Begin of Template settings +++++++++++++++++++++++++++++++++++
# All settings are made with dictionaries, most options can just be commented out, if not appliccable

## General settings for the file
general={
	 'name': 'AFM',
         ## A list of leading characters which will not be used for data lines.
         ##    If the according option is set, it can be used to find the header, footer or splitting.
         'comments': [],

         ## Select a split character for the file or None for splitting without parameter
         'split string': None,

         ## Define the sample name
         'sample': '',

         ## Define the short info present in the plot title.
         'short info': '',
         }

## Defining the file header
header={
        ## Define a stric length in lines to be interpreted as header.
        'length': 0,
        }
self.test=5. #@UndefinedVariable
## Defining the data columns
columns={
         ## Set fixed defined columns.
         'columns': [('x', 'µm'), ('y', 'µm'), ('z', 'nm')],

         ## Define columns to use for x,y,z and error column.
         ##      The list is evaluate from start and the first column found is used.
         'plot columns': {
                          'x': ['x'],
                          'y': ['y'],
                          'z': ['z'],
                          'error': []
                          },

          ## Also use lines which start with a comment character.
          #'ignore comment': True,
         }

## Defining sequence splitting
splitting={
           ## Use comment lines to split different sequences
           #'use comment': True, 

           ## Use empty lines to split different sequences
           'use empty': True,

           ## Use specific string to seperate sequences
           #'use string': ('start','end'),

          ## Search pattern to get global values from split lines.
          ##     the sequence is (search patter, search after pattern, split string, index after split)
          #'search pattern': [
          #                   ('lambda_n', 'lambda:', True, ' ', 0), 
          #                   ('distance', ' nm', False, ' ', 0), 
          #                   ],

          ## Read new columns from the inter sequence lines, see columns 'from header'.
          #'read new columns': (-1, ',', None, None),
          }

## Defining the file footer, if nothing is specified there will be no footer
footer={
        ## Use comment for footer
        #'use comment': True

        ## Define a stric length in lines to be interpreted as footer.
        'length': 0,

        }

## Define how the applicability of thes template can be checked
type_info={
           'wildcards': ['*.txt'],
            # Not jet implemented
            }

#------------------------------------ Begin of Template settings -----------------------------------