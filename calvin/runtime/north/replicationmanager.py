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

import copy

from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinuuid import uuid
from calvin.utilities.calvinlogger import get_logger
from calvin.actor.actorstate import ActorState
from calvin.actor.actorport import PortMeta

_log = get_logger(__name__)

class ReplicationData(object):
    """An actors replication data"""
    def __init__(self, actor_id=None, master=None, requirements=None, initialize=True):
        super(ReplicationData, self).__init__()
        self.id = uuid("REPLICATION") if initialize else None
        self.master = master
        self.instances = [] if actor_id is None else [actor_id]
        # TODO requirements should be plugin operation, now just do target number
        self.requirements = requirements
        self.counter = 0
        # {<actor_id>: {'known_peer_ports': [peer-ports id list], <org-port-id: <replicated-port-id>, ...}, ...}
        self.remaped_ports = {}

    def state(self, remap=None):
        state = {}
        if self.id is not None:
            # Replicas only need to keep track of id, master actor and their count number
            # Other data need to be synced from registry anyway when e.g. switching master
            state['id'] = self.id
            state['master'] = self.master
            state['counter'] = self.counter
            if remap is None:
                # For normal migration include these
                state['instances'] = self.instances
                state['requirements'] = self.requirements
                state['remaped_ports'] = self.remaped_ports
        return state

    def set_state(self, state):
        self.id = state.get('id', None)
        self.master = state.get('master', None)
        self.instances = state.get('instances', [])
        self.requirements = state.get('requirements', {})
        self.counter = state.get('counter', 0)
        self.remaped_ports = state.get('remaped_ports', {})

    def add_replica(self, actor_id):
        if actor_id in self.instances:
            return
        self.instances.append(actor_id)
        self.counter += 1

    def get_replicas(self, when_master=None):
        if self.id and self.instances and (when_master is None or when_master == self.master):
            return [a for a in self.instances if a != self.master]
        else:
            return []

    def is_master(self, actor_id):
        return self.id is not None and self.master == actor_id

    def set_remaped_ports(self, actor_id, remap_ports, ports):
        self.remaped_ports[actor_id] = remap_ports
        # Remember the ports that we knew at replication time
        self.remaped_ports[actor_id]['known_peer_ports'] = (
            [pp[1] for p in (ports['inports'].values() + ports['outports'].values()) for pp in p])

    def connect_verification(self, actor_id, port_id, peer_port_id):
        if not self.is_master(actor_id):
            return []
        connects = []
        for aid, ports in self.remaped_ports.items():
            if peer_port_id in ports['known_peer_ports']:
                continue
            # Got a port connect from an unknown peer port must be a new replica created simultaneously
            # as <aid> replica. Need to inform <aid> replica to do the connection
            connects.append((aid, ports[port_id], peer_port_id))
        return connects


