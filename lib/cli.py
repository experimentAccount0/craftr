# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import click
import nodepy
import ninja from './ninja'

VERSION = '1.0.0-nodepy-alpha'
MIN_NINJA_VERSION = '1.7.2'


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Print the version and exit.')
@click.option('--install-ninja', is_flag=True, help='Interactively install Ninja.')
@click.pass_context
def main(ctx, version, install_ninja):
  if version:
    print(VERSION)
    ctx.exit()
  if install_ninja:
    ninja.interactive_install()
    ctx.exit()
  if ctx.invoked_subcommand is None:
    print(ctx.get_help())
    ctx.exit()


@main.command()
@click.argument('file', default='Craftrfile.py')
@click.pass_context
def gen(ctx, file):
  """
  Generate the build manifest.
  """

  ninja_version = ninja.get_version()
  if not ninja_version:
    ctx.fail('Ninja could not be found, use "craftr --install-ninja" or '
      'download from https://github.com/ninja-build/ninja/releases')
  if ninja_version < MIN_NINJA_VERSION:
    ctx.fail('Ninja has version "{}", but minimum version required is "{}".\n  '
      'Use "craftr --install-ninja" or download from '
      'https://github.com/ninja-build/ninja/releases'
      .format(ninja_version, MIN_NINJA_VERSION))

  module = require.exec_main(file, current_dir='.')


@main.command()
def regen():
  """
  Generate based on previous settings.
  """

  pass


@main.command()
def build():
  """
  Run the build process.
  """

  pass


if require.main == module:
  main()
