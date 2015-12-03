# Copyright (C) 2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
''' This module is where all the magic comes from. '''

__all__ = [
  'new_context', 'test_context', 'enter_context', 'deref',
  'get_frame', 'get_assigned_name']

from contextlib import contextmanager
from werkzeug import LocalStack, LocalProxy
from sys import _getframe as get_frame

import dis


def new_context(context_name):
  ''' Create a new context with the specified *context_name* and
  return a `LocalProxy` that represents the top-most object of the
  context stack. '''

  def _lookup():
    top = object.__getattribute__(proxy, '_proxy_localstack').top
    if top is None:
      raise RuntimeError('outside of {0!r} context'.format(context_name))
    return top

  proxy = LocalProxy(_lookup)
  stack = LocalStack()
  object.__setattr__(proxy, '_proxy_localstack', stack)
  return proxy


def test_context(context_proxy):
  ''' Test if there is a context for the specified proxy and return True
  in that case, False otherwise. This can be used to check if accessing
  the proxy would raise a RuntimeError. '''

  assert isinstance(context_proxy, LocalProxy)
  stack = object.__getattribute__(context_proxy, '_proxy_localstack')
  return stack.top is not None


@contextmanager
def enter_context(context_proxy, context_obj):
  ''' Contextmanager that pushes the *context_obj* on the context stack
  of the specified *context_proxy* and pops it on exit. If the context
  object supports it, the methods `context_obj.on_context_enter()` and
  `context_obj.on_context_leave()` will be called. '''

  assert isinstance(context_proxy, LocalProxy)
  stack = object.__getattribute__(context_proxy, '_proxy_localstack')
  if hasattr(context_obj, 'on_context_enter'):
    context_obj.on_context_enter(stack.top)
  stack.push(context_obj)
  try:
    yield
  finally:
    try:
      assert stack.pop() is context_obj
    finally:
      if hasattr(context_obj, 'on_context_leave'):
        context_obj.on_context_leave()


def deref(proxy):
  ''' Dereference a `LocalProxy`. '''

  assert isinstance(proxy, LocalProxy)
  return proxy._LocalProxy__local()


def get_assigned_name(frame):
  ''' Checks the bytecode of *frame* to find the name of the variable
  a result is being assigned to and returns that name. Returns the full
  left operand of the assignment. Raises a `ValueError` if the variable
  name could not be retrieved from the bytecode (eg. if an unpack sequence
  is on the left side of the assignment).

      >>> var = get_assigned_frame(sys._getframe())
      >>> assert var == 'var'
  '''

  SEARCHING, MATCHED = 1, 2
  state = SEARCHING
  result = ''
  for op in dis.get_instructions(frame.f_code):
    if state == SEARCHING and op.offset == frame.f_lasti:
      state = MATCHED
    elif state == MATCHED:
      if result:
        if op.opname == 'LOAD_ATTR':
          result += op.argval + '.'
        elif op.opname == 'STORE_ATTR':
          result += op.argval
          break
        else:
          raise ValueError('expected {LOAD_ATTR, STORE_ATTR}', op.opname)
      else:
        if op.opname in ('LOAD_NAME', 'LOAD_FAST'):
          result += op.argval + '.'
        elif op.opname in ('STORE_NAME', 'STORE_FAST'):
          result = op.argval
          break
        else:
          message = 'expected {LOAD_NAME, LOAD_FAST, STORE_NAME, STORE_FAST}'
          raise ValueError(message, op.opname)

  if not result:
    raise RuntimeError('last frame instruction not found')
  return result
