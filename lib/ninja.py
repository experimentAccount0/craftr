# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import errno
import io
import os
import re
import requests
import subprocess
import sys
import zipfile


def get_version():
  """
  Retrieves the version of Ninja if it is installed, or returns None if
  Ninja could not be found.
  """

  try:
    output = subprocess.getoutput(['ninja', '--version']).strip()
  except OSError as exc:
    return None
  if not re.match('\d\.\d+\.\d+$', output):
    return None
  return output


def interactive_install():
  # Determine the platform name that is used in the Ninja download's filename.
  if sys.platform.startswith('win'):
    exe = 'ninja.exe'
    platform = 'win'
  elif sys.platform.startswith('darwin'):
    exe = 'ninja'
    platform = 'mac'
  elif sys.platform.startswith('linux'):
    exe = 'ninja'
    platform = 'linux'
  else:
    raise EnvironmentError('unsupported platform: "{}"'.format(sys.platform))

  # Retrieve releases sorted by version.
  def sort_key(release):
    if release['tag_name'].startswith('v'):
      return release['tag_name'].split('.')
    return ['999']
  releases = requests.get('https://api.github.com/repos/ninja-build/ninja/releases').json()
  releases.sort(key=sort_key, reverse=True)

  # Find a release that has a download for our platform.
  for release in releases:
    for asset in release['assets']:
      if asset['name'].endswith('-' + platform + '.zip'):
        break
    else:
      continue
    break
  else:
    print('Unable to find binary download matching platform "{}".'
      .format(platform))
    return False

  print('Found "{}" from release "{}".'.format(asset['name'], release['tag_name']))
  print('Where do you want to install it to?')

  # Ask for an installation directory.
  paths = os.getenv('PATH', '').split(os.pathsep)
  paths = [p for p in paths if os.access(p, os.W_OK)]
  for i, p in enumerate(paths):
    print('  [{:02d}]: {}'.format(i+1, p))

  print('You can also enter the installation path directly.')
  value = input('> ').strip()
  try:
    index = int(value) - 1
    if index < 0 or index >= len(paths):
      print('The specified value "{}" is out of range.'.format(index))
      return
    directory = paths[index]
  except ValueError:
    directory = value

  if not os.path.isdir(directory):
    print('The directory "{}" does not exist. Are you sure you want to')
    print('install Ninja {} into this directory?'.format(release['tag_name']))
    response = input('> [Y/n] ').strip().lower() or 'yes'
    if response not in ('y', 'yes'):
      print('Aborted.')
      return False

  # Make sure the directory exists.
  try:
    os.makedirs(directory)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

  url = asset['browser_download_url']
  print('Downloading "{}" ...'.format(url))
  archive = zipfile.ZipFile(io.BytesIO(requests.get(url).content))

  print('Extracting "{}" archive to "{}" ...'.format(exe, directory))
  archive.extract(exe, directory)

  print('Ninja {} successfully installed to "{}".'.format(release['tag_name'], directory))
  return True
