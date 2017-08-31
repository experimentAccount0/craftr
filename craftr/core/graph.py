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

import graph from '../lib/graph'


class BaseGraph(graph.Graph):
  """
  Duck typing, yeay!
  """

  @classmethod
  def from_(cls, objects):
    g = cls()
    for obj in objects:
      g.add(obj)
    return g

  def add(self, obj, recursive=True):
    try:
      node = self[obj.long_name]
      assert node.value is obj, (node.value, obj)
      return node
    except KeyError:
      node = graph.Node(obj.long_name, obj)
      super().add(node)

    if recursive:
      for dep in obj.deps:
        other = self.add(dep, True)
        other.connect(node)
      for dep in getattr(obj, 'visible_deps', ()):
        other = self.add(dep, True)
        other.connect(node)
    return node

  def remove(self, obj):
    node = self[obj.long_name]
    super().remove(node)

  def topo_sort(self):
    for node in super().topo_sort():
      yield node.value

  def values(self):
    return (node.value for node in self.nodes())


class TargetGraph(BaseGraph):

  def translate(self, all=False):
    for target in self.topo_sort():
      target.translate()
    g = ActionGraph()
    for target in self.values():
      for action in target.actions.values():
        if all or not action.explicit:
          g.add(action)
    return g


class ActionGraph(BaseGraph):

  def with_actions_from_targets(self, targets):
    for target in targets:
      for action in target.actions.values():
        self.add(action)
