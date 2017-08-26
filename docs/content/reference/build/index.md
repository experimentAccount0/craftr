+++
title = "Builders"
ordering-priority = 3
+++

A builder can be created by implementing the `craftr/core/build:BuildBackend`
interface. This implementation must then be exported. The backend can then be
configured by specifying the request to `require()` that implementation from
the Craftr module.

Example: A Node.py module with the name `my-craftr-backend`.

```python
import base from 'craftr/core/build'

class MyBackend(base.BuildBackend):
  ...

exports = MyBackend
```

You can now specify `--backend=my-craftr-backend` via the command-line or
the following in your `.craftrconfig`:

    [build]
      backend = "my-craftr-backend"
