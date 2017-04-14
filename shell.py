# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import os
import shlex

class safe(object):

  def __init__(self, text):
    self.text = text

  def __repr__(self):
    return '<shell.safe({1r})>'.format(self.text)

  def __str__(self):
    return str(self.text)

def split(s):
  """
  Enhanced implementation of #shlex.split().
  """

  result = shlex.split(s, posix=(os.name != 'nt'))
  if os.name == 'nt':
    # With posix=False, shlex.split() will not interpret \ as the
    # escape character (which is what we need on windows), but it
    # will also not eliminate quotes, which is what we need to do
    # here now.
    quotes = '\"\''
    result = [x[1:-1] if (x and x[0] in quotes and x[-1] in quotes) else x for x in result]
  return result

def quote(s, for_ninja=False):
  """
  Enhanced implementation of #shlex.quote() as it generates single-quotes
  on Windows which can lead to problems.
  """

  if isinstance(s, safe):
    return str(s)
  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
  else:
    s = shlex.quote(s)
  if for_ninja:
    # Fix escaped $ variables on Unix, see issue craftr-build/craftr#30
    s = re.sub(r"'(\$\w+)'", r'\1', s)
  return s

def join(command):
  return ' '.join(map(quote, command))
