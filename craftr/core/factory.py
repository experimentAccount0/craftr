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

import functools
import {Action} from './action'
import {Target, TargetImpl} from './target'
import {get_current_module} from './loader'


def target_factory(target_impl_class):
  """
  Create a factory for a #TargetImpl subclass.
  """

  @functools.wraps(target_impl_class)
  def wrapper(*, name, deps=(), visible_deps=(), **kwargs):
    cell = get_current_module().cell
    session = cell.session
    deps = [session.find_target(x) for x in deps]
    visible_deps = [session.find_target(x) for x in visible_deps]
    impl = object.__new__(target_impl_class)
    target = Target(cell, name, deps, visible_deps, impl)
    print(">>", impl)
    impl.__init__(target, **kwargs)
    cell.add_target(target)
    return target

  return wrapper


def inherit_annotations(*from_):
  """
  Decorator to inherit annotations from the object *from_*. If *from_* is
  not specified, the decorator is supposed to be used on a class and the
  parent class' annotations are inherited.
  """

  def wrapper(obj):
    nonlocal from_
    if not from_ and isinstance(obj, type):
      from_ = obj.__bases__
    for src in from_:
      for key in src.__annotations__:
        if key not in obj.__annotations__:
          obj.__annotations__[key] = src.__annotations__[key]
    return obj

  return wrapper


class AnnotatedTargetImpl(TargetImpl):
  """
  A subclass of #Target which accepts keyword parameters as annotated on the
  class level and stores them.
  """

  def __init__(self, target, **kwargs):
    for key in type(self).__annotations__.keys():
      if hasattr(type(self), key):
        value = kwargs.pop(key, getattr(type(self), key))
      else:
        try:
          value = kwargs.pop(key)
        except KeyError:
          raise TypeError('missing keyword argument: {!r}'.format(key))
      setattr(self, key, value)
    super().__init__(target, **kwargs)
