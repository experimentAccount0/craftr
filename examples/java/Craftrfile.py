
import * from 'craftr'
import * from 'craftr/lang/java'

java_library(
  name = 'utils',
  srcs = glob('src/utils/**.java')
)

java_library(
  name = 'main_lib',
  srcs = glob('src/main/**.java'),
  visible_deps = [':utils']
)

java_binary(
  name = 'main',
  deps = [':main_lib'],
  main_class = 'main.Main'
)
