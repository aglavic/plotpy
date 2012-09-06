# -*- encoding: utf-8 -*-

#++++++++++++++++++++++++++++++++++++ Begin of Template settings +++++++++++++++++++++++++++++++++++
# All settings are made with dictionaries, most options can just be commented out, if not appliccable

## General settings for the file
general={
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
        'length': 1,

        ## There are three ways to determine the header length, 
        ## if more than one is set, the procedure which gives 
        ## the highest header length will be used

        ## Use comment characters to define the header lines.
        #'use comment': True, 

        ## Search for the first line, starting with a number.
        'use number search': False,

        ## Use a specific keyword and a relative line step.
        #'search keyword': ('[data]', 0),

        ## Search pattern to get global values from header.
        ##     the sequence is (name, search patter, search after pattern, split string, index after split)
        ##     The result of found search patterns can be used in other strings (e.g. column names)
        ##     to be replaced using the syntax '<pattern name>' or '<Text only when found|pattern name|text only when found>'.
        'search pattern': [
                           ],
        }
self.test=5. #@UndefinedVariable
## Defining the data columns
columns={
         ## Set fixed defined columns.
         'columns': [('z', 'nm'), ('P', '%'), ],

         ## Read columns from specified header line.
         ##   the sequence is (header line to use, split character (or None for global), first column, last column
         #'from header': (2, None, None, None),

         ## If read from header, map specified columns to dimension, unit.
         #'columns map': {
         #                'x': ('x', 'a.u.'), 
         #                'y': ('y', 'a.u.'), 
         #                'z': ('z', 'a.u.'), 
         #                },

         ## If dimension and unit is given in the header file, use this settings to split them.
         ##    the sequence is (strip at start, characters between dimension and unit, remove at end)
         #'header column splitting': ("'", '[', "]'"), 

         ## Define a list of columns to skip when importing.
         #'ignore': [2],

         ## Define columns to be calculated from other columns with a specific function.
         ##    the sequence is (function, dimension, unit)
         ##    The functions are given using python syntax. Allowed operands are:
         ##        *,/,+,-,**,//,%
         ##    Allowd functions/constants are:
         ##        pi, exp(), sin(), cos(), tan(), arcsin(), arccos(), arctan()
         ##    Other columns are defined in []-Brackets with their dimensions name.
         ##        (This will be translated in a numpy array, so array methods can be used)
         ##    To use any additional numpy functions you can use np.* .
         'column from function': [
                                  ],

         ## Define columns to use for x,y,z and error column.
         ##      The list is evaluate from start and the first column found is used.
         'plot columns': {
                          'x': ['z'],
                          'y': ['P'],
                          #'z': [], 
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
        #'length': 5, 

        ## Search for the last line, starting with a number.
        'use number search': True,

        ## Use a specific keyword and a relative line step.
        #'search keyword': ('mc1_rot', -1),

        ## Search pattern to get global values from footer lines.
        ##     the sequence is (search patter, search after pattern, split string, index after split)
        'search pattern': [
                           ('chi', 'chi', True, None, 0),
                           ],
        }

## Define how the applicability of thes template can be checked
type_check={
            # Not jet implemented
            }

#------------------------------------ Begin of Template settings -----------------------------------