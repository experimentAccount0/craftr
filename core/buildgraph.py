
import abc
import io
import typing as t
import graph from '../lib/graph'
import reqref from '../lib/reqref'
import task from '../lib/task'
import {file_iter_chunks} from '../lib/file'


class Cell:

  name: str
  version: str
  directory: str
  targets: t.Set['Target']

  def __init__(self, name, version, directory):
    self.name = name
    self.version = version
    self.directory = directory
    self.targets = set()

  def __repr__(self):
    return '<Cell "{}">'.format(self.name)


class Target:

  session: 'Session'
  cell: Cell
  name: str
  visible_deps: t.List['Target']
  impl: 'TargetImpl'
  node: graph.Node[str, reqref.ref['Target']]
  actions: t.Set['Action']
  translated: bool = False

  def __init__(self, session, cell, name, visible_deps, impl):
    self.session = session
    self.cell = cell
    self.name = name
    self.visible_deps = visible_deps
    self.impl = impl
    self.node = graph.Node(self.long_name, reqref.ref(self))
    self.actions = set()
    impl.target = self
    session.targets.add(self.node)
    cell.targets.add(self)

  def __repr__(self):
    return '<{} "{}">'.format(type(self).__name__, self.long_name)

  @property
  def long_name(self):
    return '//{}:{}'.format(self.cell.name, self.name)

  def deps(self):
    return (node.value() for node in self.node.inputs)

  def transitive_deps(self):
    # Recursively collect all transitive dependencies.
    def recursion(target):
      result.extend(target.visible_deps)
      [recursion(dep) for dep in target.visible_deps]
    result = list(self.deps()) + self.visible_deps
    [recursion(dep) for dep in result]

    # Create unique entries in the resulting list.
    # NOTE: dicts being ordered is a 3.6 implementation detail. Since
    #       Craftr will only run CPython 3.6+, that's fine for now. We
    #       should check back in 3.7 if it stayed the same, though.
    result = list(dict.fromkeys(result))
    return result

  def leaf_actions(self):
    return (action for action in self.actions if not action.node.outputs)

  def translate(self):
    if self.translated:
      return
    for dep in self.deps():
      dep.translate()
    self.impl.translate()
    self.translated = True


class Action:

  session: 'Session'
  target: Target
  name: str
  impl: 'ActionImpl'
  input_files: t.List[str]
  output_files: t.List[str]
  node: graph.Node[str, reqref.ref['Action']]
  task: task.Task
  satisfied: bool = False
  aborted: bool = False
  __hash_key: t.Optional[str] = None

  def __init__(self, session, target, name, input_files, output_files, impl):
    self.session = session
    self.target = target
    self.name = name
    self.impl = impl
    self.input_files = input_files
    self.output_files = output_files
    self.node = graph.Node(self.long_name, reqref.ref(self))
    impl.action = self
    session.actions.add(self.node)
    target.actions.add(self)

  def __repr__(self):
    return '<{} "{}">'.format(type(self).__name__, self.long_name)

  @property
  def long_name(self):
    return '//{}!{}'.format(self.target.long_name, self.name)

  def deps(self):
    return (node.value() for node in self.node.inputs)

  def deps_satisfied(self):
    return all(action.satisfied for action in self.deps())

  def hash_key(self):
    if self.__hash_key is not None:
      return self.__hash_key
    if not self.deps_satisfied():
      raise RuntimeError('All action dependencies need to be satisfied '
        'before action hash key can be calulcated.')

    build_directory = self.session.build_directory
    scope_directory = self.target.cell.directory
    hasher = self.session.new_hasher()
    hasher.update(self.target.cell.version.encode('utf8'))

    for comp in self.impl.hash_components():
      if isinstance(comp, hashing.DataComponent):
        hasher.update(comp.data)
      elif isinstance(comp, hashing.FileComponent):
        # Find the canonical path relative to the build directory.
        directory = scope_directory if comp.is_input else build_directory
        filename = path.canonical(path.rel(comp.filename, directory))
        hasher.update(filename.encode('utf8'))

        # Hashing the contents of input files is also necessary as the same
        # action with the same inputs and outputs etc. could be build with
        # different contents in the input files.
        if comp.is_input:
          try:
            with open(comp.filename, 'rb') as fp:
              for chunk in file_iter_chunks(fp, 4096):
                hasher.update(chunk)
          except (FileNotFoundError, PermissionError):
            pass

    self.__hash_key = hasher.hexdigest()
    return self.__hash_key

  def abort(self, join=False):
    if not self.task:
      raise RuntimeError('action has not been executed')
    self.impl.abort()

  def wait(self):
    if not self.task:
      raise RuntimeError('action has not been executed')
    self.task.join()

  def execute(self):
    if self.task:
      raise RuntimeError('action has already been executed')


class TargetImpl(metaclass=abc.ABCMeta):
  """
  An implementation for a target's behaviour.
  """

  target: Target = None

  def new_action(self, action_impl_type, name, input_files = None,
                 output_files = None, deps = None, **kwargs):
    """
    Create a new action.
    """

    input_files = [] if input_files is None else input_files
    output_files = [] if output_files is None else output_files
    actual_deps = []

    # Process the dependencies.
    for dep in ([] if deps is None else deps):
      if isinstance(dep, Target):
        actual_deps.append(dep.leaf_actions())
      elif isinstance(dep, Action):
        actual_deps.append(dep)
      else:
        tn = type(dep).__name__
        raise TypeError('deps[i] must be Target/Action, got {}'.format(tn))

    impl = action_impl_type(**kwargs)
    return Action(self.target.session, self.target, name, input_files,
                  output_files, impl)

  @abc.abstractmethod
  def translate(self):
    """
    Translate the target into the action graph. Use the #new_action() method.
    """


class ActionImpl(metaclass=abc.ABCMeta):
  """
  An implementation of an action's behaviour.
  """

  action: Action = None
  buffer: io.BytesIO
  __aborted: bool = False

  def __init__(self):
    self.buffer = io.BytesIO()

  def hash_components(self) -> t.List['HashComponent']:
    """
    Implement this function to yield all information that needs to be encoded
    in the action hash key. The default implementation yields the action name
    and input and output files.
    """

    yield hashing.DataComponent(self.action.long_name.encode('utf8'))
    for filename in self.action.input_files:
      yield hashing.FileComponent(filename, True)
    for filename in self.action.output_files:
      yield hashing.FileComponent(filename, False)

  @abc.abstractmethod
  def display(self, full: bool) -> str:
    """
    Return a string representation of the action, either in full (which is
    used when information about the action is displayed only once) or in its
    current state (which is used when the action's progress is displayed
    continously).
    """

  @abc.abstractmethod
  def progress(self) -> t.Optional[float]:
    """
    Return the progress of the action's execution. The returned value does
    not need to be consistent over time and is only for display purposes.
    If #None is returned, the action is considered to have no progress
    information available.
    """

  @abc.abstractmethod
  def abort(self):
    """
    Called when the action's execution is supposed to be aborted. After this
    method is called, #action.aborted is #True as well.
    """

  @abc.abstractmethod
  def execute(self) -> int:
    """
    Execute the action. This function is called in a separate thread. Make
    sure to sometimes check for the value of #aborted() to stop the execution
    preemptively. During the execution, all output should usually be directed
    to the #buffer.

    An integer must be returned that indicates the result of the action's
    execution (0 meaning success).
    """


class HashComponent(t.NamedTuple):
  pass


class FileComponent(HashComponent):
  filename: str
  is_input: bool


class DataComponent(HashComponent):
  data: bytes
