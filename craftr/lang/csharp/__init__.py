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

__all__ = ['csharp_build', 'csharp_run']

import functools
import os
import re
import subprocess
import typing as t
import * from 'craftr'
import msvc from 'craftr/lib/msvc/toolkit'
import shell from 'craftr/lib/shell'
import {NamedObject} from 'craftr/lib/types'


class CscInfo(NamedObject):
  impl: str
  program: t.List[str]
  environ: dict
  version: str

  def __repr__(self):
    return '<CscInfo impl={!r} program={!r} environ=... version={!r}>'\
      .format(self.impl, self.program, self.version)

  def is_mono(self):
    # TODO: That's pretty dirty..
    return self.program != ['csc']

  @staticmethod
  @functools.lru_cache()
  def get():
    impl = config.get('csharp.impl', 'net' if platform == 'windows' else 'mono')
    if impl not in ('net', 'mono'):
      raise ValueError('unsupported csharp.impl={!r}'.format(impl))

    program = config.get('csharp.csc')
    if impl == 'net' and program:
      raise ValueError('csharp.csc not supported with csharp.impl={!r}'.format(impl))
    elif impl == 'net':
      program = 'csc'
    elif impl == 'mono':
      program = 'mcs'
    else: assert False

    program = shell.split(program)
    if impl == 'net':
      toolkit = msvc.MsvcToolkit.get()
      csc = CscInfo(impl, program, toolkit.environ, toolkit.csc_version)
    else:
      environ = {}
      if platform == 'windows':
        # On windows, the mono compiler is available as .bat file, thus we
        # need to run it through the shell.
        program = shell.shellify(program)
        # Also, just make sure that we can find some standard installation
        # of Mono.
        if match(arch, '*64'):
          monobin = path.join(os.getenv('ProgramFiles'), 'Mono', 'bin')
        else:
          monobin = path.join(os.getenv('ProgramFiles(x86)'), 'Mono', 'bin')
        environ['PATH'] = os.getenv('PATH') + path.pathsep + monobin

      # TODO: Cache the compiler version (like the MsvcToolkit does).
      with shell.override_environ(environ):
        version = subprocess.check_output(program + ['--version']).decode().strip()
      if impl == 'mono':
        m = re.search('compiler\s+version\s+([\d\.]+)', version)
        if not m:
          raise ValueError('Mono compiler version could not be detected from:\n\n  ' + version)
        version = m.group(1)

      csc = CscInfo(impl, program, environ, version)

    print('CSC v{}'.format(csc.version))
    return csc


class Csharp(AnnotatedTargetImpl):
  srcs: t.List[str]
  type: str
  dll_dir: str = None
  dll_name: str = None
  main: str = None
  extra_arguments: t.List[str] = None
  csc: CscInfo = None

  # TODO: More features for the C# target.
  #platform: str = None
  #win32icon
  #win32res
  #warn
  #checked

  def __init__(self, target, **kwargs):
    super().__init__(target, **kwargs)
    assert self.type in ('appcontainerexe', 'exe', 'library', 'module', 'winexe', 'winmdobj'), self.target
    if self.dll_dir:
      self.dll_dir = canonicalize(self.dll_dir, self.cell.builddir)
    else:
      self.dll_dir = self.cell.builddir
    self.dll_name = self.dll_name or (self.cell.name.split('/')[-1] + '-' + self.target.name + '-' + self.cell.version)
    self.csc = self.csc or CscInfo.get()

  @property
  def dll_filename(self):
    if self.type in ('appcontainerexe', 'exe', 'winexe'):
      suffix = '.exe'
    elif self.type == 'winmdobj':
      suffix = '.winmdobj'
    elif self.type == 'module':
      suffix = '.netmodule'
    elif self.type == 'library':
      suffix = '.dll'
    else:
      raise ValueError('invalid type: {!r}'.format(self.type))
    return path.join(self.dll_dir, self.dll_name) + suffix

  def translate(self):
    # TODO: Take C# libraries and maybe even other native libraries
    #       into account.
    deps = self.target.transitive_deps()
    modules = []
    references = []
    for dep in (x.impl for x in deps):
      if isinstance(dep, Csharp):
        if dep.type == 'module':
          modules.append(dep.dll_filename)
        else:
          references.append(dep.dll_filename)

    command = self.csc.program + ['-nologo', '-target:' + self.type]
    command += ['-out:' + self.dll_filename]
    if self.main:
      command.append('-main:' + self.main)
    if modules:
      command.append('-addmodule:' + ';'.join(modules))
    if references:
      command += ['-reference:' + x for x in reference]
    if self.extra_arguments:
      command += self.extra_arguments
    command += self.srcs

    mkdir = self.action(
      actions.Mkdir,
      name = 'mkdir',
      directory = self.dll_dir
    )
    self.action(
      actions.Commands,
      name = 'csc',
      deps = deps + [mkdir],
      environ = self.csc.environ,
      commands = [command],
      input_files = self.srcs,
      output_files = [self.dll_filename]
    )


class CsharpRun(AnnotatedTargetImpl):
  """
  At least under Windows+Mono, applications compiled with Mono should be run
  through the Mono bootstrapper.
  """

  executable: str = None
  explicit: bool = False
  environ: t.Dict[str, str] = None
  cwd: str = None
  extra_arguments: t.List[str] = None
  csc:  CscInfo = None

  def __init__(self, target, **kwargs):
    super().__init__(target, **kwargs)
    if not self.executable:
      for dep in (x.impl for x in self.target.deps):
        if isinstance(dep, Csharp) and 'exe' in dep.type:
          if self.executable:
            raise ValueError('mulitple executable Csharp dependencies, '
              'specify the one to run explicitly via `executable=...`')
          self.executable = dep.dll_filename
        # Inherit the CSC value from the dependency.
        if isinstance(dep, Csharp) and not self.csc:
          self.csc = dep.csc
      if not self.executable:
        raise ValueError('specify one Csharp executable dependency or the '
          '`executable=...` parameter.')

    self.csc = self.csc or CscInfo.get()
    environ = self.environ.copy() if self.environ else {}
    environ.update(self.csc.environ)
    self.environ = environ

  def translate(self):
    if self.csc.is_mono():
      command = ['mono']
    else:
      command = []
    command += [self.executable]
    if self.extra_arguments:
      command += self.extra_arguments

    self.action(
      actions.Commands,
      name = 'run',
      deps = self.target.transitive_deps(),
      input_files = [self.executable],
      output_files = [],
      explicit = self.explicit,
      commands = [command],
      environ = self.environ,
      cwd = self.cwd,
    )


csharp_build = build = target_factory(Csharp)
csharp_run = run = target_factory(CsharpRun)
