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

import contextlib
import json
import typing as t
import * from 'craftr'
import msvcdet from 'craftr/lib/msvcdet'
import {NamedObject} from 'craftr/lib/types'


class MsvcToolkit(NamedObject):
  """
  Similar to a #msvcdet.MsvcInstallation, this class represents an MSVC
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
  _cl_version: str = None

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
    return cls(**data)

  @classmethod
  def from_config(cls):
    installations = msvcdet.MsvcInstallation.list()
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
    json.dump(self.asdict(), file)

  @property
  def key_info(self):
    return (self.version, self.arch, self.platform_type, self.sdk_version)

  @property
  def csc_version(self):
    pass


toolkit = MsvcToolkit.from_config()
