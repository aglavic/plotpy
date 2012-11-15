# -*- encoding: utf-8 -*-
'''
  Main window action class for data plotting.
'''

import os
import gtk
import numpy
from time import sleep
from plotpy import plotting
from plotpy.config import gnuplot_preferences
from plotpy.message import warn
from dialogs import LabelArrowDialog, StyleLine, SimpleEntryDialog, \
                    PreviewDialog, VListEntry
from diverse_classes import PlotProfile

errorbars=False

__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class MainPlotting(object):
  '''
    Plotting actions
  '''
  gnuplot_initialized=False
  label_arrow_dialog=None
  gnuplot_info={
                'version': 0,
                'patch': 0,
                'terminals': [],
                }

  def initialize_gnuplot(self):
    '''
      Check gnuplot version for capabilities.
    '''
    gnuplot_version, terminals=plotting.check_gnuplot_version(self.active_session)
    if gnuplot_version[0]<4.4:
      # mouse mode only works with version 4.4 and higher
      self.mouse_mode=False
    self.gnuplot_initialized=True
    self.gnuplot_info={
                       'version': gnuplot_version[0],
                       'patch': gnuplot_version[1],
                       'terminals': terminals,
                       }

  def plot(self, session, datasets, file_name_prefix, title, names,
            with_errorbars, output_file=gnuplot_preferences.output_file_name,
            fit_lorentz=False, sample_name=None, show_persistent=False):
    '''
      Plot via script file instead of using python gnuplot pipeing.
      
      :return: Gnuplot error messages, which have been reported
    '''
    if not self.gnuplot_initialized:
      self.initialize_gnuplot()
    try:
      output, variables=plotting.gnuplot_plotpy(session,
                                               datasets,
                                               file_name_prefix,
                                               self.script_suf,
                                               title,
                                               names,
                                               with_errorbars,
                                               output_file,
                                               fit_lorentz=False,
                                               sample_name=sample_name,
                                               show_persistent=show_persistent,
                                               get_xy_ranges=self.mouse_mode)
    except RuntimeError:
      warn("Gnuplot instance lost, try to restart ...")
      # gnuplot instance was somehow killed, try to restart
      self.active_session.initialize_gnuplot()
      return self.splot(session, datasets, file_name_prefix, title, names,
            with_errorbars, output_file, fit_lorentz, sample_name, show_persistent)
    if output=='' and variables is not None and len(variables)==8:
      # calculations to map mouse position to plot xy positions
      img_size=self.image.get_allocation()
      mr_x=variables[0]/img_size.width
      mr_width=(variables[1]-variables[0])/img_size.width
      mr_height=(variables[3]-variables[2])/img_size.height
      mr_y=(variables[3])/img_size.height-mr_height
      self.mouse_data_range=((mr_x, mr_width, mr_y, mr_height), variables[4:]+[
                                          self.get_first_in_mp().logx,
                                          self.get_first_in_mp().logy])
    return output

  def plot_persistent(self, action=None):
    '''
      Open a persistent gnuplot window.
    '''
    global errorbars
    if self.active_multiplot:
      multiplot=self.multiplot
      itemlist=[item[0] for item in multiplot]
      self.last_plot_text=self.plot(self.active_session,
                                    itemlist,
                                    multiplot[0][1],
                                    multiplot.title,
                                    [item.short_info for item in itemlist],
                                    errorbars,
                                    output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                    fit_lorentz=False,
                                    #sample_name=multiplot.sample_name,
                                    show_persistent=True)
    else:
      self.label.set_text(self.active_dataset.sample_name)
      self.label2.set_text(self.active_dataset.short_info)
      self.last_plot_text=self.plot(self.active_session,
                                  [self.active_dataset],
                                  self.input_file_name,
                                  self.active_dataset.short_info,
                                  [ds.short_info for ds in self.active_dataset.plot_together],
                                  errorbars,
                                  output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                  fit_lorentz=False,
                                  show_persistent=True)
    if self.last_plot_text!='':
      warn(self.last_plot_text, group='Gnuplot Error')
      self.show_last_plot_params(None)

  def set_image(self):
    '''
      Show the image created by gnuplot.
    '''
    # in windows we have to wait for the picture to be written to disk
    if self.active_session.OPERATING_SYSTEM=='windows':
      for ignore in range(500):
        # wait for the image to be written to disk (cache), maximal 5s 
        if os.path.exists(self.active_session.TEMP_DIR+'plot_temp.png') and\
          os.path.getsize(self.active_session.TEMP_DIR+'plot_temp.png')>1000:
            break
        else:
          sleep(0.01)
      if os.path.getsize(self.active_session.TEMP_DIR+'plot_temp.png')<1000:
        # if this was not successful stop trying.
        return False
    self.image_pixbuf=gtk.gdk.pixbuf_new_from_file(self.active_session.TEMP_DIR+'plot_temp.png')
    s_alloc=self.image.get_allocation()
    pixbuf=self.image_pixbuf.scale_simple(s_alloc.width, s_alloc.height, gtk.gdk.INTERP_BILINEAR)
    if self.mouse_mode and self.active_dataset.zdata>=0:
      try:
        # estimate the size of the plot by searching for lines with low pixel intensity (Black)
        try:
          pixbuf_data=pixbuf.get_pixels_array()[:, :, :3]
        except RuntimeError:
          # not working at the moment
          raise RuntimeError
          # get raw pixel data
          pixels=pixbuf.get_pixels()
          pixbuf_data=numpy.fromstring(pixels, numpy.uint8)
          pixbuf_data=pixbuf_data.reshape(pixbuf.get_rowstride(), len(pixbuf_data)/pixbuf.get_rowstride())
          # create 2d array
          pixbuf_data=pixbuf_data[:pixbuf.get_width()*3, :pixbuf.get_height()]
          # create 3d color array
          pixbuf_data=pixbuf_data.transpose().reshape(len(pixbuf_data[0]), len(pixbuf_data)/3, 3)
          self.pixbuf_data=pixbuf_data
        black_values=(numpy.mean(pixbuf_data, axis=2)==0.)
        # as first step get the region inside all captions including colorbar
        ysum=numpy.sum(black_values, axis=0)*1.
        xsum=numpy.sum(black_values, axis=1)*1.
        xsum/=float(len(ysum))
        ysum/=float(len(xsum))
        yids=numpy.where(xsum>xsum.max()*0.9)[0]
        xids=numpy.where(ysum>ysum.max()*0.9)[0]
        x0=float(xids[0])
        x1=float(xids[-1])
        y0=float(yids[0])
        y1=float(yids[-1])
        if not plotting.maps_with_projection:
          # try to remove the colorbar from the region
          whith_values_inside=(numpy.mean(pixbuf_data[int(y0):int(y1), int(x0):int(x1)], axis=2)==255.)
          ysum2=numpy.sum(whith_values_inside, axis=0)*1.
          ysum2/=float(y1-y0)
          xids=numpy.where(ysum2==1.)[0]
          x1=float(xids[0]+x0-1)
        x0/=len(ysum)
        x1/=len(ysum)
        y0/=len(xsum)
        y1/=len(xsum)
        self.mouse_data_range=((x0, x1-x0, 1.-y1, y1-y0), self.mouse_data_range[1])
      except:
        self.mouse_data_range=((0., 0., 0., 0.), self.mouse_data_range[1])
    self.image.set_from_pixbuf(pixbuf)
    return True

  def image_resize(self, widget, rectangel):
    '''
      Scale the image during a resize.
    '''
    if self.image_do_resize and not self.active_zoom_from and not self.active_fit_selection_from and self.mouse_arrow_starting_point is None:
      self.image_do_resize=False
      try:
        # if no image was set, there is not self.image_pixbuf
        pixbuf=self.image_pixbuf.scale_simple(rectangel.width,
                                              rectangel.height,
                                              gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
      except AttributeError:
        pass
    else:
      self.image_do_resize=True

  def toggle_plotfit(self, action):
    ds=self.active_dataset
    if ds.plot_together_zindex==-1:
      ds.plot_together_zindex=0
    elif action.get_name()=='TogglePlotFit':
      ds.plot_together_zindex=-1
    else:
      ds.plot_together_zindex+=1
      if ds.plot_together_zindex==len(ds.plot_together):
        ds.plot_together_zindex=0
    self.replot()

  def change_plot_appearance(self, action):
    name=action.get_name()
    dataset=self.get_first_in_mp()
    settings=dataset.plot_options.settings
    if name=='PlotKeyLeft':
      settings['key']=['left']
    elif name=='PlotKeyRight':
      settings['key']=['right']
    elif name=='PlotKeyBottomLeft':
      settings['key']=['bottom left']
    elif name=='PlotKeyBottomRight':
      settings['key']=['bottom right']
    elif name=='PlotToggleGrid':
      # toggle through different grid styles
      if 'grid' in settings:
        if settings['grid']==['back']:
          settings['grid']=['xtics ytics mxtics mytics back ls 1 lc 0,ls 0 lc 0']
          settings['mxtics']=['5']
          settings['mytics']=['5']
        elif settings['grid']==['xtics ytics mxtics mytics back ls 1 lc 0,ls 0 lc 0']:
          del(settings['mxtics'])
          del(settings['mytics'])
          settings['grid']=['front']
        elif settings['grid']==['front']:
          settings['grid']=['xtics ytics mxtics mytics front ls 1 lc 0,ls 0 lc 0']
          settings['mxtics']=['5']
          settings['mytics']=['5']
        else:
          del(settings['mxtics'])
          del(settings['mytics'])
          del(settings['grid'])
      else:
        settings['grid']=['back']
    elif name=='PlotToggleLinespoints':
      if gnuplot_preferences.plotting_parameters==gnuplot_preferences.plotting_parameters_lines:
        gnuplot_preferences.plotting_parameters=gnuplot_preferences.plotting_parameters_linespoints
      else:
        gnuplot_preferences.plotting_parameters=gnuplot_preferences.plotting_parameters_lines
    self.replot()

  def replot(self, echo=True):
    '''
      Recreate the current plot and clear the statusbar.
    '''
    global errorbars
    # change label and plot other picture
    self.show_add_info(None)
    # set log checkbox according to active measurement
    logitems=self.active_dataset
    if self.active_multiplot:
      if len(self.multiplot)==0:
        if echo:
          print "Empty multiplot!"
        return
      logitems=self.multiplot[0][0]
    else:
      options=self.active_dataset.plot_options
      # If the dataset has ranges but the input settings are empty, fill them
      if (self.x_range_in.get_text()=="") and ((options.xrange[0] is not None) or (options.xrange[1] is not None)):
        range_x=str(options.xrange[0])+':'+str(options.xrange[1])
        self.x_range_in.set_text(range_x.replace('None', ''))
      if (self.y_range_in.get_text()=="") and ((options.yrange[0] is not None) or (options.yrange[1] is not None)):
        range_y=str(options.yrange[0])+':'+str(options.yrange[1])
        self.y_range_in.set_text(range_y.replace('None', ''))
      if (self.z_range_in.get_text()=="") and ((options.zrange[0] is not None) or (options.zrange[1] is not None)):
        range_z=str(options.zrange[0])+':'+str(options.zrange[1])
        self.z_range_in.set_text(range_z.replace('None', ''))
    # make sure the change is ignored
    self._ignore_change=True
    self.logx.set_active(logitems.logx)
    self.logy.set_active(logitems.logy)
    self.logz.set_active(logitems.logz)
    self._ignore_change=False
    #if self.font_size_label is None:
    #  self.font_size.set_

    if echo:
      self.statusbar.push(0, 'Plotting')
      self.progressbar.set_fraction(0.)
      i=0
      # wait for all gtk events to finish to get the right size
      while gtk.events_pending() and i<10:
        gtk.main_iteration(False)
        i+=1
    self.frame1.set_current_page(0)
    self.active_session.picture_width=str(self.image.get_allocation().width)
    self.active_session.picture_height=str(self.image.get_allocation().height)
    if self.active_multiplot:
      multiplot=self.multiplot
      itemlist=[item[0] for item in multiplot]
      self.last_plot_text=self.plot(self.active_session,
                                    itemlist,
                                    multiplot[0][1],
                                    multiplot.title,
                                    [item.short_info for item in itemlist],
                                    errorbars,
                                    output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                    fit_lorentz=False,
                                    sample_name=multiplot.sample_name)
      self.label.set_width_chars(30)
      self.label.set_text(multiplot.sample_name)
      self.label2.set_width_chars(30)
      self.label2.set_text(multiplot.title)
    else:
      self.label.set_width_chars(30)
      self.label.set_text(self.active_dataset.sample_name)
      self.label2.set_width_chars(30)
      self.label2.set_text(self.active_dataset.short_info)
      self.last_plot_text=self.plot(self.active_session,
                                  [self.active_dataset],
                                  self.input_file_name,
                                  self.active_dataset.short_info,
                                  [ds.short_info for ds in self.active_dataset.plot_together],
                                  errorbars,
                                  output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                                  fit_lorentz=False)
    if self.last_plot_text!='':
      self.set_title('Plotting GUI - '+self.input_file_name+" - "+str(self.index_mess))
      self.active_plot_geometry=(self.widthf, self.heightf)
      try:
        # try to read the plot image even if there was an error
        self.set_image()
        self.progressbar.set_fraction(1.)
      except:
        pass
      if echo:
        self.progressbar.set_fraction(0.5)
        warn(None, group='Gnuplot Error')
        warn(self.last_plot_text, group='Gnuplot Error')
      #self.show_last_plot_params(None)
    else:
      self.set_title('Plotting GUI - '+self.input_file_name+" - "+str(self.index_mess))
      self.active_plot_geometry=(self.widthf, self.heightf)
      self.set_image()
      self.progressbar.set_fraction(1.)
      if not self.active_multiplot:
        self.active_dataset.preview=self.image_pixbuf.scale_simple(100, 50,
                                                        gtk.gdk.INTERP_BILINEAR)
    self.plot_options_buffer.set_text(str(self.active_dataset.plot_options))
    text=self.active_session.get_active_file_info()+self.active_dataset.get_info()
    self.info_label.set_markup(text.replace('<', '[').replace('>', ']').replace('&', 'and'))
    # make sure hugeMD objects are removed from memory after plotting
    if hasattr(self.active_dataset, 'tmp_export_file'):
      self.active_dataset.store_data()
    self.reset_statusbar()
    self.emit('plot-drawn')

  def open_plot_options_window(self, action):
    '''
      Open a dialog window to insert additional gnuplot commands.
      After opening the button is rerouted.
    '''
    # TODO: Add gnuplot help functions and character selector
    if self.plot_options_window_open:
      self.plot_options_window_open.destroy()
      self.plot_options_window_open=False
      return
    #+++++++++++++++++ Adding input fields in table +++++++++++++++++
    dialog=gtk.Dialog(title='Custom Global Gnuplot settings', parent=self)
    table=gtk.Table(6, 13, False)

    # PNG terminal
    label=gtk.Label()
    label.set_markup('Terminal for PNG export (as shown in GUI Window):')
    table.attach(label, 0, 6, 0, 1, 0, 0, 0, 0);
    terminal_png=gtk.Entry()
    terminal_png.set_text(gnuplot_preferences.set_output_terminal_image)
    table.attach(terminal_png,
                # X direction #          # Y direction
                0, 6, 1, 2,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    # PS terminal
    label=gtk.Label()
    label.set_markup('Terminal for PS export:')
    table.attach(label, 0, 6, 2, 3, 0, 0, 0, 0);
    terminal_ps=gtk.Entry()
    terminal_ps.set_text(gnuplot_preferences.set_output_terminal_ps)
    table.attach(terminal_ps,
                # X direction #          # Y direction
                0, 6, 3, 4,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);

    # x-,y- and z-label
    label=gtk.Label()
    label.set_markup('x-label:')
    table.attach(label, 0, 1, 4, 5, 0, 0, 0, 0);
    cbe=gtk.combo_box_entry_new_text()
    cbe.append_text('[x-dim] [[x-unit]]')
    x_label=cbe.get_child()
    x_label.set_width_chars(14)
    x_label.set_text(gnuplot_preferences.x_label)
    table.attach(cbe, 1, 2, 4, 5, 0, 0, 0, 0);
    label=gtk.Label()
    label.set_markup('y-label:')
    table.attach(label, 2, 3, 4, 5, 0, 0, 0, 0);
    cbe=gtk.combo_box_entry_new_text()
    cbe.append_text('[y-dim] [[y-unit]]')
    y_label=cbe.get_child()
    y_label.set_width_chars(14)
    y_label.set_text(gnuplot_preferences.y_label)
    table.attach(cbe, 3, 4, 4, 5, 0, 0, 0, 0);
    label=gtk.Label()
    label.set_markup('z-label:')
    table.attach(label, 4, 5, 4, 5, 0, 0, 0, 0);
    cbe=gtk.combo_box_entry_new_text()
    cbe.append_text('[z-dim] [[z-unit]]')
    z_label=cbe.get_child()
    z_label.set_width_chars(14)
    z_label.set_text(gnuplot_preferences.z_label)
    table.attach(cbe, 5, 6, 4, 5, 0, 0, 0, 0);

    # parameters for plot
    label=gtk.Label()
    label.set_markup('Parameters for normal plot:')
    table.attach(label, 0, 6, 5, 6, 0, 0, 0, 0);
    cbe=gtk.combo_box_entry_new_text()
    cbe.append_text('w lines lw 1.5')
    cbe.append_text('w lines')
    cbe.append_text('w linespoints lw 1 pt 7 ps 1')
    plotting_parameters=cbe.get_child()
    plotting_parameters.set_text(gnuplot_preferences.plotting_parameters)
    table.attach(cbe,
                # X direction #          # Y direction
                0, 3, 6, 7,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    # parameters for plot with errorbars
    label=gtk.Label()
    label.set_markup('Parameters for plot with errorbars:')
    table.attach(label, 0, 6, 7, 8, 0, 0, 0, 0);
    cbe=gtk.combo_box_entry_new_text()
    cbe.append_text('w errorbars pt 5 ps 0.5 lw 1.5')
    cbe.append_text('w errorbars')
    cbe.append_text('w errorlines pt 5 ps 0.5 lw 1.5')
    cbe.append_text('w errorlines')
    plotting_parameters_errorbars=cbe.get_child()
    plotting_parameters_errorbars.set_text(gnuplot_preferences.plotting_parameters_errorbars)
    table.attach(cbe,
                # X direction #          # Y direction
                0, 3, 8, 9,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    # parameters for plot in 3d
    label3d=gtk.Label()
    label3d.set_markup('Parameters for 3d plot:')
    table.attach(label3d, 0, 6, 9, 10, 0, 0, 0, 0);
    plotting_parameters_3d=gtk.Entry()
    plotting_parameters_3d.set_text(gnuplot_preferences.plotting_parameters_3d)
    table.attach(plotting_parameters_3d,
                # X direction #          # Y direction
                0, 3, 10, 12,
                gtk.EXPAND|gtk.FILL, 0,
                0, 0);
    plotting_settings_3d=gtk.TextView()
    plotting_settings_3d.get_buffer().set_text(gnuplot_preferences.settings_3d)
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(plotting_settings_3d)
    sw.show()
    table.attach(sw,
                # X direction #          # Y direction
                3, 6, 10, 11,
                gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL,
                0, 5);
    plotting_settings_3dmap=gtk.TextView()
    plotting_settings_3dmap.get_buffer().set_text(gnuplot_preferences.settings_3dmap)
    sw=gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(plotting_settings_3dmap)
    sw.show()
    table.attach(sw,
                # X direction #          # Y direction
                3, 6, 11, 12,
                gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL,
                0, 5);

    # additional Gnuplot commands
    #label=gtk.Label()
    #label.set_markup('Gnuplot commands executed additionally:')
    #table.attach(label, 0, 6, 12, 13, 0, 0, 0, 0);
    #sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    #sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    #sw.add(self.plot_options_view) # add textbuffer view widget
    #table.attach(sw,
    #            # X direction #          # Y direction
    #            0, 6, 13, 14,
    #            gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL,
    #            0, 0);
    table.show_all()
    #if self.active_dataset.zdata<0:
    #  label3d.hide()
    #  plotting_parameters_3d.hide()
    #  plotting_settings_3d.hide()
    #  plotting_settings_3dmap.hide()
    #----------------- Adding input fields in table -----------------
    dialog.vbox.add(table) # add table to dialog box
    dialog.set_default_size(300, 200)
    dialog.add_button('Apply and Replot', 1) # button replot has handler_id 1
    dialog.connect("response", self.change_plot_options,
                               terminal_png, terminal_ps,
                               x_label,
                               y_label,
                               z_label,
                               plotting_parameters,
                               plotting_parameters_errorbars,
                               plotting_parameters_3d,
                               plotting_settings_3d,
                               plotting_settings_3dmap)
    # befor the widget gets destroyed the textbuffer view widget is removed
    #dialog.connect("destroy", self.close_plot_options_window, sw)
    dialog.show()
    # reroute the button to close the dialog, not open it
    #self.plot_options_button.disconnect(self.plot_options_handler_id)
    #self.plot_options_handler_id=self.plot_options_button.connect("clicked",
    #                                              lambda*w: dialog.destroy())
    self.plot_options_window_open=dialog
    # connect dialog to main window
    #self.open_windows.append(dialog)
    #dialog.connect("destroy", lambda*w: self.open_windows.remove(dialog))
    dialog.connect("destroy", self.close_plot_options_window)

  def close_plot_options_window(self, dialog):
    '''
      Reroute the plot options button and remove the textbox when dialog is closed.
      If this is not done, the textbox gets destroyed and we can't reopen the dialog.
      
      :param dialog: The dialog widget that will be closed
      :param sw: The scrolledWindow to be unpluged before closing.
    '''
    #dialog.hide()
    #sw.remove(self.plot_options_view)
    ## reroute the button to open a new window
    #self.plot_options_button.disconnect(self.plot_options_handler_id)
    #self.plot_options_handler_id=self.plot_options_button.connect("clicked", self.open_plot_options_window)
    self.plot_options_window_open=False

  def change_plot_options(self, widget, action,
                          terminal_png,
                          terminal_ps,
                          x_label,
                          y_label,
                          z_label,
                          plotting_parameters,
                          plotting_parameters_errorbars,
                          plotting_parameters_3d,
                          plotting_settings_3d,
                          plotting_settings_3dmap):
    '''
      Plot with new commands from dialog window. Gets triggerd when the apply
      button is pressed.
    '''
    # only apply when the triggered action is realy the apply button.
    if action==1:
      found=False
      if self.active_multiplot:
        self.multiplot.plot_options=\
                 self.plot_options_buffer.get_text(\
                 self.plot_options_buffer.get_start_iter(), \
                 self.plot_options_buffer.get_end_iter())
        found=True
      if not found:
        self.active_dataset.plot_options=\
          self.plot_options_buffer.get_text(\
            self.plot_options_buffer.get_start_iter(), \
            self.plot_options_buffer.get_end_iter())
      gnuplot_preferences.set_output_terminal_image=terminal_png.get_text()
      gnuplot_preferences.set_output_terminal_ps=terminal_ps.get_text()
      gnuplot_preferences.x_label=x_label.get_text()
      gnuplot_preferences.y_label=y_label.get_text()
      gnuplot_preferences.z_label=z_label.get_text()
      gnuplot_preferences.plotting_parameters=plotting_parameters.get_text()
      gnuplot_preferences.plotting_parameters_errorbars=plotting_parameters_errorbars.get_text()
      gnuplot_preferences.plotting_parameters_3d=plotting_parameters_3d.get_text()
      buffer_=plotting_settings_3d.get_buffer()
      gnuplot_preferences.settings_3d=buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter())
      buffer_=plotting_settings_3dmap.get_buffer()
      gnuplot_preferences.settings_3dmap=buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter())
      self.replot() # plot with new settings

  def show_last_plot_params(self, action):
    '''
      Show a text window with the text, that would be used for gnuplot to
      plot the current measurement. Last gnuplot errors are shown below,
      if there have been any.
    '''
    global errorbars
    if self.active_multiplot:
      itemlist=[item[0] for item in self.multiplot]
      if self.active_dataset in itemlist:
        plot_text=plotting.create_plotpy(
                          self.active_session,
                          [item[0] for item in self.multiplot],
                          self.active_session.active_file_name,
                          '',
                          self.multiplot[0][0].short_info,
                          [item[0].short_info for item in self.multiplot],
                          errorbars,
                          self.active_session.TEMP_DIR+'plot_temp.png',
                          fit_lorentz=False)
    else:
      plot_text=plotting.create_plotpy(
                         self.active_session,
                         [self.active_dataset],
                         self.active_session.active_file_name,
                         '',
                         self.active_dataset.short_info,
                         [ds.short_info for ds in self.active_dataset.plot_together],
                         errorbars,
                         output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                         fit_lorentz=False)
    # create a dialog to show the plot text for the active data
    param_dialog=gtk.Dialog(title='Last plot parameters:')
    param_dialog.set_default_size(600, 600)
    # alignment table
    vbox1=gtk.VBox()
    paned=gtk.VPaned()

    # Label
    label=gtk.Label('Gnuplot input for the last plot:')
    vbox1.pack_start(label, expand=False)

    # plot options
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    text_field1=gtk.Label(plot_text)
    #text_filed.set_markup(plot_text.replace('<', '[').replace('>', ']'))
    sw.add_with_viewport(text_field1) # add textbuffer view widget
    vbox1.add(sw)
    paned.add1(vbox1)
    # errors of the last plot
    vbox2=gtk.VBox()
    # Label
    label=gtk.Label('Error during execution:')
    vbox2.pack_start(label, expand=False)
    sw=gtk.ScrolledWindow()
    # Set the adjustments for horizontal and vertical scroll bars.
    # POLICY_AUTOMATIC will automatically decide whether you need
    # scrollbars.
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    text_field2=gtk.Label(self.last_plot_text)
    #text_field.set_markup()
    sw.add_with_viewport(text_field2) # add textbuffer view widget
    vbox2.add(sw)
    paned.add2(vbox2)
    paned.set_position(400)
    param_dialog.vbox.add(paned)
    param_dialog.show_all()
    if self.last_plot_text=='':
      paned.set_position(580)
    def update_text(ignore):
      # recreate string after replot command
      if self.active_multiplot:
        itemlist=[item[0] for item in self.multiplot]
        if self.active_dataset in itemlist:
          new_plot_text=plotting.create_plotpy(
                            self.active_session,
                            [item[0] for item in self.multiplot],
                            self.active_session.active_file_name,
                            '',
                            self.multiplot[0][0].short_info,
                            [item[0].short_info for item in self.multiplot],
                            errorbars,
                            self.active_session.TEMP_DIR+'plot_temp.png',
                            fit_lorentz=False)
      else:
        new_plot_text=plotting.create_plotpy(
                           self.active_session,
                           [self.active_dataset],
                           self.active_session.active_file_name,
                           '',
                           self.active_dataset.short_info,
                           [ds.short_info for ds in self.active_dataset.plot_together],
                           errorbars,
                           output_file=self.active_session.TEMP_DIR+'plot_temp.png',
                           fit_lorentz=False)
      text_field1.set_text(new_plot_text)
      text_field2.set_text(self.last_plot_text)
    self.connect('plot-drawn', update_text)
    # connect dialog to main window
    self.open_windows.append(param_dialog)
    param_dialog.connect("destroy", lambda*w: self.open_windows.remove(param_dialog))

  def change_color_pattern(self, action):
    '''
      Open a dialog to select a different color pattern.
      The colorpatterns are defined in config.gnuplot_preferences.
    '''
    pattern_names=sorted(gnuplot_preferences.defined_color_patterns.keys())
    # get active name
    active_pattern='Default'
    for pattern in pattern_names:
      if gnuplot_preferences.defined_color_patterns[pattern] in gnuplot_preferences.settings_3dmap:
        active_pattern=pattern
    if 'jpeg' in self.gnuplot_info['terminals'] and not\
      os.path.exists(os.path.join(self.active_session.TEMP_DIR, 'colormap.jpg')):
      # plot available colormaps
      gptext="""# Script to plot colormaps with gnuplot
  unset xtics
  unset ytics
  unset colorbox
  set lmargin at screen 0.
  set rmargin at screen 1.
  set pm3d map
  set term jpeg size 400,%i font "%s"
  set output "%s"
  set multiplot layout %i,1
      """%(
             (len(pattern_names)*30),
             os.path.join(gnuplot_preferences.font_path, 'Arial.ttf'),
             os.path.join(self.active_session.TEMP_DIR, 'colormap.jpg').replace('\\', '\\\\'),
             len(pattern_names),
             )
      portions=1./len(pattern_names)
      for i, pattern in enumerate(pattern_names):
        gptext+='set tmargin at screen %f\nset bmargin at screen %f\n'%(1.-i*portions, 1.-(i+1.)*portions)
        gptext+='set label 1 "%s" at 50,1. center front\nset palette %s\nsplot [0:100][0:2] x w pm3d t ""\n'%(
                                    pattern,
                                    gnuplot_preferences.defined_color_patterns[pattern])
      gptext+='unset multiplot\n'
      # send commands to gnuplot
      plotting.gnuplot_instance.stdin.write('reset\n') #@UndefinedVariable
      plotting.gnuplot_instance.stdin.write(gptext) #@UndefinedVariable
      plotting.gnuplot_instance.stdin.write('\nprint "|||"\n') #@UndefinedVariable
      output=plotting.gnuplot_instance.stdout.read(3) #@UndefinedVariable
      while output[-3:]!='|||':
        output+=plotting.gnuplot_instance.stdout.read(1) #@UndefinedVariable
    pattern_box=gtk.combo_box_new_text()
    # drop down menu for the pattern selection
    for i, pattern in enumerate(pattern_names):
      pattern_box.append_text(pattern)
      if pattern==active_pattern:
        pattern_box.set_active(i)
    pattern_box.show_all()
    cps_dialog=gtk.Dialog(title='Select new color pattern:')
    cps_dialog.set_default_size(400, 400)
    nb=gtk.Notebook()
    nb.show()
    cps_dialog.vbox.add(nb)
    main_items=gtk.VBox()
    main_items.pack_start(pattern_box, False)
    try:
      # Not all versions support jpg import
      pixbuf=gtk.gdk.pixbuf_new_from_file(os.path.join(self.active_session.TEMP_DIR, 'colormap.jpg'))
      image=gtk.Image()
      image.set_from_pixbuf(pixbuf)
      image.show()
      sw=gtk.ScrolledWindow()
      # Set the adjustments for horizontal and vertical scroll bars.
      # POLICY_AUTOMATIC will automatically decide whether you need
      # scrollbars.
      sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
      sw.add_with_viewport(image)
      sw.show()
      main_items.pack_end(sw, True)
    except:
      pass
    main_items.show()
    nb.append_page(main_items, gtk.Label('Color Pallettes'))
    advanced_items=self.get_advanced_gp_tab()
    nb.append_page(advanced_items, gtk.Label('Advanced Gnuplot Settings'))

    cps_dialog.add_button('OK', 1)
    cps_dialog.add_button('Apply', 2)
    cps_dialog.add_button('Cancel', 0)
    cps_dialog.show()
    cps_dialog.connect('response', self._change_color_pattern_result,
                       active_pattern, pattern_box)
    self.open_windows.append(cps_dialog)

  def _change_color_pattern_result(self, cps_dialog, result, active_pattern, pattern_box):
    if result>0:
      pattern_names=sorted(gnuplot_preferences.defined_color_patterns.keys())
      self.file_actions.activate_action('change_color_pattern',
              gnuplot_preferences.defined_color_patterns[pattern_names[pattern_box.get_active()]])
      if result==1:
        cps_dialog.destroy()
    # reset colorscale if cancel was pressed
    if result==0:
      self.file_actions.activate_action('change_color_pattern',
              gnuplot_preferences.defined_color_patterns[active_pattern])
      cps_dialog.destroy()
    self.replot()

  def get_advanced_gp_tab(self):
    # Create entries for the advanced options of the PlotOptions class
    advanced_items = gtk.VBox() #
    pre_entry = VListEntry(self.active_dataset.plot_options.free_input, title='Custom commands before script')
    pre_entry.show()
    advanced_items.pack_start(pre_entry, expand=False)
    advanced_items.show_all()
    pre_entry.connect('activate', lambda*ignore:self.replot())
    post_entry = VListEntry(self.active_dataset.plot_options.free_input_after, 
      title='Custom commands after settings')
    post_entry.show()
    advanced_items.pack_start(post_entry, expand=False)
    button = gtk.Button('Show gnuplot script')
    button.connect('clicked', self.show_last_plot_params)
    advanced_items.pack_end(button, expand=False)
    advanced_items.show_all()
    post_entry.connect('activate', lambda*ignore:self.replot())
    return advanced_items

  def change_plot_style(self, action):
    '''
      Open a Dialog to chang the style of the current plot.
    '''
    dialog=gtk.Dialog(title='Plot style settings...', parent=self)
    dialog.set_default_size(600, 300)
    nb=gtk.Notebook()
    nb.show()
    dialog.vbox.add(nb)
    main_items=gtk.VBox()
    if self.active_multiplot:
      itemlist=[item[0] for item in self.multiplot]
      i=0
      for item in itemlist:
        for dataset in item.plot_together:
          title=gtk.HBox()
          title.show()
          entry=gtk.Label('%i'%(i+1))
          entry.show()
          tentry=gtk.Entry()
          tentry.set_text('%s'%(dataset.short_info))
          tentry.show()
          title.add(entry)
          title.add(tentry)
          main_items.pack_start(title, expand=False)
          tentry.connect('activate', self.change_plot_shortinfo, dataset)
          line=StyleLine(dataset.plot_options)
          line.show()
          line.connect('changed', lambda *ignore: self.replot())
          main_items.pack_start(line, expand=False)
          i+=1
    else:
      datasets=self.active_dataset.plot_together
      for i, dataset in enumerate(datasets):
        title=gtk.HBox()
        title.show()
        entry=gtk.Label('%i'%(i+1))
        entry.show()
        tentry=gtk.Entry()
        tentry.set_text('%s'%(dataset.short_info))
        tentry.show()
        tentry.connect('activate', self.change_plot_shortinfo, dataset)
        title.add(entry)
        title.add(tentry)
        main_items.pack_start(title, expand=False)
        line=StyleLine(dataset.plot_options)
        line.show()
        line.connect('changed', lambda *ignore: self.replot())
        main_items.pack_start(line, expand=False)
    sw=gtk.ScrolledWindow()
    sw.add_with_viewport(main_items)
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.show_all()
    nb.append_page(sw, gtk.Label('Line Styles'))
    advanced_items = self.get_advanced_gp_tab()
    nb.append_page(advanced_items, gtk.Label('Advanced Gnuplot Settings'))
    dialog.show()
    self.open_windows.append(dialog)

  def change_plot_shortinfo(self, widget, dataset):
    short_info=widget.get_text()
    dataset.short_info=short_info
    self.replot()

  def change_xyzaxis_style(self, action):
    dataset=self.get_first_in_mp()
    def float_or_none(value):
      try:
        return float(value)
      except ValueError:
        return None
    # suggest commen physical units
    exponent_values=['Off', 'No prefactor', 'With Prefactor',
                     'Prefix', 'Prefix+Unit', 'Short', 'Short Exp.']
    from plotpy.config.transformations import known_transformations
    unit_suggestions=numpy.array([item[0] for item in known_transformations])
    unit_suggestions=numpy.unique(unit_suggestions)
    entries=[
                             ['x-Dimension', dataset.x.dimension, str],
                             ['x-Unit', unit_suggestions, dataset.x.unit, str],
                             ['x-tics', dataset.plot_options.tics[0] or 'auto', float_or_none],
                             ['Exponential x-labels', exponent_values, int(dataset.plot_options.exp_format[0])],
                             ['y-Dimension', dataset.y.dimension, str],
                             ['y-Unit', unit_suggestions, dataset.y.unit, str],
                             ['y-tics', dataset.plot_options.tics[1] or 'auto', float_or_none],
                             ['Exponential y-labels', exponent_values, int(dataset.plot_options.exp_format[1])],
                             ]
    if self.active_dataset.zdata>=0:
      entries+=[
                             ['z-Dimension', dataset.z.dimension, str],
                             ['z-Unit', unit_suggestions, dataset.z.unit, str],
                             ['z-tics', dataset.plot_options.tics[2] or 'auto', float_or_none],
                             ['Exponential z-labels', exponent_values, int(dataset.plot_options.exp_format[2])],
                ]
    dialog=SimpleEntryDialog('Change label settings...',
                             entries
                             )
    value, result=dialog.run()
    if result:
      dataset.x.dimension=value['x-Dimension']
      dataset.x.unit=value['x-Unit']
      dataset.y.dimension=value['y-Dimension']
      dataset.y.unit=value['y-Unit']
      dataset.plot_options.tics[0]=value['x-tics']
      dataset.plot_options.tics[1]=value['y-tics']
      dataset.plot_options.exp_format[0]=exponent_values.index(value['Exponential x-labels'])
      dataset.plot_options.exp_format[1]=exponent_values.index(value['Exponential y-labels'])
      if self.active_dataset.zdata>=0:
        dataset.z.dimension=value['z-Dimension']
        dataset.z.unit=value['z-Unit']
        dataset.plot_options.tics[2]=value['z-tics']
        dataset.plot_options.exp_format[2]=exponent_values.index(value['Exponential z-labels'])
      self.replot()
    dialog.destroy()

  def open_label_arrows_dialog(self, action):
    if self.label_arrow_dialog is None:
      self.label_arrow_dialog=LabelArrowDialog(self.active_dataset, self)
      if 'LabelArrowDialog' in self.config_object:
        size=self.config_object['LabelArrowDialog']['size']
        position=self.config_object['LabelArrowDialog']['position']
        self.label_arrow_dialog.set_default_size(*size)
        self.label_arrow_dialog.move(*position)
      self.label_arrow_dialog.show()
      def store_la_dialog_gemometry(widget, event):
        self.config_object['LabelArrowDialog']={
                                         'size': widget.get_size(),
                                         'position': widget.get_position()
                                         }
      self.label_arrow_dialog.connect('configure-event', store_la_dialog_gemometry)
    else:
      self.label_arrow_dialog.destroy()
      self.label_arrow_dialog=None

  def toggle_error_bars(self, action):
    '''
      Show or remove error bars in plots.
    '''
    global errorbars
    errorbars=not errorbars
    self.reset_statusbar()
    self.replot()
    print 'Show errorbars='+str(errorbars)

  def toggle_xyprojections(self, action):
    '''
      Show or remove error bars in plots.
    '''
    plotting.maps_with_projection=not plotting.maps_with_projection
    self.reset_statusbar()
    self.replot()

  def colorcode_points(self, action):
    '''
      Show points colorcoded by their number.
    '''
    global errorbars
    dataset=self.active_dataset
    if errorbars:
      errorbars=False
    dataset.plot_options.special_plot_parameters="w lines palette"
    dataset.plot_options.special_using_parameters=":0"
    dataset.plot_options.settings['cblabel']=['"Pointnumber"']
    dataset.plot_options.settings['pm3d']=['map']
    dataset.plot_options.splot='s'
    self.replot()
    dataset.plot_options.special_plot_parameters=None
    dataset.plot_options.special_using_parameters=""
    dataset.plot_options.splot=''
    del(dataset.plot_options.settings['cblabel'])

  def apply_to_all(self, action):
    '''
      Apply changed plotsettings to all plots. This includes x,y,z-ranges,
      logarithmic plotting and the custom plot settings.
    '''
    use_data=self.active_dataset
    use_maxcol=max([use_data.xdata, use_data.ydata, use_data.zdata, use_data.yerror])
    selection_dialog=PreviewDialog(self.active_session.file_data, buttons=('Apply', 0, 'Cancel', 1))
    selection_dialog.set_preview_parameters(self.plot, self.active_session, self.active_session.TEMP_DIR+'plot_temp.png')
    selection_dialog.set_default_size(800, 600)
    if selection_dialog.run()==0:
      for dataset in selection_dialog.get_active_objects():
        dim=dataset.dimensions()
        # skip datasets which dont have enough columns
        if len(dim)<use_maxcol:
          continue
        # skip datasets which are 2d when this is 3d or vice vercer
        if (dataset.zdata<0) and (use_data.zdata>=0):
          continue
        dataset.xdata=use_data.xdata
        dataset.ydata=use_data.ydata
        dataset.zdata=use_data.zdata
        dataset.yerror=use_data.yerror
        dataset.logx=use_data.logx
        dataset.logy=use_data.logy
        dataset.logz=use_data.logz
        dataset.plot_options=use_data.plot_options.overwrite_copy(dataset.plot_options)
        self.reset_statusbar()
        print 'Applied settings to all Plots!'
    selection_dialog.destroy()

  def change(self, action):
    '''
      Change different plot settings triggered by different events.
      
      :param action: The action that triggered the event
    '''
    if self._ignore_change:
      return
    # change the plotted columns
    if action.get_name()=='x-number':
      if self.active_multiplot:
        for dataset, ignore in self.multiplot:
          dataset.xdata=-1
      else:
        self.active_dataset.xdata=-1
    elif action.get_name()=='y-number':
      if self.active_multiplot:
        for dataset, ignore in self.multiplot:
          dataset.ydata=-1
      else:
        self.active_dataset.ydata=-1
    elif action.get_name()[0]=='x':
      dim=action.get_name()[2:]
      if self.active_multiplot:
        col=self.multiplot[0][0].data[int(dim)].dimension
        for dataset, ignore in self.multiplot:
          dataset.xdata=dataset.dimensions().index(col)
      else:
        self.active_dataset.xdata=int(dim)
    elif action.get_name()[0:2]=='y2':
      dim=action.get_name()[3:]
      self.active_dataset.y2data=int(dim)
      if self.y2_slicing.get_active():
        ds=self.active_dataset
        ds.slice_center=ds.y2.min()+(ds.y2.max()-ds.y2.min())/2.
        ds.slice_width=(ds.y2.max()-ds.y2.min())/2.
        self.y2_center.set_range(ds.y2.min(), ds.y2.max())
        self.y2_center.set_value(ds.slice_center)
        self.y2_width.set_text("%g"%ds.slice_width)
    elif action.get_name()[0]=='y':
      dim=action.get_name()[2:]
      if self.active_multiplot:
        col=self.multiplot[0][0].data[int(dim)].dimension
        for dataset, ignore in self.multiplot:
          dataset.ydata=dataset.dimensions().index(col)
      else:
        self.active_dataset.ydata=int(dim)
    elif action.get_name()[0]=='z':
      dim=action.get_name()[2:]
      if self.active_multiplot:
        col=self.multiplot[0][0].data[int(dim)].dimension
        for dataset, ignore in self.multiplot:
          dataset.zdata=dataset.dimensions().index(col)
      else:
        self.active_dataset.zdata=int(dim)
    elif action.get_name()[0]=='d':
      dim=action.get_name()[3:]
      self.active_dataset.yerror=int(dim)
    # change 3d view position
    elif action==self.view_left:
      if self.active_dataset.view_z>=10:
        self.active_dataset.view_z=self.active_dataset.view_z-10
      else:
        self.active_dataset.view_z=350
    elif action==self.view_right:
      if self.active_dataset.view_z<=340:
        self.active_dataset.view_z=self.active_dataset.view_z+10
      else:
        self.active_dataset.view_z=0
    elif action==self.view_up:
      if self.active_dataset.view_x<=160:
        self.active_dataset.view_x=self.active_dataset.view_x+10
      else:
        self.active_dataset.view_x=0
    elif action==self.view_down:
      if self.active_dataset.view_x>=10:
        self.active_dataset.view_x=self.active_dataset.view_x-10
      else:
        self.active_dataset.view_x=170
    # change plot title labels
    elif action==self.label or action==self.label2:
      if self.active_multiplot:
        self.multiplot.sample_name=self.label.get_text()
        self.multiplot.title=self.label2.get_text()
      else:
        self.active_dataset.sample_name=self.label.get_text()
        self.active_dataset.short_info=self.label2.get_text()
    # change log settings
    elif action in (self.logx, self.logy, self.logz):
      logitems=self.get_first_in_mp()
      logitems.logx=self.logx.get_active()
      logitems.logy=self.logy.get_active()
      logitems.logz=self.logz.get_active()
    elif action is self.y2_slicing:
      ds=self.active_dataset
      if action.get_active():
        ds.slice_center=ds.y2.min()+(ds.y2.max()-ds.y2.min())/2.
        ds.slice_width=(ds.y2.max()-ds.y2.min())/2.
        self.y2_center.set_sensitive(True)
        self.y2_center.set_range(ds.y2.min(), ds.y2.max())
        self.y2_center.set_value(ds.slice_center)
        self.y2_width.set_sensitive(True)
        self.y2_width.set_text("%g"%ds.slice_width)
      else:
        ds.slice_center=None
        ds.slice_width=None
        self.y2_center.set_sensitive(False)
        self.y2_width.set_sensitive(False)
    elif action is self.y2_width:
      try:
        width=float(action.get_text())
      except ValueError:
          return
      else:
        self.active_dataset.slice_width=width
    elif action is self.y2_center:
      self.active_dataset.slice_center=action.get_value()
    elif action in [self.grid_4dx, self.grid_4dy]:
      try:
        gx=int(self.grid_4dx.get_text())
        gy=int(self.grid_4dy.get_text())
      except ValueError:
        return
      else:
        self.active_dataset.gridsize_x=gx
        self.active_dataset.gridsize_y=gy
    self.replot() # plot with new Settings

  def change_range(self, action):
    '''
      Change plotting range according to textinput.
    '''
    # set the font size
    try:
      self.active_session.font_size=float(self.font_size.get_text())
    except AttributeError:
      pass
    except ValueError:
      self.active_session.font_size=24.
      self.font_size.set_text('24')
    # get selected ranges which can be given as e.g. "[1:3]", "4:" , "3,4" , 3.2 4.5
    ranges_texts=[]
    ranges_texts.append(self.x_range_in.get_text().lstrip('[').rstrip(']'))
    ranges_texts.append(self.y_range_in.get_text().lstrip('[').rstrip(']'))
    ranges_texts.append(self.z_range_in.get_text().lstrip('[').rstrip(']'))
    for i, range_ in enumerate(ranges_texts):
      if ':' in range_:
        ranges_texts[i]=range_.replace(',', '.').split(':')
      elif ',' in range_:
        ranges_texts[i]=range_.split(',')
      else:
        ranges_texts[i]=range_.strip().split()
    xin=ranges_texts[0]
    yin=ranges_texts[1]
    zin=ranges_texts[2]
    # change ranges
    plot_options=self.active_dataset.plot_options
    if self.active_multiplot:
      plot_options=self.multiplot.plot_options
    if len(xin)==2:
      try:
        plot_options.xrange=xin
      except ValueError:
        pass
    else:
      plot_options.xrange=[None, None]
    if len(yin)==2:
      try:
        plot_options.yrange=yin
      except ValueError:
        pass
    else:
      plot_options.yrange=[None, None]
    if len(zin)==2:
      try:
        plot_options.zrange=zin
      except ValueError:
        pass
    else:
      plot_options.zrange=[None, None]
    self.replot() # plot with new settings

  def load_profile(self, action):
    '''
      Load a plot profile.
    '''
    # trigger load function from a profile in the dictionary
    self.profiles[action.get_name()].load(self)
    if self.plot_options_window_open:
      self.plot_options_button.emit("clicked")
      self.plot_options_button.emit("clicked")

  def save_profile(self, action):
    '''
      Save a plot profile.
    '''
    # open a dialog asking for the profile name
    name_dialog=gtk.Dialog(title='Enter profile name:')
    name_entry=gtk.Entry()
    name_entry.show()
    name_entry.set_text('Enter Name')
    name_entry.set_width_chars(20)
    name_dialog.add_action_widget(name_entry, 1)
    name_dialog.run()
    name=name_entry.get_text()
    name_dialog.destroy()
    # add the profile to the profiles dictionary
    self.profiles[name]=PlotProfile(name)
    self.profiles[name].save(self)
    # new profile has to be added to the menu
    self.rebuild_menus()

  def delete_profile(self, action):
    '''
      Delete a plot profile.
    '''
    # open a dialog for selecting the profiel to be deleted
    delete_dialog=gtk.Dialog(title='Delete profile')
    self.delete_name=''
    radio_group=None
    # create a list of radio buttons for the profiles
    for profile in self.profiles.items():
      if radio_group==None:
        entry=gtk.RadioButton(group=None, label=profile[0])
        radio_group=entry
      else:
        entry=gtk.RadioButton(group=radio_group, label=profile[0])
      entry.connect("clicked", self.set_delete_name)
      entry.show()
      delete_dialog.vbox.add(entry)
    delete_dialog.add_button('Delete', 1)
    delete_dialog.add_button('Abbort', 2)
    response=delete_dialog.run()
    # only delet when the response is 'Delete'
    if (response==1)&(not self.delete_name==''):
      del self.profiles[self.delete_name]
    del self.delete_name
    delete_dialog.destroy()
    # remove the deleted profile from the menu
    self.rebuild_menus()

  def change_font(self, button):
    fname=button.get_font_name()
    #print fname
    #font_path, font_name=os.path.split(fontconfig.fc[fname])
    font, fontsize=fname.rsplit(' ', 1)
    font=font.strip(',')
    gnuplot_preferences.FONT_DESCRIPTION=font
    self.active_session.font_size=float(fontsize)

    dia=gtk.MessageDialog(parent=self, type=gtk.MESSAGE_QUESTION,
                          buttons=gtk.BUTTONS_YES_NO,
                          message_format='Set font as default?')
    result=dia.run()
    dia.destroy()
    if result:
      gnuplot_preferences.font=font
      gnuplot_preferences.font_size=self.active_session.font_size
    self.replot()

