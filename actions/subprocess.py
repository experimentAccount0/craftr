
__all__ = ['subprocess', 'SubprocessAction']

import io
import os
import shlex
import subprocess as _subp
import threading
import typing as t

import api from '../api'
import {ThreadedActionProcess} from './base'
import {Action, ActionProcess} from '../core/buildgraph'


class SubprocessActionProcess(ThreadedActionProcess):
  """
  Implements the #ActionProcess protocol to run a list of commands
  sequentially.
  """

  def __init__(self, action: 'SubprocessAction'):
    ThreadedActionProcess.__init__(self, capture_output=action.buffer)
    self.action = action
    self.commands = list(action.commands)  # acts as a queue
    self.current_process = None
    self.current_command = None
    self.terminated = False
    self.error_code = None
    self.done = False

  def display_text(self) -> str:
    if self.current_command is not None:
      return '$ ' + ' '.join(shlex.quote(x) for x in self.current_command)
    return 'SubprocessActionProcess'

  def terminate(self):
    with self.lock:
      if self.current_process:
        self.current_process.terminate()
      self.commands = []
      self.terminated = True

  def poll(self):
    with self.lock:
      if not self.done:
        return None
      if self.error_code is not None:
        return self.error_code
      if self.terminated:
        if self.current_process:
          return self.current_process.poll()
        return 127
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

  def run(self):
    while True:
      with self.lock:
        if not self.commands:
          break
        self.current_command = self.commands.pop(0)

        if self.capture_output:
          stdout = _subp.PIPE
          stderr = _subp.STDOUT
          stdin  = _subp.PIPE
        else:
          stdout = stderr = stdin = None

        cwd = self.action.cwd or os.getcwd()
        env = os.environ.copy()
        env.update(self.action.environ)

        try:
          self.current_process = _subp.Popen(self.current_command,
            shell=False, stdout=stdout, stderr=stderr, stdin=stdin,
            universal_newlines=False, env=env, cwd=cwd)
        except OSError as exc:
          self.print(exc, err=True)
          self.exit_code = exc.errno
          self.done = True
          break

      result = self.current_process.communicate()
      if self.capture_output:
        self.buffer.write(result[0])
      if self.current_process.returncode != 0:
        break

    with self.lock:
      self.done = True


class SubprocessAction(Action):
  """
  An action that can execute one or more system commands.
  """

  commands: t.List[t.List[str]]
  environ: t.Dict[str, str]
  cwd: t.Optional[str]
  buffer: bool

  def __init__(self, *, commands, environ=None, cwd=None, buffer=True, **kwargs):
    Action.__init__(self, **kwargs)
    self.commands = commands
    self.environ = {} if environ is None else environ
    self.cwd = cwd
    self.buffer = buffer

  def execute(self):
    return SubprocessActionProcess(self).start()


subprocess = api.action_factory(SubprocessAction)