class ReplicationManager(object):
    def __init__(self, node):
        super(ReplicationManager, self).__init__()
        self.node = node

    def supervise_actor(self, actor_id, requirements):
        try:
            actor = self.node.am.actors[actor_id]
        except:
            return calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND)

        if actor._replication_data.id is None:
            actor._replication_data = ReplicationData(
                actor_id=actor_id, master=actor_id, requirements=requirements)
        else:
            return calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST)

        # TODO add a callback to make sure storing worked
        self.node.storage.add_replication(actor._replication_data, cb=None)
        #TODO trigger replication loop
        return calvinresponse.CalvinResponse(True)

    def list_master_actors(self):
        return [a_id for a_id, a in self.node.am.actors.items() if a._replication_data.master == a_id]

    def replicate(self, actor_id, dst_node_id, callback):
        actor = self.node.am.actors[actor_id]
        if not actor._replication_data.is_master(actor.id):
            # Only replicate master actor
            raise Exception("Only replicate master actor")
        _log.analyze(self.node.id, "+", actor._replication_data.state(None))
        # TODO make name a property that combine name and counter in actor
        new_id = uuid("ACTOR")
        actor._replication_data.add_replica(new_id)
        new_name = actor.name + "/{}".format(actor._replication_data.counter)
        actor_type = actor._type
        ports = actor.connections(self.node.id)
        ports['actor_name'] = new_name
        ports['actor_id'] = new_id
        remap_ports = {pid: uuid("PORT") for pid in ports['inports'].keys() + ports['outports'].keys()}
        actor._replication_data.set_remaped_ports(new_id, remap_ports, ports)
        ports['inports'] = {remap_ports[pid]: v for pid, v in ports['inports'].items()}
        ports['outports'] = {remap_ports[pid]: v for pid, v in ports['outports'].items()}
        _log.analyze(self.node.id, "+ GET STATE", remap_ports)
        state = actor.state(remap_ports)
        state['name'] = new_name
        state['id'] = new_id
        actor.will_replicate(ActorState(state, actor._replication_data))
        if dst_node_id == self.node.id:
            # Make copies to make sure no objects are shared between actors
            state = copy.deepcopy(state)
            ports = copy.deepcopy(ports)
            self.node.am.new_from_migration(
                actor_type, state=state, prev_connections=ports, callback=CalvinCB(
                    self._replicated,
                    replication_id=actor._replication_data.id,
                    actor_id=new_id, callback=callback))
        else:
            self.node.proto.actor_new(
                dst_node_id, CalvinCB(self._replicated, replication_id=actor._replication_data.id,
                                         actor_id=new_id, callback=callback), actor_type, state, ports)

    def _replicated(self, status, replication_id=None, actor_id=None, callback=None):
        _log.analyze(self.node.id, "+", {'status': status, 'replication_id': replication_id, 'actor_id': actor_id})
        if status:
            # TODO add callback for storing
            self.node.storage.add_replica(replication_id, actor_id)
        if callback:
            status.data = {'actor_id': actor_id}
            callback(status)

    def connect_verification(self, actor_id, port_id, peer_port_id, peer_node_id):
        actor = self.node.am.actors[actor_id]
        connects = actor._replication_data.connect_verification(actor_id, port_id, peer_port_id)
        for actor_id, port_id, peer_port_id in connects:
            if actor_id in self.node.am.actors:
                # This actors replica is local
                self.node.pm.connect(actor_id=actor_id, port_id=port_id, peer_port_id=peer_port_id)
                _log.debug("Our connected(actor_id=%s, port_id=%s, peer_port_id=%s)" % (actor_id, port_id, peer_port_id))
            elif peer_node_id == self.node.id:
                # The peer actor replica is local
                self.node.pm.connect(port_id=peer_port_id, peer_port_id=port_id)
                _log.debug("Peer connected(actor_id=%s, port_id=%s, peer_port_id=%s)" %
                            (actor_id, port_id, peer_port_id))
            else:
                # Tell peer actor replica to connect to our replica
                _log.debug("Port remote connect request %s %s %s %s" % (actor_id, port_id, peer_port_id, peer_node_id))
                self.node.proto.port_remote_connect(peer_port_id=port_id, port_id=peer_port_id, node_id=peer_node_id,
                    callback=CalvinCB(
                        self._port_connected_remote, actor_id=actor_id, port_id=port_id, peer_port_id=peer_port_id, peer_node_id=peer_node_id))

    def _port_connected_remote(self, status, actor_id, port_id, peer_port_id, peer_node_id):
        _log.debug("Port remote connected %s %s %s %s %s" % (actor_id, port_id, peer_port_id, peer_node_id, str(status)))
        if not status:
            # Failed request for connecting, likely the actor having the peer port has migrated.
            # Find it and try again.
            peer_port_meta = PortMeta(self, port_id=peer_port_id)
            try:
                peer_port_meta.retrieve(callback=CalvinCB(self._found_peer_node, actor_id=actor_id, port_id=port_id, peer_port_id=peer_port_id))
            except calvinresponse.CalvinResponseException as e:
                _log.exception("Failed retrieving peer port meta info %s" % str(e))
                return

    def _found_peer_node(self, status, actor_id, port_id, peer_port_id, port_meta):
        if not status:
            # FIXME retry here? Now just ignore.
            _log.error("Failed finding peer node %s %s %s %s" % (actor_id, port_id, peer_port_id, str(status)))
            return
        _log.debug("Found peer node %s %s %s %s" % (actor_id, port_id, peer_port_id, str(status)))
        self._port_connected_remote(
            status=calvinresponse.CalvinResponse(True),
            actor_id=actor_id, port_id=port_id, peer_port_id=peer_port_id, peer_node_id=port_meta.node_id)
