# Copyright (c) 2017  Niklas Rosenstein
# All rights reserved.

import logging

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('==> %(message)s'))
logger = logging.Logger('craftr')
logger.addHandler(handler)

exports = logger
