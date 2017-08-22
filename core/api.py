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

__all__ = ['session', 'target', 'platform', 'pool']
import werkzeug.local as _local
import typing
import {TargetRef} from './utils'
import {Target, Pool} from './graph'

ListOfTargetRefsType = typing.List[typing.Union[str, TargetRef, Target]]


local = _local.Local()

#: The current session.
session = local('session')

#: A string that represents the current build target. For debug and production
#: builds, this string is either "release" or "debug". Other names can be used,
#: in which case most build targets will omitt translating to the action graph
#: completely (eg. "docs", and only targets that are used to build documentation
#: files are translated into actions).
target = _local.LocalProxy(lambda: session.target)

#: The name of the current platform.
import {name as platform} from './platform'


def new_target(target_type: typing.Type[Target], *,
               name: str, deps: ListOfTargetRefsType,
               visible_deps: typing.Optional[ListOfTargetRefsType] = None,
               pool: typing.Optional[typing.Union[str, TargetRef, Pool]] = None,
               **kwargs) -> Target:
  """
  Creates a new target of the specified *target_type* and adds it to the
  current scope.
  """

  def eval_deps(deps):
    result = []
    for dep in deps:
      if not isinstance(dep, Target):
        dep = session.find_target(dep)
      result.append(dep)
    return result

  deps = eval_deps(deps)
  visible_deps = eval_deps(visible_deps) if visible_deps is not None else None

  if pool is not None and not isinstance(pool, Pool):
    pool = session.find_pool(pool)

  return session.current_scope.new_target(target_type, name=name, deps=deps,
    visible_deps=visible_deps, pool=pool, **kwargs)


def pool(*, name: str, depth: int) -> Pool:
  """
  Create a new pool in the current scope.
  """

  return session.current_scope.new_pool(name, depth)
