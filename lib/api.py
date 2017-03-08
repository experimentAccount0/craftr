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
"""
This module provides the default global namespace for Craftr modules. Names
starting with an underscore will be ignored.
"""

import builtins
import collections
import itertools
import os
import sys

argschema = require('./utils/argschema')
craftr = require('../index')
build = require('./ninja')
loaders = require('./loaders')
logger = require('@craftr/logger')
path = require('./utils/path')
platform = require('./platform')
pyutils = require('./utils/py')
shell = require('./utils/shell')

pkg_config = loaders.pkg_config
external_file = loaders.external_file
external_archive = loaders.external_archive

Target = build.Target


def gtn(name):
  """
  Reads out the current Craftr namespace and concatenates it with the specified
  *name* string, returning an absolute identifier for *name* in the context of
  the current Craftr namespace.
  """

  return '{}:{}'.format(craftr.current_namespace().name, name)


class TargetBuilder(object):
  """
  This is a helper class for target generators that does a lot of convenience
  handling such as creating a :class:`OptionMerge` from the build options
  specified with the *frameworks* argument or from the input
  :class:`Targets<build.Target>`.

  :param name: The name of the target.
  :param option_kwargs: A dictionary of additional call-level options
    that have been passed to the target generator function. These will
    take top priority in the :class:`OptionMerge`.
  :param inputs: A list of input files or :class:`build.Target` objects
    from which the outputs will be used as input files and the build
    options will be included in the :class:`OptionMerge`.
  :param frameworks: A list of build :class:`Framework` objects that will be
    included in the :class:`OptionMerge`.
  :param outputs: A list of output filenames.
  :param implicit_deps: A list of filenames added as implicit dependencies.
  :param order_only_deps: A list of filenames added as order only dependencies.
  """

  def __init__(self, name, option_kwargs=None, frameworks=(), inputs=(),
      outputs=(), implicit_deps=(), order_only_deps=()):
    argschema.validate('name', name, {'type': str})
    argschema.validate('option_kwargs', option_kwargs,
        {'type': [None, dict, Framework]})
    argschema.validate('frameworks', frameworks,
        {'type': [list, tuple], 'items': {'type': [Framework, build.Target]}})
    argschema.validate('inputs', inputs,
        {'type': [list, tuple, build.Target],
          'items': {'type': [str, build.Target]}})
    argschema.validate('outputs', outputs,
        {'type': [list, tuple], 'items': {'type': str}})
    argschema.validate('implicit_deps', implicit_deps,
        {'type': [list, tuple], 'items': {'type': str}})
    argschema.validate('order_only_deps', order_only_deps,
        {'type': [list, tuple], 'items': {'type': str}})

    if isinstance(inputs, build.Target):
      inputs = [inputs]

    self.frameworks = []
    self.implicit_deps = list(implicit_deps)
    self.order_only_deps = list(order_only_deps)

    # If we find any Target objects in the inputs, expand the outputs
    # and append the frameworks.
    if inputs is not None:
      self.inputs = []
      for input_ in (inputs or ()):
        if isinstance(input_, build.Target):
          pyutils.unique_extend(self.frameworks, input_.frameworks)
          self.inputs += input_.outputs
        else:
          self.inputs.append(input_)
    else:
      self.inputs = None

    # Unpack the frameworks list, which may also container Targets.
    for fw in frameworks:
      if isinstance(fw, build.Target):
        self.implicit_deps.append(fw)
        self.frameworks += fw.frameworks
      else:
        self.frameworks.append(fw)

    if option_kwargs is None:
      option_kwargs = {}

    self.name = name
    self.outputs = list(outputs)
    self.metadata = {}
    self.used_option_keys = set()

    self.option_kwargs = Framework(name, **option_kwargs)
    self.option_kwargs_defaults = Framework(name + "_defaults")
    self.options_merge = OptionMerge(self.option_kwargs,
        self.option_kwargs_defaults, *self.frameworks)
    assert self.option_kwargs in self.options_merge.frameworks

  def get(self, key, default=None):
    self.used_option_keys.add(key)
    return self.options_merge.get(key, default)

  def get_list(self, key):
    self.used_option_keys.add(key)
    return self.options_merge.get_list(key)

  def add_local_framework(self, *args, **kwargs):
    fw = Framework(*args, **kwargs)
    self.options_merge.append(fw)

  def setdefault(self, key, value):
    self.option_kwargs_defaults[key] = value

  def build(self, commands, inputs=(), outputs=(), implicit_deps=(),
      order_only_deps=(), metadata=None, **kwargs):
    """
    Create a :class:`build.Target` from the information in the builder,
    add it to the build graph and return it.
    """

    unused_keys = set(self.option_kwargs.keys()) - self.used_option_keys
    if unused_keys:
      logger.warn('TargetBuilder: "{}" unhandled option keys'.format(self.name))
      with logger.indent():
        for key in unused_keys:
          logger.warn('[-] {}={!r}'.format(key, self.option_kwargs[key]))

    # TODO: We could make this a bit shorter..
    inputs = self.inputs + list(inputs or ())
    outputs = self.outputs + list(outputs or ())
    implicit_deps = self.implicit_deps + list(implicit_deps or ())
    order_only_deps = self.order_only_deps + list(order_only_deps or ())
    if metadata is None:
      metadata = self.metadata
    elif self.metadata:
      raise RuntimeError('metadata specified in constructor and build()')

    implicit_deps = list(implicit_deps)
    for item in self.get_list('implicit_deps'):
      if isinstance(item, build.Target):
        implicit_deps += item.outputs
      elif isinstance(item, str):
        implicit_deps.append(item)
      else:
        raise TypeError('expected Target or str in "implicit_deps", found {}'
            .format(type(item).__name__))

    api = require('./api')
    return api.gentarget(self.name, commands, inputs, outputs, implicit_deps,
        order_only_deps, metadata=metadata, frameworks=self.frameworks, **kwargs)


