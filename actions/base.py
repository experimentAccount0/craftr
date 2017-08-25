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

__all__ = ['ThreadedActionProcess']

import abc
import threading
import {ActionProcess} from '../core/buildgraph'


class ThreadedActionProcess(ActionProcess, threading.Thread):
  """
  A base class to implement action-processes in a separate thread. In 99% of
  the cases, this is the class that you want to inherit from when implementing
  an action process.
  """

  lock: threading.RLock

  def __init__(self, target=None):
    threading.Thread.__init__(self, target=target)
    self.lock = threading.RLock()

  def start(self) -> 'ThreadedActionProcess':
    threading.Thread.start(self)
    return self

  @abc.abstractmethod
  def run(self) -> None:
    pass

  def is_running(self) -> bool:
    return self.is_alive()

  def wait(self, timeout: float = None) -> None:
    self.join(timeout)
