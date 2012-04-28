# -*- encoding: utf-8 -*-
'''
  Main window action class for data treatment.
'''

import gtk
import numpy
from copy import deepcopy
from peakfinder import PeakFinderDialog, peaks_from_preset
from dialogs import SimpleEntryDialog, DataView
from plot_script.config import user_config, transformations

__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class MainData(object):
  '''
    Data treatment actions.
  '''

  def unit_transformation(self, action):
    '''
      Open a dialog to transform the units and dimensions of one dataset.
      A set of common unit transformations is stored in config.transformations.
    '''
    # TODO: More convinient entries.
    units=self.active_session.active_file_data[self.index_mess].units()
    dimensions=self.active_session.active_file_data[self.index_mess].dimensions()
    allowed_trans=[]
    for trans in transformations.known_transformations:
      # Only unit transformation
      if len(trans)==4:
        if trans[0] in units:
          allowed_trans.append(trans)
        elif trans[3] in units:
          allowed_trans.append([trans[3], 1./trans[1],-1*trans[2]/trans[1], trans[0]])
      else:
        if (trans[0] in dimensions) and (trans[1] in units):
          allowed_trans.append(trans)
        elif (trans[4] in dimensions) and (trans[5] in units):
          allowed_trans.append([trans[4], trans[5], 1./trans[2],-1*trans[3]/trans[2], trans[0], trans[1]])

    trans_box=gtk.combo_box_new_text()
    trans_box.append_text('empty')
    trans_box.set_active(0)
    for trans in allowed_trans:
      if len(trans)==4:
        trans_box.append_text('%s -> %s'%(trans[0], trans[3]))
      else:
        trans_box.append_text('%s -> %s'%(trans[0], trans[4]))
    transformations_dialog=gtk.Dialog(title='Transform Units/Dimensions:')
    transformations_dialog.set_default_size(600, 150)
    try:
      transformations_dialog.get_action_area().pack_end(trans_box, False)
    except AttributeError:
      button_box=transformations_dialog.vbox.get_children()[-1]
      button_box.pack_end(trans_box, False)
    transformations_dialog.add_button('Add transformation', 2)
    transformations_dialog.add_button('Apply changes', 1)
    transformations_dialog.add_button('Cancel', 0)
    table=gtk.Table(1, 1, False)
    transformations_dialog.vbox.add(table)
    transformations_dialog.show_all()
    result=transformations_dialog.run()

    transformations_list=[]
    while(result==2):
      index=trans_box.get_active()
      if index>0:
        trans=allowed_trans[index-1]
      else:
        trans=['', '', 1., 0, '', '']
      self.get_new_transformation(trans, table, transformations_list, units, dimensions)
      trans_box.set_active(0)
      result=transformations_dialog.run()
    if result==1:
      transformations_=self.create_transformations(transformations_list, units, dimensions)
      self.file_actions.activate_action('unit_transformations', transformations_)
      self.replot()
      self.rebuild_menus()
    transformations_dialog.destroy()

  def get_new_transformation(self, transformations, dialog_table,
                             list_, units, dimensions):
    '''
      Create a entry field line for a unit transformation.
    '''
    table=gtk.Table(11, 1, False)
    entry_list=[]
    entry=gtk.Entry()
    entry.set_width_chars(10)
    if len(transformations)>4:
      entry.set_text(transformations[0])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                1, 2, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    selector=gtk.MenuBar()
    selector_menu_button=gtk.MenuItem('↓')
    selector.add(selector_menu_button)
    selector_menu=gtk.Menu()
    def set_entry(action, dim, unit):
      # Put the selected unit and dimension in the entries
      entry_list[0].set_text(dim)
      entry_list[1].set_text(unit)
      entry_list[4].set_text(dim)
      entry_list[5].set_text(unit)
    for i, dim in enumerate(dimensions):
      add_menu=gtk.MenuItem("%s [%s]"%(dim, units[i]))
      add_menu.connect('activate', set_entry, dim, units[i])
      selector_menu.add(add_menu)
    selector_menu_button.set_submenu(selector_menu)

    table.attach(selector,
                # X direction #          # Y direction
                0, 1, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(transformations[1])
    else:
      entry.set_text(transformations[0])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                2, 3, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    label=gtk.Label(' · ')
    table.attach(label,
                # X direction #          # Y direction
                3, 4, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(str(transformations[2]))
    else:
      entry.set_text(str(transformations[1]))
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                4, 5, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    label=gtk.Label(' + ')
    table.attach(label,
                # X direction #          # Y direction
                5, 6, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(str(transformations[3]))
    else:
      entry.set_text(str(transformations[2]))
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                6, 7, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    label=gtk.Label(' -> ')
    table.attach(label,
                # X direction #          # Y direction
                7, 8, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    entry=gtk.Entry()
    entry.set_width_chars(10)
    if len(transformations)>4:
      entry.set_text(transformations[4])
    else:
      entry.set_text(transformations[3])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                8, 9, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    entry=gtk.Entry()
    entry.set_width_chars(6)
    if len(transformations)>4:
      entry.set_text(transformations[5])
    entry_list.append(entry)
    table.attach(entry,
                # X direction #          # Y direction
                9, 10, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    item=(table, entry_list)
    list_.append(item)
    button=gtk.Button('DEL')
    table.attach(button,
                # X direction #          # Y direction
                10, 11, 0, 1,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    dialog_table.attach(table,
                # X direction #          # Y direction
                0, 1, len(list_)-1, len(list_),
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    table.show_all()
    button.connect('activate', self.remove_transformation, item, table, list_)

  def remove_transformation(self, action, item, table, list_):
    '''
      Nothing jet.
    '''
    pass

  def create_transformations(self, items, units, dimensions):
    '''
      Read the transformation values from the entry widgets in 'items'.
    '''
    transformations=[]
    for item in items:
      entries=map(lambda entry: entry.get_text(), item[1])
      # only unit transformation
      if entries[0]=='':
        if not entries[1] in units:
          continue
        else:
          try:
            transformations.append((entries[1],
                                    float(entries[2]),
                                    float(entries[3]),
                                    entries[4]))
          except ValueError:
            continue
      else:
        if not ((entries[0] in dimensions) and (entries[1] in units)):
          continue
        else:
          try:
            transformations.append((entries[0],
                                    entries[1],
                                    float(entries[2]),
                                    float(entries[3]),
                                    entries[4],
                                    entries[5]))
          except ValueError:
            continue
    return transformations

  def show_integrated_intensities(self, int_int_values):
    '''
      Show a Dialog with the values of the integrated intensities
      calculated in extract_integrated_intensities
      
      :param int_int_values: List of (x-position,y-position,value,error) for the intensities
    '''
    message="Calculated integrated intensities:\n\n"
    for item in int_int_values:
      message+="(%.2f,%.2f)\t →   <b>%g</b> ± %g\n"%item
    dialog=gtk.MessageDialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                             type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE)
    dialog.set_title('Result')
    dialog.set_markup(message)
    dialog.show_all()
    dialog.connect('response', lambda*ignore: dialog.destroy())

  def change_data_filter(self, action):
    '''
      A dialog to select filters, that remove points from the plotted dataset.
    '''
    filters=[]
    data=self.active_dataset
    filter_dialog=gtk.Dialog(title='Filter the plotted data:', parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                             buttons=('New Filter', 3, 'OK', 1, 'Apply changes', 2, 'Cancel', 0))
    filter_dialog.set_default_size(600, 150)
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    table_rows=1
    table=gtk.Table(1, 5, False)
    sw.add_with_viewport(table) # add textbuffer view widget
    filter_dialog.vbox.add(sw)
    # add lines for every active filter
    for data_filter in data.filters:
      filters.append(self.get_new_filter(table, table_rows, data, data_filter))
      table_rows+=1
      table.resize(table_rows, 5)
    filters.append(self.get_new_filter(table, table_rows, data))
    table_rows+=1
    table.resize(table_rows, 5)
    filter_dialog.show_all()
    # open dialog and wait for a response
    filter_dialog.connect("response", self.change_data_filter_response, table, filters, data)

  def change_data_filter_response(self, filter_dialog, response, table, filters, data):
    '''
      Response actions for the add data filter dialog.
    '''
    # if the response is 'New Filter' add a new filter row and rerun the dialog
    if response==3:
      filters.append(self.get_new_filter(table, len(filters)+1, data))
      filter_dialog.show_all()
    # if response is apply change the dataset filters
    if response==1 or response==2:
      new_filters=[]
      for filter_widgets in filters:
        if filter_widgets[0].get_active()==0:
          continue
        try:
          ffrom=float(filter_widgets[1].get_text())
        except ValueError:
          ffrom=None
        try:
          fto=float(filter_widgets[2].get_text())
        except ValueError:
          fto=None
        new_filters.append(\
            (filter_widgets[0].get_active()-1, \
            ffrom, \
            fto, \
            filter_widgets[3].get_active())\
            )
      self.file_actions.activate_action('change filter', new_filters)
      self.replot()
    if response<2:
      # close dialog and replot
      filter_dialog.destroy()

  def get_new_filter(self, table, row, data, parameters=(-1, 0, 0, False)):
    ''' 
      Create all widgets for the filter selection of one filter in 
      change_data_filter dialog and place them in a table.
      
      :return: Sequence of the created widgets.
    '''
    column=gtk.combo_box_new_text()
    column.append_text('None')
    # drop down menu for the columns present in the dataset
    for column_dim in data.dimensions():
      column.append_text(column_dim)
    column.set_active(parameters[0]+1)
    table.attach(column,
                # X direction #          # Y direction
                0, 1, row-1, row,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    from_data=gtk.Entry()
    from_data.set_width_chars(8)
    from_data.set_text('{from}')
    from_data.set_text(str(parameters[1]))
    table.attach(from_data,
                # X direction #          # Y direction
                1, 2, row-1, row,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    to_data=gtk.Entry()
    to_data.set_width_chars(8)
    to_data.set_text('{to}')
    to_data.set_text(str(parameters[2]))
    table.attach(to_data,
                # X direction #          # Y direction
                2, 3, row-1, row,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    include=gtk.CheckButton(label='include region', use_underline=False)
    include.set_active(parameters[3])
    table.attach(include,
                # X direction #          # Y direction
                3, 4, row-1, row,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    return (column, from_data, to_data, include)

  def combine_data_points(self, action):
    '''
      Open a dialog to combine data points together
      to get a better statistic.
    '''
    cd_dialog=gtk.Dialog(title='Combine data points:')
    table=gtk.Table(3, 4, False)
    label=gtk.Label()
    label.set_markup('Binning:')
    table.attach(label,
                # X direction #          # Y direction
                0, 1, 0, 1,
                gtk.EXPAND|gtk.FILL, gtk.FILL,
                0, 0);
    binning=gtk.Entry()
    binning.set_width_chars(4)
    binning.set_text('1')
    table.attach(binning,
                # X direction #          # Y direction
                1, 3, 0, 1,
                0, gtk.FILL,
                0, 0);
    label=gtk.Label()
    label.set_markup('Stepsize:\n(overwrites Binning)')
    table.attach(label,
                # X direction #          # Y direction
                0, 1, 1, 2,
                gtk.EXPAND|gtk.FILL, gtk.FILL,
                0, 0);
    bin_distance=gtk.Entry()
    bin_distance.set_width_chars(4)
    bin_distance.set_text('None')
    table.attach(bin_distance,
                # X direction #          # Y direction
                1, 3, 1, 2,
                0, gtk.FILL,
                0, 0);
    table.show_all()
    # Enty activation triggers calculation, too
    binning.connect('activate', lambda*ign: cd_dialog.response(1))
    bin_distance.connect('activate', lambda*ign: cd_dialog.response(1))
    cd_dialog.vbox.add(table)
    cd_dialog.add_button('OK', 1)
    cd_dialog.add_button('Cancel', 0)
    result=cd_dialog.run()
    if result==1:
      try:
        bd=float(bin_distance.get_text())
      except ValueError:
        bd=None
      self.file_actions.activate_action('combine-data',
                                        int(binning.get_text()),
                                        bd
                                        )
    cd_dialog.destroy()
    self.rebuild_menus()
    self.replot()

  def integrate_data(self, action):
    '''
      Integrate dataset using the trapezoidal rule.
    '''
    self.file_actions.activate_action('integral')
    self.rebuild_menus()
    self.replot()

  def derivate_data(self, action):
    '''
      Derivate or smooth data using the local Savitzky Golay filter or the global
      spectral estimate method calculated with a Butterworth filter.
    '''
    parameters, result=SimpleEntryDialog('Derivate Data...',
                                         [('Select Method',
                                          ['Default 1st-Order (Moving Window)',
                                          '1st-Order (Discrete)',
                                          'Default 2nd-Order',
                                          'Moving Window (Low Errorbars)',
                                          'Spectral Estimate (Noisy or Periodic Data, Equally Spaced)',
                                          ],
                                          0)]
                                         ).run()
    if not result:
      return
    if parameters['Select Method']=='1st-Order (Discrete)':
      self.file_actions.activate_action('discrete_derivative')
      self.rebuild_menus()
      self.replot()
    elif parameters['Select Method'] in ['Default 1st-Order (Moving Window)',
                                          'Default 2nd-Order',
                                          'Moving Window (Low Errorbars)']:
      if  parameters['Select Method']=='Moving Window (Low Errorbars)':
        parameters, result=SimpleEntryDialog('Derivate Data - Moving Window Filter...',
                                             (('Window Size', 5, int),
                                                ('Polynomial Order', 2, int),
                                                ('Derivative', 1, int))).run()
        if parameters['Polynomial Order']>parameters['Window Size']-2:
          parameters['Polynomial Order']=parameters['Window Size']-2
        if parameters['Derivative']+1>parameters['Polynomial Order']:
          parameters['Derivative']=parameters['Polynomial Order']-1
        if not result:
          return
      elif  parameters['Select Method']=='Default 1st-Order (Moving Window)':
        parameters={
                    'Derivative': 1,
                    'Polynomial Order': 2,
                    'Window Size': 5,
                    }
      else:
        parameters={
                    'Derivative': 2,
                    'Polynomial Order': 3,
                    'Window Size': 7,
                    }

      # create a new dataset with the smoothed data and all derivatives till the selected order
      self.file_actions.activate_action('savitzky_golay',
                        parameters['Window Size'],
                        parameters['Polynomial Order'],
                        parameters['Derivative'])
      self.rebuild_menus()
      self.replot()
    else:
      parameters, result=SimpleEntryDialog('Derivate Data - Spectral Estimate Method...',
                                           (('Filter Steepness', 4, int),
                                              ('Noise Filter Frequency (0,1]', 0.25, float),
                                              ('Derivative', 1, int))).run()
      if result:
        # create a new dataset with the smoothed data and all derivatives till the selected order
        self.file_actions.activate_action('butterworth',
                          parameters['Filter Steepness'],
                          parameters['Noise Filter Frequency (0,1]'],
                          parameters['Derivative'])
        self.rebuild_menus()
        self.replot()

  def peak_finder(self, action):
    '''
      Find peaks using continous wavelet transform peakfinder.
      Ither opens a dialog to select the search parameters
      or uses saved preset parameters.
    '''
    name=action.get_name()
    if name=='PeakFinderDialog':
      dialog=PeakFinderDialog(self, self.active_dataset)
      if 'PeakDialog' in self.config_object:
        position=self.config_object['PeakDialog']['position']
        dialog.move(*position)
      dialog.show()
      def store_peak_dialog_gemometry(widget, event):
        self.config_object['PeakDialog']={
                                 'position': widget.get_position()
                                         }
      dialog.connect('configure-event', store_peak_dialog_gemometry)
      self.open_windows.append(dialog)
    else:
      index=name[-1]
      if index in user_config['PeakFinder']['Presets']:
        preset=user_config['PeakFinder']['Presets'][index]
        if name.startswith('PeakPresetSummary'):
          peaks_from_preset(self.active_dataset, preset, self, True)
        else:
          peaks_from_preset(self.active_dataset, preset, self, False)

  def peak_info(self, action):
    '''
      Calculate peak parameters and set a label accordigly.
    '''
    dataset=self.active_dataset
    if dataset.plot_options.scan_info[0]:
      dataset.plot_options.scan_info[0]=False
      self.replot()
      return
    x=dataset.x.view(numpy.ndarray)
    y=dataset.y.view(numpy.ndarray)
    sidx=numpy.argsort(x)
    x=x[sidx]
    y=y[sidx]
    ymax=y.max()
    xmax=x[numpy.where(y==ymax)[0][0]]
    info="Maximum %g at %g"%(ymax, xmax)
    HM=ymax/2.

    # get half maximum positions
    lhalf_high=numpy.where((x<=xmax)&(y>HM))[0][0]
    rhalf_high=numpy.where((x>=xmax)&(y>HM))[0][-1]
    try:
      lhalf_low=numpy.where((x<xmax)&(y<HM))[0][-1]
      rhalf_low=numpy.where((x>xmax)&(y<HM))[0][0]
    except IndexError:
      pass
    else:
      # get relative difference to half maximum
      lrel_low=HM-y[lhalf_low]
      lrel_high=y[lhalf_high]-HM
      rrel_low=HM-y[rhalf_low]
      rrel_high=y[rhalf_high]-HM
      # left and right x value of half maximum position
      lx=(x[lhalf_low]*lrel_high+\
          x[lhalf_high]*lrel_low)/\
         (lrel_low+lrel_high)
      rx=(x[rhalf_low]*rrel_high+\
          x[rhalf_high]*rrel_low)/\
         (rrel_low+rrel_high)
      info="Peak at %g FWHM: %g\\n"%((lx+rx)/2., rx-lx)+info
    # calculate center of mass
    COM=(y*x).sum()/y.sum()
    info+="\\nCenter of mass: %g"%COM
    dataset.plot_options.scan_info[0]=True
    dataset.plot_options.scan_info[1]=info
    self.replot()

  def extract_cross_section(self, action):
    '''
      Open a dialog to select a cross-section through an 3D-dataset.
      The user can select a line and width for the cross-section,
      after this the data is extracted and appendet to the fileobject.
      
      :return: If the extraction was successful
    '''
    data=self.active_dataset
    dimension_names=[]
    dims=data.dimensions()
    dimension_names.append(dims[data.xdata])
    dimension_names.append(dims[data.ydata])
    del(dims)
    cs_dialog=SimpleEntryDialog('Create a cross-section:',
                                [
                                ('Direction-x ('+dimension_names[0]+')', 1, float),
                                ('Direction-y ('+dimension_names[1]+')', 0, float),
                                ('Origin-x ('+dimension_names[0]+')', 0, float),
                                ('Origin-y ('+dimension_names[1]+')', 0, float),
                                ('Width', 1, float),
                                ('Bin-type', ['Stepsize', 'Points'], 0),
                                ('Binning', 1, float),
                                ('Perform Gaussian weighting', False),
                                ('σ-Gauss', 1, float),
                                ('Append plot at end', False)
                                ],
                                )
    cs_dialog.register_mouse_callback(self, [[('Origin-x ('+dimension_names[0]+')', 0),
                                              ('Origin-y ('+dimension_names[1]+')', 1)]])
    values, result=cs_dialog.run()
    cs_dialog.destroy()
    if result:
      line_x=values['Direction-x ('+dimension_names[0]+')']
      line_y=values['Direction-y ('+dimension_names[1]+')']
      line_x0=values['Origin-x ('+dimension_names[0]+')']
      line_y0=values['Origin-y ('+dimension_names[1]+')']
      line_width=values['Width']
      if values['Bin-type']=='Points':
        binning=values['Binning']
        bin_distance=None
      else:
        binning=1
        bin_distance=values['Binning']
      weight=values['Perform Gaussian weighting']
      sigma=values['σ-Gauss']
      append_plot=values['Append plot at end']
      gotit=self.file_actions.activate_action('cross-section',
                                        line_x,
                                        line_x0,
                                        line_y,
                                        line_y0,
                                        line_width,
                                        binning,
                                        weight,
                                        sigma,
                                        append_plot,
                                        bin_distance
                                        )
      if not gotit:
        message=gtk.MessageDialog(parent=self,
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
    else:
      gotit=False
    cs_dialog.destroy()
    if gotit:
      self.rebuild_menus()
      self.replot()
    return gotit

  def extract_radial_integration(self, action):
    '''
      Open a dialog to select point as center of a radial integration.
      
      :return: If the extraction was successful
    '''
    data=self.active_dataset
    dimension_names=[]
    dims=data.dimensions()
    dimension_names.append(dims[data.xdata])
    dimension_names.append(dims[data.ydata])
    ri_dialog=SimpleEntryDialog('Create a radial integration:',
                                [
                                ('x0', 0, float),
                                ('y0', 0, float),
                                ('Δr', 0.001, float),
                                ('r_max', 1e10, float),
                                ],
                                description='Click on the graph to select a xy-position.'
                                )
    ri_dialog.register_mouse_callback(self, [[('x0', 0), ('y0', 1)]])
    values, result=ri_dialog.run()
    ri_dialog.destroy()
    if result:
      dr=values['Δr']
      x0=values['x0']
      y0=values['y0']
      mr=values['r_max']
      gotit=self.file_actions.activate_action('radial_integration',
                                        x0, y0, dr, mr, False
                                        )
      if not gotit:
        message=gtk.MessageDialog(parent=self,
                                  flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format='No point in selected area.')
        message.run()
        message.destroy()
    else:
      gotit=False
    if gotit:
      self.rebuild_menus()
      self.replot()
    return gotit

  def extract_integrated_intensities(self, action):
    '''
      Open a dialog to select points and datasets for integration of intensities.
      Measured data around that point is avaridged and plotted agains a user defined value.
      
      :return: If the extraction was successful
    '''
    eii_dialog=gtk.Dialog(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                          title='Select points and datasets to integrate intensities...')
    data_list=[]
    # Get all datasets with 3d data
    for key, value in sorted(self.active_session.file_data.items()):
      for i, dataset in enumerate(value):
        if dataset.zdata>=0:
          data_list.append((key, i, dataset.short_info))
    table=gtk.Table(6, 3, False)
    position_table=gtk.Table(6, 3, False)
    dataset_table=gtk.Table(3, 2, False)
    dimension=gtk.Entry()
    dimension.set_width_chars(10)
    dimension.set_text("Dimension")
    dataset_table.attach(dimension,
                # X direction #          # Y direction
                0, 1, 0, 1,
                0, gtk.FILL,
                0, 0);
    unit=gtk.Entry()
    unit.set_width_chars(10)
    unit.set_text("Unit")
    dataset_table.attach(unit,
                # X direction #          # Y direction
                1, 2, 0, 1,
                0, gtk.FILL,
                0, 0);
    label=gtk.Label("   Selected Dataset")
    dataset_table.attach(label,
                # X direction #          # Y direction
                2, 3, 0, 1,
                0, gtk.FILL,
                0, 0);
    table.attach(position_table,
                # X direction #          # Y direction
                0, 5, 0, 1,
                0, gtk.FILL,
                0, 0);
    table.attach(dataset_table,
                # X direction #          # Y direction
                0, 5, 1, 2,
                0, gtk.FILL,
                0, 0);
    datasets=[]
    int_points=[]
    add_dataset_button=gtk.Button("Add Dataset")
    add_dataset_button.connect('clicked', self.get_dataset_selection, datasets, dataset_table, data_list)
    self.get_dataset_selection(None, datasets, dataset_table, data_list)
    add_position_button=gtk.Button("Add Position")
    add_position_button.connect('clicked', self.get_position_selection, int_points, position_table)
    self.get_position_selection(None, int_points, position_table)
    table.attach(add_dataset_button,
                # X direction #          # Y direction
                2, 5, 2, 3,
                0, gtk.FILL,
                0, 0);
    table.attach(add_position_button,
                # X direction #          # Y direction
                0, 2, 2, 3,
                0, gtk.FILL,
                0, 0);
    eii_dialog.add_button('OK', 1)
    eii_dialog.add_button('Cancel', 0)
    eii_dialog.vbox.add(table)
    table.show_all()
    result=eii_dialog.run()
    if result==1:
      # User pressed OK, try to get all entry values
      did_calculate=False
      # if only one dataset is selected the values and errors of
      # the integration are stored in a list an shown in a dialog afterwards
      int_int_values=[]
      for x_pos, y_pos, radius in int_points:
        try:
          x_pos=float(x_pos.get_text())
        except ValueError:
          continue
        try:
          y_pos=float(y_pos.get_text())
        except ValueError:
          continue
        try:
          radius=float(radius.get_text())
        except ValueError:
          continue
        data_indices=[]
        data_values=[]
        for entry in datasets:
          try:
            data_value=float(entry[0].get_text())
          except ValueError:
            data_value=0.0
          data_values.append(data_value)
          dataset=data_list[entry[1].get_active()]
          data_indices.append((dataset[0], dataset[1]))
        if len(data_indices)==0:
          print "You need to select at least one dataset."
          break
        elif len(data_indices)==1:
          dataset=self.active_session.file_data[data_indices[0][0]][data_indices[0][1]]
          value, error=self.file_actions.integrate_around_point(
                                          x_pos, y_pos, radius, dataset)
          int_int_values.append((x_pos, y_pos, value, error))
          continue
        self.file_actions.activate_action('integrate_intensities', x_pos, y_pos, radius,
                                                dimension.get_text(), unit.get_text(),
                                                data_indices, data_values)
        did_calculate=True
      eii_dialog.destroy()
      if did_calculate:
        self.replot()
      if len(int_int_values)>0:
        self.show_integrated_intensities(int_int_values)
    else:
      eii_dialog.destroy()

  def interpolate_and_smooth_dialog(self, action):
    '''
      Dialog to select the options for interpolation and smoothing of 2d-data
      into a regular grid.
    '''
    def int_or_none(input_):
      try:
        return int(input_)
      except ValueError:
        return None
    parameters, result=SimpleEntryDialog('Interpolate to regular grid and smooth data...',
                         (('x-from', 0, float),
                         ('x-to', 1, float),
                         ('x-steps', '{auto}', int_or_none),
                         ('σ-x', 0.01, float),
                         ('y-from', 0, float),
                         ('y-to', 1, float),
                         ('y-steps', '{auto}', int_or_none),
                         ('σ-y', 0.01, float),
                         )).run()
    if result==1:
      self.file_actions.activate_action('interpolate_and_smooth',
                      parameters['σ-x'],
                      parameters['σ-y'],
                      parameters['x-from'],
                      parameters['x-to'],
                      parameters['x-steps'],
                      parameters['y-from'],
                      parameters['y-to'],
                      parameters['y-steps'],
                      )
      self.replot()

  def rebin_3d_data_dialog(self, action):
    '''
      Dialog to select the options for interpolation and smoothing of 2d-data
      into a regular grid.
    '''
    def int_or_none(input_):
      try:
        return int(input_)
      except ValueError:
        return None
    parameters, result=SimpleEntryDialog('Rebin regular gridded data...',
                         (('x-steps', 2, int),
                         ('y-steps', '{same as x}', int_or_none),
                         )).run()
    if result==1:
      self.file_actions.activate_action('rebin_2d',
                      parameters['x-steps'],
                      parameters['y-steps'],
                      )
      self.replot()

  def open_dataview_dialog(self, action):
    '''
      Open a Dialog with the data of the current plot, which can also be edited.
    '''
    dataset=self.active_dataset
    unchanged_dataset=deepcopy(dataset)
    dialog=DataView(dataset, buttons=('Replot', 1, 'Revert Changes',-1, 'Close', 0))
    dialog.set_default_size(800, 800)
    dialog.show()
    self.open_windows.append(dialog)
    dialog.connect('response', self.dataview_response, unchanged_dataset)

  def dataview_response(self, widget, id_, unchanged_dataset):
    '''
      Button on dataview pressed.
    '''
    if id_==0:
      widget.destroy()
    elif id_==-1:
      self.active_dataset=deepcopy(unchanged_dataset)
      self.replot()
      widget.dataset=self.active_dataset
      widget.add_data()
    else:
      self.replot()

