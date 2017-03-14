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
ninja = require('./ninja')
path = require('./utils/path')
weakproxy = require('./utils/weakproxy')


class CraftrNamespace:
  """
  A Craftr namespace is added to a Node.py module with the
  #CraftrContext.namespace() method. The Craftr namespace keeps track of the
  Node.py modules that participate in the namespace and acts as a store for
  targets declared inside the namespace.
  """

  def __init__(self, name, context, directory):
    self.name = name
    self.participants = []
    self.targets = {}
    self.context = weakproxy.new(context)
    self.directory = directory

  def __str__(self):
    return '<CraftrNamespace {!r} at {!r}>'.format(self.name, self.directory)

  def register_target(self, name, target):
    if name in self.targets:
      raise ValueError('target {!r} already exists in namespace {!r}'
          .format(name, self.name))
    self.context.graph.add_target(target)
    self.targets[name] = target


class CraftrContext:
  """
  This class represents the Craftr build context. It keeps track of all
  modules that declare targets to the build environment.
  """

  def __init__(self):
    self.build_dir = 'build'
    self.namespaces = {}
    self.graph = ninja.Graph()
    self.platform_helper = ninja.get_platform_helper()
    self.ninja = None  # Initialized from the CLI\
    self.options = {}
    self.cache = {}
    self.do_export = False

  def namespace(self, name=None, export_api=True, directory=None):
    """
    Must be called before any targets are added to the build graph by a
    Craftr build script. This will insert a member into the global namespace
    so Craftr can identify the module later and construct full target
    identifiers and a preferred build directory.

    With *export_api* set to #True, the contents of the `@craftr/craftr/lib/api`
    module will be exported into the namespace of the calling module.

    If no *name* is specified, the namespace of the parent module is inherited.

    If the namespace is not already registered, it's directory will be
    determined automatically from the current module's location, unless the
    *directory* parameter is set. A relative path in this parameter will be
    considered relative to the current modules actual location. If the
    *directory* is specified but the namespace has already been introduced,
    a #RuntimeError is raised.
    """

    module = require.current
    if hasattr(module.namespace, '__craftr__'):
      raise RuntimeError('Craftr module already declared')

    if name is None:
      # Find the parent namespace.
      name = self.current_namespace(1).name

    try:
      namespace = self.namespaces[name]
    except KeyError:
      if directory is None:
        directory = module.directory
      else:
        directory = path.norm(directory, module.directory)
      namespace = self.namespaces[name] = CraftrNamespace(name, self, directory)
    else:
      if directory is not None:
        raise RuntimeError('namespace has already been introduced, yet '
            'a namespace directory has been specified.')

    namespace.participants.append(module)
    module.namespace.__craftr__ = weakproxy.new(namespace)
    logger.debug("Added module '%[cyan][{}]' to '%[magenta][{}]' namespace."
        .format(module.filename, name))

    if export_api:
      api = require('./api')
      for key in api.__all__:
        setattr(module.namespace, key, getattr(api, key))

  def current_namespace(self, index=0):
    """
    Returns the Craftr namespace information from the module that is currently
    being executed. If no namespace information is present, a #RuntimeError
    will be raised.
    """

    index += 1
    if index >= len(require.context.current_modules):
      raise RuntimeError('no parent module at index {!r}'.format(index - 1))

    module = require.context.current_modules[-index]
    if not hasattr(module.namespace, '__craftr__'):
      raise RuntimeError('Module {} has no Craftr namespace information'
          .format(module))
    namespace = weakproxy.deref(module.namespace.__craftr__)
    if namespace is None:
      raise RuntimeError('CraftrNamespace reference lost')
    return namespace
