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

from calvin.utilities import calvinuuid
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north import queue
from calvin.runtime.south import endpoint
import calvin.requests.calvinresponse as response
from calvin.utilities.calvinlogger import get_logger
import copy

_log = get_logger(__name__)


class Port(object):
    """docstring for Port"""

    def __init__(self, name, owner):
        super(Port, self).__init__()
        # Human readable port name
        self.name = name
        # Actor instance to which the port belongs (may change over time)
        self.owner = owner
        # Unique id to universally identify port (immutable)
        self.id = calvinuuid.uuid("PORT")
        # The token queue, will be set when connected.
        self.queue = queue.QueueNone()
        self.properties = {}

    def __str__(self):
        return "%s id=%s" % (self.name, self.id)

    def set_queue(self, new_queue):
        if self.queue is None:
            self.queue = new_queue
        elif isinstance(self.queue, queue.QueueNone) and self.queue.queue_type == new_queue.queue_type:
            # Apply state from none queue of same type (state from e.g. migration)
            new_queue._set_state(self.queue._state())
            self.queue = new_queue
        elif self.queue.queue_type == "none":
            # Stateless queue none is just replaced
            self.queue = new_queue
        elif self.queue.queue_type == new_queue.queue_type:
            # A new queue of same type, just discard to not dismiss existing tokens
            # Since this is set at each connect
            return
        else:
            # Want to replace an existing queue type (e.g. during migration)
            raise NotImplementedError("FIXME Can't swap queue types")

    def _state(self):
        """Return port state for serialization."""
        return {'name': self.name, 'id': self.id, 'queue': self.queue._state()}

    def _set_state(self, state):
        """Set port state."""
        self.name = state.pop('name')
        self.id = state.pop('id')
        self.queue._set_state(state.pop('queue'))

    def attach_endpoint(self, endpoint_):
        """
        Connect port to counterpart.
        """
        raise Exception("Can't attach endpoint to  port %s.%s with id: %s" % (
            self.owner.name, self.name, self.id))

    def detach_endpoint(self, endpoint_):
        """
        Disconnect port from counterpart.
        """
        raise Exception("Can't detach endpoint from  port %s.%s with id: %s" % (
            self.owner.name, self.name, self.id))

    def disconnect(self):
        """Disconnect port from counterpart. Raises an exception if port is not connected."""
        # FIXME: Implement disconnect
        raise Exception("Can't disconnect port %s.%s with id: %s" % (
            self.owner.name, self.name, self.id))

    @property
    def direction(self):
        return self.properties.get('direction', '')


class InPort(Port):

    """An inport can have only one endpoint."""

    def __init__(self, name, owner):
        super(InPort, self).__init__(name, owner)
        self.endpoint = endpoint.Endpoint(self)
        self.properties['direction'] = 'in'

    def __str__(self):
        s = super(InPort, self).__str__()
        return s + " " + str(self.endpoint)

    def is_connected(self):
        return self.endpoint.is_connected()

    def is_connected_to(self, peer_id):
        return self.endpoint.is_connected() and self.endpoint.get_peer()[1] == peer_id

    def attach_endpoint(self, endpoint_):
        old_endpoint = self.endpoint
        if type(old_endpoint) is not endpoint.Endpoint:
            self.detach_endpoint(old_endpoint)
        self.endpoint = endpoint_
        self.endpoint.attached()
        self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        if not self.endpoint == endpoint_:
            _log.warning("Inport: No such endpoint")
            return
        self.owner.did_disconnect(self)
        self.endpoint = endpoint.Endpoint(self, former_peer_id=endpoint_.get_peer()[1])

    def disconnect(self, peer_ids=None):
        # Ignore peer_ids since we can only have one peer
        self.owner.did_disconnect(self)
        endpoints = [self.endpoint]
        self.endpoint = endpoint.Endpoint(self, former_peer_id=self.endpoint.get_peer()[1])
        return endpoints

    def peek_token(self):
        """Used by actor (owner) to peek a token from the port. Following peeks will get next token. Reset with peek_rewind."""
        return self.endpoint.peek_token()

    def peek_rewind(self):
        """Used by actor (owner) to rewind port peeking to front token."""
        return self.endpoint.peek_rewind()

    def commit_peek_as_read(self):
        """Used by actor (owner) to rewind port peeking to front token."""
        return self.endpoint.commit_peek_as_read()

    def tokens_available(self, length):
        """Used by actor (owner) to check number of tokens on the port."""
        return self.endpoint.tokens_available(length)

    def get_peers(self):
        return [self.endpoint.get_peer()]


