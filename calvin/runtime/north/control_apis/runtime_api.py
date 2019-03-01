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

from __future__ import absolute_import
import json
from calvin.utilities import calvinresponse
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south.async import async
from .routes import handler, register
from .authentication import authentication_decorator
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib

_log = get_logger(__name__)

# FIXME: Which ones are needed?

# USED BY: CSWEB, CSCONTROL
# Can't be access controlled, as it is needed to find authorization server
# @authentication_decorator
@handler(method="GET", path="/id")
def handle_get_node_id(self, handle, connection, match, data, hdr):
    """
    GET /id
    Get id of this calvin node
    Response status code: OK
    Response: node-id
    """
    self.send_response(handle, connection, json.dumps({'id': self.node.id}))


# USED BY: GUI, CSWEB
@handler(method="GET", path="/capabilities")
def handle_get_node_capabilities(self, handle, connection, match, data, hdr):
    """
    GET /capabilities
    Get capabilities of this calvin node
    Response status code: OK
    Response: list of capabilities
    """
    self.send_response(handle, connection, json.dumps(get_calvinsys().list_capabilities() + get_calvinlib().list_capabilities()))


# USED BY: CSWEB, CSCONTROL
@handler(method="GET", path="/nodes")
@authentication_decorator
def handle_get_nodes(self, handle, connection, match, data, hdr):
    """
    GET /nodes
    List nodes in network (excluding self) known to self
    Response status code: OK
    Response: List of node-ids
    """
    self.send_response(handle, connection, json.dumps(self.node.network.list_links()))


# USED BY: CSWEB, CSCONTROL
@handler(method="DELETE", path="/node", optional=["/now", "/migrate", "/clean"])
@authentication_decorator
def handle_quit(self, handle, connection, match, data, hdr):
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

    async.DelayedCall(.2, stop_method)
    self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)


# DEPRECATED: What is this supposed to do?
@handler(method="OPTIONS", path=r"/{path}")
@authentication_decorator
def handle_options(self, handle, connection, match, data, hdr):
    """
    OPTIONS /url
    Request for information about the communication options available on url
    Response status code: OK
    Response: Available communication options
    """

    response = "HTTP/1.1 200 OK\n"

    # Copy the content of Access-Control-Request-Headers to the response
    if 'access-control-request-headers' in hdr:
        response += "Access-Control-Allow-Headers: " + \
                    hdr['access-control-request-headers'] + "\n"

    response += "Content-Length: 0\n" \
                "Access-Control-Allow-Origin: *\n" \
                "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n" \
                "Content-Type: *\n" \
                "\n\r\n"

    if connection is None:
        msg = {"cmd": "httpresp", "msgid": handle, "header": response, "data": None}
        self.tunnel_client.send(msg)
    else:
        connection.send(response)
