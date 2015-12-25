# Copyright (C) 2015  Niklas Rosenstein
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
''' Craftr is a meta build system for Ninja. '''

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '0.20.0-dev'

import sys
if sys.version < '3.4':
  raise EnvironmentError('craftr requires Python3.4')

from craftr import magic

session = magic.new_context('session')
module = magic.new_context('module')

from craftr import ext, path, ninja, warn

import builtins
import craftr
import collections
import os
import types

_path = path


class Session(object):
  ''' The `Session` object is the manage of a meta build session that
  manages the craftr modules and build `Target`s.

  Attributes:
    path: A list of additional search paths for Craftr modules.
    modules: A dictionary of craftr extension modules, without the
      `craftr.ext.` prefix.
    targets: A dictionary mapping full target names to actual `Target`
      objects that have been created. The `Target` constructors adds
      the object to this dictionary automatically.
    var: A dictionary of variables that will be exported to the Ninja
      build definitions file.
    extend_builtins: If this is True, the `builtins` module will be
      update when the Session's context is entered to contain the
      current session and module proxy and the `craftr.path` module.
    '''

  def __init__(self, cwd=None, path=None, extend_builtins=True):
    super().__init__()
    self.cwd = cwd or os.getcwd()
    self.env = os.environ.copy()
    self.extension_importer = ext.CraftrImporter(self)
    self.path = [_path.join(_path.dirname(__file__), 'lib')]
    self.modules = {}
    self.targets = {}
    self.var = {}
    self.extend_builtins = extend_builtins

    if path is not None:
      self.path.extend(path)

  def exec_if_exists(self, filename):
    ''' Executes *filename* if it exists. Used for running the Craftr
    environment files before the modules are loaded. Returns None if the
    file does not exist, a `types.ModuleType` object if it was executed. '''

    if not os.path.isfile(filename):
      return None

    # Create a fake module so we can enter a module context
    # for the environment script.
    temp_mod = types.ModuleType('craftr.ext.__temp__:' + filename)
    temp_mod.__file__ = filename
    init_module(temp_mod)
    temp_mod.__name__ = '__craftenv__'
    del temp_mod.__ident__

    with open(filename, 'r') as fp:
      code = compile(fp.read(), filename, 'exec')
    with magic.enter_context(module, temp_mod):
      exec(code, vars(module))

    return temp_mod

  def update(self):
    ''' See `extr.CraftrImporter.update()`. '''

    self.extension_importer.update()

  def on_context_enter(self, prev):
    if prev is not None:
      raise RuntimeError('session context can not be nested')

    if self.extend_builtins:
      builtins.session = session
      builtins.module = module
      builtins.path = path
      builtins.info = info
      builtins.error = error

    # We can not change os.environ effectively, we must update the
    # dictionary instead.
    self._old_environ = os.environ.copy()
    os.environ.clear()
    os.environ.update(self.env)
    self.env = os.environ

    sys.meta_path.append(self.extension_importer)
    self.update()

  def on_context_leave(self):
    ''' Remove all `craftr.ext.` modules from `sys.modules` and make
    sure they're all in `Session.modules` (the modules are expected
    to be put there by the `craftr.ext.CraftrImporter`). '''

    if self.extend_builtins:
      del builtins.session
      del builtins.module
      del builtins.path
      del builtins.info
      del builtins.error

    # Restore the original values of os.environ.
    self.env = os.environ.copy()
    os.environ.clear()
    os.environ.update(self._old_environ)
    del self._old_environ

    sys.meta_path.remove(self.extension_importer)
    for key, module in list(sys.modules.items()):
      if key.startswith('craftr.ext.'):
        name = key[11:]
        assert name in self.modules and self.modules[name] is module, key
        del sys.modules[key]
        try:
          # Remove the module from the `craftr.ext` modules contents, too.
          delattr(ext, name.split('.')[0])
        except AttributeError:
          pass


