# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

class Container(object):

  def __init__(self, **kwargs):
    for key, default in self.__container_meta__['fields']:
      if key not in kwargs:
        if default is None:
          raise TypeError('missing required keyword argument {!r}'.format(key))
        value = default()
      else:
        value = kwargs.pop(key)
      setattr(self, key, value)
    if kwargs:
      raise TypeError('unexpected keyword argument {!r}'.format(next(iter(kwargs))))

  def __str__(self):
    lines = ['{}:'.format(self.__container_meta__['name'])]
    for key, __ in self.__container_meta__['fields']:
      lines.append('  {}: {}'.format(key, getattr(self, key)))
    return '\n'.join(lines)

exports = Container
