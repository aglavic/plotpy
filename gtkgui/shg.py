# -*- encoding: utf-8 -*-
'''
  SHG GTK GUI class.
''' 

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

import gtk
from fit_data import FitSession

#----------------------- importing modules --------------------------


__author__ = "Artur Glavic"
__copyright__ = "Copyright 2008-2011"
__credits__ = []
__license__ = "GPL v3"
__version__ = "0.7.8.1"
__maintainer__ = "Artur Glavic"
__email__ = "a.glavic@fz-juelich.de"
__status__ = "Production"


 
class SHGGUI:
  def create_menu(self):
    '''
      create a specifig menu for the 4circle session
    '''
    # Create XML for squid menu
    string='''
      <menu action='SHG'>
        <menuitem action='SHGSim'/>
        <menuitem action='AddToSHGSim'/>
        <menuitem action='ToggleSHGComponents'/>
        <separator name='SHGSep'/>        
        <menuitem action='NewSHGSimEmpty'/>
        <menuitem action='NewSHGSimCopy'/>
        <menuitem action='NewSHGSimFull'/>
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ( "SHG", None,                             # name, stock id
                "SHG", None,                    # label, accelerator
                None,                                   # tooltip
                None ),
            ( "SHGSim", None,                             # name, stock id
                "SHG Simulation", '<control><shift>H',                    # label, accelerator
                None,                                   # tooltip
                self.shg_simulation_dialog ),
            ( "AddToSHGSim", None,                             # name, stock id
                "Add/Remove from simulation", '<control>H',                    # label, accelerator
                None,                                   # tooltip
                self.add_to_sim ),
            ( "ToggleSHGComponents", None,                             # name, stock id
                "Toggle show components", None,                    # label, accelerator
                None,                                   # tooltip
                self.toggle_show_components ),
            ( "NewSHGSimEmpty", None,                             # name, stock id
                "New Simulation (Empty)", None,                    # label, accelerator
                None,                                   # tooltip
                self.simulation_new_empty ),
            ( "NewSHGSimCopy", None,                             # name, stock id
                "New Simulation (Copy)", None,                    # label, accelerator
                None,                                   # tooltip
                self.simulation_new_copy ),
            ( "NewSHGSimFull", None,                             # name, stock id
                "New Simulation (All)", None,                    # label, accelerator
                None,                                   # tooltip
                self.simulation_new_all ),
             )
    return string,  actions

  def shg_simulation_dialog(self, action, window):
    '''
      Create a simulation object, if it does not exist and open a dialog with
      simulation specific settings.
    '''
    sim=self.create_shg_sim()
    domains=len(sim.domains)
    dialog=gtk.Dialog(title='SHG Simulation', buttons=('Add Chi', 1,'Remove Chi', 2, 'Add Domain', 3, 'Cancel', 0))
    label=gtk.Label("SHG Simulation with following parameter:")
    dialog.vbox.add(label)
    table=gtk.Table(4, len(sim.parameter_names)-domains, False)
    dialog.vbox.add(table)
    checkboxes=[]
    for i, chi in enumerate(zip(sim.parameter_names[1+domains:], sim.parameters[1+domains:])):
      checkbox=gtk.CheckButton(label=chi[0]+'=%.2f' % chi[1], use_underline=False)
      table.attach(checkbox, 0, 4, i, i+1)
      checkboxes.append(checkbox)
    choices=[gtk.combo_box_new_text() for i in range(3)]
    map(lambda item: item.append_text('y'), choices)
    map(lambda item: item.append_text('x'), choices)
    map(lambda item: item.set_active(0), choices)
    for j in range(3):
      table.attach(choices[j], j+1, j+2, len(sim.parameters)-domains+1, len(sim.parameters)-domains+2, 0, 0)
    table.attach(gtk.Label('χ'), 0, 1, len(sim.parameters)-domains+1, len(sim.parameters)-domains+2, 0, 0)
    for i, domain in enumerate(sim.domains):
      dstring= 'Domain %i: I=%.4f' % (i+1, sim.parameters[i+1])
      for key, value in domain.items():
        dstring+='\n     %s->%f·%s' % (sim.parameter_names[1+domains+key], value, sim.parameter_names[1+domains+key])
      domain_label=gtk.Label(dstring)
      dialog.vbox.pack_end(domain_label, False)
    dialog.show_all()
    result=dialog.run() 
    if result==2:
      for i, checkbox in enumerate(reversed(checkboxes)):
        if checkbox.get_active():
          sim.parameters.pop(len(checkboxes)-i+1)
          sim.parameter_names.pop(len(checkboxes)-i+1)
    elif result==1:
      chi=map(lambda item: item.get_active(), choices)
      sim.add_chi(chi)
    elif result==3:
      dialog.destroy()
      self.domain_dialog(action, window)
      return
    dialog.destroy()
    if result>0:
      self.shg_simulation_dialog(action, window)
  
  def domain_dialog(self, action, window):
    '''
      Add a domain with specific transformation options to the simulation.
    '''
    sim=self.create_shg_sim()
    domains=len(sim.domains)
    dialog=gtk.Dialog(title='SHG Simulation - Add Domain', buttons=('Add', 1, 'Cancel', 0))
    table=gtk.Table(2, len(sim.parameter_names)-domains, False)
    dialog.vbox.add(table)
    parameters=[]
    for i, chi in enumerate(zip(sim.parameter_names[1+domains:], sim.parameters[1+domains:])):
      label=gtk.Label(chi[0]+'=%.2f' % chi[1])
      table.attach(label, 0, 1, i, i+1)
      entry=gtk.Entry()
      entry.set_text('1')
      table.attach(entry, 1, 2, i, i+1)
      parameters.append(entry)
    dialog.show_all()
    result=dialog.run()
    if result==1:
      try:
        parameters=map(lambda param: float(param.get_text()), parameters)
      except ValueError:
        pass
      else:
        domain_parameters={}
        for i, param in enumerate(parameters):
          if param!=1:
            domain_parameters[i]=param
        sim.add_domain(domain_parameters)
    dialog.destroy()
    self.shg_simulation_dialog(action, window)
  
  def add_to_sim(self, action, window):
    sim=self.create_shg_sim()
    active=self.active_file_data[window.index_mess]
    if active.fit_object is None or active.fit_object.__class__ is FitSession:
      active.fit_object=FitSessionSHG(active)
    if active in sim.datasets:
      sim.datasets.remove(active)
      for func_line in active.fit_object.functions:
        if func_line[0] is sim:
          active.fit_object.functions.remove(func_line)
      print "Removed from Simulation"
    else:
      sim.datasets.append(active)
      active.fit_object.functions.append([sim, False, True, False, False])
      print "Added to simulation"
  
  def toggle_show_components(self, action, window):
    sim=self.create_shg_sim()
    sim.show_components=not sim.show_components
    print "show_components=%s" % sim.show_components
    sim.simulate(window.measurement[0].x)
    sim.set_simulations()
    window.replot()
  
  def simulation_new_copy(self, action, window):
    sim=self.create_shg_sim()
    self.shg_simulation=None
    newsim=self.create_shg_sim()
    newsim.parameters=list(sim.parameters)
    newsim.parameter_names=list(sim.parameter_names)
    newsim.fit_function_text=sim.fit_function_text
    newsim.datasets=[]
    newsim.domains=map(dict, sim.domains)
    self.shg_simulation=newsim

  def simulation_new_empty(self, action, window):
    self.shg_simulation=None

  def simulation_new_all(self, action, window):
    self.shg_simulation=None
    sim=self.create_shg_sim()
    for chi in [(0, 0, 0), (1, 1, 1), (0, 1, 1), (1, 0, 0), (0, 1, 0), (1, 0, 1)]:
      sim.add_chi(chi)

class FitSessionSHG(FitSession):
  def simulate(self):
    FitSession.simulate(self)
    for fit_line in self.functions:
      if fit_line[0].__class__.__name__=='ChiMultifit' and fit_line[2]:
        fit_line[0].set_simulations()