class Framework(dict):
  """
  A framework is simply a dictionary with a name to identify it. Frameworks
  are used to represent build options.
  """

  def __init__(self, __name, **kwargs):
    super().__init__(**kwargs)
    self.name = __name

  def __repr__(self):
    return '<Framework "{}": {}>'.format(self.name, super().__repr__())


class OptionMerge(object):
  """
  This class represents a virtual merge of :class:`Framework` objects. Keys
  in the first dictionaries passed to the constructor take precedence over the
  last.

  :param frameworks: One or more :class:`Framework` objects. Note that
    the constructor will expand and flatten the ``'frameworks'`` list.
  """

  def __init__(self, *frameworks):
    self.frameworks = []
    [self.append(x) for x in frameworks]

  def __getitem__(self, key):
    for options in self.frameworks:
      try:
        return options[key]
      except KeyError:
        pass  # intentional
    raise KeyError(key)

  def append(self, framework):
    def update(fw):
      if not isinstance(framework, Framework):
        raise TypeError('expected Framework, got {}'.format(type(fw).__name__))
      pyutils.unique_append(self.frameworks, fw, id_compare=True)
      [update(x) for x in fw.get('frameworks', [])]
    update(framework)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def get_list(self, key):
    """
    This function returns a concatenation of all list values saved under the
    specified *key* in all option dictionaries in this OptionMerge object.
    It gives an error if one option dictionary contains a non-sequence for
    *key*.
    """

    result = []
    for option in self.frameworks:
      value = option.get(key)
      if value is None:
        continue
      if not isinstance(value, collections.Sequence):
        raise ValueError('found "{}" for key "{}" which is a non-sequence'
            .format(tpye(value).__name__, key))
      result += value
    return result



class ToolDetectionError(Exception):
  pass


class ModuleError(Exception):
  pass


class ModuleReturn(Exception):
  """
  This exception is raised to "return" form a module execution pre-emptively
  without causing an error. See :func:`return_()`
  """




def glob(patterns, parent=None, exclude=(), include_dotfiles=False, ignore_false_excludes=False):
  """
  Wrapper for :func:`path.glob` that automatically uses the current modules
  project directory for the *parent* argument if it has not been specifically
  set.
  """

  if parent is None:
    parent = craftr.current_namespace().directory

  return path.glob(patterns, parent, exclude, include_dotfiles,
    ignore_false_excludes)


def local(rel_path):
  """
  Given a relative path, returns the absolute path relative to the current
  module's project directory.
  """

  return path.norm(rel_path, craftr.current_namespace().directory)


def buildlocal(rel_path):
  """
  Given a relative path, returns the path (still relative) to the build
  directory for the current module. This is basically a shorthand for
  prepending the module name and version to *path*.
  """

  if path.isabs(rel_path):
    return rel_path

  return path.canonical(path.abs(path.join(craftr.build_dir,
      craftr.current_namespace().name, rel_path)))


