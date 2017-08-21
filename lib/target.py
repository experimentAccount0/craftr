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

class TargetReference:
  """
  Represents a reference to another target in the build graph. Usually it is
  constructed from a string using the #TargetReference.from_string() method.
  """

  @classmethod
  def from_string(cls, s):
    """
    Creates a #TargetReference object from a string formatted as
    `[//<scope>]:<name>`. If the string's format is invalid, a #ValueError
    is raised.
    """

    if not s.startswith('//') and not s.startswith(':'):
      raise ValueError('invalid target-reference: {!r}'.format(s))
    left, sep, right = s.partition(':')
    if not sep:
      raise ValueError('invalid target-reference: {!r}'.format(s))
    if left:
      assert left.startswith('//')
      left = left[2:]
    return cls(left or None, right)

  @classmethod
  def accept_param(cls, value, param_name):
    if isinstance(value, str):
      return TargetReference.from_string(value)
    elif not isinstance(value, cls):
      raise ValueError('{} expected str or TargetReference'.format(param_name))

  def __init__(self, scope, name):
    if not isinstance(scope, str) and scope is not None:
      raise TypeError('TargetReference.scope must be str or None')
    if scope is not None and not scope:
      assert isinstance(scope, str)
      raise ValueError('TargetReference.scope must not be empty')
    if not isinstance(name, str):
      raise TypeError('TargetReference.name must be str')
    if not name:
      raise ValueError('TargetReference.name must not be empty')
    self.scope = scope
    self.name = name

  def __str__(self):
    s = ':' + self.name
    if self.scope:
      s = '//' + self.scope + s
    return s

  def __repr__(self):
    return '<TargetReference "{!s}">'.format(s)

  def __eq__(self, other):
    if isinstance(other, TargetReference):
      return (other.scope, other.name) == (self.scope, self.name)
    return False

  def __hash__(self):
    return hash(self.scope, self.name)


class Target:
  """
  A target represents something that can be built using one or more #Actions.
  Actions usually take input files and generate output files. Targets need to
  be subclassed so they can implement #generate_actions().

  # Members
  name (TargetReference)
  deps (list of TargetReference)
  visible_deps (None, list of TargetReference)
  translator (None, GraphTranslator)
  """

  def __init__(self, name, deps=(), visible_deps=None):
    """
    # Parameters
    name (str, TargetReference)
    deps (list of (str, TargetReference))
    visible_deps (None, list of (str, TargetReference))
    """

    self.name = TargetReference.accept_param(name, 'Target.name')
    if not self.name.scope:
      raise ValueError('Target.name must have a scope')

    self.deps = []
    for dep in deps:
      self.deps.append(TargetReference.accept_param(dep, 'Target.deps[i]'))

    if visible_deps is None:
      self.visible_deps = None
    else:
      self.visible_deps = []
      for dep in visible_deps:
        self.visible_deps.append(TargetReference.accept_param(dep, 'Target.visible_deps[i]'))

    self.translator = None

  def get_visible_deps(self):
    """
    Returns the actual visible dependencies of the target. This is the same
    as #visible_deps, but falls back to #deps if #visible_deps is #None.
    """

    if self.visible_deps is None:
      return self.deps
    else:
      return self.visible_deps

  def prepare_translation(self, translator):
    """
    Called to initialize the translation of targets to actions. A
    #GraphTranslator instance is passed to this #Target to be owned
    by it.
    """

    self.translator = translator

  def generate_actions(self, graph):
    """
    This function must be implemented by #Target subclasses to generate
    one or more #Action#s for this target and place it into the
    *action_graph*. This graph can then be turned into an executable
    build graph.
    """

    deps = graph.evaluate_deps(self)
    for dep in deps:
      if isinstance(dep, CxxLibrary):
        libs.append(dep.filename)
      # ...

    action = graph.new_action(

    raise NotImplementedError


__all__ = ['TargetReference', 'Target']
import {Action} from './action'
