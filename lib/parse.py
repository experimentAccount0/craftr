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


class TargetRef(t.NamedTuple):
  """
  Represents a reference to a target. Target references can be parsed from
  the following syntax:

  ```
  [//scope]:target
  ```
  """

  scope: str
  target: str

  @classmethod
  def parse(cls, s: str, default_scope: str = None) -> 'TargetRef':
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
