# -*- encoding: utf-8 -*-
'''
  Datafile import template pattern to make it possible for the user to import any ascii column data.
'''


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
        
        ## Search for the first line, starting with a number.
        'use number search': True,
        
        }

## Defining the data columns
columns={
         ## Set fixed defined columns.
         'columns': [('Θ','°'),('I','counts'),],
                           
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
                                  ('sqrt([I])', 'dI', '[I]'), 
                                  ('4.*pi/1.54*sin([Θ]/180*pi)', 'q', 'A^{-1}'), 
                                  ], 
         
         ## Define columns to use for x,y,z and error column.
         ##      The list is evaluate from start and the first column found is used.
         'plot columns': {
                          'x': ['q'], 
                          'y': ['I'], 
                          'error': ['dI']
                          }, 
          
         }

## Defining sequence splitting
splitting={
           ## Use empty lines to split different sequences
           'use empty': True, 
           
          }

## Defining the file footer, if nothing is specified there will be no footer
footer={
        }

## Define how the applicability of thes template can be checked
type_info={
           'wildcards': ['*.txt'],
            }

#------------------------------------ Begin of Template settings -----------------------------------
