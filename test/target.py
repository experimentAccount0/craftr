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
import {TargetRef, Target} from '../core/target'


def test_TargetRef_from_str():
  with assert_raises(ValueError):
    TargetRef.from_str('hello')
  with assert_raises(ValueError):
    TargetRef.from_str('//scopename')
  with assert_raises(ValueError):
    TargetRef.from_str('scopename:hello')
  assert_equals(TargetRef.from_str(':hello'),
    TargetRef(None, 'hello'))
  assert_equals(TargetRef.from_str('//scopename:hello'),
    TargetRef('scopename', 'hello'))


def test_TargetRef___str__():
  assert_equals(str(TargetRef(None, 'hello')), ':hello')
  assert_equals(str(TargetRef('scopename', 'hello')), '//scopename:hello')


def test_TargetRef___init__():
  with assert_raises(TypeError):
    TargetRef('scopename', None)
  with assert_raises(ValueError):
    TargetRef('scopename', '')
  with assert_raises(ValueError):
    TargetRef('', 'hello')
  with assert_raises(ValueError):
    TargetRef('', '')
  with assert_raises(TypeError):
    TargetRef(None, None)
  TargetRef(None, 'hello')
  TargetRef('thescope', 'hello')
