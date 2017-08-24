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

__all__ = ['session', 'target', 'platform', 'pool']
import werkzeug.local as _local
import typing
import sys

local = _local.Local()

#: The current session.
session = local('session')

#: A string that represents the current build target. For debug and production
#: builds, this string is either "release" or "debug". Other names can be used,
#: in which case most build targets will omitt translating to the action graph
#: completely (eg. "docs", and only targets that are used to build documentation
#: files are translated into actions).
target = _local.LocalProxy(lambda: session.target)

#: Determine the name of the current platform.
if sys.platform.startswith('win32'):
  name = 'windows'
elif sys.platform.startswith('darwin'):
  name = 'macos'
elif sys.platform.startswith('linux'):
  name = 'linux'
else:
  raise EnvironmentError('Unsupported platform: {}'.format(sys.platform))
