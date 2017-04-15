# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import json
import functools
import os
import re
import sys
craftr = require('../api')
platform = require('../platform')
shell = require('../shell')
Library = require('./cxx/library')

@functools.lru_cache()
def get_config(python_bin=None):
  """
  Given the name or path to a Python executable, this function returns
  the dictionary that would be returned by
  #distutils.sysconfig.get_config_vars() of that Python version.

  The returned dictionary contains an additional key `'_PYTHON_BIN'`
  that is set to the value of the *python_bin* parameter. Note that
  the parameter defaults to the `python` option value and otherwise to the
  `PYTHON` environment variable.
  """

  if not python_bin:
    python_bin = craftr.option('python', default=os.getenv('PYTHON', 'python'))

  pyline = 'import json, distutils.sysconfig; '\
    'print(json.dumps(distutils.sysconfig.get_config_vars()))'

  command = shell.split(python_bin) + ['-c', pyline]
  output = shell.pipe(command, shell=True).output
  result = json.loads(output)
  result['_PYTHON_BIN'] = python_bin
  return result

def get_library(python_bin=None):
  """
  Uses #get_config() to read the configuration values of the specified
  Python executable and returns a #cxx.Library() that can be used in C/C++
  compiler interfaces.
  """

  config = get_config(python_bin)

  # LIBDIR seems to be absent from Windows installations, so we
  # figure it from the prefix.
  if platform.WINDOWS and 'LIBDIR' not in config:
    config['LIBDIR'] = path.join(config['prefix'], 'libs')

  library = Library(
    name = config['_PYTHON_BIN'],
    includes = [config['INCLUDEPY']],
    libpath = [config['LIBDIR']],
  )

  # The name of the Python library is something like "libpython2.7.a",
  # but we only want the "python2.7" part. Also take the library flags
  # m, u and d into account (see PEP 3149).
  if 'LIBRARY' in config:
    lib = re.search('python\d\.\d(?:d|m|u){0,3}', config['LIBRARY'])
    if lib:
      library.libs = [lib.group(0)]
  elif platform.WINDOWS:
    # This will make pyconfig.h nominate the correct .lib file.
    library.defines = ['MS_COREDLL']

  return library
