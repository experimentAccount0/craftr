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
"""
This module provides the base facilities to implement a graph of abstract
build targets, which can then be turned into build actions. Actions are then
either exported to a different format for the build process (eg. a Ninja build
manifest) or can be executed directly.
"""

import abc
import contextlib
import hashlib
import typing
import keying from './keying'
import log from './log'
import path from './path'
import platform from './platform'
import {Configuration} from './config'
import {StashServer} from './stash'
import {TargetRef, reqref} from './utils'

VERSION = module.package.json['version']


class Scope:
  """
  Represents the scope of a build module. Keeps track of the #Target#s and
  #Pool#s created in that scope.
  """

  def __init__(self, name: str, directory: str):
    self.name = name
    self.directory = directory
    self.targets = {}

  def __repr__(self):
    return '<Scope {!r}>'.format(self.name)


class Pool:
  """
  Pools allow you to limit the execution of targets to a finite number of
  concurrent jobs. This is useful for CPU or memory heave tasks such as link
  steps. There is one special "console" pool that ensures that ensures that
  actions generated by a targets inside that pool are executed sequentially
  and output is redirected to the terminal in real-time.

  Similar to targets, pools are also scoped with a #TargetRef.
  """

  def __init__(self, scope: typing.Optional[Scope], name: str, depth: int):
    self.scope = reqref(scope)
    self.name = name
    self.depth = depth

  def __repr__(self) -> str:
    ref = TargetRef(self.scope, self.name)
    return '<Pool "{}" (depth: {})>'.format(ref, self.depth)


Pool.console = Pool(None, 'console', 1)


class Target(metaclass=abc.ABCMeta):
  """
  A #Target is an abstraction of a task to translate input files into output
  files. After all targets are collected and the target graph is complete,
  they are each turned into one or more #Action#s to form the action graph.
  Subclasses must implement the #translate() method for this conversion.

  Targets are identified by a scope and target name.

  Every Target may expose a set of visible dependencies. If no visible
  dependencies are explicitly defined, they will be the same as the target's
  normal dependencies (#deps and #visible_deps will be the exact same list).

  Target subclasses are supposed to perform instance-checks on their
  dependencies (not their visible dependencies) against other known target
  subclasses to be able to consider additional information when translating
  into Actions (e.g. C/C++ library targets should be considered when building
  other libraries or executables).
  """

  def __init__(self, scope: Scope, name: str, deps: typing.List['Target'],
                     visible_deps: typing.Optional[typing.List['Target']],
                     pool: typing.Optional['Pool'] = None):
    self.scope = reqref(scope)
    self.name = name
    self.deps = deps[:]
    self.visible_deps = self.deps if visible_deps is None else visible_deps[:]
    self.actions = {}

  def __repr__(self) -> str:
    ref = TargetRef(self.scope, self.name)
    return '<{} "{}">'.format(type(self).__name__, ref)

  @abc.abstractmethod
  def translate(self, session: 'Session') -> None:
    """
    Translate this #Target into one or more actions.
    """


class ActionProcess(metaclass=abc.ABCMeta):
  """
  Descibes the running process of an executing #Action. Actions may be
  implemented as Python threads, but it is recommended to implement them
  as subprocesses.
  """

  @abc.abstractmethod
  def display_name(self) -> str:
    """
    Return the display name of the action.
    """

  @abc.abstractmethod
  def is_running(self) -> bool:
    """
    Returns #True while the action is still in progress.
    """

  @abc.abstractmethod
  def status(self) -> typing.Optional[int]:
    """
    Return a status-code for the action. A status code of zero indicates
    success, any other value indicates failure. If the process is still
    running, #None is returned.
    """

  @abc.abstractmethod
  def stdout(self) -> str:
    """
    Returns the output of the process.
    """


