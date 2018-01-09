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
import time

from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinuuid import uuid
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import dynops
from calvin.utilities.requirement_matching import ReqMatch
from calvin.utilities.replication_defs import REPLICATION_STATUS, PRE_CHECK
from calvin.actorstore.store import GlobalStore
from calvin.runtime.south.plugins.async import async
from calvin.runtime.north.plugins.requirements import req_operations
from calvin.actor.actorport import PortMeta
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities.utils import enum

_log = get_logger(__name__)


class ReplicationId(object):
    """An actors replication identity"""
    def __init__(self, replication_id=None, original_actor_id=None, index=None):
        super(ReplicationId, self).__init__()
        self.id = replication_id
        self.original_actor_id = original_actor_id
        self.index = index
        self._terminate_with_node = False
        self._placement_req = []

    def state(self, remap=None):
        state = {}
        if self.id:
            state['id'] = self.id
            state['original_actor_id'] = self.original_actor_id
            state['index'] = self.index
            state['_terminate_with_node'] = self._terminate_with_node
            state['_placement_req'] = self._placement_req
        return state

    def set_state(self, state):
        self.id = state.get('id', None)
        self.original_actor_id = state.get('original_actor_id', None)
        self.index = state.get('index', None)
        self._terminate_with_node = state.get('_terminate_with_node', False)
        self._placement_req = state.get('_placement_req', [])

    def terminate_with_node(self, actor_id):
        return self._terminate_with_node and not (actor_id == self.original_actor_id)

class ReplicationData(object):
    """Replication state"""
    def __init__(self, actor_id=None, original_actor_id=None, requirements=None):
        super(ReplicationData, self).__init__()
        self.id = uuid("REPLICATION")
        self.original_actor_id = original_actor_id
        self.instances = [] if actor_id is None else [actor_id]
        self.requirements = requirements
        self.counter = 0
        # {<actor_id>: {'known_peer_ports': [peer-ports id list], <org-port-id: <replicated-port-id>, ...}, ...}
        self.remaped_ports = {}
        self.status = REPLICATION_STATUS.UNUSED
        self._terminate_with_node = False
        self._one_per_runtime = False
        self._placement_req = []
        self.leader_election = None
        self.leader_node_id = None
        self.actor_state = None

    def state(self):
        state = {}
        state['id'] = self.id
        state['original_actor_id'] = self.original_actor_id
        state['counter'] = self.counter
        state['_terminate_with_node'] = self._terminate_with_node
        state['_one_per_runtime'] = self._one_per_runtime
        state['_placement_req'] = self._placement_req
        state['leader_election'] = self.leader_election
        state['leader_node_id'] = self.leader_node_id
        state['actor_state'] = self.actor_state
        state['instances'] = self.instances
        state['requirements'] = self.requirements
        state['remaped_ports'] = self.remaped_ports
        state['status'] = REPLICATION_STATUS.READY
        try:
            state['req_op'] = req_operations[self.requirements['op']].get_state(self)
        except:
            pass
        return state

    def set_state(self, state):
        self.id = state.get('id', None)
        self.original_actor_id = state.get('original_actor_id', None)
        self.instances = state.get('instances', [])
        self.requirements = state.get('requirements', {})
        self.counter = state.get('counter', 0)
        self._terminate_with_node = state.get('_terminate_with_node', False)
        self._one_per_runtime = state.get('_one_per_runtime', False)
        self._placement_req = state.get('_placement_req', [])
        self.remaped_ports = state.get('remaped_ports', {})
        self.status = state.get('status', REPLICATION_STATUS.UNUSED)
        self.leader_election = state.get('leader_election', None)
        self.leader_node_id = state.get('leader_node_id', None)
        self.actor_state = state.get('actor_state', None)
        try:
            req_operations[self.requirements['op']].set_state(self, state['req_op'])
        except:
            pass

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
        if self.id and self.instances and (when_master is None or when_master == self.original_actor_id):
            return [a for a in self.instances if a != self.original_actor_id]
        else:
            return []

    def is_master(self, actor_id):
        return self.id is not None and self.original_actor_id == actor_id

    def is_busy(self):
        return self.status in [REPLICATION_STATUS.REPLICATING, REPLICATION_STATUS.DEREPLICATING]

    def terminate_with_node(self, actor_id):
        return self._terminate_with_node and not self.is_master(actor_id)

    def inhibate(self, actor_id, inhibate):
        if inhibate:
            if self.requirements:
                self.status = REPLICATION_STATUS.INHIBATED
        elif self.is_master(actor_id):
            self.status = REPLICATION_STATUS.READY
        else:
            self.status = REPLICATION_STATUS.UNUSED

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

    def init_requirements(self, requirements=None):
        if requirements is not None:
            self.requirements = requirements
        if not self.requirements:
            return
        try:
            req_operations[self.requirements['op']].init(self)
        except:
            _log.exception("init_requirements")

