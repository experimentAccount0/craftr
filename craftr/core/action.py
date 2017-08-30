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
import traceback
import weakref
import task from '../lib/task'


class Action:
  """
  Actions are generated from targets. They represent any action that is
  necessary to produce a target. The behaviour of an action is implemented as
  #ActionImpl. To create an Action and ActionImpl pair, use `__new__()`.

  ```python
  impl = object.__new__(MyActionImpl)
  action = Action(target, name, deps, input_files, output_files, impl)
  impl.__init__(action, ...)
  """

  def __init__(self, target, name, deps, input_files, output_files, impl):
    self.__target = weakref.ref(target)
    self.name = name
    self.deps = deps
    self.input_files = input_files
    self.output_files = output_files
    self.impl = impl
    self.task = None
    self.aborted = False

  def __repr__(self):
    return '<Action "{}">'.format(self.long_name)

  @property
  def target(self):
    return self.__target()

  @property
  def session(self):
    return self.target.session

  @property
  def long_name(self):
    return '{}!{}'.format(self.target.long_name, self.name)

  def display(self, full):
    return self.impl.display(full)

  def get_buffered_output(self):
    return self.impl.buf.getvalue()

  def is_running(self):
    return self.task and self.task.is_running

  def is_executed(self):
    return self.task and not self.task.is_running

  def exit_code(self):
    if not self.task:
      raise RuntimeError('Action execution has not begun')
    return self.task.result(None)

  def wait(self):
    if not self.task:
      raise RuntimeError('Action execution has not begun')
    self.task.join()

  def abort(self):
    if not self.task:
      raise RuntimeError('Action execution has not begun')
    if not self.aborted:
      self.aborted = True
      self.impl.abort()

  def execute(self):
    if self.task:
      raise RuntimeError('Action was already executed')
    assert all(dep.is_executed() for dep in self.deps)

    def runner():
      try:
        return self.impl.execute()
      except BaseException as e:
        if isinstance(e, SystemExit):
          return e.code
        else:
          self.impl.buf.write(traceback.format_exc().encode())
        if isinstance(e, OSError):
          return e.errno
        return 127

    self.task = task.Task(runner, print_exc=False)


class ActionImpl(metaclass=abc.ABCMeta):
  """
  This interface describes the behaviour of an action.
  """

  def __init__(self, action):
    self.__action = weakref.ref(action)
    self.__buf = io.BytesIO()

  @property
  def action(self):
    return self.__action()

  @property
  def buf(self):
    return self.__buf

  def progress(self):
    return None

  @abc.abstractmethod
  def display(self, full):
    pass

  @abc.abstractmethod
  def abort(self):
    pass

  @abc.abstractmethod
  def execute(self):
    pass
