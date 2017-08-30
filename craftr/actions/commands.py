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

import os
import shlex
import subprocess
import {ActionImpl} from '../core/action'


class Commands(ActionImpl):

  def __init__(self, action, *, commands, environ=None, cwd=None, buffer=True):
    super().__init__(action)
    self.commands = commands
    self.environ = environ
    self.cwd = cwd or os.getcwd()
    self.buffer = buffer
    self._index = 0
    self._process = None

  def display(self, full):
    if full:
      return '\n'.join(' '.join(map(shlex.quote, x)) for x in self.commands)
    elif self._index < len(self.commands):
      return ' '.join(map(shlex.quote, self.commands[self._index]))
    else:
      return 'commands(done)'

  def abort(self):
    if self._process:
      self._process.terminate()

  def progress(self):
    if self.commands:
      return self._index / len(self.commands)
    return 1.0

  def execute(self):
    environ = os.environ.copy()
    if self.environ is not None:
      environ.update(self.environ)

    stdin = stdout = stderr = None
    if self.buffer:
      stdin = stdout = subprocess.PIPE
      stderr = subprocess.STDOUT

    code = 0
    for i in range(len(self.commands)):
      self._index = i
      self._process = subprocess.Popen(
        self.commands[i], env=environ, cwd=self.cwd,
        stdin=stdin, stdout=stdout, stderr=stderr,
        universal_newlines=False)
      content = self._process.communicate()[0]
      if self.buffer:
        self.buf.write(content)
      code = self._process.returncode
      if code != 0:
        break

    return code
