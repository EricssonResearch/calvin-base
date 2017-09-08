# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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
from random import randint
from calvin.runtime.north import metering
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south.plugins.async import server_connection
from urlparse import urlparse
from calvin.requests import calvinresponse
from calvin.utilities.security import Security
from calvin.utilities import calvinuuid
from calvin.utilities.issuetracker import IssueTracker
#
# Dynamically build selected set of APIs
#
from control_apis import routes
from control_apis import security_api
from control_apis import runtime_api
from control_apis import application_api
from control_apis import documentation_api
from control_apis import logging_api
from control_apis import metering_api
from control_apis import registry_api
from control_apis import uicalvinsys_api

_log = get_logger(__name__)

_calvincontrol = None

def get_calvincontrol():
    """ Returns the CalvinControl singleton
    """
    global _calvincontrol
    if _calvincontrol is None:
        _calvincontrol = CalvinControl()
    return _calvincontrol


class CalvinControl(object):

    """ A HTTP REST API for calvin nodes
    """

    def __init__(self):
        self.node = None
        self.loggers = {}
        self.server = None
        self.connections = {}
        self.tunnel = None
        self.host = None
        self.tunnel_server = None
        self.tunnel_client = None
        self.metering = None
        self.security = None
        self.routes = routes.install_handlers(self)

    def start(self, node, uri, tunnel=False, external_uri=None):
        """ If not tunnel, start listening on uri and handle http requests.
            If tunnel, setup a tunnel to uri and handle requests.
        """
        self.metering = metering.get_metering()
        self.node = node
        self.security = Security(self.node)
        schema, _ = uri.split(':', 1)
        if tunnel:
            # Connect to tunnel server
            self.tunnel_client = CalvinControlTunnelClient(uri, self)
        else:
            url = urlparse(uri)
            self.port = int(url.port)
            self.host = url.hostname
            if external_uri is not None:
                self.external_host = urlparse(external_uri).hostname
            else:
                self.external_host = self.host
            _log.info("Control API listening on: %s:%s" % (self.host, self.port))

            self.server = server_connection.ServerProtocolFactory(self.handle_request, "http", node_name=node.node_name)
            self.server.start(self.host, self.port)

            # Create tunnel server
            self.tunnel_server = CalvinControlTunnelServer(self.node)

    def stop(self):
        """ Stop """
        self.server.stop()
        if self.tunnel_server is not None:
            self.tunnel_server.stop()
        if self.tunnel_client is not None:
            self.tunnel_client.stop()

    def close_log_tunnel(self, handle):
        """ Close log tunnel
        """
        for user_id, logger in self.loggers:
            if logger.handle == handle:
                del self.loggers[user_id]

    def handle_request(self, actor_ids=None):
        """ Handle incoming requests on socket
        """
        if self.server.pending_connections:
            addr, conn = self.server.accept()
            self.connections[addr] = conn

        for handle, connection in self.connections.items():
            if connection.data_available:
                command, headers, data = connection.data_get()
                self.route_request(handle, connection, command, headers, data)

    def _handler_for_route(self, command):
        for re_route, handler in self.routes:
            match_object = re_route.match(command)
            if match_object:
                # FIXME: Return capture groups instead
                return handler, match_object
        return None, None

    def route_request(self, handle, connection, command, headers, data):
        if self.node.quitting:
            # Answer internal error on all requests while quitting, assume client can handle that
            # TODO: Answer permantely moved (301) instead with header Location: <another-calvin-runtime>???
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)
            return
        try:
            issuetracker = IssueTracker()
            handler, match = self._handler_for_route(command)
            if handler:
                credentials = None
                if data:
                    data = json.loads(data)
                _log.debug("Calvin control handles:%s\n%s\n---------------" % (command, data))
                handler(handle, connection, match, data, headers)
            else:
                _log.error("No route found for: %s\n%s" % (command, data))
                self.send_response(handle, connection, None, status=404)
        except Exception as e:
            _log.info("Failed to parse request", exc_info=e)
            self.send_response(handle, connection, None, status=calvinresponse.BAD_REQUEST)

    def send_response(self, handle, connection, data, status=200, content_type=None):
        """ Send response header text/html
        """
        content_type = content_type or "Content-Type: application/json"
        content_type += "\n"

        # No data return 204 no content
        if data is None and status in range(200, 207):
            status = 204

        header = "HTTP/1.0 " + \
            str(status) + " " + calvinresponse.RESPONSE_CODES[status] + \
            "\n" + ("" if data is None else content_type ) + \
            "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n" + \
            "Access-Control-Allow-Origin: *\r\n" + "\n"

        if connection is None:
            msg = {"cmd": "httpresp", "msgid": handle, "header": header, "data": data}
            self.tunnel_client.send(msg)
        else:
            if not connection.connection_lost:
                connection.send(header)
                if data:
                    connection.send(data)
                connection.close()
            del self.connections[handle]

    def send_streamheader(self, handle, connection):
        """ Send response header for text/event-stream
        """
        response = "HTTP/1.0 200 OK\n" + "Content-Type: text/event-stream\n" + \
            "Access-Control-Allow-Origin: *\r\n" + "\n"

        if connection is not None:
            if not connection.connection_lost:
                connection.send(response)
        elif self.tunnel_client is not None:
                msg = {"cmd": "logresp", "msgid": handle, "header": response, "data": None}
                self.tunnel_client.send(msg)

    #
    # Logging hooks
    #
    def log_actor_firing(self, actor_id, action_method, tokens_produced, tokens_consumed, production):
        pass

    def log_actor_new(self, actor_id, actor_name, actor_type, is_shadow):
        pass

    def log_actor_destroy(self, actor_id):
        pass

    def log_actor_migrate(self, actor_id, dest_node_id):
        pass

    def log_actor_replicate(self, actor_id, replica_actor_id, replication_id, dest_node_id):
        pass

    def log_actor_dereplicate(self, actor_id, replica_actor_id, replication_id):
        pass

    def log_application_new(self, application_id, application_name):
        pass

    def log_application_destroy(self, application_id):
        pass

    def log_link_connected(self, peer_id, uri):
        pass

    def log_link_disconnected(self, peer_id):
        pass

    def log_log_message(self, message):
        pass



