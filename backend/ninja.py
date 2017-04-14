# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import json
import re
from ninja_syntax import Writer as NinjaWriter
path = require('../path')
shell = require('../shell')
platform = require('../platform')

class Exporter(object):
  """
  Exporter for Ninja manifests from Craftr build information.
  """

  def __init__(self, craftr, builddir=None, commandsdir=None):
    self.craftr = craftr
    self.builddir = builddir or craftr.option('builddir')
    self.commandsdir = commandsdir or path.join(self.builddir, 'ninja_commands')

  def export(self, file):
    if file is None:
      file = path.join(self.builddir, 'build.ninja')
    if isinstance(file, str):
      path.makedirs(path.dir(file))
      with open(file, 'w') as fp:
        self.write_all(NinjaWriter(fp))
    else:
      self.write_all(NinjaWriter(file))

  def write_all(self, writer):
    with open(path.join(__directory__, '../package.json')) as fp:
      version = json.load(fp)['version']
    writer.comment('Generated with Craftr v{}'.format(version))
    writer.comment('From working directory: {}'.format(path.cwd()))
    writer.newline()
    for key, value in self.craftr.options.items():
      if key.startswith('ninja:'):
        writer.variable(key[6:], value)
    for rule in self.craftr.rules.values():
      self.write_rule(rule, writer)

  def write_rule(self, rule, writer):
    if rule.name == 'phony':
      raise ValueError('rule name "phony" is reserved')
    writer.comment('Rule: {!r}'.format(rule.name))
    command_files, command = prep_commands(
        self.commandsdir, rule.commands, rule.name, rule.cwd, rule.env)
    writer.rule(ninjafy(rule.name), shell.join(command), pool=rule.pool, deps=rule.deps,
        depfile=rule.depfile, description=rule.description)
    writer.newline()
    for target in rule.targets:
      self.write_target(target, writer)

  def write_target(self, target, writer):
    rule = ninjafy(target.rule.name)
    if target.foreach:
      assert len(target.inputs) == len(target.outputs), target
      for inf, outf in zip(target.inputs, target.outputs):
        writer.build([outf], rule, [inf], implicit=target.implicit,
            order_only=target.order_only)
    else:
      writer.build(target.outputs or [self.name], rule, target.inputs,
          implicit=target.implicit, order_only=target.order_only)
    if target.name and target.outputs and target.name not in target.outputs:
      writer.build(target.name, 'phony', target.outputs)

def export(craftr, file=None):
  exporter = Exporter(craftr)
  return exporter.export(file)

def ninjafy(name):
  return re.sub('[^a-zA-Z0-9_]', '_', name)

def prep_commands(commandsdir, commands, rule_name, cwd=None, env=None):
  """
  This function prepares a list of one or more commands and returns a list of
  generated files and the possibly changed command. For a single command in
  *commands*, that single command is usually returned unchanged.

  !!!note "Keep in mind:
      The second element of the returned tuple is only a single command (thus
      only a list of str instead of a list of list of str)! If multiple
      commands are specified, usually these commands will be exported into a
      separate file and a single command to invoke that file will be returned.

  # Return
  (list of str, list of str)
  """

  if not commands:
    raise ValueError('a rule requires at least one command ({!r})'.format(rule_name))
  if len(commands) != 1:
    raise RuntimeError('only single commands are currently supported')
  if env:
    raise RuntimeError('command environment currently not supported')

  # TODO: ISSUE craftr-build/craftr#67
  # On Windows, commands that are not executables need to be invoked via CMD.

  command = commands[0]
  if cwd and platform.UNIXLIKE:
    command = [shell.safe('('), 'cd', cwd, shell.safe('&&')] + command + [shell.safe(')')]
  elif cwd and platform.WINDOWS:
    command = ['cmd', '/c', 'cd', cwd, shell.safe('&&')] + command

  return [], command
