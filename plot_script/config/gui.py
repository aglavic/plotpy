'''
  Configurations for the GUI frontend.
  Mostly used for the global parameter 'toolkit' which is a string
  defining the prefix for the gui package, e.g. 'gtk' for using the
  gtkgui package.
  
  At the moment the gtk version is much more mature and feature rich 
  so it is recommanded to use this if possible.
'''

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Development"

#toolkit='wx'
toolkit='gtk'

DOWNLOAD_PAGE_URL='http://iffwww.iff.kfa-juelich.de/~glavic/plotupdate.py'

ICONS={
               'Apply': 'apply.png',
               'ErrorBars': 'errorbars.png',
               'ToggleMousemode': 'mousemode.png',
               'ExportAll': 'exportselection.png',
               'ExportAs': 'export.png',
               'Export': 'export.png',
               'AddMultiplot': 'multiplotadd.png',
               'Multiplot': 'multiplot.png',
               'SnapshotSub': 'snapshot.png',
               'SaveSnapshot': 'snapshotsave.png',
               'SaveSnapshotAs': 'snapshotsave.png',
               'LoadSnapshot': 'snapshotload.png',
               'LoadSnapshotFrom': 'snapshotload.png',
               'PlotKeyLeft': 'keytopleft.png',
               'PlotKeyRight': 'keytopright.png',
               'PlotKeyBottomLeft': 'keybottomleft.png',
               'PlotKeyBottomRight': 'keybottomright.png',
               'PlotToggleGrid': 'grid.png',
               'PlotToggleLinespoints': 'linespoints.png',
               'ShowPersistent': 'plotexternal.png',
               'XYProjections': 'togglexyprojection.png',

               }
ICON_SIZE=24