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

__all__ = ['null', 'NullAction']

import api from '../api'
import {Action, ActionProcess} from '../core/buildgraph'


class NullActionProcess(ActionProcess):

  def display_text(self):
    return 'NullAction'

  def terminate(self):
    pass

  def is_running(self):
    return False

  def wait(self):
    pass

  def poll(self):
    return 0

  def stdout(self):
    return b''


class NullAction(Action):
  """
  An action that represents no action. It is used for example in targets that
  represent prebuilt information where nothing actually needs to be done.
  While generating no actions from a target is valid, order of dependencies
  would be lost if no action would be generated.
  """

  def execute(self):
    return NullActionProcess()


null = api.action_factory(NullAction)
