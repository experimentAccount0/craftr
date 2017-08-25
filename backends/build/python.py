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
import time
import typing as t
import {Backend} from '../../core/backend'
import {Session, Target} from '../../core/buildgraph'
import {topological_sort} from '../../core/graph'


class PythonBackend(Backend):
  """
  The pure-python Craftr build backend.
  """

  def build(self, targets: t.List[Target]):
    graph = self.session.action_graph
    completed_actions = set()
    actions = [n.data for n in topological_sort(graph)]

    def can_run(action):
      for dep in graph.inputs(action.identifier):
        if dep not in completed_actions:
          return False
      return True

    class BuildError:
      pass

    # A list of all running actions and processes.
    processes = []
    def check_process(process):
      action, process = process
      code = process.poll()
      if code is None: return
      processes.remove((action, process))
      completed_actions.add(action.identifier)
      process.print_stdout(prefix='[{}]: {}\n'.format(action.identifier, process.display_text()))
      sys.stdout.flush()
      if code != 0:
        print(file=sys.stderr)
        print('*** craftr error: action {} exited with non-zero status code {}'
          .format(action.identifier, code), file=sys.stderr)
        sys.exit(code)

    try:
      for action in actions:
        while True:
          if can_run(action):
            processes.append((action, action.execute()))
            print(processes[-1][1].display_text())
            break

          # Check the status of all currently running processes.
          for process in processes[:]:
            check_process(process)

          time.sleep(0.25)

      while processes:
        for process in processes[:]:
          check_process(process)
        time.sleep(0.25)

    except BaseException as e:
      for action, process in processes:
        if process.poll() is None:
          process.terminate()
      for action, process in processes:
        process.wait()

      time.sleep(0.25)
      if isinstance(e, KeyboardInterrupt):
        print(file=sys.stderr)
        print('*** craftr error: keyboard interrupt', file=sys.stderr)
      else:
        raise

  def clean(self, targets: t.List[Target]):
    raise NotImplementedError


exports = PythonBackend
