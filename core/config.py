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
import typing as t


class OptionKey(t.NamedTuple):
  scope: t.Optional[str]
  name: str

  @classmethod
  def parse(cls, s: str) -> 'OptionKey':
    scope, sep, name = s.rpartition('.')
    if not scope and not sep and not name:
      raise ValueError('invalid option key: {!r}'.format(s))
    return cls(scope, name)


class Configuration:
  """
  This class represents the contents of a Craftr build configuration file.
  It is basically a cleaner interface for the #configparser.ConfigParser
  class.
  """

  def __init__(self):
    self._parser = configparser.SafeConfigParser()

  def read(self, filename: str) -> None:
    self._parser.read([filename])

  def write(self, filename: str) -> None:
    with open(filename, 'w') as fp:
      self._parser.write(fp)

  def __getitem__(self, key: str) -> str:
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if not self._parser.has_section(scope):
      raise KeyError(key)
    if not self._parser.has_option(scope, name):
      raise KeyError(key)
    return self._parser.get(scope, name)

  def __setitem__(self, key: str, value: str):
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if not self._parser.has_section(scope):
      self._parser.add_section(scope)
    self._parser.set(scope, name, value)

  def get(self, key: str, default: t.Any = None) -> t.Any:
    try:
      return self[key]
    except KeyError:
      return default

  def sections(self) -> t.List[str]:
    return self._parser.sections()

  def options(self, section: str = None) -> t.List[str]:
    if not section:
      options = []
      for section in self._parser.sections():
        options.extend(self.options(section))
      return options
    else:
      prefix = section + '.'
      try:
        return [prefix + opt for opt in self._parser.options(section)]
      except configparser.NoSectionError:
        return []
