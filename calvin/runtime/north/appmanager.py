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

import os
import random
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)
from calvin.runtime.north.plugins.requirements import req_operations


class Application(object):

    """ Application class """

    def __init__(self, id, name, actor_id, origin_node_id, actor_manager):
        self.id = id
        self.name = name
        self.ns = os.path.splitext(os.path.basename(name))[0]
        self.am = actor_manager
        self.actors = {}
        self.add_actor(actor_id)
        self.origin_node_id = origin_node_id
        self._track_actor_cb = None
        self.actor_placement = None
        # node_info contains key: node_id, value: list of actors
        # Currently only populated at destruction time
        self.node_info = {}

    def add_actor(self, actor_id):
        # Save actor_id and mapping to name while the actor is still on this node
        if not isinstance(actor_id, list):
            actor_id = [actor_id]
        for a in actor_id:
            self.actors[a] = self.am.actors[a].name if a in self.am.actors else None

    def remove_actor(self, actor_id):
        try:
            self.actors.pop(actor_id)
        except:
            pass

    def get_actors(self):
        return self.actors.keys()

    def get_actor_name_map(self, ns):
        actors = {v: [k] for k, v in self.actors.items() if v is not None}
        # Collect all actors under top component name
        components = {}
        l = (len(ns)+1) if ns else 0 
        for name, _id in actors.iteritems():
             if name.find(':',l)> -1:
                # This is a component
                # component name including optional namespace
                component = ':'.join(name.split(':')[0:(2 if ns else 1)])
                if component in components.keys():
                    components[component] += _id
                else:
                    components[component] = _id
        actors.update(components)
        return actors

    def __str__(self):
        s = "id: " + self.id + "\n"
        s += "name: " + self.name + "\n"
        for _id, name in self.actors.iteritems():
            s += "actor: " + _id + ", " + (name if name else "<UNKNOWN>") + "\n"
            if self.actor_placement and _id in self.actor_placement:
                s += "\t" + str(list(self.actor_placement[_id])) + "\n"
        return s

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
            self.applications[application_id].add_actor(actor_id)
        else:
            self.applications[application_id] = Application(application_id, application_name, actor_id, 
                                                            self._node.id, self._node.am)
        self.storage.add_application(self.applications[application_id])

    def destroy(self, application_id):
        """ Destroy an application and its actors """
        # FIXME should take callback and wait for finalization of app destruction
        _log.analyze(self._node.id, "+", {'application_id': application_id})
        if application_id in self.applications:
            self._destroy(self.applications[application_id])
        else:
            self.storage.get_application(application_id, CalvinCB(self._destroy_app_info_cb))

    def _destroy_app_info_cb(self, application_id, value):
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'value': value})
        if value:
            self._destroy(Application(application_id, value['name'], value['actors'], value['origin_node_id']))

    def _destroy(self, application):
        _log.analyze(self._node.id, "+", {'actors': application.actors})
        application.clear_node_info()
        # Loop over copy of app's actors, since modified inside loop
        for actor_id in application.actors.keys()[:]:
            if actor_id in self._node.am.list_actors():
                _log.analyze(self._node.id, "+ LOCAL ACTOR", {'actor_id': actor_id})
                # TODO: Check if it whent ok
                self._node.am.destroy(actor_id)
                application.remove_actor(actor_id)
            else:
                _log.analyze(self._node.id, "+ REMOTE ACTOR", {'actor_id': actor_id})
                self.storage.get_actor(actor_id, CalvinCB(func=self._destroy_actor_cb, application=application))

        if not application.actors or application.complete_node_info():
            # Actors list already empty, all actors were local or the storage was calling the cb in-loop
            _log.analyze(self._node.id, "+ DONE", {})
            self._destroy_final(application)

    def _destroy_actor_cb(self, actor_id, value, application, retries=0):
        """ Get actor callback """
        _log.analyze(self._node.id, "+", {'actor_id': actor_id, 'value': value, 'retries': retries})
        if value and 'node_id' in value:
            application.update_node_info(value['node_id'], actor_id)
        else:
            if retries<10:
                # FIXME add backoff time
                _log.analyze(self._node.id, "+ RETRY", {'actor_id': actor_id, 'value': value, 'retries': retries})
                self.storage.get_actor(actor_id, CalvinCB(func=self._destroy_actor_cb, application=application, retries=(retries+1)))
            else:
                # FIXME report failure
                _log.analyze(self._node.id, "+ GIVE UP", {'actor_id': actor_id, 'value': value, 'retries': retries})
                application.update_node_info(None, actor_id)

        if application.complete_node_info():
            self._destroy_final(application)

    def _destroy_final(self, application):
        """ Final destruction of the application on this node and send request to peers to also destroy the app """

        def _callback(*args, **kwargs):
            _log.debug("Destroyed actor params (%s, %s)" % (args, kwargs))
            _log.analyze(self._node.id, "+ CALLBACK DESTROYED ACTOR", {'args': args, 'kwargs': kwargs})

        _log.analyze(self._node.id, "+", {'node_info': application.node_info, 'origin_node_id': application.origin_node_id})
        for node_id, actor_ids in application.node_info.iteritems():
            if not node_id:
                _log.analyze(self._node.id, "+ UNKNOWN NODE", {})
                continue
            # Inform peers to destroy their part of the application
            # FIXME interested in response, use a callback
            self._node.proto.app_destroy(node_id, CalvinCB(_callback, node_id), application.id, actor_ids)

        if application.id in self.applications:
            del self.applications[application.id]
        elif application.origin_node_id not in application.node_info:
            # All actors migrated from the original node, inform it also
            _log.analyze(self._node.id, "+ SEP APP NODE", {})
            self._node.proto.app_destroy(application.origin_node_id, None, application.id, [])

        self.storage.delete_application(application.id)

    def destroy_request(self, application_id, actor_ids):
        """ Request from peer of local application parts destruction and related actors """
        _log.debug("Destroy request, app: %s, actors: %s" % (application_id, actor_ids))
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'actor_ids': actor_ids})
        reply = "ACK"
        for actor_id in actor_ids:
            if actor_id in self._node.am.list_actors():
                self._node.am.destroy(actor_id)
            else:
                reply = "NACK"
        if application_id in self.applications:
            del self.applications[application_id]
        _log.debug("Destroy request reply %s" % reply)
        _log.analyze(self._node.id, "+ RESPONSE", {'reply': reply})
        return reply

    def list_applications(self):
        """ Returns list of applications """
        return list(self.applications.keys())


    ### DEPLOYMENT ###
    
    def deployment_add_requirements(self, application_id, reqs, cb):
        app = None
        try:
            app = self.applications[application_id]
        except:
            _log.debug("deployment_add_requirements did not find app %s" % (application_id,))
            cb(status="NACK")
            return
        _log.debug("deployment_add_requirements(app=%s,\n reqs=%s)" % (self.applications[application_id], reqs))

        # TODO extract groups

        if "requirements" not in reqs:
            # No requirements then we are happy
            cb(status="ACK")
            return

        if hasattr(app, '_org_cb'):
            # application deployment requirements ongoing, abort
            cb(status="ACK")
            return
        app._org_cb = cb
        name_map = app.get_actor_name_map(ns=app.ns)
        app._track_actor_cb = app.get_actors()[:]  # take copy of app's actor list, to remove each when done
        app.actor_placement = {}  # Clean placement slate
        for actor_name, req in reqs["requirements"].iteritems():
            # Component returns list of actor ids, actors returns list with single id
            actor_ids = name_map.get((app.ns + ":" if app.ns else "") + actor_name, None)
            # Apply same rule to all actors in a component, rule get component information and can act accordingly
            for actor_id in actor_ids:
                if actor_id not in self._node.am.actors.keys():
                    _log.debug("Only apply requirements to local actors")
                    continue
                actor = self._node.am.actors[actor_id]
                actor.deployment_add_requirements(req, component=(actor_ids if len(actor_ids)>1 else None))
                self.actor_requirements(app, actor_id)

    def actor_requirements(self, app, actor_id):
        if actor_id not in self._node.am.list_actors():
            _log.error("Currently we ignore deployment requirements for actor not local to the node, %s" % actor_id)
            return

        actor = self._node.am.actors[actor_id]
        _log.debug("actor_requirements(actor_id=%s), reqs=%s" % (actor_id, actor._deployment_requirements))
        possible_nodes = set([None])  # None to mark no real response
        impossible_nodes = set([None])  # None to mark no real response
        reqs = actor._deployment_requirements[:]
        for req in actor._deployment_requirements:
            if req['op']=='union_group':
                # Special operation that first forms a union of a requirement's list response set
                # To allow alternative requirements options
                self._union_requirements(req=req,
                                            app=app,
                                            actor_id=actor_id,
                                            possible_nodes=possible_nodes,
                                            impossible_nodes=impossible_nodes,
                                            reqs=reqs)
            else:
                try:
                    req_operations[req['op']].req_op(self._node, 
                                           CalvinCB(self._actor_requirements_cb,
                                                    req=req,
                                                    app=app,
                                                    actor_id=actor_id,
                                                    possible_nodes=possible_nodes,
                                                    impossible_nodes=impossible_nodes,
                                                    reqs=reqs),
                                            actor_id=actor_id,
                                            component=req['component'],
                                            **req['kwargs'])
                except:
                    _log.error("actor_requirements one req failed for %s!!!" % actor_id, exc_info=True)
                    reqs.remove(req)
        if not reqs:
            _log.error("actor_requirements all req failed for %s!!!" % actor_id)
            app._track_actor_cb.remove(actor_id)
            self._actor_requirements_combined(app, actor_id, possible_nodes, impossible_nodes)

    def _union_requirements(self, **state):
        state['union_nodes'] = set([])
        union_reqs = state['req']['requirements'][:]
        for union_req in state['req']['requirements']:
            try:
                req_operations[union_req['op']].req_op(self._node, 
                                       CalvinCB(self._union_requirements_cb,
                                                union_reqs=union_reqs,
                                                union_req=union_req,
                                                **state),
                                        actor_id=state['actor_id'],
                                        component=state['req']['component'],
                                        **union_req['kwargs'])
            except:
                _log.error("union_requirements one req failed for %s!!!" % state['actor_id'], exc_info=True)
                union_reqs.remove(union_req)
        if not union_reqs:
            _log.error("union_requirements all req failed for %s!!!" % state['actor_id'])
            self._actor_requirements_cb(node_ids=state['union_nodes'], 
                                        app=state['app'], 
                                        req=state['req'],
                                        actor_id=state['actor_id'],
                                        possible_nodes=state['possible_nodes'],
                                        impossible_nodes=state['impossible_nodes'],
                                        reqs=state['reqs'])

    def _union_requirements_cb(self, node_ids, **state):
        _log.debug("_union_requirements_cb(node_ids=%s)", node_ids)
        if node_ids:
            state['union_nodes'] |= set(node_ids)
        state['union_reqs'].remove(state['union_req'])
        if not state['union_reqs']:
            _log.debug("_union_requirements_cb req done union nodes: %s" % (state['union_nodes'],))
            self._actor_requirements_cb(node_ids=state['union_nodes'], 
                                        app=state['app'], 
                                        req=state['req'],
                                        actor_id=state['actor_id'],
                                        possible_nodes=state['possible_nodes'],
                                        impossible_nodes=state['impossible_nodes'],
                                        reqs=state['reqs'])

    def _actor_requirements_cb(self, node_ids, app, req, actor_id, possible_nodes, impossible_nodes, reqs):
        _log.debug("_actor_requirements_cb(node_ids=%s)", node_ids)
        if req['type']=='+' and node_ids:
            # Positive rule, collect in possible nodes
            if None in possible_nodes:
                # Possible set starts empty hence fill it with first response
                possible_nodes -= set([None])
                possible_nodes |= set(node_ids)
            else:
                # Possible set is section between all individual req's sets
                possible_nodes &= set(node_ids)
        elif req['type']=='-' and node_ids:
            # Negative rule, collect in impossible nodes
            if None in impossible_nodes:
                # Impossible set starts empty hence fill it with first response
                impossible_nodes -= set([None])
                impossible_nodes |= set(node_ids)
            else:
                # Impossible set is section between all individual req's sets
                impossible_nodes &= set(node_ids)
        reqs.remove(req)
        if not reqs:
            _log.debug("_actor_requirements_cb req done possible: %s, impossible: %s" % (possible_nodes, impossible_nodes))
            # Collected all rules for actor, 
            app._track_actor_cb.remove(actor_id)
            self._actor_requirements_combined(app, actor_id, possible_nodes, impossible_nodes)

    def _actor_requirements_combined(self, app, actor_id, possible_nodes, impossible_nodes):
        possible_nodes -= set([None])
        impossible_nodes -= set([None])
        possible_nodes -= impossible_nodes
        app.actor_placement[actor_id] = possible_nodes
        if not app._track_actor_cb:
            # Done collecting possible actor placement for all actors in application
            self._app_requirements(app)

    def _app_requirements(self, app):
        _log.debug("_app_requirements(app=%s)" % (app,))
        _log.analyze(self._node.id, "+ ACTOR PLACEMENT", {'placement': {k: list(v) for k, v in app.actor_placement.iteritems()}})
        if any([not n for n in app.actor_placement.values()]):
            # At least one actor have no possible placement
            app._org_cb(status="NACK")
            del app._org_cb
            return

        # Collect an actor by actor matrix stipulating a weighting 0.0 - 1.0 for their connectivity
        actor_ids, actor_matrix = self._actor_connectivity(app)
        _log.analyze(self._node.id, "+ ACTOR MATRIX", {'actor_ids': actor_ids, 'actor_matrix': actor_matrix})

        # Get list of all possible nodes
        node_ids = set([])
        for possible_nodes in app.actor_placement.values():
            node_ids |= possible_nodes
        node_ids = list(node_ids)

        # Weight the actors possible placement with their connectivity matrix
        weighted_actor_placement = {}
        for actor_id in actor_ids:
            # actor matrix is symmetric, so independent if read horizontal or vertical
            actor_weights = actor_matrix[actor_ids.index(actor_id)]
            # Sum the actor weights for each actors possible nodes, matrix mult AA * AN,
            # AA actor weights, AN actor * node with 1 when possible
            weights = [sum([actor_weights[actor_ids.index(_id)] if node_id in app.actor_placement[_id] else 0
                             for _id in actor_ids])
                             for node_id in node_ids]
            # Get first node with highest weight
            # FIXME should verify that the node actually exist also
            # TODO should select from a resource sharing perspective also, instead of picking first max
            weighted_actor_placement[actor_id] = node_ids[weights.index(max(weights))]

        for actor_id, node_id in weighted_actor_placement.iteritems():
            # TODO could add callback to try another possible node if the migration fails
            _log.debug("Actor deployment %s \t-> %s" % (app.actors[actor_id], node_id))
            self._node.am.migrate(actor_id, node_id)

        app._org_cb(status="ACK", placement=weighted_actor_placement)
        del app._org_cb

    def _actor_connectivity(self, app):
        """ Matrix of weights between actors how close they want to be
            0 = don't care
            1 = same node
            
            Currently any nodes that are connected gets 0.5, and
            diagonal is 1:s
        """
        list_actors = app.get_actors()
        l= len(list_actors)
        actor_matrix = [[0 for x in range(l)] for x in range(l)]
        for actor_id in list_actors:
            connections = self._node.am.connections(actor_id)
            for p in connections['inports'].values():
                try:
                    peer_actor_id = self._node.pm._get_local_port(port_id=p[1]).owner.id
                except:
                    # Only work while the peer still is local
                    # TODO get it from storage
                    continue
                actor_matrix[list_actors.index(actor_id)][list_actors.index(peer_actor_id)] = 0.5
                actor_matrix[list_actors.index(peer_actor_id)][list_actors.index(actor_id)] = 0.5
        for i in range(l):
            actor_matrix[i][i] = 1
        return (list_actors, actor_matrix)
