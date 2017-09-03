# C# language module

Compile C# projects.

## Options

* `csharp.impl` (str): The name of the C# implementation. Defaults to `'net'`
  on Windows and `'mono'` on all other platforms.
* `csharp.csc` (str): The C# compiler. On Windows, it defaults to `csc` in the
  most recent or the configured MSVC toolkit. On other platforms, it defaults
  to `mcs`.
* Options inherited from the `craftr/lib/msvc` module

## Functions

### `csharp.build()`

Compile a set of C# source files into an executable or any other supported
target type.

__Parameters__

* `srcs` (list)
* `type` (str)
* `dll_dir` (str)
* `dll_name` (str)
* `main` (str)
* `extra_arguments` (list)
* `csc` (CscInfo): The C# compiler. Defaults to the standard compiler that
  can be retrieved with `CscInfo.get()`.

### `csharp.run()`

Run a C# executable.

__Parameters__

* `executable` (str): Automatically determined from the target's dependencies
  if an executable `csharp()` target is found.
* `explicit` (bool)
* `environ` (dict)
* `cwd` (str)
* `extra_arguments` (list)
* `csc` (CscInfo): The C# compiler. If not specfied, inherits the compiler
  from its dependencies (only if the `executable` is automatically determined)
  or the standard C# compiler.

## Todo

* More target options (platform, optimize, warn, resource,
  win32icon, etc.)
* Separate functions for modules and execuables (?)
* Target to collect all executables and modules in a single
  directory
