#-*- coding: utf8 -*-
'''
  Dialog for peakfinder algorithm.
'''

import os, sys
import gtk
from numpy import ndarray, array, exp, zeros_like, sqrt, argsort
from plot_script.peakfinder import PeakFinder
from plot_script.measurement_data_structure import MeasurementData, PhysicalProperty, PlotStyle
from plot_script.fit_data import FitFunction, FitSession, FitGaussian
from plot_script.config import user_config

if not 'PeakFinder' in user_config:
  user_config['PeakFinder']={'Presets':{}}

def readjust(adjustment, other, move_up):
  value=adjustment.get_value()
  ovalue=other.get_value()
  ostep=other.get_step_increment()
  if move_up and ovalue<value:
    other.set_value(value+ostep)
  elif not move_up and ovalue>value:
    other.set_value(value-ostep)


class PeakFinderDialog(gtk.Dialog):
  '''
    A dialog to select the peakfinder parameters and interactively plot the
    resulting peak positions.
  '''

  def __init__(self, parent, dataset, title='Peak Finder Parameters'):
    gtk.Dialog.__init__(self, title=title, parent=parent,
                        buttons=('Draw Peaks', 1, 'Summary', 3, 'Fit&Show', 2, 'Cancel', 0))
    self.parent_window=parent
    self.dataset=dataset
    print "Creating CWT peak finder"
    sort_idx=argsort(dataset.x)
    self.peakfinder=PeakFinder(dataset.x.view(ndarray)[sort_idx],
                               dataset.y.view(ndarray)[sort_idx],
                               )
    self._init_entries()
    self.peaks=[]
    self.plot_style=PlotStyle()
    self.plot_style.style='points'
    self.connect('response', self._responde)
    self._evaluate()
    self._responde(None, 1)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logopurple.png").replace('library.zip', ''))

  def _init_entries(self):
    '''
      Create entry widgets
    '''
    self.snr_adjust=gtk.Adjustment(value=2., lower=0.75, upper=20.,
                              step_incr=0.25, page_incr=1.)
    snr_slider=gtk.HScale(self.snr_adjust)
    self.vbox.add(gtk.Label('Signal to Noise'))
    self.vbox.add(snr_slider)

    self.min_width_adjust=gtk.Adjustment(value=0., lower=0., upper=100.,
                              step_incr=0.1, page_incr=5.)
    self.max_width_adjust=gtk.Adjustment(value=50., lower=0., upper=100.,
                              step_incr=0.1, page_incr=5.)
    self.min_width_adjust.connect('value-changed', readjust,
                                  self.max_width_adjust, True)
    self.max_width_adjust.connect('value-changed', readjust,
                                  self.min_width_adjust, False)
    min_width=gtk.HScale(self.min_width_adjust)
    max_width=gtk.HScale(self.max_width_adjust)
    self.vbox.add(gtk.Label('Minimal Peak Width'))
    self.vbox.add(min_width)
    self.vbox.add(gtk.Label('Maximal Peak Width'))
    self.vbox.add(max_width)

    self.ridge_adjust=gtk.Adjustment(value=20, lower=0, upper=100,
                              step_incr=1., page_incr=5.)
    ridge_slider=gtk.HScale(self.ridge_adjust)
    self.vbox.add(gtk.Label('CWT peak ridge length'))
    self.vbox.add(ridge_slider)

    self.auto_plot=gtk.CheckButton('Update Peaks on Change')
    self.vbox.add(self.auto_plot)

    # connect events
    self.snr_adjust.connect('value-changed', self._evaluate)
    self.min_width_adjust.connect('value-changed', self._evaluate)
    self.max_width_adjust.connect('value-changed', self._evaluate)
    self.ridge_adjust.connect('value-changed', self._evaluate)

    preset_bar=gtk.HBox()
    self.vbox.add(gtk.Label('Store Options as Preset:'))
    for i in range(5):
      preset_button=gtk.Button("%i"%(i+1))
      preset_bar.add(preset_button)
      preset_button.connect("clicked", self._save_preset, i+1)
    self.vbox.add(preset_bar)


    preset_bar=gtk.HBox()
    self.vbox.add(gtk.Label('Load Preset:'))
    preset_button=gtk.Button("Default")
    preset_bar.add(preset_button)
    preset_button.connect("clicked", self._load_preset, 6)
    for i in range(5):
      preset_button=gtk.Button("%i"%(i+1))
      preset_bar.add(preset_button)
      preset_button.connect("clicked", self._load_preset, i+1)
    self.vbox.add(preset_bar)

    self.vbox.show_all()

  def _evaluate(self, *ignore):
    '''
      Read all parameters and evaluate the peakfinder with it.
      Replot the dataset including these peaks.
    '''
    min_width_relative=self.min_width_adjust.get_value()
    max_width_relative=self.max_width_adjust.get_value()
    ds=self.dataset
    xwidth=float(ds.x.max()-ds.x.min())
    min_width=min_width_relative*xwidth*0.01
    max_width=max_width_relative*xwidth*0.01

    snr=self.snr_adjust.get_value()
    ridge_length=self.ridge_adjust.get_value()
    self.peaks=self.peakfinder.get_peaks(snr=snr,
                                    min_width=min_width,
                                    max_width=max_width,
                                    ridge_length=ridge_length,
                                    analyze=False)
    print "%i Peaks found"%len(self.peaks)
    if self.auto_plot.get_active():
      self._responde(None, 1)

  def _save_preset(self, button, index):
    min_width_relative=self.min_width_adjust.get_value()
    max_width_relative=self.max_width_adjust.get_value()
    snr=self.snr_adjust.get_value()
    ridge_length=self.ridge_adjust.get_value()
    user_config['PeakFinder']['Presets']["%i"%index]={
                'PeakWidth': (min_width_relative, max_width_relative),
                'SNR': snr,
                'RidgeLength': ridge_length,
                                                 }

  def _load_preset(self, button, index):
    if index==6:
      self.min_width_adjust.set_value(0.)
      self.max_width_adjust.set_value(50.)
      self.snr_adjust.set_value(2.)
      self.ridge_adjust.set_value(20)
      return
    str_index="%i"%index
    if str_index in user_config['PeakFinder']['Presets']:
      preset=user_config['PeakFinder']['Presets'][str_index]
      self.min_width_adjust.set_value(preset['PeakWidth'][0])
      self.max_width_adjust.set_value(preset['PeakWidth'][1])
      self.snr_adjust.set_value(preset['SNR'])
      self.ridge_adjust.set_value(preset['RidgeLength'])

  def _responde(self, ignore, response_id):
    '''
      Handle dialog response events.
    '''
    if response_id==1:
      if len(self.peaks)>0:
        ds=self.dataset
        peaks=array(self.peaks)
        xpos=peaks[:, 0]
        w=peaks[:, 1]
        BG=array([float(ds.y[(ds.x>=(xposi-2.*wi))&(ds.x<=(xposi+2.*wi))].min())\
                  for xposi, wi in zip(xpos, w)])
        I=peaks[:, 2]+BG
        md=MeasurementData()
        md.data.append(PhysicalProperty(
                                        ds.x.dimension,
                                        ds.x.unit,
                                        xpos
                                        ))
        md.data.append(PhysicalProperty(
                                        ds.y.dimension,
                                        ds.y.unit,
                                        I,
                                        ))
        md.plot_options._special_plot_parameters=self.plot_style
        md.short_info='Found Peaks'
        ds.plot_together.append(md)
        self.parent_window.replot()
        ds.plot_together.pop(-1)
      else:
        self.parent_window.replot()
    else:
      if response_id>1:
        self._fit_result(response_id==3)
      self.destroy()

  def _fit_result(self, summary=False):
    '''
      Fit Gaussians to the peaks found.
    '''
    fit_result(self.peaks,
               self.dataset,
               self.parent_window,
               summary)
    if summary:
      self._responde(None, 1)

