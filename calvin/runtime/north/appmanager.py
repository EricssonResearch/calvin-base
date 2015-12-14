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
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import dynops
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.requirements import req_operations
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinuuid
from calvin.actorstore.store import ActorStore, GlobalStore
from calvin.runtime.south.plugins.async import async
from calvin.utilities.security import Security

_log = calvinlogger.get_logger(__name__)


class Application(object):

    """ Application class """

    def __init__(self, id, name, origin_node_id, actor_manager, actors=None, deploy_info=None):
        self.id = id
        self.name = name or id
        self.ns = os.path.splitext(os.path.basename(self.name))[0]
        self.am = actor_manager
        self.actors = {} if actors is None else actors
        self.origin_node_id = origin_node_id
        self._track_actor_cb = None
        self.actor_placement = None
        # node_info contains key: node_id, value: list of actors
        # Currently only populated at destruction time
        self.node_info = {}
        self.components = {}
        self.deploy_info = deploy_info
        self._collect_placement_cb = None

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
            if self.actor_placement and _id in self.actor_placement and self.actor_placement[_id]:
                s += "\t" + str(list(self.actor_placement[_id])) + "\n"
            elif self.actor_placement and _id in self.actor_placement:
                s += "\t" + str(self.actor_placement[_id]) + "\n"
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

    def group_components(self):
        self.components = {}
        l = (len(self.ns)+1) if self.ns else 0
        for name in self.actors.values():
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
                                                            and name in self.deploy_info['requirements']) else None


