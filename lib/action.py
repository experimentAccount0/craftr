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

class Action:
  """
  """

  def __init__(self, source, name, deps):
    """
    # Parameters
    source (Target)
    name (None, str)
    deps (list of Action)
    """

    if not isinstance(source, Target):
      raise TypeError('Action.source must be a Target')
    self.source = source

    if not isinstance(name, str):
      raise TypeError('ACtion.name must be a string')
    self.name = name

    self.deps = list(deps)
    for dep in self.deps:
      if not isinstance(dep, Action):
        raise TypeError('Action.deps[i] must be an Action')

  def __repr__(self):
    return '<{} "{}::{}">'.format(type(self).__name__, self.source.name, self.name)


import {Target} from './target'

print(Action(Target('//scope:hello', []), 'build', []))
