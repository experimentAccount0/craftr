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

__all__ = ['session', 'target', 'platform', 'arch', 'builddir', 'scope',
           'projectdir', 'projectbuilddir', 'config', 'glob', 'canonicalize',
           'path']
import functools
import typing as t
import werkzeug.local as _local
import path from './core/path'
import {Scope, Target, Action} from './core/buildgraph'
import {TargetRef} from './core/util'
import {name as platform} from './core/platform'

local = _local.Local()

#: The current session.
session = local('session')

#: A string that represents the current build target. For debug and production
#: builds, this string is either "release" or "debug". Other names can be used,
#: in which case most build targets will omitt translating to the action graph
#: completely (eg. "docs", and only targets that are used to build documentation
#: files are translated into actions).
target = lambda: session.target

#: The build output directory. Defaults to target/<arch>-<target>.
builddir = lambda: session.build_directory

#: A string that represents the target architecture. This can be an arbitrary
#: string, but defaults to the current platform's architecture.
arch = lambda: session.arch

#: The sessions configuration object.
config = lambda: session.config

#: The current scope.
scope = lambda: session.current_scope

#: Returns the directory of the currently executed module. This directory
#: should be used when handling relative paths.
projectdir = lambda: require.context.current_module.directory

#: The build directory of the current project.
projectbuilddir = lambda: path.join(session.build_directory, 'scopes', scope().name)


def create_target(
      type: t.Type[Target], *,
      name: str,
      deps: t.List[str] = None,
      visible_deps: t.List[str] = None,
      scope: t.Union[str, Scope] = None,
      **kwargs) -> Target:
  """
  Create a new target of the specified *type* and register it to the
  current #Session and scope (or the specified scope).
  """

  current_scope = session.current_scope
  scope = scope or current_scope

  # Make sure all dependencies are absolute references.
  if deps is not None:
    deps = [str(TargetRef.parse(x, current_scope.name)) for x in deps]
  if visible_deps is None:
    # The visible deps match the invisible deps, if they are not
    # explicitly specified.
    visible_deps = deps
  else:
    visible_deps = [str(TargetRef.parse(x, current_scope.name))
                    for x in visible_deps]


  target = type(name=name, scope=scope, visible_deps=visible_deps, **kwargs)
  session.add_target(target)

  # Link the dependencies of the target.
  for ref in (deps or ()):
    session.target_graph.edge(ref, target.identifier)
  for ref in (visible_deps or ()):
    session.target_graph.edge(ref, target.identifier)

  return target


def target_factory(cls: t.Type[Target]) -> t.Callable[..., Target]:
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
    return create_target(cls, *args, **kwargs)

  wrapper.wrapped_target_type = cls
  return wrapper


def create_action(
      cls: t.Type[Action],
      source: Target,
      *,
      name: str,
      pure: bool = True,
      deps: t.List[t.Union[Action, Target]] = None,
      inputs: t.List[str] = None,
      outputs: t.List[str] = None,
      **kwargs) -> Action:
  """
  Create a new action for *target* of the specified *cls*. The action will be
  immediately registered to the target and the action graph.
  """

  action_deps = []
  for dep in (deps or ()):
    if isinstance(dep, Target):
      action_deps.extend(dep.leaf_actions())
    elif isinstance(dep, Action):
      action_deps.append(dep)
    else:
      raise TypeError('deps[i] must be Target/Action, got {}'.format(
        type(dep).__name__))

  action = cls(source=source, name=name, pure=pure, inputs=inputs,
               outputs=outputs, **kwargs)
  session.add_action(source, action, deps=action_deps)
  return action


def action_factory(cls: t.Type[Action]) -> t.Callable[..., Action]:
  """
  Creates a wrapper for #Action subclasses that accepts a #Target as first
  parameter (for the source) and then any additional arguments for the
  constructor for *cls*. The action will be added to target specified to the
  first argument immediately. Example:

  ```
  class MyAction(craftr.Action):
    ...

  my_action = action_factory(MyAction)

  class MyTarget(craftr.Target):

    def translate(self):
      my_action(self, 'action-name', deps=self.deps())
  ```

  The returned callable has a `wrapped_action_type` argument that contains
  the specified *cls* object.
  """

  @functools.wraps(cls)
  def wrapper(*args, **kwargs) -> cls:
    return create_action(cls, *args, **kwargs)

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


class AnnotatedTarget(Target):
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
    Target.__init__(self, **kwargs)


def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the scope
  base directory!).
  """

  if not parent:
    parent = require.context.current_module.directory
  return path.glob(patterns, parent, excludes)


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
