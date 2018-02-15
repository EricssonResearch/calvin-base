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
from calvin.runtime.north.plugins.port import queue
import calvin.requests.calvinresponse as response
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.runtime.north.plugins.port.endpoint.common import Endpoint

import copy

_log = get_logger(__name__)


class Port(object):
    """docstring for Port"""

    def __init__(self, name, owner, properties=None):
        super(Port, self).__init__()
        # Human readable port name
        self.name = name
        # Actor instance to which the port belongs (may change over time)
        self.owner = owner
        # Unique id to universally identify port (immutable)
        self.id = calvinuuid.uuid("PORT")
        # The token queue, will be set when connected.
        self.queue = queue.common.QueueNone()
        self.properties = {}
        self.properties['routing'] = 'default'
        self.properties['nbr_peers'] = 1
        if properties:
            self.properties.update(properties)

    def __str__(self):
        return "%s id=%s" % (self.name, self.id)

    def set_config(self, config):
        """
        Set additional config information on the port.
        The default behaviour is to delegate the information to the port's queue.
        The 'config' parameter is a dictionary with settings.
        """

        def _local_name(peer_actor):
            _, local_name = peer_actor._name.rsplit(':', 1)
            return local_name

        port_to_id = {'{}.{}'.format(_local_name(ep.peer_port.owner), ep.peer_port.name) : ep.peer_port.id for ep in self.endpoints}
        if 'port-order' in config:
            # Remap from actor.port to port_id
            # FIXME: Will not work in the general case.
            #        Extend calvinsys with runtime API and use that instead
            port_order = config['port-order']
            config['port-order'] = [port_to_id[p] for p in port_order]
        if 'port-mapping' in config:
            # Remap from actor.port to port_id
            # FIXME: Will not work in the general case.
            #        Extend calvinsys with runtime API and use that instead
            mapping = config['port-mapping']
            config['port-mapping'] = {k:port_to_id[p] for k,p in mapping.iteritems()}

        self.queue.set_config(config)

    def set_queue(self, new_queue):
        if self.queue is None:
            self.queue = new_queue
        elif isinstance(self.queue, queue.common.QueueNone) and self.queue.queue_type == new_queue.queue_type:
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
        return {'name': self.name, 'id': self.id, 'queue': self.queue._state(), 'properties': self.properties}

    def _set_state(self, state):
        """Set port state."""
        self.name = state.get('name')
        self.id = state.get('id', calvinuuid.uuid("PORT"))
        self.properties.update(state.get('properties', {}))
        if 'queue' in state:
            self.queue._set_state(state.get('queue'))

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

    def disconnect(self, peer_ids, terminate):
        """Disconnect port from counterpart."""
        raise Exception("Must be implemented in sub-classes")

    @property
    def direction(self):
        return self.properties.get('direction', '')


