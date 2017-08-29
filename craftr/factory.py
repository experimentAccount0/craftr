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
import {Action} from './core/action'
import {Target} from './core/target'
import {get_current_module} from './core/loader'


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
    impl.__init__(target, **kwargs)
    cell.add_target(target)
    return target

  return wrapper
