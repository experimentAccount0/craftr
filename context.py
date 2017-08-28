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
import typing as t
import path from './core/path'
import {Cell, Target, TargetImpl, Action} from './core/buildgraph'
import {TargetRef} from './lib/parse'
import {name as platform} from './core/platform'


class BuildContext:

  __all__ = ['session', 'config', 'path']

  def __init__(self, session):
    self.session = session
    self.path = path
    for func in EXPORTED_FUNCTIONS:
      setattr(self, func.__name__, func)
    for func in STAR_EXPORTED_FUNCTIONS:
      setattr(self, func.__name__, func)
    self.__all__ = self.__all__ + [func.__name__ for func in STAR_EXPORTED_FUNCTIONS]

  @property
  def cell(self):
    return self.session.current_cell

  @property
  def outdir(self):
    return path.join(self.builddir, 'cells', self.cell.name)

  @property
  def builddir(self):
    return self.session.build_directory

  @property
  def config(self):
    return self.session.config

  def resolve_deps(self, deps):
    return [self.session.targets[k].value() for k in deps]

  def create_target(self,
        target_impl_type: t.Type[TargetImpl], *,
        name: str,
        deps: t.List[str] = None,
        visible_deps: t.List[str] = None,
        **kwargs) -> Target:
    """
    Create a new target of the specified *type* and register it to the
    current #Session and cell (or the specified cell).
    """

    current_cell = self.session.current_cell

    # Make sure all dependencies are absolute references.
    if deps is None:
      deps = []
    else:
      deps = [str(TargetRef.parse(x, current_cell.name)) for x in deps]
    if visible_deps is None:
      # The visible deps match the invisible deps, if they are not
      # explicitly specified.
      visible_deps = deps
    else:
      visible_deps = [str(TargetRef.parse(x, current_cell.name))
                      for x in visible_deps]

    deps = self.resolve_deps(deps)
    visible_deps = self.resolve_deps(visible_deps)

    impl = object.__new__(target_impl_type, **kwargs)
    target = Target(self.session, self.cell, name, visible_deps, impl)
    impl.__init__(**kwargs)

    # Link the dependencies of the target.
    for ref in (deps or ()):
      ref.node.connect(target.node)
    for ref in (visible_deps or ()):
      ref.node.connect(target.node)

    return target


  def target_factory(self, cls: t.Type[Target]) -> t.Callable[..., Target]:
    """
    Creates a wrapper for #Target subclasses that calls #create_target() with
    the specified target *cls*. Example:

    ```
    class MyTarget(craftr.Target):
      ...

    my_target = craftr.target_factory(MyTarget)
    ```

    The returned callable has a `wrapped_target_type` argument that contains
    the specified *cls* object.
    """

    @functools.wraps(cls)
    def wrapper(*args, **kwargs):
      return self.create_target(cls, *args, **kwargs)

    wrapper.wrapped_target_type = cls
    return wrapper




EXPORTED_FUNCTIONS = []
STAR_EXPORTED_FUNCTIONS = []

def export(func):
  EXPORTED_FUNCTIONS.append(func)
  return func

def star_export(func):
  STAR_EXPORTED_FUNCTIONS.append(func)
  return func


@export
class AnnotatedTarget(TargetImpl):
  """
  A subclass of #Target which accepts keyword parameters as annotated on the
  class level and stores them.
  """

  def __init__(self, **kwargs):
    for key in type(self).__annotations__.keys():
      if hasattr(type(self), key):
        value = kwargs.pop(key, getattr(type(self), key))
      else:
        try:
          value = kwargs.pop(key)
        except KeyError:
          raise TypeError('missing keyword argument: {!r}'.format(key))
      setattr(self, key, value)
    TargetImpl.__init__(self, **kwargs)


@export
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


@star_export
def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the cell
  base directory!).
  """

  if not parent:
    parent = require.context.current_module.directory
  return path.glob(patterns, parent, excludes)


@star_export
def canonicalize(paths: t.Union[str, t.List[str]],
                 parent: str = None) -> t.Union[str, t.List[str]]:
  """
  Canonicalize a path or a list of paths. Relative paths are converted to
  absolute paths from the currently executed module's directory.
  """

  parent = parent or require.context.current_module.directory
  if isinstance(paths, str):
    return path.canonical(path.abs(paths, parent))
  else:
    return [path.canonical(path.abs(x, parent)) for x in paths]
