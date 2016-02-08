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

from calvin.utilities import dynops
from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.utilities.calvinresponse as response
from calvin.actor.actor_factory import ActorFactory
from calvin.actor.actor import ShadowActor
from calvin.actor.connection_handler import ConnectionHandler

_log = get_logger(__name__)


def log_callback(reply, **kwargs):
    if reply:
        _log.info("%s: %s" % (kwargs['prefix'], reply))


class ActorManager(object):

    """docstring for ActorManager"""

    def __init__(self, node, factory=None, connection_handler=None):
        super(ActorManager, self).__init__()
        self.actors = {}
        self.node = node
        self.factory = factory if factory else ActorFactory(node)
        self.connection_handler = connection_handler if connection_handler else ConnectionHandler(node)

    def new(self, actor_type, args, state=None, prev_connections=None, connection_list=None, callback=None,
            signature=None, app_id=None):
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
        a = self._new(actor_type, args, state, signature, app_id)

        self.connection_handler.setup_connections(a, prev_connections=prev_connections, connection_list=connection_list,
                                                  callback=callback)

        if callback:
            callback(status=response.CalvinResponse(True), actor_id=a.id)
        else:
            return a.id

    def _new(self, actor_type, args, state=None, signature=None, app_id=None):
        """
        Instantiate an actor of type 'actor_type'. Parameters are passed in 'args',
        'name' is an optional parameter in 'args', specifying a human readable name.
        Returns actor id on success and raises an exception if anything goes wrong.
        """
        _log.analyze(self.node.id, "+", {'actor_type': actor_type, 'state': state})

        a = self.factory.create_actor(actor_type=actor_type, state=state, args=args, signature=signature, app_id=app_id)
        self.node.control.log_actor_new(a.id, a.name, actor_type, isinstance(a, ShadowActor))
        self.actors[a.id] = a

        return a

    def new_replica(self, actor_type, args, state, prev_connections, app_id, callback):
        """Creates a new replica"""
        _log.debug("Creating new replica of type {}, with args {}, prev_connections {}".format(
            actor_type, args, prev_connections))

        state['id'] = args.pop('id')
        state['name'] = args.pop('name')
        state['set_ports'] = False

        a = self._new(actor_type, args, state, app_id=app_id)

        self.connection_handler.setup_replica_connections(a, state, prev_connections)
        if callback:
            callback(status=response.CalvinResponse(True), actor_id=a.id)

        return a

    def destroy(self, actor_id):
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
        if actor_id in self.actors:
            self.actors[actor_id].enable()

    # DEPRECATED: Disabling of an actor is dependent on wether it's connected or not
    def disable(self, actor_id):
        if actor_id in self.actors:
            self.actors[actor_id].disable()
        else:
            _log.info("!!!FAILED to disable %s", actor_id)

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


    def migrate(self, actor_id, node_id, callback = None):
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
        callback = CalvinCB(self._migrate_disconnected,
                            actor=actor,
                            actor_type=actor_type,
                            ports=ports,
                            node_id=node_id,
                            callback=callback)
        self.node.pm.disconnect(callback=callback, actor_id=actor_id)

    def _migrate_disconnected(self, actor, actor_type, ports, node_id, status, callback=None, **state):
        """ Actor disconnected, continue migration """
        if status:
            state = actor.state()
            self.destroy(actor.id)
            self.node.proto.actor_new(node_id, callback, actor_type, state, ports, app_id=actor.app_id)
        elif callback:  # FIXME handle errors!!!
            callback(status=status)

    def replicate(self, actor_id, node_id, callback=None):
        """Replicate an actor actor_id to peer node node_id """
        if actor_id not in self.actors:
            # Can only replicate actors from our node
            if callback:
                callback(status=response.CalvinResponse(False))
            return

        actor = self.actors[actor_id]
        actor_type = actor._type
        prev_connections = actor.connections(self.node.id)
        prev_connections['port_names'] = actor.port_names()
        prev_connections['outports'] = []  # TODO update when (if) we allow multiple inports
        state = actor.state()

        args = actor.replication_args()
        app = self.node.app_manager.get_actor_app(actor_id)
        app_id = app.id if app else state['app_id']
        if app:
            app.actors[args['id']] = args['name']
            self.node.storage.add_application(app)

        self.node.proto.actor_replication(node_id, callback, actor_type, state, prev_connections, args, app_id)

    def peernew_to_local_cb(self, reply, **kwargs):
        if kwargs['actor_id'] == reply:
            # Managed to setup since new returned same actor id
            self.node.set_local_reply(kwargs['lmsg_id'], "OK")
        else:
            # Just pass on new cmd reply if it failed
            self.node.set_local_reply(kwargs['lmsg_id'], reply)

    def connections(self, actor_id):
        if actor_id not in self.actors:
            return

        return self.connection_handler.connections(self.actors[actor_id])

    def dump(self, actor_id):
        actor = self.actors.get(actor_id, None)
        if not actor:
            raise Exception("Actor '%s' not found" % (actor_id,))
        _log.debug("-----------")
        _log.debug(actor)
        _log.debug("-----------")

    def set_port_property(self, actor_id, port_type, port_name, port_property, value):
        try:
            actor = self.actors[actor_id]
        except Exception as e:
            _log.exception("Actor '%s' not found" % (actor_id,))
            raise e
        success = actor.set_port_property(port_type, port_name, port_property, value)
        return 'OK' if success else 'FAILURE'

    def get_port_state(self, actor_id, port_id):
        try:
            actor = self.actors[actor_id]
        except Exception as e:
            _log.exception("Actor '%s' not found" % (actor_id,))
            raise e

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
        return self.actors.get(actor_id, None).report()

    def enabled_actors(self):
        return [actor for actor in self.actors.values() if actor.enabled()]

    def list_actors(self):
        return self.actors.keys()
