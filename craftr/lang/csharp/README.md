# C# language module

Compile C# projects.

## Options

* `csharp.csc` (str)
* Options inherited from the `craftr/lib/msvc` module

## Functions

### `csharp()`

__Parameters__

* `srcs` (list)
* `type` (str)
* `dll_dir` (str)
* `dll_name` (str)
* `main` (str)
* `extra_arguments` (list)
* `csc` (CscInfo)

### `csharp_run()`

__Parameters__

* `executable` (str): Automatically determined from the target's dependencies
  if an executable `csharp()` target is found.
* `explicit` (bool)
* `environ` (dict)
* `cwd` (str)
* `extra_arguments` (list)
* `csc` (CscInfo)

## Todo

* More target options (platform, optimize, warn, resource,
  win32icon, etc.)
* Separate functions for modules and execuables (?)
* Target to collect all executables and modules in a single
  directory
