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

import sys
import threading
import traceback
import typing as t


class Task:
  """
  A thread-like object that delivers the result of the wrapped callable.
  Creating a task immediately starts it in a separate thread.
  """

  function: t.Callable[[], t.Any]
  thread: threading.Thread
  condition: threading.Condition

  def __init__(self, function, print_exc=True, daemon=True):
    self.function = function
    self.print_exc = print_exc
    self.__exception = None
    self.__result = None
    self.thread = threading.Thread(target=self.__run)
    self.thread.daemon = daemon
    self.condition = threading.Condition()
    self.thread.start()

  def __run(self):
    result = None
    exception = None
    try:
      result = self.function()
    except BaseException:
      exception = sys.exc_info()
      if self.print_exc:
        traceback.print_exc()
    with self.condition:
      self.__result = result
      self.__exception = exception
      self.condition.notify_all()

  def join(self, timeout=None):
    self.thread.join(timeout)

  def result(self, default=NotImplemented):
    if self.thread.is_alive():
      if default is NotImplemented:
        self.thread.join()
      else:
        return default
    with self.condition:
      if self.__exception is not None:
        reraise(self.__exception)
      return self.__result

  def exception(self, default=NotImplemented):
    if self.thread.is_alive():
      if default is NotImplemented:
        self.thread.join()
      else:
        return default
    with self.condition:
      return self.__exception


def reraise(exc_info):
  et, ev, tb = exc_info
  raise ev.with_traceback(tb)
