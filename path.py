# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

from os import getcwd as cwd
from os.path import join, split, splitext, dirname as dir, basename as base
import errno
import os

def makedirs(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise
