# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.
"""
When this file is #require()d from another Node.py module, the Craftr
command-line arguments are automatically parsed and only then will the
normal execution continue.
"""

craftr = require('.')
path = require('./path')
shell = require('./shell')
logger = require('./logger')

import click
import json
import os
import sys
import textwrap

def load_project_cache():
  """
  Loads the `.CraftrProjectCache` and returns it.
  """

  if path.isfile('.CraftrProjectCache'):
    logger.debug('loading project cache ...')
    with open('.CraftrProjectCache') as fp:
      return json.load(fp)
  else:
    logger.debug('project cache does not exist')
  return {}

def save_project_cache():
  """
  Saves the #craftr.cache dictionary into the `.CraftrProjectCache` file.
  """

  with open('.CraftrProjectCache', 'w') as fp:
    logger.debug('saving project cache ...')
    json.dump(craftr.cache, fp)

def load_build_cache(builddir, error=False):
  """
  Loads the `.CraftrBuildCache` from the specified *builddir*.
  """

  filename = path.join(builddir, '.CraftrBuildCache')
  if os.path.isfile(filename):
    logger.debug('loading build cache ...')
    with open(filename) as fp:
      return json.load(fp)
  else:
    if error:
      craftr.error('"{}" does not exist'.format(filename))
    logger.debug('build cache does not exist')
  return {}

def save_build_cache(builddir):
  """
  Saves the #craftr.backend, #craftr.buildtype and #craftr.options into the
  specified *builddir*.
  """

  cache = {
    'backend': craftr.backend,
    'buildtype': craftr.buildtype,
    'options': craftr.options
  }
  filename = path.join(builddir, '.CraftrBuildCache')
  path.makedirs(path.dir(filename))
  with open(filename, 'w') as fp:
    logger.debug('saving build cache ...')
    json.dump(cache, fp)

def parse_options(options, error_remainders=True):
  """
  Given a list of command-line arguments that represent build options,
  parses them into #craftr.options. If *error_remainders* is #True, any
  arguments that are not in option format will cause a #craftr.Error to be
  raised, otherwise they will be returned in a list.
  """

  remainders = []
  for option in options:
    if option in ('-h', '--help'):
      parser.print_help()
      return sys.exit(0)
    if '=' in option:
      key, sep, value = option.partition('=')
      if not key:
        craftr.error('invalid option: {!r}'.format(option))
      if sep and not value:
        craftr.options.pop(key, None)
      elif not sep:
        craftr.options[key] = 'true'
      else:
        craftr.options[key] = value
    else:
      if error_remainders:
        craftr.error('not an option value: "{}"'.format(option))
      remainders.append(option)

  return remainders

@click.group()
def main():
  """
  Craftr is a general purpose build-system built on Node.py.

      https://github.com/craftr-build/craftr
  """

  pass

@main.command()
@click.argument('options', nargs=-1)
@click.option('-t', '--buildtype', type=click.Choice(craftr.buildtypes))
@click.option('-f', '--file', help='The build script to execute. Defaults to ./Craftrfile')
def run(options, buildtype, file):
  """
  Run the build script without exporting build information.
  """

  craftr.cache = load_project_cache()
  craftr.action = 'run'
  parse_options(options)
  if buildtype:
    craftr.buildtype = buildtype
  craftr.register_nodepy_extension()
  try:
    require.exec_main(file or './Craftrfile', current_dir=os.getcwd())
  finally:
    save_project_cache()

@main.command()
@click.argument('options', nargs=-1)
@click.option('-b', '--builddir', help='Alternate build directory.')
@click.option('-B', '--backend', help='Choose the build backend (defaults to ninja)')
@click.option('-t', '--buildtype', type=click.Choice(craftr.buildtypes))
@click.option('-f', '--file', help='The build script to execute. Defaults to ./Craftrfile')
@click.option('-r', '--reexport', is_flag=True, help='Load the options from the previous '
              'export step. Note that you can use the `reexport` command as a shortcut.')
def export(options, builddir, backend, buildtype, file, reexport):
  """
  Export build information.

  Executes the Craftr build script and export the project to the build
  directory. The information of the last exported build will be saved
  in a `.craftr` file in the current working directory.
  """

  craftr.action = 'export'
  craftr.cache = load_project_cache()

  if reexport and not builddir:
    builddir = craftr.cache.get('builddir')
  if not builddir:
    builddir = craftr.builddir

  if reexport:
    cache = load_build_cache(builddir)
    if cache['options']:
      logger.info('reusing previous build options:')
      for key, value in cache['options'].items():
        logger.info('  {}={}'.format(key, value))
      craftr.options.update(cache['options'])
    if not backend:
      backend = cache['backend']
      logger.info('reusing previous backend: {}'.format(backend))
    if not buildtype:
      buildtype = cache['buildtype']
      logger.info('reusing previous buildtype: {}'.format(buildtype))

  parse_options(options)
  if builddir:
    craftr.builddir = builddir
  if backend:
    craftr.backend = backend
  if buildtype:
    craftr.buildtype = buildtype

  file = file or './Craftrfile'
  logger.info('running build script: "{}"'.format(file))
  craftr.register_nodepy_extension()
  try:
    require.exec_main(file or './Craftrfile', current_dir=os.getcwd())
  finally:
    save_project_cache()
    save_build_cache(craftr.builddir)
  craftr.export()

@main.command()
@click.argument('options', nargs=-1)
@click.option('-b', '--builddir', help='Alternate build directory.')
@click.option('-B', '--backend', help='Choose the build backend (defaults to ninja)')
@click.option('-t', '--buildtype', type=click.Choice(craftr.buildtypes))
@click.option('-f', '--file', help='The build script to execute. Defaults to ./Craftrfile')
def reexport(options, builddir, backend, buildtype, file):
  """
  Export build information, taking previous build options into account.
  """

  return export(list(options) + ['--builddir', builddir, '--backend', backend,
      '--buildtype', buildtype, '--file', file, '--reexport'])

@main.command()
@click.argument('options', nargs=-1)
@click.option('-b', '--builddir', help='Alternate build directory. By default, '
              'the build directory previously exported to will be used.')
@click.option('-c', '--clean', is_flag=True, help='Clean the specified targets '
              'instead of building them. If no targets are specified, all '
              'targets are cleaned. Note that the `clean` subcommand is an '
              'alias for this flag.')
def build(options, builddir, clean):
  """
  Invoke the build process.

  You can specify zero, one or more targets that will be built explicitly.
  If none are specified, all default targets will be built.
  """

  craftr.action = 'clean' if clean else 'build'
  craftr.cache = load_project_cache()
  if not builddir:
    builddir = craftr.cache.get('builddir', craftr.builddir)
  if not os.path.isdir(builddir):
    craftr.error('build directory {!r} does not exist'.format(builddir))

  cache = load_build_cache(builddir, error=True)
  craftr.options.update(cache['options'])
  targets = parse_options(options, error_remainders=False)
  if clean:
    sys.exit(craftr.clean(builddir, targets))
  else:
    sys.exit(craftr.build(builddir, targets))

@main.command()
@click.argument('options', nargs=-1)
@click.option('-b', '--builddir', help='Alternate build directory. By default, '
              'the build directory previously exported to will be used.')
def clean(options, builddir):
  """
  Clean build products.
  """

  return build(list(options) + ['--builddir', builddir, '--clean'])

if require.main == module:
  try:
    main()
  except craftr.Error as exc:
    logger.error(str(exc))
    sys.exit(exc.code)
