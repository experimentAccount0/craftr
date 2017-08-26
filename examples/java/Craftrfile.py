
import * from 'craftr'
import * from 'craftr/lang/java'

print(builddir)

java_library(
  name = 'library',
  srcs = glob('src/**.java')
)

java_binary(
  name = 'main',
  deps = [':library'],
  main_class = 'Main'
)
