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
import {Action} from './action'


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
    self.actions = {}
    self.translated = False

  def __repr__(self):
    return '<Target "{}">'.format(self.long_name)

  @property
  def cell(self):
    return self.__cell()

  @property
  def session(self):
    return self.cell.session

  @property
  def long_name(self):
    return '//{}:{}'.format(self.cell.name, self.name)

  def add_action(self, action):
    assert action.target is self
    if action.name in self.actions:
      raise RuntimeError('action {!r} already exists.'.format(action.name))
    self.actions[action.name] = action

  def leaf_actions(self):
    actions = set(self.actions.values())
    outputs = set()
    for action in actions:
      for dep in action.deps:
        outputs.add(dep)
    return actions - outputs

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

  def translate(self):
    if self.translated:
      raise RuntimeError('target {!r} already translated'.format(self.long_name))

    # Ensure that all dependencies are translated.
    for dep in self.deps:
      assert dep.translated, dep
    for dep in self.visible_deps:
      assert dep.translated, dep

    self.translated = True
    self.impl.translate()


class TargetImpl(metaclass=abc.ABCMeta):
  """
  This interface describes the behaviour of a #Target.
  """

  def __init__(self, target):
    self.__target = weakref.ref(target)

  @property
  def target(self):
    return self.__target()

  @property
  def cell(self):
    return self.target.cell

  def action(self, action_impl_type, *, name, deps=(), input_files=(),
                   output_files=(), **kwargs):
    """
    Add a new #Action to the target. Should be used inside #translate().
    """

    target = self.target

    def unpack_deps():
      new_deps = []
      for dep in deps:
        if isinstance(dep, Target):
          new_deps += dep.leaf_actions()
        elif isinstance(dep, Action):
          new_deps.append(dep)
        elif isinstance(dep, str):
          new_deps.append(target.actions[dep])
        else:
          raise TypeError('dependency must be Target/Action/str', type(dep))
      return new_deps

    deps = unpack_deps()
    input_files = [os.path.abspath(x) for x in input_files]
    output_files = [os.path.abspath(x) for x in output_files]
    impl = object.__new__(action_impl_type)
    action = Action(target, name, deps, input_files, output_files, impl)
    impl.__init__(action, **kwargs)
    target.add_action(action)
    return action

  @abc.abstractmethod
  def translate(self):
    pass


def parse_target_reference(s, default_scope=None):
  """
  Parses a target reference of the form `[//scope]:target`.
  """

  if not s.startswith('//') and not s.startswith(':'):
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  left, sep, right = s.partition(':')
  if not sep:
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  if left:
    assert left.startswith('//')
    left = left[2:]
  return (left or default_scope, right)
