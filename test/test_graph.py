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

from nose.tools import *
import {Graph, Node} from 'craftr/lib/graph'


def test_graph():
  g = Graph()

  node1 = g.add(Node('node1', None))
  node2 = g.add(Node('node2', None))
  node3 = g.add(Node('node3', None))
  node4 = g.add(Node('node4', None))
  node5 = g.add(Node('node5', None))
  node6 = g.add(Node('node6', None))

  with assert_raises(ValueError):
    g.add(Node('node3', None))  # Node with key 'node3' already exists

  node1.connect(node3)
  node2.connect(node3)
  node3.connect(node4)
  node3.connect(node5)
  node4.connect(node6)
  node5.connect(node6)
  list(g.topo_sort())

  node6.connect(node1)
  with assert_raises(RuntimeError):
    list(g.topo_sort())  # has cycle

  with assert_raises(ValueError):
    node1.disconnect(node6)  # no such connection

  node6.disconnect(node1)
  list(g.topo_sort())
