<img align="right" src="http://i.imgur.com/NPcPEF5.png">

# The Craftr build system (version 3.x)

Craftr is a language-agnostic build system implemented in Python 3.6. It is
built on top of the [Node.py] runtime and leverages the **nppm** package
manager, allowing you to install the exact version of Craftr that you need
to get a fully reproducible build, and also to make use of other modules and
their build definitions.

This new version of Craftr is largely inspired by [Buck], which represents the
build graph as abstract targets that are then translated into actions. Craftr
also inherits the target reference format `[//scope]:target` for specifying
dependencies in the target graph. As such, Craftr can look quite familar to
users of Buck.

![](.assets/diagram.jpg)

  [Node.py]: https://nodepy.org
  [Buck]: https://buckbuild.com/

## Getting Started

### Installation

You can install Craftr using the **nppm** package manager. It is reccommended
to install Craftr locally in a project, instead of globally. Craftr 3.x is
not currently available on the [nodepy package registry], and thus needs to be
installed from Git.

  [nodepy package registry]: https://registry.nodepy.org/

    $ pip install --user node.py
    $ cd my_project/
    $ nppm install git+https://github.com/craftr-build/craftr.git@dev/craftr-3.x
    $ export PATH=nodepy_modules/.bin:${PATH}

If you have a Node.py `package.json` already in your project's directory, you
can add the `--save` or `--save-dev` option to save the dependency to the
manifest. You can then use `nppm lock` to lock the dependency versions and
restore them on the next checkout of your project with `nppm install`.

### Project Structure

The structure of Craftr projects can be selected arbitrary. All the information
that is necessary to build a project is specified in the `Craftrfile.py` build
script. Every `Craftrfile.py` should be accompagnied by a `package.json` file.
The "name" field in that manifest will specify the scope to which declared
targets are added. If no `package.json` is present, the namespace of the module
that loads the build-script is inherited.

    my_project/
      Craftrfile.py
      package.json
      nodepy_modules/
      src/

The only exception is the main build script that serves as the entry point to
the project's build definitions. It's default scope name is called `__main__`.
Note that if a `package.json` is preset, it will still be assigned to that
manifest's scope name instead.

### Target declaration

Targets are an abstraction of an entity in the build graph. A target may
represent an executable, a shared or dynamic library or something completely
different. When all targets are loaded, they are turned into **actions** that
can be executed (or exported to another format, depending on the selected
build backend).

In order to declare a target, you must first import a target factory function.
In Craftr, unlike Buck, most of the target factories are not available to the
build script by default.

Note that you can use the Node.py "import syntax" if you have the extension
enabled in your `package.json` or in the header of your build script.

```python
# nodepy-extensions: !require-import-syntax

import * from 'craftr'                # require.symbols('craftr')
import * from 'craftr/lang/java'      # require.symbols('craftr/lang/java')

java_prebuilt(
  name = 'hdecomp',
  binary_jar = 'vendor/hdecomp/dist/hdecomp.jar'
)
java_library(
  name = 'utils',
  srcs = glob('src/utils/**.java'),
  deps = [':hdecomp']
)
java_binary(
  name = 'binary',
  srcs = glob('src/*.java'),
  deps = [':utils']
)
```

### Custom targets

Custom targets can be implemented in your own build scripts. This is useful to
provide new functionality to the Craftr build system, e.g. for other languages.

```python
import craftr from 'craftr'
import actions from 'craftr/actions'

class SayHello(craftr.Target):

  def __init__(self, *, subject: str, **kwargs):
    craftr.Target.__init__(self, **kwargs)
    self.subject = subject

  def translate(self):
    actions.subprocess(self,
      name = 'a_subcommand',
      deps = self.deps(),
      commands = [
        ['echo', 'Hello, {}!'.format(self.subject)],
        ['sleep', '1']
      ],
      buffer = True
    )

say_hello = craftr.target_factory(SayHello)

say_hello(
  name = 'hello',
  subject = 'Peter'
)
```

### Custom Actions

Actions are what will actually be executed during the build. Most actions are
implemented as *pure functions*, meaning that the same inputs must result in
the same outputs. This allows us to stash build artifacts, see
[Build artifact stashes](#build-artifact-stashes) for more information.

TODO

### Build backends

A build backend can be created by implementing the `craftr/core/backend:Backend`
interface. This implementation must then be exported. The backend can then be
configured by specifying the request to `require()` that implementation from
the Craftr module.

Example: A Node.py module with the name `my-craftr-backend`.

```python
import {Backend} from 'craftr/core/backend'

class MyBackend(Backend):
  ...

exports = MyBackend
```

You can now specify `--backend=my-craftr-backend` via the command-line or
the following in your `.craftrconfig`:

    [build]
      backend = "my-craftr-backend"

### Build artifact stashes

Actions that are implemented as *pure functions* can be stashed and re-used
from other machines. For that, a stash server must be set-up, and the project
must be configured to use that stash server.

Before an action is executed, Craftr computes the action hash key and check if
there is a stash available for that key. If it is, the files from that stash
are materialized locally in the build directory. Otherwise, the action will be
executed and the outputs will be uploaded to the stash server.

A stash server can be created by implementing the `craftr/core/stash:StashServer`
interface. Similar to custom build backends, the stash server can be configured
in the  `.craftrconfig`.

    [build]
      stashes = "my-craftr-stashserver"
      uploads = on    # Enable/disable upload of artifacts
      downloads = on  # Enable/disable download of artifacts

If further configuration is needed, arbitrary option sections and names may
be used by the `StashServer` implementation.

```python
import base from 'craftr/core/stash'

class MyFileInfo(base.FileInfo):
  ...

class MyStash(base.Stash):
  ...

class MyStashBuilder(base.StashBuilder):
  ...

class MyStashServer(base.StashServer):
  ...

exports = MyStashServer
```
