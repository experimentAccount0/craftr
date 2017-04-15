# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

class Library(require('../../utils/container')):
  """
  Represents a C or C++ library.

  # Members

  name (str): Name of the library.
  include (list of str): A list of include directories.
  defines (list of str): A list of preprocessor macros.
  libpath (list of str): A list of library search paths.
  libs (list of str): A list of library names to link with.
  external_libs (list of str): A list of absolute paths to libraries to link with.
  cflags (list of str): A list of additional command-line arguments when
      compiling C source files (depending on the current compiler).
  cppflags (list of str): A list of additional command-line arguments when
      compiling C++ source files (depending on the current compiler).
  ldflags (list of str): A list of additional command-line arguments when
      linking object files when this library is in use (depending on the
      current compiler).
  deps (list of Library): A list of other #Library objects that this library
      depends on.
  """

  __container_meta__ = {
    'name': 'cxx.Library',
    'fields': [
      ('name', None),
      ('includes', list),
      ('defines', list),
      ('libpath', list),
      ('libs', list),
      ('external_libs', list),
      ('cflags', list),
      ('cppflags', list),
      ('ldflags', list),
      ('deps', list)
    ]
  }

exports = Library
