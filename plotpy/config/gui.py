'''
  Configurations for the GUI frontend.
'''

import os

config_file='gui'

DOWNLOAD_PAGE_URL='http://plotpy.sourceforge.net/plotupdate.py'

show_toolbars=[0, 1]
show_statusbar=True
seperate_view=False

# locate icons
own_path=os.path.dirname(os.path.abspath(__file__))
if '.zip' in own_path:
  from zipfile import ZipFile
  import tempfile
  z=ZipFile(own_path.split('.zip')[0]+'.zip')
  tmp_folder=os.path.join(tempfile.gettempdir(), 'plotpy_gui')
  if not os.path.exists(tmp_folder):
    os.mkdir(tmp_folder)
    names=z.namelist()
    names=filter(lambda item: item.startswith('plotpy/gtkgui/icons'), names)
    z.extractall(tmp_folder, members=names)
  ICON_PATH=os.path.join(tmp_folder, 'plotpy', 'gtkgui', 'icons')
else:
  ICON_PATH=os.path.join(os.path.split(own_path)[0], 'gtkgui', 'icons')
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
               'Logo': 'logo.png',
               'LogoP': 'logopurple.png',
               'LogoG': 'logogreen.png',
               'LogoB': 'logoblue.png',
               'LogoY': 'logoyellow.png',

               }
ICON_SIZE=24
for key, value in ICONS.items():
  ICONS[key]=os.path.join(ICON_PATH, value)
del(key)
del(value)
