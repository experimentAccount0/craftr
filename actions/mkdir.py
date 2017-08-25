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

__all__ = ['mkdir', 'MkdirAction']

import errno
import os
import api from '../api'
import {ThreadedActionProcess} from './base'
import {Action} from '../core/buildgraph'


class MkdirActionProcess(ThreadedActionProcess):

  def __init__(self, directory):
    self.directory = directory
    self.exit_code = None
    super().__init__()

  def display_text(self):
    return 'mkdir: {}'.format(self.directory)

  def terminate(self):
    pass

  def poll(self):
    with self.lock:
      return self.exit_code

  def run(self):
    exit_code = 0
    try:
      os.makedirs(self.directory)
    except OSError as e:
      if e.errno != errno.EEXIST:
        exit_code = e.errno
        self.print(e, err=True)
    with self.lock:
      self.exit_code = exit_code


class MkdirAction(Action):

  def __init__(self, *, directory: str, **kwargs):
    super().__init__(**kwargs)
    self.directory = directory

  def skippable(self, build):
    if os.path.isdir(self.directory):
      return True

  def execute(self):
    return MkdirActionProcess(self.directory).start()


mkdir = api.action_factory(MkdirAction)
