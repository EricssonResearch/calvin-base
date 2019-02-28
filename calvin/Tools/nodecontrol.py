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

import time
from calvin.runtime.north import calvin_node
from calvin.utilities import storage_node
from calvin.requests.request_handler import RequestHandler


def node_control(control_uri, barrier=True, request_handler=None):
    class NodeControl(object):

        def __init__(self, control_uri, barrier):
            super(NodeControl, self).__init__()
            self._id = None
            self._uris = None
            self.control_uri = control_uri
            self.request_handler = request_handler or RequestHandler()
            delay = 0.1
            # When barrier ordered make sure we can contact the runtime
            if barrier:
                success = False
                # Try 20 times waiting for control API to be up and running
                for i in range(20):
                    try:
                        self._id = self.request_handler.get_node_id(self)
                        success = True
                        break
                    except Exception:
                        time.sleep(delay)
                        delay = 2*delay if delay < 1.0 else 1.0
                assert success

        @property
        def id(self):
            if self._id is None:
                self._id = self.request_handler.get_node_id(self)
            return self._id

        @property
        def uris(self):
            if self._uris is None:
                self._uris = self.request_handler.get_node(self, self.id)["uris"]
            return self._uris
        
    return NodeControl(control_uri, barrier=barrier)


def dispatch_node(uris, control_uri, trace=False, attributes=None, barrier=True):
    """ Dispatch calvin runtime in new process.
        uris: list of uris for rt2rt comm
        control_uri: uri to control the rt
        trace: True/False
        attributes: dictionary according to documentation in AttributeResolver
        barrier: when True wait until managed to obtain the id of the runtime
    """
    p = calvin_node.start_node(uris, control_uri, trace, attributes)
    return node_control(control_uri, barrier=barrier), p


def start_node(uri, control_uri, trace=False, attributes=None):
    if trace:
        calvin_node.create_tracing_node(uri, control_uri, trace, attributes)
    else:
        calvin_node.create_node(uri, control_uri, attributes)


def dispatch_storage_node(uri, control_uri, trace=False, attributes=None):
    p = storage_node.start_node(uri, control_uri, trace, attributes)
    return node_control(control_uri), p


def start_storage_node(uri, control_uri, trace=False, attributes=None):
    if trace:
        storage_node.create_tracing_node(uri, control_uri, trace, attributes)
    else:
        storage_node.create_node(uri, control_uri, attributes)