class CalvinControlTunnelServer(object):

    """ A Calvin control tunnel server
    """

    def __init__(self, node):
        self.node = node
        self.tunnels = {}
        self.controltunnels = {}
        # Register for incoming control proxy requests
        self.node.proto.register_tunnel_handler("control", CalvinCB(self.tunnel_request_handles))

    def stop(self):
        for _, control in self.controltunnels.items():
            control.close()

    def tunnel_request_handles(self, tunnel):
        """ Incoming tunnel request for storage proxy server
            Start a socket server and update peer node with control uri
        """
        # Register tunnel
        self.tunnels[tunnel.peer_node_id] = tunnel
        self.controltunnels[tunnel.peer_node_id] = CalvinControlTunnel(tunnel)
        tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
        tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
        tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
        # We accept it by returning True
        return True

    def tunnel_down(self, tunnel):
        """ Callback that the tunnel is not accepted or is going down """
        self.controltunnels[tunnel.peer_node_id].close()
        del self.tunnels[tunnel.peer_node_id]
        del self.controltunnels[tunnel.peer_node_id]
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, tunnel):
        """ Callback that the tunnel is working """
        _log.analyze(self.node.id, "+ SERVER", {"tunnel_id": tunnel.id})
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a storage client request"""
        self.controltunnels[tunnel.peer_node_id].handle_response(payload)


class CalvinControlTunnel(object):

    """ A Calvin control socket to tunnel proxy
    """

    def __init__(self, tunnel):
        self.tunnel = tunnel
        self.connections = {}

        # Start a socket server on same interface as calvincontrol
        self.host = get_calvincontrol().host

        for x in range(0, 10):
            try:
                self.port = randint(5100, 5200)
                self.server = server_connection.ServerProtocolFactory(self.handle_request, "http")
                self.server.start(self.host, self.port)
                _log.info("Control proxy for %s listening on: %s:%s" % (tunnel.peer_node_id, self.host, self.port))
                break
            except:
                pass

        # Tell peer node that we a listening and on what uri
        msg = {"cmd": "started",
               "controluri": "http://" + get_calvincontrol().external_host + ":" + str(self.port)}
        self.tunnel.send(msg)

    def close(self):
        self.server.stop()

    def handle_request(self, actor_ids=None):
        """ Handle connections and tunnel requests
        """
        if self.server.pending_connections:
            addr, conn = self.server.accept()
            msg_id = calvinuuid.uuid("MSGID")
            self.connections[msg_id] = conn
            _log.debug("New connection msg_id: %s" % msg_id)

        for msg_id, connection in self.connections.items():
            if connection.data_available:
                command, headers, data = connection.data_get()
                _log.debug("CalvinControlTunnel handle_request msg_id: %s command: %s" % (msg_id, command))
                msg = {"cmd": "httpreq",
                       "msgid": msg_id,
                       "command": command,
                       "headers": headers,
                       "data": data}
                self.tunnel.send(msg)

    def handle_response(self, payload):
        """ Handle a tunnel response
        """
        if "msgid" in payload:
            msgid = payload["msgid"]
            if msgid in self.connections:
                if "cmd" in payload and "header" in payload and "data" in payload:
                    cmd = payload["cmd"]
                    if cmd == "httpresp":
                        self.send_response(msgid, payload["header"], payload["data"], True)
                        return
                    elif cmd == "logresp":
                        self.send_response(msgid, payload["header"], payload["data"], False)
                        return
                    elif cmd == "logevent":
                        result = self.send_response(msgid, payload["header"], payload["data"], False)
                        if not result:
                            msg = {"cmd": "logclose"}
                            self.tunnel.send(msg)
                        return
        _log.error("Unknown control proxy response %s" % payload)

    def send_response(self, msgid, header, data, closeConnection):
        """ Send response header text/html
        """
        connection = self.connections[msgid]
        if not connection.connection_lost:
            if header is not None:
                connection.send(str(header))
            if data is not None:
                connection.send(str(data))
            if closeConnection:
                connection.close()
                del self.connections[msgid]
            return True
        del self.connections[msgid]
        return False


class CalvinControlTunnelClient(object):

    """ A Calvin control tunnel client
    """

    def __init__(self, uri, calvincontrol):
        self.uri = uri
        self.calvincontrol = calvincontrol
        self.tunnel = None
        self.calvincontrol.node.network.join([uri], CalvinCB(self._start_link_cb))

    def stop(self):
        pass

    def _start_link_cb(self, status, uri, peer_node_id):
        if status == "NACK":
            return
        # Got link set up tunnel
        master_id = peer_node_id
        self.tunnel = self.calvincontrol.node.proto.tunnel_new(master_id, 'control', {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def tunnel_down(self):
        """ Callback that the tunnel is not accepted or is going down """
        if not self.tunnel:
            return True
        self.tunnel = None
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self):
        """ Callback that the tunnel is working """
        if not self.tunnel:
            return True
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, payload):
        """ Gets called when a control proxy replies"""
        if "cmd" in payload:
            if payload["cmd"] == "httpreq":
                try:
                    self.calvincontrol.route_request(
                        payload["msgid"], None, payload["command"], payload["headers"], payload["data"])
                except:
                    _log.exception("FIXME! Caught exception in calvincontrol when tunneling.")
                    self.calvincontrol.send_response(payload["msgid"], None, None, status=calvinresponse.INTERNAL_ERROR)
            elif payload["cmd"] == "started":
                self.calvincontrol.node.external_control_uri = payload["controluri"]
                self.calvincontrol.node.storage.add_node(self.calvincontrol.node)
                return
            elif payload["cmd"] == "logclose":
                self.calvincontrol.close_log_tunnel(payload["msg_id"])
                return
        _log.error("Tunnel client received unknown command %s" % payload['cmd'] if 'cmd' in payload else "")

    def send(self, msg):
        if self.tunnel:
            self.tunnel.send(msg)
        else:
            _log.error("No tunnel connected")
