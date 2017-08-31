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
import os
import sys
import {Session} from './core/session'
import {Configuration} from './lib/config'
import trick from './lib/trick'
import platform from './lib/platform'


def load_config(config, filename, format):
  filename = os.path.expanduser(filename)
  if format == 'toml':
    with contextlib.suppress(FileNotFoundError):
      config.read(filename)
  elif format == 'python':
    try:
      module = require(filename, current_dir=os.getcwd(), exec_=False, exports=False)
    except require.ResolveError as e:
      if e.request.name != filename:
        raise
    else:
      module.namespace.config = config
      module.exec_()
  else:
    raise ValueError('invalid format: {!r}'.format(format))


def load_backend(prefix, name):
  request = './backends/{}/{}'.format(prefix, name)
  try:
    return require(request)
  except require.ResolveError as e:
    if e.request.name != request:
      raise
  return require(name)


@trick.group()
@trick.argument('-m', '--module', default='./Craftrfile.py')
@trick.argument('-d', '--define', action='append', default=[])
@trick.argument('--debug', action='store_true',
  help='Short form of --target=debug.')
@trick.argument('--release', action='store_true',
  help='Short form of --target=release.')
@trick.argument('--arch', default=platform.arch, metavar='ARCH',
  help='The build architecture. Defaults to "' + platform .arch + '". Note '
    'that usually only native code compilation is architecture dependent and '
    'if none such is used, the validity of this value will not be checked.')
@trick.argument('--target', metavar='TARGET',
  help='The build target (usually "debug" or "release"). Defaults to "debug".')
@trick.argument('--build-dir', '--build-directory', metavar='DIRNAME',
  help='The build output directory. Defaults to "build/{arch}-{target}".')
@trick.argument('--builder', metavar='BUILDER',
  help='The build backend to use. Defaults to "python".')
def main(subcommand, *, module, define, debug, release, arch, target,
         build_dir, builder):
  """
  The Craftr build system.
  """

  if sum(map(bool, (debug, release, target))) > 1:
    print('fatal: --target, --debug and --release can not be combined.', file=sys.stderr)
    return 1
  if debug:
    target = 'debug'
  elif release:
    target = 'release'

  arch = arch or platform.arch
  target = target or 'debug'
  build_dir = build_dir or os.path.join('build', arch + '-' + target)

  # Load the configuration files.
  config = Configuration(props={
    'platform': platform.name, 'arch': arch, 'target': target})
  load_config(config, '~/.craftr/config.toml', 'toml')
  load_config(config, '~/.craftr/config.py', 'python')
  load_config(config, './.craftrconfig.toml', 'toml')
  load_config(config, './.craftrconfig.py', 'python')
  for string in define:
    key, sep, value = string.partition('=')
    if not sep:
      print('fatal: invalid value for -d,--define: {!r}'.format(string), file=sys.stderr)
      return 1
    if value.lower() in ('off', 'false'):
      value = False
    elif value.lower() in ('on', 'true'):
      value = True
    if value == '':
      config.pop(key, None)
    else:
      config[key] = value

  # Load the builder  implementation.
  builder = builder or config.get('build.backend', 'python')
  builder = load_backend('build', builder)()

  # TODO: Extend the 'trick' module with a per-invokation context that can
  #       be accessed from the wrapped functions.
  global session
  session = Session(config, builder, arch, target, build_dir)
  session.main_module_name = module

  if not subcommand:
    print('fatal: missing subcommand', file=sys.stderr)
    sys.exit(1)


@main.command()
def generate():
  """
  Execute the "generate" procedure of the build backend. The native Python
  backend does not require this step.
  """

  session.builder.generate(session)


@main.command()
@trick.argument('targets', nargs='*')
def build(targets):
  """
  Execute the "build" procedure of the build backend.
  """

  session.builder.build(session, targets)


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
  sys.exit(main())
