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
import calvin.utilities.calvinresponse as response
from calvin.utilities import calvinuuid
from calvin.actorstore.store import ActorStore

class Application(object):

    """ Application class """

    def __init__(self, id, name, origin_node_id, actor_manager):
        self.id = id
        self.name = name or id
        self.ns = os.path.splitext(os.path.basename(name))[0]
        self.am = actor_manager
        self.actors = {}
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

    def new(self, name):
        application_id = calvinuuid.uuid("APP")
        self.applications[application_id] = Application(application_id, name, self._node.id, self._node.am)
        return application_id

    def add(self, application_id, actor_id):
        """ Add an actor """
        if application_id in self.applications:
            self.applications[application_id].add_actor(actor_id)
        else:
            _log.error("Non existing application id (%s) specified" % application_id)
            return

    def req_done(self, status, placement=None):
        _log.analyze(self._node.id, "+", {'status': str(status), 'placement': placement}, tb=True)

    def finalize(self, application_id, migrate=False, cb=None):
        if application_id not in self.applications:
            _log.error("Non existing application id (%s) specified" % application_id)
            return
        self.storage.add_application(self.applications[application_id])
        if migrate:
            self.execute_requirements(application_id, cb if cb else self.req_done)
        elif cb:
            cb(status=response.CalvinResponse(True))

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
        _log.debug("Destroy app info %s: %s" % application_id, value)
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

    def _destroy_actor_cb(self, key, value, application, retries=0):
        """ Get actor callback """
        _log.analyze(self._node.id, "+", {'actor_id': key, 'value': value, 'retries': retries})
        _log.debug("Destroy app peers actor cb %s" % key)
        if value and 'node_id' in value:
            application.update_node_info(value['node_id'], key)
        else:
            if retries<10:
                # FIXME add backoff time
                _log.analyze(self._node.id, "+ RETRY", {'actor_id': key, 'value': value, 'retries': retries})
                self.storage.get_actor(key, CalvinCB(func=self._destroy_actor_cb, application=application, retries=(retries+1)))
            else:
                # FIXME report failure
                _log.analyze(self._node.id, "+ GIVE UP", {'actor_id': key, 'value': value, 'retries': retries})
                application.update_node_info(None, key)

        if application.complete_node_info():
            self._destroy_final(application)

    def _destroy_final(self, application):
        """ Final destruction of the application on this node and send request to peers to also destroy the app """

        def _callback(*args, **kwargs):
            _log.debug("Destroyed actor params (%s, %s)" % (args, kwargs))
            _log.analyze(self._node.id, "+ CALLBACK DESTROYED ACTOR", {'args': str(args), 'kwargs': str(kwargs)})

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
        reply = response.CalvinResponse(True)
        for actor_id in actor_ids:
            if actor_id in self._node.am.list_actors():
                self._node.am.destroy(actor_id)
            else:
                reply = response.CalvinResponse(False)
        if application_id in self.applications:
            del self.applications[application_id]
        _log.debug("Destroy request reply %s" % reply)
        _log.analyze(self._node.id, "+ RESPONSE", {'reply': str(reply)})
        return reply

    def list_applications(self):
        """ Returns list of applications """
        return list(self.applications.keys())


    ### DEPLOYMENT ###
    
    def execute_requirements(self, application_id, cb):
        app = None
        try:
            app = self.applications[application_id]
        except:
            _log.debug("execute_requirements did not find app %s" % (application_id,))
            cb(status=response.CalvinResponse(False))
            return
        _log.debug("execute_requirements(app=%s)" % (self.applications[application_id],))

        # TODO extract groups

        if hasattr(app, '_org_cb'):
            # application deployment requirements ongoing, abort
            cb(status=response.CalvinResponse(True))
            return
        app._org_cb = cb
        name_map = app.get_actor_name_map(ns=app.ns)
        app._track_actor_cb = app.get_actors()[:]  # take copy of app's actor list, to remove each when done
        app.actor_placement = {}  # Clean placement slate
        _log.analyze(self._node.id, "+ APP REQ", {}, tb=True)
        for actor_id in app.get_actors():
            if actor_id not in self._node.am.actors.keys():
                _log.debug("Only apply requirements to local actors")
                continue
            _log.analyze(self._node.id, "+ ACTOR REQ", {'actor_id': actor_id}, tb=True)
            self.actor_requirements(app, actor_id)
            _log.analyze(self._node.id, "+ ACTOR REQ DONE", {'actor_id': actor_id}, tb=True)
        _log.analyze(self._node.id, "+ DONE", {'application_id': application_id}, tb=True)

    def actor_requirements(self, app, actor_id):
        if actor_id not in self._node.am.list_actors():
            _log.error("Currently we ignore deployment requirements for actor not local to the node, %s" % actor_id)
            return

        actor = self._node.am.actors[actor_id]
        _log.debug("actor_requirements(actor_id=%s), reqs=%s" % (actor_id, actor.requirements_get()))
        possible_nodes = set([None])  # None to mark no real response
        impossible_nodes = set([None])  # None to mark no real response
        reqs = actor.requirements_get()[:]
        for req in actor.requirements_get():
            if req['op']=='union_group':
                # Special operation that first forms a union of a requirement's list response set
                # To allow alternative requirements options
                self._union_requirements(req=req,
                                            app=app,
                                            actor_id=actor_id,
                                            possible_nodes=possible_nodes,
                                            impossible_nodes=impossible_nodes,
                                            reqs=reqs,
                                            component=actor.component_members())
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
                                            component=actor.component_members(),
                                            **req['kwargs'])
                except:
                    _log.error("actor_requirements one req failed for %s!!!" % actor_id, exc_info=True)
                    reqs.remove(req)
        if not reqs and actor_id in app._track_actor_cb:
            _log.analyze(self._node.id, "+ LOOP DONE", {'actor_id': actor_id, '_track_actor_cb': app._track_actor_cb}, tb=True)
            app._track_actor_cb.remove(actor_id)
            self._actor_requirements_combined(app, actor_id, possible_nodes, impossible_nodes)
        _log.analyze(self._node.id, "+ DONE", {'actor_id': actor_id}, tb=True)

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
                                        component=state['component'],
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
            state['union_reqs'].append(None)  # To prevent _union_requirements from also calling _actor_requirements_cb
            _log.debug("_union_requirements_cb req done union nodes: %s" % (state['union_nodes'],))
            self._actor_requirements_cb(node_ids=state['union_nodes'], 
                                        app=state['app'], 
                                        req=state['req'],
                                        actor_id=state['actor_id'],
                                        possible_nodes=state['possible_nodes'],
                                        impossible_nodes=state['impossible_nodes'],
                                        reqs=state['reqs'])

    def _actor_requirements_cb(self, node_ids, app, req, actor_id, possible_nodes, impossible_nodes, reqs):
        _log.analyze(self._node.id, "+", {'actor_id': actor_id,
                     'node_ids': list(node_ids) if isinstance(node_ids, set) else node_ids,
                     'req': req}, tb=True)
        if req['type']=='+' and node_ids is not None:
            # Positive rule, collect in possible nodes
            if None in possible_nodes:
                # Possible set starts empty hence fill it with first response
                possible_nodes -= set([None])
                possible_nodes |= set(node_ids)
            else:
                # Possible set is section between all individual req's sets
                possible_nodes &= set(node_ids)
        elif req['type']=='-' and node_ids is not None:
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
        _log.analyze(self._node.id, "+ DONE", {'node_ids': list(node_ids) if isinstance(node_ids, set) else node_ids}, tb=True)

    def _actor_requirements_combined(self, app, actor_id, possible_nodes, impossible_nodes):
        possible_nodes -= set([None])
        impossible_nodes -= set([None])
        possible_nodes -= impossible_nodes
        app.actor_placement[actor_id] = possible_nodes
        _log.analyze(self._node.id, "+", {'actor_id': actor_id, 'possible_nodes': list(possible_nodes),
                     'track_actor_cb': app._track_actor_cb}, tb=True)
        if not app._track_actor_cb:
            # Done collecting possible actor placement for all actors in application
            _log.analyze(self._node.id, "+ ALL ACTORS FINISHED", {'app_id': app.id}, tb=True)
            self._app_requirements(app)
        _log.analyze(self._node.id, "+ DONE", {'actor_id': actor_id}, tb=True)

    def _app_requirements(self, app):
        _log.debug("_app_requirements(app=%s)" % (app,))
        _log.analyze(self._node.id, "+ ACTOR PLACEMENT", {'placement': {k: list(v) for k, v in app.actor_placement.iteritems()}}, tb=True)
        if any([not n for n in app.actor_placement.values()]):
            # At least one actor have no possible placement
            app._org_cb(status=response.CalvinResponse(False))
            del app._org_cb
            _log.analyze(self._node.id, "+ NO PLACEMENT", {'app_id': app.id}, tb=True)
            return

        # Collect an actor by actor matrix stipulating a weighting 0.0 - 1.0 for their connectivity
        actor_ids, actor_matrix = self._actor_connectivity(app)

        # Get list of all possible nodes
        node_ids = set([])
        for possible_nodes in app.actor_placement.values():
            node_ids |= possible_nodes
        node_ids = list(node_ids)
        _log.analyze(self._node.id, "+ ACTOR MATRIX", {'actor_ids': actor_ids, 'actor_matrix': actor_matrix, 'node_ids': node_ids}, tb=True)

        # Weight the actors possible placement with their connectivity matrix
        weighted_actor_placement = {}
        for actor_id in actor_ids:
            # actor matrix is symmetric, so independent if read horizontal or vertical
            actor_weights = actor_matrix[actor_ids.index(actor_id)]
            # Sum the actor weights for each actors possible nodes, matrix mult AA * AN,
            # AA actor weights, AN actor * node with 1 when possible
            weights = [sum([actor_weights[actor_ids.index(_id)] if node_id in app.actor_placement[actor_id] else 0
                             for _id in actor_ids])
                             for node_id in node_ids]
            # Get first node with highest weight
            # FIXME should verify that the node actually exist also
            # TODO should select from a resource sharing perspective also, instead of picking first max
            _log.analyze(self._node.id, "+ WEIGHTS", {'actor_id': actor_id, 'weights': weights})
            weighted_actor_placement[actor_id] = node_ids[weights.index(max(weights))]

        for actor_id, node_id in weighted_actor_placement.iteritems():
            # TODO could add callback to try another possible node if the migration fails
            _log.debug("Actor deployment %s \t-> %s" % (app.actors[actor_id], node_id))
            self._node.am.migrate(actor_id, node_id)

        app._org_cb(status=response.CalvinResponse(True), placement=weighted_actor_placement)
        del app._org_cb
        _log.analyze(self._node.id, "+ DONE", {'app_id': app.id}, tb=True)

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


