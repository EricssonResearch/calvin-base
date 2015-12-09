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

from calvin.actorstore.store import ActorStore
from calvin.utilities import dynops
from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.utilities.security import Security
from calvin.actor.actor import ShadowActor

_log = get_logger(__name__)


def log_callback(reply, **kwargs):
    if reply:
        _log.info("%s: %s" % (kwargs['prefix'], reply))


class ActorManager(object):

    """docstring for ActorManager"""

    def __init__(self, node):
        super(ActorManager, self).__init__()
        self.actors = {}
        self.node = node

    def _actor_not_found(self, actor_id):
        _log.exception("Actor '{}' not found".format(actor_id))
        raise Exception("Actor '{}' not found".format(actor_id))

    def new(self, actor_type, args, state=None, prev_connections=None, connection_list=None, callback=None,
            signature=None, credentials=None):
        """
        Instantiate an actor of type 'actor_type'. Parameters are passed in 'args',
        'name' is an optional parameter in 'args', specifying a human readable name.
        Returns actor id on success and raises an exception if anything goes wrong.
        Optionally applies a serialized state to the actor, the supplied args are ignored and args from state
        is used instead.
        Optionally reconnecting the ports, using either
          1) an unmodified connections structure obtained by the connections command supplied as
             prev_connections or,
          2) a mangled list of tuples with (in_node_id, in_port_id, out_node_id, out_port_id) supplied as
             connection_list
        """
        _log.debug("class: %s args: %s state: %s, signature: %s" % (actor_type, args, state, signature))
        _log.analyze(self.node.id, "+", {'actor_type': actor_type, 'state': state})

        try:
            if state:
                a = self._new_from_state(actor_type, state)
            else:
                a = self._new(actor_type, args, credentials)
        except Exception as e:
            _log.exception("Actor creation failed")
            raise(e)

        # Store the actor signature to enable GlobalStore lookup
        a.signature_set(signature)

        self.actors[a.id] = a

        self.node.storage.add_actor(a, self.node.id)

        if prev_connections:
            # Convert prev_connections to connection_list format
            connection_list = self._prev_connections_to_connection_list(prev_connections)

        self.node.control.log_actor_new(a.id, a.name, actor_type, isinstance(a, ShadowActor))

        if connection_list:
            # Migrated actor
            self.connect(a.id, connection_list, callback=callback)
        else:
            # Nothing to connect then we are OK
            if callback:
                callback(status=response.CalvinResponse(True), actor_id=a.id)
            else:
                return a.id

    def _new_actor(self, actor_type, actor_id=None, credentials=None):
        """Return a 'bare' actor of actor_type, raises an exception on failure."""
        if credentials is not None:
            sec = Security()
            sec.set_principal(credentials)
            sec.authenticate_principal()
        else:
            sec = None
        (found, is_primitive, class_) = ActorStore(security=sec).lookup(actor_type)
        if not found:
            # Here assume a primtive actor, now become shadow actor
            _log.analyze(self.node.id, "+ NOT FOUND CREATE SHADOW ACTOR", {'class': class_})
            found = True
            is_primitive = True
            class_ = ShadowActor
        if not found or not is_primitive:
            _log.error("Requested actor %s is not available" % (actor_type))
            raise Exception("ERROR_NOT_FOUND")
        try:
            # Create a 'bare' instance of the actor
            a = class_(actor_type, actor_id=actor_id)
        except Exception as e:
            _log.exception("")
            _log.error("The actor %s(%s) can't be instantiated." % (actor_type, class_.__init__))
            raise(e)
        try:
            a.set_credentials(credentials, security=sec)
            a._calvinsys = self.node.calvinsys()
            a.check_requirements()
        except Exception as e:
            _log.exception("Catched new from state")
            _log.analyze(self.node.id, "+ FAILED REQS CREATE SHADOW ACTOR", {'class': class_})
            a = ShadowActor(actor_type, actor_id=actor_id)
            a.set_credentials(credentials, security=sec)
            a._calvinsys = self.node.calvinsys()
        return a


    def _new(self, actor_type, args, credentials=None):
        """Return an initialized actor in PENDING state, raises an exception on failure."""
        try:
            a = self._new_actor(actor_type, credentials=credentials)
            # Now that required APIs are attached we can call init() which may use the APIs
            human_readable_name = args.pop('name', '')
            a.name = human_readable_name
            self.node.pm.add_ports_of_actor(a)
            a.init(**args)
            a.setup_complete()
        except Exception as e:
            _log.exception("_new")
            raise(e)
        return a


    def _new_from_state(self, actor_type, state):
        """Return a restored actor in PENDING state, raises an exception on failure."""
        try:
            _log.analyze(self.node.id, "+", state)
            credentials = state.pop('credentials', None)
            try:
                state['_managed'].remove('credentials')
            except:
                pass
            a = self._new_actor(actor_type, actor_id=state['id'], credentials=credentials)
            if '_shadow_args' in state:
                # We were a shadow, do a full init
                args = state.pop('_shadow_args')
                state['_managed'].remove('_shadow_args')
                a.init(**args)
                # If still shadow don't call did_migrate
                did_migrate = isinstance(a, ShadowActor)
            else:
                did_migrate = True
            # Always do a set_state for the port's state
            a._set_state(state)
            self.node.pm.add_ports_of_actor(a)
            if did_migrate:
                a.did_migrate()
            a.setup_complete()
        except Exception as e:
            _log.exception("Catched new from state %s %s" % (a, dir(a)))
            raise(e)
        return a

    def destroy(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        # @TOOD - check order here
        self.node.metering.remove_actor_info(actor_id)
        a = self.actors[actor_id]
        a.will_end()
        self.node.pm.remove_ports_of_actor(a)
        # @TOOD - insert callback here
        self.node.storage.delete_actor(actor_id)
        del self.actors[actor_id]
        self.node.control.log_actor_destroy(a.id)

    # DEPRECATED: Enabling of an actor is dependent on wether it's connected or not
    def enable(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        self.actors[actor_id].enable()

    # DEPRECATED: Disabling of an actor is dependent on wether it's connected or not
    def disable(self, actor_id):
        if actor_id not in self.actors:
            _log.info("!!!FAILED to disable %s", actor_id)
            self._actor_not_found(actor_id)

        self.actors[actor_id].disable()

    def update_requirements(self, actor_id, requirements, extend=False, move=False, callback=None):
        """ Update requirements and trigger a potential migration """
        if actor_id not in self.actors:
            # Can only migrate actors from our node
            _log.analyze(self.node.id, "+ NO ACTOR", {'actor_id': actor_id})
            if callback:
                callback(status=response.CalvinResponse(False))
            return
        if not isinstance(requirements, (list, tuple)):
            # requirements need to be list
            _log.analyze(self.node.id, "+ NO REQ LIST", {'actor_id': actor_id})
            if callback:
                callback(status=response.CalvinResponse(response.BAD_REQUEST))
            return
        actor = self.actors[actor_id]
        actor._collect_placement_counter = 0
        actor._collect_placement_last_value = 0
        actor._collect_placement_cb = None
        actor.requirements_add(requirements, extend)
        node_iter = self.node.app_manager.actor_requirements(None, actor_id)
        possible_placements = set([])
        done = [False]
        node_iter.set_cb(self._update_requirements_placements, node_iter, actor_id, possible_placements,
                         move=move, cb=callback, done=done)
        _log.analyze(self.node.id, "+ CALL CB", {'actor_id': actor_id, 'node_iter': str(node_iter)})
        # Must call it since the triggers might already have released before cb set
        self._update_requirements_placements(node_iter, actor_id, possible_placements,
                                 move=move, cb=callback, done=done)
        _log.analyze(self.node.id, "+ END", {'actor_id': actor_id, 'node_iter': str(node_iter)})

    def _update_requirements_placements(self, node_iter, actor_id, possible_placements, done, move=False, cb=None):
        _log.analyze(self.node.id, "+ BEGIN", {}, tb=True)
        actor = self.actors[actor_id]
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
                                                    node_iter, actor_id, possible_placements, done=done,
                                                     move=move, cb=cb)
            return
        except StopIteration:
            # all possible actor placements derived
            _log.analyze(self.node.id, "+ ALL", {})
            done[0] = True
            if move and len(possible_placements)>1:
                possible_placements.discard(self.node.id)
            if not possible_placements:
                if cb:
                    cb(status=response.CalvinResponse(False))
                return
            if self.node.id in possible_placements:
                # Actor could stay, then do that
                if cb:
                    cb(status=response.CalvinResponse(True))
                return
            # TODO do a better selection between possible nodes
            self.migrate(actor_id, possible_placements.pop(), callback=cb)
            _log.analyze(self.node.id, "+ END", {})
        except:
            _log.exception("actormanager:_update_requirements_placements")

    def migrate(self, actor_id, node_id, callback=None):
        """ Migrate an actor actor_id to peer node node_id """
        if actor_id not in self.actors:
            # Can only migrate actors from our node
            if callback:
                callback(status=response.CalvinResponse(False))
            return
        if node_id == self.node.id:
            # No need to migrate to ourself
            if callback:
                callback(status=response.CalvinResponse(True))
            return

        actor = self.actors[actor_id]
        actor._migrating_to = node_id
        actor.will_migrate()
        actor_type = actor._type
        ports = actor.connections(self.node.id)
        # Disconnect ports and continue in _migrate_disconnect
        self.node.pm.disconnect(callback=CalvinCB(self._migrate_disconnected,
                                                  actor=actor,
                                                  actor_type=actor_type,
                                                  ports=ports,
                                                  node_id=node_id,
                                                  callback=callback),
                                actor_id=actor_id)
        self.node.control.log_actor_migrate(actor_id, node_id)

    def _migrate_disconnected(self, actor, actor_type, ports, node_id, status, callback = None, **state):
        """ Actor disconnected, continue migration """
        if status:
            state = actor.state()
            self.destroy(actor.id)
            self.node.proto.actor_new(node_id, callback, actor_type, state, ports)
        else:
            # FIXME handle errors!!!
            if callback:
                callback(status=status)

    def peernew_to_local_cb(self, reply, **kwargs):
        if kwargs['actor_id'] == reply:
            # Managed to setup since new returned same actor id
            self.node.set_local_reply(kwargs['lmsg_id'], "OK")
        else:
            # Just pass on new cmd reply if it failed
            self.node.set_local_reply(kwargs['lmsg_id'], reply)

    def _prev_connections_to_connection_list(self, prev_connections):
        """Convert prev_connection format to connection_list format"""
        cl = []
        for in_port_id, out_id in prev_connections['inports'].iteritems():
            cl.append((self.node.id, in_port_id, out_id[0], out_id[1]))
        for out_port_id, in_list in prev_connections['outports'].iteritems():
            for in_id in in_list:
                cl.append((self.node.id, out_port_id, in_id[0], in_id[1]))
        return cl

    def connect(self, actor_id, connection_list, callback=None):
        """
        Reconnecting the ports can be done using a connection_list
        of tuples (node_id i.e. our id, port_id, peer_node_id, peer_port_id)
        """
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        peer_port_ids = [c[3] for c in connection_list]

        for node_id, port_id, peer_node_id, peer_port_id in connection_list:
            self.node.pm.connect(port_id=port_id,
                                 peer_node_id=peer_node_id,
                                 peer_port_id=peer_port_id,
                                 callback=CalvinCB(self._actor_connected,
                                                   peer_port_id=peer_port_id,
                                                   actor_id=actor_id,
                                                   peer_port_ids=peer_port_ids,
                                                   _callback=callback))

    def _actor_connected(self, status, peer_port_id, actor_id, peer_port_ids, _callback, **kwargs):
        """ Get called for each of the actor's ports when connecting, but callback should only be called once
            status: success or not
            _callback: original callback
            peer_port_ids: list of port ids kept in context between calls when *changed* by this function,
                           do not replace it
        """
        # Send negative response if not already done it
        if not status and peer_port_ids:
            if _callback:
                del peer_port_ids[:]
                _callback(status=response.CalvinResponse(False), actor_id=actor_id)
        if peer_port_id in peer_port_ids:
            # Remove this port from list
            peer_port_ids.remove(peer_port_id)
            # If all ports done send OK
            if not peer_port_ids:
                if _callback:
                    _callback(status=response.CalvinResponse(True), actor_id=actor_id)

    def connections(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        return self.actors[actor_id].connections(self.node.id)

    def dump(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        actor = self.actors[actor_id]
        _log.debug("-----------")
        _log.debug(actor)
        _log.debug("-----------")

    def set_port_property(self, actor_id, port_type, port_name, port_property, value):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)
        actor = self.actors[actor_id]
        success = actor.set_port_property(port_type, port_name, port_property, value)
        return 'OK' if success else 'FAILURE'

    def get_port_state(self, actor_id, port_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        actor = self.actors[actor_id]
        for port in actor.inports.values():
            if port.id == port_id:
                return port.fifo._state()
        for port in actor.outports.values():
            if port.id == port_id:
                return port.fifo._state()
        raise Exception("No port with id: %s" % port_id)

    def actor_type(self, actor_id):
        actor = self.actors.get(actor_id, None)
        return actor._type if actor else 'BAD ACTOR'

    def report(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        return self.actors[actor_id].report()

    def enabled_actors(self):
        return [actor for actor in self.actors.values() if actor.enabled()]

    def list_actors(self):
        return self.actors.keys()
