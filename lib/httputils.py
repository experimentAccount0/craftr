# Copyright (c) 2017 Niklas Rosenstein
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

argschema = require('./argschema')
path = require('./path')

from urllib.error import URLError, HTTPError
import cgi
import urllib.request


class UserInterrupt(Exception):
  """
  An exception that represents the intended abortion of an operation.
  """


def download_file(url, filename=None, file=None, directory=None,
    on_exists='rename', progress=None, chunksize=4096, urlopen_kwargs=None):
  """
  Download a file from a URL to one of the following destinations:

  :param filename: A filename to write the downloaded file to.
  :param file: A file-like object.
  :param directory: A directory. The filename will be automatically
    determined from the ``Content-Disposition`` header received from
    the server or the last path elemnet in the URL.

  Additional parameters for the *directory* parameter:

  :param on_exists: The operation to perform when the file already exists.
    Available modes are ``rename``, ``overwrite`` and ``skip``.

  Additional parameters:

  :param progress: A callable that accepts a single parameter that is a
    dictionary with information about the progress of the download. The
    dictionary provides the keys ``size``,  ``downloaded`` and ``response``.
    If the callable returns :const:`False` (specifically the value False), the
    download will be aborted and a :class:`UserInterrupt` will be raised.
  :param urlopen_kwargs: A dictionary with additional keyword arguments
    for :func:`urllib.request.urlopen`.

  Raise and return:

  :raise HTTPError: Can be raised by :func:`urllib.request.urlopen`.
  :raise URLError: Can be raised by :func:`urllib.request.urlopen`.
  :raise UserInterrupt: If the *progress* returned :const:`False`.
  :return: If the download mode is *directory*, the name of the downloaded
    file will be returned and False if the file was newly downloaded, True
    if the download was skipped because the file already existed.
    Otherwise, the number of bytes downloaded will be returned.
  """

  argschema.validate('on_exists', on_exists, {'enum': ['rename', 'overwrite', 'skip']})

  if sum(map(bool, [filename, file, directory])) != 1:
    raise ValueError('exactly one of filename, file or directory must be specifed')

  response = urllib.request.urlopen(url, **(urlopen_kwargs or {}))

  if directory:
    try:
      filename = parse_content_disposition(
        response.headers.get('Content-Disposition', ''))
    except ValueError:
      filename = url.split('/')[-1]
    filename = path.join(directory, filename)
    path.makedirs(directory)

    if path.exists(filename):
      if on_exists == 'skip':
        return filename, True
      elif on_exists == 'rename':
        index = 0
        while True:
          new_filename = filename + '_{:0>4}'.format(index)
          if not path.exists(new_filename):
            filename = new_filename
            break
          index += 1
      elif on_exists != 'overwrite':
        raise RuntimeError

  try:
    size = int(response.headers.get('Content-Length', ''))
  except ValueError:
    size = None

  progress_info = {'response': response, 'size': size, 'downloaded': 0,
    'completed': False, 'filename': filename, 'url': url}
  if progress and progress(progress_info) is False:
    raise UserInterrupt

  def copy_to_file(fp):
    while True:
      data = response.read(chunksize)
      if not data:
        break
      progress_info['downloaded'] += len(data)
      fp.write(data)
      if progress and progress(progress_info) is False:
        raise UserInterrupt
    progress_info['completed'] = True
    if progress and progress(progress_info) is False:
      raise UserInterrupt

  if filename:
    path.makedirs(path.dirname(filename))
    try:
      with open(filename, 'wb') as fp:
        copy_to_file(fp)
    except BaseException:
      # Delete the file if it could not be downloaded successfully.
      path.remove(filename, silent=True)
      raise
  elif file:
    copy_to_file(file)

  return filename, False


def parse_content_disposition(value):
  """
  Parse the ``Content-Disposition`` header.
  """

  value, param = cgi.parse_header(value)
  if value != 'attachment':
    raise ValueError('not an attachment header')
  if 'filename' not in param:
    raise ValueError('no filename parmaeter')
  return param['filename']
