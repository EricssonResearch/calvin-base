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

from calvin.runtime.north.plugins.storage import storage_factory
from calvin.runtime.north.plugins.coders.messages import message_coder_factory
from calvin.runtime.south.plugins.async import async
from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.actor import actorport

_log = calvinlogger.get_logger(__name__)


class Storage(object):

    """
    Storage helper functions.
    All functions in this class should be async and never block.
    """

    def __init__(self):
        self.localstore = {}
        self.started = False        
        self.storage = storage_factory.get("dht") # TODO: read storage type from config?
        self.coder = message_coder_factory.get("json")  # TODO: always json?
        self.flush_delayedcall = None
        self.flush_timout = 1

    def flush_localdata(self):
        """ Write data in localstore to storage
        """
        self.flush_delayedcall = None
        for key in self.localstore:
            self.storage.set(key=key, value=self.localstore[key], cb=CalvinCB(func=self.set_cb, org_key=None, org_value=None, org_cb=None))

    def started_cb(self, *args, **kwargs):
        """ Called when storage has started, flushes localstore
        """
        if args[0] == True:
            self.started = True
            self.flush_localdata()
            if kwargs["org_cb"]:
                kwargs["org_cb"](args[0])

    def start(self, cb=None):
        """ Start storage
        """
        self.storage.start(cb=CalvinCB(self.started_cb, org_cb=cb))

    def stop(self, cb=None):
        """ Stop storage
        """
        if self.started:
            self.storage.stop(cb=cb)
        self.started = False

    def set_cb(self, key, value, org_key, org_value, org_cb):
        """ set callback, on error store in localstore and retry after flush_timout
        """
        if value == True:
            if org_cb:
                org_cb(key=key, value=True)
            if key in self.localstore:
                del self.localstore[key]
        else:
            _log.error("Failed to store %s" % key)
            if org_key and org_value:
                if not org_value is None:
                    self.localstore[key] = org_value
            if org_cb:
                org_cb(key=key, value=False)
            if self.flush_delayedcall is None:
                self.flush_delayedcall = async.DelayedCall(self.flush_timout, self.flush_localdata)
            else:
                self.flush_delayedcall.reset()

    def set(self, prefix, key, value, cb):
        """ Set key: prefix+key value: value
        """
        if value:
            value = self.coder.encode(value)

        if self.started:
            self.storage.set(key=prefix + key, value=value, cb=CalvinCB(func=self.set_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if value:
                self.localstore[prefix + key] = value
            if cb:
                cb(key=key, value=True)

    def get_cb(self, key, value, org_cb, org_key):
        """ get callback
        """
        if value:
            value = self.coder.decode(value)
        org_cb(org_key, value)

    def get(self, prefix, key, cb):
        """ Get value for key: prefix+key, first look in localstore
        """
        if cb:
            if prefix + key in self.localstore:
                value = self.localstore[prefix + key]
                if value:
                    value = self.coder.decode(value)
                cb(key=key, value=value)
            else:
                try:
                    self.storage.get(key=prefix + key, cb=CalvinCB(func=self.get_cb, org_cb=cb, org_key=key))
                except:
                    _log.error("Failed to get: %s" % key)
                    cb(key=key, value=False)

    def delete(self, prefix, key, cb):
        """ Delete key: prefix+key (value set to None)
        """
        if prefix + key in self.localstore:
            del self.localstore[prefix + key]
        if self.started:
            self.set(prefix, key, None, cb)
        else:
            if cb:
                cb(key, True)

    def add_node(self, node, cb=None):
        """
        Add node to storage
        """
        self.set(prefix="node-", key=node.id, value={"uri": node.uri, "control_uri": node.control_uri}, cb=cb)

    def get_node(self, node_id, cb=None):
        """
        Get node data from storage
        """
        self.get(prefix="node-", key=node_id, cb=cb)

    def delete_node(self, node_id, cb=None):
        """
        Delete node from storage
        """
        self.delete(prefix="node-", key=node_id, cb=cb)

    def add_application(self, application, cb=None):
        """
        Add application to storage
        """
        self.set(prefix="application-", key=application.id,
                 value={"name": application.name,
                        "actors": application.actors,
                        "origin_node_id": application.origin_node_id},
                 cb=cb)

    def get_application(self, application_id, cb=None):
        """
        Get application from storage
        """
        self.get(prefix="application-", key=application_id, cb=cb)

    def delete_application(self, application_id, cb=None):
        """
        Delete application from storage
        """
        self.delete(prefix="application-", key=application_id, cb=cb)

    def add_actor(self, actor, node_id, cb=None):
        """
        Add actor and its ports to storage
        """
        data = {"name": actor.name, "type": actor._type, "node_id": node_id}
        inports = []
        for p in actor.inports.values():
            port = {"id": p.id, "name": p.name}
            inports.append(port)
            self.add_port(p, node_id, actor.id, "in")
        data["inports"] = inports
        outports = []
        for p in actor.outports.values():
            port = {"id": p.id, "name": p.name}
            outports.append(port)
            self.add_port(p, node_id, actor.id, "out")
        data["outports"] = outports
        self.set(prefix="actor-", key=actor.id, value=data, cb=cb)

    def get_actor(self, actor_id, cb=None):
        """
        Get actor from storage
        """
        self.get(prefix="actor-", key=actor_id, cb=cb)

    def delete_actor(self, actor_id, cb=None):
        """
        Delete actor from storage
        """
        self.delete(prefix="actor-", key=actor_id, cb=cb)

    def add_port(self, port, node_id, actor_id=None, direction=None, cb=None):
        """
        Add port to storage
        """
        if direction is None:
            if isinstance(port, actorport.InPort):
                direction = "in"
            else:
                direction = "out"

        if actor_id is None:
            actor_id = port.owner.id

        data = {"name": port.name, "connected": port.is_connected(
        ), "node_id": node_id, "actor_id": actor_id, "direction": direction}
        if direction == "out":
            if port.is_connected():
                data["peers"] = port.get_peers()
            else:
                data["peers"] = []
        elif direction == "in":
            if port.is_connected():
                data["peer"] = port.get_peer()
            else:
                data["peer"] = None
        self.set(prefix="port-", key=port.id, value=data, cb=cb)

    def get_port(self, port_id, cb=None):
        """
        Get port from storage
        """
        self.get(prefix="port-", key=port_id, cb=cb)

    def delete_port(self, port_id, cb=None):
        """
        Delete port from storage
        """
        self.delete(prefix="port-", key=port_id, cb=cb)
