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
from calvin.runtime.north import fifo
from calvin.runtime.south import endpoint
from calvin.utilities.calvinlogger import get_logger
import copy

_log = get_logger(__name__)


class Port(object):
    """docstring for Port"""

    def __init__(self, name, owner, fifo_size=5):
        super(Port, self).__init__()
        # Human readable port name
        self.name = name
        # Actor instance to which the port belongs (may change over time)
        self.owner = owner
        # Unique id to universally identify port (immutable)
        self.id = calvinuuid.uuid("PORT")
        # The token queue. Not all scenarios use it,
        # but needed when e.g. changing from local to remote connection.
        self.fifo = fifo.FIFO(fifo_size)

    def __str__(self):
        return "%s id=%s" % (self.name, self.id)

    def _state(self):
        """Return port state for serialization."""
        return {'name': self.name, 'id': self.id, 'fifo': self.fifo._state()}

    def _set_state(self, state):
        """Set port state."""
        self.name = state.pop('name')
        self.id = state.pop('id')
        self.fifo._set_state(state.pop('fifo'))

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


class InPort(Port):

    """An inport can have only one endpoint."""

    def __init__(self, name, owner):
        super(InPort, self).__init__(name, owner)
        self.fifo.add_reader(self.id)
        self.endpoint = endpoint.Endpoint(self)

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
        self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        if not self.endpoint == endpoint_:
            _log.warning("Inport: No such endpoint")
            return
        self.owner.did_disconnect(self)
        self.endpoint = endpoint.Endpoint(self, former_peer_id=endpoint_.get_peer()[1])

    def disconnect(self):
        self.owner.did_disconnect(self)
        endpoints = [self.endpoint]
        self.endpoint = endpoint.Endpoint(self, former_peer_id=self.endpoint.get_peer()[1])
        return endpoints

    def read_token(self):
        """Used by actor (owner) to read a token from the port. Returns None if token queue is empty."""
        return self.endpoint.read_token()

    def peek_token(self):
        """Used by actor (owner) to peek a token from the port. Following peeks will get next token. Reset with peek_rewind."""
        return self.endpoint.peek_token()

    def peek_rewind(self):
        """Used by actor (owner) to rewind port peeking to front token."""
        return self.endpoint.peek_rewind()

    def commit_peek_as_read(self):
        """Used by actor (owner) to rewind port peeking to front token."""
        return self.endpoint.commit_peek_as_read()

    def available_tokens(self):
        """Used by actor (owner) to check number of tokens on the port."""
        return self.endpoint.available_tokens()

    def get_peer(self):
        return self.endpoint.get_peer()


class OutPort(Port):

    """An outport can have many endpoints."""

    def __init__(self, name, owner):
        super(OutPort, self).__init__(name, owner)
        self.fanout = 1
        self.endpoints = []

    def __str__(self):
        s = super(OutPort, self).__str__()
        s = s + "fan-out: %s\n" % self.fanout
        s = s + " [ "
        for ep in self.endpoints:
            s = s + str(ep) + " "
        s = s + "]"
        return s

    def _state(self):
        state = super(OutPort, self)._state()
        state['fanout'] = self.fanout
        return state

    def _set_state(self, state):
        self.fanout = state.pop('fanout')
        super(OutPort, self)._set_state(state)

    def is_connected(self):
        if len(self.endpoints) < self.fanout:
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

        self.fifo.add_reader(endpoint_.peer_id)
        self.endpoints.append(endpoint_)
        self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        if endpoint_ not in self.endpoints:
            _log.warning("Outport: No such endpoint")
            return
        self.owner.did_disconnect(self)
        self.endpoints.remove(endpoint_)

    def disconnect(self):
        self.owner.did_disconnect(self)
        endpoints = self.endpoints
        self.endpoints = []
        # Rewind any tentative reads to acked reads
        # When local no effect since already equal
        # When tunneled transport tokens after last continuous acked token will be resent later, receiver will just ack them again if rereceived
        for e in endpoints:
            peer_node_id, peer_id = e.get_peer()
            self.fifo.commit_reads(peer_id, False)
        return endpoints

    def write_token(self, data):
        """docstring for write_token"""
        if not self.fifo.write(data):
            raise Exception("FIFO full when writing to port %s.%s with id: %s" % (
                self.owner.name, self.name, self.id))

    def available_tokens(self):
        """Used by actor (owner) to check number of token slots available on the port."""
        return self.fifo.available_slots()

    def can_write(self):
        """Used by actor to test if writing a token is possible. Returns a boolean."""
        return self.fifo.can_write()

    def get_peers(self):
        peers = []
        for ep in self.endpoints:
            peers.append(ep.get_peer())
        if len(peers) < len(self.fifo.readers):
            all = copy.copy(self.fifo.readers)
            all -= set([p[1] for p in peers])
            peers.extend([(None, p) for p in all])
        return peers


if __name__ == '__main__':
    class Stub(object):

        def __init__(self, name):
            self.name = name

    a = Stub('a')

    i = InPort('in', None, a)
    o = OutPort('out', None, a)

    print(i.id)
    print(o.id)
