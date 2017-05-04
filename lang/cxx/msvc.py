# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

platform = require('../craftr/platform/win32')
pyutils = require('../craftr/utils/pyutils')

from nr.types.recordclass import recordclass
from operator import itemgetter

import contextlib
import craftr.platform.win32
import functools
import json
import logging
import os
import sys
import re
import tempfile


valid_archs = ('x86', 'amd64', 'ia64')
real_arch = os.environ.get('PROCESSOR_ARCHITEW6432', '').lower()
if not real_arch:
  real_arch = os.environ.get('PROCESSOR_ARCHITECTURE', 'x86').lower()
if real_arch not in valid_archs:
  raise EnvironmentError('failed to determine current platform architecture, '
      '{!r} is not supported'.format(real_arch))


@contextlib.contextmanager
def override_environ(new_environ, merge=True):
  """
  Context-manager that temporarily overwrites the current process'
  environment variables.
  """

  old_environ = os.environ.copy()
  try:
    if not merge:
      os.environ.clear()
    os.environ.update(new_environ)
    yield
  finally:
    # Restore the old enviroment variables.
    os.environ.clear()
    os.environ.update(old_environ)


@functools.lru_cache()
def identify(program):
  """
  Detects the version of the MSVC compiler from the specified #program
  name and returns a dictionary with all the version information.

  This function also supports detecting Clang-CL.

  @param program: The name of the program to execute and check.
  @return:
    ```python
    {
      "name": "msvc|clang-cl",
      "version": "...",
      "version_str": "..."
      "target": "...",
      "thread_model": "...",
      "msvc_deps_prefix": "...",
      "ml_program": "...",
      "link_program": "...",
      "lib_program": "...",
    }
    ```
  @raise ToolDetectionError: If the #program is not MSVC or Clang-CL
  """

  clang_cl_expr = r'clang\s+version\s+([\d\.]+).*\n\s*target:\s*([\w\-\_]+).*\nthread\s+model:\s*(\w+)'
  msvc_expr = re.compile(r'compiler\s+version\s*([\d\.]+)\s*\w+\s*(x\w+)', re.I | re.U | re.M)

  # Determine kind and version. We need to do this separately from
  # the /showIncludes detection as Clang CL does not display a logo
  # when being invoked.
  #
  # We can't use the /? option if the actual "program" is a batch
  # script as this will print the help for batch files (Microsoft, pls).
  # MSVC will error on -v, Clang CL will give us good info.
  try:
    res = shell.pipe([program, '-v'], shell=True, check=False)
    hint = 'clang'
    if res.returncode != 0:
      # Seems to be MSVC, which does not support a -v flag. It provides
      # all the information when being invoked with no arguments.
      res = shell.pipe([program], shell=True, check=False)
      hint = 'msvc'
    output = res.output
  except OSError as exc:
    raise ToolDetectionError(exc)

  if hint == 'clang':
    match = re.match(clang_cl_expr, output, re.I)
    if not match:
      raise ToolDetectionError('Clang-CL version and architecture could not be detected\n\n' + output)
    # We've detected a version of Clang CL!
    name = 'clang-cl'
    version = match.group(1)
    arch = match.group(2)
    thread_model = match.group(3)
  else:
    # Extract the MSVC compiler version and architecture.
    match = msvc_expr.search(output)
    if not match:
      raise ToolDetectionError('MSVC version and architecture could not be detected\n\n' + output)

    name = 'msvc'
    version = match.group(1)
    arch = match.group(2)
    thread_model = 'win32'

  # Determine the msvc_deps_prefix by making a small test. The
  # compilation will not succeed since no entry point is defined.
  deps_prefix = None
  with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as fp:
    fp.write(b'#include <stddef.h>\n')
    fp.close()
    command = [program, '/Zs', '/showIncludes', fp.name]
    try:
      output = shell.pipe(command, shell=True, check=False).output
    except OSError as exc:
      raise ToolDetectionError(exc)
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

  if not deps_prefix:
    logger.warn('identify("{}"): msvc_deps_prefix could not be determined'.format(program))
    logger.debug(output, indent = 1)
    deps_prefix = 'Note: including file:'


  return {
    'name': name,
    'version': version,
    'version_str': output.split('\n', 1)[0].strip(),
    'target': arch,
    'thread_model': thread_model,
    'msvc_deps_prefix': deps_prefix,
    'ml_program': ('ml64' if arch == 'x64' else 'ml') if name == 'msvc' else program,  # TODO: Assembler for Clang CL?
    'link_program': 'link' if name == 'msvc' else 'lld-link',
    'lib_program': 'lib' if name == 'msvc' else 'llvm-lib'
  }


