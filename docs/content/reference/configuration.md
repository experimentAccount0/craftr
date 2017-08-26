+++
title = "Configuration"
+++

Craftr uses TOML and Python configuration files. The configuration files are
loaded in the following order:

* `~/.craftr/config.toml`
* `~/.craftr/config.py`
* `./.craftrconfig.toml`
* `./.craftrconfig.py`

## TOML

TOML configuration files can make use of in sections, as well as specifying
options for multiple sections. Filters can be used on the following properties:

* arch
* platform
* target

To apply a filter, add a semi-colon to a section name in the configuration
file. These can be used multiple times in the same section to apply multiple
filters. Additionally, if the part before the semi-colon is not a filter
expression, it is considered as an additional section name. Example:

```toml
["gcc; clang; platform=windows; arch=amd64"]
  options...
```

The following filter opertors are available:

* `=`, `==` (equality)
* `!=` (inequality)
* `~` (glob matching)
* `%` (contains)

## Python

Python configuration files are loaded just like Craftrfiles are, only a few
steps earlier. They have full access to the Craftr build environment and can
set up the session configuration.

Example:

```python
import os
import * from 'craftr'

if 'MYPROJECT_STASH_LOCATION' in os.environ:
  config['stashes.location'] = os.environ['MYPROJECT_STASH_LOCATION']
```
