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

import collections
import os
import requests
import shutil
import subprocess
import sys
import tempfile
import zipfile

logger = require('../logger')

_platform = require('../platform')
_ninja_suffix = '.exe' if _platform.WINDOWS else ''
_ninja_dist = {_platform.WINDOWS: 'win', _platform.LINUX: 'linux',
               _platform.MACOS: 'mac'}[True]
_ninja_bin = os.path.join(__directory__, 'bin', 'ninja' + _ninja_suffix)

NinjaInfo = collections.namedtuple('NinjaInfo', 'bin version')


def ninja_version():
  """
  Checks the locally installed Ninja version first, then the globally installed
  Ninja version. Returns the command that did not error and the Ninja version
  number. Raises #FileNotFoundError if Ninja is not available.
  """

  choices = [_ninja_bin, 'ninja']
  for command in choices:
    try:
      output = subprocess.check_output([command, '--version'])
    except FileNotFoundError:
      continue
    return NinjaInfo(command, output.decode().rstrip())
  raise FileNotFoundError('ninja')


def download_ninja(version='1.7.2', dest_dir=None, verbose=False):
  """
  Downloads Ninja from the GitHub releases and unpacks it into *dest_dir*. If
  the *dest_dir* is not specified, it will be unpacked into the `bin/` directory
  of this module.
  """

  if not dest_dir:
    dest_dir = os.path.dirname(_ninja_bin)
    dest_fn = _ninja_bin
  else:
    dest_fn = os.path.join(dest_dir, 'ninja' + _ninja_suffix)

  if not os.path.isdir(dest_dir):
    os.makedirs(dest_dir)

  url = 'https://github.com/ninja-build/ninja/releases/download/v{}/ninja-{}.zip'
  url = url.format(version, _ninja_dist)
  if verbose:
    logger.info("Downloading Ninja v{} ...".format(version))
    logger.info("  from %[magenta][{}]".format(url))
    logger.info("  to   %[cyan][{}]".format(dest_fn))

  response = requests.get(url)
  response.raise_for_status()
  with tempfile.NamedTemporaryFile(mode='wb', delete=False) as fp:
    for chunk in response.iter_content(4098):
      fp.write(chunk)
    fp.close()
    try:
      with zipfile.ZipFile(fp.name) as zip:
        src = zip.read('ninja' + _ninja_suffix)
        with open(dest_fn, 'wb') as out:
          out.write(src)
    finally:
      os.remove(fp.name)

  if verbose:
    logger.info("Ninja v{} downloaded.".format(version))

  return dest_fn


if require.main == module:
  try:
    path, version = ninja_version()
  except FileNotFoundError:
    download_ninja(verbose=True)
  else:
    print("Ninja v{} found ({})".format(version, path))
