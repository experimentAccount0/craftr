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
import traceback
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
    self.after_load_handlers = []

  @staticmethod
  def get_current():
    return get_current_module().cell.session

  def finally_(self, func):
    self.after_load_handlers.append(func)

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
      for func in self.after_load_handlers:
        try:
          func()
        except:
          traceback.print_exc()

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


class NoSuchTargetError(Exception):
  pass
