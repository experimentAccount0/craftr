
import * from 'craftr'
import * from 'craftr/lang/csharp'

csharp(
  name = 'main',
  srcs = glob('src/*.cs'),
  type = 'exe'
)

gentarget(
  name = 'run',
  deps = [':main'],
  commands = [
    [resolve(':main').dll_filename]
  ],
  explicit = True
)
