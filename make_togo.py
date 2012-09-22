'''
  Create a two file executable with a plotpy zip archive and startup script.
'''
import os
from zipfile import ZipFile, ZIP_DEFLATED
from glob import glob
from subprocess import call

call(['python', '-O', '-m', 'compileall', 'plotpy'])
call(['cp', 'plotpy_togo.py', 'dist/to_go/plot.py'])
call(['chmod', 'a+x', 'dist/to_go/plot.py'])

z=ZipFile('/home/glavic/plotting/dist/to_go/plotpy.zip', 'w', ZIP_DEFLATED)


def rec_find_pyc(folder):
  output=glob(os.path.join(folder, '*.pyo'))+glob(os.path.join(folder, '*.py'))
  for item in glob(os.path.join(folder, '*')):
    if os.path.isdir(item):
      output+=rec_find_pyc(item)
  return output
files=rec_find_pyc('plotpy')
icons=glob('plotpy/gtkgui/icons/*')
for filename in files+icons:
  print filename
  z.write(filename, filename)
z.close()
