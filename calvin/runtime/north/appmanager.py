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

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)

class Application(object):

    """ Application class """

    def __init__(self, id, name, actor_id, origin_node_id):
        self.id = id
        self.name = name
        self.actors = [actor_id]
        self.origin_node_id = origin_node_id
        # node_info contains key: node_id, value: list of actors
        # Currently only populated at destruction time
        self.node_info = {}

    def clear_node_info(self):
        self.node_info = {}

    def update_node_info(self, node_id, actor_id):
        """ Collect information on current actor deployment """
        if node_id in self.node_info:
            self.node_info[node_id].append(actor_id)
        else:
            self.node_info[node_id] = [actor_id]

    def complete_node_info(self):
        return sum([len(a) for a in self.node_info.itervalues()]) == len(self.actors)
        
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
            self.applications[application_id] = Application(application_id, application_name, actor_id, self._node.id)
        self.storage.add_application(self.applications[application_id])

    def destroy(self, application_id):
        """ Destroy an application and its actors """
        # FIXME should take callback and wait for finalization of app destruction
        _log.debug("Destroy %s" % application_id)
        if application_id in self.applications:
            self._destroy(self.applications[application_id])
        else:
            self.storage.get_application(application_id, CalvinCB(self._destroy_app_info_cb))

    def _destroy_app_info_cb(self, application_id, value):
        _log.debug("Destroy app info %s: %s" % application_id, value)
        self._destroy(Application(application_id, value['name'], value['actors'], value['origin_node_id']))

    def _destroy(self, application):
        _log.debug("Destroy app w actors: %s" % application.actors)
        application.clear_node_info()
        # Loop over copy of app's actors, since modified inside loop
        for actor_id in application.actors[:]:
            if actor_id in self._node.am.list_actors():
                _log.debug("Destroy app local actor %s" % actor_id)
                self._node.am.destroy(actor_id)
                application.actors.remove(actor_id)
            else:
                _log.debug("Destroy app peers actor %s" % actor_id)
                self.storage.get_actor(actor_id, CalvinCB(func=self._destroy_actor_cb, application=application))

        if not application.actors:
            # Actors list already empty, all actors were local
            _log.debug("Destroy app all actors local")
            self._destroy_final(application)

    def _destroy_actor_cb(self, actor_id, value, application):
        """ Get actor callback """
        _log.debug("Destroy app peers actor cb %s" % actor_id)
        application.update_node_info(value['node_id'], actor_id)
        if application.complete_node_info():
            self._destroy_final(application)

    def _destroy_final(self, application):
        """ Final destruction of the application on this node and send request to peers to also destroy the app """
        _log.debug("Destroy final \n%s\n%s" % (application.node_info, application.origin_node_id))
        for node_id, actor_ids in application.node_info.iteritems():
            # Inform peers to destroy their part of the application
            # FIXME interested in response, use a callback
            self._node.proto.app_destroy(node_id, None, application.id, actor_ids)
        if application.id in self.applications:
            del self.applications[application.id]
        elif application.origin_node_id not in application.node_info:
            # All actors migrated from the original node, inform it also
            self._node.proto.app_destroy(application.origin_node_id, None, application.id, [])

        self.storage.delete_application(application.id)

    def destroy_request(self, application_id, actor_ids):
        """ Request from peer of local application parts destruction and related actors """
        _log.debug("Destroy request, app: %s, actors: %s" % (application_id, actor_ids))
        reply = "ACK"
        for actor_id in actor_ids:
            if actor_id in self._node.am.list_actors():
                self._node.am.destroy(actor_id)
            else:
                reply = "NACK"
        if application_id in self.applications:
            del self.applications[application_id]
        _log.debug("Destroy request reply %s" % reply)
        return reply

    def list_applications(self):
        """ Returns list of applications """
        print self.applications.keys()
        return list(self.applications.keys())
