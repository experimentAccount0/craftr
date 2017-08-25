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

__all__ = ['Scope', 'Target', 'Action', 'Session', 'compute_action_key']

import abc
import hashlib
import sys
import typing as t
import hashing from './hashing'
import path from './path'
import {Configuration} from './config'
import {Graph} from './graph'
import platform from './platform'
import {reqref, file_iter_chunks} from './util'


class Scope:
  """
  A scope represents a single module in the build environment and is a
  container for targets. The name of a scope matches the name of the
  Node.py package that it is representative for.
  """

  name: str
  directory: str
  targets: t.Dict[str, 'Target']

  def __init__(self, name: str, directory: str):
    self.name = name
    self.directory = directory
    self.targets = {}

  def __repr__(self):
    return '<Scope "{}" @ "{}">'.format(self.name, self.directory)

  def add_target(self, target: 'Target') -> None:
    assert target.scope() is self
    if target.name in self.targets:
      raise RuntimeError('target {!r} already exists'.format(target.name))
    self.targets[target.name] = target


class Target(metaclass=abc.ABCMeta):
  """
  A target is an abstraction of a task that takes a set of inputs and other
  targets as dependencies and generates a set of output files from them.
  Targets are created inside Craftr build scripts and inserted into the
  #Session.target_graph. Once all targets have been collected, they are
  translated into concrete #Action#s.
  """

  session: reqref['Session']
  scope: reqref[Scope]
  name: str
  actions: t.Dict[str, 'Action']

  def __init__(self, scope: Scope, name: str, visible_deps: t.List[str] = None):
    self.session = None
    self.scope = reqref[Scope](scope)
    self.name = name
    self.visible_deps = visible_deps
    self.actions = {}

  def __repr__(self):
    typename = type(self).__name__
    return '<{} "{}">'.format(typename, self.identifier)

  @property
  def identifier(self):
    return '//{}:{}'.format(self.scope().name, self.name)

  def deps(self, visible=False) -> t.List['Target']:
    """
    Returns the target's dependencies. If *visible* is #True, only its
    visible dependencies are returned (which are stored directly in the
    target rather than in the target graph).

    Can only be used with the #Target registered to a #Session. Raises
    a #RuntimeError otherwise.
    """

    if not self.session:
      raise RuntimeError('target not attached to a session')

    graph = self.session().target_graph
    if visible and self.visible_deps is not None:
      keys = [graph[key] for key in self.visible_deps]
    else:
      keys = list(graph.inputs(self.identifier))

    return [graph[k] for k in keys]

  def add_action(self, action: 'Action') -> None:
    """
    Adds an action to the #Target.
    """

    assert action.source() is self
    if action.name in self.actions:
      raise RuntimeError('action {!r} already exists'.format(action.name))
    self.actions[action.name] = action

  def leaf_actions(self) -> t.Iterable['Action']:
    """
    Returns a list of all the actions in this target that do not serve as an
    input to another action inside the same target. These actions are
    considered "leaf actions" and are used by default when a Target is passed
    to the dependencies of an action when using #api.create_action() or
    #api.action_factory().
    """

    if not self.session:
      raise RuntimeError('target not attached to a session')

    graph = self.session().action_graph
    for action in self.actions.values():
      for output in graph.outputs(action.identifier):
        if graph[output].source() is self:
          break
      else:
        yield action

  @abc.abstractmethod
  def translate(self):
    pass


class Action(metaclass=abc.ABCMeta):
  """
  An action is a concrete implementation of a task or a partial task that is
  represented by a #Target in an abstract way. Actions may be interpreted
  separately by matching their type against known action implementations,
  depending on the selected build backend. Only the native Python build
  backend executes the #run() method (or other build backends may choose to
  execute it in place of a semantically equal system command).

  Actions must be implemented as **pure functions**. There are some cases
  where this behaviour is undesirable (eg. stashing is undesirable, the
  action represents running tests or other executables that should be executed
  like a normal system command with direct access to the build process'
  standard in- and output, etc.). The action's #pure member can be set to
  #False in that case.

  In order for stashing to function properly, actions must provide data that
  influences the outcome of the action in order to be hashed. The default
  implementation of #get_hash_components() yields the input and output
  filenames. #compute_action_key() will already take the version of Craftr
  into account.

  > Note: Since input and output filenames are hashed into the action key,
  > filenames outside of the scope or build directory, respectively, are
  > problematic since no well-defined relative path can be constructed.
  """

  source: reqref[Target]
  name: str
  pure: bool
  inputs: t.List[str]
  outputs: t.List[str]

  def __init__(self, source: Target, name: str, pure: bool = True,
               inputs: t.List[str] = None, outputs: t.List[str] = None):
    self.source = reqref[Target](source)
    self.name = name
    self.pure = pure
    self.inputs = [] if inputs is None else inputs
    self.outputs = [] if outputs is None else outputs

  @property
  def identifier(self):
    return '{}/{}'.format(self.source().identifier, self.name)

  def get_hash_components(self) -> t.Iterable:
    yield hashing.DataComponent(self.identifier.encode('utf8'))
    for filename in self.inputs:
      yield hashing.FileComponent(filename, True)
    for filename in self.outputs:
      yield hashing.FileComponent(filename, False)

  @abc.abstractmethod
  def execute(self) -> 'ActionProcess':
    pass


