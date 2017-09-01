# Java language module

Compile Java projects.

## Options

* `java.onejar` (str)
* `java.javac` (str)
* `java.javac_jar` (str)
* `java.extra_arguments` (list of str)
* `java.dist_type` (str)

## Functions

### `java_library()`

__Parameters__

* `jar_dir`
* `jar_name`
* `javac_jar`
* `main_class`
* `srcs`
* `src_roots`
* `class_dir`
* `javac`
* `extra_arguments`

### `java_binary()`

__Parameters__

* `jar_dir`
* `jar_name`
* `javac_dir`
* `main_class`
* `dist_type`

### `java_prebuilt()`

__Parameters__

* `binary_jar`

## Todo

* Support inclusion of resource files in JARs
* More options (warning flags, debug/release, linting, 
  provided dependencies, etc.)