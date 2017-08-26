+++
title = "Builders"
ordering-priority = 3
+++

A builder can be created by implementing the `craftr/core/build:BuildBackend`
interface. This implementation must then be exported. A backend can be selected
in the Craftr configuration by specifying the name of the module that can be
`require()`d to retrieve the implementation subclass.

```toml
[build]
  backend = "my-craftr-backend"
```

Builders have full control over the execution flow using the `Session` API.
For example, an implementation may choose to not execute the build scripts,
if all information can already be derived from other data (eg. previously
generated information from an `export` command).

The following commands are available to backends and can be implemented as the
same-named methods.

* `generate` -- Generate build information. This is usually only implemented
  for builders that export to a format readable by other backends. Backends
  that do not require the generation of build information can simply print a
  notice that a geeneration step is not required.
* `build` -- Execute the build (for the specified targets). Builders the
  implement `gen` may skip to execute the Craftr build scripts.
* `clean` -- Clean the build directory (for the specified targets).

## Example

This sample does not implement building/cleaning only the specified targets
and also invokes the build actions non-sequentially.

```python
import base from 'craftr/core/build'

class MyBackend(base.BuildBackend):

  def generate(self):
    print('the selected backend does not require a generate step.')
  
  def build(self, targets):
    for action in (n.data for n in topological_sort(self.session.action_graph)):
      process = action.execute()
      process.wait()
      process.print_stdout()
      if process.poll() != 0:
        print('error: action "{}" exited with return-code {}'
          .format(action.identifier, process.poll()))
        sys.exit(process.poll())
    print('Build done.')
  
  def clean(self, targets):
    for action in self.session.action_graph.values():
      for fname in action.outputs:
        try:
          os.remove(fname)
        except FileNotFoundError:
          pass
        except OSError as e:
          print('{}: {}'.format(fname, e))

exports = MyBackend
```
