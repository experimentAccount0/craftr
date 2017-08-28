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

import json
import os
import sys
import time
import typing as t
import base from '../../core/build'
import {Target} from '../../core/buildgraph'
import {Session} from '../../core/session'


class PythonBackend(base.BuildBackend):
  """
  The pure-python Craftr build backend.
  """

  @property
  def cache_filename(self):
    return os.path.join(self.session.build_directory, 'cache.json')

  def __init__(self, session):
    super().__init__(session)
    self._cache = {}

    filename = self.cache_filename
    if os.path.isfile(filename):
      with open(filename, 'r') as fp:
        self._cache = json.load(fp)

  def _action_completed(self, action):
    action.completed = True
    data = self._cache.setdefault('actions', {}).setdefault(action.identifier, {})
    data['key'] = action.compute_hash_key()

  def get_cached_action_key(self, action: str) -> t.Optional[str]:
    return self._cache.get('actions', {}).get(action, {}).get('key')

  def build(self, targets: t.List[Target]):
    graph = self.session.actions
    actions = [n.value() for n in graph.topo_sort()]

    def can_run(action):
      for dep in action.deps():
        if not dep.completed:
          return False
      return True

    class BuildError:
      pass

    # A list of all running actions and processes.
    processes = []
    def check_process(process):
      action, process = process
      if process.is_running():
        return
      code = process.poll()
      processes.remove((action, process))
      process.print_stdout(prefix='[{}]: {}\n'.format(action.identifier, process.display_text()))
      sys.stdout.flush()
      if code != 0:
        print(file=sys.stderr)
        print('*** craftr error: action {} exited with non-zero status code {}'
          .format(action.identifier, code), file=sys.stderr)
        sys.exit(code)
      else:
        self._action_completed(action)

    try:
      for action in actions:
        while True:
          if can_run(action):
            if action.skippable(self):
              self._action_completed(action)
              break
            processes.append((action, action.execute()))
            print('[{}]: {}'.format(action.identifier, processes[-1][1].display_text()))
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
        raise
      else:
        raise

  def clean(self, targets: t.List[Target]):
    raise NotImplementedError

  def finalize(self):
    # We must only keep the hash keys for actions that are still in the graph.
    actions = self._cache.setdefault('actions', {})
    for key in list(actions.keys()):
      if key not in self.session.actions:
        del actions[key]
    with open(self.cache_filename, 'w') as fp:
      json.dump(self._cache, fp)


exports = PythonBackend
