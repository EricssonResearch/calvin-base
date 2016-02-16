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

from calvin.utilities.calvinlogger import get_logger
import calvin.utilities.calvinresponse as response
from calvin.actor.actor_factory import ActorFactory
from calvin.actor.actor import ShadowActor
from calvin.actor.connection_handler import ConnectionHandler
from calvin.actor.requirements import ActorRequirements
from calvin.runtime.north.migrator import Migrator

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
        self.migrator = Migrator(self.node, self)

    def new(self, actor_type, args, state=None, prev_connections=None, connection_list=None, callback=None,
            signature=None):
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

        a = self._new(actor_type, args, state, signature)
        self.connection_handler.setup_connections(a, prev_connections=prev_connections, connection_list=connection_list)

        if callback:
            callback(status=response.CalvinResponse(True), actor_id=a.id)
        else:
            return a.id

    def _new(self, actor_type, args, state=None, signature=None):
        """
        Instantiate an actor of type 'actor_type'. Parameters are passed in 'args',
        'name' is an optional parameter in 'args', specifying a human readable name.
        Returns actor id on success and raises an exception if anything goes wrong.
        """
        _log.analyze(self.node.id, "+", {'actor_type': actor_type, 'state': state})

        a = self.factory.create_actor(actor_type=actor_type, state=state, args=args, signature=signature)
        self.node.control.log_actor_new(a.id, a.name, actor_type, isinstance(a, ShadowActor))
        self.actors[a.id] = a

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
        requirements = ActorRequirements(self.node, self, requirements, actor_id)
        requirements.fulfill(self.actors, extend, move, callback)

    def migrate(self, actor_id, node_id, callback=None):
        """ Migrate an actor actor_id to peer node node_id """
        self.migrator.migrate_actor(actor_id, node_id, callback)

    def peernew_to_local_cb(self, reply, **kwargs):
        if kwargs['actor_id'] == reply:
            # Managed to setup since new returned same actor id
            self.node.set_local_reply(kwargs['lmsg_id'], "OK")
        else:
            # Just pass on new cmd reply if it failed
            self.node.set_local_reply(kwargs['lmsg_id'], reply)

    def connections(self, actor_id):
        if actor_id not in self.actors:
            return []

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
        if actor_id not in self.actors:
            msg = "Actor '{}' not found".format(actor_id)
            _log.exception(msg)
            raise Exception(msg)

        return self.actors[actor_id].get_port_state(port_id)

    def actor_type(self, actor_id):
        if actor_id not in self.actors:
            return 'BAD ACTOR'

        return self.actors[actor_id]

    def report(self, actor_id):
        return self.actors.get(actor_id, None).report()

    def enabled_actors(self):
        return [actor for actor in self.actors.values() if actor.enabled()]

    def list_actors(self):
        return self.actors.keys()
