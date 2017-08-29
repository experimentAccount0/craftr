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
import weakref


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

  @property
  def target(self):
    return self.__target()

  @property
  def session(self):
    return self.target.session

  @property
  def long_name(self):
    return '{}!{}'.format(self.target.name, self.name)


class ActionImpl(metaclass=abc.ABCMeta):
  """
  This interface describes the behaviour of an action.
  """

  def __init__(self, action):
    self.__action = weakref.ref(action)

  @property
  def action(self):
    return self.__action()

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
