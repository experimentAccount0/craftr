# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

from collections import Mapping, Sequence
from operator import itemgetter
import json
import textwrap
import sys
argschema = require('ppym/lib/argschema')
logger = require('./logger')
path = require('./path')
platform = require('./platform')
pyutils = require('./pyutils')
shell = require('./shell')

action = 'run'
builddir = 'build'
backend = './backend/ninja'
buildtype = 'develop'  #: choices are 'develop', 'debug' and 'release'
options = {}
rules = {}
targets = {}
products = {}
pools = {}
cache = {}

def option(name, type=str, default=NotImplemented, inherit=True):
  """
  Retrieve an option value of the specified *type* by *name*. If *inherit* is
  #True, the namespace of *name* will be removed and checked again. The
  namespace separate is `:`. The option value is read from the global #options
  dictionary.

  # Example

  ```python
  version = craftr.option('curl:version')
  build_examples = craftr.option('curl:build_examples', bool)
  ```
  """

  value = NotImplemented
  if name in options:
    value = options[name]
  elif ':' in name:
    name = name.split(':', 1)[1]
    if name in options:
      value = options[name]
  if value is NotImplemented:
    if default is NotImplemented:
      return type()
    return default

  if type == bool:
    value = str(value).strip().lower()
    if value in ('yes', 'on', 'true', '1'):
      value = True
    elif value in ('no', 'off', 'false', '0'):
      value = False
    else:
      raise ValueError("invalid value for option {!r} of type 'bool': {!r}"
          .format(name, value))
  else:
    try:
      value = type(value)
    except (ValueError, TypeError) as exc:
      raise ValueError("invalid value for option {!r} of type 'str': {!r} ({})"
          .format(name, value, exc))

  return value

def rule(name, commands, pool=None, deps=None, depfile=None, cwd=None,
         env=None, description=None):
  """
  Creates a new build rule that can be referenced when creating a build target
  with the #target() function. The *commands* parameter must be a list of list
  of string, representing one or more command-line argument sequences.
  """

  argschema.validate('name', name, {'type': str})
  argschema.validate('commands', commands,
      {'type': Sequence, 'items': {'type': Sequence, 'items': {'type': str}}})
  argschema.validate('pool', pool, {'type': [None, str]})
  argschema.validate('deps', deps, {'type': [None, str]})
  argschema.validate('depfile', depfile, {'type': [None, str]})
  argschema.validate('description', description, {'type': [None, str]})
  argschema.validate('cwd', cwd, {'type': [None, str]})
  argschema.validate('env', env, {'type': [None, dict]})

  if name in rules:
    raise ValueError('rule {!r} already exists'.format(rule))
  if pool and pool not in pools:
    raise ValueError('pool {!r} does not exist'.format(pool))
  if deps and deps not in ('gcc', 'msvc'):
    raise ValueError("invalid value for 'deps': {!r}'".format(deps))

  rule = Rule(
    name = name,
    commands = commands,
    pool = pool,
    deps = deps,
    depfile = depfile,
    description = description,
    cwd = cwd,
    env = env
  )
  rules[name] = rule
  return rule

def target(name, rule, inputs=(), outputs=(), implicit=(),
           order_only=(), foreach=False):
  """
  Create a target using the specified *rule* using the *inputs* and *outputs*.
  If no *name* is specified, the target will not be aliased.
  """

  argschema.validate('name', name, {'type': [None, str]})
  argschema.validate('rule', rule, {'type': [Rule, str]})
  argschema.validate('inputs', inputs, {'type': Sequence})
  argschema.validate('outputs', outputs, {'type': Sequence})
  argschema.validate('implicit', implicit, {'type': Sequence})
  argschema.validate('order_only', order_only, {'type': Sequence})

  if isinstance(rule, str):
    if rule not in rules:
      raise ValueError('rule {!r} does not exist'.format(rule))
    rule = rules[rule]
  if name is not None and name in targets:
    raise ValueError('target {!r} already exists'.format(name))

  target = Target(
    name = name,
    rule = rule,
    inputs = [path.norm(x) for x in inputs],
    outputs = [path.norm(x) for x in outputs],
    implicit = [path.norm(x) for x in implicit],
    order_only = [path.norm(x) for x in order_only],
    foreach = foreach,
  )
  if name is not None:
    targets[name] = target
  rule.targets.append(target)
  return target

def product(name, type, meta=None, **data):
  """
  Creates a named #Product instance and returns it. A product represents
  a collection of information on a build artefact that can be included in
  other build procedures, usually libraries.

  Note that products can also be created dynamically, which is why the
  #resolve_product() function should always be used to resolve a product
  name reference to an actual #Product instance.
  """

  if name in products:
    raise ValueError('product {!r} already exists'.format(name))
  product = Product(name, type, meta, data)
  products[name] = product
  return product

