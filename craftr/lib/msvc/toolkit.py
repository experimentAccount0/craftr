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
Options:

- msvc.version (int)
- msvc.arch (str)
- msvc.platform_type (str)
- msvc.sdk_version (str)
- msvc.cache (bool)
"""

__all__ = ['MsvcToolkit']

import contextlib
import functools
import json
import os
import re
import subprocess
import tempfile
import typing as t
import * from 'craftr'
import {MsvcInstallation} from './finder'
import {override_environ} from '../shell'
import {NamedObject} from '../types'


class AsDictJSONEncoder(json.JSONEncoder):

  def default(self, obj):
    if hasattr(obj, '_asdict'):
      return obj._asdict()
    elif hasattr(obj, 'asdict'):
      return obj.asdict()
    return super().default(obj)


class ClInfo(NamedObject):

  version: str
  version_str: str
  target: str
  msvc_deps_prefix: str = None
  assembler_program: str
  link_program: str
  lib_program: str

  VERSION_REGEX = re.compile(r'compiler\s+version\s*([\d\.]+)\s*\w+\s*(x\w+)', re.I | re.M)

  @classmethod
  def from_program(cls, program, env=None):
    with override_environ(env or {}):
      version_output = subprocess.check_output(['cl'], stderr=subprocess.STDOUT).decode()
    match = cls.VERSION_REGEX.search(version_output)
    if not match:
      raise RuntimeError('ClInfo could not be detected from {!r}'
        .format(program))

    version = match.group(1)
    arch = match.group(2)

    # Determine the msvc_deps_prefix by making a small test. The
    # compilation will not succeed since no entry point is defined.
    deps_prefix = None
    with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as fp:
      fp.write(b'#include <stddef.h>\n')
      fp.close()
      command = [program, '/Zs', '/showIncludes', fp.name]
      try:
        with override_environ(env or {}):
          output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode()
      finally:
        os.remove(fp.name)

      # Find the "Note: including file:" in the current language. We
      # assume that the structure is the same, only the words different.
      # After the logo output follows the filename followed by the include
      # notices.
      for line in output.split('\n'):
        if 'stddef.h' in line:
          if 'C1083' in line or 'C1034' in line:
            # C1083: can not open include file
            # C1034: no include path sep
            msg = 'MSVC can not compile a simple C program.\n  Program: {}\n  Output:\n\n{}'
            raise ToolDetectionError(msg.format(program, output))
          match = re.search('[\w\s]+:[\w\s]+:', line)
          if match:
            deps_prefix = match.group(0)

    return cls(
      version = version,
      version_str = version_output.split('\n', 1)[0].strip(),
      target = arch,
      msvc_deps_prefix = deps_prefix,
      assembler_program = 'ml64' if arch == 'x64' else 'ml',
      link_program = 'link',
      lib_program = 'lib'
    )


class MsvcToolkit(NamedObject):
  """
  Similar to a #MsvcInstallation, this class represents an MSVC
  installation, however it is fixed to a specific target architecture and
  Windows SDK, etc. Additionally, it can be saved to and loaded from disk.
  """

  CACHEFILE = path.join(session.builddir, '.config', 'msvc-toolkit.json')

  version: int
  directory: str
  environ: dict
  arch: str
  platform_type: str = None
  sdk_version: str = None
  _csc_version: str = None
  _vbc_version: str = None
  _cl_info: ClInfo = None

  @classmethod
  def from_installation(cls, inst, arch=None, platform_type=None, sdk_version=None):
    environ = inst.environ(arch, platform_type, sdk_version)
    return cls(inst.version, inst.directory, environ, arch, platform_type, sdk_version)

  @classmethod
  def from_file(cls, file):
    if isinstance(file, str):
      with open(file, 'r') as fp:
        return cls.from_file(fp)
    data = json.load(file)
    if data.get('_cl_info'):
      data['_cl_info'] = ClInfo(**data['_cl_info'])
    return cls(**data)

  @classmethod
  @functools.lru_cache()
  def from_config(cls):
    installations = MsvcInstallation.list()
    if not installations:
      raise RuntimeError('Unable to detect any MSVC installation. Is it installed?')

    version = config.get('msvc.version')
    if version:
      version = int(version)
      install = next((x for x in installations if x.version == version), None)
      if not install:
        raise RuntimeError('MSVC version "{}" is not available.'.format(version))
    else:
      install = installations[0]
      version = install.version

    arch = config.get('msvc.arch', session.arch)
    platform_type = config.get('msvc.platform_type')
    sdk_version = config.get('msvc.sdk_version')
    cache_enabled = config.get('msvc.cache', True)

    cache = None
    if cache_enabled:
      try:
        with contextlib.suppress(FileNotFoundError):
          cache = cls.from_file(cls.CACHEFILE)
      except json.JSONDecodeError as e:
        print('warning: could not load MsvcToolkit cache ({}): {}'
          .format(cls.CACHEFILE, e))

    key_info = (version, arch, platform_type, sdk_version)
    if not cache or cache.key_info != key_info:
      toolkit = cls.from_installation(install, arch, platform_type, sdk_version)
      if cache_enabled:
        toolkit.save(cls.CACHEFILE)
    else:
      toolkit = cache  # Nothing has changed

    if cache_enabled:
      session.finally_(lambda: toolkit.save(cls.CACHEFILE))

    return toolkit

  def save(self, file):
    if isinstance(file, str):
      path.makedirs(path.dir(file))
      with open(file, 'w') as fp:
        return self.save(fp)
    json.dump(self.asdict(), file, cls=AsDictJSONEncoder)

  @property
  def key_info(self):
    return (self.version, self.arch, self.platform_type, self.sdk_version)

  @property
  def csc_version(self):
    if not self._csc_version:
      with override_environ(self.environ):
        output = subprocess.check_output(['csc', '/version']).decode()
        self._csc_version = output.strip()
    return self._csc_version

  @property
  def cl_version(self):
    return self.cl_info.version

  @property
  def cl_info(self):
    if not self._cl_info:
      self._cl_info = ClInfo.from_program('cl', self.environ)
    return self._cl_info

  @property
  def vbc_version(self):
    if not self._vbc_version:
      with override_environ(self.environ):
        output = subprocess.check_output(['vbc', '/version']).decode()
        self._vbc_version = output.strip()
    return self._vbc_version

  @classmethod
  @functools.lru_cache()
  def get():
    toolkit = MsvcToolkit.from_config()
    print('MSVC v{}-{} ({})'.format(
      toolkit.version, toolkit.arch, toolkit.directory))
    return toolkit
