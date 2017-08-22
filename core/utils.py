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

import typing
import weakref

T = typing.TypeVar('T')


class reqref(typing.Generic[T]):
  """
  Like a #weakref.ref(), but when the referenced object no longer exists, a
  #RuntimeError is raised instead of #None being returned. Another difference
  is that #None is allowed as a parameter, and #None will always be returned
  in that case when it is dereferenced.
  """

  def __init__(self, obj: T):
    self._type = type(obj)
    self._obj = weakref.ref(obj) if obj is not None else None

  def __call__(self) -> T:
    if self._obj is None:
      return None
    obj = self._obj()
    if obj is None:
      raise RuntimeError('lost reference to {} object'.format(self._type.__name__))
    return obj

  def __repr__(self) -> str:
    return '<reqref of {}>'.format(self._type.__name__)


class TargetRef:
  """
  Represents a reference to a #Target in the target graph. Targets are created
  in a build module, which has a scope name, and every target has its own name
  inside that scope. Target references can be expressed as plain strings using
  the following syntax:

      [//scope]:target
  """

  def __init__(self, scope: typing.Optional[str], name: str):
    if not isinstance(name, str):
      raise TypeError('parameter "name" must be str')
    if not name:
      raise ValueError('parameter "name" can not be empty')
    if not scope and scope is not None:
      raise ValueError('parameter "scope" must be None or non-empty string')
    if scope and not isinstance(scope, str):
      raise TypeError('parameter "scope" must be str or None')
    self.scope = scope
    self.name = name

  def __repr__(self) -> str:
    return '<TargetRef {}>'.format(self)

  def __str__(self) -> str:
    result = ':' + self.name
    if self.scope:
      result = '//' + self.scope + result
    return result

  def __hash__(self):
    return hash(self.scope, self.name)

  def __eq__(self, other):
    if isinstance(other, TargetRef):
      return (self.scope, self.name) == (other.scope, other.name)
    return False

  @classmethod
  def from_str(cls, s: str) -> 'TargetRef':
    """
    Parses *s* as a target reference.

    # Raises
    ValueError: If the specified string can not be parsed into a target
      reference.
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

  def isabs(self) -> bool:
    """
    Returns #True if this is an absolute target reference (that is, with a
    scope name assigned to it), #False if it is relative.
    """

    return bool(self.scope)