def resolve_target(name):
  if name.startswith(':'):
    name = get_current_namespace() + name
  elif name.startswith('//'):
    name = name[2:]
  if name not in targets:
    raise ResolveError('target {!r} does not exist'.format(name))
  return targets[name]

def resolve_product(name):
  """
  This function is used to search for a #Product in the registered #products
  dictionary or eventually invoke a dynamic product generation process based
  on the *name*.

  Currently, only the special `pkg-config:<libname>` names are supported for
  dynamic product creation.
  """

  if name.startswith(':'):
    name = get_current_namespace() + name
  elif name.startswith('//'):
    name = name[2:]

  if name in products:
    return products[name]
  if name.startswith('pkg-config:'):
    libname = name[11:]
    try:
      product = pkg_config(libname)
    except PkgConfigError as exc:
      raise ResolveError(exc)
    products[name] = product
    return product
  raise ResolveError('product {!r} does not exist'.format(name))

def pkg_config(pkg_name, static=False):
  """
  If available, this function uses `pkg-config` to extract flags for compiling
  and linking with the package specified with *pkg_name*. If `pkg-config` is
  not available or the it can not find the package, a #PkgConfigError is raised.

  Returns a #Product object.
  """

  cmdversion = ['pkg-config', '--modversion', pkg_name]
  cmdflags = ['pkg-config', '--cflags', '--libs']
  if static:
    cmdflags.append('--static')
  cmdflags.append(pkg_name)

  try:
    flags = shell.pipe(cmdflags, check=True).stdout
    version = shell.pipe(cmdversion, check=True).stdout.rstrip()
  except FileNotFoundError as exc:
    raise PkgConfigError('pkg-config is not available ({})'.format(exc))
  except shell.CalledProcessError as exc:
    raise PkgConfigError('{} not installed on this system\n\n{}'.format(
        pkg_name, exc.stderr or exc.stdout))

  product = Product('pkg-config:' + pkg_name, 'cxx',
      meta={'name': pkg_name, 'version': version})
  # TODO: What about a C++ library? Is it okay to use ccflags nevertheless? Or
  #       how do we otherwise find out if the library is a C++ library?

  for flag in shell.split(flags):
    if flag.startswith('-I'):
      product.data.setdefault('includes', []).append(flag[2:])
    elif flag.startswith('-D'):
      product.data.setdefault('defines', []).append(flag[2:])
    elif flag.startswith('-l'):
      product.data.setdefault('libs', []).append(flag[2:])
    elif flag.startswith('-L'):
      product.data.setdefault('libpath', []).append(flag[2:])
    elif flag.startswith('-Wl,'):
      product.data.setdefault('ldflags', []).append(flag[4:])
    else:
      product.data.setdefault('ccflags', []).append(flag)

  return product

def grn(name, prefix):
  """
  This function can be used in functions that generate build targets if no
  rule name has been specified to retrieve a unique rule name, assuming that
  no call to #rule() follows before the rule with the returned name has been
  created.

  If *name* is specified, it will be returned as-is, unless it does not
  contain a `:` character, in in which case it is concatenated with the
  currently executed module's `namespace` variable.
  """

  if name:
    if ':' not in name:
      name = get_current_namespace() + ':' + name
    return name

  index = 0
  while True:
    name = '{}_{:0>4d}'.format(prefix, index)
    if name not in rules:
      break
    index += 1
  return name

def get_current_namespace():
  """
  Returns the value of the `namespace` variable that is specified in the
  currently executed module, or raises a #RuntimeError if it is not
  specified.
  """

  if 'namespace' not in vars(require.current.namespace):
    raise RuntimeError("Relative target name specified, but currently "
        "executed module '{}' does not provide a 'namespace' variable.\n"
        "Please put 'namespace = \"mynamespace\"' at the beginning of "
        "your Craftr build script.".format(require.current.filename))
  return require.current.namespace.namespace

def load_cache(builddir=None):
  """
  Loads the last cache from the specified *builddir* or alternatively the
  `builddir` option into the #cache dictionary.
  """

  builddir = builddir or globals()['builddir']
  cachefile = path.join(builddir, '.craftr_cache')
  if not path.isfile(cachefile):
    return
  with open(cachefile, 'r') as fp:
    cache.update(json.load(fp))

def save_cache(builddir=None):
  """
  Saves the #cache dictionary in JSON format to the `.craftr_cache` file in
  the specified *builddir*.
  """

  builddir = builddir or globals()['builddir']
  cachefile = path.join(builddir, '.craftr_cache')
  path.makedirs(builddir)
  cache['backend'] = backend
  cache['options'] = options
  with open(cachefile, 'w') as fp:
    json.dump(cache, fp)

