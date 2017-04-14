# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

from os import getcwd as cwd
from os.path import (
    join, split, splitext, isabs, isfile, isdir, islink, ismount, samefile,
    curdir, pardir, sep, dirname as dir, basename as base)
import errno
import os

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
  if os.name == 'nt':
    path = path.lower()
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
