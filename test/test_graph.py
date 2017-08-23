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
import {Graph} from 'craftr/core/graph'


def test_graph():
  g = Graph()
  g['//libcurl:compile'] = ['main.cpp']
  g['//libcurl:curl'] = ['libcurl.a']
  g.edge('//libcurl:compile', '//libcurl:curl')

  assert_equals(list(g.inputs('//libcurl:compile')), [])
  assert_equals(list(g.inputs('//libcurl:curl')), ['//libcurl:compile'])
  assert_equals(list(g.outputs('//libcurl:compile')), ['//libcurl:curl'])
  assert_equals(list(g.outputs('//libcurl:curl')), [])
  assert g.has_edge('//libcurl:compile', '//libcurl:curl')
  assert ('//libcurl:compile', '//libcurl:curl') in g

  print(g.nodes)