def export(file=None, backend=None):
  """
  Exports a build manifest to *file* using the specified *backend*. If the
  *backend* is not specified, it will default to what is globally configured
  in the #backend variable. If the *file* is omitted, it will default to
  whatever the backend prefers (usually taking the #builddir into account).

  Note that most backends expect an actual filename for *file* and some may
  support a file-like object.
  """

  if backend is None:
    backend = globals()['backend']
  if isinstance(backend, str):
    backend = require(backend)
  return backend.export(module.namespace, file)

def error(*objects, code=1):
  """
  Raise an #Error exception with the message specified with *objects*. If
  uncatched, the exception will be handled by a special exception handler.
  """

  raise Error(' '.join(map(str, objects)), code)

class Rule(object):

  def __init__(self, name, commands, pool, deps, depfile, cwd, env, description):
    self.name = name
    self.commands = commands
    self.pool = pool
    self.deps = deps
    self.depfile = depfile
    self.cwd = cwd
    self.env = env
    self.description = description
    self.targets = []

  def __repr__(self):
    return '<craftr.Rule {!r}>'.format(self.name)

  def target(self, name=None, inputs=(), outputs=(), implicit=(), order_only=(), foreach=False):
    return target(name, self.name, inputs, outputs, implicit, order_only, foreach)

class Target(object):

  def __init__(self, name, rule, inputs, outputs, implicit, order_only, foreach):
    self.name = name
    self.rule = rule
    self.inputs = inputs
    self.outputs = outputs
    self.implicit = implicit
    self.order_only = order_only
    self.foreach = foreach

  def __repr__(self):
    return '<craftr.Target {} :: {!r}>'.format(
        repr(self.name) if self.name else '<unnamed>', self.rule.name)

class Product(Mapping):
  """
  A #Product is an extended representation of a build target with additional
  information that is used by target generating functions. It may also
  represent externally produced build information. An example of this is the
  #pkg_config() function which returns a #Product that does not represent a
  #Target but instead an external library.

  Keys in a #Product are automatically prefixed with the product's #type as
  in `type:key`. This ensures proper namespacing of option values in products
  of different types.

  # Members
  name (str): The name of the product. For automatically generated Products
      from a target generator function, this is usually the target name.
  type (str): A product type identifier. For example, the type identifier
      for C/C++ libraries is `'cxx'`.
  data (dict): A dictionary that contains the product information. The format
      of this information depends on the Product's #types.
  """

  def __init__(self, name, type, meta, data):
    argschema.validate('name', name, {'type': str})
    argschema.validate('type', type, {'type': str})
    argschema.validate('meta', meta, {'type': [None, dict]})
    argschema.validate('data.keys()', data.keys(), {'items': {'type': str}})
    self.name = name
    self.type = type
    self.meta = meta if meta is not None else {}
    self.data = data

  def __iter__(self):
    for key in self.data:
      yield self.type + ':' + key

  def __len__(self):
    return len(self.data)

  def __contains__(self, key):
    if not key.startswith(self.type + ':'):
      return False
    key = key[len(self.type) + 1:]
    return key in self.data

  def __eq__(self, other):
    """
    Returns #True if the #other Product has at least one type in common with
    this Product and the #data matches exactly. Does **not** take the Product
    #name into account.
    """

    if not isinstance(other, Product):
      return False
    if self.type != other.type:
      return False
    return self.data == other.data

  def __repr__(self):
    return 'Product({!r}, {!r})'.format(self.name, self.type)

  def __str__(self):
    lines = ['Product({!r}, {!r})'.format(self.name, self.type)]
    if self.data or self.meta: lines[0] += ':'
    for key, value in sorted(self.data.items(), key=itemgetter(0)):
      lines.append('  | {}: {!r}'.format(key, value))
    if self.meta:
      lines.append('  Metadata:')
    for key, value in sorted(self.meta.items(), key=itemgetter(0)):
      lines.append('    | {}: {!r}'.format(key, value))
    return '\n'.join(lines)

  def __getitem__(self, key):
    argschema.validate('key', key, {'type': str})
    if not key.startswith(self.type + ':'):
      raise KeyError(key)
    try:
      return self.data[key[len(self.type) + 1:]]
    except KeyError as exc:
      raise KeyError(key) from exc

  def __setitem__(self, key, value):
    argschema.validate('key', key, {'type': str})
    if ':' in key and not key.startswith(self.type + ':'):
      raise KeyError(key)
    if ':' in key:
      key = key[len(self.type) + 1]
    self.data[key] = value

