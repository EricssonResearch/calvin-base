# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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

import importlib
from jsonschema import validate

from calvin.utilities import calvinconfig
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

class calvinsys(object):

    """
    Handles calvinsys objects.
    """

    def __init__(self, node):
        self._node = node
        self.capabilities = {}
        self.objects = []
        capabilities = _conf.get('calvinsys', 'capabilities') or []
        blacklist = _conf.get(None, 'capabilities_blacklist') or []

        for capability in capabilities:
            if capability['name'] not in blacklist:
                self.capabilities[capability['name']] = {'name': capability['name'], 'path': capability['module'], 'attributes': capability['attributes'], 'module': None}
                _log.info("Capability '%s' registered with module '%s'" % (capability['name'], capability['module']))

    def open(self, name, **kwargs):
        capability = self.capabilities.get(name, None)
        if capability is None:
            raise Exception("No such capability '%s'", name)
        pymodule = capability.get('module', None)
        if pymodule is None:
            pymodule = importlib.import_module('calvin.runtime.south.calvinsys.' + capability['path'])
            if pymodule is None:
                raise Exception("Failed to import module '%s'" % name)
            capability['module'] = pymodule
        class_name = capability["path"].rsplit(".", 1)
        pyclass = getattr(pymodule, class_name[1])
        if not pyclass:
            raise Exception("No entry %s in %s" % (name, capability['path']))

        obj = pyclass(calvinsys=self, name=name)
        data = dict(capability['attributes'], **kwargs)
        validate(data, obj.init_schema)
        obj.init(**data)
        self.objects.append(obj)
        return obj

    def validate_data(self, data, schema):
        try:
            validate(data, schema)
            return True
        except:
            return False

    def can_write(self, obj):
        data = obj.can_write()
        if self.validate_data(data, obj.can_write_schema):
            return data
        else:
            _log.error("Calvinsys object '%s' has no schema for '%s'" % (obj.name, data))

    def write(self, obj, data):
        if self.validate_data(data, obj.write_schema):
            obj.write(data)
        else:
            _log.error("Calvinsys object '%s' has no schema for '%s'" % (obj.name, data))

    def can_read(self, obj):
        data = obj.can_read()
        if self.validate_data(data, obj.can_read_schema):
            return data
        else:
            _log.error("Calvinsys object '%s' has no schema for '%s'" % (obj.name, data))

    def read(self, obj):
        data = obj.read()
        if self.validate_data(data, obj.read_schema):
            return data
        else:
            _log.error("Calvinsys object '%s' has no schema for '%s'" % (obj.name, data))

    def close(self, obj):
        obj.close()
        self.objects.remove(obj)

    def scheduler_wakeup(self):
        self._node.sched.trigger_loop()

    def has_capability(self, requirement):
        """
        Returns True if "requirement" is satisfied in this system,
        otherwise False.
        """
        return requirement in self.capabilities

    def list_capabilities(self):
        """
        Returns list of requirements this system satisfies
        """
        return self.capabilities.keys()

    def get_node(self):
        return self._node
