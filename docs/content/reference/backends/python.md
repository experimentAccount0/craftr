+++
title = "Python Backend"
+++

```
[build]
  backend = "python"
```

A pure-python backend to execute the action graph. This backend will deliver
the most consistent results as all actions possess a Python-based
implementation.

__Options__

* `build.jobs`: The number of jobs to execute in parallel at maximum. This
  will be capped at X*2.5 where X is the number of processor cores available
  to the machine.
