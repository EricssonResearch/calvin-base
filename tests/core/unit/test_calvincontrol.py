# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2018 Ericsson AB
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


import uuid

import pytest
from unittest.mock import Mock, patch

from calvin.runtime.north.calvincontrol import CalvinControl


def calvincontrol():
    control = CalvinControl()
    control.send_response = Mock()
    control.send_response = Mock()
    control.node = Mock()
    control.node.quitting = False
    return control

@pytest.fixture(scope="module", params=["prefixed", "non-prefixed"])
def _uuids(request):
    if request.param == "prefixed":
        return {
            "trace_id": str(uuid.uuid4()),
            "app_id": str(uuid.uuid4()),
            "port_id": str(uuid.uuid4()),
            "node_id": str(uuid.uuid4()),
            "actor_id": str(uuid.uuid4())
        }
    elif request.param == "non-prefixed":
        return {
            "trace_id": str(uuid.uuid4()),
            "app_id": str(uuid.uuid4()),
            "port_id": str(uuid.uuid4()),
            "node_id": str(uuid.uuid4()),
            "actor_id": str(uuid.uuid4())
        }


@pytest.mark.parametrize("url, match, handler", [
    ("POST /log HTTP/1", None, "handle_post_log"),
    ("DELETE /log/{trace_id} HTTP/1", ["trace_id"], "handle_delete_log"),
    ("GET /log/{trace_id} HTTP/1", ["trace_id"], "handle_get_log"),
    ("GET /id HTTP/1", None, "handle_get_node_id"),
    ("GET /nodes HTTP/1", None, "handle_get_nodes"),
    ("GET /node/{node_id} HTTP/1", ["node_id"], "handle_get_node"),
    ("GET /applications HTTP/1", None, "handle_get_applications"),
    ("GET /application/{app_id} HTTP/1", ["app_id"], "handle_get_application"),
    ("DELETE /application/{app_id} HTTP/1", ["app_id"], "handle_del_application"),
    ("GET /actors HTTP/1", None, "handle_get_actors"),
    ("GET /actor/{actor_id} HTTP/1", ["actor_id"], "handle_get_actor"),
    ("GET /actor/{actor_id}/report HTTP/1", ["actor_id"], "handle_get_actor_report"),
    ("POST /actor/{actor_id}/report HTTP/1", ["actor_id"], "handle_post_actor_report"),
    ("POST /actor/{actor_id}/migrate HTTP/1", ["actor_id"], "handle_actor_migrate"),
    ("GET /actor/{actor_id}/port/{port_id} HTTP/1", ["actor_id", "port_id"], "handle_get_port"),
    ("GET /actor/{actor_id}/port/{port_id}/state HTTP/1", ["actor_id", "port_id"], "handle_get_port_state"),
    ("POST /deploy HTTP/1", None, "handle_deploy"),
    ("POST /application/{app_id}/migrate HTTP/1", ["app_id"], "handle_post_application_migrate"),
    ("DELETE /node HTTP/1", None, "handle_quit"),
    ("DELETE /node/migrate HTTP/1", ["/migrate"], "handle_quit"),
    ("DELETE /node/now HTTP/1", ["/now"], "handle_quit"),
    ("DELETE /node/clean HTTP/1", ["/clean"], "handle_quit"),
    ("GET /index/abc123 HTTP/1", ["abc123", None, None], "handle_get_index"),
    ("GET /index/abc123?root_prefix_level=3 HTTP/1", ["abc123", "?root_prefix_level=3", "3"], "handle_get_index"),
    ("OPTIONS /abc123 HTTP/1", None, "handle_options"),
    ("POST /node/resource/cpu_avail HTTP/1", ["cpu_avail"], "handle_resource_avail"),
    ("POST /node/resource/mem_avail HTTP/1", ["mem_avail"], "handle_resource_avail")
])

def test_routes_correctly(url, match, handler, _uuids):
    control = CalvinControl(node=Mock(), uri="http://localhost:5101")
    handler_func, mo = control._handler_for_route(url.format(**_uuids))
    assert handler_func is not None
    assert handler_func.__name__ == handler
    assert mo is not None
    if match is not None:
        # If any of the 'match'es are in _uuids we assume they should be uuids
        match = [_uuids.get(m, m) for m in match]
        assert list(mo.groups()) == match

def test_send_response():
    control = CalvinControl(node=Mock(), uri="http://localhost:5101")
    control.start()
    handle = 'foo'
    connection = Mock()
    connection.connection_lost = False
    data = {'value': 1}
    status = 200

    control.server.connection_map = {handle:connection}
    control.send_response(handle, data, status)
    connection.send.assert_called()
    callseq = ['send', 'send', 'close']
    assert len(connection.method_calls) == len(callseq)
    for index, call_ in enumerate(connection.method_calls):
        name, args, kwargs = call_
        # print(name, args, kwargs)
        assert name == callseq[index]
    assert handle not in control.server.connection_map
    control.stop()


def test_send_streamheader():
    control = CalvinControl(node=Mock(), uri="http://localhost:5101")
    control.start()
    handle = 'foo'
    connection = Mock()
    connection.connection_lost = False
    data = {'value': 1}
    status = 200

    control.server.connection_map = {handle:connection}
    control.send_streamheader(handle)
    connection.send.assert_called()
    callseq = ['send']
    print(connection.method_calls)
    assert len(connection.method_calls) == len(callseq)
    for index, call_ in enumerate(connection.method_calls):
        name, args, kwargs = call_
        # print(name, args, kwargs)
        assert name == callseq[index]
    control.stop()
