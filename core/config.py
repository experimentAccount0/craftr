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

import configparser
import {TargetRef} from './utils'


class Configuration:
  """
  This class represents the contents of a Craftr build configuration file.
  It is basically a cleaner interface for the #configparser.ConfigParser
  class.
  """

  def __init__(self):
    self._parser = configparser.SafeConfigParser()

  def read(self, filename):
    self._parser.read([filename])

  def write(self, filename):
    with open(filename, 'w') as fp:
      self._parser.write(fp)

  def __getitem__(self, key):
    try:
      ref = TargetRef.from_str(key)
    except ValueError:
      raise KeyError(key)
    if not ref.isabs:
      raise KeyError(key)
    if not self._parser.has_section(ref.scope):
      raise KeyError(key)
    if not self._parser.has_option(ref.scope, ref.name):
      raise KeyError(key)
    return self._parser.get(ref.scope, ref.name)

  def __setitem__(self, key, value):
    try:
      ref = TargetRef.from_str(key)
    except ValueError:
      raise KeyError(key)
    if not ref.isabs:
      raise KeyError(key)
    if not self._parser.has_section(ref.scope):
      self._parser.add_section(ref.scope)
    self._parser.set(ref.scope, ref.name, value)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default
