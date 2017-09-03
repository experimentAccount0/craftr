
import * from 'craftr'
import csharp from 'craftr/lang/csharp'

csharp.build(
  name = 'lib',
  srcs = glob('src/lib/*.cs'),
  type = 'module'
)

csharp.build(
  name = 'main',
  deps = [':lib'],
  srcs = glob('src/*.cs'),
  type = 'exe'
)

csharp.run(
  name = 'run',
  deps = [':main'],
  explicit = True
)