def peaks_from_preset(ds, preset, parent_window=None, summary=False):
  '''
    Return peak positions using parameters from a preset.
  '''
  print "Creating CWT peak finder"
  sort_idx=argsort(ds.x)
  peakfinder=PeakFinder(ds.x.view(ndarray)[sort_idx],
                        ds.y.view(ndarray)[sort_idx],
                             )
  min_width_relative=preset['PeakWidth'][0]
  max_width_relative=preset['PeakWidth'][1]
  snr=preset['SNR']
  ridge_length=preset['RidgeLength']
  xwidth=float(ds.x.max()-ds.x.min())
  min_width=min_width_relative*xwidth*0.01
  max_width=max_width_relative*xwidth*0.01
  print "Filter peaks with preset options"
  peaks=peakfinder.get_peaks(snr=snr,
                            min_width=min_width,
                            max_width=max_width,
                            ridge_length=ridge_length,
                            analyze=False)
  print "Fit Gaussians to peak parameters"
  fit_result(peaks, ds, parent_window, summary)

def fit_result(peaks, ds, parent_window=None, summary=False):
  '''
    Fit Gaussians to the peaks found.
  '''
  if ds.fit_object is None and not summary:
    ds.fit_object=FitSession(ds)
  fits=[]
  for x0, sigma, I, ignore, ignore in peaks:
    fit=FitGaussian([I, x0, sigma, 0.])
    fits.append(fit)
    fit.x_from=x0-2.*sigma
    fit.x_to=x0+2.*sigma
    fit.refine(ds.x, ds.y, ds.y.error)
    fit.fit_function_text='I=[I] x_0=[x0] σ=[σ]'
    if not summary:
      ds.fit_object.functions.append([fit, False, True, False, False])
  if not summary:
    ds.fit_object.simulate()
    parent_window.replot()
  else:
    parameter_names=['x', 'Δx', 'I', 'ΔI', 'σ', 'Δσ']
    parameters=[]
    for fit in fits:
      covar=fit.last_fit_output.covar
      errors=[sqrt(covar[j, j]) for j in range(3)]
      params=fit.parameters
      parameters.append([params[1], errors[1],
                         params[0], errors[0],
                         params[2], errors[2]])
    dialog=FitSummary(parameter_names, parameters, title='Peak Summary',
                      parent=parent_window)
    dialog.set_default_size(700, 400)
    dialog.show()