def relocate_files(files, outdir, suffix, replace_suffix=True, parent=None):
  """
  Converts a list of filenames, relocating them to *outdir* and replacing
  their existing suffix. If *suffix* is a callable, it will be passed the
  new filename and expected to return the same filename, eventually with
  a different suffix.
  """

  if parent is None:
    parent = craftr.current_namespace().directory
  result = []
  for filename in files:
    filename = path.join(outdir, path.rel(filename, parent))
    filename = path.addsuffix(filename, suffix, replace=replace_suffix)
    result.append(filename)
  return result


def filter(predicate, iterable):
  """
  Alternative for the built-in ``filter()`` function that returns a list
  instead of an iterable (which is the behaviour since Python 3).
  """

  result = []
  for item in iterable:
    if predicate(item):
      result.append(item)
  return result


def map(procedure, iterable):
  """
  Alternative for the built-in ``map()`` function that returns a list instead
  of an iterable (which is the behaviour since Python 3).
  """

  result = []
  for item in iterable:
    result.append(procedure(item))
  return result


def zip(*iterables, fill=NotImplemented):
  """
  Alternative to the Python built-in ``zip()`` function. This function returns
  a list rather than an iterable and also supports swapping to the
  :func:`itertools.izip_longest` version if the *fill* parameter is specified.
  """

  if fill is NotImplemented:
    return list(builtins.zip(*iterables))
  else:
    return list(itertools.zip_longest(*iterables, fillvalue=fill))


def load_file(filename, export_default_namespace=True):
  """
  Loads a Python file into a new module-like object and returns it. The
  *filename* is assumed relative to the currently executed module's
  directory (NOT the project directory which can be different).
  """

  module = session.module
  __name__ = module.ident + ':' + filename
  if not path.isabs(filename):
    filename = path.join(module.directory, filename)
  filename = path.norm(filename)

  module.dependent_files.append(filename)
  with open(filename, 'r') as fp:
    code = compile(fp.read(), filename, 'exec')

  scope = Namespace()
  if export_default_namespace:
    vars(scope).update(module.get_init_globals())
    scope.__module__ = module.namespace
  scope.__file__ = filename
  scope.__name__ = __name__
  exec(code, vars(scope))

  return scope


def include_defs(filename, globals=None):
  """
  Uses :mod:`load_file` to load a Python file and then copies all symbols
  that do not start with an underscore into the *globals* dictionary. If
  *globals* is not specified, it will fall back to the globals of the frame
  that calls the function.
  """

  module = load_file(filename)
  if globals is None:
    globals = sys._getframe(1).f_globals
  for key, value in vars(module).items():
    if not key.startswith('_'):
      globals[key] = value


def gentool(commands, preamble=None, environ=None, name=None):
  """
  Create a :class:`~build.Tool` object. The name of the tool will be derived
  from the variable name it is assigned to unless *name* is specified.
  """

  tool = build.Tool(name, commands, preamble, environ)
  craftr.graph.add_tool(tool)
  return tool


def gentarget(name, commands, inputs=(), outputs=(), *args, **kwargs):
  """
  Create a :class:`~build.Target` object. The name of the target will be
  derived from the variable name it is assigned to unless *name* is specified.
  """

  target = build.Target(gtn(name), commands, inputs, outputs, *args, **kwargs)
  craftr.current_namespace().register_target(name, target)
  return target


def genalias(*targets, name, **kwargs):
  """
  Create a target that serves as an alias for all targets list in *targets*.
  """

  return gentarget([['echo', 'alias: ' + name]], name=name,
    implicit_deps = targets, **kwargs)


def gentask(func, args = None, inputs = (), outputs = (), name = None, **kwargs):
  """
  Create a Task that can be embedded into the build chain. Tasks can have input
  and output files that cause the task to be embedded into the build chain. By
  default, tasks need to be explicitly built or required by other targets.

  If *args* is not specified, it will be replaced by ``[inputs, outputs]``.

  :param func: A function to call to execute the task. It must accept a
    variable number of arguments, which are the arguments passed via the *args*
    parameter. This function will be called from Ninja using the ``craftr run``
    command.
  :param args: A list of arguments to pass to *func*. Note that non-string
    arguments will be pickled, compressed and and encoded in base64, prefixed
    with the string `pickle://`. These will be unpickled when the task is run.
    Note that ``$in`` and ``$out`` will be expanded in this argument list.
  :param inputs: A list of input files.
  :param inputs: A list of output files.
  :param name: Alternative target name.
  :param kwargs: Additional parameters for the :class:`Task` constructor.
  :return: A :class:`Target` object.
  """

  if args is None:
    args = [inputs, outputs]
  builder = TargetBuilder(name, inputs = inputs)
  task = build.Task(builder.name, func, args)
  return craftr.graph.add_task(task, inputs = builder.inputs, outputs = outputs)


