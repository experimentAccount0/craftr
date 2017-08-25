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
"""
A small tool to merge multiple JAR files into one.
"""

import sys
if sys.version < '3.6':
  raise EnvironmentError("Need CPython3.6 or newer")

import click
import contextlib
import os
import shutil
import subprocess
import tempfile


@contextlib.contextmanager
def temporary_directory():
  directory = tempfile.mkdtemp()
  try:
    yield directory
  finally:
    shutil.rmtree(directory)


def parse_manifest(fp):
  """
  Parses a Java manifest file.
  """

  for line in fp:
    if ':' not in line: continue
    yield line.rstrip().partition(':')[::2]


def write_manifest(fp, data):
  """
  Writes a Java manifest file.
  """

  for key, value in data.items():
    fp.write('{}: {}\n'.format(key, value))


@click.command()
@click.argument('jars', nargs=-1)
@click.option('-o', '--output', required=True)
@click.option('-v', '--verbose', is_flag=True)
@click.option('--jar-command', default='jar', help='The JAR command name.')
@click.option('--main-class', help='The JAR\'s new Main-Class.')
def main(jars, output, verbose, jar_command, main_class):
  """
  Merge multiple JAR files into one. Only the following manifest properties
  are maintained:

  * Class-Path (join)

  Additionally, the following manifest properties are automatically set
  or influenced by command-line options:

  * Manifest-Version: 1.0
  * Main-Class

  IMPORTANT: Currently this command does not check when files form the JARs
  collide. A JAR listed later on the command-line may overwrite a file from
  a previously expanded JAR file.
  """

  if not jars:
    print('fatal: no input files', file=sys.stderr)
    sys.exit(1)

  output = os.path.abspath(output)
  v = 'v' if verbose else ''

  # A dictionary that keeps track of the data from the manifests.
  manifest = {'Manifest-Version': '1.0'}

  # Unpack the JAR files into the temporary directory.
  with temporary_directory() as dirname:
    manifest_fn = os.path.join(dirname, 'META-INF', 'MANIFEST.MF')

    for jar_fn in jars:
      jar_fn = os.path.abspath(jar_fn)
      subprocess.check_call([jar_command, '-xf' + v, jar_fn], cwd=dirname)

      # Merge the manifest from that JAR.
      with open(manifest_fn) as fp:
        for key, value in parse_manifest(fp):
          if key == 'Class-Path':
            # Extend the class-path.
            manifest[key] = manifest.get(key, '') + ' ' + value

    if main_class:
      manifest['Main-Class'] = main_class

    with open(manifest_fn, 'w') as fp:
      write_manifest(fp, manifest)

    subprocess.check_call([jar_command, '-cfm' + v, output, manifest_fn, '.'], cwd=dirname)


if require.main == module:
  main()
