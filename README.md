<img src="https://i.imgur.com/zkceTvb.png" align="right"></img>

# Craftr

Craftr is a meta build system based on Python and Ninja. It uses [Node.py]
and the [PPYM] package management ecosystem to provide a modular and
extensible infrastructure.

  [Node.py]: https://github.com/nodepy/nodepy
  [PPYM]: https://ppym.org

Using Craftr is similar to tools like gulp in Node.js: First you install
the [Craftr CLI], then you install Craftr into your project as development
dependencies. Note that it is not a requirement to use a Node.py `package.json`
in your project, but it is highly recommended.

  [Craftr CLI]: https://github.com/craftr-build/craftr-cli

    $ ppym install -g @craftr/cli
    $ ppym install craftr --save-dev

## Example

Craftr build scripts are basically [Node.py] Python scripts that make use
of the `craftr` API, however you won't get much out of it without using the
Craftr CLI. Follow the instructions above to install the CLI and the Craftr
API locally, then also install the C/C++ language extension:

    $ ppym install @craftr/cxx --save-dev

Then create a `Craftrfile.py` and put the following into it:

```python
require('craftr').namespace('my-project', export_api=True)
cxx = require('@craftr/cxx')

cxx.executable(
  name = 'main',
  inputs = cxx.compile_cpp(
    name = 'main-objects',
    sources = glob('src/*.cpp')
  )
)
```

Also make sure that there is at least one `.cpp` file in the `src/` directory.
Now you are ready to generate a Ninja build manifest and then execute the
build process.

    $ craftr generate
    $ craftr build
