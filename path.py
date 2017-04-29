# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

from os import getcwd as cwd
from os.path import (
    join, split, splitext, isabs, isfile, isdir, islink, ismount, samefile,
    curdir, pardir, sep, pathsep, dirname as dir, basename as base)
import errno
import glob as _glob
import os
import shutil
import tempfile as _tempfile

def makedirs(path):
  """
  Make sure that *path* is an existing directory. If it already exists and is
  a directory, no error will be raised. However, if the directory can not be
  created or if *path* is a file, an #OSError will be raised.
  """

  try:
    os.makedirs(path)
  except FileExistsError:
    pass  # intentional

def abs(path, parent=None):
  if not isabs(path):
    path = join(parent or cwd(), path)
  return path

def rel(path, parent=None, par=True):
  try:
    res = os.path.relpath(path, parent)
  except ValueError:
    # Possible on Windows when *path* and *parent* are on different drives.
    if not par:
      return path
    raise
  else:
    if not par and ispar(res):
      return path
    return res

def ispar(path):
  return path.startswith(curdir + sep) or path.startswith(pardir + sep)

def norm(path, parent=None):
  path = os.path.normpath(abs(path, parent))
  # Leads to problems eg. with the Java JAR creation because of filenames
  # that are lowercase even though the original .java source and class name
  # contain uppercase characters.
  #if os.name == 'nt':
  #  path = path.lower()
  return path

def addprefix(subject, prefix):
  """
  Adds the specified *prefix* to the last path element in *subject*.
  If *prefix* is a callable, it must accept exactly one argument, which
  is the last path element, and return a modified value.
  """

  if not prefix:
    return subject
  dir_, base = split(subject)
  if callable(prefix):
    base = prefix(base)
  else:
    base = prefix + base
  return join(dir_, base)

def addsuffix(subject, suffix, replace=False):
  """
  Adds the specified *suffix* to the *subject*. If *replace* is True, the
  old suffix will be removed first. If *suffix* is callable, it must accept
  exactly one argument and return a modified value.
  """

  if not suffix and not replace:
    return subject
  if replace:
    subject = rmvsuffix(subject)
  if suffix and callable(suffix):
    subject = suffix(subject)
  elif suffix:
    subject += suffix
  return subject

def setsuffix(subject, suffix):
  return addsuffix(subject, suffix, replace=True)

def rmvsuffix(subject):
  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    subject = subject[:index]
  return subject

def getsuffix(subject):
  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    return subject[index+1:]
  return None

def glob(pattern, parent=None):
  """
  Glob pattern matching. Acts always recursive on '**'.
  """

  if isinstance(pattern, str):
    pattern = [pattern]
  result = []
  for p in pattern:
    result += _glob.glob(abs(p, parent), recursive=True)
  return result

def transition(filename, oldbase, newbase):
  """
  Translates the *filename* from the directory *oldbase* to the new directory
  *newbase*. This is identical to finding the relative path of *filename* to
  *oldbase* and joining it with *newbase*. The #filename must be a sub-path
  of *oldbase*.

  ```python
  >>> transition('src/main.c', 'src', 'build/obj')
  build/obj/main.c
  ```
  """

  rel_file = rel(filename, oldbase, par=False)
  if isabs(rel_file):
    raise ValueError("filename must be a sub-path of oldbase", filename, oldbase)
  return join(newbase, rel_file)

def remove(path, recursive=False, silent=False):
  """
  Like :func:`os.remove`, but the *silent* parmaeter can be specified to
  prevent the function from raising an exception if the *path* could not be
  removed. Also, the *recursive* parameter allows you to use this function
  to remove directories as well. In this case, :func:`shutil.rmtree` is
  used.
  """

  try:
    if recursive and isdir(path):
      shutil.rmtree(path)
    else:
      os.remove(path)
  except OSError as exc:
    if not silent or exc.errno != errno.ENOENT:
      raise

class tempfile(object):
  """
  A better temporary file class where the #close() function does not delete
  the file but only #__exit__() does. Obviously, this allows you to close
  the file and re-use it with some other processing before it finally gets
  deleted.

  This is especially important on Windows because apparently another
  process can't read the file while it's still opened in the process
  that created it.

  ```python
  from craftr.tools import tempfile
  with tempfile(suffix='c', text=True) as fp:
    fp.write('#include <stdio.h>\nint main() { }\n')
    fp.close()
    shell.run(['gcc', fp.name])
  ```

  @param suffix: The suffix of the temporary file.
  @param prefix: The prefix of the temporary file.
  @param dir: Override the temporary directory.
  @param text: True to open the file in text mode. Otherwise, it
    will be opened in binary mode.
  """

  def __init__(self, suffix='', prefix='tmp', dir=None, text=False):
    self.fd, self.name = _tempfile.mkstemp(suffix, prefix, dir, text)
    self.fp = os.fdopen(self.fd, 'w' if text else 'wb')

  def __enter__(self):
    return self

  def __exit__(self, *__):
    try:
      self.close()
    finally:
      remove(self.name, silent=True)

  def __getattr__(self, name):
    return getattr(self.fp, name)

  def close(self):
    if self.fp:
      self.fp.close()
      self.fp = None
