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

import os
import glob
import importlib

from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)

CONDITION_CHECKS_PATH = os.path.dirname(__file__)
CONDITION_CHECKS_NS = "calvin.runtime.north.plugins.authorization_checks"

# Find python files in plugins/authorization_checks
module_paths = glob.glob(os.path.join(CONDITION_CHECKS_PATH, "*.py"))
modules = [os.path.basename(f)[:-3] for f in module_paths 
		   if not os.path.basename(f).startswith('_') and os.path.isfile(f)]

authz_plugins = {}

for m in modules:
    try:
        authz_plugins[m] = importlib.import_module(CONDITION_CHECKS_NS + "." + m)
    except:
        _log.debug("Could not import condition check plugin %s" % (m,), exc_info=True)
        continue
    _log.debug("Imported condition check plugin %s" % (m,))

def check_authorization_plugin_list(plugin_list):
    authorization_results = []
    for plugin in plugin_list:
        try:
            authorization_results.append(authz_plugins[plugin["id"]].authorization_check(**plugin["attributes"]))
        except Exception:
            return False
    # At least one of the authorization checks for the plugins must return True.
    return True in authorization_results