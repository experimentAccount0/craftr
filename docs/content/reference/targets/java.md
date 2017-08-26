+++
title = "Java"
+++

```python
import * from 'craftr/lang/java'
```

## Functions

### java_prebuilt()

Define a target that contains a prebuilt Java JAR library.

__Parameters__

* `binary_jar`: The path to the prebuilt Java JAR file.

### java_library()

Create a Java JAR library from a set of source files.

__Parameters__

* `srcs`: A list of source files. If `srcs_root` is not specified, the config
  option `java.src_roots` to determine the root of the source files.

* `src_roots`: A list of source root directories. Defaults to `java.src_roots`
  config. The default value for this configuration is
  `['src', 'java', 'javatest']`.

* `class_dir`: The directory where class files will be compiled to.

* `jar_dir`: The directory where the jar will be created in.

* `jar_name`: The name of the JAR file. Defaults to the target name.

* `main_class`: A classname that serves as an entry point for the JAR archive.
  Note that this target does not merge the dependencies into a single target.
  If you want to create a one-file executable JAR archive, you should use the
  `java_binary()` target.

* `javac`: The name of Java compiler to use. If not specified, defaults to the
  value of the `java.javac` option or simply "javac".

* `javac_jar`: The name of Java JAR command to use. If not specified, defaults
  to the value of the `java.javac_jar` option or simply "jar".

* `extra_arguments`: A list of additional arguments for the Java compiler.
  They will be appended to the ones specified in the configuration.

### java_binary()

Create an executable JAR archive from all the specified dependencies. You can
choose to merge all JAR archives into one single archieve, or to use [One-Jar]
(which is usually preferred).

  [One-Jar]: http://one-jar.sourceforge.net/

Craftr comes pre-bundled with `one-jar-boot-0.97.jar`, but you can specify
a different one using the `java.onejar` option.

```toml
[java]
  onejar = "path/to/onejar.jar"
```

__Parameters__

* `jar_dir`: The directory where the jar will be created in.

* `jar_name`: The name of the JAR file. Defaults to the target name.

* `main_class`: The name of the main Java class.

* `dist_type`: Can be `'onejar'` (default) or `'merge'`.

* `javac_jar`: The name of Java JAR command to use. If not specified, defaults
  to the value of the `java.javac_jar` option or simply "jar".

## Example

```python
import * from 'craftr'
import * from 'craftr/lang/java'

java_prebuilt(
  name = 'guava',
  binary_jar = 'vendor/guava-22.0.jar'
)

java_library(
  name = 'library',
  srcs = glob(['**/*.java']),
  deps = [':guava']
)

java_binary(
  name = 'main',
  deps = [':library'],
  entry_point = 'Main'
)
```
