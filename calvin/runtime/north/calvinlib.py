# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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
_calvinlib = None

TESTING=False

def get_calvinlib():
    """ Returns the calvinlib singleton"""
    global _calvinlib
    global TESTING
    if _calvinlib is None and TESTING:
        _calvinlib = MockCalvinLib()

    if _calvinlib is None:
        _calvinlib = CalvinLib()
    return _calvinlib


class CalvinLib(object):

    """
    Handles calvinlib objects.
    """

    def __init__(self):
        self.capabilities = {}
        self.objects = []

    def init(self):
        """
        Get and setup capabilities from config
        """
        capabilities = _conf.get('calvinlib', 'capabilities') or {}
        blacklist = _conf.get(None, 'capabilities_blacklist') or []
        for capability in blacklist:
            capabilities.pop(capability, None)
        for key, value in capabilities.iteritems():
            module = value['module']
            value['path'] = module
            value['module'] = None
            _log.info("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities


    def use(self, name, **kwargs):
        """
        Open a capability and return corresponding object
        """
        capability = self.capabilities.get(name, None)
        if capability is None:
            raise Exception("No such capability '%s'", name)
        pymodule = capability.get('module', None)
        if pymodule is None:
            pymodule = importlib.import_module('calvin.runtime.south.calvinlib.' + capability['path'])
            if pymodule is None:
                raise Exception("Failed to import module '%s'" % name)
            capability['module'] = pymodule
        class_name = capability["path"].rsplit(".", 1)
        pyclass = getattr(pymodule, class_name[1])
        if not pyclass:
            raise Exception("No entry %s in %s" % (name, capability['path']))
        obj = pyclass(calvinlib=self, name=name)
        if capability.get('attributes'):
            data = dict(capability['attributes'], **kwargs)
            validate(data, obj.init_schema)
            obj.init(**data)
        else :
            obj.init()
        self.objects.append(obj)
        return obj


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

class MockCalvinLib(CalvinLib):

    def init(self, capabilities):
        """
        setup capabilities from config
        """
        for key, value in capabilities.iteritems():
            module = value['module']
            value['path'] = module
            value['module'] = None
            _log.info("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities
