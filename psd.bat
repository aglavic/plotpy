@echo off
PATH=%PATH%;C:\python26;C:\plotting-script;C:\plotting-script\gnuplot\bin;C:\Program Files\gfortran\bin;C:\Programme\gfortran\bin
python C:\plotting-script\plot.py squid -gs %*
