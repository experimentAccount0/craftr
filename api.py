# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

from collections import Sequence
from operator import itemgetter
import json
argschema = require('ppym/lib/argschema')
path = require('./path')
platform = require('./platform')
shell = require('./shell')

action = 'run'
builddir = 'build'
backend = './backend/ninja'
options = {}
rules = {}
targets = {}
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
    foreach = foreach
  )
  if name is not None:
    targets[name] = target
  rule.targets.append(target)
  return target

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

  product = Product('pkg-config:' + pkg_name, 'cxx_library',
      includes = [], defines = [], libs = [], libpath = [],
      ccflags = [], ldflags = [], version = version)
  # TODO: What about a C++ library? Is it okay to use ccflags nevertheless? Or
  #       how do we otherwise find out if the library is a C++ library?

  for flag in shell.split(flags):
    if flag.startswith('-I'):
      product['includes'].append(flag[2:])
    elif flag.startswith('-D'):
      product['defines'].append(flag[2:])
    elif flag.startswith('-l'):
      product['libs'].append(flag[2:])
    elif flag.startswith('-L'):
      product['libpath'].append(flag[2:])
    elif flag.startswith('-Wl,'):
      product['ldflags'].append(flag[4:])
    else:
      product['ccflags'].append(flag)

  return product

def unique_rule_name(prefix):
  """
  This function can be used in functions that generate build targets if no
  rule name has been specified to retrieve a unique rule name, assuming that
  no call to #rule() follows before the rule with the returned name has been
  created.
  """

  index = 0
  while True:
    name = '{}_{:0>4d}'.format(prefix, index)
    if name not in rules:
      break
    index += 1
  return name

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

class Product(object):
  """
  A #Product is an extended representation of a build target with additional
  information that is used by target generating functions. It may also
  represent externally produced build information. An example of this is the
  #pkg_config() function which returns a #Product that does not further specify
  a #Target but instead represent an external library.

  # Members
  name (str): The name of the product. For automatically generated Products
      from a target generator function, this is usually the target name.
  types (list of str): A list of product type identifiers. For example, the
      type identifier for C/C++ libraries is `'cxx_library'`.
  targets (list of Target): A list of targets that this product wraps.
      Target generator functions may choose to use the outputs of these
      targets as new inputs.
  data (dict): A dictionary that contains the product information. The format
      of this information depends on the Product's #types.
  """

  def __init__(self, name, types, targets=None, **data):
    if isinstance(types, str):
      types = [types]
    for item in types:
      if not isinstance(item, str):
        raise ValueError('Product type must be str')
    self.name = name
    self.types = types
    self.data = data

  def __repr__(self):
    return 'Product({!r}, {})'.format(self.name, self.types)

  def __str__(self):
    lines = ['Product({!r}, {}):'.format(self.name, self.types)]
    for key, value in sorted(self.data.items(), key=itemgetter(0)):
      lines.append('  | {}: {!r}'.format(key, value))
    return '\n'.join(lines)

  def __getitem__(self, key):
    return self.data[key]

  def __setitem__(self, key, value):
    self.data[key] = value

class PkgConfigError(Exception):
  """
  Raised by #pkg_config().
  """