class Deployer(object):

    """
    Process an app_info dictionary (output from calvin parser) to
    produce a running calvin application.
    """

    def __init__(self, deployable, node, name=None, deploy_info=None, verify=True, cb=None):
        super(Deployer, self).__init__()
        self.deployable = deployable
        self.deploy_info = deploy_info
        self.actor_map = {}
        self.actor_connections = {}
        self.node = node
        self.verify = verify
        self.cb = cb
        if name:
            self.name = name
            self.app_id = self.node.app_manager.new(self.name)
            self.ns = os.path.splitext(os.path.basename(self.name))[0]
        elif "name" in self.deployable:
            self.name = self.deployable["name"]
            self.app_id = self.node.app_manager.new(self.name)
            self.ns = os.path.splitext(os.path.basename(self.name))[0]
        else:
            self.app_id = self.node.app_manager.new(None)
            self.name = self.app_id
            self.ns = ""

        self.components = {}
        l = (len(self.ns)+1) if self.ns else 0 
        for name in self.deployable['actors']:
             if name.find(':',l)> -1:
                # This is part of a component
                # component name including optional namespace
                component = ':'.join(name.split(':')[0:(2 if self.ns else 1)])
                if component in self.components:
                    self.components[component].append(name)
                else:
                    self.components[component] = [name]

    def component_name(self, name):
        l = (len(self.ns)+1) if self.ns else 0 
        if name.find(':',l)> -1:
            return ':'.join(name.split(':')[0:(2 if self.ns else 1)])
        else:
            return None

    def get_req(self, actor_name):
        name = self.component_name(actor_name) or actor_name
        name = name.split(':', 1)[1] if self.ns else name
        return self.deploy_info['requirements'][name] if (self.deploy_info and 'requirements' in self.deploy_info
                                                            and name in self.deploy_info['requirements']) else []
        
    def instantiate(self, actor_name, actor_type, argd, signature=None):
        """
        Instantiate an actor.
          - 'actor_name' is <namespace>:<identifier>, e.g. app:src, or app:component:src
          - 'actor_type' is the actor class to instatiate
          - 'argd' is a dictionary with <actor_name>:<argdict> pairs
          - 'signature' is the GlobalStore actor-signature to lookup the actor
        """
        req = self.get_req(actor_name)
        found, is_primitive, actor_def = ActorStore().lookup(actor_type)
        if self.verify and not found:
            raise Exception("Unknown actor type: %s" % actor_type)
        if self.verify and not is_primitive:
            raise Exception("Non-primitive type: %s" % actor_type)

        actor_id = self.instantiate_primitive(actor_name, actor_type, argd, req, signature)
        if not actor_id:
            raise Exception(
                "Could not instantiate actor of type: %s" % actor_type)
        self.actor_map[actor_name] = actor_id
        self.node.app_manager.add(self.app_id, actor_id)

    def instantiate_primitive(self, actor_name, actor_type, args, req=None, signature=None):
        # name is <namespace>:<identifier>, e.g. app:src, or app:component:src
        # args is a **dictionary** of key-value arguments for this instance
        # signature is the GlobalStore actor-signature to lookup the actor
        args['name'] = actor_name
        actor_id = self.node.am.new(actor_type=actor_type, args=args, signature=signature)
        if req:
            self.node.am.actors[actor_id].requirements_add(req)
        return actor_id

    def connectid(self, connection):
        src_actor, src_port, dst_actor, dst_port = connection
        # connect from dst to src
        # use node info if exists, otherwise assume local node

        dst_actor_id = self.actor_map[dst_actor]
        src_actor_id = self.actor_map[src_actor]
        src_node = self.node.id
        result = self.node.connect(
            actor_id=dst_actor_id,
            port_name=dst_port,
            port_dir='in',
            peer_node_id=src_node,
            peer_actor_id=src_actor_id,
            peer_port_name=src_port,
            peer_port_dir='out')
        return result

    def set_port_property(self, actor, port_type, port_name, port_property, value):
        self.node.am.set_port_property(self.actor_map[actor], port_type, port_name, port_property, value)

    def deploy(self):
        """
        Instantiate actors and link them together.
        """
        if not self.deployable['valid']:
            raise Exception("Deploy information is not valid")

        for actor_name, info in self.deployable['actors'].iteritems():
            self.instantiate(actor_name, info['actor_type'], info['args'], signature=info['signature'])

        for component_name, actor_names in self.components.iteritems():
            actor_ids = [self.actor_map[n] for n in actor_names]
            for actor_id in actor_ids:
                self.node.am.actors[actor_id].component_add(actor_ids)

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

        self.node.app_manager.finalize(self.app_id, migrate=True if self.deploy_info else False, 
                                       cb=CalvinCB(self.cb, deployer=self))

