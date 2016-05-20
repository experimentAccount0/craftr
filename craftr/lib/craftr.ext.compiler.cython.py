# -*- mode: python -*-
# Copyright (C) 2016  Niklas Rosenstein
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

__all__ = ['CythonCompiler']

from craftr import *

from craftr.ext.compiler import gen_objects, BaseCompiler
import craftr
import re


class CythonCompiler(BaseCompiler):
  ''' Compiler interface for Cython. A small example:

  .. code:: python
    from craftr import path, options
    from craftr.ext.compiler.cython import cythonc

    c_files = cythonc.compile(
      py_sources = path.glob('mymodule/**/*.pyx'),
      python_version = int(options.get('python_version', 3)),
      fast_fail = True,
      cpp = True,
    )
  '''

  name = 'Cython'

  def __init__(self, program='cython', detect=True, **kwargs):
    super().__init__(program=program, **kwargs)
    self.version = None
    if detect:
      output = craftr.shell.pipe([program, '-V']).output
      match = re.match(r'cython\s+version\s+([\d\.]+)', output, re.I)
      if match:
        self.version = match.group(1)

  def compile(self, py_sources, outputs=None, frameworks=(), target_name=None, **kwargs):
    ''' Compile the specified *py_sources* files to C or C++ source files.

    :param py_sources: A list of ``.pyx`` or ``.py`` files.
    :param outputs: Override the output filenames. If omitted, default
      output filenames are generated.
    :param frameworks: List of additional frameworks.
    :param target_name: Alternative target name.
    :param include: Additional include directories for Cython.
    :param fast_fail: True to enable the ``--fast-fail`` flag.
    :param cpp: True to translate to C++ source files.
    :param additional_flags: List of additional flags for the Cython command.
    :param python_version: The Python version to build for (2 or 3).
      Defaults to 3.
    '''

    builder = self.builder(py_sources, frameworks, kwargs, name=target_name)

    cpp = builder.get('cpp', False)
    python_version = builder.get('python_version', 3)
    fast_fail = builder.get('fast_fail', False)

    if outputs is None:
      outputs = gen_objects(py_sources, 'cython', suffix='.cpp' if cpp else '.c')
    if python_version not in (2, 3):
      raise ValueError('invalid python_version: {0!r}'.format(python_version))

    include = set(builder.merge('include'))
    command = [builder['program'], '$in', '-o', '$out', '-' + str(python_version)]
    command += ['-I' + x for x in include]
    command += ['--fast-fail'] if fast_fail else []
    command += ['--cplus'] if cpp else []
    command += builder.merge('additional_flags')

    # xxx: Determine the Python Framework and add it to the target!

    return builder.create_target(command, outputs=outputs, foreach=True)


cythonc = CythonCompiler()
