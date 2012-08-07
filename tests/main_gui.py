#-*- coding: utf8 -*-
'''
  Testing the main window.
'''

import unittest
import os
import sys
import gtk
from plot_script.sessions.circle import CircleSession
from plot_script.gtkgui.main_window import ApplicationMainWindow

class TestMainWindow(unittest.TestCase):
  '''
    Check the behavior of the base data holding array type.
  '''

  @classmethod
  def setUpClass(self):
    self.session=CircleSession(['/home/glavic/inplan_2plane_radial_scans.spec'])
    self.gui=ApplicationMainWindow(self.session)

  @classmethod
  def tearDownClass(self):
    self.gui.main_quit()
    while gtk.events_pending():
      gtk.main_iteration_do(block=False)

  def setUp(self):
    while gtk.events_pending():
      gtk.main_iteration_do(block=False)

  def tearDown(self):
    while gtk.events_pending():
      gtk.main_iteration_do(block=False)

  def test_1show(self):
    self.assertTrue(self.gui.get_visible(), 'GUI is not shown')
    self.assertEqual(self.session, self.gui.active_session, 'Session not associated')

  def test_2image_created(self):
    image_file=self.session.TEMP_DIR+'plot_temp.png'
    self.assertTrue(os.path.exists(image_file), 'Plot image not created')

  def test_3persistent(self):
    self.gui.plot_persistent()

  def test_4ipython(self):
    self.gui.open_ipy_console()
    self.assertNotEqual(False, getattr(self.gui, 'active_ipython', False),
                        'IPythonView not created')

  def test_5ipython_close(self):
    self.gui.active_ipython.destroy()
    self.assertNotEqual(False, getattr(self.gui, 'ipython_user_namespace', False),
                        'Namspace not saved')
    self.assertNotEqual(False, getattr(self.gui, 'ipython_user_history', False),
                        'History not saved')

  def test_6opow(self):
    self.gui.open_plot_options_window(None)

  def test_7cpow(self):
    self.gui.open_plot_options_window(None)

  def test_8slpp(self):
    self.gui.show_last_plot_params(None)


if __name__=='__main__':
  #unittest.main()
  loader=unittest.TestLoader()
  suite=loader.loadTestsFromTestCase(TestMainWindow)
  unittest.TextTestRunner(verbosity=2).run(suite)
