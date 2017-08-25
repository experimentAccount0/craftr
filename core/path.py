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

import glob2
import os
import typing as t

from os import (
  sep,
  pathsep,
  curdir,
  pardir,
  getcwd as cwd
)
from os.path import (
  expanduser,
  normpath as canonical,
  isabs,
  isfile,
  isdir,
  exists,
  join,
  split,
  dirname as dir
)


def abs(path: str, parent: str = None) -> str:
  if not isabs(path):
    return join(parent or cwd(), path)
  return path


def rel(path: str, parent: str = None, par: bool = False) -> str:
  """
  Takes *path* and computes the relative path from *parent*. If *parent* is
  omitted, the current working directory is used.

  If *par* is #True, a relative path is always created when possible.
  Otherwise, a relative path is only returned if *path* lives inside the
  *parent* directory.
  """

  try:
    res = os.path.relpath(path, parent)
  except ValueError:
    # Raised eg. on Windows for differing drive letters.
    if not par:
      return abs(path)
    raise
  else:
    if not issub(res):
      return abs(path)
    return res


def issub(path: str) -> bool:
  """
  Returns #True if *path* is a relative path that does not point outside
  of its parent directory or is equal to its parent directory (thus, this
  function will also return False for a path like `./`).
  """

  if isabs(path):
    return False
  if path.startswith(curdir + sep) or path.startswith(pardir + sep):
    return False
  return True


def isglob(path):
  """
  # Parameters
  path (str): The string to check whether it represents a glob-pattern.

  # Returns
  #True if the path is a glob pattern, #False otherwise.
  """

  return '*' in path or '?' in path


def glob(patterns: t.Union[str, t.List[str]], parent: str = None,
         excludes: t.List[str] = None, include_dotfiles: bool = False,
         ignore_false_excludes: bool = False) -> t.List[str]:
  """
  Wrapper for #glob2.glob() that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with #norm().

  Relative patterns are automaticlly joined with *parent*. If the
  parameter is omitted, it defaults to the current working directory.

  If *excludes* is specified, it must be a string or a list of strings
  that is/contains glob patterns or filenames to be removed from the
  result before returning.

  > Every file listed in *excludes* will only remove **one** match from
  > the result list that was generated from *patterns*. Thus, if you
  > want to exclude some files with a pattern except for a specific file
  > that would also match that pattern, simply list that file another
  > time in the *patterns*.

  # Parameters
  patterns (list of str): A list of glob patterns or filenames.
  parent (str): The parent directory for relative paths.
  excludes (list of str): A list of glob patterns or filenames.
  include_dotfiles (bool): If True, `*` and `**` can also capture
    file or directory names starting with a dot.
  ignore_false_excludes (bool): False by default. If True, items listed
    in *excludes* that have not been globbed will raise an exception.

  # Returns
  list of str: A list of filenames.
  """

  if isinstance(patterns, str):
    patterns = [patterns]

  if not parent:
    parent = cwd()

  result = []
  for pattern in patterns:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    result += glob2.glob(canonical(pattern))

  for pattern in excludes:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    pattern = canonical(pattern)
    if not isglob(pattern):
      try:
        result.remove(pattern)
      except ValueError as exc:
        if not ignore_false_excludes:
          raise ValueError('{} ({})'.format(exc, pattern))
    else:
      for item in glob2.glob(pattern):
        try:
          result.remove(item)
        except ValueError as exc:
          if not ignore_false_excludes:
            raise ValueError('{} ({})'.format(exc, pattern))

  return result