class Merge(Mapping):
  """
  This class is a collection of #Mapping#s, usually #Product instances or
  #dict#ionaries, and treats them as one merged #Mapping. Additionally, it
  allows to retrieve values cummulatively using #getlist().

  Setting items on the #Merge instance will cause the value to be found
  as the first value when using #__getitem__() but will cause the value to
  be treated cumulative to previously set values when using #getlist().

  # Members
  mappings (list of Mapping): The mappings specified upon initialization.
      If one or more *recursive_keys* was specified, #Merge.expand() was
      used to expand any nested mappings into a flat list.
  used_keys (set of str): A set of the keys that have been used to access
      properties in this #Merge instance. This is used to check for unused
      option values passed to target generator functions.
  """

  def __init__(self, mappings, recursive_keys=()):
    self.mappings = list(Merge.expand(mappings, recursive_keys))
    self.mappings.insert(0, {})
    self.used_keys = set()

  @staticmethod
  def expand(mappings, recursive_keys):
    if not recursive_keys:
      yield from mappings
      return
    for obj in mappings:
      yield obj
      for key in recursive_keys:
        try:
          children = obj[key]
        except KeyError:
          pass
        else:
          if isinstance(children, Mapping):
            children = [children]
          yield from Merge.expand(children, recursive_keys)

  def __iter__(self):
    keys = set()
    for obj in self.mappings:
      for key in obj:
        if key not in keys:
          keys.add(key)
          yield key

  def __len__(self):
    return sum(1 for __ in self)

  def __contains__(self, key):
    for obj in self.mappings:
      if key in obj:
        return True
    return False

  def __str__(self):
    lines = ['Merge of:']
    for obj in self.mappings:
      lines.extend(textwrap.indent(str(obj), '  ').split('\n'))
    return '\n'.join(lines)

  def __getitem__(self, key):
    self.used_keys.add(key)
    for obj in self.mappings:
      if isinstance(obj, Mapping):
        try:
          return obj[key]
        except KeyError: pass
      else:
        try:
          return getattr(obj, key)
        except AttributeError: pass
    raise KeyError(key)

  def __setitem__(self, key, value):
    if key in self.mappings[0]:
      self.mappings.insert(0, {})
    self.mappings[key] = value

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def getlist(self, key):
    """
    Collects all values associated with the specified *key* in the objects
    passed in the #Merge constructor into a list and returns it.
    """

    self.used_keys.add(key)
    result = []
    for obj in self.mappings:
      try:
        value = obj[key]
      except KeyError:
        continue
      if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError('expected non-string sequence for {!r}'.format(key), obj)
      result.extend(value)
    return result

class Error(Exception):
  """
  Raised by #error().
  """

  def __init__(self, message, code=1):
    self.message = str(message)
    self.code = code

  def __str__(self):
    return self.message

class PkgConfigError(Error):
  """
  Raised by #pkg_config().
  """

class ResolveError(Exception):
  """
  Raised when a target or product name could not be resolved.
  """

def local(*parts):
  """
  Accepts a relative path and returns its absolute representation, assuming
  it be relative to the currently executed module.
  """

  return path.norm(path.join(*parts), require.current.directory)

def buildlocal(*parts):
  """
  Accepts a relative path and returns its absolute representation, assuming
  it be relative to the build output directory specified in #builddir.

  If a `:` appears in the path passed to this function, it will be replaced
  by #path.sep. This is to conveniently support generating a build output
  directory from a target name,
  """

  p = path.join(*parts).replace(':', path.sep)
  return path.norm(p, path.abs(builddir))

def split_input_list(inputs):
  """
  Accepts as inputs a string or a #Product, or a list mixed of such objects.
  Separates lists of input files and #Product#s and returns a tuple containung
  the respective items.

  Strings may be of the format `//<targetname>` in which case they are
  substituted by the outputs of the referenced target.
  """

  argschema.validate('inputs', inputs, {'type': [Sequence, str, Product],
      'items': {'type': [str, Product]}})
  if isinstance(inputs, (str, Product)):
    inputs = [inputs]

  files = []
  products = []
  for item in inputs:
    if isinstance(item, str):
      if item.startswith('//') or item.startswith(':'):
        # Product existence is optional for inputs.
        try:
          product = resolve_product(item)
        except ResolveError: pass
        else:
          products.append(product)
        # Target existence however is mandatory.
        target = resolve_target(item)
        files += target.outputs
      else:
        files.append(item)
    elif isinstance(item, Product):
      products.append(item)
      for target in item.targets:
        files += target.outputs
    else: assert False

  return files, products

def register_nodepy_extension():
  """
  Registers `Craftrfile` to the current Node.py Context's index files and
  associates it to be loaded with the `.py` loader.
  """

  require.context.register_index_file('Craftrfile')
  require.context.register_extension('Craftrfile', require.context.get_extension('.py'))
