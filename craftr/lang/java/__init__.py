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
Targets for building Java projects.
"""

__all__ = ['java_library', 'java_binary', 'java_prebuilt']

import nodepy
import re
import typing as t
import * from 'craftr'

ONEJAR_FILENAME = canonicalize(
  config.get('java.onejar',
  path.join(__directory__, 'one-jar-boot-0.97.jar')))


def partition_sources(
    sources: t.List[str],
    base_dirs: t.List[str],
    parent: str
  ) -> t.Dict[str, t.List[str]]:
  """
  Partitions a set of files in *sources* to the appropriate parent directory
  in *base_dirs*. If a file is found that is not located in one of the
  *base_dirs*, a #ValueError is raised.

  A relative path in *sources* and *base_dirs* will be automatically converted
  to an absolute path using the *parent*, which defaults to the currently
  executed module's directory.
  """

  base_dirs = canonicalize(base_dirs, parent)
  result = {}
  for source in canonicalize(sources, parent):
    for base in base_dirs:
      rel_source = path.rel(source, base)
      if path.isrel(rel_source):
        break
    else:
      raise ValueError('could not find relative path for {!r} given the '
        'specified base dirs:\n  '.format(source) + '\n  '.join(base_dirs))
    result.setdefault(base, []).append(rel_source)
  return result


class _JarBase(AnnotatedTargetImpl):
  """
  jar_dir:
    The directory where the jar will be created in.

  jar_name:
    The name of the JAR file. Defaults to the target name. Note that the Java
    JAR command does not support dots in the output filename, thus it will
    be rendered to a temporary directory.

  main_class:
    A classname that serves as an entry point for the JAR archive. Note that
    you should prefer to use `java_binary()` to create a JAR binary that
    contains all its dependencies merged into one.

  javac_jar:
    The name of Java JAR command to use. If not specified, defaults to the
    value of the `java.javac_jar` option or simply "jar".
  """

  jar_dir: str = None
  jar_name: str = None
  main_class: str = None
  javac_jar: str = None

  def __init__(self, target, **kwargs):
    super().__init__(target, **kwargs)
    if self.jar_dir:
      self.jar_dir = canonicalize(self.jar_dir, self.cell.builddir)
    else:
      self.jar_dir = self.cell.builddir
    self.jar_name = self.jar_name or (self.cell.name.split('/')[-1] + '-' + self.target.name + '-' + self.cell.version)
    self.javac_jar = self.javac_jar or config.get('java.javac_jar', 'jar')

  @property
  def jar_filename(self) -> str:
    return path.join(self.jar_dir, self.jar_name) + '.jar'


@inherit_annotations()
class JavaLibrary(_JarBase):
  """
  The base target for compiling Java source code and creating a Java binary
  or libary JAR file.

  # Parameters
  srcs:
    A list of source files. If `srcs_root` is not specified, the config option
    `java.src_roots` to determine the root of the source files.

  src_roots:
    A list of source root directories. Defaults to `java.src_roots` config.
    The default value for this configuration is `['src', 'java', 'javatest']`.

  class_dir:
    The directory where class files will be compiled to.

  javac:
    The name of Java compiler to use. If not specified, defaults to the value
    of the `java.javac` option or simply "javac".

  extra_arguments:
    A list of additional arguments for the Java compiler. They will be
    appended to the ones specified in the configuration.
  """

  srcs: t.List[str]
  src_roots: t.List[str] = None
  class_dir: str = None
  javac: str = None
  extra_arguments: t.List[str] = None

  def __init__(self, target, **kwargs):
    super().__init__(target, **kwargs)
    self.srcs = canonicalize(self.srcs)
    if self.src_roots is None:
      self.src_roots = config.get('java.src_roots', ['src', 'java', 'javatest'])
    if self.src_roots:
      self.src_roots = canonicalize(self.src_roots)
    self.class_dir = canonicalize(self.class_dir or 'classes/' + self.target.name, self.cell.builddir)
    self.javac = self.javac or config.get('java.javac', 'javac')

  def translate(self):
    deps = self.target.transitive_deps()
    extra_arguments = config.get('java.extra_arguments', []) + (self.extra_arguments or [])
    classpath = []

    for dep in (x.impl for x in deps):
      if isinstance(dep, JavaLibrary):
        classpath.append(dep.jar_filename)
      elif isinstance(dep, JavaPrebuilt):
        classpath.append(dep.binary_jar)

    # Calculate output files.
    classfiles = []
    for base, sources in partition_sources(self.srcs, self.src_roots, self.target.cell.directory).items():
      for src in sources:
        classfiles.append(path.join(self.class_dir, path.setsuffix(src, '.class')))

    if self.srcs:
      command = [self.javac, '-d', self.class_dir]
      if classpath:
        command += ['-classpath', path.pathsep.join(classpath)]
      command += self.srcs
      command += extra_arguments

      mkdir = self.action(
        actions.Mkdir,
        name = 'mkdir',
        directory = self.class_dir
      )
      javac = self.action(
        actions.Commands,
        name = 'javac',
        commands = [command],
        deps = deps + [mkdir],
        input_files = self.srcs,
        output_files = classfiles
      )
    else:
      javac = None

    flags = 'cvf'
    if self.main_class:
      flags += 'e'

    command = [self.javac_jar, flags, self.jar_filename]
    if self.main_class:
      command.append(self.main_class)
    command += ['-C', self.class_dir, '.']

    mkdir = self.action(
      actions.Mkdir,
      name = 'jar_dir',
      directory = self.jar_dir
    )
    self.action(
      actions.Commands,
      name = 'jar',
      commands = [command],
      deps = [javac, mkdir] if javac else [mkdir],
      input_files = classfiles,
      output_files = [self.jar_filename]
    )


@inherit_annotations()
class JavaBinary(_JarBase):
  """
  Takes a list of Java dependencies and creates an executable JAR archive
  from them.

  # Parameters
  dist_type:
    The distribution type. Can be `'merge'` or `'onejar'`. The default is
    the value configured in `java.dist_type` or `'onejar'`
  """

  main_class: str = None  # Default value inherited by parent class..
  dist_type: str = None

  def __init__(self, target, **kwargs):
    super().__init__(target, **kwargs)
    if not self.main_class:
      raise ValueError('missing value for "main_class"')
    if not self.dist_type:
      self.dist_type = config.get('java.dist_type', 'onejar')
    if self.dist_type not in ('merge', 'onejar'):
      raise ValueError('invalid dist_type: {!r}'.format(self.dist_type))

  def translate(self):
    deps = self.target.transitive_deps()

    inputs = []
    for dep in deps:
      if isinstance(dep.impl, JavaLibrary):
        inputs.append(dep.impl.jar_filename)
      elif isinstance(dep.impl, JavaPrebuilt):
        inputs.append(dep.impl.binary_jar)

    outputs = [self.jar_filename]

    command = nodepy.proc_args + [require.resolve('./augjar')]
    command += ['-o', self.jar_filename]

    if self.dist_type == 'merge':
      command += [inputs.pop(0)]  # Merge into the first specified dependency.
      command += ['-s', 'Main-Class=' + self.main_class]
      for infile in inputs:
        command += ['-m', infile]

    else:
      assert self.dist_type == 'onejar'
      command += [ONEJAR_FILENAME]
      command += ['-s', 'One-Jar-Main-Class=' + self.main_class]
      for infile in inputs:
        command += ['-f', 'lib/' + path.base(infile) + '=' + infile]

    mkdir = self.action(
      actions.Mkdir,
      name = 'jar_dir',
      directory = self.jar_dir
    )
    self.action(
      actions.Commands,
      name = self.dist_type,
      deps = deps,
      input_files = inputs,
      output_files = outputs,
      commands = [command]
    )


class JavaPrebuilt(AnnotatedTargetImpl):
  """
  Represents a prebuilt JAR. Does not yield actions.

  # Parameters
  binary_jar:
    The path to a binary `.jar` file.
  """

  binary_jar: str

  def translate(self):
    self.action(
      actions.Null,
      name = 'null',
      deps = self.target.transitive_deps()
    )


java_library = library = target_factory(JavaLibrary)
java_binary = binary = target_factory(JavaBinary)
java_prebuilt = prebuilt = target_factory(JavaPrebuilt)