def find_installations(versions=()):
  """
  Finds available MSVC installations and returns a list of (path, version).
  """

  _valid_versions = [90, 100, 110, 120, 130, 140, 150]
  versions = [int(x) for x in versions]
  for v in versions:
    if v in _valid_versions:
      raise ValueError('{} is an invalid or unsupported MSVC version'.format(v))

  # A list of (path, version) to the VS installation directory that we were
  # able to make out on this system for the specified versions.
  dirs = []
  found_versions = set()
  if versions:
    for ver in versions:
      # The VSXXXCOMNTOOLS variables always points to the
      # $(VSINSTALLDIR)/Common7/Tools directory.
      key = 'VS{}COMNTOOLS'.format(ver)
      vspath = os.getenv(key, '')
      dirs.append((vspath, ver))
  else:
    for key, value in os.environ.items():
      if key.startswith('VS') and key.endswith('COMNTOOLS'):
        try:
          ver = int(key[2:-9])
          if ver not in _valid_versions:
            raise ValueError
        except ValueError:
          continue
        vspath = os.getenv(key, '')
        dirs.append((vspath, ver))
        found_versions.add(ver)

  result = []

  # Clean up the directories.
  for vspath, ver in dirs:
    vspath = vspath.rstrip('\\')
    if vspath:
      vspath = path.dirname(path.dirname(vspath))
      if os.path.isdir(vspath):
        result.append((vspath, ver))

  # Handle MSVC 2017 special, since the directory structure changed and
  # the VS150COMNTOOLS is usually not available.
  # TODO: Can MSVC 2017 be installed in an alternative location?
  if 150 not in found_versions and (not versions or 150 in versions):
    programfiles = os.getenv('ProgramFiles(x86)', '') or os.getenv('ProgramFiles', '')
    if programfiles:
      vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Community')
      if not os.path.isdir(vspath):
        vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Professional')
      if not os.path.isdir(vspath):
        vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Enterprise')
      if os.path.isdir(vspath):
        result.append((vspath, 150))

  return result

@functools.lru_cache()
def find_installation(versions=(), arch=None):
  """
  Finds the MSVC platform Toolkit of a Visual Studio installation
  that is installed on the host machine. Note that this

  @param versions: A list of versions that should be looked for.
    If specified, no version other than the ones specified will
    be checked. Otherwise, any version is checked. Valid versions
    are 90, 100, 110, 120, 130, 140, 150
  @param arch: Override the target architecture of the platform toolkit.
    Defaults to the `craftr.tools.msvc.ARCH` option. Must be one of
    `x86`, `amd64` and `ia64`.
  @raise ToolDetectionError: If no Visual Studio insallation could be found.
  """

  installations = find_installations(versions)
  if not installations:
    raise ToolDetectionError('Visual Studio could not be detected on the system.')
  installations.sort(key=itemgetter(1), reverse=True)  # newest first

  logger.debug('Detected Visual Studio Installations:')
  for vspath, ver in installations:
    logger.debug('  {} ({})'.format(vspath, ver))

  # Choose the first where we can successfully determine the
  # environment information.
  last_error = None
  for vspath, ver in installations:
    try:
      return _get_vs_environment(vspath, ver, arch)
    except ToolDetectionError as exc:
      last_error = exc

  if last_error:
    raise last_error
  assert False

