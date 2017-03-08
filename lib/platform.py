# Copyright (c) 2017 Niklas Rosenstein
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

import sys

WINDOWS = LINUX = MACOS = UNIX = False
CYGWIN = MSYS = False

if sys.platform.startswith('win32'):
  name = 'windows'
  env = 'nt'
  WINDOWS = True
elif sys.platform.startswith('cygwin'):
  name = 'cygwin'
  env = 'unix'
  CYGWIN = UNIX = True
elif sys.platform.startswith('msys'):
  name = 'msys'
  env = 'unix'
  MSYS = UNIX = True
elif sys.platform.startswith('darwin'):
  name = 'macos'
  env = 'unix'
  MACOS = UNIX = True
elif sys.platform.startswith('linux'):
  name = 'linux'
  en = 'unix'
  LINUX = UNIX = True
else:
  raise EnvironmentError('unsupported platform: "{}"'.format(sys.platform))

WINDOS = (name == 'windows')
CYGWIN = (name == 'cygwin')
MSYS = (name == 'msys')
LINUX = (name == 'linux')
MACOS = (name == 'macos')
UNIX = (env == 'unix')

path = require('./utils/path')
if WINDOWS or CYGWIN or MSYS:
  def obj(x): return path.addsuffix(x, ".obj")
  def bin(x): return path.addsuffix(x, ".exe")
  def dll(x): return path.addsuffix(x, ".dll")
  def lib(x): return path.addsuffix(x, ".lib")
elif MACOS:
  def obj(x): return path.addsuffix(x, ".o")
  def bin(x): return x
  def dll(x): return path.addsuffix(x, ".dylib")
  def lib(x): return path.addprefix(path.addsuffix(x, ".a"), "lib")
elif LINUX:
  def obj(x): return path.addsuffix(x, ".o")
  def bin(x): return x
  def dll(x): return path.addsuffix(x, ".so")
  def lib(x): return path.addprefix(path.addsuffix(x, ".a"), "lib")
else:
  raise RuntimeError("Hm that shouldn't happen..")
