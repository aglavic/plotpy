#!/usr/bin/env python
#################################################################################################
#                     Script to plot reflectometer uxd-files with gnuplot                       #
#                                       last changes:                                           #
#                                        01.04.2009                                             #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
# Features at the moment:                                                                       #
# -convert uxd files to .out space(and other)seperated text files, splitted by sequences        #
# -plot every sequence as extra picture or in one graph                                         # 
#    (phi,th,chi scan found automatically)                                                      #
# -list seqences present in file                                                                #
# -process more than one file (wild cards possible)                                             #
# -select sequences to be plotted                                                               #
# -convert to counts/s                                                                          #
# -create .ent file for fit.f90 script from Emmanuel Kentzinger and refine some parameters      #
# -send all files to printer after processing (linux commandline printing)                      #
#                                                                                               #
# To do:                                                                                        #
# -subtract background measured in another file                                                 #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.

# import generic_session, which is the parent class for the squid_session
from plot_generic_data import generic_session
# importing preferences and data readout
import reflectometer_read_data
import reflectometer_preferences

'''
  Class to handle reflectometer data sessions
'''
class reflectometer_session(generic_session):
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  specific_help=\
'''
\tReflectometer-Data treatment:
\t-counts\t\tShow actual counts, not counts/s
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  show_counts=False
  #------------------ local variables -----------------

  
  '''
    class constructor expands the generic_session constructor
  '''
  def __init__(self, arguments):
    self.data_columns=reflectometer_preferences.data_columns
    self.transformations=reflectometer_preferences.transformations
    generic_session.__init__(self, arguments)
    
  
  '''
    additional command line arguments for reflectometer sessions
  '''
  def read_argument_add(self, argument, last_argument_option=[False, '']):
    found=True
    if (argument[0]=='-') or last_argument_option[0]:
      # Cases of arguments:
      if last_argument_option[0]:
        found=False
      elif argument=='-counts':
        self.show_counts=True
      else:
        found=False
    return (found, last_argument_option)


  '''
    function to read data files
  '''
  def read_file(self, file_name):
    return reflectometer_read_data.read_data(file_name,self.data_columns)
  
  '''
    create a specifig menu for the Reflectometer session
  '''
  def create_menu(self):
    # Create XML for squid menu
    string='''
      <menu action='ReflectometerMenu'>
      
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "ReflectometerMenu", None,                             # name, stock id
                "Reflectometer", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
             )
    return string,  actions
  
  '''
    Add the data of a new file to the session.
    In addition to generic_session counts per secong
    corrections are performed here, too.  
  '''
  def add_file(self, filename, append=True):
    datasets=generic_session.add_file(self, filename, append)
    for dataset in datasets:
      self.time_col=1
      th=0
      twoth=0
      phi=0       
      for line in dataset.info.splitlines():
        strip=line.split('=')
        if strip[0]=='STEPTIME':
          self.time_col=float(strip[1])
        if strip[0]=='THETA':
          th=float(strip[1])
        if strip[0]=='2THETA':
          twoth=float(strip[1])
        if strip[0]=='PHI':
          phi=float(strip[1])
      if not self.show_counts:
        self.units=dataset.units()
        dataset.process_funcion(self.counts_to_cps)
        dataset.unit_trans([['counts',1,0,'counts/s']])
      dataset.short_info=' started at Th='+str(round(th,4))+' 2Th='+str(round(twoth,4))+' Phi='+str(round(phi,4))



  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  '''
    Calculate counts/s for one datapoint.
    This function will be used in process_function() of
    a measurement_data_structure object.
  '''
  def counts_to_cps(self, input_data):
    output_data=input_data
    counts_column=[]
    for i,unit in enumerate(self.units): 
  # selection of the columns for counts
      if unit=='counts':
        counts_column.append(i)
    for counts in counts_column:
      output_data[counts]=output_data[counts]/self.time_col # calculate the linear correction
    return output_data
  
  #++++ functions for fitting with fortran program by E. Kentzinger ++++

  def create_ent_file(array,points,ent_file_name,\
    back_ground=0,resolution=3.5,scaling_factor=10,theta_max=2.3,fit=0,fit_params=[1,2],constrains=[]\
    ): # creates an entrance file for fit.f90 script
    from scattering_length_table import scattering_length_densities
    ent_file=open(ent_file_name,'w')
    ent_file.write('8048.0\tscattering radiaion energy (Cu-Ka)\n'+\
      str(points)+'\tnumber of datapoints\n'+\
      '\n'+str(len(array))+'\tnumber of interfaces (number of layers + 1)\n'+\
      '#### Begin of layers, first layer:')
    i=1
    for j,layer in enumerate(array):
      try:
        SL=scattering_length_densities[layer[0]]
      except KeyError:
        print layer[0]+' not found in database. Please edit scattering_length_table.py'
        SL=[10,1]
        ent_file.write(' Not in Table')
      ent_file.write(' '+str(j)+': '+layer[0]+'\n')
      if not layer[1]==None:
        ent_file.write(str(layer[1])+'\tlayer thickness (in A)\t\t\tparameter '+str(i)+'\n')
        i=i+1
      ent_file.write(str(SL[0])+'\tdelta *1e6\t\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write(str(SL[1])+'\tdelta/beta\t\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write(str(layer[2])+'\tlayer roughness (in A)\t\t\tparameter '+str(i)+'\n')
      i=i+1
      ent_file.write('#')
    ent_file.write('### End of layers.\n'+\
      str(round(back_ground,4))+'\tbackground\t\t\t\tparametar '+str(i)+'\n')
    i=i+1
    ent_file.write(str(resolution)+'\tresolution in q (sigma, in 1e-3 A^-1)\tparameter '+str(i)+'\n')
    i=i+1
    ent_file.write(str(round(scaling_factor,4))+'\tscaling factor *1e-6\t\t\tparameter '+str(i)+'\n')
    ent_file.write('\n'+str(theta_max)+'\ttheta_max (in deg) for recalibration\n\n'+\
      str(fit)+'\t1: fit; 0: simulation\n\n')
    ent_file.write(str(len(fit_params))+'\t\tNumber of parameters to be fitted\n'+str(fit_params).strip('[').strip(']').replace(',',' ')+'\t\tindices of parameters\n'+str(len(constrains))+'\t\tnumber of constrains\n')
    for constrain in constrains:
      ent_file.write(str(len(constrain))+'\t\tnumber of parameters to be kept equal\n'+\
      str(constrain).strip('[').strip(']').replace(',',' ')+'\t\tindices of those parameters\n')
    ent_file.close()

  def find_total_reflection(dataset): # find angle of total reflection from decay to 1/3 of maximum
    position=0
    max_value=0
    for point in dataset:
      position=point[0]
      if point[0]>0.05:
        if max_value<point[1]:
          max_value=point[1]
        elif max_value>(point[1]*3):
          dataset.index=0
          return position
    return position

  def read_fit_file(file_name,parameters): # load results of fit file
    result={}
    fit_file=open(file_name,'r')
    test_fit=fit_file.readlines()
    fit_file.close()
    for i,line in enumerate(reversed(test_fit)):
      split=line.split()
      if len(split)>0:
        if split[0] in parameters:
          result[split[0]]=float(split[1])
      if len(parameters)==len(result):
          return result
    return None

  def refine_scaling(layers,SF,BG,constrain_array): # refine the scaling factor within the region of total reflection
    data_lines=dataset.export('/var/tmp/fit_temp.res',False,' ',xfrom=0.005,xto=find_total_reflection(dataset))
    create_ent_file(layers,data_lines,'/var/tmp/fit_temp.ent',back_ground=BG,scaling_factor=SF,\
      constrains=constrain_array,fit=1,fit_params=[len(layers)*4+2])
    retcode = subprocess.call(['fit-script', '/var/tmp/fit_temp.res', '/var/tmp/fit_temp.ent', '/var/tmp/fit_temp','20'])
    scaling_factor=read_fit_file('/var/tmp/fit_temp.ref',[str(len(layers)*4+2)])[str(len(layers)*4+2)]
    return scaling_factor

  def refine_roughnesses(layers,SF,BG,constrain_array): # refine the roughnesses and background after the angle of total reflection
    fit_p=[i*4+4 for i in range(len(layers))]
    fit_p.append(len(layers)*4-1)
    fit_p.sort()
    data_lines=dataset.export('/var/tmp/fit_temp.res',False,' ',xfrom=find_total_reflection(dataset))
    create_ent_file(layers,data_lines,'/var/tmp/fit_temp.ent',back_ground=BG,scaling_factor=SF,\
      constrains=constrain_array,fit=1,fit_params=fit_p)
    retcode = subprocess.call(['fit-script', '/var/tmp/fit_temp.res', '/var/tmp/fit_temp.ent', '/var/tmp/fit_temp','50'])
    fit_p=map(str,fit_p)
    parameters=read_fit_file('/var/tmp/fit_temp.ref',fit_p)
    for i,layer in enumerate(layers):
      if i<len(layers)-1:
        layer[2]=abs(parameters[str(i*4+4)])
      else:
        layer[2]=abs(parameters[str(i*4+3)])
    BG=parameters[str(len(layers)*4)]
    return [layers,BG]

  def export_fit(dataset): # Function to export data for fitting with fit.f90 program
    fit_thick=fit_thicknesses
    if globals.debug:
      globals.debug_file.write('call: export_for_fit()\n')
    # create array of layers
    first_split=fit_layers.split('-')
    layer_array=[]
    constrain_array=[]
    layer_index=1
    for compound in first_split:
      if compound[-1]==']': # is there a multilayer
        count=int(compound.split('[')[0])
        second_split=compound.split('[')[1].rstrip(']').split('_')
        second_thick=fit_thick.split('-')[0].lstrip('[').rstrip(']').split('_')
        for j in range(len(second_split)):
          constrain_array.append([])
          for i in range(count): # repeat every layer in multilayer
              for j,multi_compound in enumerate(second_split):
                  constrain_array[-1-j].append((layer_index-1)*4+1) # every layer of same kind will have the same height
                  layer_array.append([multi_compound,float(second_thick[j]),fit_est_roughness])
                  layer_index=layer_index+1
      else: # no multilayer
          if len(fit_thick)>0:
              layer_array.append([compound,float(fit_thick.split('-')[0]),fit_est_roughness])
          else:
              layer_array.append([compound,None,fit_est_roughness])
          layer_index=layer_index+1
      if len(fit_thick.split('-'))>1: # remove first thickness
          fit_thick=fit_thick.split('-',1)[1]
      else:
          fit_thick=''
    dataset.unit_trans([['Theta','\\302\\260',4*math.pi/1.54/180*math.pi,0,'q','A^{-1}'],['2 Theta','\\302\\260',2*math.pi/1.54/180*math.pi,0,'q','A^{-1}']])
    data_lines=dataset.export(input_file_name+'_'+dataset.number+'.res',False,' ') # write data into files with sequence numbers in format ok for fit.f90    
    scaling_fac=(dataset.max(xstart=0.005)[1]/1e5)
    back_gr=dataset.min()[1]
    if try_refine: # Try to refine the scaling factorn, background and roughnesses
      scaling_fac=refine_scaling(layer_array,scaling_fac,back_gr,constrain_array)
      result=refine_roughnesses(layer_array,scaling_fac,back_gr,constrain_array)
      layer_array=result[0]
      back_gr=result[1]
    # create final input file and make a simulation
    create_ent_file(layer_array,data_lines,input_file_name+'_'+dataset.number+'.ent',back_ground=back_gr,\
      scaling_factor=scaling_fac,constrains=constrain_array)
    retcode = subprocess.call(['fit-script', input_file_name+'_'+dataset.number+'.res',\
      input_file_name+'_'+dataset.number+'.ent', input_file_name+'_'+dataset.number])

  #---- functions for fitting with fortran program by E. Kentzinger ----
