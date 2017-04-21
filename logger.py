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

  def __init__(self, logger, prefix='==> '):
    self.prefix = prefix
    self.logger = logger

  def format(self, record):
    result = textwrap.indent(record.msg.format(*record.args), ' '*len(self.prefix))
    result = self.prefix + result[len(self.prefix):]
    result = textwrap.indent(result, '  ' * self.logger.indentation)
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

def init_logger():
  logger = logging.Logger('craftr')
  handler = logging.StreamHandler()
  logger.addHandler(handler)

  logger = LoggerAdapter(logger, {})
  handler.setFormatter(Formatter(logger, prefix='==> '))
  return logger

exports = init_logger()
