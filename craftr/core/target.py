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

import {Cell} from './cell'
import weakref


class Target:
  """
  A target is an abstraction of an element in the build graph that represents
  one or more artifacts to build or to be considered part of another build
  target. Every target will be translated to one or more actions before the
  build is completed.

  How a target behaves is implemented with a #TargetImpl object. In order to
  properly construct a #Target and #TargetImpl pair, use `__new__()`.

  ```python
  impl = object.__new__(MyTargetImpl)
  target = Target(cell, name, deps, visible_deps, impl)
  impl.__init__(target, ...)
  ```
  """

  def __init__(self, cell, name, deps, visible_deps, impl):
    self.__cell = weakref.ref(cell)
    self.name = name
    self.deps = deps
    self.visible_deps = visible_deps
    self.impl = impl

  @property
  def cell(self):
    return self.__cell()

  @property
  def session(self):
    return self.cell.session

  @property
  def long_name(self):
    return '//{}:{}'.format(self.cell.name, self.name)

  def transitive_deps(self):
    result = self.deps[:]
    def recursion(target):
      result.extend(target.visible_deps)
      for dep in target.visible_deps:
        recursion(dep)
    for dep in self.deps:
      recursion(dep)
    recursion(self)
    return result


class TargetImpl(metaclass=abc.ABCMeta):
  """
  This interface describes the behaviour of a #Target.
  """

  def __init__(self, target):
    self.__target = weakref.ref(target)

  @property
  def target(self):
    return self.__target()
