# -*- coding: utf-8 -*-

# Copyright (c) 2016 Philip Ståhl
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

pytestmark = pytest.mark.unittest


def calvincontrol():
    control = CalvinControl()
    control.send_response = Mock()
    control.send_response = Mock()
    control.node = Mock()
    control.node.quitting = False
    return control

uuid = calvinuuid.uuid("")


def test_get_calvincontrol_returns_xxx():
    control = get_calvincontrol()
    assert control == get_calvincontrol()


@pytest.mark.parametrize("url,match,handler", [
    ("GET /actor_doc HTTP/1", None, "handle_get_actor_doc"),
    ("POST /log HTTP/1", None, "handle_post_log"),
    ("DELETE /log/TRACE_" + uuid + " HTTP/1", "TRACE_" + uuid, "handle_delete_log"),
    ("GET /log/TRACE_" + uuid + " HTTP/1", "TRACE_" + uuid, "handle_get_log"),
    ("GET /id HTTP/1", None, "handle_get_node_id"),
    ("GET /nodes HTTP/1", None, "handle_get_nodes"),
    ("GET /node/NODE_" + uuid + " HTTP/1", "NODE_" + uuid, "handle_get_node"),
    ("POST /peer_setup HTTP/1", None, "handle_peer_setup"),
    ("GET /applications HTTP/1", None, "handle_get_applications"),
    ("GET /application/APP_" + uuid + " HTTP/1", "APP_" + uuid, "handle_get_application"),
    ("DELETE /application/APP_" + uuid + " HTTP/1", "APP_" + uuid, "handle_del_application"),
    ("POST /actor HTTP/1", None, "handle_new_actor"),
    ("GET /actors HTTP/1", None, "handle_get_actors"),
    ("GET /actor/" + uuid + " HTTP/1", uuid, "handle_get_actor"),
    ("DELETE /actor/" + uuid + " HTTP/1", uuid, "handle_del_actor"),
    ("GET /actor/" + uuid + "/report HTTP/1", uuid, "handle_actor_report"),
    ("POST /actor/" + uuid + "/migrate HTTP/1", uuid, "handle_actor_migrate"),
    ("POST /actor/" + uuid + "/disable HTTP/1", uuid, "handle_actor_disable"),
    ("GET /actor/" + uuid + "/port/PORT_" + uuid + " HTTP/1", uuid, "handle_get_port"),
    ("GET /actor/" + uuid + "/port/PORT_" + uuid + "/state HTTP/1", uuid, "handle_get_port_state"),
    ("POST /connect HTTP/1", None, "handle_connect"),
    ("POST /set_port_property HTTP/1", None, "handle_set_port_property"),
    ("POST /deploy HTTP/1", None, "handle_deploy"),
    ("POST /application/APP_" + uuid + "/migrate HTTP/1", "APP_" + uuid, "handle_post_application_migrate"),
    ("POST /disconnect HTTP/1", None, "handle_disconnect"),
    ("DELETE /node HTTP/1", None, "handle_quit"),
    ("DELETE /node/migrate HTTP/1", "migrate", "handle_quit"),
    ("DELETE /node/now HTTP/1", "now", "handle_quit"),
    ("POST /meter HTTP/1", None, "handle_post_meter"),
    ("DELETE /meter/METERING_" + uuid + " HTTP/1", "METERING_" + uuid, "handle_delete_meter"),
    ("GET /meter/METERING_" + uuid + "/timed HTTP/1", "METERING_" + uuid, "handle_get_timed_meter"),
    ("GET /meter/METERING_" + uuid + "/aggregated HTTP/1", "METERING_" + uuid, "handle_get_aggregated_meter"),
    ("GET /meter/METERING_" + uuid + "/metainfo HTTP/1", "METERING_" + uuid, "handle_get_metainfo_meter"),
    ("POST /index/abc123 HTTP/1", "abc123", "handle_post_index"),
    ("DELETE /index/abc123 HTTP/1", "abc123", "handle_delete_index"),
    ("GET /index/abc123 HTTP/1", "abc123", "handle_get_index"),
    ("GET /storage/abc123 HTTP/1", "abc123", "handle_get_storage"),
    ("POST /storage/abc123 HTTP/1", "abc123", "handle_post_storage"),
    ("OPTIONS /abc123 HTTP/1", None, "handle_options"),
    ("POST /node/resource/cpuAvail HTTP/1", 25, "handle_monitor_cpu_avail"),
    ("POST /node/resource/memAvail HTTP/1", 25, "handle_monitor_mem_avail")
])

def test_routes_correctly(url, match, handler):
    control = CalvinControl()
    handler = control._handler_for_route(url)
    assert handler is not None

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
