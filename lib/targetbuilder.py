# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

build = require('./ninja')
logger = require('./logger')
craftr = require('../index')
argschema = require('./argschema')

import collections
import sys


def unique_append(lst, item, id_compare=False):
  if id_compare:
    for x in lst:
      if x is item:
        return
  else:
    if item in lst:
      return
  lst.append(item)


class TargetBuilder(object):
  """
  This is a helper class for target generators that does a lot of convenience
  handling such as creating a :class:`OptionMerge` from the build options
  specified with the *frameworks* argument or from the input
  :class:`Targets<build.Target>`.

  :param name: The name of the target.
  :param option_kwargs: A dictionary of additional call-level options
    that have been passed to the target generator function. These will
    take top priority in the :class:`OptionMerge`.
  :param inputs: A list of input files or :class:`build.Target` objects
    from which the outputs will be used as input files and the build
    options will be included in the :class:`OptionMerge`.
  :param frameworks: A list of build :class:`Framework` objects that will be
    included in the :class:`OptionMerge`.
  :param outputs: A list of output filenames.
  :param implicit_deps: A list of filenames added as implicit dependencies.
  :param order_only_deps: A list of filenames added as order only dependencies.
  """

  def __init__(self, name, option_kwargs=None, frameworks=(), inputs=(),
      outputs=(), implicit_deps=(), order_only_deps=()):
    argschema.validate('name', name, {'type': str})
    argschema.validate('option_kwargs', option_kwargs,
        {'type': [None, dict, Framework]})
    argschema.validate('frameworks', frameworks,
        {'type': [list, tuple], 'items': {'type': [Framework, build.Target]}})
    argschema.validate('inputs', inputs,
        {'type': [list, tuple, build.Target],
          'items': {'type': [str, build.Target]}})
    argschema.validate('outputs', outputs,
        {'type': [list, tuple], 'items': {'type': str}})
    argschema.validate('implicit_deps', implicit_deps,
        {'type': [list, tuple], 'items': {'type': str}})
    argschema.validate('order_only_deps', order_only_deps,
        {'type': [list, tuple], 'items': {'type': str}})

    if isinstance(inputs, build.Target):
      inputs = [inputs]

    self.frameworks = []
    self.implicit_deps = list(implicit_deps)
    self.order_only_deps = list(order_only_deps)

    # If we find any Target objects in the inputs, expand the outputs
    # and append the frameworks.
    if inputs is not None:
      self.inputs = []
      for input_ in (inputs or ()):
        if isinstance(input_, build.Target):
          pyutils.unique_extend(self.frameworks, input_.frameworks)
          self.inputs += input_.outputs
        else:
          self.inputs.append(input_)
    else:
      self.inputs = None

    # Unpack the frameworks list, which may also container Targets.
    for fw in frameworks:
      if isinstance(fw, build.Target):
        self.implicit_deps.append(fw)
        self.frameworks += fw.frameworks
      else:
        self.frameworks.append(fw)

    if option_kwargs is None:
      option_kwargs = {}

    self.name = name
    self.outputs = list(outputs)
    self.metadata = {}
    self.used_option_keys = set()

    self.option_kwargs = Framework(name, **option_kwargs)
    self.option_kwargs_defaults = Framework(name + "_defaults")
    self.options_merge = OptionMerge(self.option_kwargs,
        self.option_kwargs_defaults, *self.frameworks)
    assert self.option_kwargs in self.options_merge.frameworks

  def get(self, key, default=None):
    self.used_option_keys.add(key)
    return self.options_merge.get(key, default)

  def get_list(self, key):
    self.used_option_keys.add(key)
    return self.options_merge.get_list(key)

  def add_local_framework(self, *args, **kwargs):
    fw = Framework(*args, **kwargs)
    self.options_merge.append(fw)

  def setdefault(self, key, value):
    self.option_kwargs_defaults[key] = value

  def build(self, commands, inputs=(), outputs=(), implicit_deps=(),
      order_only_deps=(), metadata=None, **kwargs):
    """
    Create a :class:`build.Target` from the information in the builder,
    add it to the build graph and return it.
    """

    unused_keys = set(self.option_kwargs.keys()) - self.used_option_keys
    if unused_keys:
      logger.warn('TargetBuilder: "{}" unhandled option keys'.format(self.name))
      with logger.indent():
        for key in unused_keys:
          logger.warn('[-] {}={!r}'.format(key, self.option_kwargs[key]))

    # TODO: We could make this a bit shorter..
    inputs = self.inputs + list(inputs or ())
    outputs = self.outputs + list(outputs or ())
    implicit_deps = self.implicit_deps + list(implicit_deps or ())
    order_only_deps = self.order_only_deps + list(order_only_deps or ())
    if metadata is None:
      metadata = self.metadata
    elif self.metadata:
      raise RuntimeError('metadata specified in constructor and build()')

    implicit_deps = list(implicit_deps)
    for item in self.get_list('implicit_deps'):
      if isinstance(item, build.Target):
        implicit_deps += item.outputs
      elif isinstance(item, str):
        implicit_deps.append(item)
      else:
        raise TypeError('expected Target or str in "implicit_deps", found {}'
            .format(type(item).__name__))

    target = build.Target(self.name, commands, inputs, outputs, implicit_deps,
        order_only_deps, metadata=metadata, frameworks=self.frameworks, **kwargs)
    session.graph.add_target(target)
    return target


class Framework(dict):
  """
  A framework is simply a dictionary with a name to identify it. Frameworks
  are used to represent build options.
  """

  def __init__(self, __name, **kwargs):
    super().__init__(**kwargs)
    self.name = __name

  def __repr__(self):
    return '<Framework "{}": {}>'.format(self.name, super().__repr__())


class OptionMerge(object):
  """
  This class represents a virtual merge of :class:`Framework` objects. Keys
  in the first dictionaries passed to the constructor take precedence over the
  last.

  :param frameworks: One or more :class:`Framework` objects. Note that
    the constructor will expand and flatten the ``'frameworks'`` list.
  """

  def __init__(self, *frameworks):
    self.frameworks = []
    [self.append(x) for x in frameworks]

  def __getitem__(self, key):
    for options in self.frameworks:
      try:
        return options[key]
      except KeyError:
        pass  # intentional
    raise KeyError(key)

  def append(self, framework):
    def update(fw):
      if not isinstance(framework, Framework):
        raise TypeError('expected Framework, got {}'.format(type(fw).__name__))
      pyutils.unique_append(self.frameworks, fw, id_compare=True)
      [update(x) for x in fw.get('frameworks', [])]
    update(framework)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def get_list(self, key):
    """
    This function returns a concatenation of all list values saved under the
    specified *key* in all option dictionaries in this OptionMerge object.
    It gives an error if one option dictionary contains a non-sequence for
    *key*.
    """

    result = []
    for option in self.frameworks:
      value = option.get(key)
      if value is None:
        continue
      if not isinstance(value, collections.Sequence):
        raise ValueError('found "{}" for key "{}" which is a non-sequence'
            .format(tpye(value).__name__, key))
      result += value
    return result