+++
title = "Local"
+++

(TODO)

```toml
[stashes]
  backend = "local"
```

A backend for storing build artifacts locally or mapped network drives. The
default storage location is `~/.craftr/stashes`.

__Options__

* `stashes.location`: A string pointing to the directory that contains the
  stash objects and where new stashes can be created. (TODO)

* `stashes.ttl`: Specifies the time-to-live for new stashes. Note that since
  there is no continously running process for a local stash, stashes are only
  dropped every invokation of the build process. (TODO)
