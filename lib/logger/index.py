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

import contextlib
import logging
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

  def format(self, record):
    if record.levelname in self.color_map:
      record.levelname = term.colored(record.levelname, **self.color_map[record.levelname])
    record.msg = term.format(str(record.msg), *record.args)
    record.args = ()
    return super().format(record)


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


def _init_logger():
  logger = logging.Logger('craftr')
  logger.setLevel(logging.DEBUG)
  formatter = Formatter('[%(levelname)s]: %(message)s')
  handler = logging.StreamHandler()
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  return LoggerAdapter(logger, {})


logger = _init_logger()
exports = logger
