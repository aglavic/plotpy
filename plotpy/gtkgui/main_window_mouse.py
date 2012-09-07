# -*- encoding: utf-8 -*-
'''
  Main window mouse actions.
'''

import numpy
import gtk

from dialogs import SimpleEntryDialog
from plotpy import fitdata

__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class MainMouse(object):
  '''
    Mouse movement actions.
  '''

  # used for mouse tracking and interaction on the picture
  mouse_mode=True
  mouse_data_range=[(0., 1., 0., 1.), (0., 1., 0., 1., False, False)]
  mouse_position_callback=None
  mouse_arrow_starting_point=None
  active_zoom_from=None
  active_zoom_last_inside=None
  active_fit_selection_from=None

  def update_picture(self, widget, event):
    '''
      After releasing the mouse the picture gets replot.
    '''
    if event.type==gtk.gdk.FOCUS_CHANGE and self.active_plot_geometry!=(self.widthf, self.heightf) and self.init_complete:
      self.replot()

  def catch_mouse_position(self, widget, action):
    '''
      Get the current mouse position when the pointer was mooved on to of the image.
    '''
    if not self.mouse_mode:
      return
    position=self.get_position_on_plot()
    if position is not None:
      self.xindicator.set_text('%12g'%position[0])
      self.yindicator.set_text('%12g'%position[1])
      if self.active_zoom_from is not None:
        # When a zoom drag is active draw a rectangle on the image
        self.active_zoom_last_inside=position
        az=self.active_zoom_from
        self.image_pixmap.draw_rectangle(self.get_style().black_gc, False, min(az[4], position[4]),
                                                                            min(az[5], position[5]),
                                         abs(position[4]-az[4]), abs(position[5]-az[5]))
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Zoom: x1=%10g  y1=%10g'%(az[0], az[1]))
        self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
      elif self.active_fit_selection_from is not None:
        # When a drag is active draw a rectangle on the image
        af=self.active_fit_selection_from
        self.image_pixmap.draw_rectangle(self.get_style().black_gc, False, min(af[4], position[4]),
                                                                            min(af[5], position[5]),
                                         abs(position[4]-af[4]), abs(position[5]-af[5]))
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Fit-region: x1=%10g  y1=%10g'%(af[0], af[1]))
        self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
      elif self.mouse_arrow_starting_point is not None:
        # if an arrow drag is active show a different status and draw a line from the starting
        # point to the active mouse position
        ma=self.mouse_arrow_starting_point
        self.image_pixmap.draw_line(self.get_style().black_gc, ma[4], ma[5], position[4], position[5])
        self.image.set_from_pixmap(self.image_pixmap, self.image_mask)
        self.statusbar.push(0, 'Draw Arrow: x1=%10g y1=%10g'%(ma[0], ma[1]))
        self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
      else:
        # show the position of the cusor on the plot
        if 'GDK_CONTROL_MASK' in action.state.value_names:
          info='Fit peak with gaussian (left), voigt (middle) or lorentzian (right) profile.'
        elif 'GDK_SHIFT_MASK' in action.state.value_names:
          info='Place label (left), draw arrow (middle) or label position (right).'
        else:
          info='Zoom (right), unzoom (middle). <ctrl>-fit / <shift>-label/arrow'
        self.statusbar.push(0, info)
      try:
        # if the cusor is inside the plot we change it's icon to a crosshair
        self.image.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSSHAIR))
      except AttributeError:
        # catch an example when event is triggered after window got closed
        pass
    else:
      try:
        # reset the mouse icon
        self.image.window.set_cursor(None)
      except AttributeError:
        # catch an example when event is triggered after window got closed
        pass

  def mouse_press(self, widget, action):
    '''
      Catch mouse press event on image.
    '''
    if not self.mouse_mode:
      return
    position=self.get_position_on_plot()
    dataset=self.get_first_in_mp()
    if 'GDK_CONTROL_MASK' in action.state.value_names:
      # control was pressed during button press
      # fit a peak function to the active mouse position
      if position is not None:
        self.active_fit_selection_from=position
        self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
      else:
        self.active_fit_selection_from=None
    elif not 'GDK_SHIFT_MASK' in action.state.value_names:
      # no control/alt/shift button is pressed
      if action.button==3:
        # Zoom into region
        if position is not None:
          self.active_zoom_from=position
          self.active_zoom_last_inside=position
          self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
        else:
          self.active_zoom_from=None
      if action.button==1 and position is not None and self.mouse_position_callback is not None:
        # activate a function registered as callback
        self.mouse_position_callback(position)
      if action.button==2:
        # unzoom the plot
        dataset.plot_options.xrange=[None, None]
        dataset.plot_options.yrange=[None, None]
        self.x_range_in.set_text('')
        self.y_range_in.set_text('')
        self.replot()
      if 'GDK_2BUTTON_PRESS'==action.type.value_name:
        # double klick event
        if action.button==1:
          if position is None:
            return self.change_xyzaxis_style(None)
          else:
            if dataset.zdata<0:
              return self.change_plot_style(None)
            else:
              return self.change_color_pattern(None)
    else:
      # shift pressed during button press leads to label or arrow
      # to be added to the plot
      if position is not None:
        ds=dataset
        if action.button==1:
          parameters, result=SimpleEntryDialog('Enter Label...',
                                         [('Text', 'Label', str)]
                                         ).run()
          if result:
            ds.plot_options.labels.append([(position[0], position[1], 1),
                                           parameters['Text'], True, False, False, False, ''])

            if self.label_arrow_dialog is not None:
              self.label_arrow_dialog.update()
        if action.button==2:
          self.mouse_arrow_starting_point=position
          self.image_pixmap, self.image_mask=self.image_pixbuf.render_pixmap_and_mask()
        if action.button==3:
          parameters, result=SimpleEntryDialog('Enter Label...',
                                         [('Text', '(%g,%g)'%(position[0], position[1]), str)]
                                         ).run()
          if result:
            ds.plot_options.labels.append([(position[0], position[1], 1),
                                           parameters['Text'], True, True, False, False, ''])

            if self.label_arrow_dialog is not None:
              self.label_arrow_dialog.update()
        self.replot()

  def mouse_release(self, widget, action):
    '''
      Catch mouse release event.
    '''
    position=self.get_position_on_plot()
    dataset=self.get_first_in_mp()
    if self.active_zoom_from is not None:
      # Zoom in to the selected Area
      if position is None or abs(position[2]-self.active_zoom_from[2])<0.1 and abs(position[3]-self.active_zoom_from[3])<0.1:
        # if mouse is outside the ploted region, use the last position where it was inside
        position=self.active_zoom_last_inside
      dsp=dataset.plot_options
      x0=min(position[0], self.active_zoom_from[0])
      x1=max(position[0], self.active_zoom_from[0])
      y0=min(position[1], self.active_zoom_from[1])
      y1=max(position[1], self.active_zoom_from[1])
      dsp.xrange=[x0, x1]
      dsp.yrange=[y0, y1]
      self.active_zoom_from=None
      self.replot()
    if self.mouse_arrow_starting_point is not None:
      # draw an arrow in the plot
      start=self.mouse_arrow_starting_point
      self.mouse_arrow_starting_point=None
      if position is not None:
        dataset.plot_options.arrows.append([((start[0], start[1], 1),
                                             (position[0], position[1], 1)),
                                            False, True, ''])
        self.replot()
        if self.label_arrow_dialog is not None:
          self.label_arrow_dialog.update()
    if self.active_fit_selection_from is not None:
      start=self.active_fit_selection_from
      self.active_fit_selection_from=None
      if position is None or self.active_multiplot:
        return
      ds=dataset
      if (abs(start[2]-position[2])+abs(start[3]-position[3]))<0.03:
        # Position was only clicked
        if ds.zdata>=0:
          return
        width=(ds.x.max()-ds.x.min())/10.
        start_range=None
        end_range=None
        x_0=position[0]
        I=position[1]
        bg=0.
      else:
        # Position was dragged, define a range of plotting
        width=abs(position[0]-start[0])/4.
        start_range=min(position[0], start[0])
        end_range=max(position[0], start[0])
        x_0=(end_range-start_range)/2.+start_range
        if ds.zdata>=0:
          start_range_y=min(position[1], start[1])
          end_range_y=max(position[1], start[1])
          y_0=(end_range_y-start_range_y)/2.+start_range_y
          I=ds.z[((ds.x>=start_range)&(ds.x<=end_range)&\
                  (ds.y>=start_range_y)&(ds.y<=end_range_y))].max()
          bg=ds.z[((ds.x>=start_range)&(ds.x<=end_range)&\
                  (ds.y>=start_range_y)&(ds.y<=end_range_y))].min()
        else:
          I=abs(position[1]-start[1])/4.
          bg=min(position[1], start[1])
      if (ds.fit_object==None):
        ds.fit_object=fitdata.FitSession(ds)
      if ds.zdata<0:
        if action.button==1:
          gaussian=fitdata.FitGaussian([ I, x_0, width, bg])
          gaussian.x_from=start_range
          gaussian.x_to=end_range
          gaussian.refine(ds.x, ds.y)
          ds.fit_object.functions.append([gaussian, False, True, False, False])
        if action.button==2:
          voigt=fitdata.FitVoigt([ I, x_0, width/2., width/2., bg])
          voigt.x_from=start_range
          voigt.x_to=end_range
          voigt.refine(ds.x, ds.y)
          ds.fit_object.functions.append([voigt, False, True, False, False])
        if action.button==3:
          lorentz=fitdata.FitLorentzian([ I, x_0, width, bg])
          lorentz.x_from=start_range
          lorentz.x_to=end_range
          lorentz.refine(ds.x, ds.y)
          ds.fit_object.functions.append([lorentz, False, True, False, False])
      else:
        if action.button==1:
          gaussian=fitdata.FitGaussian3D([ I, x_0, y_0, width, width, 0., bg])
          gaussian.x_from=start_range
          gaussian.x_to=end_range
          gaussian.y_from=start_range_y
          gaussian.y_to=end_range_y
          gaussian.constrains[4]={'bounds': [None, None], 'tied': ''}
          gaussian.refine_parameters=range(7)
          gaussian.fit_function_text='G: [I] at [x_0],[y_0]'
          gaussian.refine(ds.x, ds.y, ds.z)
          ds.fit_object.functions.append([gaussian, False, True, False, False])
        if action.button==2:
          voigt=fitdata.FitPsdVoigt3D([ I, x_0, y_0, width/2., width/2.,
                                        width/2., width/2., 0., 0.5, bg])
          voigt.x_from=start_range
          voigt.x_to=end_range
          voigt.y_from=start_range_y
          voigt.y_to=end_range_y
          voigt.constrains[4]={'bounds': [None, None], 'tied': ''}
          voigt.fit_function_text='V: [I] at [x_0],[y_0]'
          voigt.refine(ds.x, ds.y, ds.z)
          ds.fit_object.functions.append([voigt, False, True, False, False])
        if action.button==3:
          lorentz=fitdata.FitLorentzian3D([ I, x_0, y_0, width, width, 0., bg])
          lorentz.x_from=start_range
          lorentz.x_to=end_range
          lorentz.y_from=start_range_y
          lorentz.y_to=end_range_y
          lorentz.constrains[4]={'bounds': [None, None], 'tied': ''}
          lorentz.refine_parameters=range(7)
          lorentz.fit_function_text='L: [I] at [x_0],[y_0]'
          lorentz.refine(ds.x, ds.y, ds.z)
          ds.fit_object.functions.append([lorentz, False, True, False, False])
      self.file_actions.activate_action('simmulate_functions')
      if ds.zdata>=0:
        self.rebuild_menus()
      self.replot()

  def get_position_on_plot(self):
    '''
      Calculate the position of the mouse cursor on the plot. If the cursor
      is outside, return None.
    '''
    position=self.image.get_pointer()
    img_size=self.image.get_allocation()
    #img_width=float(img_size[2]-img_size[0])
    #img_height=float(img_size[3]-img_size[1])
    mr, pr=self.mouse_data_range
    if mr[1]==0. or mr[3]==0.:
      return None
    mouse_x=position[0]/float(img_size.width)
    mouse_x-=mr[0]
    mouse_x/=mr[1]
    mouse_y=1.-position[1]/float(img_size.height)
    mouse_y-=mr[2]
    mouse_y/=mr[3]
    if not (mouse_x>=0. and mouse_x<=1. and mouse_y>=0. and mouse_y<=1.):
      return None
    if pr[4]:
      x_position=10.**(mouse_x*(numpy.log10(pr[1])-numpy.log10(pr[0]))+numpy.log10(pr[0]))
    else:
      x_position=(pr[1]-pr[0])*mouse_x+pr[0]
    if pr[5]:
      y_position=10.**(mouse_y*(numpy.log10(pr[3])-numpy.log10(pr[2]))+numpy.log10(pr[2]))
    else:
      y_position=(pr[3]-pr[2])*mouse_y+pr[2]
    return x_position, y_position, mouse_x, mouse_y, position[0], position[1]

  def toggle_mouse_mode(self, action=None):
    '''
      Activate/Deactivate cursor mode.
    '''
    self.mouse_mode=not self.mouse_mode
    self.replot()

