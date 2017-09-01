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

__all__ = ['NamedObject']

import sys

# This module requires Python 3.6 or newer (type annotations on class
# variables. ordered dictionaries, object.__init_subclass__()).
if sys.version < '3.6':
  raise EnvironmentError('Python 3.6+ required')


class NamedObject:
  """
  A base-class similar to the #typing.NamedTuple.
  """

  def __init_subclass__(cls, **kwargs):
    # Inherit the annotations of the base classes, in the correct order.
    annotations = getattr(cls, '__annotations__', {})
    new_annotations = {}
    for base in cls.__bases__:
      for key, value in getattr(base, '__annotations__', {}).items():
        if key not in annotations:
          new_annotations[key] = value
    new_annotations.update(annotations)
    cls.__annotations__ = new_annotations
    return super().__init_subclass__(**kwargs)

  def __init__(self, *args, **kwargs):
    annotations = getattr(self, '__annotations__', {})
    if len(args) > len(annotations):
      raise TypeError('{}() expected {} positional arguments, got {}'
        .format(type(self).__name__, len(annotations), len(args)))

    for arg, (key, ant) in zip(args, annotations.items()):
      setattr(self, key, arg)
      if key in kwargs:
        raise TypeError('{}() duplicate value for argument "{}"'
          .format(type(self).__name__, key))

    for key, ant in annotations.items():
      if key in kwargs:
        setattr(self, key, kwargs.pop(key))
      elif not hasattr(self, key):
        raise TypeError('{}() missing argument "{}"'
          .format(type(self).__name__, key))

    for key in kwargs.keys():
      raise TypeError('{}() unexpected keyword argument "{}"'
        .format(type(self).__name__, key))

  def __repr__(self):
    members = ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in self.__annotations__)
    return '{}({})'.format(type(self).__name__, members)

  def __iter__(self):
    for key in self.__annotations__:
      yield getattr(self, key)

  def asdict(self):
    return {k: getattr(self, k) for k in self.__annotations__}
