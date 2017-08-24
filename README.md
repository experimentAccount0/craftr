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