def _get_vs_environment(install_dir, vsversion, arch=None):
  """
  Internal method that retrieves the environment information for a
  Visual Studio installation. *install_dir* must point to the root
  installation directory.
  """

  arch = arch or options.target
  if arch not in valid_archs:
    raise ValueError("invalid architecture: {!r}".format(arch))

  if vsversion >= 150:
    vcvarsall = path.join(install_dir, 'VC', 'Auxiliary', 'Build', 'vcvarsall.bat')
  else:
    vcvarsall = path.join(install_dir, 'VC', 'vcvarsall.bat')

  # Run the batch file and print the environment.
  cmd = [vcvarsall, arch, shell.safe('&&'), sys.executable, '-c', 'import os, json; print("JSONOUTPUTBEGIN:" + json.dumps(dict(os.environ)))']
  try:
    output = shell.pipe(cmd, shell=True).output
  except OSError as exc:
    raise ToolDetectionError('Visual Studio Environment could not be detected.\n\n' + str(exc)) from exc

  key = 'JSONOUTPUTBEGIN:'
  jsondata = output[output.find(key) + len(key):]

  try:
    env = json.loads(jsondata)
  except json.JSONDecodeError:
    logger.debug('failed to parse output of "{}"'.format(vcvarsall))
    raise ToolDetectionError('Visual Studio Environment could not be detected')
  return {'env': env, 'arch': arch, 'version': vsversion}

