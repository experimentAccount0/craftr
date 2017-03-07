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
  name = 'mac'
  env = 'unix'
  MACOS = UNIX = True
elif sys.platform.startswith('linux'):
  name = 'linux'
  en = 'unix'
  LINUX = UNIX = True
else:
  raise EnvironmentError('unsupported platform: "{}"'.format(sys.platform))