class AppManager(object):

    """ Manage deployed applications """

    def __init__(self, node):
        self._node = node
        self.storage = node.storage
        self.applications = {}

    def new(self, name):
        application_id = calvinuuid.uuid("APP")
        self.applications[application_id] = Application(application_id, name, self._node.id, self._node.am)
        self._node.control.log_application_new(application_id, name)
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
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'migrate': migrate, 'cb': str(cb)})
        if application_id not in self.applications:
            _log.error("Non existing application id (%s) specified" % application_id)
            return
        self.storage.add_application(self.applications[application_id])
        if migrate:
            self.execute_requirements(application_id, cb if cb else self.req_done)
        elif cb:
            cb(status=response.CalvinResponse(True))

    def destroy(self, application_id, cb=None):
        """ Destroy an application and its actors """
        _log.analyze(self._node.id, "+", {'application_id': application_id})
        if application_id in self.applications:
            self._destroy(self.applications[application_id], cb=cb)
        else:
            self.storage.get_application(application_id, CalvinCB(self._destroy_app_info_cb, cb=cb))

    def _destroy_app_info_cb(self, application_id, value, cb=None):
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'value': value})
        _log.debug("Destroy app info %s: %s" % application_id, value)
        if value:
            self._destroy(Application(application_id, value['name'], value['origin_node_id'],
                                      self._node.am, value['actors_name_map']))
        elif cb:
            cb(status=response.CalvinResponse(response.NOT_FOUND))

    def _destroy(self, application, cb=None):
        _log.analyze(self._node.id, "+", {'actors': application.actors})
        application.destroy_cb = cb
        try:
            del application._destroy_node_ids
        except:
            pass
        application.clear_node_info()
        # Loop over copy of app's actors, since modified inside loop
        for actor_id in application.actors.keys()[:]:
            if actor_id in self._node.am.list_actors():
                _log.analyze(self._node.id, "+ LOCAL ACTOR", {'actor_id': actor_id})
                # TODO: Check if it went ok
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
        if hasattr(application, '_destroy_node_ids'):
            # Already called
            return
        _log.analyze(self._node.id, "+", {'node_info': application.node_info, 'origin_node_id': application.origin_node_id})
        application._destroy_node_ids = {n: None for n in application.node_info.keys()}
        for node_id, actor_ids in application.node_info.iteritems():
            if not node_id:
                _log.analyze(self._node.id, "+ UNKNOWN NODE", {})
                application._destroy_node_ids[None] = response.CalvinResponse(False)
                continue
            # Inform peers to destroy their part of the application
            self._node.proto.app_destroy(node_id, CalvinCB(self._destroy_final_cb, application, node_id),
                application.id, actor_ids)

        if application.id in self.applications:
            del self.applications[application.id]
        elif application.origin_node_id not in application.node_info and application.origin_node_id != self._node.id:
            # All actors migrated from the original node, inform it also
            _log.analyze(self._node.id, "+ SEP APP NODE", {})
            self._node.proto.app_destroy(application.origin_node_id, None, application.id, [])

        self.storage.delete_application(application.id)
        self._destroy_final_cb(application, '', response.CalvinResponse(True))

    def _destroy_final_cb(self, application, node_id, status):
        _log.analyze(self._node.id, "+", {'node_id': node_id, 'status': status})
        application._destroy_node_ids[node_id] = status
        if any([s is None for s in application._destroy_node_ids.values()]):
            return
        # Done
        if all(application._destroy_node_ids.values()):
            application.destroy_cb(status=response.CalvinResponse(True))
        else:
            application.destroy_cb(status=response.CalvinResponse(False))
        self._node.control.log_application_destroy(application.id)

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


    ### DEPLOYMENT REQUIREMENTS ###

    def collect_placement(self, it, app):
        _log.analyze(self._node.id, "+ BEGIN", {}, tb=True)
        if app._collect_placement_cb:
            app._collect_placement_cb.cancel()
            app._collect_placement_cb = None
        try:
            while True:
                _log.analyze(self._node.id, "+ ITER", {})
                actor_node_id = it.next()
                app._collect_placement_last_value = app._collect_placement_counter
                app.actor_placement.setdefault(actor_node_id[0], set([])).add(actor_node_id[1])
        except dynops.PauseIteration:
            _log.analyze(self._node.id, "+ PAUSED",
                    {'counter': app._collect_placement_counter,
                     'last_value': app._collect_placement_last_value,
                     'diff': app._collect_placement_counter - app._collect_placement_last_value})
            # FIXME the dynops should be self triggering, but is not...
            # This is a temporary fix by keep trying
            delay = 0.0 if app._collect_placement_counter > app._collect_placement_last_value + 100 else 0.2
            app._collect_placement_counter += 1
            app._collect_placement_cb = async.DelayedCall(delay, self.collect_placement, it=it,
                                                                    app=app)
            return
        except StopIteration:
            if not app.done_final:
                app.done_final = True
                # all possible actor placements derived
                _log.analyze(self._node.id, "+ ALL", {})
                self._app_requirements(app)
                _log.analyze(self._node.id, "+ END", {})
        except:
            _log.exception("appmanager:collect_placement")

    ### DEPLOYMENT ###

    def execute_requirements(self, application_id, cb):
        """ Build dynops iterator to collect all possible placements,
            then trigger migration.

            For initial deployment (all actors on the current node)
        """
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
            cb(status=response.CalvinResponse(False))
            return
        app._org_cb = cb
        app.done_final = False
        app._collect_placement_counter = 0
        app._collect_placement_last_value = 0
        actor_placement_it = dynops.List()
        app.actor_placement = {}  # Clean placement slate
        _log.analyze(self._node.id, "+ APP REQ", {}, tb=True)
        for actor_id in app.get_actors():
            if actor_id not in self._node.am.actors.keys():
                _log.debug("Only apply requirements to local actors")
                continue
            _log.analyze(self._node.id, "+ ACTOR REQ", {'actor_id': actor_id}, tb=True)
            actor_req = self.actor_requirements(app, actor_id).set_name("Actor"+actor_id)
            actor_placement_it.append((actor_id, actor_req), trigger_iter = actor_req)
            _log.analyze(self._node.id, "+ ACTOR REQ DONE", {'actor_id': actor_id}, tb=True)
        actor_placement_it.final()
        collect_iter = dynops.Collect(actor_placement_it)
        collect_iter.set_cb(self.collect_placement, collect_iter, app)
        self.collect_placement(collect_iter, app)
        _log.analyze(self._node.id, "+ DONE", {'application_id': application_id}, tb=True)

    def actor_requirements(self, app, actor_id):
        if actor_id not in self._node.am.list_actors():
            _log.error("Currently we ignore deployment requirements for actor not local to the node, %s" % actor_id)
            return

        actor = self._node.am.actors[actor_id]
        _log.debug("actor_requirements(actor_id=%s), reqs=%s" % (actor_id, actor.requirements_get()))
        intersection_iters = []
        difference_iters = []
        for req in actor.requirements_get():
            if req['op']=='union_group':
                # Special operation that first forms a union of a requirement's list response set
                # To allow alternative requirements options
                intersection_iters.append(self._union_requirements(req=req,
                                                    app=app,
                                                    actor_id=actor_id,
                                                    component=actor.component_members()).set_name("SActor"+actor_id))
            else:
                try:
                    _log.analyze(self._node.id, "+ REQ OP", {'op': req['op'], 'kwargs': req['kwargs']})
                    it = req_operations[req['op']].req_op(self._node,
                                            actor_id=actor_id,
                                            component=actor.component_members(),
                                            **req['kwargs']).set_name(req['op']+",SActor"+actor_id)
                    if req['type']=='+':
                        intersection_iters.append(it)
                    elif req['type']=='-':
                        difference_iters.append(it)
                    else:
                        _log.error("actor_requirements unknown req type %s for %s!!!" % (req['type'], actor_id),
                                   exc_info=True)
                except:
                    _log.error("actor_requirements one req failed for %s!!!" % actor_id, exc_info=True)
                    # FIXME how to handle failed requirements, now we drop it
        return_iter = dynops.Intersection(*intersection_iters).set_name("SActor"+actor_id)
        if difference_iters:
            return_iter = dynops.Difference(return_iter, *difference_iters).set_name("SActor"+actor_id)
        return return_iter

    def _union_requirements(self, **state):
        union_iters = []
        for union_req in state['req']['requirements']:
            try:
                union_iters.append(req_operations[union_req['op']].req_op(self._node,
                                        actor_id=state['actor_id'],
                                        component=state['component'],
                                        **union_req['kwargs']).set_name(union_req['op']+",UActor"+state['actor_id']))
            except:
                _log.error("union_requirements one req failed for %s!!!" % state['actor_id'], exc_info=True)
        return dynops.Union(*union_iters)

    def _app_requirements(self, app):
        _log.debug("_app_requirements(app=%s)" % (app,))
        _log.analyze(self._node.id, "+ ACTOR PLACEMENT", {'placement': app.actor_placement}, tb=True)
        status = response.CalvinResponse(True)
        if any([not n for n in app.actor_placement.values()]) or len(app.actors) > len(app.actor_placement):
            # At least one actor have no required placement
            # Let them stay on this node
            for actor_id in [a for a in app.actors if a not in app.actor_placement]:
                app.actor_placement[actor_id] = set([self._node.id])
            # Status will indicate success, but be different than the normal OK code
            status = response.CalvinResponse(response.CREATED)
            _log.analyze(self._node.id, "+ MISS PLACEMENT", {'app_id': app.id, 'placement': app.actor_placement}, tb=True)

        # Collect an actor by actor matrix stipulating a weighting 0.0 - 1.0 for their connectivity
        actor_ids, actor_matrix = self._actor_connectivity(app)

        # Get list of all possible nodes
        node_ids = set([])
        for possible_nodes in app.actor_placement.values():
            node_ids |= possible_nodes
        node_ids = list(node_ids)
        node_ids = [n for n in node_ids if not isinstance(n, dynops.InfiniteElement)]
        for actor_id, possible_nodes in app.actor_placement.iteritems():
            if any([isinstance(n, dynops.InfiniteElement) for n in possible_nodes]):
                app.actor_placement[actor_id] = node_ids
        _log.analyze(self._node.id, "+ ACTOR MATRIX", {'actor_ids': actor_ids, 'actor_matrix': actor_matrix,
                                            'node_ids': node_ids, 'placement': app.actor_placement}, tb=True)

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

        app._org_cb(status=status, placement=weighted_actor_placement)
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

    # Remigration

    def migrate_with_requirements(self, app_id, deploy_info, move=False, cb=None):
        """ Migrate actors of app app_id based on newly supplied deploy_info.
            Optional argument move controls if actors prefers to stay when possible.
        """
        self.storage.get_application(app_id, cb=CalvinCB(self._migrate_got_app,
                                                         app_id=app_id, deploy_info=deploy_info,
                                                         move=move, cb=cb))

    def _migrate_got_app(self, key, value, app_id, deploy_info, move, cb):
        if not value:
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND))
            return
        app = Application(app_id, value['name'], value['origin_node_id'],
                                              self._node.am, actors=value['actors_name_map'], deploy_info=deploy_info)
        app.group_components()
        app._migrated_actors = {a: None for a in app.actors}
        for actor_id, actor_name in app.actors.iteritems():
            req = app.get_req(actor_name)
            if req is None:
                _log.analyze(self._node.id, "+ NO REQ", {'actor_id': actor_id, 'actor_name': actor_name})
                # No requirement then leave as is.
                self._migrated_cb(response.CalvinResponse(True), app, actor_id, cb)
                continue
            if actor_id in self._node.am.actors:
                _log.analyze(self._node.id, "+ OWN ACTOR", {'actor_id': actor_id, 'actor_name': actor_name})
                self._node.am.update_requirements(actor_id, req, False, move,
                                                 callback=CalvinCB(self._migrated_cb, app=app,
                                                                   actor_id=actor_id, cb=cb))
            else:
                _log.analyze(self._node.id, "+ OTHER NODE", {'actor_id': actor_id, 'actor_name': actor_name})
                self.storage.get_actor(actor_id, cb=CalvinCB(self._migrate_from_rt, app=app,
                                                                  actor_id=actor_id, req=req,
                                                                  move=move, cb=cb))

    def _migrate_from_rt(self, key, value, app, actor_id, req, move, cb):
        if not value:
            self._migrated_cb(response.CalvinResponse(response.NOT_FOUND), app, actor_id, cb)
            return
        _log.analyze(self._node.id, "+", {'actor_id': actor_id, 'node_id': value['node_id']},
                                                                peer_node_id=value['node_id'])
        self._node.proto.actor_migrate(value['node_id'], CalvinCB(self._migrated_cb, app=app, actor_id=actor_id, cb=cb),
                                     actor_id, req, False, move)

    def _migrated_cb(self, status, app, actor_id, cb):
        app._migrated_actors[actor_id] = status
        _log.analyze(self._node.id, "+", {'actor_id': actor_id, 'status': status, 'statuses': app._migrated_actors})
        if any([s is None for s in app._migrated_actors.values()]):
            return
        # Done
        if cb:
            cb(status=response.CalvinResponse(all([s for s in app._migrated_actors.values()])))

