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

import sys
import typing as t
import {Backend} from '../../core/backend'
import {Session, Target} from '../../core/buildgraph'
import {topological_sort} from '../../core/graph'


class PythonBackend(Backend):
  """
  The pure-python Craftr build backend.
  """

  def build(self, targets: t.List[Target]):
    for node in topological_sort(self.session.action_graph):
      process = node.data.execute()
      process.wait()
      code = process.poll()
      if code != 0:
        print('*** craftr error: action {} exited with non-zero status code {}'
          .format(node.key, code), file=sys.stderr)
        process.print_stdout()
        sys.exit(code)
      else:
        process.print_stdout()
        sys.stdout.flush()

  def clean(self, targets: t.List[Target]):
    raise NotImplementedError


exports = PythonBackend
