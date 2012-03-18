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

import numpy
# import GenericSession, which is the parent class for the squid_session
from generic import GenericSession
from plot_script.fit_data import FitFunction3D
from plot_script.measurement_data_structure import PhysicalProperty, MeasurementData
# importing data readout
from plot_script.read_data import shg as read_data
# import gui functions for active config.gui.toolkit
from plot_script.config import gui as gui_config
try:
  GUI=__import__(gui_config.toolkit+'gui.shg', fromlist=['SHGGUI']).SHGGUI
except ImportError:
  class GUI: pass

__author__="Artur Glavic"
__credits__=["Ulrich Ruecker"]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

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
  FILE_WILDCARDS=[('SHG Parameters (.par)', '*.par'), ]
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
    return read_data.read_data(file_name)


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
  parameters=[0., 0.01]
  parameter_names=['δφ', 'I_0']
  parameter_description={
                         'I_0': 'General scaling factor.',
                         'δφ': 'Tilt of Sample-axis',
                         }
  fit_function_text='SHG Simulation'
  max_iter=50. # maximum numer of iterations for fitting (should be lowered for slow functions)
  is_3d=False
  show_components=False
  # domain switch operations, key is the index of the Chi and the value is a factor
  domains=[({})]

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
    sin=numpy.sin
    cos=numpy.cos
    dphi=p[0]*numpy.pi/180
    domains=len(self.domains)
    Chis=self.get_chis(p[1+domains:])
    pol_terms={
               0: cos(pol+dphi),
               1: sin(pol+dphi),
               }
    I=numpy.zeros_like(pol)
    components=map(lambda comp: numpy.zeros_like(pol), Chis)
    for i, domain in enumerate(self.domains):
      I0=p[i+1]
      for key, value in domain.items():
        Chis[key][0]*=value
      Ex=numpy.zeros_like(pol)
      Ey=numpy.zeros_like(pol)
      domain_components=[]
      for Chi in Chis:
        Ex_comp=(Chi[0]*Chi[1]*pol_terms[Chi[2]]*pol_terms[Chi[3]])
        Ey_comp=(Chi[0]*(1-Chi[1])*pol_terms[Chi[2]]*pol_terms[Chi[3]])
        if Chi[2]!=Chi[3]:
          # tensors with the last terms different are exchangebal
          # it's equivalent to use one term twice
          Ex_comp*=2.
          Ey_comp*=2.
        domain_components.append((Ex_comp, Ey_comp))
        Ex+=Ex_comp
        Ey+=Ey_comp
      I_domain=I0*(cos(ana+dphi)*Ey+sin(ana+dphi)*Ex)**2
      domain_components=map(lambda Exy: I0*(sin(ana+dphi)*Exy[0]+cos(ana+dphi)*Exy[1])**2,
                                 domain_components)
      I+=I_domain
      for comp, domain_comp in zip(components, domain_components):
        comp+=domain_comp
    self.last_fit_components=components
    self.last_fit_sum=I
    return I

  def add_chi(self, Chi):
    '''
      Add a specific Chi_ijk factor.
    '''
    name='%s%s%s'%tuple(map(lambda i: "x"*i+"y"*(1-i), Chi))
    name_eq=name[0]+name[2]+name[1]
    if not (name in self.parameter_names or name_eq in self.parameter_names):
      self.parameter_names.append(name)
      self.parameters.append(0.)
      return True
    return False

  def remove_chi(self, Chi):
    name='%s%s%s'%tuple(map(lambda i: "x"*i+"y"*(1-i), Chi))
    if Chi in self.parameter_names:
      idx=self.parameter_names.index(name)
      self.parameters.remove(idx)
      self.parameter_names.remove(idx)
      return True
    return False

  def get_chis(self, scale):
    '''
      Return a list of chi_ijk as (chi_ijk, i, j, k).
    '''
    domains=len(self.domains)
    Chinames=self.parameter_names[1+domains:]
    Chis=map(lambda item: [
                           item[0],
                           int(item[1][0]=='x'),
                          int(item[1][1]=='x'),
                          int(item[1][2]=='x')],
            zip(scale, Chinames))
    return Chis

  def add_domain(self, operations):
    '''
      Add a domain to the model.
    '''
    self.domains.append(operations)
    domains=len(self.domains)
    self.parameter_names.insert(domains, 'I_%i'%(domains-1))
    self.parameters.insert(domains, 0.)

  def delete_domain(self, index):
    '''
      Remove a domain.
    '''
    domains=len(self.domains)
    if index>=0 and index<domains:
      self.domains.pop(index)
      self.parameter_names.pop(index+1)
      self.parameters.pop(index+1)

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
      anai=numpy.array(dataset.data[ana_index]%'rad')
      poli=numpy.array(dataset.data[pol_index]%'rad')
      shgi=numpy.array(dataset.y)
      pol=numpy.append(pol, poli)
      ana=numpy.append(ana, anai)
      shg=numpy.append(shg, shgi)
    return ana, pol, shg

  def simulate(self, x, *ign, **ignore):
    '''
      Simulate for all datasets.
    '''
    ana, pol, ignore=self.get_anapol()
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
      Ids.data.append(PhysicalProperty('SHG', '', Ii))
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
            cds.data.append(PhysicalProperty(name, '', ci))
            cds.short_info=name+"-component"
            d.plot_together.append(cds)
      i=j

  def refine(self, i1, i2, dataset_yerror=None, progress_bar_update=None):
    '''
      Create arrays whith the combined data and start a refienement.
    '''
    ana, pol, shg=self.get_anapol()
    return FitFunction3D.refine(self, pol, ana, shg, progress_bar_update=progress_bar_update)
