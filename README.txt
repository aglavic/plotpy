      Release Notes for the plotting script collection Version 0.7.2
             Please report bugs and feature requests to http://iffwww.iff.kfa-juelich.de/~glavic/plotwiki


Content:

0   - introduction
1    - changes since version 0.7
1.1 - changes from version 0.6.3 to 0.7
1.2 - changes from version 0.5 to 0.6.3
1.3 - changes from version 0.4 to 0.5
2   - installation Linux
2.1 - installation Windows
3   - goles for later releases

----------- 0 - introduction --------------
This is the fourth release of scripts for plotting mpms/ppms, 4Circle, reflectometer, treff, dns and some more file formats.
The main goal of this project is to create one framework for common data evaluation of a bunch of instuments
so that common tasks are automated and the user saves a lot of time. Many people use gnuplot and with this
program you can create nice gnuplot graphs quite fast and change the gnuplot script after exporting it.
For a description of the features see chapter 3. 
Version 0.7 is a huge step in functionality and usability. A lot of new features have been implemented and the old ones
have been polished. The basic data structure has been reworked to be much faster and advanced.
This version also introduces an ineractive ipython console, which can be used to run own scripts to interfere with the program
interactively or to perform operations on the data. (For this purpose the new PhysicalProperty class which is used to store
the data internally can be quite helpful.)

The following list of changes does not claim to be complete:

----- 1    - changes since version 0.7 -----
- Support for 4-ID-C datatype of APS
- Added templates support in GUI, user can define an ASCII file format with a simple template file.
- Added experimental mouse support for mapplots under Linux.
- Completed the "PlotTree" Dilaog, which shows a list of all plots including preview.
- Improved GUI useablinity with e.g. important dialogs reappear at their last used position
- IPython console improvements:
  - Script lines can be automatically run at startup using the "-ipy" and "-ipr" command line parameters
  - Keyboard shortcuts get redirected to the main window, e.g. <control>+N changes to the next plot
  - Important mathematic functions as 'exp' and 'sin' are directly added to the namespace without using the np. prefix.
  - 'ls' and 'cat' functions now use python functions as the result had not been shown in the program but the Unix console.
  - GUI Menu functions are directly aveilable via the new 'menus' object.
- Fix a bug making plotting impossible with Gnuplot versions <4.4
- Fix small bug which could raise an error on unix systems where it should have been cought (WindowsError not defined)

----- 1.1 - changes from version 0.6.3 to 0.7 -------
- For gnuplot version >=4.4 mouse support was added for 2d plots including position status message, 
  zoom functionality, adding labels on shift+click and fitting peak functions on ctrl+click.
- Added template framework to fast create new datatypes.
- Added MARIA, D7, general SPEC and IN17 datatype.
- Added possibilty to derivate data using a moving window (Savitzky-Golay filter) or global (FFT) approach.
- Added rebinning and smoothing options for 3d (map) data.
- Added fit for 3d (map) datasets.
- Added color selection dialog showing the available color scales.
- Added some new fit functions.
- Added FFT analysis of reflectivity measurements.
- Export, apply options and print multple datasets together, which can be selected with previews.
- Added a DataView dialog to show the data of the active plot in a table.
- Possibility to update the program from a website (updatescript itself needs to be written, but will be downloaded
  automatically)
- Updated Polarized Neutron Reflectivity fit program from Emmanuel Kentzinger
- Rework the data output leading to a speedup in plotting of 70-95%.
- Rework of the MeasurementData and PhysicalProperty objects which store the data, now the columns storing data are
  derived from the numpy.ndarray object, which make calculations a lot faster and gives the possiblity to use them with
  numpy universal functions.
- Added program icons in the system menu and file type assignment (Windows/Debian package)
- Fix rescaling the program window
- Fix some unicode issues
- Improved error handling and debug.log
- A lot of bugfixes.

----- 1.2 - changes from version 0.5 to 0.6.3 -------
- added printing with system print dialog (pygtk >= 2.10) or with commandline tool for unix
- added Radial integration around one point of a plotted maps
- added some convenience functions to the IPython console to give experienced users the possibility to 
   treat the data with own functions
