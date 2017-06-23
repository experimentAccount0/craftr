<img align="right" src="assets/craftr_icon.png">

# Craftr 3.x Build System

  [Ninja]: https://ninja-build.org/
  [Python]: https://www.python.org/
  [Node.py]: https://nodepy.org/

Craftr is a language-agnostic build system based on [Ninja] and [Python].
It's modular structure allows you to easily embed existing build definitions
into your project by using the [Node.py] package manager *nppm*.

__Features__

* Clean and expressive syntax
* Allows you to implement complex build requirements with [Python]
* [ ] Extensive standard library for building C, C++, C#, Cython and Java projects
* [ ] Built-in support for major C/C++ compilers (GCC, Clang, MSVC)

__Example__

*Note that this example is subject to change as the Craftr 3.x development
progresses.*

```python
import {path} from 'craftr'
import cxx from 'craftr/lib/cxx'

# Only needed when there is no package.json and the script is imported
# from some other module.
namespace = 'mybuildnamespace'  

# Declare a boolean option (exposed as `mybuildnamespace.build_examples`).
# Inherits the value of the global `build_examples` option if not explicitly
# overwritten.
build_examples = option(bool, inherit=True, help='Compile in debug mode.')
static = option(bool, default=True, help='Build a static library.')

cxx.library(
  name = 'library',
  srcs = path.glob('src/**/*.cpp'),
  libs = ['//@craftr/libcurl:library'],
  link_type = 'static' if static else 'shared'
)

if build_examples:
  for filename in path.glob('examples/*.cpp'):
    cxx.executable(
      name = path.rmvsuffix(path.basename(filename)),
      srcs = [filename],
      libs = [':library']
    )
```
