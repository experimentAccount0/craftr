
import typing as t
import graph from '../lib/graph'
import platform from './platform'
import {Configuration} from './config'
import {Cell, Target, Action} from './buildgraph'


class Session:
  """
  The session manages cells and the target and action graph.
  """

  build: 'BuildBackend'
  build_directory: str
  stashes: 'StashServer'
  targets: graph.Graph[str, Target]
  actions: graph.Graph[str, Action]
  cells: t.Dict[str, Cell]
  cellstack: t.List[Cell]
  config: Configuration

  def __init__(self, target: str = 'debug', arch: str = None):
    self.build = None
    self.build_directory = None
    self.targets = graph.Graph()
    self.actions = graph.Graph()
    self.cells = {}
    self.cellstack = []
    self.config = Configuration({
      'arch': arch or platform.arch,
      'platform': platform.name,
      'target': target
    })
    self.config['build.arch'] = arch or platform.arch
    self.config['build.target'] = target

  @property
  def arch(self):
    return self.config['build.arch']

  @property
  def target(self):
    return self.config['build.target']

  @property
  def current_cell(self) -> Cell:
    return self.cellstack[-1]

  def cell(self, name: str) -> Cell:
    return self.cells[name]

  def enter_cell(self, name: str, directory: str, version: str) -> Cell:
    if name not in self.cells:
      cell = Cell(name, version, directory)
      self.cells[name] = cell
    else:
      cell = self.cells[name]
      if cell.directory != directory or cell.version != version:
        raise RuntimeError('cell mismatch (duplicate cells?)')
    self.cellstack.append(cell)
    return cell

  def leave_cell(self, name: str) -> None:
    assert self.cellstack.pop().name == name

  def translate_targets(self):
    """
    Translate all targets to actions.
    """

    for node in self.targets.leafs():
      node.value().translate()

    for node in self.targets.nodes():
      assert node.value().translated, node.value()
