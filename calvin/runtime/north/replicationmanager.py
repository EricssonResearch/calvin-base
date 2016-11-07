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
import random

from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinuuid import uuid
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import dynops
from calvin.runtime.south.plugins.async import async
from calvin.actor.actorstate import ActorState
from calvin.actor.actorport import PortMeta
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities.utils import enum

_log = get_logger(__name__)

FIRINGS_LENGTH = 20
REPLICATION_STATUS = enum('UNUSED', 'READY', 'REPLICATING', 'DEREPLICATING')

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
        self.replication_pressure_counts = {}
        self.status = REPLICATION_STATUS.UNUSED

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
                state['status'] = self.status
        return state

    def set_state(self, state):
        self.id = state.get('id', None)
        self.master = state.get('master', None)
        self.instances = state.get('instances', [])
        self.requirements = state.get('requirements', {})
        self.counter = state.get('counter', 0)
        self.remaped_ports = state.get('remaped_ports', {})
        self.status = state.get('status', REPLICATION_STATUS.UNUSED)

    def add_replica(self, actor_id):
        if actor_id in self.instances:
            return
        self.instances.append(actor_id)
        self.counter += 1

    def remove_replica(self):
        if len(self.instances) < 2:
            return None
        actor_id = self.instances.pop()
        # Should counter reflect current? Probably not, better to introduce seperate current count
        # self.counter -= 1
        return actor_id

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
        elif actor._replication_data.is_master(actor_id):
            # If we already is master that is OK
            return calvinresponse.CalvinResponse(True)
        else:
            return calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST)
        actor._replication_data.status = REPLICATION_STATUS.READY

        # TODO add a callback to make sure storing worked
        self.node.storage.add_replication(actor._replication_data, cb=None)
        self.node.storage.add_actor(actor, self.node.id, cb=None)
        #TODO trigger replication loop
        return calvinresponse.CalvinResponse(True)

    def list_master_actors(self):
        return [a for a_id, a in self.node.am.actors.items() if a._replication_data.master == a_id]

    #
    # Replicate
    #
    def replicate(self, actor_id, dst_node_id, callback):
        try:
            actor = self.node.am.actors[actor_id]
        except:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        if not actor._replication_data.is_master(actor.id):
            # Only replicate master actor
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        if actor._replication_data.status != REPLICATION_STATUS.READY:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.SERVICE_UNAVAILABLE))
            return
        _log.analyze(self.node.id, "+", actor._replication_data.state(None))
        actor._replication_data.status = REPLICATION_STATUS.REPLICATING
        cb_status = CalvinCB(self._replication_status_cb, replication_data=actor._replication_data, cb=callback)
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
                    actor_id=new_id, callback=cb_status, master_id=actor.id, dst_node_id=dst_node_id))
        else:
            self.node.proto.actor_new(
                dst_node_id, CalvinCB(self._replicated, replication_id=actor._replication_data.id,
                                         actor_id=new_id, callback=cb_status, master_id=actor.id,
                                         dst_node_id=dst_node_id),
                actor_type, state, ports)

    def _replicated(self, status, replication_id=None, actor_id=None, callback=None, master_id=None, dst_node_id=None):
        _log.analyze(self.node.id, "+", {'status': status, 'replication_id': replication_id, 'actor_id': actor_id})
        if status:
            # TODO add callback for storing
            self.node.storage.add_replica(replication_id, actor_id)
            self.node.control.log_actor_replicate(
                actor_id=master_id, replica_actor_id=actor_id,
                replication_id=replication_id, dest_node_id=dst_node_id)
        if callback:
            status.data = {'actor_id': actor_id, 'replication_id': replication_id}
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

    #
    # Dereplication
    #

    def dereplicate(self, actor_id, callback, exhaust=False):
        terminate = DISCONNECT.EXHAUST if exhaust else DISCONNECT.TERMINATE
        try:
            replication_data = self.node.am.actors[actor_id]._replication_data
        except:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        if not replication_data.is_master(actor_id):
            # Only dereplicate by master actor
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        if replication_data.status != REPLICATION_STATUS.READY:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.SERVICE_UNAVAILABLE))
            return
        replication_data.status = REPLICATION_STATUS.DEREPLICATING
        last_replica_id = replication_data.remove_replica()
        if last_replica_id is None:
            replication_data.status = REPLICATION_STATUS.READY
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        cb_status = CalvinCB(self._replication_status_cb, replication_data=replication_data, cb=callback)
        if last_replica_id in self.node.am.actors:
            self.node.am.destroy_with_disconnect(last_replica_id, terminate=terminate,
                callback=CalvinCB(self._dereplicated, replication_data=replication_data,
                                    last_replica_id=last_replica_id, 
                                    node_id=None, cb=cb_status))
        else:
            self.node.storage.get_actor(last_replica_id,
                CalvinCB(func=self._dereplicate_actor_cb,
                            replication_data=replication_data, terminate=terminate, cb=cb_status))

    def _dereplicate_actor_cb(self, key, value, replication_data, terminate, cb):
        """ Get actor callback """
        _log.analyze(self.node.id, "+", {'actor_id': key, 'value': value})
        if value and 'node_id' in value:
            # Use app destroy since it can remotely destroy actors
            self.node.proto.app_destroy(value['node_id'],
                CalvinCB(self._dereplicated, replication_data=replication_data, last_replica_id=key, 
                            node_id=value['node_id'], cb=cb),
                None, [key], disconnect=terminate)
        else:
            # FIXME Should do retries
            if cb:
                cb(calvinresponse.CalvinResponse(False))

    def _dereplicated(self, status, replication_data, last_replica_id, node_id, cb):
        if status:
            # TODO add callback for storing
            self.node.storage.remove_replica(replication_data.id, last_replica_id)
            self.node.control.log_actor_dereplicate(
                actor_id=replication_data.master, replica_actor_id=last_replica_id,
                replication_id=replication_data.id)
        if cb:
            status.data = {'actor_id': last_replica_id}
            cb(status)

    def _replication_status_cb(self, status, replication_data, cb):
        replication_data.status = REPLICATION_STATUS.READY
        if cb:
            cb(status)

    #
    # Requirement controlled replication
    #

    def replication_loop(self):
        replicate = []
        for actor in self.list_master_actors():
            if actor._replication_data.status != REPLICATION_STATUS.READY:
                continue
            replicate_actor = False
            pressure = actor.get_pressure()
            counts = {}
            for port_pair, port_queues in pressure.items():
                position, count, full_positions = port_queues
                counts[port_pair] = count
                if len(full_positions) < 2:
                    continue
                # Check if two new recent queue full events
                if (actor._replication_data.replication_pressure_counts.get(port_pair, 0) < (count - 2) and
                    full_positions[-1] > (position - 15) and
                    full_positions[-2] > (position - 15)):
                    replicate_actor = True
            if replicate_actor:
                 replicate.append(actor)
                 actor._replication_data.replication_pressure_counts = counts
        # TODO Do the complete requirement matching replication based what the requirements are besides the normal
        # attribute matching
        for actor in replicate:
            _log.debug("Auto-replicate")
            #self.replicate(actor.id, self.node.id, CalvinCB(self._replication_loop_log_cb, actor_id=actor.id))
            self.replicate_by_requirements(actor, CalvinCB(self._replication_loop_log_cb, actor_id=actor.id))

    def _replication_loop_log_cb(self, status, actor_id):
        _log.info("Auto-replicated %s: %s" % (actor_id, str(status)))

    def replicate_by_requirements(self, actor, callback=None):
        """ Update requirements and trigger a replication """
        actor._collect_placement_counter = 0
        actor._collect_placement_last_value = 0
        actor._collect_placement_cb = None
        node_iter = self.node.app_manager.actor_requirements(None, actor.id)
        possible_placements = set([])
        done = [False]
        node_iter.set_cb(self._update_requirements_placements, node_iter, actor, possible_placements,
                         cb=callback, done=done)
        _log.analyze(self.node.id, "+ CALL CB", {'actor_id': actor.id, 'node_iter': str(node_iter)})
        # Must call it since the triggers might already have released before cb set
        self._update_requirements_placements(node_iter, actor, possible_placements, cb=callback, done=done)
        _log.analyze(self.node.id, "+ END", {'actor_id': actor.id, 'node_iter': str(node_iter)})

    def _update_requirements_placements(self, node_iter, actor, possible_placements, done, move=False,
                                        authorization_check=False, cb=None):
        _log.analyze(self.node.id, "+ BEGIN", {}, tb=True)
        if actor._collect_placement_cb:
            actor._collect_placement_cb.cancel()
            actor._collect_placement_cb = None
        if done[0]:
            return
        try:
            while True:
                _log.analyze(self.node.id, "+ ITER", {})
                node_id = node_iter.next()
                possible_placements.add(node_id)
        except dynops.PauseIteration:
            _log.analyze(self.node.id, "+ PAUSED",
                    {'counter': actor._collect_placement_counter,
                     'last_value': actor._collect_placement_last_value,
                     'diff': actor._collect_placement_counter - actor._collect_placement_last_value})
            # FIXME the dynops should be self triggering, but is not...
            # This is a temporary fix by keep trying
            delay = 0.0 if actor._collect_placement_counter > actor._collect_placement_last_value + 100 else 0.2
            actor._collect_placement_counter += 1
            actor._collect_placement_cb = async.DelayedCall(delay, self._update_requirements_placements,
                                                    node_iter, actor, possible_placements, done=done,
                                                    cb=cb)
            return
        except StopIteration:
            # All possible actor placements derived
            _log.analyze(self.node.id, "+ ALL", {})
            done[0] = True
            if not possible_placements:
                if cb:
                    cb(status=calvinresponse.CalvinResponse(False))
                return
            print "PLACEMENTS", possible_placements
            # TODO pick a runtime that is lightly loaded
            self.replicate(actor.id, random.choice(list(possible_placements)), callback=cb)
            _log.analyze(self.node.id, "+ END", {})
        except:
            _log.exception("actormanager:_update_requirements_placements")
