+++
title = "Actions"
ordering-priority = 2
+++

__Parameters__

* `source` (positional 0): The target that generates this action. This is
  usually just plain `self` inside `Target.translate()`.

* `name`: The name of the action. This name must be unique inside the domain
  of all the actions defined inside the same target.

* `deps`: A list of actions or targets that this action depends on. Usually,
  the first action that processes the input files simply takes `self.deps()`
  (where `self` is a `Target`).

* `inputs`: A list of input files. It is important to always consistently
  define specify the input and output files of actions, as otherwise the
  dirty check and action hash key can not be calculated properly.

* `outputs`: A list of output files.

### Custom Actions

Actions are what will actually be executed during the build. Most actions are
implemented as *pure functions*, meaning that the same inputs must result in
the same outputs. This allows us to stash build artifacts, see
[Build artifact stashes](#build-artifact-stashes) for more information.

TODO
