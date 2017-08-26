+++
title = "Targets"
ordering-priority = 1
+++

Every target factory in Craftr has a few parameters in common, namely the
parameters that are necessary to construct a build graph.

__Parameters__

* `name`: Every target in Craftr requires a name. This name is automatically
  inserted into the current scope. It must be unique inside that scope.

* `deps`: A list of target names, either as relative or absolute references.
  The reference syntax is `[//scope]:target`.

* `visible_deps`: Similar to `deps`, this must also be a list of target
  references, but they can be recognized by other targets that depend on
  this target transitively. For example, if you jave a `java_library()` that
  has a visible dependency to a `java_prebuilt()` target, a target that
  depends on your `java_library()` target can take the `java_prebuilt()`
  dependency into account.

  Note: If `visible_deps` is not specified or `None`, it matches `deps`.

## Custom targets

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
