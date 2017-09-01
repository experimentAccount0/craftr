
import * from 'craftr'
import * from 'craftr/lang/csharp'

csharp(
  name = 'lib',
  srcs = glob('src/lib/*.cs'),
  type = 'module'
)

csharp(
  name = 'main',
  deps = [':lib'],
  srcs = glob('src/*.cs'),
  type = 'exe',
  main = 'Main'
)

gentarget(
  name = 'run',
  deps = [':main'],
  commands = [
    [resolve(':main').dll_filename]
  ],
  explicit = True
)
