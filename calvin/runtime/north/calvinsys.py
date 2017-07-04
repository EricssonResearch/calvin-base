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
_calvinsys = None

def get_calvinsys():
    """ Returns the calvinsys singleton"""
    global _calvinsys
    if _calvinsys is None:
        _calvinsys = CalvinSys()
    return _calvinsys

class CalvinSys(object):

    """
    Handles calvinsys objects.
    """

    def __init__(self):
        self._node = None
        self.capabilities = {}
        self.objects = []

    def init(self, node):
        """
        Get and setup capabilities from config
        """
        self._node = node
        capabilities = _conf.get('calvinsys', 'capabilities') or {}
        blacklist = _conf.get(None, 'capabilities_blacklist') or []
        for capability in blacklist:
            _ = capabilities.pop(capability, None)
        for key, value in capabilities.iteritems():
            module = value['module']
            value['path'] = module
            value['module'] = None
            _log.info("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities

    def open(self, name, actor, **kwargs):
        """
        Open a capability and return corresponding object
        """
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
        obj = pyclass(calvinsys=self, name=name, actor=actor)
        data = dict(capability['attributes'], **kwargs)
        validate(data, obj.init_schema)
        obj.init(**data)
        self.objects.append(obj)
        return obj

    def scheduler_wakeup(self, actor):
        """
        Trigger scheduler
        """
        self._node.sched.trigger_loop(actor_ids=[actor.id])

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

    def remove(self, obj):
        """
        Remove object
        """
        try:
            self.objects.remove(obj)
        except ValueError:
            _log.debug("Object does not exist")