class InPort(Port):

    """An inport can have many endpoints."""

    def __init__(self, name, owner, properties=None):
        super(InPort, self).__init__(name, owner, properties)
        self.properties['direction'] = 'in'
        self.endpoints = []

    def __str__(self):
        s = super(InPort, self).__str__()
        s = s + "%s: %s\n" % (self.properties.get('routing','default'), self.properties.get('nbr_peers', 1))
        s = s + " [ "
        for ep in self.endpoints:
            s = s + str(ep) + " "
        s = s + "]"
        return s

    def is_connected(self):
        if len(self.endpoints) < self.properties.get('nbr_peers', 1):
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
            old_endpoint = Endpoint.void()
        else:
            old_endpoint = match[0]
            self.detach_endpoint(old_endpoint)

        self.endpoints.append(endpoint_)
        endpoint_.attached()
        nbr_peers = len(self.queue.get_peers())
        if nbr_peers > self.properties['nbr_peers']:
            # We have more peers due to replication
            self.properties['nbr_peers'] = nbr_peers
        else:
            # No need to tell actor it could be fully connected since it was that also before
            self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        # Only called from attach_endpoint with the old endpoint
        if endpoint_ not in self.endpoints:
            _log.warning("Outport: No such endpoint")
            return
        self.endpoints.remove(endpoint_)

    def disconnect(self, peer_ids=None, terminate=DISCONNECT.TEMPORARY):
        if peer_ids is None:
            endpoints = self.endpoints
        else:
            endpoints = [e for e in self.endpoints if e.get_peer()[1] in peer_ids]
        _log.debug("actorinport.disconnect %s remove: %s current: %s %s" % (self.id, peer_ids, [e.get_peer()[1] for e in self.endpoints], DISCONNECT.reverse_mapping[terminate]))
        # Remove all endpoints corresponding to the peer ids
        self.endpoints = [e for e in self.endpoints if e not in endpoints]
        for e in endpoints:
            e.detached(terminate=terminate)
        if terminate >= DISCONNECT.TERMINATE:
            self.properties['nbr_peers'] -= len(endpoints)
        exhausting = self.queue.is_exhausting()
        if len(self.endpoints) == 0 and not exhausting:
            self.owner.did_disconnect(self)
        _log.debug("actorinport.disconnected %s removed: %s current: %s" % (self.id, peer_ids, [e.get_peer()[1] for e in self.endpoints]))
        return endpoints

    def any_outstanding_exhaustion_tokens(self):
        try:
            return self.queue.any_outstanding_exhaustion_tokens()
        except AttributeError:
            # When not implemented by queue assume it's not needed
            return False

    def exhausted_tokens(self, tokens):
        _log.debug("actorinport.exhausted_tokens %s %s" % (self.owner._id, self.id))
        self.queue.set_exhausted_tokens(tokens)
        exhausting = self.queue.is_exhausting()
        if len(self.endpoints) == 0 and not exhausting:
            self.owner.did_disconnect(self)
            _log.debug("actorinport.exhausted_tokens did_disconnect")

    def finished_exhaustion(self):
        if len(self.endpoints) == 0 and not self.queue.is_exhausting():
            self.owner.did_disconnect(self)
            _log.debug("actorinport.finished_exhaustion did_disconnect %s" % self.id)

    def peek_token(self, metadata=None):
        """Used by actor (owner) to peek a token from the port. Following peeks will get next token. Reset with peek_cancel."""
        if metadata is None:
            metadata = self.id
        return self.queue.peek(metadata)

    def peek_cancel(self, metadata=None):
        """Used by actor (owner) to cancel port peeking to front token."""
        if metadata is None:
            metadata = self.id
        return self.queue.cancel(metadata)

    def peek_commit(self, metadata=None):
        """Used by actor (owner) to commit port peeking to front token."""
        if metadata is None:
            metadata = self.id
        # The return has information on if the queue exhausted the remaining tokens
        return self.queue.commit(metadata)

    def read(self, metadata=None):
        """
        Used by actor (owner) to read a token from the port.
        Returns tuple (token, exhaust) where exhaust is port (exhausted) or None (not exhausted)
        """
        # FIXME: We no longer need the peek/commit/cancel functionality.
        #        Queues should be changed accordingly, and this method should use queue.read()
        if metadata is None:
            metadata = self.id
        token = self.peek_token(metadata)
        exhausted = self.peek_commit(metadata)
        return (token, exhausted)

    def tokens_available(self, length, metadata=None):
        """Used by actor (owner) to check number of tokens on the port."""
        if metadata is None:
            metadata = self.id
        return self.queue.tokens_available(length, metadata)

    def get_peers(self):
        peers = []
        for ep in self.endpoints:
            peers.append(ep.get_peer())
        queue_peers = self.queue.get_peers()
        if queue_peers is not None and len(peers) < len(queue_peers):
            all = set(queue_peers)
            all -= set([p[1] for p in peers])
            peers.extend([(None, p) for p in all])
        return peers


