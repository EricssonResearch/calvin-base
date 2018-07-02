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

import pytest
from mock import Mock, patch

from calvin.runtime.north.calvincontrol import get_calvincontrol, CalvinControl
from calvin.utilities import calvinuuid
from calvin.runtime.north.control_apis.routes import path_regex

pytestmark = pytest.mark.unittest


def calvincontrol():
    control = CalvinControl()
    control.send_response = Mock()
    control.send_response = Mock()
    control.node = Mock()
    control.node.quitting = False
    return control

@pytest.fixture(scope="module", params=["prefixed", "non-prefixed"])
def uuids(request):
    if request.param == "prefixed":
        return {
            "trace_id": calvinuuid.uuid("TRACE"),
            "app_id": calvinuuid.uuid("APP"),
            "port_id": calvinuuid.uuid("PORT"),
            "node_id": calvinuuid.uuid("NODE"),
            "actor_id": calvinuuid.uuid("ACTOR")
        }
    elif request.param == "non-prefixed":
        return {
            "trace_id": calvinuuid.uuid(""),
            "app_id": calvinuuid.uuid(""),
            "port_id": calvinuuid.uuid(""),
            "node_id": calvinuuid.uuid(""),
            "actor_id": calvinuuid.uuid("")
        }


def test_get_calvincontrol_returns_xxx():
    control = get_calvincontrol()
    assert control == get_calvincontrol()

@pytest.mark.parametrize("url, match, handler", [
    ("GET /actor_doc HTTP/1", None, "handle_get_actor_doc"),
    ("POST /log HTTP/1", None, "handle_post_log"),
    ("DELETE /log/{trace_id} HTTP/1", ["trace_id"], "handle_delete_log"),
    ("GET /log/{trace_id} HTTP/1", ["trace_id"], "handle_get_log"),
    ("GET /id HTTP/1", None, "handle_get_node_id"),
    ("GET /nodes HTTP/1", None, "handle_get_nodes"),
    ("GET /node/{node_id} HTTP/1", ["node_id"], "handle_get_node"),
    ("POST /peer_setup HTTP/1", None, "handle_peer_setup"),
    ("GET /applications HTTP/1", None, "handle_get_applications"),
    ("GET /application/{app_id} HTTP/1", ["app_id"], "handle_get_application"),
    ("DELETE /application/{app_id} HTTP/1", ["app_id"], "handle_del_application"),
    ("POST /actor HTTP/1", None, "handle_new_actor"),
    ("GET /actors HTTP/1", None, "handle_get_actors"),
    ("GET /actor/{actor_id} HTTP/1", ["actor_id"], "handle_get_actor"),
    ("DELETE /actor/{actor_id} HTTP/1", ["actor_id"], "handle_del_actor"),
    ("GET /actor/{actor_id}/report HTTP/1", ["actor_id"], "handle_get_actor_report"),
    ("POST /actor/{actor_id}/report HTTP/1", ["actor_id"], "handle_post_actor_report"),
    ("POST /actor/{actor_id}/migrate HTTP/1", ["actor_id"], "handle_actor_migrate"),
    ("POST /actor/{actor_id}/disable HTTP/1", ["actor_id"], "handle_actor_disable"),
    ("GET /actor/{actor_id}/port/{port_id} HTTP/1", ["actor_id", "port_id"], "handle_get_port"),
    ("GET /actor/{actor_id}/port/{port_id}/state HTTP/1", ["actor_id", "port_id"], "handle_get_port_state"),
    ("POST /connect HTTP/1", None, "handle_connect"),
    ("POST /set_port_property HTTP/1", None, "handle_set_port_property"),
    ("POST /deploy HTTP/1", None, "handle_deploy"),
    ("POST /application/{app_id}/migrate HTTP/1", ["app_id"], "handle_post_application_migrate"),
    ("POST /disconnect HTTP/1", None, "handle_disconnect"),
    ("DELETE /node HTTP/1", None, "handle_quit"),
    ("DELETE /node/migrate HTTP/1", ["/migrate"], "handle_quit"),
    ("DELETE /node/now HTTP/1", ["/now"], "handle_quit"),
    ("DELETE /node/clean HTTP/1", ["/clean"], "handle_quit"),
    ("POST /index/abc123 HTTP/1", ["abc123"], "handle_post_index"),
    ("DELETE /index/abc123 HTTP/1", ["abc123"], "handle_delete_index"),
    ("GET /index/abc123 HTTP/1", ["abc123", None, None], "handle_get_index"),
    ("GET /index/abc123?root_prefix_level=3 HTTP/1", ["abc123", "?root_prefix_level=3", "3"], "handle_get_index"),
    ("GET /storage/abc123 HTTP/1", ["abc123"], "handle_get_storage"),
    ("POST /storage/abc123 HTTP/1", ["abc123"], "handle_post_storage"),
    ("OPTIONS /abc123 HTTP/1", None, "handle_options"),
    ("POST /node/resource/cpu_avail HTTP/1", ["cpu_avail"], "handle_resource_avail"),
    ("POST /node/resource/mem_avail HTTP/1", ["mem_avail"], "handle_resource_avail")
])

def test_routes_correctly(url, match, handler, uuids):
    control = CalvinControl()
    handler_func, mo = control._handler_for_route(url.format(**uuids))
    assert handler_func is not None
    assert handler_func.__name__ == handler
    assert mo is not None
    if match is not None:
        # If any of the 'match'es are in uuids we assume they should be uuids
        match = [uuids.get(m, m) for m in match]
        assert list(mo.groups()) == match

def test_send_response():
    control = CalvinControl()
    control.tunnel_client = Mock()

    handle = Mock()
    connection = Mock()
    data = {'value': 1}
    status = 200

    control.connections[handle] = connection
    control.send_response(handle, None, data, status)
    assert control.tunnel_client.send.called

    control.connections[handle] = connection
    connection.connection_lost = True
    control.send_response(handle, connection, data, status)
    assert not connection.send.called

    control.connections[handle] = connection
    connection.connection_lost = False
    control.send_response(handle, connection, data, status)
    assert connection.send.called
    connection.send.assert_called_with(data)

    assert handle not in control.connections


def test_send_streamhader():
    control = CalvinControl()
    control.tunnel_client = Mock()

    handle = Mock()
    connection = Mock()

    control.connections[handle] = connection
    control.send_streamheader(handle, None)
    assert control.tunnel_client.send.called

    control.connections[handle] = connection
    connection.connection_lost = True
    control.send_streamheader(handle, connection)
    assert not connection.send.called

    control.connections[handle] = connection
    connection.connection_lost = False
    control.send_streamheader(handle, connection)
    assert connection.send.called
