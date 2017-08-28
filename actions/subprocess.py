
__all__ = ['Subprocess']

import io
import os
import shlex
import subprocess as _subp
import threading
import typing as t

import {ActionImpl, DataComponent} from '../core/buildgraph'


class Subprocess(ActionImpl):

  commands: t.List[t.List[str]]
  environ: t.Dict[str, str]
  cwd: t.Optional[str]
  buffer_output: bool

  def __init__(self, commands, environ=None, cwd=None, buffer_output=True):
    super().__init__()
    self.commands = commands
    self.environ = {} if environ is None else environ
    self.cwd = cwd
    self.buffer_output = buffer_output
    self.__queue = None
    self.__current_command = None
    self.__current_process = None

  def hash_compnents(self):
    yield from super().hash_compnents()
    commands = ''.join(''.join(cmd) for cmd in self.commands)
    yield DataComponent(commands.encode('utf8'))

  def display(self, full):
    if full:
      return '\n'.join(' '.join(map(shlex.quote, cmd) for cmd in self.commands))
    else:
      if self.__current_command:
        return ' '.join(map(shlex.quote, self.__current_command))

  def progress(self):
    if not self.__queue:
      return 1.0
    return len(self.__queue) / len(self.commands)

  def abort(self):
    if self.__current_process:
      self.__current_command.terminate()

  def execute(self):
    while self.__queue:
      # TODO: Synchronization
      self.__current_command = self.__queue.pop(0)
      if self.buffer_output:
        stdout = _subp.PIPE
        stderr = _subp.STDOUT
        stdin  = _subp.PIPE
      else:
        stdout = stderr = stdin = None

      cwd = self.cwd or os.getcwd()
      env = os.environ.copy()
      env.update(self.environ)

      try:
        self.__current_process = _subp.Popen(
          self.__current_command,
          shell=False, stdout=stdout, stderr=stderr, stdin=stdin,
          universal_newlines=False, env=env, cwd=cwd)
      except OSError as exc:
        self.print(exc, err=True)
        return exc.errno

      result = self.__current_process.communicate()
      if self.buffer_output:
        self.buffer.write(result[0])
      code = self.__current_process.returncode
      if code != 0:
        return code

    return 0