class FitSummary(gtk.Dialog):
  '''
    Dialog with a treeview of the peak data.
  '''

  def __init__(self, parameter_names, parameters, **opts):
    gtk.Dialog.__init__(self, **opts)
    self.liststore=gtk.ListStore(int, *[float for ignore in range(len(parameter_names))])
    self.treeview=gtk.TreeView(self.liststore)
    self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    self.treeview.set_rubber_banding(True)
    self.columns=parameter_names
    self.create_columns()
    # insert the treeview in the dialog
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(self.treeview)
    sw.show_all()
    self.vbox.add(sw)
    # insert the data into the treeview
    self.add_data(parameters)
    self.set_icon_from_file(os.path.join(
                            os.path.split(
                           os.path.realpath(__file__))[0],
                           "..", "config", "logopurple.png").replace('library.zip', ''))
    self.clipboard=gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    self.treeview.connect('key-press-event', self.key_press_response)
    self.data=parameters

  def create_columns(self):
    '''
      Add columns to the treeview.
    '''
    columns=self.columns
    textrenderer=gtk.CellRendererText()
    textrenderer.set_property('editable', False)
    # Add the columns
    column=gtk.TreeViewColumn('Peak', textrenderer, text=0)
    column.set_sort_column_id(0)
    self.treeview.append_column(column)
    for i, col in enumerate(columns):
      column=gtk.TreeViewColumn('%s'%(col), textrenderer, text=i+1)
      column.set_sort_column_id(i+1)
      self.treeview.append_column(column)

  def add_data(self, parameters):
    '''
      Add the data to the treeview.
    '''
    for i, peak in enumerate(parameters):
      self.liststore.append([i+1]+list(peak))

  def key_press_response(self, widget, event):
    keyname=gtk.gdk.keyval_name(event.keyval)
    if event.state&gtk.gdk.CONTROL_MASK:
      # copy selection
      if keyname=='c':
        ignore, selection=self.treeview.get_selection().get_selected_rows()
        indices=map(lambda select: self.liststore[select][0]-1, selection)
        items=map(lambda index: "\t".join(map(str, self.data[index])), indices)
        clipboard_content="#"+"\t".join(self.columns)+"\n"+"\n".join(items)
        self.clipboard.set_text(clipboard_content)
      if keyname=='a':
        self.treeview.get_selection().select_all()

class FitMultiGauss(FitFunction):
  '''
    Fit multiple Gauss functions including linear interpolated background.
  '''

  name="MultipleGaussian"
  parameters=[]
  parameter_names=[]
  parameter_description={'I': 'Scaling'}
  fit_function_text=''
  number_peaks=0
  max_iter=50

  def __init__(self, peak_params):
    parameters=[]
    parameter_names=[]
    fit_function_text=''
    constrains={}
    for i, peak in enumerate(peak_params):
      parameters.append(peak[2])
      parameter_names.append("I_%i"%(i+1))
      parameters.append(peak[0])
      parameter_names.append("x_%i"%(i+1))
      parameters.append(peak[1])
      parameter_names.append("σ_%i"%(i+1))
      fit_function_text+='I_{%i}=[I_%i]  x_{%i}=[x_%i]  σ_{%i}=[σ_%i]\\n'%tuple([i+1]*6)
      # only positive intensities
      constrains[i*3]={'bounds': [0, None], 'tied': ''}
    parameters.append(0.)
    parameter_names.append('BG')
    #for i in range(len(peak_params)):
    #  parameters.append(0.)
    #  parameter_names.append('BG_%i'%(i+1))
    self.parameters=parameters
    self.parameter_names=parameter_names
    self.fit_function_text=fit_function_text
    self.number_peaks=len(peak_params)
    self.constrains=constrains
    FitFunction.__init__(self, self.parameters)

  def fit_function(self, p, x):
    '''
      Gaussian functions for each peak.
    '''
    I=zeros_like(x)
    for i in range(self.number_peaks):
      I+=p[i*3]*exp(-0.5*((x-p[i*3+1])/p[i*3+2])**2)
    I+=p[-1]
    return I

#  def BG(self, p, x):
#    '''
#      Linear interpolated background between all peaks
#    '''
#    BG=zeros_like(x)
#    BGparams=p[self.number_peaks:]
#    for i in range(self.number_peaks):
#      if i>0:
#        x0=p[i*3+1]
#      else:
#        x0=x.min()
#      if i<(self.number_peaks-1):
#        x1=p[(i+1)*3+1]
#      else:
#        x1=x.max()
#      a=(BGparams[i+1]-BGparams[i])/(x1-x0) # background slope
#      b=BGparams[i]-a*x0  # background offset
#      region=(x>=x0)&(x<x1)
#      BG[region]+=a*x[region]+b
#    BG[x==x1]=BGparams[-1]
#    return BG
