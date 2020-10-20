"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import os

from reegis.config import *

_loaded = False
if not _loaded:
    init(paths=[os.path.dirname(__file__)])
    _loaded = True
