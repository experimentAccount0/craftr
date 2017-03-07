# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
This file will be invoked by the Craftr command-line in the local installation
of Craftr, and thus has access to the same API that the Craftrfile will be
executed with.
"""

import click
import logging
import nodepy
import os
import subprocess
import sys

craftr = require('./index')
logger = require('@craftr/logger')
ninja = require('./lib/ninja')
download_ninja = require('./lib/ninja/get-ninja')
path = require('./lib/path')


@click.group()
@click.option('-v', '--verbose', is_flag=True)
def main(verbose):
  if verbose:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)
  try:
    craftr.ninja = ninja.version()
  except FileNotFoundError:
    logger.warning('No ninja executable found. Attempting to install ...')
    ninja.download(verbose=True)
    craftr.ninja = ninja.version()

  logger.debug('Found ninja v{} (%[cyan][{}])'.format(
      craftr.ninja.version, craftr.ninja.bin))


@main.command()
@click.argument('script', required=False)
@click.argument('options', nargs=-1)
@click.option('-b', '--build-dir', default='build')
def generate(script, options, build_dir):
  if script == '-' or not script:
    script = 'Craftrfile'

  path.makedirs(build_dir)
  craftr.build_dir = build_dir
  require.context.register_index_file('Craftrfile')

  # Parse options and fill them into the context options.
  for option in options:
    if '=' not in option:
      key, value = option, 'true'
    else:
      key, value = option.split('=', 1)
    if not value:
      craftr.options.pop(key, None)
    else:
      craftr.options[key] = value

  with require.hide_main():
    logger.info("Loading module '%[yellow][{}]'".format(script))
    require.exec_main(script, current_dir='.')

  ninja_manifest = path.join(build_dir, 'build.ninja')
  logger.info("Writing '%[cyan][{}]'".format(ninja_manifest))
  with open(ninja_manifest, 'w') as fp:
    context = ninja.ExportContext(craftr.ninja.version, craftr.build_dir)
    craftr.graph.export(ninja.NinjaWriter(fp), context, craftr.platform_helper)


@main.command()
@click.option('-b', '--build-dir', default='build')
def build(build_dir):
  if not path.isdir(build_dir):
    logger.error("Directory '%[cyan][{}]' does not exist".format(build_dir))
    sys.exit(1)
  if not path.isfile(path.join(build_dir, 'build.ninja')):
    logger.error("No '%[cyan][build.ninja]' in directory '%[cyan][{}]'".format(build_dir))
    sys.exit(1)
  cmd = [craftr.ninja.bin]
  res = subprocess.call([cmd], cwd=build_dir)
  if res != 0:
    logger.error('Ninja returned with exit-code {}'.format(res))


if require.main == module:
  main()
