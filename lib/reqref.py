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
  """
  This exception is raised when a #reqref object is dereferenced but the
  reference is lost.
  """


class ref(t.Generic[T]):
  """
  A weak reference that requires the referenced object to be available when it
  is dereferenced. If the reference is list, a #ReferenceLostError is raised.

  Unlike #weakref.ref(), the ref may be initialized with a #None value.
  """

  #: The type of the object that the ref was initialized with. It is used
  #: to provide a useful error message when a #ReferenceLostError is raised.
  __type: T

  #: The internal weak reference, or None if the ref was initialized
  #: with None.
  __ref: t.Optional[weakref.ref]

  def __init__(self, obj: T):
    self.__type = type(obj)
    self.__ref = weakref.ref(obj) if obj is not None else None

  def __call__(self) -> T:
    """
    Returns the referenced object. If the reference is lost, a
    #ReferenceLostError is raised instead.
    """

    if self.__ref is None:  # Was initialized with None.
      return None

    obj = self.__ref()
    if obj is None:
      msg = 'lost reference to {} object'.format(self.__type.__name__)
      raise ReferenceLostError(msg)

    return obj

  def __repr__(self):
    return '<ref of type "{}">'.format(self.__type.__name__)


class ref_property:
  """
  A descriptor that saves values as a #ref.
  """

  def __init__(self, name):
    self.name = name

  def __get__(self, instance, klass=None):
    name = '_{}__{}'.format(type(instance).__name__, self.name)
    return getattr(instance, name)()

  def __set__(self, instance, value):
    name = '_{}__{}'.format(type(instance).__name__, self.name)
    setattr(instance, name, ref(value))


ref.property = ref_property
ref.error = ReferenceLostError
