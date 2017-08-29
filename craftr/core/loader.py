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

import nodepy
import os
import weakref
import {BuildContext} from './context'


class LoaderSupport(nodepy.FilesystemLoaderSupport):

  def __init__(self, session):
    self.__session = weakref.ref(session)

  @property
  def session(self):
    return self.__session()

  def new_module(self, **kwargs):
    package = kwargs.get('package')
    if package:
      cell = self.session.get_or_create_cell(package.json['name'],
        package.json.get('version', '1.0.0'), package.directory)
    else:
      cell = self.session.get_main_cell()
    module = CraftrModule(cell, **kwargs)
    module.extensions.append('!require-import-syntax')
    return module

  def suggest_try_files(self, filename):
    return [os.path.join(filename, 'Craftrfile.py')]

  def can_load(self, filename):
    return os.path.basename(filename) == 'Craftrfile.py'

  def get_loader(self, filename, request):
    return nodepy.PythonLoader(filename, python_module_class=self.new_module)


class CraftrModule(nodepy.PythonModule):

  def __init__(self, cell, *args, **kwargs):
    self.__cell = weakref.ref(cell)
    self.build_context = BuildContext(cell)
    super().__init__(*args, **kwargs)

  @property
  def cell(self):
    return self.__cell()


def get_current_module(frame=None):
  for module in reversed(require.context.current_modules):
    if isinstance(module, CraftrModule):
      return module
  raise RuntimeError('no Craftr module in the stack.')