class LeaderElection(object):
    def __init__(self, node, replication_data):
        """ Implements all the different leader election methods """
        super(LeaderElection, self).__init__()
        self.replication_data = replication_data
        self.node = node

    def elect(self, cb):
        method = self.replication_data.leader_election
        if method == 'actor':
            if self.replication_data.original_actor_id in self.node.am.list_actors():
                cb(status=calvinresponse.OK, leader=self.node.id)
                return
            else:
                def master_node(key, value):
                    if calvinresponse.isnotfailresponse(value) and 'node_id' in value:
                        cb(status=calvinresponse.OK, leader=value['node_id'])
                    else:
                        cb(status=calvinresponse.NOT_FOUND, leader=self.node.id)

                self.node.storage.get_actor(actor_id=self.replication_data.master, cb=master_node)
                return
        elif method == 'registry_central':
            def super_node(value):
                if calvinresponse.isnotfailresponse(value):
                    if self.node.id in value:
                        cb(status=calvinresponse.OK, leader=self.node.id)
                    else:
                        cb(status=calvinresponse.OK, leader=value[0])
                else:
                    cb(status=calvinresponse.NOT_FOUND, leader=self.node.id)
            self.node.storage.get_super_node(1, cb=super_node)
        elif method is None:
            cb(status=calvinresponse.OK, leader=self.node.id)

