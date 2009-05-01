#!/usr/bin/env python
'''
  class for 4 circle data sessions
'''
# TODO: fit psd.Voigt
#################################################################################################
#                     Script to plot 4Circle-measurements with gnuplot                          #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -import spec .spec files, splitted by sequences                                               #
# -plot every sequence as extra picture or in one graph                                         # 
#    (h,k,l,phi,th,chi scan/mesh found by const. columns)                                       #
# -convert to counts/s                                                                          #
# -plot meshes in 3d                                                                            #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import circle_read_data
import circle_preferences

class circle_session(generic_session):
  '''
    Class to handle 4 circle data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\t4 CIRCLE-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  show_counts=False
  file_wildcards=(('4circle data','*.spec'), )  
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the generic_session constructor
    '''
    self.columns_mapping=circle_preferences.columns_mapping
    self.measurement_types=circle_preferences.measurement_types
    self.transformations=circle_preferences.transformations
    generic_session.__init__(self, arguments)
    # TODO: counts to cps
    
  
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    '''
      additional command line arguments for squid sessions
    '''
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        found=False
      elif argument=='-counts':
        show_counts=True
      else:
        found=False
    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      function to read data files
    '''
    return circle_read_data.read_data(file_name,self.columns_mapping,self.measurement_types)



  def add_file(self, filename, append=True):
    '''
      Add the data of a new file to the session.
      In addition to generic_session short info is set.
    '''
    datasets=generic_session.add_file(self, filename, append)
    # faster lookup
    for dataset in datasets:
      dataset.logx=self.logx
      dataset.logy=self.logy
      # name the dataset
      hkl=[str(round(dataset.data[0].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
      str(round(dataset.data[1].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0'),\
      str(round(dataset.data[2].values[len(dataset)/2],2)).rstrip('0').rstrip('.').replace('-0','0')] # h,k,l information from middle of the Scan with 2 post point digits but with trailing 0 striped      
      if (dataset.xdata==0)&(dataset.zdata==-1):
        dataset.short_info='h,'+hkl[1] +','+hkl[2] +' scan'
      elif (dataset.xdata==1)&(dataset.zdata==-1):
        dataset.short_info=hkl[0] +',k,'+hkl[2] +' scan'
      elif (dataset.xdata==2)&(dataset.zdata==-1):
        dataset.short_info=+hkl[0] +','+hkl[1] +',l scan'
      elif dataset.zdata>=0:
        dataset.short_info=dataset.xdim()+dataset.ydim()+' mesh at '+hkl[0]+ ','+hkl[1]+ ','+ hkl[2]
      else:
        dataset.short_info=dataset.xdim()+' scan at '+hkl[0] +','+ hkl[1]+ ','+hkl[2]
      if not self.show_counts:
        self.units=dataset.units()
        dataset.process_funcion(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
    return datasets

  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string='''
      <menu action='4CircleMenu'>
      
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "4CircleMenu", None,                             # name, stock id
                "4 Circle", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def counts_to_cps(self, input_data):
    '''
      Calculate counts/s for one datapoint.
      This function will be used in process_function() of
      a measurement_data_structure object.
    '''
    output_data=input_data
    counts_column=[]
    time_column=0
    for i,unit in enumerate(self.units): 
  # selection of the columns for counts
      if unit=='counts':
        counts_column.append(i)
      if unit=='s':
        time_column=i
    for counts in counts_column:
      output_data[counts]=output_data[counts]/output_data[time_column]# calculate cps
    return output_data
