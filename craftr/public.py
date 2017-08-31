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

import actions from './actions'
import {Action, ActionImpl} from './core/action'
import {Target, TargetImpl} from './core/target'
import {get_current_module} from './core/loader'
import {inherit_annotations, target_factory, AnnotatedTargetImpl} from './core/factory'
import path from './lib/path'
import {name as platform} from './lib/platform'

import werkzeug.local as _local

cell = _local.LocalProxy(lambda: get_current_module().cell)
session = _local.LocalProxy(lambda: require('./main').session)
config = _local.LocalProxy(lambda: session.config)


def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the cell
  base directory!).
  """

  if not parent:
    parent = require.context.current_module.directory
  return path.glob(patterns, parent, excludes)


def canonicalize(paths, parent = None):
  """
  Canonicalize a path or a list of paths. Relative paths are converted to
  absolute paths from the currently executed module's directory (NOT the
  curren Craftr module but the current Node.py module).
  """

  parent = parent or require.context.current_module.directory
  if isinstance(paths, str):
    return path.canonical(path.abs(paths, parent))
  else:
    return [path.canonical(path.abs(x, parent)) for x in paths]


def resolve(ref):
  """
  Resolve a target reference and return the #TargetImpl object.
  """

  return session.find_target(ref).impl


@target_factory
class gentarget(AnnotatedTargetImpl):

  commands: list
  environ: dict = None
  cwd: str = None
  explicit: bool = False

  def translate(self):
    self.action(
      actions.Commands,
      name = 'run',
      deps = self.target.transitive_deps(),
      commands = self.commands,
      environ = self.environ,
      cwd = self.cwd,
      explicit = self.explicit
    )
