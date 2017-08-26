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
Target implementations for building Java projects.
"""

__all__ = ['java_library', 'java_binary', 'java_prebuilt']

import nodepy
import re
import typing as t
import craftr, * from 'craftr'
import actions from 'craftr/actions'


def partition_sources(sources: t.List[str], base_dirs: t.List[str],
                      parent: str = None) -> t.Dict[str, t.List[str]]:
  """
  Partitions a set of files in *sources* to the appropriate parent directory
  in *base_dirs*. If a file is found that is not located in one of the
  *base_dirs*, a #ValueError is raised.

  A relative path in *sources* and *base_dirs* will be automatically converted
  to an absolute path using the *parent*, which defaults to the currently
  executed module's directory.
  """

  parent = parent or projectdir()
  base_dirs = [canonicalize(b, parent) for b in base_dirs]
  result = {}
  for source in (canonicalize(s, parent) for s in sources):
    for base in base_dirs:
      rel_source = path.rel(source, base)
      if path.isrel(rel_source):
        break
    else:
      raise ValueError('could not find relative path for {!r} given the '
        'specified base dirs:\n  '.format(source) + '\n  '.join(base_dirs))
    result.setdefault(base, []).append(rel_source)
  return result


class JavaLibrary(craftr.AnnotatedTarget):
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

  jar_dir:
    The directory where the jar will be created in.

  jar_name:
    The name of the JAR file. Defaults to the target name.

  main_class:
    A classname that serves as an entry point for the JAR archive. Note that
    you should prefer to use `java_binary()` to create a JAR binary that
    contains all its dependencies merged into one.

  javac:
    The name of Java compiler to use. If not specified, defaults to the value
    of the `java.javac` option or simply "javac".

  javac_jar:
    The name of Java JAR command to use. If not specified, defaults to the
    value of the `java.javac_jar` option or simply "jar".

  extra_arguments:
    A list of additional arguments for the Java compiler. They will be
    appended to the ones specified in the configuration.
  """

  srcs: t.List[str]
  src_roots: t.List[str] = None
  class_dir: str = None
  jar_dir: str = None
  jar_name: str = None
  main_class: str = None
  javac: str = None
  javac_jar: str = None
  extra_arguments: t.List[str] = None

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.srcs = canonicalize(self.srcs)
    if self.src_roots is None:
      self.src_roots = config.get('java.src_roots', ['src', 'java', 'javatest'])
    if self.src_roots:
      self.src_roots = canonicalize(self.src_roots, projectdir())
    self.class_dir = canonicalize(self.class_dir or 'classes/' + self.name, projectbuilddir())
    self.jar_dir = canonicalize(self.jar_dir or projectbuilddir())
    self.jar_name = self.jar_name or self.name
    self.javac = self.javac or config.get('java.javac', 'javac')
    self.javac_jar = self.javac_jar or config.get('java.javac_jar', 'jar')

  @property
  def jar_filename(self) -> str:
    return path.join(self.jar_dir, self.jar_name) + '.jar'

  def translate(self):
    deps = self.deps()
    extra_arguments = config.get('java.extra_arguments', []) + (self.extra_arguments or [])
    classpath = []

    for dep in deps:
      if isinstance(dep, JavaLibrary):
        # TODO: Make sure dependencies are already translated at the time
        #       the target is executed.
        classpath.append(dep.jar_filename)
      elif isinstance(dep, JavaPrebuilt):
        classpath.append(dep.binary_jar)

    # Calculate output files.
    classfiles = []
    for base, sources in partition_sources(self.srcs, self.src_roots).items():
      for src in sources:
        classfiles.append(path.join(self.class_dir, path.setsuffix(src, '.class')))

    if self.srcs:
      command = [self.javac, '-d', self.class_dir]
      if classpath:
        command += ['-classpath', path.pathsep.join(classpath)]
      command += self.srcs
      command += extra_arguments

      mkdir = actions.mkdir(self,
        name = 'class_dir',
        directory = self.class_dir
      )
      javac = actions.subprocess(self,
        name = 'javac',
        commands = [command],
        deps = deps + [mkdir],
        inputs = self.srcs,
        outputs = classfiles
      )
    else:
      javac = None

    flags = 'cvf'
    if self.main_class:
      flags += 'e'

    command = [self.javac_jar, flags, self.jar_filename]
    if self.main_class:
      command.append(self.main_class)
    command.append('-C')
    command.append(self.class_dir)
    command.append('.')

    mkdir = actions.mkdir(self,
      name = 'jar_dir',
      directory = self.jar_dir
    )
    actions.subprocess(self,
      name = 'jar',
      commands = [command],
      deps = [javac, mkdir] if javac else [mkdir],
      inputs = classfiles,
      outputs = [self.jar_filename]
    )


class JavaBinary(craftr.AnnotatedTarget):
  """
  Takes a list of Java dependencies and creates an executable JAR archive
  from them.

  # Parameters
  jar_dir:
    The directory where the jar will be created in.

  jar_name:
    The name of the JAR file. Defaults to the target name.

  main_class:
    The name of the main Java class.

  javac_jar:
    The name of Java JAR command to use. If not specified, defaults to the
    value of the `java.javac_jar` option or simply "jar".
  """

  jar_dir: str = None
  jar_name: str = None
  main_class: str
  javac_jar: str = None

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.jar_dir = canonicalize(self.jar_dir or projectbuilddir())
    self.jar_name = self.jar_name or self.name
    self.javac_jar = self.javac_jar or config.get('java.javac_jar', 'jar')

  @property
  def jar_filename(self) -> str:
    return path.join(self.jar_dir, self.jar_name) + '.jar'

  def translate(self):
    deps = self.deps()

    inputs = []
    for dep in deps:
      if isinstance(dep, JavaLibrary):
        inputs.append(dep.jar_filename)
      elif isinstance(dep, JavaPrebuilt):
        inputs.append(dep.binary_jar)

    outputs = [self.jar_filename]

    command = nodepy.proc_args + [require.resolve('./mergejar')]
    command += ['-o', self.jar_filename] + inputs
    command += ['--main-class', self.main_class]

    mkdir = actions.mkdir(self,
      name = 'jar_dir',
      directory = self.jar_dir
    )
    t = actions.subprocess(self,
      name = 'merge',
      deps = deps,
      inputs = inputs,
      outputs = outputs,
      commands = [command]
    )


class JavaPrebuilt(craftr.AnnotatedTarget):
  """
  Represents a prebuilt JAR. Does not yield actions.

  # Parameters
  binary_jar:
    The path to a binary `.jar` file.
  """

  binary_jar: str

  def translate(self):
    actions.null(self, name='null', deps=self.deps())


java_library = craftr.target_factory(JavaLibrary)
java_binary = craftr.target_factory(JavaBinary)
java_prebuilt = craftr.target_factory(JavaPrebuilt)
