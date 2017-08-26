+++
title = "Build Backends"
ordering-priority = 3
+++

A build backend can be created by implementing the `craftr/core/backend:Backend`
interface. This implementation must then be exported. The backend can then be
configured by specifying the request to `require()` that implementation from
the Craftr module.

Example: A Node.py module with the name `my-craftr-backend`.

```python
import {Backend} from 'craftr/core/backend'

class MyBackend(Backend):
  ...

exports = MyBackend
```

You can now specify `--backend=my-craftr-backend` via the command-line or
the following in your `.craftrconfig`:

    [build]
      backend = "my-craftr-backend"
