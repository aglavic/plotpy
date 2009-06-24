@echo off
echo "Install the script."
md c:\plotting-script
echo "Please extract the script files into the directory."
explorer c:\plotting-script
pause

echo "Install Gnuplot."
md c:\plotting-script\gnuplot
echo "Please extract gnuplot into the directory."
explorer c:\plotting-script\gnuplot
pause

echo "Install GTK."
gtk-2.12.9-win32-2.exe
echo "Install python."
python-2.6.1.msi
echo "Please put the gtk,python and script folder into the path now."
PATH=%PATH%;c:\gtk;c:\plotting-script;c:\python26;"c:\program files\gtk";"c:\programme\gtk"
pause
echo "Install pygtk."
pycairo-1.4.12-2.win32-py2.6.exe
pygobject-2.14.2-2.win32-py2.6.exe
pygtk-2.12.1-3.win32-py2.6.exe
echo "Install numpy+scipy."
numpy-1.3.0-win32-superpack-python2.6.exe
scipy-0.7.1rc3-win32-superpack-python2.6.exe

echo "Install gfortran."
gfortran-windows.exe
PATH=%PATH%;"c:\program files\gfortran";"c:\programme\gfortran"
