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

import sys
if sys.version < '3.6':
  print('fatal: Craftr requires CPython 3.6 or higher')
  sys.exit(1)

import click
import configparser
import functools
import nodepy
import operator
import sys
import api from './api'
import path from './core/path'
import {Session, compute_action_key} from './core/buildgraph'
import _graph from './core/graph'

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
      require(filename, current_dir=path.cwd())
    except require.ResolveError as e:
      if e.request.name != filename:
        raise
  else:
    raise ValueError('invalid format: {!r}'.format(format))


def print_err(*args, **kwargs):
  kwargs.setdefault('file', sys.stderr)


def pass_session(f):
  @click.pass_context
  @functools.wraps(f)
  def wrapper(ctx, *args, **kwargs):
    return ctx.invoke(f, ctx.obj['session'], *args, **kwargs)
  return wrapper


@click.group()
@click.option('-b', '--build-directory', metavar='DIRNAME',
  help='The build directory.')
@click.option('-f', '--file', metavar='FILENAME', default='Craftrfile.py',
  help='The build script to execute.')
@click.option('-c', '--config', metavar='FILENAME', default='.craftrconfig',
  help='The Craftr configuration file.')
@click.option('--debug', is_flag=True, help='Short form of --target=debug')
@click.option('--release', is_flag=True, help='Short form of --target=release')
@click.option('--arch', metavar='ARCH', default=None,
  help='The target architecture to build for.')
@click.option('--target', metavar='TARGET', default='debug',
  help='The build target (usually "debug" or "release").')
@click.option('--backend', metavar='BACKEND',
  help='Name of the build backend. Defaults to "python"')
@click.pass_context
def main(ctx, build_directory, file, config, debug, release, target,
         arch, backend):
  """
  The Craftr build system.
  """

  if debug:
    target = 'debug'
  elif release:
    target = 'release'

  # Create a new session object and expose it to the Craftr API.
  session = Session(target=target, arch=arch)
  api.local.session = session

  # Load the configuration files.
  load_config(path.expanduser('~/.craftr/config.toml'), format='toml')
  load_config(path.expanduser('~/.craftr/config.py'), format='python')
  load_config('./.craftrconfig.toml', format='toml')
  load_config('./.craftrconfig.py', format='python')

  # Determine the build directory.
  if not build_directory:
    build_directory = 'target/{}-{}'.format(session.arch, session.target)
  session.build_directory = build_directory

  # Load the backend.
  if not backend:
    backend = session.config.get('build.backend', 'python')
  try:
    backend_class = require('./backends/build/' + backend)
  except require.ResolveError:
    backend_class = require(backend, current_dir=path.cwd())
  session.build = backend_class(session)

  # Load the stash server.
  stashes = session.config.get('stashes.backend', None)
  if stashes:
    try:
      stashes_class = require('./backends/stashes/' + stashes)
    except require.ResolveError:
      stashes_class = require(stashes, current_dir=path.cwd())
    session.stashes = stashes_class(session)

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
    require.exec_main(file, current_dir=path.cwd())
  finally:
    require.context.event_handlers.remove(event_handler)
    session.leave_scope('__main__')

  ctx.obj = {'session': session}


@main.command()
@pass_session
def build(session):
  """
  Execute the build.
  """

  session.translate_targets()
  session.build.build([])
  session.build.finalize()


@main.command()
@pass_session
def clean(session):
  """
  Clean the build directory.
  """

  session.translate_targets()
  session.build.clean([])


@main.command()
@click.option('--targets', is_flag=True, help='Visualize targets. This is the default')
@click.option('--actions', is_flag=True, help='Visualiez actions.')
@click.option('-o', '--output', metavar='FILENAME', help='Output filename.')
@pass_session
def dotviz(session, targets, actions, output):
  """
  Generate a DOT visualization.
  """

  if not targets and not actions:
    targets = True
  if targets and actions:
    print_err('Error: --targets and --actions can not be combined')
    sys.exit(1)
  if targets:
    def text_of(target):
      lines = [type(target).__name__, target.identifier]
      return '\\n'.join(lines)
    graph = session.target_graph
  elif actions:
    def text_of(action):
      target = action.source()
      lines = [type(target).__name__ + '({})'.format(target.identifier),
               type(action).__name__ + '({})'.format(action.name)]
      if action.pure:
        lines.append(compute_action_key(action)[:10] + '...')
      return '\\n'.join(lines)
    session.translate_targets()
    graph = session.action_graph
  else:
    raise RuntimeError

  if not output:
    dest = sys.stdout
    do_close = False
  else:
    dest = open(output, 'w')
    do_close = True

  try:
    _graph.dotviz(dest, graph, text_of=text_of)
  finally:
    if do_close:
      dest.close()


if require.main == module:
  #try:
  main(standalone_mode=False)
  #except click.Abort:
  #  sys.exit(127)
