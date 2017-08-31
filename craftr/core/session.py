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

import contextlib
import nodepy
import os
import graph from '../lib/graph'
import platform from '../lib/platform'
import {Cell} from './cell'
import {parse_target_reference} from './target'
import {LoaderSupport, get_current_module} from './loader'


class Session:

  def __init__(self, config, builder, arch=None, target=None,
               builddir=None, maindir=None):
    self.cells = {}
    self.config = config
    self.builder = builder
    self.arch = arch or platform.arch
    self.target = target or 'debug'
    self.maindir = maindir or os.getcwd()
    self.builddir = builddir or 'build'
    self.main_module_name = '.'
    self.main_cell = None

  @staticmethod
  def get_current():
    return get_current_module().cell.session

  @contextlib.contextmanager
  def with_loader(self):
    loader = next((x for x in require.context.resolvers if isinstance(x, nodepy.FilesystemResolver)), None)
    if not loader:
      raise RuntimeError('FilesystemLoader not found')
    support = LoaderSupport(self)
    loader.supports.insert(0, support)
    try:
      yield
    finally:
      loader.supports.remove(support)

  def get_main_cell(self):
    return self.get_or_create_cell('__main__', '1.0.0', self.maindir)

  def get_or_create_cell(self, name, version, directory):
    cell = self.cells.get(name)
    if cell and (cell.version, cell.directory) != (version, directory):
      raise RuntimeError('cell version/directory mismatch: {!r}'.format(name))
    if not cell:
      cell = Cell(self, name, version, directory)
      self.cells[name] = cell
    return cell

  def find_target(self, identifier, cell=None):
    scope, name = parse_target_reference(identifier)
    if not scope:
      if not cell:
        cell = get_current_module().cell
      scope = cell.name
      identifier = '//{}:{}'.format(scope, name)

    cell = self.cells.get(scope)
    if cell is None:
      raise NoSuchTargetError(identifier)
    target = cell.targets.get(name)
    if target is None:
      raise NoSuchTargetError(identifier)
    return target

  def targets(self):
    for cell in self.cells.values():
      yield from cell.targets.values()

  def actions(self):
    for target in self.targets():
      yield from target.actions.values()

  def load_targets(self):
    with self.with_loader():
      require(self.main_module_name, current_dir=self.maindir)

  def resolve_targets(self, targets):
    return [self.find_target(x, self.main_cell) for x in targets]

  def create_target_graph(self):
    g = TargetGraph()
    for target in self.targets():
      g.add(target)
    return g

  def create_action_graph(self):
    g = ActionGraph()
    for action in self.actions():
      g.add(action)
    return g


class BaseGraph(graph.Graph):
  """
  Duck typing, yeay!
  """

  def add(self, obj, recursive=True):
    try:
      node = self[obj.long_name]
      assert node.value is obj, (node.value, obj)
      return node
    except KeyError:
      node = graph.Node(obj.long_name, obj)
      super().add(node)

    if recursive:
      for dep in obj.deps:
        other = self.add(dep, True)
        other.connect(node)
      for dep in getattr(obj, 'visible_deps', ()):
        other = self.add(dep, True)
        other.connect(node)
    return node

  def remove(self, obj):
    node = self[obj.long_name]
    super().remove(node)

  def topo_sort(self):
    for node in super().topo_sort():
      yield node.value

  def values(self):
    return (node.value for node in self.nodes())


class TargetGraph(BaseGraph):

  def translate(self):
    for target in self.topo_sort():
      target.translate()
    g = ActionGraph()
    for target in self.values():
      for action in target.actions.values():
        g.add(action)
    return g


class ActionGraph(BaseGraph):
  pass


class NoSuchTargetError(Exception):
  pass
