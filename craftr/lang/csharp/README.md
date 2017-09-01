# C# language module

Compile C# projects.

## Options

* `csharp.csc` (str)
* Options inherited from the `craftr/lib/msvc` module

## Functions

### `csharp()`

__Parameters__

* `srcs`
* `type`
* `dll_dir`
* `dll_name`
* `main`
* `extra_arguments`
* `csc`

## Todo

* More target options (platform, optimize, warn, resource,
  win32icon, etc.)
* Separate functions for modules and execuables (?)
* Target to collect all executables and modules in a single
  directory
