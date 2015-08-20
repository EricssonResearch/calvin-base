# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import glob
import importlib

# Remember these imports are only run at the first time the calvinsys is
# used, i.e. at import time!
SYSGROUP = "io"
modules = glob.glob(os.path.dirname(__file__) + "/*.py")
__all__ = [os.path.basename(f)[:-3] for f in modules if not os.path.basename(
    f).startswith('_') and os.path.isfile(f) and os.path.basename(f) != (SYSGROUP + ".py")]
subsys = {}
for m in __all__:
    subsys[m] = importlib.import_module("calvin.calvinsys." + SYSGROUP + "." + m)

# The class is instanciated per Actor


class Io(object):

    """Io is the IO interface to the calvin runtime for the actor
    """

    def __init__(self, actor, node):
        super(Io, self).__init__()
        self._node = node
        for m in __all__:
            subsys[m].register(node, actor, self)
