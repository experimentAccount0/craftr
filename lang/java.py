# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import functools
import re
craftr = require('..')
path = require('../path')

def get_class_files(sources, source_dir, output_dir):
  """
  This function computes the Java `.class` files in *output_dir* that
  will be generated from the specified *sources* in *source_dir*.

  # Example

  ```python
  >>> get_class_files(['src/org/company/package/Main.java'], 'src', 'build/java')
  ['build/java/org/company/package/Main.class']
  ```
  """

  classes = []
  for fn in sources:
    assert fn.endswith('.java')
    classes.append(path.join(output_dir, path.rel(fn, source_dir)))
  return [path.setsuffix(x, '.class') for x in classes]

class JavaCompiler:
  """
  High-level interface for compiling Java source files using `javac`
  and generating JARs using `jar`.
  """

  def __init__(self, javac=None, jar=None):
    self.javac = javac or craftr.option('javac') or 'javac'
    self.jar_ = jar or craftr.option('jar') or 'jar'

  @property
  @functools.lru_cache()
  def version(self):
    """
    The version of the Java compiler in the format of `(name, version`).
    """

    output = craftr.shell.pipe([self.javac, '-version']).output
    return [x.strip() for x in output.split(' ')]

  def compile(self, name, src_dir, out_dir=None, srcs=None, debug=False,
              warn=True, additional_flags=(), **kwargs):
    """
    Compiles Java sources to class files.

    # Parameters
    name (str): The name of the target. Can be passed #None to generate a
        unique rule name in the format `java_XXXX`.
    src_dir (str): The root directory of all source files. This is important
        for the correct generation of the output filenames.
    srcs (list of str): A list of the source files to compile. These sources
        must all be inside the specified *src_dir*. If this parameter is
        omitted, all `.java` files in the *src_dir* will be used.
    out_dir (str): The output directory for the Java `.class` files. Defaults
        to a subdirectory in the build directory like `build/<name>/obj` where
        `<name>` is the target name.
    debug (bool): True to pass the `-g` flag.
    warn (bool): False to pass the `-nowarn` flag.
    additional_flags (list of str): A list of additional arguments for the
        `javac` command, added after all automatically generated arguments.
    kwargs (dict): Additional arguments that are passed into a #craftr.Product
        instance of type `'java'`. Below is a description of the supported
        product options.

    # `java` Product Parameters
    classpath (list of str): A list of class search paths and zip/jar files.
    deps (list of craftr.Product): A list of other #craftr.Product objects
        that represent the dependencies of the product.

    # Returns
    A new #craftr.Product instance created from the specified *kwargs*.
    Contains the generated #craftr.Target object in #craftr.Product.targets.

    The #Product.meta dictionary provides a `out_dir` key of the specified
    or automatically generated *out_dir* parameter.
    """

    name = craftr.grn(name, 'java')
    if not out_dir:
      out_dir = craftr.buildlocal(name)
    if srcs is None:
      srcs = path.glob('**/*.java', src_dir)
      deps = []
    else:
      srcs, deps = craftr.split_input_list(srcs)

    product = craftr.product(name, 'java', {'out_dir': out_dir}, **kwargs)
    options = craftr.Merge([product] + deps, recursive_keys=['deps'])

    outputs = get_class_files(srcs, src_dir, out_dir)
    command = [self.javac, '-d', out_dir, '$in']
    command += ['-g'] if debug else []
    command += [] if warn else ['-nowarn']

    cp = options.getlist('java:classpath')
    command += ['-cp', path.pathsep.join(cp)] if cp else []
    command += additional_flags

    # Use all .jar and .zip files in the classpath as implicit dependencies.
    implicit = [x for x in cp if x.endswith('.jar') or x.endswith('.zip')]

    craftr.target(name, craftr.rule(name, [command]), srcs, outputs, implicit=implicit)
    return product

  def jar(self, name, classfiles, output=None, classroot=None, entry_point=None):
    """
    Create a JAR file at *output* from the specified *classfiles*. If
    *output* is omitted, it is derived from the target *name*.

    # Parameters
    name (str): The target name. Defaults to `jar_XXXX`.
    classfiles (list of str): A list of class files to include in the JAR
        archive.
    output (str): The name of the output JAR archive (including suffix).
    classroot (str): The name of the parent directory to take as the root
        when combining the *classfiles* into a JAR. If not specified, the
        *classfiles* must be a #Product generated with #compile() to take
        the #Product.meta `out_dir` key from.

    # Returns
    A #craftr.Product instance of type `'java'`.
    """

    name = craftr.grn(name, 'jar')
    output = craftr.buildlocal(output or name)
    if not output.endswith('.jar'):
      output += '.jar'
    inputs, deps = craftr.split_input_list(classfiles)
    if not classroot:
      if not deps:
        raise ValueError('no "classroot" specified, pass a Product of type '
                         '`java` or specify "classroot" explicitly')
      classroot = deps[0].meta['out_dir']

    product = craftr.product(name, 'java', {'jar': output},
        deps=deps, classpath=[output])

    flags = 'cvf'
    if entry_point:
      flags += 'e'
    command = [self.jar_, flags, output]
    if entry_point:
      command += [entry_point]
    for ifn in inputs:
      command += ['-C', classroot, path.rel(ifn, classroot)]

    craftr.target(name, craftr.rule(name, [command]), inputs, [output])
    return product

exports = JavaCompiler()
craftr.logger.info('Java compiler {!r} version {!r}', *exports.version)
