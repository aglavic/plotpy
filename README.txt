      Release Notes for the plotting script collection Version 0.6
             Please report bugs to a.glavic@fz-juelich.de


Content:

0   - introduction
1   - changes since version 0.5
1.1   - changes from version 0.4 to 0.5
2   - installation Linux
2.1 - installation Windows
3   - list of modules and packages
4   - description of scripts
5   - goles for later releases

----------- 0 - introduction --------------
This is the third release of scripts for plotting mpms/ppms, 4Circle, reflectometer, treff and in12 data,
For a description of the features see chapter 3. 
If you would like some new features, found any bugs or would like to have additional file-types
supported by the script feel free to contact me.

----- 1 - changes since version 0.5 -------
- added support for treff data and image files
- added support for in12 data files
- changed module structure introducing config, read_data and sessions packages
- added fitting dialog
- platform independent python setup
- save gnuplot and datafile which creates the same image as present in GUI
- major speed enhacement for plottin and data import, slow import formats (as squid raw
   and treff image files) are stored as binary objects after readout
- included fonts for linux distributions missing it
- history for reflectometer fit
- code cleanup and consistancy
- multiplot from different files (stil needs imporvement)


----- 1.1 - changes from version 0.4 to 0.5 -------
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
plotting-scripts:
1. Extract Plot-script-{VERSION}.tar.gz to any destination folder:

  tar -xvvzf Plot-script-{VERSION}.tar.gz

  You now have to options, link the script to your bin-directory and run it from this folder or install it as python module:

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
  
  this creates symbolic links for plot.py, plot_4circle_data, plot_reflectometer_data, 
  plot_SQUID_data (scripts) and p4d,prd,pld (gui mode) in /usr/bin .
  !! if you don't have administrator priviliges, use ./install {PATH} , with a directory {PATH}
     inside one of your system path folders. (type "print $PATH" to find out where to look)

!!! If you have the previous version installed, you have !!!
!!! to uninstall it first, as the links have changed.    !!!

For full functionality you will need the gfortran compiler(fit.f90), gnuplot.py(speedup), numpy, scipy and pygtk(GUI) packages.

----------- 2.1 - installation --------------
Installation in Windows is not that easy, first of all because gnuplot is not as common 
   as it is in Linux and especially because the GUI is programed using GTK+ with pygtk. 
   The installation of pygtk is quite extensive, but not so complicated. If you want to
   use my installation batch go to b).

a)I am trying to make it easy with a step by step procedure:

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
    - i had to reboot after that to get the installation to work

- put the installation folders of python and gnuplot into your path ( found in the environment variables
  in window advanced system settings which opens when you press windows+pause)

- extract the *.zip file, and run:

  python setup.py install

b) Everything described above is also done by my installation batch file I provide together with all
   packages need. You can download it from http://atzes.homeip.net/plotting .
   Start the self extractor and extract all files to a temporal directory. Start install.bat, this should
   install all the packages.

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
  
  configobj.py                                           - class for storing of variables in .ini files, from external source

  config/fit/fit.f90                                        - actual program



------- 4 - description of scripts -------
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
The next releases will hopefully come in about 2 month cycles. 
At the moment I have these plans for the future releases:

  v0.7) - setting up proper printing dialog
        - color selection for 3d plots
        - more error handling
        - save more settings in the config file, savable window profiles

  v0.8) - include powder diffractometer format and interface to fullprof
        - complete mpms and ppms functionalities for all measurements
        - complete reflectometer functionalities (don't know what I will do there yet,
          perhaps you have any further ideas?)

  v0.9) - complete 4circle functionality (don't know that either, perhaps a remote control
          interface for the 4circle for real time measurements with the GUI)

  v1.0) - get rid of most of the bugs
        - increase usability (please tell me what is confusing or complicated to use
        - perhaps making it conform to the GNU license for publication
        - add additional file formats (any ideas welcome), perhaps combine it with
          my DNS data evaluation script
        - more automated data evaluation functions for the measurement types

Don't expect to much, this is just a loose schedule.
