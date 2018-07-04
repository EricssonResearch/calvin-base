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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
import importlib
import os
import sys
import imp

from calvin.utilities import calvinconfig


# Spec
_modules = {'sql': {'sql': 'sql_client'}}

fw_modules = None
__all__ = []

if not fw_modules:
    _dirname = os.path.dirname(__file__)
    fw_modules = os.listdir(_dirname)
    for i, fw_module in enumerate(fw_modules):
        if not os.path.exists(os.path.join(_dirname, fw_module, '__init__.py')):
            del fw_modules[i]

_conf = calvinconfig.get()
fw_path = _conf.get(None, 'framework')

if not fw_path in fw_modules:
    raise Exception("No framework '%s' with that name, avalible ones are '%s'" % (fw_path, fw_modules))


for module, _classes in list(_modules.items()):
    for _name, _module in list(_classes.items()):
        module_obj = importlib.import_module(".{}.{}.{}".format(fw_path, module, _module), package="calvin.runtime.south.plugins.storage")
        globals()[_name] = module_obj
        __all__.append(module_obj)
