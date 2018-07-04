# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
import importlib
from calvin.runtime.north.plugins.port.endpoint.common import Endpoint

# Endpoint methods
_MODULES = {'local': ['LocalInEndpoint', 'LocalOutEndpoint'],
            'tunnel':  ['TunnelInEndpoint', 'TunnelOutEndpoint']}
from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


for module, classes in list(_MODULES.items()):
    module_obj = importlib.import_module(name=".{}".format(module), package="calvin.runtime.north.plugins.port.endpoint")
    for class_ in classes:
        globals()[class_] = getattr(module_obj, class_)
