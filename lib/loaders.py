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

api = require('./api')
path = require('./utils/path')
shell = require('./utils/shell')
logger = require('@craftr/logger')
craftr = require('../index')
httputils = require('./utils/httputils')
_archive = require('./utils/archive')

import os


def iter_copyfileobj(sfp, dfp, size=None, chunksize=4096):
  """
  Generator that yields the progress after every chunk has been copied
  from *sfp* to *dfp*. If *size* is not specified, *sfp* will be seeked
  first. The yielded progress is a tuple of ``(bytes_copied, size)``.
  """

  if size is None:
    pos = sfp.tell()
    sfp.seek(os.SEEK_END)
    size = sfp.tell()
    sfp.seek(pos)

  bytes_copied = 0
  while True:
    yield bytes_copied, size
    data = dfp.read(chunksize)
    if not data:
      break
    written = sfp.write(data)
    if written is not None and written != len(data):
      raise IOError('wrote {} of {} bytes'.format(written, len(data)))
    bytes_copied += len(data)


def get_loader_cache(loader_name, module=None):
  """
  Retrieve the cache of a loader by its *loader_name* and *module*. If no
  cache exists, an empty dictionary is returned.
  """

  module = module or craftr.get_current_module_name()
  assert isinstance(module, str)
  loaders = craftr.cache.setdefault('loaders', {})
  module_cache = loaders.setdefault(module, {})
  return module_cache.setdefault(loader_name, {})


def _external_file_download_callback(progress_text, directory, filename, cache, data):
  """
  *Private*. Callback function used in :func:`external_file` when a file
  is downloaded with :func:`httputils.download_file`.

  :param progress_text: The text to display on the progress bar.
  :param directory: The directory passed to :func:`external_file`.
  :param filename: The filename passed to :func:`external_file`.
  :param cache: A dictionary that contains cached information, eventually
      from a previous download.
  :param data: The data passed from :func:`httputils.download_file`.
  """

  is_spinning = data['size'] is None

  # Before the download starts but the request is already made, we can
  # check if the file already exists.
  if data['downloaded'] == 0:
    logger.progress_begin(progress_text, is_spinning)
  elif data['completed']:
    logger.progress_end()
  elif is_spinning:
    # TODO: Convert bytes to human readable
    logger.progress_update(None, data['downloaded'])
  elif not is_spinning:
    # TODO: Convert bytes to human readable
    logger.progress_update(data['downloaded'] / data['size'], data['downloaded'])


class NoExternalFileMatch(Exception):

  def __init__(self, name, urls, excs):
    if len(urls) != len(excs):
      raise ValueError("number of exceptions must match number of urls")
    self.name = name
    self.urls = urls
    self.excs = excs

  def __str__(self):
    urls = ['  - {} ({})'.format(u, e) for (u, e) in zip(self.urls, self.excs)]
    return '\n'.join([self.name] + urls)


def external_file(*urls, name, filename = None, directory = None,
    copy_file_url = False):
  """
  Downloads a file from the first valid URL and saves it into *directory*
  under the specified *filename*.

  :param urls: One or more URLs. Supports ``http://``, ``https://``,
      ``ftp://`` and ``file://`. Note that if a ``file://`` URL is
      specified, the file is not copied to the output filename unless
      *copy_file_url* is True.
  :param filename: The output filename of the downloaded file. Defaults
      to the filename of the downloaded file.
  :param directory: The directory to save the file to. If *filename*
      is a relative path, it will be joined with this directory. Defaults
      to a path in the build directory.
  :param copy_file_url: If True, ``file://`` URLs will be copied instead
      of used as-is.
  :param name: The name of the loader action. This name is used to store
      information in the :attr:`Session.cache` so we can re-use existing
      downloaded data.
  :return: The path to the downloaded file.
  """

  if not directory and not filename:
    directory = path.buildlocal('data')
  cache = get_loader_cache(name)

  # TODO: expand variables of the current module.

  target_filename = None
  exceptions = []
  for url in urls:
    if url == cache.get('download_url'):
      existing_file = cache.get('download_file')
      if existing_file and path.isfile(existing_file):
        return existing_file

    progress_info = 'Downloading {} ...'.format(url)
    if url.startswith('file://'):
      source_file = url[7:]
      if path.isfile(source_file):
        if not copy_file_url:
          return source_file
        if not filename:
          filename = path.basename(source_file)

        # TODO: Use httputils.download_file() for this as well?
        logger.progress_begin(progress_info)
        path.makedirs(directory)
        target_filename = path.join(directory, filename)
        with open(source_file, 'rb') as sfp:
          with open(target_filename, 'wb') as dfp:
            for bytes_copied, size in iter_copyfileobj(sfp, dfp):
              logger.progress_update(float(bytes_copied) / size)
        logger.progress_end()

        # TODO: Copy file permissions
        break
      else:
        exceptions.append(FileNotFoundError(url))
    else:
      progress = lambda data: _external_file_download_callback(
          progress_info, directory, filename, cache, data)

      try:
        target_filename, reused = httputils.download_file(
          url, filename = filename, directory = directory, on_exists = 'skip',
          progress = progress)
      except (httputils.URLError, httputils.HTTPError) as exc:
        exceptions.append(exc)
      else:
        break
      finally:
        logger.progress_end()

  if target_filename:
    cache['download_url'] = url
    cache['download_file'] = target_filename
    return target_filename

  raise NoExternalFileMatch(name, urls, exceptions)


