<img src=".assets/logo.png" align="right">

# The Craftr build system (3.x)

[![Travis CI: dev/craftr-3.x](https://travis-ci.org/craftr-build/craftr.svg?branch=dev%2Fcraftr-3.x)](https://travis-ci.org/craftr-build/craftr/branches)
[![Build status](https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik/branch/dev/craftr-3.x?svg=true)](https://ci.appveyor.com/project/NiklasRosenstein/craftr/branch/dev/craftr-3.x)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

### Requirements

* Python 3.6+
* [Node.py](https://nodepy.org) 0.0.22+

### Installation Steps

Craftr is supposed to be installed on a per-project basis. Before you can
install Craftr however, you will need Node.py and its package manager *nppm*.

    $ pip3.6 install --user node.py -v
    $ nppm version
    nppm-0.0.22 (on Node.py-0.0.22 [cpython 3.6.2 64-bit])

Inside your project, it is recommended you create a `package.json` to keep
track of Node.py dependencies. After that, you can install Craftr into your
project.

    $ nppm init
    ...
    $ nppm install --save-dev git+https://github.com/craftr-build/craftr.git@dev/craftr-3.x

### Compile Python from Source (Linux)

Some Linux distributions don't yet offer Python 3.6 in their package
repositories. To compile Python from source, follow these steps:

    $ wget https://www.python.org/ftp/python/3.6.2/Python-3.6.2.tgz
    $ tar -xvf Python-3.6.2.tgz
    $ cd Python-3.6.2
    $ sudo apt-get install build-essential libncursesw5-dev libreadline5-dev \
      libssl-dev libgdbm-dev libc6-dev libsqlite3-dev libbz2-dev liblzma-dev
    $ ./configure --enable-optimizations
    $ make && sudo make install
