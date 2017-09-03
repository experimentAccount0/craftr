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
Detect MSVC installations on the current system (Windows only).
"""

__all__ = ['MsvcInstallation']

import json
import operator
import os
import functools
import subprocess
import sys
import typing as t
import platform from '../platform'
import shell from '../shell'
import {NamedObject} from '../types'


class MsvcInstallation(NamedObject):
  """
  Represents an MSVC installation directory.
  """

  version: int
  directory: str

  @property
  @functools.lru_cache()
  def vcvarsall(self):
    """
    Generates the path to the `vcvarsall.bat`.
    """

    if self.version >= 2017:
      return os.path.join(self.directory, 'VC', 'Auxiliary', 'Build', 'vcvarsall.bat')
    else:
      return os.path.join(self.directory, 'VC', 'vcvarsall.bat')

  @functools.lru_cache()
  def environ(self, arch=None, platform_type=None, sdk_version=None):
    """
    Executes the `vcvarsall.bat` of this installation with the specified
    *arch* and returns the environment dictionary after that script
    initialized it. If *arch* is omitted, it defaults to the current
    platform's architecture.

    If the specified architecture is incorrect or anything else happens that
    results in the `vcvarsall.bat` to not update the environment, a
    #ValueError is raised.

    If the `vcvarsall.bat` can not be exeuted, #subprocess.CalledProcessError
    is raised.
    """

    arch = platform.arch
    if arch == 'x86_64':
      arch = 'x86_amd64'

    cmd = [self.vcvarsall, arch]
    if platform_type:
      cmd.append(platform_type)
    if sdk_version:
      cmd.append(sdk_version)

    key = 'JSONOUTPUTBEGIN:'
    pyprint = 'import os, json; print("{}" + json.dumps(dict(os.environ)))'\
      .format(key)

    cmd = shell.join(cmd + [shell.safe('&&'), sys.executable, '-c', pyprint])
    output = subprocess.check_output(cmd, shell=True).decode()

    key = 'JSONOUTPUTBEGIN:'
    env = json.loads(output[output.find(key) + len(key):])
    if env == os.environ:
      content = output[:output.find(key)]
      raise ValueError('failed: ' + cmd + '\n\n' + content)

    return env

  @classmethod
  @functools.lru_cache()
  def list(cls):
    """
    List all available MSVC installations.
    """

    # Check all VS_COMNTOOLS environment variables.
    results = []
    for key, value in os.environ.items():
      if not (key.startswith('VS') and key.endswith('COMNTOOLS')):
        continue
      try:
        ver = int(key[2:-9])
      except ValueError:
        continue

      # Clean up the directory name.
      value = value.rstrip('\\')
      if not value or not os.path.isdir(value):
        continue
      if os.path.basename(value).lower() == 'tools':
        # The VS_COMNTOOLS variable points to the Common7\Tools
        # subdirectory, usually.
        value = os.path.dirname(os.path.dirname(value))

      results.append(cls(version=ver, directory=value))

    have_versions = set(x.version for x in results)

    # Special handling for MSVC 2017.
    # TODO: Can MSVC 2017 be installed in an alternative location?
    if 2017 not in have_versions:
      programfiles = os.getenv('ProgramFiles(x86)', '') or os.getenv('ProgramFiles', '')
      if programfiles:
        vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Community')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Professional')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Enterprise')
        if os.path.isdir(vspath):
          results.append(cls(2017, vspath))

    # TODO: Special handling for newer MSVC versions?

    return sorted(results, key=operator.attrgetter('version'), reverse=True)


def main():
  if not MsvcInstallation.list():
    print('no MSVC installations could be detected.', file=sys.stderr)
    sys.exit(1)
  for inst in MsvcInstallation.list():
    print('- %4d: %s' % (inst.version, inst.directory))


if require.main == module:
  main()
