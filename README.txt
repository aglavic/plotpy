      Release Notes for the plotting script collection Version 0.6.2
             Please report bugs and feature requests to http://atzes.homeip.net/plotwiki/tiki-forums.php


Content:

0   - introduction
1   - changes since version 0.6
1.1 - changes from version 0.5 to 0.6
1.2 - changes from version 0.4 to 0.5
2   - installation Linux
2.1 - installation Windows
3   - list of modules and packages
4   - description of scripts
5   - goles for later releases

----------- 0 - introduction --------------
This is the third release of scripts for plotting mpms/ppms, 4Circle, reflectometer, treff, dns and in12 data.
The main goal of this project is to create one framework for common data evaluation of a bunch of instuments
so that common tasks are automated and the user saves a lot of time. Many people use gnuplot and with this
program you can create nice gnuplot graphs quite fast and change the gnuplot script after exporting it.
For a description of the features see chapter 3. 
If you would like some new features, found any bugs or would like to have additional file-types
supported by the script feel free to go to the Wiki http://atzes.homeip.net/plotwiki/ . Any contribution
to the Wiki content is also welcome.

----- 1 - changes since version 0.6 -------
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

----- 1.1 - changes from version 0.5 to 0.6 -------
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
- transform units and dimensions with some predefined units (e.g. ° to mrad)
- plot profiles now include all 3d-plot settings, too
- better window resize using scrolled window and gnuplot with different export sizes and not scaling
- font size option in GUI
- first stages of macro framework to make it easier to repeat common tasks on differen measurments,
  at the moment not intuitive and only implemented for some of the tasks (e.g. fit and cross-section)
  see Help-> Action History to find tasks used in the active session
- automatically check online for new updates
- dialog to export information when encountering an error
- config files in user directory if installed by admin


----- 1.2 - changes from version 0.4 to 0.5 -------
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


----------- 2 - installation --------------
See http://atzes.homeip.net/plotwiki for more information

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

  !!! If you have the previous version installed, you have to uninstall it first, as the links have changed.  !!!

  For full functionality you will need the gfortran compiler(fit.f90), gnuplot.py(speedup), numpy, scipy and pygtk(GUI) packages.

----------- 2.1 - installation --------------
You can install the complete binary package found in the wiki, but this is not always up to date
  and could be a bit unstable, instead you can also install the software together with a python environment,
  but that is not that easy, first of all because gnuplot is not as common 
   as it is in Linux and especially because the GUI is programed using GTK+ with pygtk. 
   The installation of pygtk is quite extensive, but not so complicated. 

I am trying to make it easy with a step by step procedure:

- get the needed installers for python, gnuplot and pygtk:
    - gnuplot win32 version can be found at http://www.gnuplot.info/download.html
    - for python get version 2.5.x or 2.6.x from http://www.python.org/download/releases/
      (3.x versions have not been tested)
    - from http://pygtk.org/downloads.html download
      -PyCairo
      -PyGObject
      -PyGTK
      -follow the Link to GTK+ and download the developer environment ( a file called
                something like gtk-dev-2.12.9-win32-2.exe )
      -be sure to get the right version fitting for the python version you downloaded.
    - gfortran from http://gcc.gnu.org/wiki/GFortranBinaries ("native Windows")
    - for the installers to work i had also to download MSVCR71.dll from the Internet in Vista
- install the environment:
    - install gnuplot,python and GTK
    - install pycairo,pygobject and pygtk
    - add the gnuplot, python, gfortran and python/scripts folders to your systems path
      ( found in the environment variables
        in window advanced system settings which opens when you press windows+pause)
    - i had to reboot after that to get the installation to work

- extract the *.zip file, and run   "python setup.py install" or just use the windows installer


Now you should be ready to use the scripts with and without GUI-mode under windows. 
  Building an exe file with py2exe resulted in major problems with pygtk so I won't provide it in the near future.


---------- 3 - list of modules and packages -------------
Plot-script-0.6.tar.gz (.zip) contains:
  config/                                                         - package with all settings for the datafile import and plot layout
                                                                        to change these can make sense also for users
  read_data/                                                   - contains all modules for datafile readout
  sessions/                                                     - interfaces between plot script and data readout/treatment
  
  measurement_data_plotting.py                 - plotting functions
  measurement_data_structure.py               - data structure classes
  plot.py                                                      - executable script, mostly just module imports
  plotting_gui.py                                          - class for the gui
  file_actions                                               - functions for the new macro functionality
  
  configobj.py                                           - class for storing of variables in .ini files, from external source

  config/fit/                                                  - fortran programs for reflectivity simulations



------- 4 - description of scripts -------
I don't have time to rewrite this list. Just try it...

Commom:
  All sessions (with and without gui) have some common features:
    - the session type can be given as the first parameter
    - Typing the script name followed by '--help' option will show the command line parameters
    - Every script excepts input file names as command line parameters in any order and with
      wild cards too
    - The Scripts try to split the input files into measured sequences, in most cases due to
      settings in the ..._preferences.py files
    - The sequences can be plotted in one plot command line option
    - Use Linux command line tool to send all plots to a printer

4circle:
  - The script will additionally calculate the counts/s value and error bars.

Reflectometer:
  - The script will additionally calculate the counts/s value and error bars.
  - It can export entrance files for fit.f90 program and refine some parameters automatically
    by calling the program with different parameters
  - You can use the GUI to refine all parameters including multilayer functionality

SQUID:
  - Units are converted to SI by settings in SQUID_preferences
  - can make dia-/paramagnetic correction with parameters from the command line

GUI:
  - Same functionalities as script with additional control over some plotting parameters
  - Free possibilities to combine different plots
  - Change title info of specific Plot
  - Interactive change of plotted Column mostly useful in SQUID script
  - Change and show all gnuplot parameters and store it as profile

------- 5 - goals for later releases -------
The next releases will hopefully come in about 3-6 month cycles. 
At the moment I have these plans for the future releases:

  v0.7)  - convert the program to the wxWidgets backend to make the program
              accessible under OSX, too.
        - replace the multiplot functionality by a plot dialog which is easier to use and has
          additional functionality as to plot more than one column of a file
        - revisite the datastructure, perhaps link the errors to the data
        - make numpy a prerequisite and use only numpy arrays for speedup
        - setting up proper printing dialog
        - more error handling
        - save more settings in the config file, savable window profiles
        - open the gui without any file
        - combine data from different files together
        - increase command line functionality
        - Save working status for easier reaccess e.g. for Treff fit sessions.

  v0.8) - include powder diffractometer format and interface to fullprof
        - complete mpms and ppms functionalities for all measurements
        - complete reflectometer functionalities (don't know what I will do there yet,
          perhaps you have any further ideas?)

  v0.9) - complete 4circle functionality (don't know that either, perhaps a remote control
          interface for the 4circle for real time measurements with the GUI)

  v1.0) - get rid of most of the bugs
        - increase usability (please tell me what is confusing or complicated to use
        - perhaps making it conform to the GNU license for publication
        - more automated data evaluation functions for the measurement types

Don't expect to much, this is just a loose schedule.