- added possibilty to use gzip compressed files for most of the session types
- added reflectometer option to combine multiple scans into one map (rocking curves)
- added possibility to open the GUI without datafile so it can be run from the menu (.deb and windows
   automatically adds menu entries)
- added a button to show the plot in an external gnuplot (wxt/windows) window, this gives the possibility to
  zomm in with the mouse, find the exact position of a point and have multiple plots opened at the same time
- added possibility to select the picture size in the export dialog
- fix export and open dialogs now stay in the last used folder
- fix multiplot did not have it's own title
- fix first title entry will lose changes when entering into second title entry at the same time
- fix IPython did not work on all systems, especially windows
- fix Postscript export with wrong symbols
- fix integrate intensities of only one dataset
- a lot of small fixes for the usability
- added snapshot framework to store the working stat including fits etc.
- added possiblity to combine reflectometer rocking curves to 3d maps
- added gui option to change squid dia- and paramagnetic correction including fit to asymptotic behaviour
- added function to integrate intensities of differen datasets
- fix TREFF and reflectometer fits with different datasets not working in one session
- fix reflectometer custom constrints not working whith multilayer parameters
- revisited scattering length density table of reflectometer
- filtering datapoints can be applied without closing the dialog
- fix crash when trying to import improper squid/ppms data files
- fix DNS crashes when -xyz option is evoked and not all sequences have 6 channels
- better DNS correction posibilities
- reload config files and .mds files when a new script version is created
- some minor changes an fixes
- rearanged menu structure to improve usability
- added new Plot.py logo to the gui
- improved the scaling of the GUI image
- added a import status dialog when starting the progran, 
  that can be viewed from the GUI after import.
- added KWS2 datatype
- added Lambda setting in dns config
- PPMS split AC measurements by frequency
- added x-ray ka1, ka2 fit function
- added 4circle reload a measurement and toggle cps
- added iPython console window for interactive python access to the program variables
- using unicode source files
- fixed covariance is None issue in fit routine
- fixed DeprecationWarnig using gtk.Tooltips in plotting_gui.py
- fixed Time out when update server is not reachable
- fixed Import in reflectometer doesn't need leeding spaces
- fixed DNS reimplement a column with the file numbers
- fixed small issue in DNS fullauto import optional
- some minor fixes and changes
- added support for treff data and image files
  - create intensity maps from the detector data, join scans
  - extract "true" specular reflectivity from those maps
  - fit the specular reflectivity with the pnr_multi.f90 program from E. Kentzinger
  - import structure information for fit from x-ray .ent file
- added support for in12 data files
- added support for DNS single crystal and powder data with additional functionality:
  - fullauto mode for fast data analysis
  - transform to q-space, with variable omega-offset
  - correct for vanadium and background file
  - correct for flipping ratio
  - split file sequences by number of polarizations
  - transform to reciprocal lattice units with given d-spacing
  - Linear combination and multiplicatoin of different measurements for separation
- changed module structure introducing config, read_data and sessions packages
- added fitting dialog for common functions
- optional platform independent python setup and Linux RPM+.deb packages
- Windows binary build using py2exe
- save gnuplot and datafile which creates the same image as present in GUI for later change
- major speed enhacement for plotting and data import, slow import formats (as squid raw
   and treff image files) are stored as binary objects after readout
- included fonts for linux distributions missing it, long folder name problem has been solved
- history for reflectometer/treff fit parameters
- custom constraints in reflectometer/treff fit
- relfectometer and treff fit dialog shows number of iterations and chi while fit is running
- code cleanup and consistancy
- multiplot from different files (stil needs imporvement)
- automatic session detection from file postfix
- color selection for 3d plots (can be personalized in config/gnuplot_preferences.py)
- create arbitrary cross-sections through 3d-plots bin the data as standard and gaussian weighted mean, 
  join datapoints with equal numbers or in equal steps
- transform units and dimensions with some predefined units (e.g. 째 to mrad)
- plot profiles now include all 3d-plot settings, too
- better window resize using scrolled window and gnuplot with different export sizes and not scaling
- font size option in GUI
- first stages of macro framework to make it easier to repeat common tasks on differen measurments,
  at the moment not intuitive and only implemented for some of the tasks (e.g. fit and cross-section)
  see Help-> Action History to find tasks used in the active session
