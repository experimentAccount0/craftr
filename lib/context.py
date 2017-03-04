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

logger = require('./logger')
weakproxy = require('./weakproxy')


class CraftrNamespace:
  """
  A Craftr namespace is added to a Node.py module with the
  #CraftrContext.namespace() method. The Craftr namespace keeps track of the
  Node.py modules that participate in the namespace and acts as a store for
  targets declared inside the namespace.
  """

  def __init__(self, name):
    self.name = name
    self.participants = []
    self.targets = {}

  def __str__(self):
    return '<CraftrNamespace {!r}>'.format(self.name)


class CraftrContext:
  """
  This class represents the Craftr build context. It keeps track of all
  modules that declare targets to the build environment.
  """

  def __init__(self):
    self.namespaces = {}

  def namespace(self, name, export_api=True):
    """
    Must be called before any targets are added to the build graph by a
    Craftr build script. This will insert a member into the global namespace
    so Craftr can identify the module later and construct full target
    identifiers and a preferred build directory.

    With *export_api* set to #True, the contents of the `@craftr/craftr/lib/api`
    module will be exported into the namespace of the calling module.
    """

    module = require.current
    if hasattr(module.namespace, '__craftr__'):
      raise RuntimeError('Craftr module already declared')

    try:
      namespace = self.namespaces[name]
    except KeyError:
      namespace = self.namespaces[name] = CraftrNamespace(name)

    namespace.participants.append(module)
    module.namespace.__craftr__ = weakproxy.new(namespace)
    logger.debug('Module %[yellow][{}] from "%[cyan][{}]" added to '
        '%[blue][{}] namespace.'.format(module.name, module.filename, name))

  def current_namespace(self):
    """
    Returns the Craftr namespace information from the module that is currently
    being executed. If no namespace information is present, a #RuntimeError
    will be raised.
    """

    module = require.current
    if not hasattr(module.namespace, '__craftr__'):
      raise RuntimeError('Module {} has no Craftr namespace information'
          .format(module))
    namespace = weakproxy.deref(module.namespace.__craftr__)
    if namespace is None:
      raise RuntimeError('CraftrNamespace reference lost')
    return namespace

