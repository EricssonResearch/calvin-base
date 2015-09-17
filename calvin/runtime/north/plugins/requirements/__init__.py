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

from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)

# FIXME should be read from calvin config
REQ_PLUGIN_PATH = os.path.dirname(__file__)
REQ_PLUGIN_NS = "calvin.runtime.north.plugins.requirements"

# Find python files in plugins/requirements
module_paths = glob.glob(os.path.join(REQ_PLUGIN_PATH, "*.py"))
modules = [os.path.basename(f)[:-3] for f in module_paths if not os.path.basename(
    f).startswith('_') and os.path.isfile(f)]

# Find directories with __init__.py python file
module_paths = glob.glob(os.path.join(REQ_PLUGIN_PATH, "*"))
dirs = [f for f in module_paths if not os.path.basename(f).startswith('_') and os.path.isdir(f)]
modules += [os.path.basename(d) for d in dirs if os.path.isfile(os.path.join(d, "__init__.py"))]

req_operations = {}

for m in modules:
    try:
        req_operations[m] = importlib.import_module(REQ_PLUGIN_NS + "." + m)
    except:
        _log.debug("Could not import requirements rule %s" % (m,), exc_info=True)
        continue
    _log.debug("Imported requirements plugin %s" % (m,))