- automatically check online for new updates
- dialog to export information when encountering an error
- config files in user directory if installed by admin


----- 1.3 - changes from version 0.4 to 0.5 -------
- combined all scripts into one executable with many changes in the backend for more
  flexibility using more object orientation
- using temporal folder depending on the process ID so you can use more then one instance
  of the script without interfering with an other.
- now running under Windows
- many bugs fixed in scripts and gui
- improvements of the GUI, e.g. open files from within the GUI, add any gnuplot command
  and save gnuplot settings in profiles
- some code cleanup and comments
- module insertion into GUI dependent on the run script
- including and excluding filtering of the datasets by any column
- interactive reflectometer fitting, using the fit.f90 back end by E. Kentzinger (modified)
- a lot more of minor improvements


----------- 2 - installation (Linux) --------------
See http://iffwww.iff.kfa-juelich.de/~glavic/plotwiki for more information

!!!On Debian systems I recommand to use the debian package available via the wiki download page.!!!

plotting-scripts:
1. Extract Plot-script-{VERSION}.tar.gz to any destination folder:

  tar -xvvzf Plot-script-{VERSION}.tar.gz

  You now have two options, link the script to your bin-directory and run it from this folder or install it as python module(recomanded):

2a- Link the script using the install shell script:
  In the folder type:
    ./install
  
  this creates symbolic links for plot.py, plot_4circle_data, plot_reflectometer_data, 
  plot_SQUID_data (scripts) and p4d,prd,pld (gui mode) in /usr/bin .
  !! if you don't have administrator priviliges, use ./install {PATH} , with a directory {PATH}
     inside one of your system path folders. (type "print $PATH" to find out where to look)

  To remove the script is just as easy, go to the installation folder and type
    ./uninstall
  this will remove the symbolic links. If you installed to another path, use uninstall with
  the same parameters as the install script earlier.

  !!! If you have the previous version installed, you have !!!
  !!! to uninstall it first, as the links have changed.    !!!
  For full functionality you will need the gfortran compiler(fit.f90), gnuplot.py(speedup) and pygtk(GUI) packages.


2b- Run the installtion with python:

  python setup.py install
  
  this creates scripts to run the program
  ! if you don't have administrator priviliges, use 
      python setup.py install --prefix {Inst.Dir} --install-scripts {folder in your path}
      inside one of your system path folders. (type "print $PATH" to find out where to look)

  For full functionality you will need the gfortran compiler(fit.f90), numpy, scipy and pygtk(GUI) packages.

----------- 2.1 - installation (Windows) --------------
As installation from source is quite complicated on windows I skip to provide this information here.

!!! I recommand to use the package installer available on the wiki download page. !!!!

If you still want to try installing from source please reffer to the wiki page for more information.

------- 3 - goals for later releases -------
The next releases will hopefully come in about 3-6 month cycles. 
At the moment I have these plans for the future releases:
!!! Please give me feedback, thats the only way for me to find errors 
     arising from differnt input options/operating systems !!!

  v0.8) 
        - replace the multiplot functionality by a plot dialog which is easier to use and has
          additional functionality as to plot more than one column of a file, still no idea how
        - save more settings in the config file, savable window profiles, more user control on the
          GUI behaviour
        - combine data from different files together (for all file types)
        - increase console functionality
        - increase stability of the new data types and the gui functions
        - review dialogs and old evaluation functions for errors.
        - add convenience functions like fitting of multiple peaks at once or fit of multiple datasets

  v0.8) 
        ? include powder diffractometer format and interface to fullprof ?
        - complete mpms and ppms functionalities for all measurement types
        - complete reflectometer functionalities (don't know what I will do there yet,
          perhaps you have any further ideas?)
        - complete 4circle functionality (don't know that either, perhaps a remote control
          interface for the 4circle for real time measurements with the GUI)
  
  v0.9)
        - Easier, plug in like datatype interface to make development of for others easier.

  v1.0) 
        - get rid of most of the bugs
        - increase usability of the interface (please tell me what is confusing or complicated to use)
        - perhaps making it conform to the GNU license for publication
        - more automated data evaluation functions for the measurement types

Don't expect to much, this is just a loose schedule.
