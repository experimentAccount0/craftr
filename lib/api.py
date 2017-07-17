


def target(name, command, inputs=(), outputs=(), implicit=(), order_only=(),
           pool=None):
  """
  Generate a new build target.
  """

  raise NotImplementedError  # TODO


def namespace():
  """
  Returns the current namespace.
  """

  package = require.context.current_module.package
  if package:
    return package.json.get('name', '__main__')
  return '__main__'


def isref(string):
  """
  Returns #True if *string* is a reference string, #False otherwise.
  """

  if string.count(':') != 1:
    return False
  return string.startswith('//') or string.startswith(':')


def resolve(reference_string):
  """
  Resolves the *reference_string* and returns either a #Product or #Target
  object.

  # Raises
  ValueError: If #isref() would return #False for *reference_string*.
  NoSuchBuildProductError: If *reference_string* could not be resolved.
  """

  raise NotImplementedError # TODO