class Deployer(object):

    """
    Process an app_info dictionary (output from calvin parser) to
    produce a running calvin application.
    """

    def __init__(self, deployable, node, name=None, deploy_info=None, credentials=None, verify=True, cb=None):
        super(Deployer, self).__init__()
        self.deployable = deployable
        self.deploy_info = deploy_info
        self.credentials = credentials
        self.sec = Security()
        self.sec.set_principal(self.credentials)
        self.actorstore = ActorStore(security=self.sec)
        self.actor_map = {}
        self.actor_connections = {}
        self.node = node
        self.verify = verify
        self.cb = cb
        self._deploy_cont_done = False
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
        self.group_components()
        _log.analyze(self.node.id, "+ SECURITY", {'sec': str(self.sec)})

    # TODO Make deployer use the Application class group_components, component_name and get_req
    def group_components(self):
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
        _log.analyze(self.node.id, "+ SECURITY", {'sec': str(self.sec)})
        found, is_primitive, actor_def = self.actorstore.lookup(actor_type)
        if not found or not is_primitive:
            raise Exception("Not known actor type: %s" % actor_type)

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
        actor_id = self.node.am.new(actor_type=actor_type, args=args, signature=signature, credentials=self.credentials)
        if req:
            self.node.am.actors[actor_id].requirements_add(req, extend=False)
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

    def select_actor(self, out_iter, kwargs, final, comp_name_desc):
        _log.analyze(self.node.id, "+", {'comp_name_desc': comp_name_desc}, tb=True)
        if final[0] and not kwargs['done']:
            kwargs['done'] = True
            for name, desc_list in kwargs['priority'].iteritems():
                if desc_list:
                    out_iter.append(desc_list[0])
            out_iter.final()
            return
        desc = comp_name_desc[1]
        try:
            # List of (found, is_primitive, info)
            actor_types = [self.actorstore.lookup(actor['actor_type'])
                                for actor in desc['component']['structure']['actors'].values()]
        except KeyError:
            actor_types = []
            # Not a component, shadow actor candidate, likely
            kwargs['priority'][comp_name_desc[0]].insert(0, comp_name_desc)
            comp_name_desc[1]['shadow_actor'] = True
            return
        except Exception as e:
            # FIXME Handled when security verification failed
            _log.exception("select_actor desc: %s" % desc)
            raise e
        if all([a[0] and a[1] for a in actor_types]):
            # All found and primitive (quite unlikely), insert after any primitive shadow actors in priority
            index = len([1 for a in kwargs['priority'][comp_name_desc[0]] if 'shadow_actor' in a[1]])
            kwargs['priority'][comp_name_desc[0]].insert(index, comp_name_desc)
            comp_name_desc[1]['shadow_component'] = actor_types
            return
        # A component containing shadow actors
        # TODO Dig deeper to priorities between shadow components, now just insert in order
        kwargs['priority'][comp_name_desc[0]].append(comp_name_desc)
        comp_name_desc[1]['shadow_component'] = actor_types

    def resolve_remote(self, deployables):
        all_desc_iters = dynops.List()
        store = GlobalStore(node=self.node)
        for actor_name, info in deployables.iteritems():
            desc_iter = store.global_lookup_iter(info['signature'], info['args'].keys())
            all_desc_iters.append((actor_name, desc_iter), trigger_iter=desc_iter)
        all_desc_iters.final()
        collect_desc_iter = dynops.Collect(all_desc_iters).set_name("collected_desc")
        select_iter = dynops.Map(self.select_actor, collect_desc_iter, done=False,
                                                         priority={k:[] for k in self.deployable['actors'].keys()},
                                                         eager=True).set_name("select_actor")
        select_iter.set_cb(self.deploy_unhandled_actors, select_iter)
        self.deploy_unhandled_actors(select_iter)

    def deploy_unhandled_actors(self, comp_name_desc):
        while True:
            try:
                name, desc = comp_name_desc.next()
                _log.analyze(self.node.id, "+", {'name': name, 'desc': desc}, tb=True)
            except StopIteration:
                # Done
                if self._deploy_cont_done:
                    return
                self._deploy_cont_done = True
                self.group_components()
                _log.analyze(self.node.id, "+ DONE", {'deployable': self.deployable, 'components': self.components})
                self._deploy_cont()
                return
            except dynops.PauseIteration:
                return
            if 'shadow_actor' in desc:
                _log.analyze(self.node.id, "+ SHADOW ACTOR", {'name': name})
                # It was a normal primitive shadow actor, just instanciate
                req = self.get_req(name)
                info = self.deployable['actors'][name]
                actor_id = self.instantiate_primitive(name, info['actor_type'], info['args'], req, info['signature'])
                if not actor_id:
                    _log.error("Second phase, could not make shadow actor %s!" % info['actor_type'])
                self.actor_map[name] = actor_id
                self.node.app_manager.add(self.app_id, actor_id)
            elif 'shadow_component' in desc:
                _log.analyze(self.node.id, "+ SHADOW COMPONENT", {'name': name})
                # A component that needs to be broken up into individual primitive actors
                # First get the info and remove the component
                req = self.get_req(name)
                info = self.deployable['actors'][name]
                self.deployable['actors'].pop(name)
                # Then add the new primitive actors
                for actor_name, actor_desc in desc['component']['structure']['actors'].iteritems():
                    args = {k: v[1] if v[0] == 'VALUE' else info['args'][v[1]] for k, v in actor_desc['args'].iteritems()}
                    inports = [c['dst_port'] for c in desc['component']['structure']['connections'] if c['dst'] == actor_name]
                    outports = [c['src_port'] for c in desc['component']['structure']['connections'] if c['src'] == actor_name]
                    sign_desc = {'is_primitive': True,
                                 'actor_type': actor_desc['actor_type'],
                                 'inports': inports[:],
                                 'outports': outports[:]}
                    sign = GlobalStore.actor_signature(sign_desc)
                    self.deployable['actors'][name + ":" + actor_name] = {'args': args,
                                                                          'actor_type': actor_desc['actor_type'],
                                                                          'signature_desc': sign_desc,
                                                                          'signature': sign}
                    # Replace component connections with actor connection
                    #   outports
                    comp_outports = [(c['dst_port'], c['src_port']) for c in desc['component']['structure']['connections']
                                        if c['src'] == actor_name and c['dst'] == "."]
                    for c_port, a_port in comp_outports:
                        if (name + "." + c_port) in self.deployable['connections']:
                            self.deployable['connections'][name + ":" + actor_name + "." + a_port] = \
                                self.deployable['connections'].pop(name + "." + c_port)
                    #   inports
                    comp_inports = [(c['src_port'], c['dst_port']) for c in desc['component']['structure']['connections']
                                        if c['dst'] == actor_name and c['src'] == "."]
                    for outport, ports in self.deployable['connections'].iteritems():
                        for c_inport, a_inport in comp_inports:
                            if (name + "." + c_inport) in ports:
                                ports.remove(name + "." + c_inport)
                                ports.append(name + ":" + actor_name + "." + a_inport)
                    _log.analyze(self.node.id, "+ REPLACED PORTS", {'comp_outports': comp_outports,
                                                                   'comp_inports': comp_inports,
                                                                   'actor_name': actor_name,
                                                                   'connections': self.deployable['connections']})
                    # Add any new component internal connections (enough with outports)
                    for connection in desc['component']['structure']['connections']:
                        if connection['src'] == actor_name and connection['src_port'] in outports and connection['dst'] != ".":
                            self.deployable['connections'].setdefault(
                                name + ":" + actor_name + "." + connection['src_port'], []).append(
                                    name + ":" + connection['dst'] + "." + connection['dst_port'])
                    _log.analyze(self.node.id, "+ ADDED PORTS", {'connections': self.deployable['connections']})
                    # Instanciate it
                    actor_id = self.instantiate_primitive(name + ":" + actor_name, actor_desc['actor_type'], args, req, sign)
                    if not actor_id:
                        _log.error("Third phase, could not make shadow actor %s!" % info['actor_type'])
                    self.actor_map[name + ":" + actor_name] = actor_id
                    self.node.app_manager.add(self.app_id, actor_id)


    def deploy(self):
        """
        Instantiate actors and link them together.
        """
        if not self.deployable['valid']:
            raise Exception("Deploy information is not valid")

        # Authenticate Security instance once
        self.sec.authenticate_principal()

        unhandled = {}

        for actor_name, info in self.deployable['actors'].iteritems():
            try:
                self.instantiate(actor_name, info['actor_type'], info['args'], signature=info['signature'])
            except:
                unhandled[actor_name] = info

        if unhandled:
            _log.analyze(self.node.id, "+ UNHANDLED", {'unhandled': unhandled})
            self.resolve_remote(unhandled)
            return

        self._deploy_cont()

    def _deploy_cont(self):
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

