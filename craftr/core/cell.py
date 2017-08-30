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

import os
import weakref


class Cell:
  """
  A cell is a scope where targets can be created. Every scope has a unique
  name (that matches the Node.py package name, thus it may contain slashes!),
  a base directory (where the `package.json` resides) and a version number
  (also from the Node.py package).
  """

  def __init__(self, session, name, version, directory):
    self.__session = weakref.ref(session)
    self.name = name
    self.version = version
    self.directory = directory
    self.targets = {}

  def __repr__(self):
    return '<Cell "{}">'.format(self.name)

  @property
  def session(self):
    return self.__session()

  @property
  def builddir(self):
    return os.path.join(self.session.builddir, 'cells', self.name)

  def add_target(self, target):
    assert target.cell is self
    if target.name in self.targets:
      raise RuntimeError('target {!r} already exists'.format(target.long_name))
    self.targets[target.name] = target
