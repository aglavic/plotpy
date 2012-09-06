#-*- coding: utf8 -*-
'''
  Testing the datatype framewok.
'''

from plotpy.mds import PhysicalProperty
from numpy import array, ndarray, arange, float32, sqrt, zeros_like, ones_like, pi, sin
import unittest

class TestPhysicalProperty(unittest.TestCase):
  '''
    Check the behavior of the base data holding array type.
  '''

  def setUp(self):
    self.error=array([2. for ignore in range(100)], dtype=float32)
    self.values=arange(1., 101., 1.0, dtype=float32)
    self.data=PhysicalProperty('x', '°', self.values, self.error)

  def test_add(self):
    # test the base calculations with addition
    add_res=self.data+self.data
    self.assertEqual(add_res.view(ndarray).tolist(),
                      (2.*self.values).tolist(),
                     "Add results")
    self.assertEqual(add_res.error.tolist(),
                     (sqrt(2.)*self.error).tolist(),
                     "Add errors")

  def test_sub(self):
    # test the base calculations with subtraction
    sub_res=self.data-self.data
    self.assertEqual(sub_res.view(ndarray).tolist(),
                     (zeros_like(self.values)).tolist(),
                     "Subtract results")
    self.assertEqual(sub_res.error.tolist(),
                     (sqrt(2.)*self.error).tolist(),
                     "Subtract errors")

  def test_mul(self):
    # test the base calculations with multiplication
    mul_res=self.data*self.data
    self.assertEqual(mul_res.view(ndarray).tolist(),
                     (self.values**2).tolist(),
                     "Multiply results")
    self.assertEqual(mul_res.error.tolist(),
                     (sqrt((self.error*self.values)**2+
                           (self.error*self.values)**2)).tolist(),
                     "Multiply errors")

  def test_div(self):
    # test the base calculations with division
    div_res=self.data/self.data
    self.assertEqual(div_res.view(ndarray).tolist(),
                     (ones_like(self.values)).tolist(),
                     "Devision results")
    self.assertEqual(div_res.error.tolist(),
                     (sqrt((self.error/self.values)**2+
                           (self.error/self.values)**2)).tolist(),
                     "Devision errors")

  def test_unit_conversions(self):
    # test automatic and manual unit conversion
    deg=self.data
    rad=deg%'rad'
    self.assertEqual(rad.unit, 'rad',
                     "Unit conversion from ° to rad - Unit")
    self.assertEqual((deg*(pi/180.)).tolist(),
                     rad.tolist(),
                     "Unit conversion from ° to rad - Value")
    # automatic conversion when added
    degrad=deg+rad
    self.assertEqual(degrad.tolist(), (2.*deg).tolist(),
                     "Unit auto conversion in addition")
    # automatic conversion for angle functions
    degsin=sin(deg)
    radsin=sin(rad)
    self.assertEqual(degsin.tolist(), radsin.tolist(),
                     "Unit auto conversion in sin(x)")


class TestBla(unittest.TestCase):
  pass

if __name__=='__main__':
  #unittest.main()
  loader=unittest.TestLoader()
  suite=loader.loadTestsFromTestCase(TestPhysicalProperty)
  suite.addTest(loader.loadTestsFromTestCase(TestBla))
  unittest.TextTestRunner(verbosity=2).run(suite)
