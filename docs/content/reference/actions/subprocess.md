+++
title = "Subprocess"
+++

```python
import {subprocess} from 'craftr/actions'
```

This action represents one or multiple system commands.

__Parameters__

* `commands`: A nested list of command argumen lists. 
  Eg. `[['echo', 'Hello!'], ['sleep', '10']]`

* `environ`: A dictionary that specifies environment variables for the
  commands. Note that the values in this dictionary *overwrite* the current
  environment variables, thus if you need to augment `PATH`, you have to
  manually append it and set the full `PATH` value in this dictionary.

* `cwd`: The working directort for the commands.

* `buffer`: True if the output of the commands should be buffered (default),
  False if it should be connected to the build process' standard in- and
  output.
