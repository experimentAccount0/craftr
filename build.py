# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.
"""
This module implements the representation of a build graph that can then be
converted to project files and build manifests by a backend implementation.
"""

from collections import Sequence
argschema = require('ppym/lib/argschema')
path = require('./path')

class BuildContainer:
  """
  The #BuildContainer is a collection of all the available build information,
  including pools, rules and targets.
  """

  def __init__(self):
    self.pools = {'console': Pool.console}
    self.rules = {}
    self.targets = {}

  def pool(self, name):
    if name in self.pools:
      raise ValueError("pool '{}' already exists".format(name))
    pool = self.pools[name] = Pool(name)
    return pool

  def rule(self, name, *args, **kwargs):
    if name in self.rules:
      raise ValueError("rule '{}' already exists".format(name))
    rule = self.rules[name] = Rule(name, *args, **kwargs)
    return rule

  def target(self, name, *args, **kwargs):
    if name is not None and name in self.targets:
      raise ValueError("target '{}' already exists".format(name))
    target = Target(name, *args, **kwargs)
    if name is not None:
      self.targets[name] = target
    return target

class Pool:
  """
  A #Pool allows you to allocate one or more rules or edges a finite number
  of concurrent jobs which is more tightly restricted than the default
  parallelism.

  Backends that do not support pools can usually ignore them.
  """

  #: Assigned the default pool that is used to execute jobs synchronously
  #: in the shell with stdin attached to the terminal.
  console = None

  def __init__(self, name):
    argschema.validate('name', name, {'type': str})
    self.name = name

  def __repr__(self):
    return "<Pool '{}'>".format(self.name)

Pool.console = Pool('console')

class Rule:
  """
  A #Rule defines how a set of input files is transformed to a set of output
  files. A rule may also produce no files. Many times, one rule only exists
  for one #Target.
  """

  def __init__(self, name, commands, pool=None, deps=None, depfile=None,
               cwd=None, env=None, description=None):
    argschema.validate('name', name, {'type': str})
    argschema.validate('commands', commands,
        {'type': Sequence, 'items': {'type': Sequence, 'items': {'type': str}}})
    argschema.validate('pool', pool, {'type': [None, Pool]})
    argschema.validate('deps', deps, {'type': [None, str]})
    argschema.validate('depfile', depfile, {'type': [None, str]})
    argschema.validate('description', description, {'type': [None, str]})
    argschema.validate('cwd', cwd, {'type': [None, str]})
    argschema.validate('env', env, {'type': [None, dict]})

    self.name = name
    self.commands = commands
    self.pool = pool
    self.deps = deps
    self.depfile = depfile
    self.description = description
    self.cwd = cwd
    self.env = env
    self.targets = []

  def __repr__(self):
    return "<Rule '{}'>".format(self.name)

class Target:
  """
  A target specifies a rule and the input and output files for that rule.
  Many times there exists exactly one #Target for a #Rule.

  If a target is flagged as #foreach, the rule is applied for each pair of
  input and output files respectively.

  If a target is flagged as #explicit, it is not built by default, unless
  required by another target.
  """

  def __init__(self, name, rule, inputs=(), outputs=(), implicit=(),
               order_only=(), foreach=False, explicit=False):
    argschema.validate('name', name, {'type': [None, str]})
    argschema.validate('rule', rule, {'type': Rule})
    argschema.validate('inputs', inputs, {'type': Sequence})
    argschema.validate('outputs', outputs, {'type': Sequence})
    argschema.validate('implicit', implicit, {'type': Sequence})
    argschema.validate('order_only', order_only, {'type': Sequence})

    self.name = name
    self.rule = rule
    self.inputs = [path.abs(x) for x in inputs]
    self.outputs = [path.abs(x) for x in outputs]
    self.implicit = [path.abs(x) for x in implicit]
    self.order_only = [path.abs(x) for x in order_only]
    self.foreach = foreach
    self.explicit = explicit
    rule.targets.append(self)

  def __repr__(self):
    if self.name:
      return "<Target '{}'>".format(self.name)
    else:
      return "<unnamed Target of {}>".format(self.rule)
