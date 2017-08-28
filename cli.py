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
min_version = module.package.json['engines']['python'][2:]
if sys.version < min_version:
  print('fatal: Craftr requires CPython {} or higher'.format(min_version))
  sys.exit(1)

import click
import configparser
import functools
import nodepy
import operator
import sys
import context from './context'
import path from './core/path'
import _graph from './lib/graph'
import {Session} from './core/session'

craftr_main = require('./main', exports=False).namespace

VERSION = module.package.json['version']


def load_config(filename, format):
  """
  Loads a configuration file. *format* can be either `'toml'` or `'python'`.
  """

  config = craftr_main.exports.config
  if format == 'toml':
    if path.isfile(filename):
      config.read(filename)
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
  print(*args, **kwargs)


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
@click.option('-d', '--define', metavar='KEY=VALUE', multiple=True,
  help='Specify a KEY=VALUE pair to insert into the configuration.')
@click.pass_context
def main(ctx, build_directory, file, config, debug, release, target,
         arch, backend, define):
  """
  The Craftr build system.
  """

  if debug:
    target = 'debug'
  elif release:
    target = 'release'

  # Create a new session object and expose it to the Craftr API.
  session = Session(target=target, arch=arch)
  craftr_main.exports = context.BuildContext(session)

  # Load the configuration files.
  load_config(path.expanduser('~/.craftr/config.toml'), format='toml')
  load_config(path.expanduser('~/.craftr/config.py'), format='python')
  load_config('./.craftrconfig.toml', format='toml')
  load_config('./.craftrconfig.py', format='python')
  for string in define:
    key, sep, value = string.partition('=')
    if not sep:
      print_err('fatal: invalid value for -d,--define: {!r}'.format(string))
      sys.exit(1)
    if value == '':
      session.config.pop(key, None)
    else:
      session.config[key] = value

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
  # module with the cell stack in the Craftr session.
  def event_handler(event_name, data):
    if event_name in (nodepy.Context.Event_Enter, nodepy.Context.Event_Leave):
      module = data
      if module.package:
        name = module.package.json['name']
        if event_name == nodepy.Context.Event_Enter:
          directory = module.package.directory
          version = module.package.json.get('version', '1.0.0')
          print("ENTER", name)
          session.enter_cell(name, directory, version)
        else:
          print("LEAVE", name)
          session.leave_cell(name)

  session.enter_cell('__main__', path.cwd(), '1.0.0')
  require.context.event_handlers.append(event_handler)
  try:
    # For the current project, the default cell is __main__. If the Craftrfile
    # is embedded in a Node.py package, that namespace will be automatically
    # obtained when the module is loaded (due to the event handler that we
    # just registered).
    require.exec_main(file, current_dir=path.cwd())
  finally:
    require.context.event_handlers.remove(event_handler)
    session.leave_cell('__main__')

  ctx.obj = {'session': session}


@main.command()
@pass_session
def build(session):
  """
  Execute the build.
  """

  session.translate_targets()
  try:
    session.build.build([])
  finally:
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
