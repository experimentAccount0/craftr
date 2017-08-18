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


class Target:
  """
  A target represents something that can be built using one or more #Actions.
  Actions usually take input files and generate output files. Targets need to
  be subclassed so they can implement #generate_actions().

  # Members
  name (TargetReference): The full-qualified name of the target as a
    #TargetReference object.
  """

  def __init__(self, name, deps):
    pass