class Target(object):
  ''' This class is a direct representation of a Ninja rule and the
  corresponding in- and output files that will be built using that rule.

  Attributes:
    name: The name of the target. This is usually deduced from the
      variable the target is assigned to if no explicit name was
      passed to the `Target` constructor. Note that the actualy
      identifier of the target that can be passed to Ninja is
      concatenated with the `module` identifier.
    module: A Craftr extension module which this target belongs to. It
      can be specified on construction manually, or the current active
      module is used automatically.
    command: A list of strings that represents the command to execute.
    inputs: A list of filenames that are listed as direct inputs.
    outputs: A list of filenames that are generated by the target.
    implicit_deps: A list of filenames that mark the target as dirty
      if they changed and will cause it to be rebuilt, but that are
      not taken as direct input files (i.e. `$in` does not expand these
      files).
    order_only_deps: See "Order-only dependencies" in the [Ninja Manual][].
    foreach: A boolean value that determines if the command is appliead
      for each pair of filenames in `inputs` and `outputs`, or invoked
      only once. Note that if this is True, the number of elements in
      `inputs` and `outputs` must match!
    description: A description of the target to display when it is being
      built. This ends up as a variable definition to the target's rule,
      so you may use variables in this as well.
    pool: The name of the build pool. Defaults to None. Can be "console"
      for "targets" that don't actually build files but run a program.
      Craftr ensures that targets in the "console" pool are never
      executed implicitly when running Ninja.  # xxx: todo!
    deps: The mode for automatic dependency detection for C/C++ targets.
      See the "C/C++ Header Depenencies" section in the [Ninja Manual][].
    depfile: A filename that contains additional dependencies.
    msvc_deps_prefix: The MSVC dependencies prefix to be used for the rule.
    explicit: If True, the target will only be built by Ninja if it is
      explicitly targeted from the command-line or required by another
      target. Defaults to False.

  [Ninja Manual]: https://ninja-build.org/manual.html
  '''

  class Builder(object):
    ''' Helper class to build a target, used in rule functions. '''

    _unnamed_idx = 0

    @staticmethod
    def get_module(ref_module):
      if not ref_module:
        ref_module = module()
      assert isinstance(ref_module, types.ModuleType)
      assert ref_module.__name__.startswith('craftr.ext.')
      return ref_module

    @classmethod
    def get_name(cls, ref_module, name, generator=None):
      if not name:
        try:
          name = magic.get_assigned_name(magic.get_module_frame(ref_module))
        except ValueError:
          if not generator:
            raise
          name = '{0}_{1}'.format(generator, cls._unnamed_idx)
          cls._unnamed_idx += 1
      return name

    def __init__(self, generator=None, **kwargs):
      super().__init__()
      module = self.get_module(kwargs.pop('module', None))
      name = self.get_name(module, kwargs.pop('name', None), generator)
      self.data = {
        'module': module,
        'name': name,
        # 'command': [],
        # 'inputs': [],
        # 'outputs': [],
        'implicit_deps': list(kwargs.pop('implicit_deps', ())),
        'order_only_deps': list(kwargs.pop('order_only_deps', ())),
        'foreach': False,
        'pool': None,
        'description': None,
        'deps': None,
        'depfile': None,
        'msvc_deps_prefix': None,
        'meta': dict(kwargs.pop('meta', ())),
        'frameworks': list(kwargs.pop('frameworks', ())),
      }
      self.data.update(**kwargs)

    def __call__(self, *args, **kwargs):
      self.data.update(**kwargs)
      return Target(*args, **self.data)

    def __getattr__(self, key):
      return self.data[key]

    def __setattr__(self, key, value):
      if key == 'data' or key not in self.data:
        super().__setattr__(key, value)
      else:
        self.data[key] = value

    @property
    def fullname(self):
      return self.module.__ident__ + '.' + self.name

  def __init__(self, command, inputs=None, outputs=None, implicit_deps=None,
      order_only_deps=None, foreach=False, description=None, pool=None,
      var=None, deps=None, depfile=None, msvc_deps_prefix=None, meta=None,
      explicit=False,frameworks=None, module=None, name=None):

    module = Target.Builder.get_module(module)
    name = Target.Builder.get_name(module, name)

    if isinstance(command, str):
      command = shell.split(command)
    else:
      command = self._check_list_of_str('command', command)
    if not command:
      raise ValueError('command can not be empty')

    if inputs is not None:
      if isinstance(inputs, str):
        inputs = [inputs]
      inputs = expand_inputs(inputs)
      inputs = self._check_list_of_str('inputs', inputs)
    if outputs is not None:
      if isinstance(outputs, str):
        outputs = [outputs]
      elif callable(outputs):
        outputs = outputs(inputs)
      outputs = self._check_list_of_str('outputs', outputs)

    if foreach and len(inputs) != len(outputs):
      raise ValueError('len(inputs) must match len(outputs) in foreach Target')

    if implicit_deps is not None:
      implicit_deps = self._check_list_of_str('implicit_deps', implicit_deps)
    if order_only_deps is not None:
      order_only_deps = self._check_list_of_str('order_only_deps', order_only_deps)

    self.module = module
    self.name = name
    self.command = command
    self.inputs = inputs
    self.outputs = outputs
    self.implicit_deps = implicit_deps or []
    self.order_only_deps = order_only_deps or []
    self.foreach = foreach
    self.pool = pool
    self.description = description
    self.deps = deps
    self.depfile = depfile
    self.msvc_deps_prefix = msvc_deps_prefix
    self.meta = meta or {}
    self.frameworks = frameworks or []
    self.explicit = explicit

    targets = module.__session__.targets
    if self.fullname in targets:
      raise ValueError('target {0!r} already exists'.format(self.fullname))
    targets[self.fullname] = self

  def __repr__(self):
    pool = ' in "{0}"'.format(self.pool) if self.pool else ''
    command = ' running "{0}"'.format(self.command[0])
    return '<Target {self.fullname!r}{command}{pool}>'.format(**locals())

  @property
  def fullname(self):
    return self.module.__ident__ + '.' + self.name

  @staticmethod
  def _check_list_of_str(name, value):
    if not isinstance(value, str) and isinstance(value, collections.Iterable):
      value = list(value)
    if not isinstance(value, list):
      raise TypeError('expected list of str for {0}, got {1}'.format(
        name, type(value).__name__))
    for item in value:
      if not isinstance(item, str):
        raise TypeError('expected list of str for {0}, found {1} inside'.format(
          name, type(item).__name__))
    return value


