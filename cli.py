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
import api from './core/api'
import log from './core/log'
import path from './core/path'
import {VERSION, Session} from './core/graph'


@click.command(
  help="""
  Craftr v{}
  """.format(VERSION)
)
@click.option('-f', '--file', metavar='FILENAME', default='Craftrfile.py',
  help='The build script to execute.')
@click.option('-c', '--config', metavar='FILENAME', default='.craftrconfig',
  help='The Craftr configuration file.')
@click.option('--debug', is_flag=True, help='Short form of --target=debug')
@click.option('--release', is_flag=True, help='Short form of --target=release')
@click.option('--target', metavar='TARGET', default='debug',
  help='The build target (usually "debug" or "release").')
def main(file, config, debug, release, target):
  if debug:
    target = 'debug'
  elif release:
    target = 'release'

  # Create a new session object and expose it to the Craftr API.
  session = Session(target)
  api.local.session = session

  # Parse the configuration file.
  filename = path.expanduser('~/.craftrconfig')
  if path.isfile(filename):
    session.config.read(filename)
  if path.isfile(config):
    session.config.read(config)

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

  require.context.event_handlers.append(event_handler)
  try:
    # For the current project, the default scope is __main__. If the Craftrfile
    # is embedded in a Node.py package, that namespace will be automatically
    # obtained when the module is loaded (due to the event handler that we
    # just registered).
    with session.enter_scope_ctx('__main__', path.cwd()):
      require.exec_main(file)
  finally:
    require.context.event_handlers.remove(event_handler)


if require.main == module:
  main()
