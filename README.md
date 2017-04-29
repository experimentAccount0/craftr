<img src="https://i.imgur.com/zkceTvb.png" align="right"></img>

# Craftr

Craftr is a meta build system based on Python and Ninja. It uses [Node.py]
and the [PPYM] package management ecosystem to provide a modular and
extensible infrastructure.

  [Node.py]: https://github.com/nodepy/nodepy
  [PPYM]: https://ppym.org

Craftr is installed anew for every project that you want to use it for. This
ensures that the version is as close as possible to what the project was
originally created with, thus enabling very reproducible builds.

```python
ppym install craftr --save-dev
```

## Getting Started

You first need to install [Node.py] into a Python 3.4+ version available on
your system. After that, you can simply install Craftr into your current
project and start your script. It is recommended to have a `package.json`
so you can use the `--save-dev` option (which will put `"craftr"` and the
installed version into the dependencies).

    $ pip3 --user install node.py
    $ cd myproject/
    $ ppym install craftr --save-dev

It is also recommended to add `nodepy_modules/.bin` to your `PATH`.

    $ cat Craftrfile
    namespace = 'myproject'
    craftr = require('craftr')
    java = require('craftr/lang/java')
    java.compile(name='classes', src_dir='src')
    java.jar(name='jar', classfiles=':classes', entry_point='Main')
    $ craftr export
    $ craftr build
