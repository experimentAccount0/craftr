# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
:mod:`craftr.core.session`
==========================

This module provides the :class:`Session` class which manages the loading
process of Craftr modules and contains all the important root datastructures
for the meta build process (such as a :class:`craftr.core.build.Graph`).
"""

build = require('./build')
logger = require('./logging').logger
manifest = require('./manifest')
Manifest = manifest.Manifest
renames = require('./renames')
argspec = require('../utils/argspec')
path = require('../utils/path')

from nr.types.version import Version, VersionCriteria

import json
import os
import sys
import tempfile
import types
import werkzeug

MANIFEST_FILENAMES = ['manifest.cson', 'manifest.json']


class ModuleNotFound(Exception):

  def __init__(self, name, version):
    self.name = name
    self.version = version

  def __str__(self):
    if isinstance(self.version, Version):
      return '{}[={}]'.format(self.name, self.version)
    else:
      return '{}[{}]'.format(self.name, self.version)


class InvalidOption(Exception):

  def __init__(self, module, errors):
    self.module = module
    self.errors = errors

  def __str__(self):
    return '\n'.join(self.format_errors())

  def format_errors(self):
    for option, value, exc in self.errors:
      yield '{}.{} ({}): {}'.format(self.module.manifest.name, option.name,
          self.module.manifest.version, exc)


class Session(object):
  """
  This class manages the :class:`build.Graph` and loading of Craftr modules.

  .. attribute:: graph

    A :class:`build.Graph` instance.

  .. attribute:: path

    A list of paths that will be searched for Craftr modules.

  .. attribute:: module

    The Craftr module that is currently being executed. This is an instance
    of the :class:`Module` class and the same as the tip of the
    :attr:`modulestack`.

  .. attribute:: modulestack

    A list of modules where the last element (tip) is the module that is
    currently being executed.

  .. attribute:: modules

    A nested dictionary that maps from name to a dictionary of version
    numbers mapping to :class:`Module` objects. These are the modules that
    have already been loaded into the session or that have been found and
    cached but not yet been executed.

  .. attribute:: preferred_versions

    A nested dictionary with the same structure as :attr:`modules`. This
    dictionary might have been loaded from a dependency lock file and specifies
    the preferred version to load for a specific module, assuming that the
    criteria specified in the loading module's manifest is less strict. Note
    that Craftr will error if a preferred version can not be found.

  .. attribute:: maindir

    The main directory from which Craftr was run. Craftr will switch to the
    build directory at a later point, which is why we keep this member for
    reference.

  .. attribute:: builddir

    The absolute path to the build directory.

  .. attribute:: main_module

    The main :class:`Module`.

  .. attribute:: options

    A dictionary of options that are passed down to Craftr modules.

  .. attributes:: cache

    A JSON object that will be loaded from the current workspace's cache
    file and written back when Craftr exits without errors. The cache can
    contain anything and can be modified by everything, however it should
    be assured that no name conflicts and accidental modifications/deletes
    occur.

    Reserved keywords in the cache are ``"build"`` and ``"loaders"``.
  """

  #: The current session object. Create it with :meth:`start` and destroy
  #: it with :meth:`end`.
  current = None

  #: Diretory that contains the Craftr standard library.
  stl_dir = path.norm(path.join(__file__, '../../stl'))
  stl_auxiliary_dir = path.norm(path.join(__file__, '../../stl_auxiliary'))

  def __init__(self, maindir=None):
    self.maindir = path.norm(maindir or path.getcwd())
    self.builddir = path.join(self.maindir, 'build')
    self.graph = build.Graph()
    self.path = [self.stl_dir, self.stl_auxiliary_dir, self.maindir,
        path.join(self.maindir, 'craftr/modules')]
    self.platform_helper = build.get_platform_helper()
    self.modulestack = []
    self.modules = {}
    self.preferred_versions = {}
    self.main_module = None
    self.options = {}
    self.cache = {}
    self.tasks = {}
    self._tempdir = None
    self._manifest_cache = {}  # maps manifest_filename: manifest
    self._refresh_cache = True

  def __enter__(self):
    if Session.current:
      raise RuntimeError('a session was already created')
    Session.current = self
    return Session.current

  def __exit__(self, exc_value, exc_type, exc_tb):
    if Session.current is not self:
      raise RuntimeError('session not in context')
    if self._tempdir and not self.options.get('craftr.keep_temporary_directory'):
      logger.debug('removing temporary directory:', self._tempdir)
      try:
        path.remove(self._tempdir, recursive=True)
      except OSError as exc:
        logger.debug('error:', exc, indent=1)
      finally:
        self._tempdir = None
    Session.current = None

  @property
  def module(self):
    if self.modulestack:
      return self.modulestack[-1]
    return None

  def read_cache(self, fp):
    cache = json.load(fp)
    if not isinstance(cache, dict):
      raise ValueError('Craftr Session cache must be a JSON object, got {}'
          .format(type(cache).__name__))
    self.cache = cache

  def write_cache(self, fp):
    json.dump(self.cache, fp, indent='\t')

  def expand_relative_options(self, module_name=None):
    """
    After the main module has been detected, relative option names (starting
    with ``.``) should be converted to absolute option names. This is what
    the method does.
    """

    if not module_name and not self.main_module:
      raise RuntimeError('main_module not set')
    if not module_name:
      module_name = self.main_module.manifest.name

    for key in tuple(self.options.keys()):
      if key.startswith('.'):
        self.options[module_name + key] = self.options.pop(key)

  def get_temporary_directory(self):
    """
    Returns a writable temporary directory that is primarily used by loaders
    to store temporary files. The temporary directory will be deleted when
    the Session context ends unless the ``craftr.keep_temporary_directory``
    option is set.

    :raise RuntimeError: If the session is not currently in context.
    """

    if Session.current is not self:
      raise RuntimeError('session not in context')
    if not self._tempdir:
      self._tempdir = path.join(self.builddir, '.temp')
      logger.debug('created temporary directory:', self._tempdir)
    return self._tempdir


class Module(object):
  """
  This class represents a Craftr module that has been or is currently being
  executed. Every module has a project directory and a manifest with some
  basic information on the module such as its name, version, but also things
  like its dependencies and options.

  Every Craftr project (i.e. module) contains a ``manifest.json`` file
  and the main ``Craftrfile``.

  ::

    myproject/
      include/
      source/
      Craftrfile
      manifest.json

  .. attribute:: directory

    The directory that contains the ``manifest.json``. Note that the actual
    project directory depends on the :attr:`Manifest.project_dir` member.

  .. attribute:: ident

    A concentation of the name and version defined in the :attr:`manifest`.

  .. attribute:: project_dir

    Path to the project directory as specified in the :attr:`manifest`.

  .. attribute:: manifest

  .. attribute:: namespace

  .. attribute:: executed

    True if the module was executed with :meth:`run`.

  .. attribute:: options

    A :class:`~craftr.core.manifest.Namespace` that contains all the options
    for the module. This member is only initialized when the module is run
    or with :meth:`init_options`.

  .. attribute:: dependent_files

    A list of all files that influence the state of the module. This list
    is generated when the module is executed with :func:`run`. By default,
    it contains at least the filename of the :attr:`manifest` and the script
    file that is executed for the Module. Additional files might be added
    by some built-in functions like :func:`craftr.defaults.load_file`.

  .. attribute:: dependencies

    A dictionary that maps a dependency name to an actual version. This
    dictionary may contain only a subset of the dependencies listed in the
    modules manifest as the module may only load some of the dependencies.
  """

  NotFound = ModuleNotFound
  InvalidOption = InvalidOption

  def __init__(self, directory, manifest):
    self.directory = directory
    self.manifest = manifest
    self.namespace = types.ModuleType(self.manifest.name)
    self.executed = False
    self.options = None
    self.dependent_files = None
    self.dependencies = None

  def __repr__(self):
    return '<craftr.core.session.Module "{}-{}">'.format(self.manifest.name,
      self.manifest.version)

  @property
  def ident(self):
    return '{}-{}'.format(self.manifest.name, self.manifest.version)

  @property
  def project_dir(self):
    return path.norm(path.join(self.directory, self.manifest.project_dir))

  @property
  def scriptfile(self):
    return path.norm(path.join(self.directory, self.manifest.main))

  def init_options(self, recursive=False, _break_recursion=None):
    """
    Initialize the :attr:`options` member. Requires an active session context.

    :param recursive: Initialize the options of all dependencies as well.
    :raise InvalidOption: If one or more options are invalid.
    :raise ModuleNotFound: If *recursive* is specified and a dependency
      was not found.
    :raise RuntimeError: If there is no current session context.
    """

    if not session:
      raise RuntimeError('no current session')
    if _break_recursion is self:
      return

    if recursive:
      for name, version in self.manifest.dependencies.items():
        module = session.find_module(name, version)
        module.init_options(True, _break_recursion=self)

    if self.options is None:
      errors = []
      self.options = self.manifest.get_options_namespace(session.options, errors)
      if errors:
        self.options = None
        raise InvalidOption(self, errors)

  def run(self):
    """
    Loads the code of the main Craftr build script as specified in the modules
    manifest and executes it. Note that this must occur in a context where
    the :data:`session` is available.

    :raise RuntimeError: If there is no current :data:`session` or if the
      module was already executed.
    """

    if not session:
      raise RuntimeError('no current session')
    if self.executed:
      raise RuntimeError('already run')

    self.executed = True
    self.dependent_files = []
    self.dependencies = {}
    self.init_options()

    script_fn = self.scriptfile
    with open(script_fn) as fp:
      code = compile(fp.read(), script_fn, 'exec')

    self.dependent_files.append(self.manifest.filename)
    self.dependent_files.append(script_fn)

    ModuleReturn = require('../defaults').ModuleReturn

    vars(self.namespace).update(self.get_init_globals())
    self.namespace.__file__ = script_fn
    self.namespace.__name__ = self.manifest.name
    self.namespace.__version__ = str(self.manifest.version)
    try:
      session.modulestack.append(self)
      exec(code, vars(self.namespace))
    except ModuleReturn:
      pass
    finally:
      assert session.modulestack.pop() is self

  def get_init_globals(self):
    """
    Returns a dictionary initialized with the default built-in values for a
    build script.
    """

    defaults = require('../defaults')
    result = {}
    for key, value in vars(defaults).items():
      if not key.startswith('_'):
        result[key] = value
    result.update({
      'options': self.options,
      'project_dir': self.project_dir
    })
    return result

  @property
  def current_line(self):
    """
    This property is only accessible when the module is currently begin
    executed, and only from within the same thread. Returns the line at
    which the module is currently being executed.
    """

    frame = sys._getframe()
    while frame and frame.f_globals is not vars(self.namespace):
      frame = frame.f_back
    if not frame:
      raise RuntimeError('module frame not found')
    return frame.f_lineno


#: Proxy object that points to the current :class:`Session` object.
session = werkzeug.LocalProxy(lambda: Session.current)