class MsvcToolkit(object):

  Programs = recordclass.new('Programs', 'cl ml link lib')

  def __init__(self, toolkit=None, target=None):
    toolkit = toolkit or options.toolkit or 'msvc'
    target = target or options.target
    if target and target not in valid_archs:
      raise ValueError('invalid target architecture: {!r}'.format(target))

    version = ()
    if toolkit.startswith('msvc'):
      if len(toolkit) > 4:
        version = (toolkit[4:].lstrip('-'),)
    elif not toolkit == 'clang-cl':
      raise ValueError('invalid toolkit name: {!r}'.format(toolkit))

    self.info = None
    self.install_info = None
    if toolkit in ('clang-cl', 'msvc'):
      cl = 'clang-cl' if toolkit == 'clang-cl' else 'cl'
      try:
        self.info = identify(cl)
      except ToolDetectionError as exc:
        pass

    if not self.info:
      self.install_info = find_installation(version, target or real_arch)
      cl = 'cl'
      with override_environ(self.install_info['env']):
        self.info = identify(cl)

    real_target = self.info['target']
    if self.name == 'clang-cl':
      if real_target == 'x86_64-pc-windows-msvc':
        real_target = 'x64'
      else:
        # TODO: Understand more Clang CL targets.
        error('unsupported clang-cl target: {}'.format(self.info['target']))

    # Warn if there might be some misconfiguration happening.
    if target and real_target != target:
      logger.warn('{}: expected target "{}" does not match with actual compiler target "{}"'
          .format(self.name, target, real_target))

    self.toolkit = toolkit
    self.target_arch = real_target
    self.programs = self.Programs('cl.exe', self.info['ml_program'],
        self.info['link_program'], self.info['lib_program'])

  def __str__(self):
    return self.info['version_str']

  def __repr__(self):
    return '<MsvcToolkit version={!r}>'.format(self.version)

  @property
  def name(self):
    return self.info['name']

  @property
  def version(self):
    return self.info['version']

  def compile(self, language, sources, *, frameworks=(), source_directory=None, name=None, **kwargs):
    if language not in ('asm', 'c', 'c++'):
      raise ValueError('unsupported language: {!r}'.format(language))

    builder = TargetBuilder(gtn(name, 'msvc_compile'), kwargs, frameworks, sources)
    for callback in builder.get_list('cxc_compile_prepare_callbacks'):
      callback(self, builder)

    suffix = builder.get('suffix', platform.obj)
    objects = relocate_files(builder.inputs, buildlocal('obj'), suffix, parent=source_directory)

    debug = builder.get('debug', options.debug)
    defines = builder.get_list('defines')
    if builder.get('msvc_use_default_defines', True):
      defines += ['WIN32', '_WIN32']
    if debug:
      pyutils.unique_extend(defines, ['_DEBUG', 'DEBUG'])
    else:
      pyutils.unique_extend(defines, ['NDEBUG'])
    undefines = builder.get_list('undefines')

    if language == 'asm':
      command = [self.programs.ml]
    else:
      command = [self.programs.cl]
    command += ['/nologo', '/Fo$out', '/c', '$in']
    command += ['/wd' + str(x) for x in builder.get_list('msvc_disable_warnings')]
    command += ['/we' + str(x) for x in builder.get_list('msvc_warnings_as_errors')]

    # Check if we need a response file for the includes.
    include_args = ['/I' + x for x in builder.get_list('include')]
    response_file, response_args = write_response_file(include_args, builder, suffix='.include')
    command += response_args

    command += ['/D' + x for x in defines]
    command += ['/U' + x for x in undefines]
    command += ['/FI' + x for x in builder.get_list('forced_include')]
    if debug:
      command += ['/Od', '/RTC1', '/FC']
      if not self.version or self.version >= 'v18':
        # Enable parallel writes to .pdb files. We also assume that this
        # option is necessary by default.
        command += ['/FS']
      if options.embedd_debug_symbols:
        command += ['/Z7']
      else:
        command += ['/Zi', '/Fd$out.pdb']

    exceptions = builder.get('exceptions', None)
    if exceptions:
      if language != 'c++':
        logger.warn("invalid value for exceptions: {!r} "
          "(not supported in language {!r})".format(exceptions, language))
      command += ['/EHsc']
    elif exceptions is None and language == 'c++':
      # Enable exceptions by default.
      command += ['/EHsc']

    if language == 'c++':
      rtti = builder.get('rtti', options.rtti)
      if rtti is not None:
        command += ['/GR'] if rtti else ['/GR-']

    warn = builder.get('warn', None)
    if warn == 'all':
      # /Wall really shows too many warnings, /W4 is pretty good.
      command += ['/W4']
    elif warn == 'none':
      command += ['/w']
    elif warn is None:
      pass
    else:
      logger.warn("invalid value for optimize: {!r}".format(optimize))

    optimize = builder.get('optimize', None)
    if debug:
      if optimize and optimize != 'debug':
        logger.warn("invalid value for optimize: {!r} "
          "(no optimize with debug enabled)".format(optimize))
    elif optimize == 'speed':
      command += ['/O2']
    elif optimize == 'size':
      command += ['/O1', '/Os']
    elif optimize in ('debug', 'none'):
      command += ['/Od']
    elif optimize is not None:
      logger.warn("invalid value for optimize: {!r}".format(optimize))

    msvc_runtime_library = builder.get('msvc_runtime_library', 'dynamic')
    if language != 'asm':
      if msvc_runtime_library == 'dynamic':
        command += ['/MDd' if debug else '/MD']
      elif msvc_runtime_library == 'static':
        command += ['/MTd' if debug else '/MT']
      elif msvc_runtime_library is not None:
        raise ValueError('invalid msvc_runtime_library: {!r}'.format(msvc_runtime_library))

    autodeps = builder.get('autodeps', True)
    params = {}
    if autodeps and language != 'asm':
      params['deps'] = 'msvc'
      params['msvc_deps_prefix'] = self.info['msvc_deps_prefix']
      command += ['/showIncludes']
    command += builder.get_list('msvc_additional_flags')
    command += builder.get_list('msvc_compile_additional_flags')
    if self.name == 'clang-cl':
      command += builder.get_list('clangcl_compile_additional_flags')
    command += builder.get_list('additional_flags')

    environ = None
    if self.install_info:
      environ = self.install_info['env']

    pyutils.strip_flags(command, builder.get_list('remove_flags'))
    t = builder.build([command], None, objects, foreach=True, environ=environ,
      description='{} compile ($out)'.format(self.info['name']),
      **params)
    return t

  def link(self, output_type, inputs, output, frameworks=(), name=None, **kwargs):
    if output_type not in ('bin', 'dll'):
      raise ValueError('invalid output_type: {!r}'.format(output_type))

    builder = TargetBuilder(gtn(name, "msvc_link"), kwargs, frameworks, inputs)
    for callback in builder.get_list('cxc_link_prepare_callbacks'):
      callback(self, builder)

    suffix = builder.get(output_type + '_suffix')
    if not suffix:
      suffix = builder.get('suffix', getattr(platform, output_type))

    output = buildlocal(path.addsuffix(output, suffix))
    outputs = [output]
    meta = {'link_output': output}

    libpath = builder.get_list('libpath')
    libs = builder.get_list('libs')
    libs += builder.get_list('msvc_libs')
    external_libs = builder.get_list('external_libs')
    if self.info['target'] == 'x86':
      libs += builder.get_list('win32_libs')
      external_libs += builder.get_list('win32_external_libs')
    else:
      libs += builder.get_list('win64_libs')
      external_libs += builder.get_list('win64_external_libs')
    external_libs = [path.abs(x) for x in external_libs]
    debug = builder.get('debug', options.debug)

    command = [self.programs.link, '/nologo']

    # Check if we need a response file for the inputs.
    response_file, response_args = write_response_file(builder.inputs, builder)
    if response_file:
      command += response_args
    else:
      command += ['$in']

    if output_type == 'dll':
      implib = path.setsuffix(output, '.lib')
      command += ['/DLL', '/IMPLIB:' + implib]
      outputs.append(implib)
      meta['dll_link_target'] = implib
    if debug:
      pdbfile = path.setsuffix(output, '.pdb')
      command += ['/DEBUG', '/PDB:' + pdbfile]
      outputs.append(pdbfile)
    command += ['/LIBPATH:{0}'.format(x) for x in libpath]
    command += ['/OUT:' + output]
    command += [x + '.lib' for x in libs]
    command += external_libs

    pyutils.strip_flags(command, builder.get_list('remove_flags'))
    command += builder.get_list('additional_flags')
    command += builder.get_list('msvc_link_additional_flags')

    environ = None
    if self.install_info:
      environ = self.install_info['env']

    return builder.build([command], None, outputs,
      implicit_deps=external_libs, metadata=meta, environ=environ,
      description='{} link ($out)'.format(self.info['name']))

  def staticlib(self, inputs, output, export_symbols=(), additional_flags=(),
                msvc_additional_flags=(), name=None, **kwargs):

    builder = TargetBuilder(gtn(name, "msvc_staticlib"), kwargs, (), inputs)
    for callback in builder.get_list('cxc_staticlib_prepare_callbacks'):
      callback(self, builder)

    output = buildlocal(platform.lib(output))
    command = [self.programs.lib, '/nologo']
    command += ['/export:' + x for x in export_symbols]
    command += additional_flags
    command += msvc_additional_flags

    response_file, response_args = write_response_file(builder.inputs, builder)
    if response_file:
      command += response_args
    else:
      command += ['$in']

    command += ['/OUT:$out']

    environ = None
    if self.install_info:
      environ = self.install_info['env']
    return builder.build([command], None, [output], environ=environ,
      description='{} staticlib ($out)'.format(self.info['name']),
      metadata={'staticlib_output': output})


cxc = msvc = MsvcToolkit()
