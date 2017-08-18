# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from nose.tools import *
import {TargetReference} from './buildgraph'


def test_TargetReference_from_string():
  with assert_raises(ValueError):
    TargetReference.from_string('hello')
  with assert_raises(ValueError):
    TargetReference.from_string('//scopename')
  with assert_raises(ValueError):
    TargetReference.from_string('scopename:hello')
  assert TargetReference.from_string(':hello') == \
    TargetReference(None, 'hello')
  assert TargetReference.from_string('//scopename:hello') == \
    TargetReference('scopename', 'hello')


def test_TargetReference___str__():
  assert_equals(str(TargetReference(None, 'hello')), ':hello')
  assert_equals(str(TargetReference('scopename', 'hello')), '//scopename:hello')
  with assert_raises(TypeError):
    TargetReference('scopename', None)
  with assert_raises(ValueError):
    TargetReference('scopename', '')
  with assert_raises(ValueError):
    TargetReference('', 'hello')
  with assert_raises(ValueError):
    TargetReference('', '')
  with assert_raises(TypeError):
    TargetReference(None, None)
