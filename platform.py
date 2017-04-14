# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import sys

#: Bool values indicating a certain OS type. Some of these values might be
#: enabled at the same time. For example, on Cygwin, the #WINDOWS and #UNIXLIKE
#: flag will be set.
WINDOWS = False
MACOS = False
LINUX = False
CYGWIN = False
MSYS = False
UNIXLIKE = False

if sys.platform.startswith('win32'):
  name = 'windows'
  WINDOWS = True
elif sys.platform.startswith('cygwin'):
  name = 'cygwin'
  WINDOWS = True
  CYGWIN = True
  UNIXLIKE = True
elif sys.platform.startswith('msys'):
  name = 'msys'
  WINDOWS = True
  MSYS = True
  UNIXLIKE = True
elif sys.platform.startswith('linux'):
  name = 'linux'
  LINUX = True
  UNIXLIKE = True
elif sys.platform.startswith('darwin'):
  name = 'mac'
  MACOS = True
  UNIXLIKE = True
else:
  raise EnvironmentError(
      'platform {!r} is currently not supported'.format(sys.platform))
