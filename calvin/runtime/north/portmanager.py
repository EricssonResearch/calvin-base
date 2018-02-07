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

from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.plugins.port.connection import ConnectionFactory, PURPOSE
from calvin.actor.actorport import PortMeta
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.actor.actor import ShadowActor
from calvin.utilities.utils import enum
from calvin.runtime.north.plugins.port import DISCONNECT

_log = calvinlogger.get_logger(__name__)

class PortManager(object):
    """
    PortManager handles the setup of communication between ports intra- & inter-runtimes
    """

    def __init__(self, node, proto):
        super(PortManager, self).__init__()
        self.node = node
        self.ports = {}  # key: port_id, value: port
        self.connections_data = ConnectionFactory(self.node, PURPOSE.INIT, portmanager=self).init()

    def _set_port_property(self, port, port_property, value):
        if isinstance(port_property, basestring):
            # TODO verify property and value are allowed and correct
            port.properties[port_property] = value
            return response.CalvinResponse(True)
        return response.CalvinResponse(response.BAD_REQUEST)

    def set_port_property(self, port_id=None, actor_id=None, port_dir=None, port_name=None,
                            port_property=None, value=None):
        _log.analyze(self.node.id, "+", {port_property: value})
        port = self._get_local_port(actor_id=actor_id, port_name=port_name, port_dir=port_dir, port_id=port_id)
        return self._set_port_property(port, port_property, value)

    def set_script_port_property(self, actor_id, port_property_list):
        _log.analyze(self.node.id, "+", port_property_list)
        success = []
        if port_property_list is None:
            return response.CalvinResponse(True)
        for p in port_property_list:
            if p['direction'] is None:
                p['direction'] = "unknown"
            try:
                port = self._get_local_port(actor_id=actor_id, port_name=p['port'], port_dir=p['direction'],
                                            port_id=None)
                for port_property, value in p['properties'].items():
                    success.append(self._set_port_property(port, port_property, value))
            except:
                success.append(False)
        ok = all(success)
        return response.CalvinResponse(True) if ok else response.CalvinResponse(response.BAD_REQUEST)

    def set_port_properties(self, port_id=None, actor_id=None, port_dir=None, port_name=None,
                            **port_properties):
        _log.analyze(self.node.id, "+", port_properties)
        port = self._get_local_port(actor_id=actor_id, port_name=port_name, port_dir=port_dir, port_id=port_id)
        success = []
        for port_property, value in port_properties.items():
            success.append(self._set_port_property(port, port_property, value))
        ok = all(success)
        return response.CalvinResponse(True) if ok else response.CalvinResponse(response.BAD_REQUEST)

    def get_port_properties(self, port_id=None, actor_id=None, port_dir=None, port_name=None):
        port = self._get_local_port(actor_id=actor_id, port_name=port_name, port_dir=port_dir, port_id=port_id)
        return port.properties

    def connection_request(self, payload):
        """ A request from a peer to connect a port"""
        _log.analyze(self.node.id, "+", payload, peer_node_id=payload['from_rt_uuid'])
        if not ('peer_port_id' in payload or
                ('peer_actor_id' in payload and
                'peer_port_name' in payload and
                'peer_port_properties' in payload)):
            # Not enough info to find port
            _log.analyze(self.node.id, "+ NOT ENOUGH DATA", payload, peer_node_id=payload['from_rt_uuid'])
            return response.CalvinResponse(response.BAD_REQUEST)
        our_port_meta = PortMeta(self,
                                actor_id=payload['peer_actor_id'],
                                port_id=payload['peer_port_id'],
                                port_name=payload['peer_port_name'],
                                properties=payload['peer_port_properties'],
                                node_id=self.node.id)
        try:
            port = our_port_meta.port
        except:
            # We don't have the port
            _log.analyze(self.node.id, "+ PORT NOT FOUND", payload, peer_node_id=payload['from_rt_uuid'])
            return response.CalvinResponse(response.NOT_FOUND)
        else:
            # Let a specific connection handler take care of the request
            peer_port_meta = PortMeta(self,
                                    port_id=payload['port_id'],
                                    node_id=payload['from_rt_uuid'],
                                    properties=payload['port_properties'])
            return ConnectionFactory(self.node, PURPOSE.CONNECT).get(
                    port, peer_port_meta, payload=payload).connection_request()

    def connect(self, callback=None, actor_id=None, port_name=None, port_properties=None, port_id=None,
                peer_node_id=None, peer_actor_id=None, peer_port_name=None, peer_port_properties=None,
                peer_port_id=None):
        """ Obtain any missing information to enable making a connection and make actual connect
            callback: an optional callback that gets called with status when finished
            local port identified by:
                actor_id, port_name and port_dir='in'/'out' or
                port_id
            peer_node_id: an optional node id the peer port is locate on, will use storage to find it if not supplied
            peer port (remote or local) identified by:
                peer_actor_id, peer_port_name and peer_port_dir='in'/'out' or
                peer_port_id
        """

        local_port_meta = PortMeta(self, actor_id=actor_id, port_id=port_id, port_name=port_name,
                            properties=port_properties, node_id=self.node.id)
        peer_port_meta = PortMeta(self, actor_id=peer_actor_id, port_id=peer_port_id, port_name=peer_port_name,
                            properties=peer_port_properties, node_id=peer_node_id)

        _log.analyze(self.node.id, "+", {'local': local_port_meta, 'peer': peer_port_meta},
                    peer_node_id=peer_node_id, tb=True)
        try:
            port = local_port_meta.port
        except response.CalvinResponseException as e:
            if callback:
                callback(status=e.response,
                         actor_id=actor_id,
                         port_name=port_name,
                         port_id=port_id,
                         peer_node_id=peer_node_id,
                         peer_actor_id=peer_actor_id,
                         peer_port_name=peer_port_name,
                         peer_port_id=peer_port_id)
                return
            else:
                raise e.response

        # Retrieve node id etc, raise exception if not possible, continue in _connect otherwise
        try:
            peer_port_meta.retrieve(callback=CalvinCB(self._connect, local_port=port, callback=callback))
        except response.CalvinResponseException as e:
            if callback:
                callback(status=e.response,
                         actor_id=actor_id,
                         port_name=port_name,
                         port_id=port_id,
                         peer_node_id=peer_node_id,
                         peer_actor_id=peer_actor_id,
                         peer_port_name=peer_port_name,
                         peer_port_id=peer_port_id)
                return
            else:
                raise e.response

    def _connect(self, local_port=None, callback=None, status=None, port_meta=None):
        """ Do the connection of ports, all neccessary information supplied but
            maybe not all pre-requisites for remote connections.
        """
        if not status:
            if callback:
                callback(status=status,
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
            return
        _log.analyze(self.node.id, "+", {'local_port': local_port, 'peer_port': port_meta},
                        peer_node_id=port_meta.node_id, tb=True)

        ConnectionFactory(self.node, PURPOSE.CONNECT).get(local_port, port_meta, callback).connect()

    def disconnect(self, callback=None, actor_id=None, port_name=None, port_dir=None, port_id=None,
                   terminate=DISCONNECT.TEMPORARY):
        """ Do disconnect for port(s)
            callback: an optional callback that gets called with status when finished
            ports identified by only local actor_id:
                actor_id: the actor that all ports will be disconnected on
                port_dir: when set to "in" or "out" selects all the in or out ports, respectively
                callback will be called once when all ports are diconnected or first failed
            local port identified by:
                actor_id, port_name and port_dir='in'/'out' or
                port_id
                callback will be called once when all peer ports (fanout) are disconnected or first failed

            disconnect -*> _disconnect_port -*> _disconnected_port (-*> _disconnecting_actor_cb) -> !
        """
        port_ids = []
        if actor_id and not (port_id or port_name):
            # We disconnect all ports on an actor
            try:
                actor = self.node.am.actors[actor_id]
            except:
                # actor not found
                status = response.CalvinResponse(response.NOT_FOUND, "Actor %s must be local" % (actor_id))
                if callback:
                    callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id)
                    return
                else:
                    raise response.CalvinResponseException(status)

            # It is possible to select only in or out ports
            if port_dir is None or port_dir == "in":
                port_ids.extend([p.id for p in actor.inports.itervalues()])
            if port_dir is None or port_dir == "out":
                port_ids.extend([p.id for p in actor.outports.itervalues()])
            # Need to collect all callbacks into one
            if callback:
                callback = CalvinCB(self._disconnecting_actor_cb, _callback=callback,
                                    port_ids=port_ids, actor_id=actor_id)
        else:
            # Just one port to disconnect
            if port_id:
                port_ids.append(port_id)
            else:
                # Awkward but lets get the port id from name etc so that the rest can loop over port ids
                try:
                    port = self._get_local_port(actor_id, port_name, port_dir, port_id)
                except:
                    # not local
                    status = response.CalvinResponse(response.NOT_FOUND,
                                        "Port %s on actor %s must be local" %
                                        (port_name if port_name else port_id, actor_id if actor_id else "some"))
                    if callback:
                        callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id)
                        return
                    else:
                        raise response.CalvinResponseException(status)
                else:
                    # Found locally
                    port_ids.append(port.id)

        _log.analyze(self.node.id, "+", {'port_ids': port_ids})
        
        # Run over copy of list of ports since modified inside the loop
        for port_id in port_ids[:]:
            _log.analyze(self.node.id, "+ PRE FACTORY", {'port_id': port_id})
            connections = ConnectionFactory(self.node, PURPOSE.DISCONNECT).get_existing(
                            port_id, callback=callback)
            _log.analyze(self.node.id, "+ POST FACTORY", {'port_id': port_id,
                            'connections': map(lambda x: str(x), connections)})
            # Run over copy since connections modified (tricky!) in loop
            for c in connections[:]:
                c.disconnect(terminate=terminate)
            _log.analyze(self.node.id, "+ POST DISCONNECT", {'port_id': port_id,
                            'connection': str(c)})
        _log.analyze(self.node.id, "+ DONE", {'actor_id': actor_id})

    def _disconnecting_actor_cb(self, status, _callback, port_ids, port_id=None, actor_id=None):
        """ Get called for each of the actor's ports when disconnecting, but callback should only be called once
            status: OK or not
            _callback: original callback
            port_ids: list of port ids kept in context between calls when *changed* by this function, do not replace it
            state: dictionary keeping disconnect information
        """
        _log.analyze(self.node.id, "+", {'port_ids': port_ids, 'port_id': port_id})
        # Send negative response if not already done it
        if not status and port_ids:
            if _callback:
                del port_ids[:]
                _callback(status=status, actor_id=actor_id, port_id=port_id)
            return

        if port_id in port_ids:
            # Remove this port from list
            port_ids.remove(port_id)
            # If all ports done send positive response
            if not port_ids:
                if _callback:
                    _callback(status=response.CalvinResponse(True), actor_id=actor_id)

    def disconnection_request(self, payload):
        """ A request from a peer to disconnect a port"""
        if not ('peer_port_id' in payload or
                ('peer_actor_id' in payload and
                'peer_port_name' in payload and
                'peer_port_dir' in payload)):
            # Not enough info to find port
            return response.CalvinResponse(response.BAD_REQUEST)
        # Check if port actually is local
        local_port_meta = PortMeta(
            self,
            actor_id=payload['peer_actor_id'] if 'peer_actor_id' in payload else None,
            port_id=payload['peer_port_id'] if 'peer_port_id' in payload else None,
            port_name=payload['peer_port_name'] if 'peer_port_name' in payload else None,
            properties={'direction': payload['peer_port_dir'] if 'peer_port_dir' in payload else None},
            node_id=self.node.id)
        peer_port_meta = PortMeta(self, port_id=payload['port_id'], node_id=payload['from_rt_uuid'])

        _log.analyze(self.node.id, "+", {'local': local_port_meta, 'peer': peer_port_meta},
                    peer_node_id=payload['from_rt_uuid'], tb=True)
        try:
            port = local_port_meta.port
        except response.CalvinResponseException as e:
            # We don't have the port
            return response.CalvinResponse(response.NOT_FOUND)
        else:
            # Disconnect and destroy endpoints
            return ConnectionFactory(self.node, PURPOSE.DISCONNECT).get(
                    local_port_meta.port, peer_port_meta, payload=payload
                    ).disconnection_request(payload.get('terminate', False), payload.get('remaining_tokens', {}))

    def add_ports_of_actor(self, actor):
        """ Add an actor's ports to the dictionary, used by actor manager """
        for port in actor.inports.values():
            self.ports[port.id] = port
        for port in actor.outports.values():
            self.ports[port.id] = port

    def remove_ports_of_actor(self, actor):
        """ Remove an actor's ports in the dictionary, used by actor manager """
        port_ids = []
        for port in actor.inports.values():
            port_ids.append(port.id)
            self.ports.pop(port.id)
            # Also unregister any left over endpoints (during app destroy we don't disconnect)
            for e in port.endpoints:
                try:
                    self.node.sched.unregister_endpoint(e)
                except:
                    pass
        for port in actor.outports.values():
            port_ids.append(port.id)
            self.ports.pop(port.id)
            # Also unregister any left over endpoints (during app destroy we don't disconnect)
            for e in port.endpoints:
                try:
                    self.node.sched.unregister_endpoint(e)
                except:
                    pass
        return port_ids

    def _get_local_port(self, actor_id=None, port_name=None, port_dir=None, port_id=None):
        """ Return a port if it is local otherwise raise exception """
        if port_id and port_id in self.ports:
            return self.ports[port_id]
        if port_name and actor_id and port_dir in ['in', 'out']:
            for port in self.ports.itervalues():
                if port.name == port_name and port.owner and port.owner.id == actor_id and port.direction == port_dir:
                    return port
            # For new shadow actors we create the port
            _log.analyze(self.node.id, "+ SHADOW PORT?", {'actor_id': actor_id, 'port_name': port_name,
                                                            'port_dir': port_dir, 'port_id': port_id})
            actor = self.node.am.actors.get(actor_id, None)
            _log.debug("SHADOW ACTOR: %s, %s, %s" %
                        (("SHADOW" if isinstance(actor, ShadowActor) else "NOT SHADOW"), type(actor), actor))
            if isinstance(actor, ShadowActor):
                port = actor.create_shadow_port(port_name, port_dir, port_id)
                _log.analyze(self.node.id, "+ CREATED SHADOW PORT",
                                {'actor_id': actor_id, 'port_name': port_name,
                                'port_dir': port_dir, 'port_id': port.id if port else None})
                if port:
                    self.ports[port.id] = port
                    return port
        elif port_name and actor_id and port_dir == 'unknown':
            for port in self.ports.itervalues():
                if port.name == port_name and port.owner and port.owner.id == actor_id:
                    return port
        raise KeyError("Port '%s' not found locally" % (port_id if port_id else str(actor_id) +
                                                        "/" + str(port_name) + ":" + str(port_dir)))