class Action(metaclass=abc.ABCMeta):
  """
  An action represents a concrete build instruction and task. Actions are
  generated from targets when their #Target.translate() method is called.

  Actions are "pure functions" in that the same inputs produce the exact same
  outputs, always. Thus, actions must be uniquely identifiable by a key. This
  key can be used, for example, to stash build artifacts for later use.
  """

  def __init__(self, source: 'Target', name: str, deps: typing.List['Action'],
                     inputs: typing.List[str], outputs: typing.List[str]):
    self.source = reqref(source)
    self.name = name
    self.deps = deps
    self.inputs = inputs
    self.outputs = outputs

  def __repr__(self) -> str:
    typename = type(self).__name__
    targetref = TargetRef(self.source.scope, self.source.name)
    return '<{} {!r} -> {}>'.format(typename, self.name, targetref)

  def get_action_key_components(self) -> typing.Iterator[keying.Component]:
    """
    Yield the components from which this action's key should be calculated.
    The default implementation yields a #keying.File for every input and
    output file of this action.

    Subclasses must override this implementation to additionally yield
    information that has great influence on the result of the action, such
    as (impactful) environment variables, command-line arguments and compiler
    types and versions. Platform-dependent actions should also yield the
    platform name and architecture.
    """

    for filename in self.inputs:
      yield keying.File(filename, type=keying.File.Input)
    for filename in self.outputs:
      yield keying.File(filename, type=keying.File.Output)

  @abc.abstractmethod
  def run(self) -> ActionProcess:
    """
    Implement the action. As almost all Python implementations can not be
    multithreaded in the same process, thus it is recommended to start a
    subprocess for the action.

    Note that only native build backends use this method. Backends
    require export to a different build system (such as Ninja) will interpret
    concrete implementations.
    """


class TranslateHelper:
  """
  A helper class that is passed to #Target.translate() to make the translation
  process easier.
  """

  def __init__(self, target: Target, session: 'Session'):
    self.target = target
    self.session = session

  def new(self, action_type: typing.Type[Action], *args, **kwargs) -> Action:
    action = action_type(self.target, *args, **kwargs)
    self.target[action.name] = action
    return action


class ScopeMismatchError(RuntimeError):
  """
  Raised when #Session.enter_scope() is called with a scope that already
  exists but with a different base directory.
  """

  def __init__(self, scope_name, dir_a, dir_b):
    self.scope_name = scope_name
    self.dir_a = dir_a
    self.dir_b = dir_b

  def __str__(self):
    return '{}: {!r} <==> {!r}'.format(self.scope_name, self.dir_a, self.dir_b)


class Session:
  """
  The Session is the central object that manages the build process and all of
  the associated data and routines.
  """

  def __init__(self, target: str = 'debug', stashes: StashServer = None):
    self.config = Configuration()
    self.target = target
    self.stashes = stashes
    self.scopes = {}
    self.scopestack = []

  def __repr__(self) -> str:
    return '<Session target:{}>'.format(self.target)

  def compute_action_key(self, action: Action) -> str:
    """
    Computes the key for an action.
    """

    base_directory = action.scope().directory

    sha1 = hashlib.sha1()
    sha1.update('Craftr-v{}'.format(VERSION).encode('utf8'))
    for comp in action.get_action_key_components():
      if isinstance(comp, keying.Bytes):
        sha1.update(comp.data)
      elif isinstace(comp, keying.File):
        relpath = path.canonical(path.rel(comp.filename, base_directory))
        sha1.update(relpath.encode('utf8'))
        if comp.type == keying.File.Input:
          try:
            with open(comp.filename, 'rb') as fp:
              while True:
                data = fp.read(4096)
                if not data: break
                sha1.update(data)
          except FileNotFoundError:
            pass # Swallow the exception
      else:
        log.warn('Session.compute_action_key(): Unknown keying component: %s',
          type(comp).__name__)

    return sha1.hexdigest()

  def enter_scope(self, name, directory):
    """
    Pushes a new #Scope on the stack. All targets that are created following
    this call are being associated with this scope. If a scope with the
    specified *name* already exists, but the *directory* is not the same,
    a #ScopeMismatchError will be raised.
    """

    directory = path.canonical(directory)
    if name not in self.scopes:
      scope = Scope(name, directory)
      self.scopes[name] = scope
    else:
      scope = self.scopes[name]
      if scope.directory != directory:
        raise ScopeMismatchError(name, directory, scope.directory)

    self.scopestack.append(scope)
    return scope

  def leave_scope(self, name):
    """
    Pops a #Scope from the stack. If the *name* is not the same as the name
    of the current scope, a #RuntimeError is raised.
    """

    other = self.scopestack.pop()
    if other.name != name:
      raise RuntimeError('Expected to leave scope {!r}, but was '
        'attempting to leave scope {!r}'.format(other.name, name))

  @contextlib.contextmanager
  def enter_scope_ctx(self, name, directory):
    self.enter_scope(name, directory)
    try:
      yield
    finally:
      self.leave_scope(name)

  @property
  def current_scope(self):
    return self.scopestack[-1] if self.scopestack else None
