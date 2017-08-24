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

import typing as t
import weakref

T = t.TypeVar('T')


class ReferenceLostError(RuntimeError):
  pass


class reqref(t.Generic[T]):
  """
  A "required weakref" is similar to a normal weakref, but dereferencing it
  and loosing its object raises a #ReferenceLostError.
  """

  _type: T
  _ref: t.Optional[weakref.ref]

  def __init__(self, obj: T):
    self._type = type(obj)
    self._ref = weakref.ref(obj) if obj is not None else None

  def __call__(self) -> T:
    if self._ref is None:
      return None
    obj = self._ref()
    if obj is None:
      msg = 'lost reference to {} object'.format(self._type.__name__)
      raise ReferenceLostError(msg)
    return obj

  def __repr__(self):
    return '<reqref of {}>'.format(self._type.__name__)


def file_iter_chunks(fp: t.IO[T], chunksize: int = 4096) -> t.Iterable[T]:
  """
  Iterates over a file-like object in chunks and yields them.
  """

  while True:
    data = fp.read(chunksize)
    if not data:
      break
    yield data


class TargetRef(t.NamedTuple):
  """
  Represents a reference to a target. Target references can be parsed from
  the following syntax:

      [//scope]:target
  """

  scope: str
  target: str

  @classmethod
  def parse(cls, s: str, default_scope: str = None):
    if not s.startswith('//') and not s.startswith(':'):
      raise ValueError('invalid target-reference string: {!r}'.format(s))
    left, sep, right = s.partition(':')
    if not sep:
      raise ValueError('invalid target-reference string: {!r}'.format(s))
    if left:
      assert left.startswith('//')
      left = left[2:]
    return cls(left or default_scope, right)

  def __str__(self):
    res = ':' + self.target
    if self.scope:
      res = '//' + self.scope + res
    return res
