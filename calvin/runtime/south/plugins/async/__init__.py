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

"""
        Abstraction for the diffrent frameworks that can be used by the system.

"""
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import importlib
from calvin.utilities import calvinconfig


# Spec
_MODULES = {'async': ['DelayedCall', 'run_ioloop', 'stop_ioloop'],
            'filedescriptor': ['FD'],
            'pipe': ['Pipe'],
            'defer': [],
            'threads': [],
            'server_connection': ['ServerProtocolFactory', 'LineProtocol', 'RawDataProtocol'],
            'sse_event_source': ['EventSource'],
            'client_connection': ['ClientProtocolFactory'],
            'http_client': ['HTTPClient']}

_FW_MODULES = []
__all__ = []

if not _FW_MODULES:
    DIRNAME = os.path.dirname(__file__)
    DIRS = os.listdir(DIRNAME)
    for i, fw_module in enumerate(DIRS):
        if "impl" in fw_module:
            _FW_MODULES.append(fw_module)

_CONF = calvinconfig.get()
_FW_PATH = _CONF.get(None, 'framework')


def get_framework():
    """
        Get the framework used on the runtime
    """
    return _FW_PATH


def get_frameworks():
    """
        Get all frameworks in the system
    """
    return _FW_MODULES

if _FW_PATH not in _FW_MODULES:
    raise Exception("No framework '%s' with that name, avalible ones are '%s'" % (_FW_PATH, _FW_MODULES))

for module, _classes in list(_MODULES.items()):
    module_obj = importlib.import_module(name=".{}.{}".format(_FW_PATH, module), package="calvin.runtime.south.plugins.async")
    globals()[module] = module_obj
    __all__.append(module_obj)