class ActionProcess(metaclass=abc.ABCMeta):
  """
  The #ActionProcess represents state information for an action that is
  executed in another thread or even another process. It is generally
  reccommended to implement actions in a separate process since Python does
  not support true parallelism.
  """

  @abc.abstractmethod
  def display_text(self) -> str:
    """
    Returns a status message for the current state of the process.
    """

  @abc.abstractmethod
  def is_running(self) -> bool:
    """
    Returns #True while the action is still in progress.
    """

  @abc.abstractmethod
  def wait(self, timeout: float = None) -> None:
    """
    Wait until the process completed, or at max *timeout* seconds.
    """

  @abc.abstractmethod
  def poll(self) -> t.Optional[int]:
    """
    Return a status-code for the action. A status code of zero indicates
    success, any other value indicates failure. If the process is still
    running, #None is returned.
    """

  @abc.abstractmethod
  def stdout(self) -> t.Union[str, bytes]:
    """
    Returns the output of the process. Some actions might be implemented as
    having direct access to the build process' standard in- and output. In
    this case, the function should simply return an empty string.
    """

  def print_stdout(self) -> None:
    """
    Retrieves the output of this process from #stdout() and prints it to this
    process' standard output.
    """

    data = self.stdout()
    if isinstance(data, bytes):
      sys.stdout.buffer.write(data)
    else:
      std.stdout.write(data)


class Session:
  """
  The session manages scopes and the target and action graph.
  """

  target: str
  target_graph: Graph[str, Target]
  action_graph: Graph[str, Action]
  scopes: t.Dict[str, Scope]
  scopestack: t.List[Scope]

  def __init__(self, target: str = 'debug', arch: str = None):
    self.build_directory = 'build'
    self.target_graph = Graph()
    self.action_graph = Graph()
    self.scopes = {}
    self.scopestack = []
    self.config = Configuration({
      'arch': arch or platform.arch,
      'platform': platform.name,
      'target': target
    })
    self.config['build.arch'] = arch or platform.arch
    self.config['build.target'] = target

  @property
  def arch(self):
    return self.config['build.arch']

  @property
  def target(self):
    return self.config['build.target']

  @property
  def current_scope(self) -> Scope:
    return self.scopestack[-1]

  def scope(self, name: str) -> Scope:
    return self.scopes[name]

  def enter_scope(self, name: str, directory: str) -> Scope:
    if name not in self.scopes:
      scope = Scope(name, directory)
      self.scopes[name] = scope
    else:
      scope = self.scopes[name]
      if scope.directory != directory:
        raise RuntimeError('scope directory mismatch (duplicate scopes?)')
    self.scopestack.append(scope)
    return scope

  def leave_scope(self, name: str) -> None:
    assert self.scopestack.pop().name == name

  def add_target(self, target: Target):
    """
    Adds a target to the graph and its scope.
    """

    target.session = reqref(self)
    target.scope().add_target(target)
    self.target_graph[target.identifier] = target

  def add_action(self, target: Target, action: Action,
                 deps: t.List[Action] = None):
    """
    Adds an action to the specified *target* and into the action graph. If
    specified, *deps* can be used to specify temporal dependencies to the
    action.
    """

    assert target.session() is self
    target.add_action(action)

    ident = action.identifier
    self.action_graph[ident] = action
    for dep in (deps or ()):
      self.action_graph.edge(dep.identifier, ident)

  def translate_targets(self):
    """
    Translate all targets to actions.
    """

    for target in self.target_graph.values():
      target.translate()


def compute_action_key(action: Action):
  """
  Computes the hash key of an action. This should only be used for "pure"
  actions, as impure actions are not supposed to be hashed (since it they
  are considered to yield different outputs for two equal invokations).
  """

  directory = action.source().scope().directory
  hasher = hashlib.sha1()

  hasher.update(module.package.json['version'].encode('utf8'))
  for comp in action.get_hash_components():
    if isinstance(comp, hashing.DataComponent):
      hasher.update(comp.data)
    elif isinstance(comp, hashing.FileComponent):
      filename = path.canonical(path.rel(comp.filename, directory))
      hasher.update(filename)
      if comp.is_input:
        try:
          with open(comp.filename, 'rb') as fp:
            for chunk in file_iter_chunks(fp, 4096):
              hasher.update(chunk)
        except (FileNotFoundError, PermissionError):
          pass

  return hasher.hexdigest()
