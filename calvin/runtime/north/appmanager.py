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

from calvin.utilities import utils
from calvin.utilities.calvin_callback import CalvinCB

class Application(object):

    """ Application class """

    def __init__(self, id, name, actor_id):
        self.id = id
        self.name = name
        self.actors = [actor_id]

class AppManager(object):

    """ Manage deployed applications """

    def __init__(self, node):
        self._node = node
        self.storage = node.storage
        self.applications = {}

    def add(self, application_id, application_name, actor_id):
        """ Add an actor """
        if application_id in self.applications:
            self.applications[application_id].actors.append(actor_id)
        else:
            self.applications[application_id] = Application(application_id, application_name, actor_id)
        self.storage.add_application(self.applications[application_id])

    def get_node_cb(self, key, value, actor_id):
        """ Get node callback """
        rt = utils.RT(value['control_uri'])
        utils.delete_actor(rt, actor_id)

    def get_actor_cb(self, key, value, actor_id):
        """ Get actor callback """
        self.storage.get_node(value['node_id'], CalvinCB(func=self.get_node_cb, actor_id=actor_id))

    def destroy(self, application_id):
        """ Destroy an application and its actors """
        if application_id in self.applications:
            for actor in self.applications[application_id].actors:
                if actor in self._node.am.list_actors():
                    self._node.am.destroy(actor)
                else:
                    self.storage.get_actor(actor, CalvinCB(func=self.get_actor_cb, actor_id=actor))
            del self.applications[application_id]
        self.storage.delete_application(application_id)

    def list_applications(self):
        """ Returns list of applications """
        print self.applications.keys()
        return list(self.applications.keys())
