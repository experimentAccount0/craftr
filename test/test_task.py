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
import time
import threading
import task from 'craftr/lib/task'


def test_task():

  event = threading.Event()
  def action():
    event.wait()
    return 42

  t = task.Task(action)
  assert_equals(t.result(None), None)
  event.set()
  assert_equals(t.result(), 42)
  event.clear()

  t = task.Task(action)
  assert_equals(t.result(58), 58)
  event.set()
  assert_equals(t.result(), 42)
  assert_equals(t.result(), 42)
  event.clear()

  def raiser():
    event.wait()
    raise IndexError("foobar!")

  t = task.Task(raiser, print_exc=False)
  assert_equals(t.result(None), None)
  event.set()
  with assert_raises(IndexError):
    t.result()
  event.clear()
