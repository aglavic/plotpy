# -*- encoding: utf-8 -*-
'''
  class for SHG data sessions
'''
#################################################################################################
#                        Script to plot IN12-measurements with gnuplot                          #
#                                                                                               #
#                                   Written by Artur Glavic                                     #
#                         please report bugs to a.glavic@fz-juelich.de                          #
#                                                                                               #
#                                                                                               #
#################################################################################################

# Pleas do not make any changes here unless you know what you are doing.
import sys
import numpy
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
from fit_data import FitFunction3D
from measurement_data_structure import PhysicalProperty, MeasurementData
# importing data readout
import read_data.shg
# import gui functions for active config.gui.toolkit
import config.gui
try:
  GUI=__import__( config.gui.toolkit+'gui.shg', fromlist=['SHGGUI']).SHGGUI
except ImportError: 
  class GUI: pass

__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = ["Ulrich Ruecker"]
__license__ = "GPL v3"
__version__ = "0.7.7"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Development"

class SHGSession(GUI, GenericSession):
  '''
    Class to handle SHG data sessions
  '''
  #++++++++++++++ help text string +++++++++++++++++++++++++++
  SPECIFIC_HELP=\
'''
\tSHG-Data treatment:
'''
  #------------------ help text strings ---------------

  #++++++++++++++++++ local variables +++++++++++++++++
  FILE_WILDCARDS=[('SHG Parameters (.par)', '*.par'),]
  mds_create=False
  shg_simulation=None

#  TRANSFORMATIONS=[\
#  ['','',1,0,'',''],\
#  ]  
#  COMMANDLINE_OPTIONS=GenericSession.COMMANDLINE_OPTIONS+[]  
  #------------------ local variables -----------------

  
  def __init__(self, arguments):
    '''
      class constructor expands the GenericSession constructor
    '''
    GenericSession.__init__(self, arguments)
  
#  def read_argument_add(self, argument, last_argument_option=[False, ''], input_file_names=[]):
#    '''
#      additional command line arguments for squid sessions
#    '''
#    found=True
#    if (argument[0]=='-') or last_argument_option[0]:
#      # Cases of arguments:
#      if last_argument_option[0]:
#        found=False
#      elif argument=='-no-img':
#        self.import_images=False
#        found=True
#      else:
#        found=False
#    return (found, last_argument_option)


  def read_file(self, file_name):
    '''
      Function to read data files.
    '''
    return read_data.shg.read_data(file_name )


  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++
  
  def create_shg_sim(self):
    '''
      Create a simulation object.
    '''
    if self.shg_simulation is None:
      self.shg_simulation=ChiMultifit([])
    return self.shg_simulation



class ChiMultifit(FitFunction3D):
  '''
    Class to fit the SHG Chi terms for several datasets at once.
  '''
  
  name="SHG Signal"
  parameters=[0.001, 0.]
  parameter_names=['I_0', 'δφ']
  parameter_description={
                         'I_0': 'General scaling factor.', 
                         'δφ': 'Tilt of Sample-axis', 
                         }
  fit_function_text='SHG Simulation'
  max_iter=50. # maximum numer of iterations for fitting (should be lowered for slow functions)
  is_3d=False
  show_components=False
  
  def __init__(self, datasets, Chis=[]):
    '''
      Create the Object with a list of datasets.
    '''
    self.datasets=datasets
    self.parameter_names=list(self.parameter_names)
    for Chi in Chis:
      self.add_chi(Chi)
    self.last_fit_components=[]
    FitFunction3D.__init__(self, [])
  
  def fit_function(self, p, pol, ana):
    '''
      Simulate the SHG Intensity dependent on the polarizer/analzer tilt.
    '''
    cos=numpy.cos
    pih=numpy.pi*0.5
    I0=p[0]
    dphi=p[1]*numpy.pi/180
    Chis=self.get_chis(p[2:])
    I=numpy.zeros_like(pol)
    components=[]
    self.last_fit_components=components
    for Chi in Chis:
      component=I0*(Chi[0]*cos(ana-Chi[1]*pih+dphi) *\
                        cos(pol-Chi[2]*pih+dphi) *\
                        cos(pol-Chi[3]*pih+dphi))**2
      components.append(component)
      I+=component
    self.last_fit_sum=I
    return I
  
  def add_chi(self, Chi):
    '''
      Add a specific Chi_ijk factor.
    '''
    name='χ_%s%s%s' % tuple(map(lambda i: "x"*i+"y"*(1-i), Chi))
    if not name in self.parameter_names:
      self.parameter_names.append(name)
      self.parameters.append(0.)
      return True
    return False
  
  def remove_chi(self, Chi):
    name='χ_%s%s%s' % tuple(map(lambda i: "x"*i+"y"*(1-i), Chi))
    if chi in self.parameter_names:
      idx=self.parameter_names.index(name)
      self.parameters.remove(idx)
      self.parameter_names.remove(idx)
      return True
    return False
  
  def get_chis(self, scale):
    '''
      Return a list of chi_ijk as (chi_ijk, i, j, k).
    '''
    Chinames=self.parameter_names[2:]
    Chis=map(lambda item: [
                           item[0], 
                           int(item[1][3]=='x'), 
                          int(item[1][4]=='x'), 
                          int(item[1][5]=='x')], 
            zip(scale, Chinames))
    return Chis
  
  def get_anapol(self):
    '''
      Return analser,polariser and x of all datasets as one array.
    '''
    datasets=self.datasets
    pol=numpy.array([])
    ana=numpy.array([])
    shg=numpy.array([])
    for dataset in datasets:
      cols=dataset.dimensions()
      pol_index=cols.index('Polariser')
      ana_index=cols.index('Analyser')
      anai=numpy.array(dataset.data[ana_index] % 'rad')
      poli=numpy.array(dataset.data[pol_index] % 'rad')
      shgi=numpy.array(dataset.y)
      pol=numpy.append(pol, poli)
      ana=numpy.append(ana, anai)
      shg=numpy.append(shg, shgi)
    return ana, pol, shg
  
  def simulate(self, x, *ign, **ignore):
    '''
      Simulate for all datasets.
    '''
    ana, pol, ign=self.get_anapol()
    try:
      y=self.fit_function(self.parameters, pol, ana)
    except TypeError, error:
      raise ValueError, "Could not execute function with numpy array: "+str(error)
    return x, y[:len(x)]
  
  def set_simulations(self):
    '''
      Insert the simulation and components to the datasets.
    '''
    datasets=self.datasets
    I=self.last_fit_sum
    meanI=I.mean()
    comp=self.last_fit_components
    i=0
    for d in datasets:
      j=i+len(d)
      Ii=I[i:j]
      Ids=MeasurementData()
      Ids.data.append(d.x)
      Ids.data.append( PhysicalProperty('SHG', '', Ii) )
      Ids.short_info=self.fit_function_text_eval
      d.plot_together=[d, Ids]
      if self.show_components:
        for k, component in enumerate(comp):
          ci=component[i:j]
          if ci.mean()>(meanI*0.1):
            cds=MeasurementData()
            cds.data.append(d.x)
            name=self.parameter_names[k+2]
            name=name.replace('_', '_{')+'}'
            cds.data.append( PhysicalProperty(name, '', ci) )
            cds.short_info=name+"-component"
            d.plot_together.append(cds)
      i=j
  
  def refine(self,  i1, i2, dataset_yerror=None, progress_bar_update=None):
    '''
      Create arrays whith the combined data and start a refienement.
    '''
    ana, pol, shg=self.get_anapol()
    return FitFunction3D.refine(self, pol, ana, shg, progress_bar_update=progress_bar_update )
  
