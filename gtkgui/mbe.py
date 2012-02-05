#-*- coding: utf8 -*-
'''
  LEED GTK gui class 
'''

#+++++++++++++++++++++++ importing modules ++++++++++++++++++++++++++

from numpy import sin, cos, arctan, sqrt, pi, ndarray, where
# own modules
from measurement_data_structure import PhysicalProperty
from gtkgui.dialogs import SimpleEntryDialog, MouseReader
from config.mbe import LEED_SCREEN_SIZE, LEED_DISTANCE, H_over_2m, \
                       RHEED_SCREEN_SIZE, RHEED_DISTANCE, RHEED_CENTER_X, \
                       RHEED_CENTER_Y, RHEED_SCREEN_PIXELS, O_ENERGY
from fit_data import FitGaussian3D
#from dialogs import SimpleEntryDialog

#----------------------- importing modules --------------------------


__author__="Artur Glavic"
__credits__=[]
from plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"


class MBEGUI:
#  def new_configuration(self, setups, file_name, folder):
#    '''
#      Create a new intrumental setup.
#    '''
#    #file_type=file_name.rsplit('.', 1)[-1]
#    setup=dict(setup_config)
#    dialog=SimpleEntryDialog('File parameters:', [
#                      ('Screen Center x [pix]', setup['CENTER_X'], float),
#                      ('Screen Center y [pix]', setup['CENTER_Y'], float),
#                      ('Screen Tilt [°]', setup['TILT'], float),
#                      ('Screen Diameter [mm]', setup['DETECTOR_DIAMETER'], float),
#                      ('Screen Diameter [pix]', setup['DETECTOR_PIXELS'], float),
#                      ('Screen-Sample Distance [mm]', setup['DETECTOR_DISTANCE'], float),
#                      ('Swap xy-axes', setup['SWAP_YZ']),
#                      ('Electron Energy [eV]', setup['ENERGY'], float),
#                      ('Apply to Files', file_name, str),
#                                                  ])
#    parameters, result=dialog.run()
#    if result:
#      file_names=parameters['Apply to Files']
#      setup={
#              'CENTER_X' : parameters['Screen Center x [pix]'],
#              'CENTER_Y' : parameters['Screen Center y [pix]'],
#              'TILT' : parameters['Screen Tilt [°]'],
#              'DETECTOR_DIAMETER': parameters['Screen Diameter [mm]'],
#              'DETECTOR_PIXELS': parameters['Screen Diameter [pix]'],
#              'DETECTOR_DISTANCE': parameters['Screen-Sample Distance [mm]'],
#              'ENERGY' : parameters['Electron Energy [eV]'],
#              'SWAP_YZ': parameters['Swap xy-axes'],
#             }
#      setups[file_names]=setup
#      setups.write()
#    dialog.destroy()

  def create_menu(self):
    '''
      Create a specifig menu for the DNS session
    '''
    # Create XML for squid menu
    string='''
      <menu action='ED'>
        <menuitem action='LEEDtoQ'/>
        <menuitem action='RHEEDtoQ'/>
        <menuitem action='AESCorrect'/>
      </menu>
    '''
    # Create actions for the menu
    actions=(
            ("ED", None, # name, stock id
              "Electron Diffraction", None, # label, accelerator
              None, # tooltip
              None),
            ("LEEDtoQ", None, # name, stock id
             "Transform LEED data to Q-Space", "<control>L", # label, accelerator
                None, # tooltip
                self.leed_to_q),
            ("RHEEDtoQ", None, # name, stock id
             "Transform RHEED data to Q-Space", "<control>R", # label, accelerator
                None, # tooltip
                self.rheed_to_q),
            ("AESCorrect", None, # name, stock id
             "Correct AES Energy", "<control>A", # label, accelerator
                None, # tooltip
                self.correct_aes),
                )
    return string, actions

  #++++++++++++++++++++++++++ data treatment functions ++++++++++++++++++++++++++++++++

  def correct_aes(self, action, window):
    '''
      Correct the x-position of an AES spectrum.
    '''
    dataset=window.active_dataset
    if window.mouse_mode:
      old_freeinput=dataset.plot_options.free_input
      old_range=dataset.plot_options.xrange
      dataset.plot_options.xrange=[O_ENERGY-100., O_ENERGY+100.]
      dataset.plot_options.free_input=[
             'set label "O" at %f, %f point front'%(O_ENERGY, 0.),
             'set arrow from %f,%f to %f,%f nohead front'%(O_ENERGY-100.,
                                                           0.,
                                                           O_ENERGY+100.,
                                                           0.),
                                       ]
      window.replot()
      dataset.plot_options.free_input=old_freeinput
      dataset.plot_options.xrange=old_range
      position=MouseReader('Select Position of Oxygen Line', window).run()
    else:
      position=(O_ENERGY, 0.)
    dialog=SimpleEntryDialog('AES correction:',
                             [
                              ('Oxygen Line [eV]', position[0], float),
                              ]
                             )
    parameters, result=dialog.run()
    dialog.destroy()
    if result:
      dataset.x-=parameters['Oxygen Line [eV]']-O_ENERGY
      window.replot()


  def leed_to_q(self, action, window):
    '''
      Transform the data from xy to QxQy.
    '''
    if window.mouse_mode:
      dataset=window.active_dataset
      if dataset.xdata==3:
        dataset.xdata=0
        dataset.ydata=1
        dataset.plot_options.xrange=[None, None]
        dataset.plot_options.yrange=[None, None]
        dataset.is_matrix_data=True
        window.replot()
      # The mouse can be used to get center positions, tilt and screen size 
      point11=MouseReader('Select one point in Qx', window).run()
      point12=MouseReader('Select a second point in Qx', window).run()
      point21=MouseReader('Select one point in Qy', window).run()
      point3=MouseReader('Select a point on the screen edge', window).run()
      # refine positions
      x, y, z=dataset.data[0:3]
      fit=FitGaussian3D([50., point11[0], point11[1], 5., 5., 0., 10.])
      region=where((x>=(point11[0]-30))&(x<=(point11[0]+30))&\
                   (y>=(point11[1]-30))&(y<=(point11[1]+30)))
      fit.refine(x[region], y[region], z[region])
      point11=fit.parameters[1:3]
      fit=FitGaussian3D([50., point12[0], point12[1], 5., 5., 0., 10.])
      region=where((x>=(point12[0]-30))&(x<=(point12[0]+30))&\
                   (y>=(point12[1]-30))&(y<=(point12[1]+30)))
      fit.refine(x[region], y[region], z[region])
      point12=fit.parameters[1:3]
      fit=FitGaussian3D([50., point21[0], point21[1], 5., 5., 0., 10.])
      region=where((x>=(point21[0]-30))&(x<=(point21[0]+30))&\
                   (y>=(point21[1]-30))&(y<=(point21[1]+30)))
      fit.refine(x[region], y[region], z[region])
      point21=fit.parameters[1:3]


      # calculate center and radius from the 5 points
      # distance square points in x
      L=((point11[0]-point12[0])**2+(point11[1]-point12[1])**2)
      # distance square point 1 in x to point 1 in y
      A1=((point11[0]-point21[0])**2+(point11[1]-point21[1])**2)
      # distance square point 2 in x to point 1 in y
      A2=((point12[0]-point21[0])**2+(point12[1]-point21[1])**2)
      L1=(A1-A2+L)/2./sqrt(L)
      center_x=point11[0]-(point11[0]-point12[0])*L1/sqrt(L)
      center_y=point11[1]-(point11[1]-point12[1])*L1/sqrt(L)
      screen_size=sqrt((point3[0]-center_x)**2+(point3[1]-center_y)**2)*2.
      tilt=arctan((center_y-point11[1])/(center_x-point11[0]))*180./pi

      old_freeinput=dataset.plot_options.free_input
      dataset.plot_options.free_input=[
             'set label "Point 1" at %f, %f point front'%tuple(point11),
             'set label "Point 2" at %f, %f point front'%tuple(point12),
             'set label "Point 3" at %f, %f point front'%tuple(point21),
             'set label "Center" at %f, %f point front'%(center_x, center_y),
             'set arrow from %f,%f to %f,%f nohead front'%(center_x, center_y,
                                                           point3[0], point3[1]),
                                       ]
      window.replot()
      dataset.plot_options.free_input=old_freeinput
    else:
      center_x=100.
      center_y=100.
      screen_size=500.
      tilt=0.
    dialog=SimpleEntryDialog('LEED parameters:',
                             [
                              ('Energy [eV]', 100., float),
                              ('Center x [pix]', center_x, float),
                              ('Center y [pix]', center_y, float),
                              ('Screen Size [pix]', screen_size, float),
                              ('Axes tilt [°]', tilt, float),
                              ]
                             )
    parameters, result=dialog.run()
    dialog.destroy()
    if result:
      dataset=window.active_dataset
      x, y=dataset.data[0:2]

      lamda=H_over_2m/sqrt(parameters['Energy [eV]'])
      pixel_size=LEED_SCREEN_SIZE/parameters['Screen Size [pix]']
      th_x=arctan((x.view(ndarray)-parameters['Center x [pix]'])*pixel_size/LEED_DISTANCE)
      th_y=arctan((y.view(ndarray)-parameters['Center y [pix]'])*pixel_size/LEED_DISTANCE)
      tilt=parameters['Axes tilt [°]']*pi/180.
      qx_array=2.*pi/lamda*sin(th_x)
      qy_array=2.*pi/lamda*sin(th_y)
      qtmp=qx_array
      qx_array=qx_array*cos(tilt)+qy_array*sin(tilt)
      qy_array=qy_array*cos(tilt)-qtmp*sin(tilt)

      if len(dataset.data)==3:
        dataset.data.append(PhysicalProperty('Q_x', 'Å^{-1}', qx_array))
        dataset.data.append(PhysicalProperty('Q_y', 'Å^{-1}', qy_array))
      else:
        dataset.data[3]=PhysicalProperty('Q_x', 'Å^{-1}', qx_array)
        dataset.data[4]=PhysicalProperty('Q_y', 'Å^{-1}', qy_array)
      dataset.is_matrix_data=False
      dataset.xdata=3
      dataset.ydata=4
      dataset.plot_options.xrange=[None, None]
      dataset.plot_options.yrange=[None, None]
      window.rebuild_menus()
      window.replot()

  def rheed_to_q(self, action, window):
    '''
      Transform the data from xy to QxQy.
    '''
    if window.mouse_mode:
      dataset=window.active_dataset
      if dataset.xdata==4:
        dataset.xdata=0
        dataset.ydata=1
        dataset.plot_options.xrange=[None, None]
        dataset.plot_options.yrange=[None, None]
        dataset.is_matrix_data=True
        window.replot()
      # The mouse can be used to get center positions, tilt and screen size 
      specular=MouseReader('Select the specular reflection', window).run()
      #x, y, z=dataset.data[0:3]
      #fit=FitGaussian3D([50., specular[0], specular[1], 5., 5., 0., 10.])
      #region=where((x>=(specular[0]-30))&(x<=(specular[0]+30))&\
      #             (y>=(specular[1]-30))&(y<=(specular[1]+30)))
      #fit.refine(x[region], y[region], z[region])
      #specular=fit.parameters[1:3]
      specdiv=(specular[0]-RHEED_CENTER_X, specular[1]-RHEED_CENTER_Y)
      specdist=sqrt(specdiv[0]**2+specdiv[1]**2)
      speccenter=(specular[0]-specdiv[0]/2., specular[1]-specdiv[1]/2.)
      divnorm=(specdiv[0]/specdist, specdiv[1]/specdist)

      old_freeinput=dataset.plot_options.free_input
      dataset.plot_options.free_input=[
             'set label "Specular" at %f, %f point front'%tuple(specular),
             'set label "Horizon" at %f, %f front center'%(speccenter[0]+divnorm[1]*55,
                                                    speccenter[1]-divnorm[0]*55),
             'set arrow from %f,%f to %f,%f nohead front'%(speccenter[0]-divnorm[1]*50,
                                                           speccenter[1]+divnorm[0]*50,
                                                           speccenter[0]+divnorm[1]*50,
                                                           speccenter[1]-divnorm[0]*50
                                                           )
                                       ]
      window.replot()
      dataset.plot_options.free_input=old_freeinput

    else:
      specular=(400., 400.)
    dialog=SimpleEntryDialog('RHEED parameters:',
                             [
                              ('Energy [eV]', 10000., float),
                              ('Specular x [pix]', specular[0], float),
                              ('Specular y [pix]', specular[1], float),
                              ]
                             )
    parameters, result=dialog.run()
    dialog.destroy()
    if result:
      dataset=window.active_dataset
      x=dataset.data[0].view(ndarray)
      y=dataset.data[1].view(ndarray)
      specular=(parameters['Specular x [pix]'], parameters['Specular y [pix]'])
      # difference between specular position and zero position
      specdiv=(specular[0]-RHEED_CENTER_X, specular[1]-RHEED_CENTER_Y)
      specdist=sqrt(specdiv[0]**2+specdiv[1]**2)
      speccenter=(specular[0]-specdiv[0]/2., specular[1]-specdiv[1]/2.)
      divnorm=(specdiv[0]/specdist, specdiv[1]/specdist)
      pixel_size=RHEED_SCREEN_SIZE/RHEED_SCREEN_PIXELS
      alpha_i=arctan(specdist/2.*pixel_size/RHEED_DISTANCE)
      alpha_f=arctan((((x-speccenter[0])*divnorm[0])+\
                            ((y-speccenter[1])*divnorm[1]))*\
                      pixel_size/RHEED_DISTANCE)
      phi=arctan((((x-speccenter[0])*divnorm[1])-\
                            ((y-speccenter[1])*divnorm[0]))*\
                      pixel_size/RHEED_DISTANCE)



      lamda=H_over_2m/sqrt(parameters['Energy [eV]'])
      qx_array=2.*pi/lamda*(cos(alpha_f)*cos(phi)-cos(alpha_i))
      qy_array=2.*pi/lamda*(sin(phi)*cos(alpha_f))
      qx_array[alpha_f>=0.]*=-1

      if len(dataset.data)==3:
        dataset.data.append(PhysicalProperty('Q_x', 'Å^{-1}', qx_array))
        dataset.data.append(PhysicalProperty('Q_y', 'Å^{-1}', qy_array))
      else:
        dataset.data[3]=PhysicalProperty('Q_x', 'Å^{-1}', qx_array)
        dataset.data[4]=PhysicalProperty('Q_y', 'Å^{-1}', qy_array)
      dataset.is_matrix_data=False
      dataset.xdata=4
      dataset.ydata=3
      dataset.plot_options.xrange=[None, None]
      dataset.plot_options.yrange=[None, None]
      window.rebuild_menus()
      window.replot()

