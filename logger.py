# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import contextlib
import logging
import textwrap
term = require('./term')

class Formatter(logging.Formatter):
  """
  Special formatter for level color coding and terminal color formatting with
  the #term.format() function. This formatter should only be used with stream
  handlers for standard output or error.
  """

  color_map = {
    'CRITICAL': {'color': 'red', 'on_color': 'white'},
    'ERROR': {'color': 'red'},
    'WARNING': {'color': 'magenta'},
    'INFO': {'color': 'blue'},
    'DEBUG': {'color': 'yellow'},
  }

  def __init__(self, prefix='==> '):
    self.prefix = prefix

  def format(self, record):
    result = textwrap.indent(record.msg.format(*record.args), ' '*len(self.prefix))
    result = self.prefix + result[len(self.prefix):]
    if record.levelname in self.color_map:
      result = term.colored(result, **self.color_map[record.levelname])
    return result

class LoggerAdapter(logging.LoggerAdapter):

  indentation = 0

  @contextlib.contextmanager
  def indent(self, amount=1):
    self.indentation += amount
    try:
      yield
    finally:
      self.indentation -= amount

  def process(self, msg, kwargs):
    msg = '  ' * self.indentation + msg
    return (msg, kwargs)

def init_logger():
  handler = logging.StreamHandler()
  handler.setFormatter(Formatter(prefix='==> '))
  logger = logging.Logger('craftr')
  logger.addHandler(handler)
  return LoggerAdapter(logger, {})

exports = init_logger()
