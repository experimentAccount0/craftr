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

import abc
import typing as t
import {Target, Action} from './buildgraph'
import {Session} from './session'


class BuildBackend(metaclass=abc.ABCMeta):
  """
  Describes the interface for a build backend.
  """

  session: Session

  def __init__(self, session: Session):
    self.session = session

  @abc.abstractmethod
  def get_cached_action_key(self, action: str) -> t.Optional[str]:
    """
    Return the previous hash key of the specified *action*. This only needs
    to be implemented when the backend uses, for example, the
    #Action.skippable() method.
    """

  @abc.abstractmethod
  def build(self, targets: t.List[Target]):
    pass

  @abc.abstractmethod
  def clean(self, targets: t.List[Target]):
    pass

  @abc.abstractmethod
  def finalize(self):
    """
    Called when the build process is about to exit successfully.
    """
