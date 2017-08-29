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
import {Cell} from './cell'
import {LoaderSupport} from './loader'


class Session:

  def __init__(self, maindir=None, builddir=None):
    self.cells = {}
    self.builddir = builddir or 'build'
    self.maindir = maindir or os.getcwd()

  @contextlib.contextmanager
  def with_loader(self):
    loader = next((x for x in require.context.resolvers if isinstance(x, nodepy.FilesystemResolver)), None)
    if not loader:
      raise RuntimeError('FilesystemLoader not found')
    support = LoaderSupport(self)
    loader.supports.insert(0, support)
    try:
      yield self
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
