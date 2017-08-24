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

__all__ = ['Node', 'Graph']
import typing as t
import {reqref} from './util'

K = t.TypeVar('K')
V = t.TypeVar('V')
EdgeKey = t.Tuple[K, K]


class NotReassignableError(ValueError):

  def __init__(self, key):
    self.key = key

  def __str__(self):
    msg = 'Graph does not support reassignment (attempted to reassign {!r})'
    return msg.format(self.key)


class Node(t.Generic[K, V]):

  outputs: t.List[reqref['Node[K, V]']]
  inputs: t.List[reqref['Node[K, V]']]
  key: K
  data: V

  def __init__(self, key: K, data: V):
    self.outputs = []
    self.inputs = []
    self.key = key
    self.data = data

  def __repr__(self):
    return '<Node {!r} ({} in, {} out)>'.format(
      self.key, len(self.inputs), len(self.outputs))

  def edge_to(self, node: 'Node[K, V]') -> None:
    if node not in self.inputs:
      self.inputs.append(reqref(node))
    if self not in node.outputs:
      node.outputs.append(reqref(self))


class Graph(t.Generic[K, V]):
  """
  Represents a directed graph. Graphs
  """

  nodes: t.Dict[K, Node[K, V]]
  reassignable: bool

  def __init__(self, reassignable: bool = True):
    self.nodes = {}
    self.reassignable = bool(reassignable)

  def __getitem__(self, key: K) -> V:
    return self.nodes[key].data

  def __setitem__(self, key: K, data: V) -> None:
    if not self.reassignable and key in self.nodes:
      raise NotReassignableError(key)
    node = Node(key, data)
    self.nodes[key] = node
    return node

  def __contains__(self, key: t.Union[EdgeKey, K]) -> bool:
    if isinstance(key, tuple):
      return self.has_edge(*key)
    return key in self.nodes

  def edge(self, origin: K, dest: K) -> None:
    self.nodes[dest].edge_to(self.nodes[origin])

  def has_edge(self, origin: K, dest: K) -> bool:
    return origin in self.inputs(dest)

  def inputs(self, key: K) -> t.Iterable[K]:
    return (noderef().key for noderef in self.nodes[key].inputs)

  def outputs(self, key: K) -> t.Iterable[K]:
    return (noderef().key for noderef in self.nodes[key].outputs)

  def keys(self) -> t.Iterable[K]:
    return self.nodes.keys()

  def values(self) -> t.Iterable[V]:
    return (node.data for node in self.nodes.values())

  def nodes(self) -> t.Iterable[Node]:
    return self.nodes.values()