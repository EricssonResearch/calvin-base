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
    Tests for frameworks
"""

import inspect

from calvin.utilities import calvinlogger
from calvin.runtime.south.plugins.async import get_frameworks
from calvin.runtime.south.plugins.async import twistedimpl
from twisted.internet import defer, threads
import pytest

pytestmark = pytest.mark.unittest


_LOG = calvinlogger.get_logger(__name__)

FRAMEWORKS = get_frameworks()
REFERENCE_FW = "twistedimpl"

# TODO: move this to __init__.py of async instead of _modueles ?
MODULES = {'defer': {'Deferred':         {'type': 'class', 'comp': defer.Deferred},
                     'DeferredList':     {'type': 'class', 'comp': defer.DeferredList},
                     'inline_callbacks': {'type': 'function', 'comp': defer.inlineCallbacks},
                     'maybe_deferred':   {'type': 'function', 'comp': defer.maybeDeferred}},
           'async': {'DelayedCall': {'type': 'class', 'comp': twistedimpl.async.DelayedCall},
                     'run_ioloop':  {'type': 'class', 'comp': twistedimpl.async.run_ioloop},
                     'stop_ioloop': {'type': 'class', 'comp': twistedimpl.async.stop_ioloop}},
           'server_connection': {'ServerProtocolFactory': {'type': 'class', 'comp': twistedimpl.server_connection.ServerProtocolFactory},
                                 'LineProtocol': {'type': 'class', 'comp': twistedimpl.server_connection.LineProtocol},
                                 'RawDataProtocol': {'type': 'class', 'comp': twistedimpl.server_connection.LineProtocol}},
           'threads': {'defer_to_thread': {'type': 'function', 'comp': threads.deferToThread},
                       'call_multiple_in_thread': {'type': 'function', 'comp': threads.callMultipleInThread}},
           'filedescriptor': {'FD': {'type': 'class', 'comp': twistedimpl.filedescriptor.FD}}}


def function_check(func1, func2):
    """
        Function param tester
    """
    func1_args = inspect.getargspec(func1)
    func2_args = inspect.getargspec(func2)
    return func1_args == func2_args


class TestFrameworks(object):
    """
        Testign frameworks implemented
    """
    def test_api_exists(self, monkeypatch):
        """
                Just test that all fw have all the API specified.
        """
        for framework in FRAMEWORKS:
            for module, items in MODULES.items():
                module_obj = __import__("calvin.runtime.south.plugins.async.%s.%s" % (framework, module),
                                        globals=globals(), fromlist=[''])
                for item, info in items.items():
                    # Check for existans
                    item_obj = getattr(module_obj, item, None)
                    comp_obj = info['comp']

                    assert item_obj
                    assert type(item_obj) == type(comp_obj)

                    if info['type'] == 'class':
                        # Loop and check for attr and functions
                        # TODO: check for classes in classes ?!?
                        for item_name in dir(item_obj):
                            if not item_name.startswith("_"):
                                a_obj = getattr(item_obj, item_name)
                                c_obj = getattr(comp_obj, item_name, None)
                                if callable(a_obj):
                                    assert function_check(a_obj, c_obj)
                                else:
                                    assert type(a_obj) == type(c_obj)
                    elif info['type'] == 'function':
                        # check name and params
                        assert function_check(item_obj, comp_obj)
