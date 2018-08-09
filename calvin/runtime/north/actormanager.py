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

import random
from calvin.actorstore.store import ActorStore
from calvin.utilities import dynops
from calvin.utilities.requirement_matching import ReqMatch
from calvin.runtime.south.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.utilities.security import Security, security_enabled
from calvin.actor.actor import ShadowActor
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib


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
            signature=None, actor_def=None, security=None, access_decision=None, shadow_actor=False,
            port_properties=None):
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
        _log.debug("class: %s args: %s state: %s, signature: %s\nprev_connections: %s connection_list:%s" %
                    (actor_type, args, state, signature, prev_connections, connection_list))
        _log.analyze(self.node.id, "+", {'actor_type': actor_type, 'state': state})

        try:
            if state:
                a = self._new_from_state(actor_type, state, actor_def, security, access_decision, shadow_actor)
            else:
                a = self._new(actor_type, args, actor_def, security, access_decision, shadow_actor, port_properties)
        except Exception as e:
            _log.exception("Actor creation failed")
            raise(e)

        # Store the actor signature to enable GlobalStore lookup
        a.signature_set(signature)

        self.actors[a.id] = a

        a._migration_connected = False

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
            a._migration_connected = True
            if callback:
                callback(status=response.CalvinResponse(True), actor_id=a.id)
            else:
                return a.id

    def _new_actor(self, actor_type, class_=None, actor_id=None, security=None, access_decision=None, shadow_actor=False):
        """Return a 'bare' actor of actor_type, raises an exception on failure."""
        if security_enabled() and not access_decision:
            _log.debug("Security policy check for actor failed, access_decision={}".format(access_decision))
            shadow_actor = True
        if shadow_actor:
            class_ = ShadowActor
        if class_ is None:
            try:
                class_, signer = self.lookup_and_verify(actor_type, security)
            except Exception:
                class_ = ShadowActor
        try:
            # Create a 'bare' instance of the actor
            a = class_(actor_type, actor_id=actor_id, security=security)
        except Exception as e:
            _log.error("The actor %s(%s) can't be instantiated." % (actor_type, class_.__init__))
            raise(e)
        if isinstance(access_decision, tuple):
            # Authorization checks needed if access_decision is a tuple.
            a.set_authorization_checks(access_decision[1])
        return a

    def _new(self, actor_type, args, actor_def=None, security=None, access_decision=None, shadow_actor=False,
             port_properties=None):
        """Return an initialized actor in PENDING state, raises an exception on failure."""
        try:
            a = self._new_actor(actor_type, actor_def, security=security,
                                access_decision=access_decision, shadow_actor=shadow_actor)
            # Now that required APIs are attached we can call init() which may use the APIs
            human_readable_name = args.pop('name', '')
            a.name = human_readable_name
            self.node.pm.add_ports_of_actor(a)
            self.node.pm.set_script_port_property(a.id, port_properties)
            a.init(**args)
            a.setup_complete()
        except Exception as e:
            _log.exception("_new")
            raise(e)
        return a

    def new_from_migration(self, actor_type, state, prev_connections=None, connection_list=None, callback=None):
        """Instantiate an actor of type 'actor_type' and apply the 'state' to the actor."""
        try:
            _log.analyze(self.node.id, "+", state)
            subject_attributes = state['security'].pop('_subject_attributes', None)
            migration_info = state['private'].pop('_migration_info', None)
            try:
                state['security'].remove('_subject_attributes')
                state['private'].remove('_migration_info')
            except:
                pass
            if security_enabled():
                security = Security(self.node)
                security.set_subject_attributes(subject_attributes)
            else:
                security = None
            actor_def, signer = self.lookup_and_verify(actor_type, security)
            requirements = actor_def.requires if hasattr(actor_def, "requires") else []
            self.check_requirements_and_sec_policy(requirements, security, state['private']['_id'],
                                                   signer, migration_info,
                                                   CalvinCB(self.new, actor_type, None,
                                                            state, prev_connections=prev_connections,
                                                            connection_list=connection_list,
                                                            callback=callback,
                                                            actor_def=actor_def,
                                                            security=security))
        except Exception:
            # Still want to create shadow actor.
            self.new(actor_type, None, state, prev_connections=prev_connections,
                    connection_list=connection_list, callback=callback, shadow_actor=True)

    def _new_from_state(self, actor_type, state, actor_def, security,
                             access_decision=None, shadow_actor=False):
        """Return a restored actor in PENDING state, raises an exception on failure."""
        try:
            a = self._new_actor(actor_type, actor_def, actor_id=state['private']['_id'], security=security,
                                access_decision=access_decision, shadow_actor=shadow_actor)
            if '_shadow_args' in state['managed']:
                # We were a shadow, do a full init
                args = state['managed'].pop('_shadow_args')
                a.init(**args)
                # If still shadow don't call did_replicate even when replication
                did_replicate = (not isinstance(a, ShadowActor)) and 'replication' in state
                # If still shadow don't call did_migrate also skip if replication
                did_migrate = isinstance(a, ShadowActor) and not did_replicate
            else:
                did_migrate = True
                did_replicate = False
            # Always do a set_state for the port's state
            a.deserialize(state)
            self.node.pm.add_ports_of_actor(a)
            if did_migrate:
                a.did_migrate()
            if did_replicate:
                try:
                    a.did_replicate(state['private']['_replication_id']['index'])
                except:
                    _log.exception("did_replicate failed for actor %s" % a.name)
            a.setup_complete()
        except Exception as e:
            _log.exception("Catched new from state %s %s" % (a, dir(a)))
            raise(e)
        return a

    def destroy(self, actor_id, temporary=False):
        """ Destroy an actor, temporary should be True when migrating """
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        # @TOOD - check order here
        a = self.actors[actor_id]
        a._will_end()
        port_ids = self.node.pm.remove_ports_of_actor(a)
        # @TOOD - insert callback here
        if not temporary:
            self.node.storage.delete_actor(actor_id, cb=self._destroy_log_cb)
            for port_id in port_ids:
                self.node.storage.delete_port(port_id)
            self.node.control.log_actor_destroy(a.id)
        del self.actors[actor_id]

    def _destroy_log_cb(self, key, value):
        _log.debug("DESTROY CB %s %s %s" % (key, value, self.node.id))

    def destroy_with_disconnect(self, actor_id, terminate=DISCONNECT.TERMINATE, callback=None):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)
        if terminate == DISCONNECT.EXHAUST:
            actor = self.actors[actor_id]
            actor.exhaust(CalvinCB(self._destroy_with_disconnect_exhausted, actor_id=actor_id, terminate=terminate, callback=callback))
            # Exhaust first disconnects all inports then all outports after inports exhausted
            self.node.pm.disconnect(callback=CalvinCB(self._destroy_with_disconnect_in_cb, terminate=terminate,
                                                      callback=callback),
                                    actor_id=actor_id, port_dir="in", terminate=terminate)
        else:
            self.node.pm.disconnect(callback=CalvinCB(self._destroy_with_disconnect_cb,
                                                      callback=callback),
                                    actor_id=actor_id, terminate=terminate)

    def _destroy_with_disconnect_exhausted(self, status, actor_id, terminate, callback=None):
        # FIXME handled failed exhaust when we do return anything but OK
        _log.debug("Disconnected and exhausted all inports %s %s" % (actor_id, str(status)))
        self.node.pm.disconnect(callback=CalvinCB(self._destroy_with_disconnect_cb,
                                                  callback=callback),
                                actor_id=actor_id, port_dir="out", terminate=terminate)

    def _destroy_with_disconnect_in_cb(self, status, actor_id, terminate, callback=None, **kwargs):
        # FIXME handle failed disconnect
        _log.debug("Disconnected all inports %s %s" % (actor_id, str(status)))

    def _destroy_with_disconnect_cb(self, status, actor_id, callback=None, **kwargs):
        _log.debug("Disconnected all ports %s %s" % (actor_id, str(status)))
        self.destroy(actor_id)
        if callback:
            callback(status=status)

    # DEPRECATED: Enabling of an actor is dependent on whether it's connected or not
    def enable(self, actor_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        self.actors[actor_id].enable()

    # DEPRECATED: Disabling of an actor is dependent on whether it's connected or not
    def disable(self, actor_id):
        if actor_id not in self.actors:
            _log.info("!!!FAILED to disable %s", actor_id)
            self._actor_not_found(actor_id)

        self.actors[actor_id].disable()

    def lookup_and_verify(self, actor_type, security=None):
        """Lookup and verify actor in actor store."""
        found, is_primitive, actor_def, signer = ActorStore(security=security).lookup(actor_type)
        if not found or not is_primitive:
            raise Exception("Not known actor type: %s" % actor_type)
        return (actor_def, signer)

    def check_requirements_and_sec_policy(self, requirements, security=None, actor_id=None,
                                          signer=None, decision_from_migration=None, callback=None):
        for req in requirements:
            if not get_calvinsys().has_capability(req) and not get_calvinlib().has_capability(req):
                raise Exception("Actor requires %s" % req)
        if security_enabled():
            # Check if access is permitted for the actor by the security policy.
            # Will continue directly with callback if authorization is not enabled.
            security.check_security_policy(callback, actor_id=actor_id, requires=['runtime'] + requirements,
                                            element_type="actor",
                                            element_value=signer,
                                            decision_from_migration=decision_from_migration)
        else:
            callback()

    def update_requirements(self, actor_id, requirements, extend=False, move=False,
                            authorization_check=False, callback=None):
        """ Update requirements and trigger a potential migration """
        if actor_id not in self.actors:
            # Can only migrate actors from our node
            _log.analyze(self.node.id, "+ NO ACTOR", {'actor_id': actor_id})
            if callback:
                callback(status=response.CalvinResponse(False))
            return
        if not isinstance(requirements, (list, tuple)):
            # Requirements need to be list
            _log.analyze(self.node.id, "+ NO REQ LIST", {'actor_id': actor_id})
            if callback:
                callback(status=response.CalvinResponse(response.BAD_REQUEST))
            return
        actor = self.actors[actor_id]
        actor.requirements_add(requirements, extend)
        self.node.storage.add_actor(actor, self.node.id)  # Update requirements in registry
        r = ReqMatch(self.node,
                     callback=CalvinCB(self._update_requirements_placements, actor_id=actor_id, move=move, cb=callback))
        r.match_for_actor(actor_id)
        _log.analyze(self.node.id, "+ END", {'actor_id': actor_id})

    def _update_requirements_placements(self, actor_id, possible_placements, status=None, move=False, cb=None):
        _log.analyze(self.node.id, "+ BEGIN", {}, tb=True)
        if move and len(possible_placements)>1:
            possible_placements.discard(self.node.id)
        actor = self.actors[actor_id]
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
        # TODO: should also ask authorization server before selecting node to migrate to.
        # Try the possible placements in random order
        pp = list(possible_placements)
        random.shuffle(pp)
        self.robust_migrate(actor_id, pp, callback=cb)
        _log.analyze(self.node.id, "+ END", {})

    def robust_migrate(self, actor_id, node_ids, callback, **kwargs):
        """ Will try to migrate the actor to each of the suggested node_ids (which is modified),
            Optionally kwargs can contain state, actor_type and ports
            If all else fails the state, actor_type and ports will be returned in the callback.
            These could be used by the callback to either try another list of node_ids,
            recreate the actor locally or just ignore.
        """
        if kwargs.get('status', False):
            # Success
            if callback:
                callback(status=kwargs['status'])
            return
        if node_ids:
            node_id = node_ids.pop(0)
        else:
            if callback:
                callback(
                    status=kwargs.get('status', response.CalvinResponse(False)),
                    state=kwargs.get('state', None),
                    actor_type=kwargs.get('actor_type', None),
                    ports=kwargs.get('ports', None))
            return
        if 'state' in kwargs:
            # Retry another node
            self.node.proto.actor_new(
                node_id,
                CalvinCB(self._robust_migrate_cb, actor_id=actor_id, node_ids=node_ids, callback=callback),
                kwargs.get('actor_type', None), kwargs.get('state', None), kwargs.get('ports', None))
        else:
            # Start with standard migration
            self.migrate(actor_id, node_id,
                        CalvinCB(self._robust_migrate_cb, actor_id=actor_id, node_ids=node_ids, callback=callback))

    def _robust_migrate_cb(self, status, actor_id, node_ids, callback, **kwargs):
        # Just for moving status into kwargs, TODO the reply_handler should use kwarg
        kwargs['status'] = status
        self.robust_migrate(actor_id, node_ids, callback, **kwargs)

    def migrate(self, actor_id, node_id, callback=None):
        """ Migrate an actor actor_id to peer node node_id """
        if actor_id not in self.actors:
            # Can only migrate actors from our node
            if callback:
                callback(status=response.CalvinResponse(False))
            return
        actor = self.actors[actor_id]
        if actor._migrating_to is not None:
            # We can't migrate while migrating
            if callback:
                callback(status=response.CalvinResponse(response.BAD_REQUEST))
            return
        if not actor._migration_connected:
            # We can't migrate before finished with setup actor from previous migration
            if callback:
                callback(status=response.CalvinResponse(response.SERVICE_UNAVAILABLE))
            return
        if node_id == self.node.id:
            # No need to migrate to ourself
            if callback:
                callback(status=response.CalvinResponse(True))
            return
        actor._migrating_to = node_id
        actor.will_migrate()
        actor_type = actor._type
        ports = actor.connections(self.node.id)
        # Disconnect ports and continue in _migrate_disconnect
        _log.analyze(self.node.id, "+ PRE DISCONNECT", {'actor_name': actor.name, 'actor_id': actor.id})
        self.node.pm.disconnect(callback=CalvinCB(self._migrate_disconnected,
                                                  actor=actor,
                                                  actor_type=actor_type,
                                                  ports=ports,
                                                  node_id=node_id,
                                                  callback=callback),
                                actor_id=actor_id)
        _log.analyze(self.node.id, "+ POST DISCONNECT", {'actor_name': actor.name, 'actor_id': actor.id})
        self.node.control.log_actor_migrate(actor_id, node_id)

    def _migrate_disconnected(self, actor, actor_type, ports, node_id, status, callback = None, **state):
        """ Actor disconnected, continue migration """
        _log.analyze(self.node.id, "+ DISCONNECTED", {'actor_name': actor.name, 'actor_id': actor.id, 'status': status})
        state = actor.serialize()
        self.destroy(actor.id, temporary=True)
        if status:
            callback = CalvinCB(callback, state=state, ports=ports, actor_type=actor_type)
            self.node.proto.actor_new(node_id, callback, actor_type, state, ports)
        else:
            if callback:
                callback(status=status, state=state, ports=ports, actor_type=actor_type)

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
        for in_port_id, out_list in prev_connections['inports'].iteritems():
            for out_id in out_list:
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
        _log.debug("ACTOR CONNECT BEGIN %s" % actor_id)
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)
        _log.debug("ACTOR CONNECT LIST %s %s\n%s" % (actor_id, self.actors[actor_id]._name, connection_list))
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
        _log.debug("_actor_connected %s %s" % (actor_id, status))
        # Send negative response if not already done it
        if not status and peer_port_ids:
            self.actors[actor_id]._migration_connected = True
            if _callback:
                del peer_port_ids[:]
                _callback(status=response.CalvinResponse(False), actor_id=actor_id)
        if peer_port_id in peer_port_ids:
            # Remove this port from list
            peer_port_ids.remove(peer_port_id)
            # If all ports done send OK
            if not peer_port_ids:
                self.actors[actor_id]._migration_connected = True
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

    def get_port_state(self, actor_id, port_id):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        actor = self.actors[actor_id]
        for port in actor.inports.values():
            if port.id == port_id:
                return port.queue._state()
        for port in actor.outports.values():
            if port.id == port_id:
                return port.queue._state()
        raise Exception("No port with id: %s" % port_id)

    def actor_type(self, actor_id):
        actor = self.actors.get(actor_id, None)
        return actor._type if actor else 'BAD ACTOR'

    def report(self, actor_id, kwargs):
        if actor_id not in self.actors:
            self._actor_not_found(actor_id)

        return self.actors[actor_id].report(**(kwargs if kwargs and isinstance(kwargs, dict) else {}))

    def enabled_actors(self):
        return [actor for actor in self.actors.values() if actor.enabled()]

    def denied_actors(self):
        return [actor for actor in self.actors.values() if actor.denied()]

    def migratable_actors(self):
        return [actor for actor in self.actors.values() if actor.migratable()]

    def list_actors(self):
        return self.actors.keys()
