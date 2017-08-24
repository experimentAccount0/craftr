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

import click
import configparser
import nodepy
import operator
import sys
import api from './api'
import path from './core/path'
import {Session, compute_action_key} from './core/buildgraph'
import {Graph, dotviz} from './core/graph'

VERSION = module.package.json['version']


def load_config(filename, format):
  """
  Loads a configuration file. *format* can be either `'toml'` or `'python'`.
  """

  if format == 'toml':
    if path.isfile(filename):
      api.session.config.read(filename)
  elif format == 'python':
    try:
      require(filename)
    except require.ResolveError as e:
      if e.request.name != filename:
        raise
  else:
    raise ValueError('invalid format: {!r}'.format(format))


@click.command(help="Craftr v{}".format(VERSION))
@click.option('-f', '--file', metavar='FILENAME', default='Craftrfile.py',
  help='The build script to execute.')
@click.option('-c', '--config', metavar='FILENAME', default='.craftrconfig',
  help='The Craftr configuration file.')
@click.option('--debug', is_flag=True, help='Short form of --target=debug')
@click.option('--release', is_flag=True, help='Short form of --target=release')
@click.option('--target', metavar='TARGET', default='debug',
  help='The build target (usually "debug" or "release").')
@click.option('--backend', metavar='BACKEND',
  help='Name of the build backend. Defaults to "python"')
@click.option('--dotviz-targets', metavar='FILENAME',
  help='Generate a DOT visualizaton of the target graph.')
@click.option('--dotviz-actions', metavar='FILENAME',
  help='Generate a DOT visualizaton of the action graph.')
def main(file, config, debug, release, target, backend,
         dotviz_targets, dotviz_actions):
  if debug:
    target = 'debug'
  elif release:
    target = 'release'

  # Create a new session object and expose it to the Craftr API.
  session = Session(target)
  api.local.session = session

  # Load the configuration files.
  load_config(path.expanduser('~/.craftr/config'), format='toml')
  load_config(path.expanduser('~/.craftr/config.py'), format='python')
  load_config('./.craftrconfig', format='toml')
  load_config('./.craftrconfig.py', format='python')

  # Load the backend.
  if not backend:
    backend = session.config.get('build.backend', 'python')
  try:
    backend_class = require(backend)
  except require.ResolveError:
    backend_class = require('./backends/' + backend)

  # Make sure that Node.py modules with a 'Craftrfile' can be loaded
  # using `require()` or `import ... from '...'`.
  require.context.register_index_file('Craftrfile')

  # This is a Node.py context event handler that synchronizes the current
  # module with the scope stack in the Craftr session.
  def event_handler(event_name, data):
    if event_name in (nodepy.Context.Event_Enter, nodepy.Context.Event_Leave):
      module = data
      if module.package:
        if event_name == nodepy.Context.Event_Enter:
          session.enter_scope(module.package.json['name'], module.package.directory)
        else:
          session.leave_scope(module.package.json['name'])

  session.enter_scope('__main__', path.cwd())
  require.context.event_handlers.append(event_handler)
  try:
    # For the current project, the default scope is __main__. If the Craftrfile
    # is embedded in a Node.py package, that namespace will be automatically
    # obtained when the module is loaded (due to the event handler that we
    # just registered).
    require.exec_main(file)
  finally:
    require.context.event_handlers.remove(event_handler)
    session.leave_scope('__main__')

  session.translate_targets()

  if dotviz_targets:
    do_visualize(dest=dotviz_targets, graph=session.target_graph)
  if dotviz_actions:
    def text_of(action):
      append = ''
      if action.pure:
        append = '\\n' + compute_action_key(action)[:10] + '...'
      return action.identifier + append
    do_visualize(dest=dotviz_actions, graph=session.action_graph, text_of=text_of)
  if dotviz_targets or dotviz_actions:
    return

  backend = backend_class(session)
  backend.build([])


def do_visualize(dest: str, graph: Graph, text_of = None) -> None:
  if text_of is None:
    text_of = operator.attrgetter('identifier')

  if dest in ('', '-'):
    dest = sys.stdout
    do_close = False
  else:
    dest = open(dest, 'w')
    do_close = True

  try:
    dotviz(dest, graph, text_of=text_of)
  finally:
    if do_close:
      dest.close()


if require.main == module:
  main()
