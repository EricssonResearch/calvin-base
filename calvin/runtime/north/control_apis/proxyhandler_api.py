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
from calvin.requests import calvinresponse
from routes import handler
from calvin.runtime.north.proxyhandler import ProxyHandler
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

@handler(method="GET", path="/proxy/{node_id}/capabilities")
def handle_get_proxy_capabilities(self, handle, connection, match, data, hdr):
    """
    GET /proxy/{node-id}/capabilities
    Get capabilities from proxy peer {node-id}
    Response status code: Capabilities
    """
    try:
        data = self.node.proxy_handler.get_capabilities(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_proxy_capabilities")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection,
            json.dumps(data) if status == calvinresponse.OK else None, status=status)

@handler(method="DELETE", path="/proxy/{node_id}", optional=["/now", "/migrate", "/clean"])
def handle_delete_proxy(self, handle, connection, match, data, hdr):
    """
    DELETE /proxy/{node-id}/{/now|/migrate|/clean}
    Stop (this) calvin node
     now: stop the runtime without handling actors on the runtime
     migrate: migrate any actors before stopping the runtime
     clean: stop & destroy all actors before stopping [default]
    Response status code: ACCEPTED
    Response: none
    """
    try:
        self.node.proxy_handler.destroy(match.group(1), match.group(2))
        status = calvinresponse.OK
    except Exception as e:
        _log.exception("Failed to destroy peer")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status=status)