class ReplicationManager(object):
    def __init__(self, node):
        super(ReplicationManager, self).__init__()
        self.node = node
        self.managed_replications = {}  # {<rep_id>: <rep_data>, ...} for which we are elected leader

    def inhibate(self, *args, **kwargs):
        # FIXME need to implement this if still needed
        _log.debug("FIXME FIXME inhibate FIXME FIXME")
        pass

    def supervise_actor(self, actor_id, requirements, actor_args):
        try:
            actor = self.node.am.actors[actor_id]
        except:
            # Only possible to supervise a local actor
            return calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND)

        if actor._replication_id.id is not None:
            # We don't allow changing scaling requirements
            return calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST)

        # Create main replication data
        replication_data = ReplicationData(actor_id=actor_id, original_actor_id=actor_id, requirements=requirements)
        replication_data.init_requirements()
        # Copy some data that is needed on each replica
        actor._replication_id = ReplicationId(replication_id=replication_data.id, original_actor_id=actor.id, index=0)
        actor._replication_id._terminate_with_node = replication_data._terminate_with_node
        actor._replication_id._placement_req = replication_data._placement_req
        # Update registry with the actors replication id
        self.node.storage.add_actor(actor, self.node.id, cb=None)

        # Create the base state of actor, that is used for initial replica states
        # The actor is not neccessarily connected, hence peer port (queue) information
        # need to be updated when replicating
        state = actor.serialize()
        _log.debug("supervise_actor type %s state %s" % (type(actor), state))
        # Some data is missing from serialized state that is needed, place it in replication state ns
        state['replication'] = {'_type': actor._type}
        # Move port id, name and property (not queue, i.e. peer and tokens) into replication ns
        state['replication']['inports'] = {k:
            {n: v[n] for n in ('id', 'name', 'properties')} for k, v in state['private']['inports'].items()}
        state['replication']['outports'] = {k:
            {n: v[n] for n in ('id', 'name', 'properties')} for k, v in state['private']['outports'].items()}
        state['private']['inports'] = {}
        state['private']['outports'] = {}
        if actor_args is not None:
            # We got actor_args hence we should create an initial state that looks like a shadow actor
            # Replace managed actor attributes with the shadow args, i.e. init args
            state['managed'] = {'_shadow_args': actor_args}
            state['private']['_has_started'] = False

        replication_data.actor_state = state
        # UNUSED until leader election settled and any shadow actor data fetched
        self.add_replication_leader(replication_data, status=REPLICATION_STATUS.UNUSED)

        replication_data._wait_for_outstanding = ['leader', 'ports']
        # If supervised actor is ShadowActor, the ports and requires are missing
        if actor.is_shadow():
            replication_data._wait_for_outstanding.append('requires')
            # Find requires
            def _desc_cb(signature, description):
                _log.debug("REQUIRES BACK %s \n%s" % (replication_data._wait_for_outstanding, description))
                requires = None
                for actor_desc in description:
                    # We get list of possible descriptions back matching the signature
                    # In reality it is only one
                    if 'requires' in actor_desc:
                        requires = actor_desc['requires']
                if requires is not None:
                    replication_data.actor_state['private']['_requires'] = requires
                replication_data._wait_for_outstanding.remove('requires')
                if not replication_data._wait_for_outstanding:
                    self.move_replication_leader(replication_data.id, replication_data._move_to_leader)
            try:
                GlobalStore(node=self.node).global_signature_lookup(actor._signature, cb=_desc_cb)
            except:
                _log.exception("supervise actor GlobalStore exception")
                replication_data._wait_for_outstanding.remove('requires')

        def _leader_elected(status, leader):
            _log.debug("LEADER ELECTED %s, %s" % (status, leader))
            replication_data._wait_for_outstanding.remove('leader')
            if not replication_data._wait_for_outstanding:
                self.move_replication_leader(replication_data.id, leader)
            else:
                replication_data._move_to_leader = leader
        LeaderElection(self.node, replication_data).elect(cb=_leader_elected)

        return calvinresponse.CalvinResponse(True, {'replication_id': replication_data.id})

    def deployed_actors_connected(self, actor_ids):
        for replication_data in self.managed_replications.values():
            if replication_data.original_actor_id not in actor_ids:
                continue
            # supervised actor now fully connected
            try:
                actor = self.node.am.actors[replication_data.original_actor_id]
            except Exception as e:
                # This should never happen
                _log.exception("deployed_actors_connected, actor %s missing" % replication_data.original_actor_id)
                raise(e)
            state = actor.serialize()
            # Move port id, name and property (not queue, i.e. peer and tokens) into replication ns
            replication_data.actor_state['replication']['inports'] = {k:
                {n: v[n] for n in ('id', 'name', 'properties')} for k, v in state['private']['inports'].items()}
            replication_data.actor_state['replication']['outports'] = {k:
                {n: v[n] for n in ('id', 'name', 'properties')} for k, v in state['private']['outports'].items()}
            replication_data._wait_for_outstanding.remove('ports')
            if not replication_data._wait_for_outstanding:
                self.move_replication_leader(replication_data.id, replication_data._move_to_leader)

    def list_master_actors(self):
        return [a for a_id, a in self.node.am.actors.items() if a._replication_id.original_actor_id == a_id]

    def list_replication_actors(self, replication_id):
        return [a_id for a_id, a in self.node.am.actors.items() if a._replication_id.id == replication_id]

    def move_replication_leader(self, replication_id, dst_node_id, cb=None):
        _log.debug("move_replication_leader")
        if replication_id not in self.managed_replications:
            return cb(status=calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
        rd = self.managed_replications.pop(replication_id)
        if self.node.id == dst_node_id:
            # Even if moving to same node insert it again
            self.add_replication_leader(rd)
            return cb(status=calvinresponse.CalvinResponse(calvinresponse.OK))
        def _elected_cb(reply):
            if not reply:
                # Failed, put it back in
                _log.debug("Failed to move to the new elected leader")
                self.add_replication_leader(rd)
            if cb:
                cb(reply)
        self.node.proto.leader_elected(peer_node_id=dst_node_id, leader_type="replication", cmd="create",
                                       data=rd.state(), callback=_elected_cb)

    def add_replication_leader(self, replication_data, status=None):
        if isinstance(replication_data, dict):
            try:
                replication_data = ReplicationData(initialize=False).set_state(replication_data)
            except:
                return calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST)

        if not isinstance(replication_data, ReplicationData):
            return calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST)

        replication_data.leader_node_id = self.node.id
        self.managed_replications[replication_data.id] = replication_data
        self.node.storage.set_replication_data(replication_data, cb=None)
        if status is None:
            replication_data.status = REPLICATION_STATUS.READY
        else:
            replication_data.status = status
        #TODO trigger replication loop
        return calvinresponse.CalvinResponse(calvinresponse.OK)

    def remove_replication_leader(self, replication_id):
        # TODO for final removal, update registry
        try:
            rd = self.managed_replications.pop(replication_id)
            self.node.storage.delete_replication_data(replication_id)
            return rd
        except:
            _log.exception("remove_replication_leader %s" % replication_id)
            return None

    def destroy_replication_leader(self, replication_id, cb=None):
        _log.debug("destroy_replication_leader %s" % replication_id)
        if replication_id in self.managed_replications.keys():
            _log.debug("destroy_replication_leader %s" % replication_id)
            self.remove_replication_leader(replication_id)
            if cb:
                cb(status=calvinresponse.CalvinResponse(calvinresponse.OK))
            return calvinresponse.CalvinResponse(calvinresponse.OK)
        # Remote leader
        def _leader_node_cb(key, value):
            # Tell leader to be destroyed
            _log.debug("destroy_replication_leader _leader_node_cb %s" % replication_id)
            try:
                self.node.proto.leader_elected(peer_node_id=value['leader_node_id'], leader_type="replication", cmd="destroy", 
                                                data=replication_id, callback=cb)
            except:
                _log.exception("fail destroy_replication_leader _leader_node_cb %s" % replication_id)
                if cb:
                    cb(status=calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND))
        # Find leader
        self.node.storage.get_replication_data(replication_id, cb=_leader_node_cb)
        return calvinresponse.CalvinResponse(calvinresponse.ACCEPTED)

    #
    # Replicate
    #
    def replicate_by_requirements(self, replication_data, callback=None):
        """ Update requirements and trigger a replication """
        if replication_data.status != REPLICATION_STATUS.READY:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.SERVICE_UNAVAILABLE))
            return
        replication_data.status = REPLICATION_STATUS.REPLICATING
        replication_data._replicate_callback = callback
        req = replication_data.requirements
        # Initiate any scaling specific actions
        req_operations[req['op']].initiate(self.node, replication_data, **req['kwargs'])
        r = ReqMatch(self.node,
                     callback=CalvinCB(self._update_requirements_placements, replication_data=replication_data),
                     replace_infinite=True)
        r.match_actor_registry(replication_data.original_actor_id)
        _log.analyze(self.node.id, "+ END", {'replication_data_id': replication_data.id})

    def _update_requirements_placements(self, replication_data, possible_placements, status=None):
        _log.analyze(self.node.id, "+ BEGIN", {'possible_placements':possible_placements, 'status':status}, tb=True)
        # All possible actor placements derived
        if not possible_placements:
            replication_data.status = REPLICATION_STATUS.READY
            if replication_data._replicate_callback:
                replication_data._replicate_callback(status=calvinresponse.CalvinResponse(False))
            return
        # Select, always a list of node_ids, could be more than one
        req = replication_data.requirements
        selected = req_operations[req['op']].select(self.node, replication_data, possible_placements, **req['kwargs'])
        _log.analyze(self.node.id, "+", {'possible_placements': possible_placements, 'selected': selected})
        if not selected:
            replication_data.status = REPLICATION_STATUS.READY
            if replication_data._replicate_callback:
                replication_data._replicate_callback(status=calvinresponse.CalvinResponse(False))
            return
        # FIXME create as many replicas as nodes in list (would need to serialize)
        self.replicate(replication_data.id, selected[0], callback=replication_data._replicate_callback)

    def replicate_by_known_placement(self, replication_data, callback=None):
        """ Trigger a replication """
        if replication_data.status != REPLICATION_STATUS.READY:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.SERVICE_UNAVAILABLE))
            return
        replication_data.status = REPLICATION_STATUS.REPLICATING
        replication_data._replicate_callback = callback
        # Select, always a list of node_ids, could be more than one
        req = replication_data.requirements
        selected = req_operations[req['op']].select(self.node, replication_data, set([]), **req['kwargs'])
        _log.analyze(self.node.id, "+", {'selected': selected})
        if not selected:
            replication_data.status = REPLICATION_STATUS.READY
            if replication_data._replicate_callback:
                replication_data._replicate_callback(status=calvinresponse.CalvinResponse(False))
            return
        self.replicate(replication_data.id, selected[0], callback=replication_data._replicate_callback)
        _log.analyze(self.node.id, "+ END", {'replication_data_id': replication_data.id})

    def replicate(self, replication_id, dst_node_id, callback):
        """ Can't be called directly, only via replicate_by_requirements
            Will perform the actual replication.
        """
        try:
            replication_data = self.managed_replications[replication_id]
        except:
            if callback:
                callback(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        _log.analyze(self.node.id, "+", {'replication_id': replication_id, 'dst_node_id': dst_node_id})
        
        # TODO make name a property that combine name and counter in actor
        new_id = uuid("ACTOR")
        # FIXME change this time stuff when changing replication_loop
        replication_data.check_instances = time.time()
        replication_data.add_replica(new_id)
        new_name = replication_data.actor_state['private']["_name"] + "/{}".format(replication_data.counter)
        state = copy.deepcopy(replication_data.actor_state)
        state['private']['_name'] = new_name
        state['private']['_id'] = new_id
        state['private']['_replication_id']['index'] = replication_data.counter
        # Remove unneeded port states since will populate the standard private ones
        del state['replication']['inports']
        del state['replication']['outports']
        rep_state = replication_data.actor_state['replication']
        # Need to first build connection_list from previous connections
        connection_list = []
        ports = [p['id'] for p in rep_state['inports'].values() + rep_state['outports'].values()]
        _log.debug("REPLICA CONNECT %s " % ports)

        def _got_port(key, value, port, dir):
            ports.remove(port['id'])
            _log.debug("REPLICA CONNECT got port %s %s" % (port['id'], value))
            if calvinresponse.isnotfailresponse(value) and 'peers' in value:
                new_port_id = uuid("PORT")
                connection_list.extend(
                    [(dst_node_id, new_port_id, self.node.id if p[0] == 'local' else p[0], p[1]) for p in value['peers']])
                state['private'][dir + 'ports'][port['name']] = copy.deepcopy(port)
                state['private'][dir + 'ports'][port['name']]['id'] = new_port_id
            else:
                # TODO Don't know how to handle this, retry? Why would the original port be gone from registry?
                # Potentially when destroying application while we replicate, seems OK to ignore
                _log.warning("During replication failed to find original port in repository")
            if not ports:
                # Got all responses
                self._replicate_cont(replication_data, state, connection_list, dst_node_id, callback=callback)

        for port in rep_state['inports'].values():
            self.node.storage.get_port(port['id'], cb=CalvinCB(_got_port, port=port, dir="in"))
        for port in rep_state['outports'].values():
            self.node.storage.get_port(port['id'], cb=CalvinCB(_got_port, port=port, dir="out"))

    def _replicate_cont(self, replication_data, state, connection_list, dst_node_id, callback):
        cb_status = CalvinCB(self._replication_status_cb, replication_data=replication_data, cb=callback)
        actor_type = replication_data.actor_state['replication']['_type']
        new_id = state['private']['_id']
        if dst_node_id == self.node.id:
            self.node.am.new_from_migration(
                actor_type, state=state, connection_list=connection_list, callback=CalvinCB(
                    self._replicated,
                    replication_id=replication_data.id,
                    actor_id=new_id, callback=cb_status, master_id=replication_data.original_actor_id, dst_node_id=dst_node_id))
        else:
            self.node.proto.actor_new(
                dst_node_id, CalvinCB(self._replicated, replication_id=replication_data.id,
                                         actor_id=new_id, callback=cb_status, master_id=replication_data.original_actor_id,
                                         dst_node_id=dst_node_id),
                actor_type, state, None, connection_list=connection_list)

    def _replicated(self, status, replication_id=None, actor_id=None, callback=None, master_id=None, dst_node_id=None):
        _log.analyze(self.node.id, "+", {'status': status, 'replication_id': replication_id, 'actor_id': actor_id})
        if status:
            # TODO add callback for storing
            self.node.storage.add_replica(replication_id, actor_id, dst_node_id)
            self.node.control.log_actor_replicate(
                actor_id=master_id, replica_actor_id=actor_id,
                replication_id=replication_id, dest_node_id=dst_node_id)
        if callback:
            status.data = {'actor_id': actor_id, 'replication_id': replication_id}
            callback(status)

    def connect_verification(self, actor_id, port_id, peer_port_id, peer_node_id):
        # FIXME This need to be solved
        return
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

    def dereplicate(self, replication_id, callback, exhaust=False):
        _log.analyze(self.node.id, "+", {'replication_id': replication_id, 'exhaust': exhaust})
        terminate = DISCONNECT.EXHAUST if exhaust else DISCONNECT.TERMINATE
        try:
            replication_data = self.managed_replications[replication_id]
        except:
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
        # FIXME change this time stuff when changing replication_loop
        replication_data.check_instances = time.time()
        if last_replica_id in self.node.am.actors:
            self.node.am.destroy_with_disconnect(last_replica_id, terminate=terminate,
                callback=CalvinCB(self._dereplicated, replication_data=replication_data,
                                    last_replica_id=last_replica_id, 
                                    node_id=self.node.id, cb=cb_status))
        else:
            self.node.storage.get_actor(last_replica_id,
                CalvinCB(func=self._dereplicate_actor_cb,
                            replication_data=replication_data, terminate=terminate, cb=cb_status))

    def _dereplicate_actor_cb(self, key, value, replication_data, terminate, cb):
        """ Get actor callback """
        _log.analyze(self.node.id, "+", {'actor_id': key, 'value': value})
        if calvinresponse.isnotfailresponse(value) and 'node_id' in value:
            # Use app destroy since it can remotely destroy actors
            self.node.proto.app_destroy(value['node_id'],
                CalvinCB(self._dereplicated, replication_data=replication_data, last_replica_id=key, 
                            node_id=value['node_id'], cb=cb),
                None, [key], disconnect=terminate, replication_id=replication_data.id)
        else:
            # FIXME Should do retries
            if cb:
                cb(calvinresponse.CalvinResponse(False))

    def _dereplicated(self, status, replication_data, last_replica_id, node_id, cb):
        if status:
            # TODO add callback for storing
            self.node.storage.remove_replica(replication_data.id, last_replica_id)
            if node_id == self.node.id:
                self.node.storage.remove_replica_node(replication_data.id, last_replica_id)
            self.node.control.log_actor_dereplicate(
                actor_id=replication_data.original_actor_id, replica_actor_id=last_replica_id,
                replication_id=replication_data.id)
        if cb:
            status.data = {'actor_id': last_replica_id}
            cb(status)

    def _replication_status_cb(self, status, replication_data, cb):
        replication_data.status = REPLICATION_STATUS.READY
        if cb:
            cb(status)
        req = replication_data.requirements
        if req and req_operations[req['op']].direct_replication(self.node,
                                                                replication_data=replication_data, **req['kwargs']):
            # More replicas should be created directly trigger scheduler
            self.node.sched.replication_direct(replication_id=replication_data.id)

    #
    # Terminate specific replica
    #

    def terminate(self, actor_id, terminate=DISCONNECT.TERMINATE, callback=None):
        try:
            replication_data = self.node.am.actors[actor_id]._replication_data
        except:
            if callback:
                callback(status=calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST))
            return
        replication_data._is_terminating = True
        self.node.storage.remove_replica(replication_data.id, actor_id)
        self.node.storage.remove_replica_node(replication_data.id, actor_id)
        self.node.control.log_actor_dereplicate(
                actor_id=replication_data.master, replica_actor_id=actor_id,
                replication_id=replication_data.id)
        self.node.am.destroy_with_disconnect(actor_id, terminate=terminate,
            callback=callback)

    #
    # Requirement controlled replication
    #

    def replication_loop(self):
        _log.debug("REPLICATION LOOP")
        if self.node.quitting:
            return
        for replication_data in self.managed_replications.values():
            _log.debug("REPLICATION LOOP %s %s" % (replication_data.id, REPLICATION_STATUS.reverse_mapping[replication_data.status]))
            if replication_data.status != REPLICATION_STATUS.READY:
                continue
            try:
                req = replication_data.requirements
                if not req:
                    continue
                pre_check = req_operations[req['op']].pre_check(self.node,
                                replication_data=replication_data, **req['kwargs'])
            except:
                _log.exception("Pre check exception")
                pre_check = PRE_CHECK.NO_OPERATION
            if pre_check == PRE_CHECK.SCALE_OUT:
                _log.info("Auto-replicate")
                self.replicate_by_requirements(replication_data, 
                    CalvinCB(self._replication_loop_log_cb, replication_id=replication_data.id))
            if pre_check == PRE_CHECK.SCALE_OUT_KNOWN:
                _log.info("Auto-replicate known")
                self.replicate_by_known_placement(replication_data, 
                    CalvinCB(self._replication_loop_log_cb, replication_id=replication_data.id))
            elif pre_check == PRE_CHECK.SCALE_IN:
                _log.info("Auto-dereplicate")
                self.dereplicate(replication_data.id, CalvinCB(self._replication_loop_log_cb, replication_id=replication_data.id), exhaust=True)
            # elif pre_check == PRE_CHECK.NO_OPERATION:
            #     if not hasattr(actor._replication_data, "check_instances"):
            #         actor._replication_data.check_instances = time.time()
            #     t = time.time()
            #     if t > (actor._replication_data.check_instances + 2.0):
            #         actor._replication_data.check_instances = t
            #         self.node.storage.get_replica(actor._replication_data.id, CalvinCB(self._current_actors_cb, actor=actor))
        return
        
        ######################################################
        
        replicate = []
        dereplicate = []
        no_op = []
        for actor in self.list_master_actors():
            if actor._replication_data.status != REPLICATION_STATUS.READY:
                continue
            if actor._migrating_to is not None:
                continue
            if not actor.enabled():
                continue
            try:
                req = actor._replication_data.requirements
                if not req:
                    continue
                pre_check = req_operations[req['op']].pre_check(self.node, actor_id=actor.id,
                                        component=actor.component_members(), **req['kwargs'])
            except:
                _log.exception("Pre check exception")
                pre_check = PRE_CHECK.NO_OPERATION
            if pre_check == PRE_CHECK.SCALE_OUT:
                 replicate.append(actor)
            elif pre_check == PRE_CHECK.SCALE_IN:
                 dereplicate.append(actor)
            elif pre_check == PRE_CHECK.NO_OPERATION:
                 no_op.append(actor)
        for actor in replicate:
            _log.info("Auto-replicate")
            self.replicate_by_requirements(actor, CalvinCB(self._replication_loop_log_cb, actor_id=actor.id))
        for actor in dereplicate:
            _log.info("Auto-dereplicate")
            self.dereplicate(actor.id, CalvinCB(self._replication_loop_log_cb, actor_id=actor.id), exhaust=True)
        for actor in no_op:
            if not hasattr(actor._replication_data, "check_instances"):
                actor._replication_data.check_instances = time.time()
            t = time.time()
            if t > (actor._replication_data.check_instances + 2.0):
                actor._replication_data.check_instances = t
                self.node.storage.get_replica(actor._replication_data.id, CalvinCB(self._current_actors_cb, actor=actor))

    def _current_actors_cb(self, value, actor):
        collect_actors = [] if calvinresponse.isfailresponse(value) else value
        missing = set(actor._replication_data.instances) - set(collect_actors + [actor.id])
        for actor_id in missing:
            actor._replication_data.instances.remove(actor_id)

    def _replication_loop_log_cb(self, status, replication_id):
        _log.info("Auto-(de)replicated %s: %s" % (replication_id, str(status)))

