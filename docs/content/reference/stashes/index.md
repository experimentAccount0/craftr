+++
title = "Stashes"
+++

Actions that are implemented as *pure functions* can be stashed and re-used
from other machines. For that, a stash backend must be set-up, and the project
must be configured to use that stash backend.

Before an action is executed, Craftr computes the action hash key and check if
there is a stash available for that key. If it is, the files from that stash
are materialized locally in the build directory. Otherwise, the action will be
executed and the outputs will be uploaded to the stash backend.

A stash backend can be created by implementing the `craftr/core/stash:StashBackend`
interface. Similar to custom build backends, the stash backend can be configured
in the  `.craftrconfig`.

    [stashes]
      backend = "my-craftr-stash"
      uploads = on    # Enable/disable upload of artifacts
      downloads = on  # Enable/disable download of artifacts

If further configuration is needed, arbitrary option sections and names may
be used by the `StashBackend` implementation.

```python
import base from 'craftr/core/stash'

class MyFileInfo(base.FileInfo):
  ...

class MyStash(base.Stash):
  ...

class MyStashBuilder(base.StashBuilder):
  ...

class MyStashBackend(base.StashBackend):
  ...

exports = MyStashBackend
```
