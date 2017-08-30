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
A simple Click-like command-line parsing library based on `argparse`.
"""

import argparse
import sys


class Command:

  def __init__(self, func, **kwargs):
    if 'description' not in kwargs and func.__doc__:
      kwargs['description'] = func.__doc__
    self._parser = argparse.ArgumentParser(**kwargs)
    self._func = func
    self._args_from_queue()

  def __call__(self, argv=None):
    args = vars(self._parser.parse_args())
    return self._func(**args)

  def _args_from_queue(self):
    queue = getattr(self._func, '_queued_args', None)
    if queue is not None:
      delattr(self._func, '_queued_args')
      for a, kw in queue:
        self._parser.add_argument(*a, **kw)

  @classmethod
  def from_parser(cls, func, parser):
    self = object.__new__(cls)
    self._parser = parser
    self._func = func
    self._args_from_queue()
    return self

  @classmethod
  def decorator(cls, **kwargs):
    def inner_decorator(func):
      return cls(func, **kwargs)
    return inner_decorator


class Group(Command):

  def __init__(self, func, **kwargs):
    super().__init__(func, **kwargs)
    self._subparser = self._parser.add_subparsers(dest='__command__')
    self._subcommands = {}

  def __call__(self, argv=None):
    args = vars(self._parser.parse_args(argv))
    subc = args.pop('__command__')

    main_kwargs = {}
    for action in self._parser._actions:
      if action.default == '==SUPPRESS==': continue
      if action.dest == '__command__': continue
      main_kwargs[action.dest] = args.pop(action.dest)

    code = self._func(subc, **main_kwargs)
    if code in (None, 0) and subc is not None:
      code = self._subcommands[subc]._func(**args)

    return code

  def command(self, **kwargs):
    def inner_decorator(func):
      name = kwargs.get('name', func.__name__)
      parser = self._subparser.add_parser(name)
      command = Command.from_parser(func, parser)
      self._subcommands[name] = command
      return command
    return inner_decorator


def argument(*args, **kwargs):
  def inner_decorator(func):
    if not hasattr(func, '_queued_args'):
      func._queued_args = []
    func._queued_args.append((args, kwargs))
    return func
  return inner_decorator


command = Command.decorator
group = Group.decorator