class Framework(dict):
  ''' A framework rerpresentation a set of options that are to be taken
  into account by compiler classes. Eg. you might create a framework
  that contains the additional information and options required to
  compile code using OpenCL and pass that to the compiler interface.

  Compiler interfaces may also add items to `Target.frameworks`
  that can be taken into account by other target rules. `expand_inputs()`
  returns a list of frameworks that are being used in the inputs.

  Use the `Framework.Join` class to create an object to process the
  data from multiple frameworks. '''

  class Join(object):
    ''' Helper to process a collection of `Framework`s. '''

    def __init__(self, *frameworks):
      super().__init__()
      self.used_keys = set()
      self.frameworks = []
      for fw in frameworks:
        if isinstance(fw, (list, tuple)):
          self.frameworks.extend(fw)
        else:
          self.frameworks.append(fw)
      for fw in self.frameworks:
        if not isinstance(fw, Framework):
          raise TypeError('expected Framework, got {0}'.format(type(fw).__name__))

    def __getitem__(self, key):
      self.used_keys.add(key)
      for fw in self.frameworks:
        try:
          return fw[key]
        except KeyError:
          pass
      raise KeyError(key)

    def get(self, key, default=None):
      ''' Get the first available value of *key* from the frameworks. '''

      try:
        return self[key]
      except KeyError:
        return default

    def get_merge(self, key):
      ''' Merge all values of *key* in the frameworks into one list,
      assuming that every key is a non-string sequence and can be
      appended to a list. '''

      self.used_keys.add(key)
      result = []
      for fw in self.frameworks:
        try:
          value = fw[key]
        except KeyError:
          continue
        if not isinstance(value, collections.Sequence) or isinstance(value, str):
          raise TypeError('expected a non-string sequence for {0!r} '
            'in framework {1!r}, got {0}'.format(key, fw.name, type(value).__name__))
        result += value
      return result

  def __init__(self, __fw_name, __init_dict=None, **kwargs):
    super().__init__()
    if __init_dict is not None:
      self.update(__init_dict)
    self.update(kwargs)
    self.name = __fw_name

  def __repr__(self):
    return 'Framework(name={0!r}, {1})'.format(self.name, super().__repr__())


class ModuleError(RuntimeError):
  ''' This function is raised with `error()`. It will cause Craftr to
  exit with the supplied message. '''

  def __init__(self, message, module):
    self.message = message
    self.module = module

  def __str__(self):
    return 'craftr: error: [{0}] {1}'.format(self.module.project_name, self.message)


def info(*args, **kwargs):
  prefix = 'craftr: info: [{0}]'.format(module.project_name)
  print(prefix, *args, **kwargs)


def error(*objects, sep=' ', module=None):
  ''' Raise `ModuleError` with the specified message. '''

  message = sep.join(map(str, objects))
  if not module:
    module = globals()['module']()
  raise ModuleError(message, module)


def init_module(module):
  ''' Called when a craftr module is being imported before it is
  executed to initialize its contents. '''

  assert module.__name__.startswith('craftr.ext.')
  module.__session__ = session()
  module.project_dir = path.dirname(module.__file__)
  module.project_name = module.__name__[11:]

  # Backwards compatibility
  module.__ident__ = module.project_name


def finish_module(module):
  ''' Called when a craftr extension module was imported. This function
  makes sure that there is a `__all__` member on the module that excludes
  all the built-in names and that are not module objects. '''

  if not hasattr(module, '__all__'):
    module.__all__ = []
    for key in dir(module):
      if key.startswith('_') or key in ('project_dir', 'project_name'):
        continue
      if isinstance(getattr(module, key), types.ModuleType):
        continue
      module.__all__.append(key)


def expand_inputs(inputs, join=None):
  ''' Expands a list of inputs into a list of filenames. An input is a
  string (filename) or a `Target` object from which the `Target.outputs`
  are used. Returns a list of strings.

  If *join* is specified, it must be a `Framework.Join` object that
  will be appended the frameworks used in the Targets that were
  passed in *inputs*. '''

  result = []
  if isinstance(inputs, (str, Target)):
    inputs = [inputs]
  for item in inputs:
    if isinstance(item, Target):
      if join:
        join.frameworks += item.frameworks
      result += item.outputs
    elif isinstance(item, str):
      result.append(item)
    else:
      raise TypeError('input must be Target or str, got {0}'.format(type(item).__name__))
  return result


__all__ = ['craftr', 'expand_inputs', 'session', 'module', 'path', 'warn', 'Target', 'Framework']
