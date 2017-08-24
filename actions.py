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

import abc
import io
import os
import shlex
import subprocess as _subp
import threading
import typing as t
import {Action, ActionProcess} from './core/buildgraph'
import api from './api'


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


class SubprocessActionProcess(ThreadedActionProcess):

  def __init__(self, action: 'SubprocessAction'):
    ThreadedActionProcess.__init__(self)
    self.action = action
    self.commands = list(action.commands)  # acts as a queue
    self.capture = action.capture
    self.current_process = None
    self.current_command = None
    self.buffer = io.BytesIO()

  def display_text(self) -> str:
    if self.current_command is not None:
      return '$ ' + ' '.join(shlex.quote(x) for x in self.current_command)
    return 'SubprocessActionProcess'

  def poll(self):
    with self.lock:
      if self.current_process:
        code = self.current_process.poll()
        if code is None:
          return None  # process not finished
        if code == 0:
          if self.commands:
            return None  # commands left to execute
          return 0
        return code  # bad exit code
      if self.commands:
        return None
      return 0  # no commands, nothing to do

  def stdout(self) -> bytes:
    return self.buffer.getvalue()

  def run(self):
    while True:
      with self.lock:
        if not self.commands:
          break
        self.current_command = self.commands.pop(0)

        if self.capture:
          stdout = _subp.PIPE
          stderr = _subp.STDOUT
          stdin  = _subp.PIPE
        else:
          stdout = stderr = stdin = None

        cwd = self.action.cwd or os.getcwd()
        env = os.environ.copy()
        env.update(self.action.environ)
        self.current_process = _subp.Popen(self.current_command,
          shell=False, stdout=stdout, stderr=stderr, stdin=stdin,
          universal_newlines=False, env=env, cwd=cwd)

        result = self.current_process.communicate()
        if self.capture:
          self.buffer.write(result[0])
        if self.current_process.returncode != 0:
          break


class SubprocessAction(Action):
  """
  An action that can execute one or more system commands.
  """

  commands: t.List[t.List[str]]
  environ: t.Dict[str, str]
  cwd: t.Optional[str]
  capture: bool

  def __init__(self, *, commands, environ=None, cwd=None, capture=True, **kwargs):
    Action.__init__(self, **kwargs)
    self.commands = commands
    self.environ = {} if environ is None else environ
    self.cwd = cwd
    self.capture = capture

  def execute(self):
    return SubprocessActionProcess(self).start()


subprocess = api.action_factory(SubprocessAction)