class OutPort(Port):

    """An outport can have many endpoints."""

    def __init__(self, name, owner, properties=None):
        super(OutPort, self).__init__(name, owner, properties)
        self.properties['routing'] = 'fanout'
        self.properties['direction'] = 'out'
        self.endpoints = []

    def __str__(self):
        s = super(OutPort, self).__str__()
        s = s + "%s: %s\n" % (self.properties.get('routing','default'), self.properties.get('nbr_peers', 1))
        s = s + " [ "
        for ep in self.endpoints:
            s = s + str(ep) + " "
        s = s + "]"
        return s

    def is_connected(self):
        if len(self.endpoints) < self.properties.get('nbr_peers', 1):
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
            old_endpoint = Endpoint.void()
        else:
            old_endpoint = match[0]
            self.detach_endpoint(old_endpoint)

        self.endpoints.append(endpoint_)
        endpoint_.attached()
        nbr_peers = len(self.queue.get_peers())
        if nbr_peers > self.properties['nbr_peers']:
            # We have more peers due to replication
            self.properties['nbr_peers'] = nbr_peers
        else:
            # No need to tell actor it could be fully connected since it was that also before
            self.owner.did_connect(self)
        return old_endpoint

    def detach_endpoint(self, endpoint_):
        # Only called from attach_endpoint with the old endpoint
        if endpoint_ not in self.endpoints:
            _log.warning("Outport: No such endpoint")
            return
        self.endpoints.remove(endpoint_)

    def disconnect(self, peer_ids=None, terminate=DISCONNECT.TEMPORARY):
        if peer_ids is None:
            endpoints = self.endpoints
        else:
            endpoints = [e for e in self.endpoints if e.get_peer()[1] in peer_ids]
        _log.debug("actoroutport.disconnect   remove: %s current: %s %s" % (peer_ids, [e.get_peer()[1] for e in self.endpoints], DISCONNECT.reverse_mapping[terminate]))
        # Remove all endpoints corresponding to the peer ids
        self.endpoints = [e for e in self.endpoints if e not in endpoints]
        for e in endpoints:
            e.detached(terminate=terminate)
        if terminate:
            self.properties['nbr_peers'] -= len(endpoints)
        if len(self.endpoints) == 0:
            self.owner.did_disconnect(self)
        _log.debug("actoroutport.disconnected remove: %s current: %s" % (peer_ids, [e.get_peer()[1] for e in self.endpoints]))
        return endpoints

    def exhausted_tokens(self, tokens):
        _log.debug("actoroutport.exhausted_tokens %s %s" % (self.owner._id, self.id))
        self.queue.set_exhausted_tokens(tokens)

    def write_token(self, data):
        """docstring for write_token"""
        self.queue.write(data, self.id)

    def tokens_available(self, length):
        """Used by actor (owner) to check number of token slots available on the port."""
        return self.queue.slots_available(length, self.id)

    def get_peers(self):
        peers = []
        for ep in self.endpoints:
            peers.append(ep.get_peer())
        queue_peers = self.queue.get_peers()
        if queue_peers is not None and len(peers) < len(queue_peers):
            all = set(queue_peers)
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
            except response.CalvinResponseException:
                return False
        return self.node_id == self.pm.node.id

    def check_still_local(self):
        """ Check if a retrived port meta still is local.
        """
        node = self.pm.node
        if self.actor_id is not None and self.actor_id not in node.am.actors:
            # Actor not hear anymore
            return False
        if self.port_id is not None and self.port_id not in node.pm.ports:
            # Port not hear anymore
            return False
        return True

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
        direction = None
        if self.properties and 'direction' in self.properties:
            direction = self.properties['direction']

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
        except KeyError as e:
            # not local
            if local_only:
                if self.port_id:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s must be local" % (self.port_id)) # For other side
                else:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s on actor %s must be local" % # For other side
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
