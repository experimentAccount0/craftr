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

import contextlib
import logging
import textwrap
import term from './lib/terminal'


class Formatter(logging.Formatter):
  """
  Special formatter for level color coding and terminal color formatting with
  the #term.format() function. This formatter should only be used with stream
  handlers for standard output or error.
  """

  level_info = {
    'CRITICAL': {'prefix': '!crit: ', 'color': 'red', 'on_color': 'white'},
    'ERROR':    {'prefix': 'error: ', 'color': 'red'},
    'WARNING':  {'prefix': ' warn: ', 'color': 'magenta'},
    'INFO':     {}, # {'prefix': 'info: ', 'color': 'blue'},
    'DEBUG':    {'prefix': 'debug: ', 'color': 'yellow'},
  }

  def __init__(self, logger, prefix=''):
    self.prefix = prefix
    self.logger = logger
    self.indent_prefix = '  '

  def format(self, record):
    #result = prefix + result[len(self.prefix):] # , ' ' * len(self.prefix)


    info = self.level_info.get(record.levelname)
    prefix = self.prefix + info.get('prefix', '')
    indent_chars = self.indent_prefix * self.logger.indentation

    message = term.format(record.msg, *record.args)
    lines =  []
    for line in message.split('\n'):
      lines += textwrap.wrap(line, term.terminal_size()[0] - 1 - len(indent_chars))
    if prefix:
      lines = (prefix + x if i == 0 else ' ' * len(prefix) + x for i, x in enumerate(lines))
    lines = (indent_chars + x for x in lines)
    message = '\n'.join(lines)

    if 'color' in info or 'on_color' in info:
      message = term.colored(message, color=info.get('color'), on_color=info.get('on_color'))

    return message


class LoggerAdapter(logging.LoggerAdapter):

  DEBUG = logging.DEBUG
  INFO = logging.INFO
  WARNING = logging.WARNING
  ERROR = logging.ERROR
  CRITICAL = logging.CRITICAL

  indentation = 0

  @contextlib.contextmanager
  def indent(self, amount=1):
    self.indentation += amount
    try:
      yield
    finally:
      self.indentation -= amount


def init():
  logger = logging.Logger('craftr')
  handler = logging.StreamHandler()
  logger.addHandler(handler)

  logger = LoggerAdapter(logger, {})
  logger.setLevel(logger.INFO)
  handler.setFormatter(Formatter(logger))
  return logger


exports = init()
