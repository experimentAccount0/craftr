
import * from 'craftr'
import java from 'craftr/lang/java'

java.library(
  name = 'utils',
  srcs = glob('src/utils/**.java')
)

java.library(
  name = 'main_lib',
  srcs = glob('src/main/**.java'),
  visible_deps = [':utils']
)

java.binary(
  name = 'main',
  deps = [':main_lib'],
  main_class = 'main.Main'
)

gentarget(
  name = 'run',
  deps = [':main'],
  commands = [
    ['java', '-jar', resolve(':main').jar_filename]
  ],
  explicit = True
)
