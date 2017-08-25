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
An implementation of a local stash for build artifacts.

# Configuration

location (str): The path to a directory where the stashes are stored. Defaults
  to `~/.craftr/stashes`. For platform-dependent configuration, use either
  the platform-matching features of Craftr's configuration files or use a
  `.craftrconfig.py` instead.
"""

import os
import typing as t
import path from '../../core/path'
import base from '../../core/stash'


class LocalFileInfo(base.FileInfo):
  pass


class LocalStash(base.Stash):
  pass


class LocalStashBuilder(base.StashBuilder):
  pass


class LocalStashServer(base.StashServer):

  def __init__(self, session):
    base.StashServer.__init__(self, session)

    location = session.config.get('stashes.location', None)
    if not location:
      location = path.expanduser('~/.craftr/stashes')
    self._location = location

  def can_create_new_stashes(self):
    directory = self._location
    while not path.exists(directory):
      directory = path.dir(directory)
    if not path.isdir(directory):
      print('>> not a directory:', directory)
      return False
    return os.access(directory, os.W_OK)

  def new_stash(self, key: str) -> LocalStashBuilder:
    raise NotImplementedError

  def find_stash(self, key: str) -> t.Optional[LocalStash]:
    return None


exports = LocalStashServer