def task(inputs = (), outputs = (), args = None, **kwargs):
  """
  Generate a one-off task. Optionally you can specified a list of *inputs*
  and *outputs*. If *args* is not specified, the *inputs* and *outputs* will
  be passed as arguments to the task function. Otherwise, *args* will be
  passed.
  """

  def decorator(func):
    return gentask(func, args, inputs, outputs, name = func.__name__, **kwargs)
  return decorator


def runtarget(target, *args, inputs=(), outputs=(), name, **kwargs):
  """
  Simplification of :func:`gentarget` to make it more obvious that a
  generate target is actually executed.
  """

  kwargs.setdefault('explicit', True)
  kwargs.setdefault('pool', 'console')
  return gentarget(name, [target.runprefix + [target] + list(args)], inputs, outputs, **kwargs)


def write_response_file(arguments, builder=None, name=None, force_file=False, suffix=''):
  """
  Creates a response-file with the specified *name* in the in the
  ``buildfiles/`` directory and writes the *arguments* list quoted into
  the file. If *builder* is specified, it must be a :class:`TargetBuilder`
  and the response file will be added to the implicit dependencies.

  If *force_file* is set to True, a file will always be written. Otherwise,
  the function will into possible limitations of the platform and decide
  whether to write a response file or to return the *arguments* as is.

  Returns a tuple of ``(filename, arguments)``. If a response file is written,
  the returned *arguments* will be a list with a single string that is the
  filename prepended with ``@``. The *filename* part can be None if no
  response file needed to be exported.
  """

  if not name:
    if not builder:
      raise ValueError('builder must be specified if name is bot')
    name = builder.name + suffix + '.response.txt'

  if not platform.WINDOWS:
    return None, arguments

  # We'll just assume that there won't be more than 2048 characters for
  # other flags. The windows max buffer size is 8192.
  content = shell.join(arguments)
  if len(content) < 6144:
    return None, arguments

  filename = buildlocal(path.join('buildfiles', name))
  if builder:
    builder.implicit_deps.append(filename)

  if craftr.do_export:
    path.makedirs(path.dirname(filename))
    with open(filename, 'w') as fp:
      fp.write(content)
  return filename, ['@' + filename]


def error(*message):
  """
  Raises a :class:`ModuleError` exception.
  """

  raise ModuleError(' '.join(map(str, message)))


def return_():
  """
  Raises a :class:`ModuleReturn` exception.
  """

  raise ModuleReturn


def append_PATH(*paths):
  """
  This is a helper function that is used to generate a ``PATH`` environment
  variable from the value that already exists and add the specified *paths*
  to it. It is typically used for example like this:

  .. code:: python

    run = gentarget(
      commands = [[main, local('example.ini')]],
      explicit=True,
      environ = {'PATH': append_PATH(qt5.bin_dir if qt5 else None)}
    )
  """

  result = os.getenv('PATH')
  paths = path.pathsep.join(filter(bool, paths))
  if paths:
    result += path.pathsep + paths
  return result


def option(name, type=str, inherit=True, default=NotImplemented, help=None):
  """
  Extracts an option from the Craftr context options and returns it.
  """

  full_name = gtn(name)
  if full_name in craftr.options:
    value = craftr.options[full_name]
  elif inherit and name in craftr.options:
    value = craftr.options[name]
  else:
    if default is NotImplemented:
      return type()
    return default

  return type(value)


__all__ = ['ToolDetectionError', 'ModuleError', 'ModuleReturn',
    'gtn', 'glob', 'local', 'buildlocal', 'relocate_files', 'filter',
    'map', 'zip', 'load_file', 'include_defs', 'gentool', 'gentarget',
    'genalias', 'gentask', 'task', 'write_response_file', 'error', 'return_',
    'append_PATH', 'runtarget',
    'pkg_config', 'external_archive', 'external_file',
    'TargetBuilder', 'Framework',
    'option', 'platform', 'logger', 'shell', 'path']
