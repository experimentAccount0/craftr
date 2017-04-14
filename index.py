# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.
"""
When this file is #require()d from another Node.py module, the Craftr
command-line arguments are automatically parsed and only then will the
normal execution continue.
"""

craftr = require.symbols('./api')
path = require('./path')

import atexit
import argparse
import sys

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
    * run: the default action if none is specified, only run the build
      script without exporting build information.

  One or more TARGET parameters can only be specified for the `build`
  and `clean` actions. They must be the names of targets to build or
  clean.

  --KEY=VALUE pairs can always be specified and will be copied into the
  #craftr.options dictionary. If the =VALUE part is omitted, the value of
  the specified KEY will be set to the string "true". If only the VALUE
  part is omitted (thus, the format is --KEY= ), the option will be
  removed from the #craftr.options dictionary.
  """

  usage = '{} [ACTION] {{TARGET,--KEY=VALUE}}...'.format(path.base(sys.argv[0]))
  parser = argparse.ArgumentParser(usage=usage)
  parser.add_argument('action', nargs='?', choices={'build', 'clean', 'export', 'run'})
  parser.add_argument('options', nargs='...')
  args = parser.parse_args()

  craftr.options['action'] = args.action

  targets = []
  for option in args.options:
    if option in ('-h', '--help'):
      parser.print_help()
      sys.exit(0)
    if option.startswith('--'):
      key, sep, value = option[2:].partition('=')
      if not key:
        parser.error('invalid option: {!r}'.format(option))
      if sep and not value:
        craftr.options.pop(key, None)
      elif not sep:
        craftr.options[key] = 'true'
      else:
        craftr.options[key] = value

  if args.action in ('build', 'clean'):
    parser.error('build/clean currently not implemented')

# Add the currently executed module's documentation.
if require.main.namespace.__doc__:
  main.help = '{}\n\n{}\n\n{}'.format(require.main.namespace.__doc__, '='*60, main.help)

exports = craftr
main()

@atexit.register
def finalize_action():
  if craftr.option('action') == 'export':
    craftr.export()
