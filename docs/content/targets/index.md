+++
title = "Targets"
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
