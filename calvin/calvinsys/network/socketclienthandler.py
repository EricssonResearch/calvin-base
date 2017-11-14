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

from calvin.runtime.south.plugins.async import client_connection
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class ClientHandler(object):
    def __init__(self, node, actor):
        _log.debug("Client handler %s for %s" % (self, actor.id))
        self._actor = actor
        self._node = node
        self._connections = {}

    def _trigger_sched(self):
        self._node.sched.schedule_calvinsys(actor_id=self._actor.id)

    # Callbacks from socket client imp
    def _disconnected(self, handle, addr, reason):
        self._connections[handle]['connection'] = None
        self._push_control(("disconnected", addr, reason), handle)

    def _connected(self, handle, connection_factory, addr):
        self._connections[handle]['connection'] = connection_factory
        self._push_control(("connected", addr, ""), handle)

    def _connection_failed(self, handle, connection_factory, addr, reason):
        self._push_control(("connection_failed", reason), handle)

    def _push_data(self, handle, data):
        self._connections[handle]['data'].append(data)
        self._trigger_sched()

    def _push_control(self, data, handle):
        self._connections[handle]['control'].append(data)
        self._trigger_sched()

    # External API
    def connect(self, addr, port, server_node_name=None, mode="raw", connection_type="TCP", delimiter="\r\n"):
        handle = "%s:%s:%s" % (self._actor.id, addr, port)

        if connection_type == "TCP":
            connection_factory = client_connection.TCPClientProtocolFactory(mode=mode, delimiter=delimiter,
                                                                            server_node_name=server_node_name,
                                                                            callbacks={'data_received':
                                                                                       [CalvinCB(self._push_data, handle)]})

        elif connection_type == "UDP":
            connection_factory = client_connection.UDPClientProtocolFactory(callbacks={'data_received': [CalvinCB(self._push_data, handle)]})

        connection_factory.callback_register('connected', CalvinCB(self._connected, handle, connection_factory))
        connection_factory.callback_register('disconnected', CalvinCB(self._disconnected, handle))
        connection_factory.callback_register('connection_failed', CalvinCB(self._connection_failed, handle,
                                                                           connection_factory))
        connection_factory.connect(addr, port)
        self._connections[handle] = {'data': [], 'control': [], 'connection': None}
        return ClientConnection(self, handle)

    def disconnect(self, handle):
        if self.is_connected(handle):
            self._connections[handle]['connection'].disconnect()
            self._connections[handle]['connection'] = None

    def get_data(self, handle):
        return self._connections[handle]['data'].pop()

    def is_connected(self, handle):
        return self._connections[handle]['connection'] is not None

    def have_data(self, handle):
        return len(self._connections[handle]['data'])

    def send(self, handle, data):
        return self._connections[handle]['connection'].send(data)

    def have_control(self, handle):
        return len(self._connections[handle]['control'])

    def get_control(self, handle):
        return self._connections[handle]['control'].pop()


class ClientConnection(object):
    def __init__(self, client_handler, handle):
        self._client_handler = client_handler
        self._handle = handle

    def _call(self, func, *args, **kwargs):
        return func(self._handle, *args, **kwargs)

    def __getattr__(self, name):
        class Caller(object):
            def __init__(self, f, func):
                self.f = f
                self.func = func

            def __call__(self, *args, **kwargs):
                return self.f(self.func, *args, **kwargs)

        if hasattr(self._client_handler, name):
            if callable(getattr(self._client_handler, name)):
                return Caller(self._call, getattr(self._client_handler, name))
            else:
                return getattr(self._obj, name)

        else:
            # Default behaviour
            raise AttributeError


def register(node, actor):
    """
        Called when the system object is first created.
    """
    return ClientHandler(node, actor)