class OutPort(Port):

    """An outport can have many endpoints."""

    def __init__(self, name, owner):
        super(OutPort, self).__init__(name, owner)
        self.properties['fanout'] = 1
        self.endpoints = []
        self.properties['direction'] = 'out'

    def __str__(self):
        s = super(OutPort, self).__str__()
        s = s + "fan-out: %s\n" % self.properties['fanout']
        s = s + " [ "
        for ep in self.endpoints:
            s = s + str(ep) + " "
        s = s + "]"
        return s

    def _state(self):
        state = super(OutPort, self)._state()
        state['fanout'] = self.properties['fanout']
        return state

    def _set_state(self, state):
        self.properties['fanout'] = state.pop('fanout')
        super(OutPort, self)._set_state(state)

    def is_connected(self):
        if len(self.endpoints) < self.properties['fanout']:
            return False
        for ep in self.endpoints:
            if not ep.is_connected():
                return False
        return True

    def is_connected_to(self, peer_id):
        for ep in self.endpoints:
            if ep.get_peer()[1] == peer_id:
                return True
        return False

    def attach_endpoint(self, endpoint_):
        peer_id = endpoint_.peer_id
        # Check if this is a reconnect after migration
        match = [e for e in self.endpoints if e.peer_id == peer_id]
        if not match:
            old_endpoint = None
        else:
            old_endpoint = match[0]
            self.detach_endpoint(old_endpoint)

        self.endpoints.append(endpoint_)
        endpoint_.attached()
        self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        if endpoint_ not in self.endpoints:
            _log.warning("Outport: No such endpoint")
            return
        self.owner.did_disconnect(self)
        self.endpoints.remove(endpoint_)

    def disconnect(self, peer_ids=None):
        if peer_ids is None:
            endpoints = self.endpoints
        else:
            endpoints = [e for e in self.endpoints if e.get_peer()[1] in peer_ids]
        # Remove all endpoints corresponding to the peer ids
        self.endpoints = [e for e in self.endpoints if e not in endpoints]
        # Rewind any tentative reads to acked reads
        # When local no effect since already equal
        # When tunneled transport tokens after last continuous acked token will be resent later, receiver will just ack them again if rereceived
        for e in endpoints:
            peer_node_id, peer_id = e.get_peer()
            self.queue.commit_reads(peer_id, False)
        self.owner.did_disconnect(self)
        return endpoints

    def write_token(self, data):
        """docstring for write_token"""
        if not self.queue.write(data):
            raise Exception("FIFO full when writing to port %s.%s with id: %s" % (
                self.owner.name, self.name, self.id))

    def tokens_available(self, length):
        """Used by actor (owner) to check number of token slots available on the port."""
        try:
            if self.endpoints[0].single_tokens_available:
                return self.endpoints[0].tokens_available(length)
            else:
                bool(self.endpoints and all([ep.tokens_available(length) for ep in self.endpoints]))
        except:
            return bool(self.endpoints and all([ep.tokens_available(length) for ep in self.endpoints]))

    def get_peers(self):
        peers = []
        for ep in self.endpoints:
            peers.append(ep.get_peer())
        if len(peers) < len(self.queue.readers):
            all = copy.copy(self.queue.readers)
            all -= set([p[1] for p in peers])
            peers.extend([(None, p) for p in all])
        return peers