def external_archive(*urls, name, exclude_files = (), directory = None):
  """
  Downloads an archive from the first valid URL and unpacks it into
  *directory*. Archives with a single directory at the root will be
  extracted from one level below, eliminating that single parent
  directory.

  *exclude_files* can be a list of glob patterns that will be matched
  against the arcnames in the archive. Note that to exclude a directory,
  a pattern must match all files in that directory.

  Uses :func:`external_file` to download the archive.

  :param urls: See :func:`external_file`
  :param exclude_files: A list of glob patterns.
  :param directory: The directory to unpack the archive to. Defaults
      to a directory on the build directory derived from the downloaded
      archive filename. If defined and followed by a trailing slash, the
      archive filename will be appended.
  :param name: The name of the loader action. This name is used to store
      information in the :attr:`Session.cache` so we can re-use existing
      downloaded data.
  :return: The path to the top-level directory of the unpacked archive.
  """

  if not directory:
    directory = path.buildlocal('data') + '/'

  archive = external_file(*urls, directory = directory, name = name)
  cache = get_loader_cache(name)  # shared with external_file()

  suffix = _archive.get_opener(archive)[0]
  if path.maybedir(directory):
    filename = path.basename(archive)[:-len(suffix)]
    directory = path.join(directory, filename)

  # Check if we already unpacked it etc.
  if cache.get('archive_source') == archive and \
      cache.get('archive_dir') == directory and \
      path.isdir(directory):
    return directory

  def match_exclude_files(arcname):
    for pattern in exclude_files:
      if fnmatch.fnmatch(arcname, pattern):
        return False
    return True

  def progress(index, count, filename):
    if index == -1:
      logger.progress_begin("Unpacking {} ...".format(path.basename(archive)))
      logger.progress_update(0.0, 'Reading index...')
      return
    progress = index / float(count)
    if index == 0:
      logger.progress_end()
      logger.progress_begin(None, False)
    elif index == (count - 1):
      logger.progress_end()
    else:
      logger.progress_update(progress, '{} / {}'.format(index, count))

  _archive.extract(archive, directory, suffix = suffix,
    unpack_single_dir = True, check_extract_file = match_exclude_files,
    progress_callback = progress)

  cache['archive_source'] = archive
  cache['archive_dir'] = directory
  return directory


class PkgConfigError(Exception):
  pass


def pkg_config(pkg_name, static = False):
  """
  If available, this function uses ``pkg-config`` to extract flags for
  compiling and linking with the package specified with *pkg_name*. If
  ``pkg-config`` is not available or the it can not find the package,
  :class:`PkgConfigError` is raised.
  """

  command = ['pkg-config', pkg_name, '--cflags', '--libs']
  if static:
    command.append('--static')

  try:
    flags = shell.pipe(command, check = True).stdout
  except FileNotFoundError as exc:
    raise PkgConfigError('pkg-config is not available ({})'.format(exc))
  except shell.CalledProcessError as exc:
    raise PkgConfigError('{} not installed on this system\n\n{}'.format(
        pkg_name, exc.stderr or exc.stdout))

  # Parse the flags.
  result = api.Framework('pkg-config:{}'.format(pkg_name),
      include = [], defines = [], libs = [], libpath = [],
      compile_additional_flags = [], link_additional_flags = [])
  for flag in shell.split(flags):
    if flag.startswith('-I'):
      result['include'].append(flag[2:])
    elif flag.startswith('-D'):
      result['defines'].append(flag[2:])
    elif flag.startswith('-l'):
      result['libs'].append(flag[2:])
    elif flag.startswith('-L'):
      result['libpath'].append(flag[2:])
    elif flag.startswith('-Wl,'):
      result['link_additional_flags'].append(flag[4:])
    else:
      result['compile_additional_flags'].append(flag)

  return result


pkg_config.Error = PkgConfigError
