# Java Example

This directory contains an example Java project that generates two JAR library
files and one executable JAR binary. The JAR libraries are combined into one
using [One-Jar].

  [One-Jar]: http://one-jar.sourceforge.net/

If you want to generate a binary JAR that is merged of all the input JARs,
pass `dist_type = 'merge'` to the `java_binary()` target or specify the same
in the Craftr configuration file.

```toml
[java]
  dist_type = "merge"
```
