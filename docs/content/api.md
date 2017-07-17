+++
title = "Craftr API"
+++

## References

References are strings which represent a build product that can be
included in another target's definition. Build products can be either
targets created with the [`target()`](#target) function or products
created with the [`product()`](#product) function. If both, a product and
a target, exist with the same name, the product is preferred.

__Syntax__

    # Absolute reference
    //namespace:target-or-product

    # Relative reference (inside the same namespace)
    :target-or-product

You can use the [`isref()`](#isref) function to check if a string is a
reference string. Use the [`resolve()`](#resolve) function to resolve a
reference string.

## Builtin functions

```python
import * from '@craftr/craftr'
```

### target()

```python
target(name, command, inputs=None, outputs=None, implicit=None,
       order_only=None, pool=None)
```

Define a new build target. The *name* will be automatically scoped inside the
current namespace (see the [namespace](#namespace) function for more details
about namespaces).

__Parameters__

* __name__: The name of the target.
* __command__: The command or commands to execute for the target. This must
  be a list of command arguments or a list of multiple such command argument
  lists.
* __inputs__: A list of input files or target references. Check the
  [references](#references) section for more information.


### namespace()

```python
namespace()
```

Retrieve the name of the current namespace. The namespace is determined by
the nearest Node.py package manifest (`package.json`). If no package manifest
could be found, the functions returns `"__main__"`.

### isref()

```python
isref(string)
```

Returns `True` if the specified *string* is a reference string as described
in the [references](#references) section.

### resolve()

```python
resolve(reference_string)
```

Resolves the *reference_string* and returns either a `Product` or `Target`
object.

__Raises__

* `ValueError`: If *reference_string* is not a reference string as described
  in the [references](#references) section.
* `NoSuchBuildProductError:`If there is no product nor target that the
  reference string resolves to.

## Classes

### Target

### Product
