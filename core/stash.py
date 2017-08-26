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
"""
This module provides the interface to implement a build-stash server that can
be used to store build artifacts in order to speed up the build in large-scale
enterprises. The #StashBackend is the main interface when dealing with artifact
stashing.
"""

import abc
import typing as t

#: Called to update the progress information during the upload process when
#: using the #StashBuilder.upload() method.
UploadProgress = t.Callable[[str, float], None]


class StashError(Exception):
  pass


class DuplicateStashKeyError(StashError):
  pass


class FileInfo(metaclass=abc.ABCMeta):
  """
  Represents information about a file in a #Stash.
  """

  def __repr__(self):
    typename = type(self).__name__
    return '<{} {!r} ({}b)>'.format(typename, self.name(), self.size())

  @abc.abstractmethod
  def open(self) -> t.BinaryIO:
    """
    Opens the file for reading.
    """

  @abc.abstractmethod
  def size(self) -> int:
    """
    Returns the size of the file in bytes.
    """

  @abc.abstractmethod
  def name(self) -> str:
    """
    Returns the name of the file that is represented by this #FileInfo.
    """


class Stash(metaclass=abc.ABCMeta):
  """
  A #Stash is a container for files that are produced by a build #Action.
  Stashes can not contain nested structures, only files directly. Every stash
  has associated with it the time that it was created, last accessed and the
  time it is supposed to live until it is thrown away, as well as a plain text
  description of how this stash came to be (e.g. hostname of the machine that
  built the objects, possibly the commands and compiler version that produced
  this stash, etc.)

  Stashes can not be modified after they are created.
  """

  @abc.abstractmethod
  def key(self) -> str:
    """
    Returns the key that this stash is associated with. This is usually a SHA1
    hash of the build #Action#s' inputs and outputs filenames (relative to the
    project directory and normalized), the contents of the input files, build
    system version, compiler version, impactful environment variables and
    possibly more. It depends on the actions' implementation.
    """

  @abc.abstractmethod
  def ctime(self) -> int:
    """
    Returns the time that the stash was created, in seconds (in the timezone
    of the #StashBackend).
    """

  @abc.abstractmethod
  def atime(self) -> int:
    """
    Returns the time that the stash was last accessed, in seconds (in the
    timezone of the #StashBackend).
    """

  @abc.abstractmethod
  def ttl(self) -> int:
    """
    Returns the time in seconds that this stash is supposed to live from its
    time of creation.
    """

  @abc.abstractmethod
  def filelist(self) -> t.List[str]:
    """
    Returns a list of filenames that are contained in this stash.
    """

  @abc.abstractmethod
  def fileinfo(self, filename: str) -> FileInfo:
    """
    Returns information about a file in the stash. The *filename* must be the
    same as one of the strings returned by #filelist().

    # Raises
    NoSuchFileError: If the file does not exist in the stash.
    """

  @abc.abstractmethod
  def description(self) -> str:
    """
    Returns the plain-text description of this stash. The contents of this
    text depends on the #Action that generates the stash. It may just be an
    empty string.
    """

  @abc.abstractmethod
  def open(self, filename: str) -> t.BinaryIO:
    """
    Opens a file in the stash for reading. Note that this is the same as using
    the #fileinfo() on the same *filename* and calling #FileInfo.open().

    # Raises
    NoSuchFileError: If the file does not exist.
    """


class StashBuilder(metaclass=abc.ABCMeta):
  """
  This interface allows to build a new #Stash. Once the #__exit__() method is
  called by exiting the #StashBuilder#'s with-context, it shall be uploaded to
  the #StashBackend.
  """

  def __enter__(self) -> 'StashBuilder':
    return self

  @abc.abstractmethod
  def get_key(self) -> str:
    """
    Returns the key for which this stash is built for.
    """

  @abc.abstractmethod
  def set_ttl(self, ttl: int) -> None:
    """
    Sets the time-to-live for the stash that is being created with this
    builder. Some implementations may not support this feature and always
    choose their preferred ttl for a stash.
    """

  @abc.abstractmethod
  def set_description(self, description: str) -> None:
    """
    Set the description of the stash.
    """

  @abc.abstractmethod
  def add(self, filename: str) -> None:
    """
    Add a file to the stash under the specified *filename*. The file will be
    added to the stash directly, with no subdirectory (as stashes do not
    support nested file structures).

    The file might actually be accessed only when #upload() is called.
    """

  @abc.abstractmethod
  def upload(self, progress: t.Optional[UploadProgress]) -> None:
    """
    Upload the stash's information collected with this #StashBuilder to the
    #StashBackend. The stash is not complete unless this method is called.
    Once this method completed successfully, the stash created with this
    builder must be accessible from #StashBackend.find_stash().
    """


class StashBackend(metaclass=abc.ABCMeta):
  """
  The StashBackend represents a database of Stashes that are available to the
  build system to avoid repetitive rebuilds. It provides the ability to find
  a #Stash based on hash that can be computed from a build #Action. If the
  stash exists, the #Action must not be executed, but instead the saved data
  from the #Stash can be used.
  """

  session: 'Session'

  def __init__(self, session):
    self.session = session

  @abc.abstractmethod
  def can_create_new_stashes(self) -> bool:
    """
    Returns #True if this implementation of the #StashBackend interface can
    create new #Stash#es with the #new_stash() function. Some implementations
    may serve stashes as read-only.
    """

  @abc.abstractmethod
  def new_stash(self, key: str) -> StashBuilder:
    """
    Create a new #StashBuilder for the specified *key*. Can only be used when
    #can_create_new_stashes() returns #True. If a stash with the specified
    key already exists, a #DuplicateStashKeyError is raised.
    """

  @abc.abstractmethod
  def find_stash(self, key: str) -> t.Optional[Stash]:
    """
    Finds a #Stash by the specified *key*. If there is no stash for that key,
    #None is returned instead.
    """
