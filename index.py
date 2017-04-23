# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.
"""
When this file is #require()d from another Node.py module, the Craftr
command-line arguments are automatically parsed and only then will the
normal execution continue.
"""

craftr = require('./api')
path = require('./path')
shell = require('./shell')
logger = require('./logger')

import atexit
import argparse
import os
import sys
import textwrap

def main():
  """
  Craftr is a general purpose build-system built on Node.py.

      https://github.com/craftr-build/craftr

  If ACTION is specified, it must be one of the following values:

    \b
    * build: switch to the build directory and run the build process)
    * clean: switch to the build directory and clean all or the
      specified targets.
    * export: proceed to execute the build script and export the
      build data.
    * reexport: similar to `export`, but takes all build options specified
      during the previous export into account.
    * run: the default action if none is specified, only run the build
      script without exporting build information.

  One or more TARGET parameters can only be specified for the `build`
  and `clean` actions. They must be the names of targets to build or
  clean.

  KEY=VALUE pairs can always be specified and will be copied into the
  #craftr.options dictionary. If the =VALUE part is omitted, the value of
  the specified KEY will be set to the string "true". If only the VALUE
  part is omitted (thus, the format is KEY= ), the option will be
  removed from the #craftr.options dictionary.
  """

  prog = path.base(sys.argv[0])
  usage = '{} [ACTION] [TARGET ...] [KEY=VALUE ...]'.format(prog)

  help_text = textwrap.dedent(main.__doc__)
  if require.main.namespace.__doc__:
    help_text = '{}\n\n{}\n\n{}'.format(require.main.namespace.__doc__, '='*60, help_text)
  help_text = textwrap.indent(help_text, '  ')

  parser = argparse.ArgumentParser(description=help_text, usage=usage,
      formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('-b', '--builddir')
  parser.add_argument('-B', '--backend')
  parser.add_argument('-t', '--buildtype')
  parser.add_argument('options', nargs='*')
  args = parser.parse_args()

  # If the first argument is not a KEY=VALUE pair.
  action = 'run'
  if args.options and '=' not in args.options[0]:
    action = args.options.pop(0)
  if action not in ('run', 'export', 'reexport', 'build', 'clean'):
    craftr.error('ACTION must be one of run, export, reexport, build or clean')

  # Propagate the specified action and build directory and load the cache.
  craftr.action = action
  if args.builddir:
    craftr.builddir = args.builddir
  craftr.load_cache()

  # Re-use the options of the previous export when using 'reexport'.
  if action == 'reexport':
    if 'options' in craftr.cache:
      logger.info('reusing previous build options:')
      for key, value in craftr.cache['options'].items():
        logger.info('  {}={}'.format(key, value))
      craftr.options.update(craftr.cache['options'])
    if not args.backend and 'backend' in craftr.cache:
      args.backend = craftr.cache['backend']
      logger.info('reusing previous backend: {}'.format(args.backend))
    if not args.buildtype and 'buildtype' in craftr.cache:
      args.buildtype = craftr.cache['buildtype']
      logger.info('reusing previous buildtype: {}'.format(args.buildtype))

  if not args.buildtype:
    args.buildtype = 'develop'

  # Propagate the backend now (after eventually re-using the option from
  # the previous export).
  if args.backend:
    craftr.backend = args.backend
  if args.buildtype:
    if args.buildtype not in ('debug', 'develop', 'release'):
      craftr.error('invalid buildtype: {!r}'.format(args.buildtype))
    craftr.buildtype = args.buildtype

  # Parse all other arguments into options and target names.
  targets = []
  for option in args.options:
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
      targets.append(option)

  if action in ('build', 'clean'):
    os.chdir(craftr.builddir)
    args = ['ninja']
    if action == 'clean':
      args += ['-t', 'clean']
    args += targets
    ret = shell.run(args, check=False).returncode
    sys.exit(ret)

  if targets:
    craftr.error('action {!r} does not expected targets: {}'.format(action, targets))

exports = craftr
main()

@atexit.register
def finalize_action():
  if craftr.action in ('export', 'reexport'):
    craftr.export()
    craftr.save_cache()
