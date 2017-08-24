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

import toml
import typing as t


class OptionKey(t.NamedTuple):
  scope: t.Optional[str]
  name: str

  @classmethod
  def parse(cls, s: str, allow_empty_name: bool = False) -> 'OptionKey':
    scope, sep, name = s.rpartition('.')
    if not scope and not sep:
      scope, name = name, ''
    valid = scope and ((sep and name) or allow_empty_name)
    if not valid:
      raise ValueError('invalid option key: {!r}'.format(s))
    return cls(scope, name)


class Configuration:
  """
  This class represents the contents of a Craftr build configuration file.
  It is basically a cleaner interface for the #configparser.ConfigParser
  class.
  """

  def __init__(self):
    self._data = {}

  def read(self, filename: str) -> None:
    with open(filename, 'r') as fp:
      # TODO: Catch possible ValueError (and others?) and transform them
      #       into a proper exception for configuration parsing.
      data = toml.load(fp)
    # TODO: Merge options inside sections.
    self._data.update(data)

  def write(self, filename: str) -> None:
    with open(filename, 'w') as fp:
      self._parser.write(fp)

  def __getitem__(self, key: str) -> str:
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      raise KeyError(key)
    if name not in self._data[scope]:
      raise KeyError(key)
    return self._data[scope][name]

  def __setitem__(self, key: str, value: str):
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      self._data[scope] = {}
    self._data[scope][name] = value

  def __delitem__(self, key: str):
    try:
      scope, name = OptionKey.parse(key, allow_empty_name=True)
    except ValueError:
      raise KeyError(key)
    if not name:
      del self._data[scope]
    else:
      del self._data[scope][name]

  def get(self, key: str, default: t.Any = None) -> t.Any:
    try:
      return self[key]
    except KeyError:
      return default

  def sections(self) -> t.List[str]:
    return self._data.keys()

  def options(self, section: str = None) -> t.List[str]:
    if not section:
      options = []
      for section in self._parser.keys():
        options.extend(self.options(section))
      return options
    else:
      prefix = section + '.'
      try:
        return [prefix + opt for opt in self._data[section].keys()]
      except KeyError:
        return []