class PortMeta(object):
    """ Collection and retrieval of meta data for a port """

    def __init__(self, port_manager, actor_id=None, port_id=None, port_name=None, properties=None, node_id=None):
        super(PortMeta, self).__init__()
        self.pm = port_manager
        self.actor_id = actor_id
        self.port_id = port_id
        self.port_name = port_name
        self.properties = properties
        self.node_id = node_id
        self._port = None
        self.retries = 0  # Used to keep track of how many times we have tried to find the port

    def encode(self):
        return {'actor_id': self.actor_id,
                'port_id': self.port_id,
                'port_name': self.port_name,
                'properties': self.properties,
                'node_id': self.node_id}

    def __str__(self):
        return str(self.encode())

    def is_local(self):
        if self.node_id is None:
            try:
                self.retrieve(callback=None, local_only=True)
            except:
                return False
        return self.node_id == self.pm.node.id

    @property
    def port(self):
        """ Return the port instance, only relevant if local.
            Will raise exception if not local.
        """
        if self._port is None:
            self.retrieve(callback=None, local_only=True)
        return self._port

    def retry(self, callback):
        self.node_id = None
        self.retries += 1
        self.retrieve(callback)

    def retrieve(self, callback=None, local_only=False):
        """ Try to fill in port meta information based on current
            available info. Raise CalvinResponseException (BAD_REQUEST)
            when the supplied input data is incomplete.
            Could also return OK (directly available) or
            ACCEPTED (maybe available in callback).
            When not a BAD_REQUEST the callback will be called with
            any result.

            Will only make sure that either port id or
            (actor name, port name, direction) is available.
            Node id is always retrieved.
            local_only means only looks locally for the port.
        """
        try:
            direction = self.properties['direction']
        except:
            direction = None
        try:
            self._port = self.pm._get_local_port(self.actor_id, self.port_name, direction, self.port_id)
            # Found locally
            self.actor_id = self._port.owner.id
            self.port_id = self._port.id
            self.port_name = self._port.name
            self.properties = self._port.properties
            self.node_id = self.pm.node.id
            status = response.CalvinResponse(True)
            if callback:
                callback(status=status, port_meta=self)
            return status
        except:
            # not local
            if local_only:
                if self.port_id:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s must be local" % (self.port_id))
                else:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s on actor %s must be local" %
                                                    (self.port_name, self.actor_id))
                raise response.CalvinResponseException(status)

        # No node id ...
        if not self.node_id:
            if self.port_id:
                # ... but an id of a port lets ask for more info
                self.pm.node.storage.get_port(self.port_id, CalvinCB(self._retrieve_by_port_id,
                                                                        cb=callback))
                return response.CalvinResponse(response.ACCEPTED)
            elif self.actor_id and self.port_name:
                # ... but an id of an actor lets ask for more info
                self.pm.node.storage.get_actor(self.actor_id, CalvinCB(self._retrieve_by_actor_id,
                                                                        cb=callback))
                return response.CalvinResponse(response.ACCEPTED)
            else:
                # ... and no info on how to get more info, abort
                status = response.CalvinResponse(response.BAD_REQUEST,
                                    "Unknown node id (%s), actor_id (%s) and/or port_id(%s)" %
                                    (self.node_id, self.actor_id, self.port_id))
                raise response.CalvinResponseException(status)

        # Have node id but are we missing port info
        if not ((self.actor_id and self.port_name and direction) or self.port_id):
            # We miss information on to find the peer port
            status = response.CalvinResponse(response.BAD_REQUEST,
                                "actor_id (%s) and/or port_id(%s)" %
                                (self.actor_id, self.port_id))
            raise response.CalvinResponseException(status)

        # Got everything for an answer
        status = response.CalvinResponse(True)
        if callback:
            callback(status=status, port_meta=self)
        return status

    def _retrieve_by_port_id(self, key, value, cb):
        """ Gets called when registry responds with port information """
        _log.analyze(self.pm.node.id, "+", self.encode(), peer_node_id=self.node_id, tb=True)
        if not isinstance(value, dict):
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND, "Port unknown in registry"), port_meta=self)
            return
        try:
            self.node_id = value['node_id'] or self.node_id
        except:
            if not self.node_id:
                if cb:
                    cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown node in registry"),
                        port_meta=self)
                return
        # Lets fill in any other missing info
        try:
            self.properties = value['properties'] or self.properties
        except:
            pass
        try:
            self.port_name = value['name'] or self.port_name
        except:
            pass
        try:
            self.actor_id = value['actor_id'] or self.actor_id
        except:
            pass
        # Got everything for an answer
        if cb:
            cb(status=response.CalvinResponse(True), port_meta=self)

    def _retrieve_by_actor_id(self, key, value, cb):
        """ Gets called when registry responds with actor information"""
        _log.analyze(self.pm.node.id, "+", self.encode(), peer_node_id=self.node_id, tb=True)
        if not isinstance(value, dict):
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND, "Actor unknown in registry"), port_meta=self)
            return

        try:
            self.node_id = value['node_id'] or self.node_id
        except:
            if not self.node_id:
                if cb:
                    cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown node in registry"),
                        port_meta=self)
                return

        if not self.port_id:
            try:
                # Get port id based on names
                ports = value['inports' if self.properties['direction'] == 'in' else 'outports']
                for port in ports:
                    if port['name'] == self.port_name:
                        self.port_id = port['id']
                        break
            except:
                if not self.node_id:
                    if cb:
                        cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown id in registry"),
                            port_meta=self)
                    return

        # Got everything for an answer
        if cb:
            cb(status=response.CalvinResponse(True), port_meta=self)


if __name__ == '__main__':

    class Stub(object):

        def __init__(self, name):
            self.name = name

    a = Stub('a')

    i = InPort('in', None, a)
    o = OutPort('out', None, a)

    print(i.id)
    print(o.id)
