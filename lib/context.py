# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

options = {}

class Context(object):
  """
  A context manages the build information for a single Craftr module.
  """

  def __init__(self, name):
    self.name = name

  def option(self, name, type=str, inherit_global=True, default=None):
    """
    Retrieve the value of an option specified by *name* and coerce it to
    *type*. If *inherit_global* is #True, the option will be checked in the
    global option namespace without the Context name's prefix, too. If no
    value can be found, *default* will be returned.

    Supported values for *type* are #bool, #int, #float, #str.
    """

    full_name = '{}:{}'.format(self.name, name)
    if full_name in options:
      value = options[full_name]
    elif inherit_global and name in options:
      value = options[name]
      full_name = name
    else:
      return default

    if type == bool:
      value = str(value).strip().lower()
      if value in ('yes', 'on', 'true', '1'):
        value = True
      elif value in ('no', 'off', 'false', '0'):
        value = False
      else:
        raise ValueError("invalid value for option {!r} of type 'bool': {!r}"
            .format(full_name, value))
    else:
      try:
        value = type(value)
      except (ValueError, TypeError) as exc:
        raise ValueError("invalid value for option {!r} of type 'str': {!r} ({})"
            .format(full_name, value, exc))

    return value
