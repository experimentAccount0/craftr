# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
This module provides an implementation of a directed graph (usually acyclic,
although that is not enforced). Every node has to have one unique identifier
that is constant through its entire lifetime.
"""

import collections
import typing as t
import reqref from './reqref'

K, V = t.TypeVar('K'), t.TypeVar('V')


class Node(t.Generic[K, V]):
  """
  Represents a Node in a directed graph. Every Node requires unique identifier
  that is constant throughout its entire lifetime. The key of a node must be
  hashable. The value of a #Node can be arbitrary.
  """

  def __init__(self, key: K, value: V):
    self.__graph = None
    self.__key = key
    self.__value = value
    self.__inputs = set()
    self.__outputs = set()

  def __repr__(self):
    tname = type(self).__name__
    return '<{} key={!r} value={!r}>'.format(tname, self.__key, self.__value)

  @property
  def graph(self):
    if self.__graph is not None:
      return self.__graph()
    return None

  @property
  def key(self) -> K:
    return self.__key

  @property
  def value(self) -> V:
    return self.__value

  @property
  def inputs(self) -> t.Set['Node[K, V]']:  # TODO: Return a view only
    return self.__inputs

  @property
  def outputs(self) -> t.Set['Node[K, V]']:  # TODO: Return a view only
    return self.__outputs

  def connect(self, dest: 'Node[K, V]') -> None:
    assert self.__graph().has_node(dest), dest
    self.__outputs.add(dest)
    dest.__inputs.add(self)

  def disconnect(self, dest: 'Node[K, V]') -> None:
    assert self.__graph().has_node(dest), dest
    if dest in self.__outputs:
      if self not in dest.__inputs:
        raise RuntimeError('graph consistency is compromised')
      self.__outputs.remove(dest)
      dest.__inputs.remove(self)
    elif self in dest.__inputs:
      raise RuntimeError('graph consistency is compromised')
    else:
      raise ValueError('no connection {!r} -> {!r}'.format(self.__key, dest.__key))

  def disconnect_all(self) -> None:
    for source in self.__inputs:
      source.__outputs.remove(self)
    for dest in self.__outputs:
      dest.__inputs.remove(self)
    self.__inputs.clear()
    self.__outputs.clear()


class Graph(t.Generic[K, V]):
  """
  Represents a directed graph that is constructed of #Node objects.
  """

  def __init__(self):
    self.__nodes = {}

  def __getitem__(self, key: K):
    return self.__nodes[key]

  def __contains__(self, key: t.Union[Node[K, V], K]):
    if isinstance(key, Node):
      try:
        have_node = self.__nodes[key.key]
      except KeyError:
        return False
      return have_node is key
    else:
      return key in self.__nodes

  has_node = __contains__

  def add(self, node: Node[K, V]) -> None:
    assert node._Node__graph in (None, self)
    node._Node__graph = reqref.ref(self)
    try:
      has_node = self.__nodes[node.key]
    except KeyError:
      pass
    else:
      if has_node is not node:
        raise ValueError('can not other node with same key: {!r}'.format(node.key))
    self.__nodes[node.key] = node
    return node

  def remove(self, node: Node[K, V]) -> Node[K, V]:
    has_node = self.__nodes.pop(node.key)
    if has_node is not node:
      self.add(has_node)
      raise ValueError('containing other node with same key: {!r}'.format(node.key))
    node.disconnect_all()
    node._Node__graph = None

  def node(self, key: K, default: t.Any = ...) -> t.Union[Node[K, V], t.Any]:
    if default is ...:
      return self.__nodes[key]
    else:
      return self.__nodes.get(key, default)

  def nodes(self) -> t.Iterable[Node[K, V]]:
    return self.__nodes.values()

  def roots(self) -> t.Iterable[Node[K, V]]:
    return (node for node in self.__nodes.values() if not node.inputs)

  def leafs(self) -> t.Iterable[Node[K, V]]:
    return (node for node in self.__nodes.values() if not node.outputs)

  def topo_sort(self) -> t.Iterable[Node[K, V]]:
    """
    Topologically sort the graph using Khan's Algorithm (1962). If the graph
    has a cycle, a #RuntimeError will be raised after the topological sort
    is completed.
    """

    roots = collections.deque(self.roots())
    input_counts = {node: len(node.inputs) for node in self.nodes()}
    marked_edges = set()

    while roots:
      node = roots.popleft()
      yield node

      # Update the number of un-processed input nodes, update root if the
      # count reaches zero.
      for output_node in node.outputs:
        n_inputs = input_counts[output_node]
        if (node, output_node) not in marked_edges:
          assert n_inputs > 0
          n_inputs -= 1
          input_counts[output_node] = n_inputs
          marked_edges.add((node, output_node))
        if n_inputs == 0:
          roots.append(output_node)

    # Check if the graph had any cycles.
    for node, n_inputs in input_counts.items():
      if n_inputs > 0:
        raise RuntimeError('Graph has at least one cycle.')


def dotviz(
    fp: t.IO[str],
    nodes: t.Iterable[Node[K, V]],
    title: str = 'Graph',
    text: t.Callable[[Node[K, V]], str] = None) -> None:
  """
  Convert a list of #Node's to DOT graph visualization format. The DOT code
  is rendered to *fp*. If *text* is specified, it must be a callable that
  receives a Node and returns a string representation for it. By default,
  the node's key is displayed.
  """

  if text is None:
    def text(node):
      return str(node.key)

  print('digraph "{}" {{'.format(title), file=fp)
  for node in nodes:
    print('\t{} [label="{}"];'.format(id(node), text(node)), file=fp)
    for other in node.inputs:
      print('\t\t{} -> {};'.format(id(other), id(node)), file=fp)
  print('}', file=fp)
