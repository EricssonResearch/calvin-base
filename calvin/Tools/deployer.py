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
from calvin.utilities import utils
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinuuid
import json

_log = get_logger(__name__)


class Deployer(object):

    """
    Process an app_info dictionary (output from calvin parser) to
    produce a running calvin application.
    """

    def __init__(self, runtime, deployable, node_info=None, node=None, verify=True):
        super(Deployer, self).__init__()
        self.runtime = runtime
        self.deployable = deployable
        self.actor_map = {}
        self.node_info = node_info if node_info else {}
        self.actor_connections = {}
        self.app_id = calvinuuid.uuid("APP")
        self.node = node
        self.verify = verify
        if "name" in self.deployable:
            self.name = self.deployable["name"]
        else:
            self.name = self.app_id

    def instantiate(self, actor_name, actor_type, argd):
        """
        Instantiate an actor.
          - 'actor_name' is <namespace>:<identifier>, e.g. app:src, or app:component:src
          - 'actor_type' is the actor class to instatiate
          - 'argd' is a dictionary with <actor_name>:<argdict> pairs
        """
        found, is_primitive, actor_def = ActorStore().lookup(actor_type)
        if self.verify and not found:
            raise Exception("Unknown actor type: %s" % actor_type)
        if self.verify and not is_primitive:
            raise Exception("Non-primitive type: %s" % actor_type)

        instance_id = self.instantiate_primitive(actor_name, actor_type, argd)
        if not instance_id:
            raise Exception(
                "Could not instantiate actor of type: %s" % actor_type)
        self.actor_map[actor_name] = instance_id

    def instantiate_primitive(self, actor_name, actor_type, args):
        # name is <namespace>:<identifier>, e.g. app:src, or app:component:src
        # args is a **dictionary** of key-value arguments for this instance
        args['name'] = actor_name
        if self.node is not None:
            instance_id = self.node.new(
                actor_type=actor_type,
                args=args,
                deploy_args={'app_id': self.app_id, 'app_name': self.name})
        else:
            instance_id = utils.new_actor_wargs(
                rt=self.runtime,
                actor_type=actor_type,
                actor_name=actor_name,
                args=args,
                deploy_args={'app_id': self.app_id})
        return instance_id

    def connectid(self, connection):
        src_actor, src_port, dst_actor, dst_port = connection
        # connect from dst to src
        # use node info if exists, otherwise assume local node

        dst_actor_id = self.actor_map[dst_actor]
        src_actor_id = self.actor_map[src_actor]
        if self.node is not None:
            src_node = self.node_info.get(src_actor, self.node.id)
            result = self.node.connect(
                actor_id=dst_actor_id,
                port_name=dst_port,
                port_dir='in',
                peer_node_id=src_node,
                peer_actor_id=src_actor_id,
                peer_port_name=src_port,
                peer_port_dir='out')
        else:
            src_node = self.node_info.get(src_actor, self.runtime.id)
            result = utils.connect(self.runtime, dst_actor_id, dst_port, src_node, src_actor_id, src_port)
        return result

    def set_port_property(self, actor, port_type, port_name, port_property, value):
        if self.node is not None:
            self.node.am.set_port_property(self.actor_map[actor], port_type, port_name, port_property, value)
        else:
            utils.set_port_property(
                rt=self.runtime,
                actor_id=self.actor_map[actor],
                port_type=port_type,
                port_name=port_name,
                port_property=port_property,
                value=value)

    def deploy(self):
        """
        Instantiate actors and link them together.
        """
        if not self.deployable['valid']:
            raise Exception("Deploy information is not valid")

        for actor_name, info in self.deployable['actors'].iteritems():
            self.instantiate(actor_name, info['actor_type'], info['args'])

        # FIXME: Move to analyzer
        for src, dst_list in self.deployable['connections'].iteritems():
            if len(dst_list) > 1:
                src_name, src_port = src.split('.')
                self.set_port_property(src_name, 'out', src_port, 'fanout', len(dst_list))

        for src, dst_list in self.deployable['connections'].iteritems():
            src_actor, src_port = src.split('.')
            for dst in dst_list:
                dst_actor, dst_port = dst.split('.')
                c = (src_actor, src_port, dst_actor, dst_port)
                self.connectid(c)

        return self.app_id

    def destroy(self):
        if self.node is not None:
            result = self.node.app_manager.destroy(self.app_id)
        else:
            result = utils.delete_application(self.runtime, self.app_id)
        return result

