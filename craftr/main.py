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
import sys
import trick from './lib/trick'
import platform from './lib/platform'
import {Session} from './core/session'


@trick.group()
@trick.argument('--arch', default=platform.arch, metavar='ARCH',
  help='The build architecture. Defaults to "' + platform .arch + '". Note '
    'that usually only native code compilation is architecture dependent and '
    'if none such is used, the validity of this value will not be checked.')
@trick.argument('--target', default='debug', metavar='TARGET',
  help='The build target (usually "debug" or "release"). Defaults to "debug".')
@trick.argument('--build-dir', '--build-directory', metavar='DIRNAME',
  help='The build output directory. Defaults to "build/{arch}-{target}".')
def main(subcommand, *, arch, target, build_dir):
  """
  The Craftr build system.
  """

  # TODO: Extend the 'trick' module with a per-invokation context that can
  #       be accessed from the wrapped functions.

  builder = require('./backends/build/python')()

  global session
  arch = arch or platform.arch
  target = target or platform.target
  build_dir = build_dir or os.path.join('build', arch + '-' + target)
  session = Session(arch, target, build_dir, builder=builder)



@main.command()
def generate():
  """
  Execute the "generate" procedure of the build backend. The native Python
  backend does not require this step.
  """

  session.builder.generate(session, [])


@main.command()
def build():
  """
  Execute the "build" procedure of the build backend.
  """

  session.builder.build(session, [])


@main.command()
@trick.argument('--actions', action='store_true', help='Visualize the action '
  'graph instead of the target graph.')
def viz(actions):
  """
  Generate a DOT graph from the target- or action-graph.
  """

  session.load_targets()
  graph = session.create_target_graph()
  if actions:
    graph.translate()
    graph = session.create_action_graph()

  graph.dotviz(sys.stdout)


if require.main == module:
  main()
