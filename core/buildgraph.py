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
import typing as t
import hashing from './hashing'
import path from './path'
import {Graph} from './graph'
import {reqref, file_iter_chunks} from './util'


class Scope:
  """
  A scope represents a single module in the build environment and is a
  container for targets. The name of a scope matches the name of the
  Node.py package that it is representative for.
  """

  name: str
  directory: str

  def __init__(self, name: str, directory: str):
    self.name = name
    self.directory = directory

  def __repr__(self):
    return '<Scope "{}" @ "{}">'.format(self.name, self.directory)


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

  def __init__(self, session: 'Session', scope: Scope, name: str):
    self.session = reqref[Session](session)
    self.scope = reqref[Scope](scope)
    self.name = name

  def __repr__(self):
    return '<Target "{}">'.format(self.name)

  @property
  def identifier(self):
    return '//{}:{}'.format(self.scope.name, self.name)

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

  def __init__(self, source: Target, name: str):
    self.source = reqref[Target](source)
    self.name = name
    self.pure = True
    self.inputs = []
    self.outputs = []

  @property
  def identifier(self):
    return '{}:{}'.format(self.source.identifier, self.name)

  def get_hash_components(self) -> t.Iterable:
    for filename in self.inputs:
      yield hashing.FileComponent(filename, True)
    for filename in self.outputs:
      yield hashing.FileComponent(filename, False)

  @abc.abstractmethod
  def execute(self):  # TODO
    pass


class Session:
  """
  The session manages scopes and the target and action graph.
  """

  target_graph: Graph[str, Target]
  action_graph: Graph[str, Action]

  def __init__(self, target: str = 'debug'):
    self.target = target
    self.target_graph = Graph()
    self.action_graph = Graph()
    self.scopes = {}
    self.scopestack = []

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
