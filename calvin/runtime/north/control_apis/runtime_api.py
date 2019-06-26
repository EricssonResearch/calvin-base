# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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


import json
from calvin.common import calvinresponse
from calvin.common.calvinlogger import get_logger
from calvin.common.calvin_callback import CalvinCB
from calvin.runtime.south import asynchronous
from .routes import handler, register
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib

_log = get_logger(__name__)

# FIXME: Which ones are needed?

# USED BY: CSWEB, CSCONTROL
# Can't be access controlled, as it is needed to find authorization server
# 
@handler(method="GET", path="/id")
def handle_get_node_id(self, handle, match, data, hdr):
    """
    GET /id
    Get id of this calvin node
    Response status code: OK
    Response: node-id
    """
    self.send_response(handle, json.dumps({'id': self.node.id}))


# USED BY: GUI, CSWEB
@handler(method="GET", path="/capabilities")
def handle_get_node_capabilities(self, handle, match, data, hdr):
    """
    GET /capabilities
    Get capabilities of this calvin node
    Response status code: OK
    Response: list of capabilities
    """
    self.send_response(handle, json.dumps(get_calvinsys().list_capabilities() + get_calvinlib().list_capabilities()))


# USED BY: CSWEB, CSCONTROL
@handler(method="GET", path="/nodes")

def handle_get_nodes(self, handle, match, data, hdr):
    """
    GET /nodes
    List nodes in network (excluding self) known to self
    Response status code: OK
    Response: List of node-ids
    """
    # FIXME: This is not a safe way to get peer node_id's, since it is not using the registry
    self.send_response(handle, json.dumps(self.node.network.list_links()))


# USED BY: CSWEB, CSCONTROL
@handler(method="DELETE", path="/node", optional=["/now", "/migrate", "/clean"])

def handle_quit(self, handle, match, data, hdr):
    """
    DELETE /node{/now|/migrate|/clean}
    Stop (this) calvin node
     now: stop the runtime without handling actors on the runtime
     migrate: migrate any actors before stopping the runtime
     clean: stop & destroy all actors before stopping [default]
    Response status code: ACCEPTED
    Response: none
    """

    if match.group(1) == "now":
        stop_method = self.node.stop
    elif match.group(1) == "migrate":
        stop_method = self.node.stop_with_migration
    else: # Clean up
        stop_method = self.node.stop_with_cleanup

    asynchronous.DelayedCall(.2, stop_method)
    self.send_response(handle, None, status=calvinresponse.ACCEPTED)


# DEPRECATED: What is this supposed to do?
@handler(method="OPTIONS", path=r"/{path}")

def handle_options(self, handle, match, data, hdr):
    """
    OPTIONS /url
    Request for information about the communication options available on url
    Response status code: OK
    Response: Available communication options
    """
    self.send_optionsheader(handle, hdr)
