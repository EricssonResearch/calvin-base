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
import copy
import uuid

from calvin.common.calvin_callback import CalvinCB
from calvin.common import dynops
from calvin.common import calvinlogger
from calvin.runtime.north.plugins.requirements import req_operations
import calvin.common.calvinresponse as response
from calvin.common.requirement_matching import ReqMatch

_log = calvinlogger.get_logger(__name__)


def get_req(actor_name, deploy_info):
    """
    Start searching from the most specific requirement,
    then advance higher up in the component hierarchy until a requirement is found.
    """
    # N.B. self.ns should always exist (= script name)
    # Check for existence of deploy info
    if not deploy_info or 'requirements' not in deploy_info:
        return []
    # Trim of script name
    _, name = actor_name.split(':', 1)
    parts = name.split(':')
    req = []
    while parts and not req:
        current = ':'.join(parts)
        req = deploy_info['requirements'].get(current, [])
        parts = parts[:-1]
    return req


def group_components(namespace, actors):
    import json
    try:
        return _group_components(namespace, actors)
    except Exception as e:
        _log.info(f"Failed to group componens {e}")
        _log.info(f"namespace: {namespace}")
        _log.info(f"actors: {json.dumps(actors, indent=2, default=str)}")
        raise e


def _group_components(namespace, actors):
    components = {}
    l = (len(namespace)+1) if namespace else 0
    for name in actors.keys():
        if name.find(':', l) > -1:
            # This is part of a component
            # component name including optional namespace
            component = ':'.join(name.split(':')[0:(2 if namespace else 1)])
            if component in components:
                components[component].append(name)
            else:
                components[component] = [name]
    return components


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
        return list(self.actors.keys())

    def get_actor_name_map(self, ns):
        actors = {v: [k] for k, v in iter(self.actors.items()) if v is not None}
        # Collect all actors under top component name
        components = {}
        l = (len(ns)+1) if ns else 0
        for name, _id in actors.items():
            if name.find(':', l) > -1:
                # This is a component
                # component name including optional namespace
                component = ':'.join(name.split(':')[0:(2 if ns else 1)])
                if component in components:
                    components[component] += _id
                else:
                    components[component] = _id
        actors.update(components)
        return actors

    def __str__(self):
        s = "id: " + self.id + "\n"
        s += "name: " + self.name + "\n"
        for _id, name in self.actors.items():
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
        return sum([len(a) for a in self.node_info.values()]) == len(self.actors)


class AppManager(object):

    """ Manage deployed applications """

    def __init__(self, node):
        self._node = node
        self.storage = node.storage
        self._applications = {}

    @property
    def applications(self):
        return self._applications

    def new(self, name):
        application_id = str(uuid.uuid4())
        self._applications[application_id] = Application(application_id, name, self._node.id, self._node.am)
        self._node.control.log_application_new(application_id, name)
        return application_id

    def add(self, application_id, actor_id):
        """ Add an actor """
        if application_id in self._applications:
            self._applications[application_id].add_actor(actor_id)
        else:
            _log.error("Non-existing application id (%s) specified" % application_id)
            return

    def req_done(self, status, placement=None):
        _log.analyze(self._node.id, "+", {'status': str(status), 'placement': placement}, tb=True)

    def finalize(self, application_id, migrate=False, cb=None):
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'migrate': migrate, 'cb': str(cb)})
        if application_id not in self._applications:
            _log.error("Non existing application id (%s) specified" % application_id)
            return
        self.storage.add_application(self._applications[application_id])
        if migrate:
            self.execute_requirements(application_id, cb if cb else self.req_done)
        elif cb:
            cb(status=response.CalvinResponse(True))

    def destroy(self, application_id, cb):
        """ Destroy an application and its actors """
        _log.analyze(self._node.id, "+", {'application_id': application_id})
        if application_id in self._applications:
            self._destroy(self._applications[application_id], cb=cb)
        else:
            self.storage.get_application(application_id, CalvinCB(self._destroy_app_info_cb, cb=cb))

    def _destroy_app_info_cb(self, key, value, cb):
        application_id = key
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'value': value})
        _log.debug("Destroy app info %s: %s" % (application_id, value))
        if response.isnotfailresponse(value):
            self._destroy(Application(application_id, value['name'], value['origin_node_id'],
                                      self._node.am, value['actors_name_map']), cb=cb)
        elif cb:
            cb(status=response.CalvinResponse(response.NOT_FOUND))

    def _destroy(self, application, cb):
        _log.analyze(self._node.id, "+", {'actors': application.actors})
        application.destroy_cb = cb
        try:
            del application._destroy_node_ids
        except:
            pass
        application.clear_node_info()
        for actor_id in application.actors:
            if actor_id in self._node.am.list_actors():
                application.update_node_info(self._node.id, actor_id)
            else:
                _log.analyze(self._node.id, "+ REMOTE ACTOR", {'actor_id': actor_id})
                self.storage.get_actor(actor_id, CalvinCB(func=self._destroy_actor_cb, application=application))

        if application.complete_node_info():
            # All actors were local
            _log.analyze(self._node.id, "+ DONE", {'actors': application.actors})
            self._destroy_final(application)

    def _destroy_actor_cb(self, key, value, application, retries=0):
        """ Get actor callback """
        _log.analyze(self._node.id, "+", {'actor_id': key, 'value': value, 'retries': retries})
        if response.isnotfailresponse(value) and 'node_id' in value:
            application.update_node_info(value['node_id'], key)
        else:
            if retries < 10:
                # FIXME add backoff time
                _log.analyze(self._node.id, "+ RETRY", {'actor_id': key, 'value': value, 'retries': retries})
                self.storage.get_actor(key, CalvinCB(func=self._destroy_actor_cb,
                                                     application=application, retries=(retries+1)))
            else:
                # FIXME report failure
                _log.analyze(self._node.id, "+ GIVE UP", {'actor_id': key, 'value': value, 'retries': retries})
                application.update_node_info(None, key)

        if application.complete_node_info():
            _log.debug("_destroy_actor_cb final")
            self._destroy_final(application)

    def _destroy_final(self, application):
        """ Final destruction of the application on this node and send request to peers to also destroy the app """
        _log.analyze(self._node.id, "+ BEGIN 1",
                     {'node_info': application.node_info, 'origin_node_id': application.origin_node_id})
        if hasattr(application, '_destroy_node_ids'):
            # Already called
            return
        _log.analyze(self._node.id, "+ BEGIN 2",
                     {'node_info': application.node_info, 'origin_node_id': application.origin_node_id})
        application._destroy_node_ids = {n: None for n in application.node_info}
        for node_id, actor_ids in application.node_info.items():
            if not node_id:
                _log.analyze(self._node.id, "+ UNKNOWN NODE", {})
                application._destroy_node_ids[None] = response.CalvinResponse(False, data=actor_ids)
                continue
            if node_id == self._node.id:
                ok = True
                for actor_id in actor_ids:
                    if actor_id in self._node.am.list_actors():
                        _log.analyze(self._node.id, "+ LOCAL ACTOR", {'actor_id': actor_id})
                        try:
                            self._node.am.destroy(actor_id)
                        except:
                            ok = False
                application._destroy_node_ids[node_id] = response.CalvinResponse(ok)
                continue
            # Inform peers to destroy their part of the application
            self._node.proto.app_destroy(node_id, CalvinCB(self._destroy_final_cb, application, node_id),
                                         application.id, actor_ids)

        if application.id in self._applications:
            del self._applications[application.id]
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
            # Missing is the actors that could not be found.
            # FIXME retry? They could have moved
            missing = []
            for status in application._destroy_node_ids.values():
                missing += [] if status.data is None else status.data
            application.destroy_cb(status=response.CalvinResponse(False, data=missing))
        self._node.control.log_application_destroy(application.id)

    def destroy_request(self, application_id, actor_ids):
        """ Request from peer of local application parts destruction and related actors """
        _log.debug("Destroy request, app: %s, actors: %s" % (application_id, actor_ids))
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'actor_ids': actor_ids})
        reply = response.CalvinResponse(True)
        missing = []
        for actor_id in actor_ids:
            if actor_id in self._node.am.list_actors():
                self._node.am.destroy(actor_id)
            else:
                reply = response.CalvinResponse(False)
                missing.append(actor_id)
        reply.data = missing
        if application_id in self._applications:
            del self._applications[application_id]
        _log.debug("Destroy request reply %s" % reply)
        _log.analyze(self._node.id, "+ RESPONSE", {'reply': str(reply)})
        return reply

    def destroy_request_with_disconnect(self, application_id, actor_ids, terminate, callback=None):
        _log.analyze(self._node.id, "+", {'application_id': application_id, 'actor_ids': actor_ids})
        missing = []
        for actor_id in actor_ids[:]:
            if actor_id in self._node.am.list_actors():
                self._node.am.destroy_with_disconnect(actor_id, terminate,
                                                      callback=CalvinCB(self._destroy_request_with_disconnect_cb, application_id=application_id,
                                                                        actor_ids=actor_ids, actor_id=actor_id, callback=callback, missing=missing))
            else:
                self._destroy_request_with_disconnect_cb(
                    application_id=application_id, actor_ids=actor_ids, callback=callback,
                    missing=missing, actor_id=actor_id, status=response.CalvinResponse(False))

    def _destroy_request_with_disconnect_cb(self, application_id, actor_ids, missing, status, actor_id, callback=None):
        actor_ids.remove(actor_id)
        if not status:
            missing.append(actor_id)
        if actor_ids:
            return
        if application_id in self._applications:
            del self._applications[application_id]
        if callback:
            if missing:
                callback(status=response.CalvinResponse(False, data={'missing': missing}))
            else:
                callback(status=response.CalvinResponse(True))

    def list_applications(self):
        """ Returns list of applications """
        return list(self._applications.keys())

    ### DEPLOYMENT REQUIREMENTS ###

    def execute_requirements(self, application_id, cb):
        """ Build dynops iterator to collect all possible placements,
            then trigger migration.

            For initial deployment (all actors on the current node)
        """
        app = None
        try:
            app = self._applications[application_id]
        except:
            _log.debug("execute_requirements did not find app %s" % (application_id,))
            cb(status=response.CalvinResponse(False))
            return
        _log.debug("execute_requirements(app=%s)" % (self._applications[application_id],))

        if hasattr(app, '_org_cb'):
            # application deployment requirements ongoing, abort
            cb(status=response.CalvinResponse(False))
            return
        app._org_cb = cb
        app.actor_placement = {}  # Clean placement slate
        _log.analyze(self._node.id, "+ APP REQ", {}, tb=True)
        actor_ids = app.get_actors()
        app.actor_placement_nbr = len(actor_ids)
        for actor_id in actor_ids:
            if actor_id not in self._node.am.actors:
                _log.debug("Only apply requirements to local actors")
                app.actor_placement[actor_id] = None
                continue
            _log.analyze(self._node.id, "+ ACTOR REQ", {'actor_id': actor_id}, tb=True)
            r = ReqMatch(self._node,
                         callback=CalvinCB(self.collect_placement, app=app, actor_id=actor_id))
            r.match_for_actor(actor_id)
            _log.analyze(self._node.id, "+ ACTOR REQ DONE", {'actor_id': actor_id}, tb=True)
        _log.analyze(self._node.id, "+ DONE", {'application_id': application_id}, tb=True)

    def collect_placement(self, app, actor_id, possible_placements, status):
        _log.analyze(self._node.id, "+ BEGIN", {}, tb=True)
        # TODO look at status
        app.actor_placement[actor_id] = possible_placements
        if len(app.actor_placement) < app.actor_placement_nbr:
            return
        # all possible actor placements derived
        _log.analyze(self._node.id, "+ ACTOR PLACEMENT", {'placement': app.actor_placement}, tb=True)
        status = response.CalvinResponse(True)
        if any([not n for n in app.actor_placement.values()]):
            # At least one actor have no required placement
            # Let them stay on this node
            app.actor_placement = {actor_id: set([self._node.id]) if placement is None else placement
                                   for actor_id, placement in iter(app.actor_placement.items())}
            # Status will indicate success, but be different than the normal OK code
            status = response.CalvinResponse(response.CREATED)
            _log.analyze(self._node.id, "+ MISS PLACEMENT",
                         {'app_id': app.id, 'placement': app.actor_placement}, tb=True)

        # Collect an actor by actor matrix stipulating a weighting 0.0 - 1.0 for their connectivity
        actor_ids, actor_matrix = self._actor_connectivity(app)

        # Get list of all possible nodes
        node_ids = set([])
        for possible_nodes in app.actor_placement.values():
            node_ids |= possible_nodes
        node_ids = list(node_ids)
        node_ids = [n for n in node_ids if not isinstance(n, dynops.InfiniteElement)]
        for actor_id, possible_nodes in app.actor_placement.items():
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
            # TODO: should also ask authorization server before selecting node to migrate to.
            _log.analyze(self._node.id, "+ WEIGHTS", {'actor_id': actor_id, 'weights': weights})
            #weighted_actor_placement[actor_id] = node_ids[weights.index(max(weights))]
            # Get a list of nodes in sorted weighted order
            weighted_actor_placement[actor_id] = [n for (w, n) in sorted(zip(weights, node_ids), reverse=True)]
        for actor_id, node_id in weighted_actor_placement.items():
            _log.debug("Actor deployment %s \t-> %s" % (app.actors[actor_id], node_id))
            # FIXME add callback that recreate the actor locally
            self._node.am.robust_migrate(actor_id, node_id[:], None)

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
        l = len(list_actors)
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
        if response.isfailresponse(value):
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND))
            return
        app = Application(app_id, value['name'], value['origin_node_id'],
                          self._node.am, actors=value['actors_name_map'], deploy_info=deploy_info)
        app.components = group_components(app.ns, app.actors)
        app._migrated_actors = {a: None for a in app.actors}
        for actor_id, actor_name in app.actors.items():
            req = get_req(actor_name, app.deploy_info)
            if not req:
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
        if response.isfailresponse(value):
            self._migrated_cb(response.CalvinResponse(response.NOT_FOUND), app, actor_id, cb)
            return
        _log.analyze(self._node.id, "+", {'actor_id': actor_id, 'node_id': value['node_id']},
                     peer_node_id=value['node_id'])
        self._node.proto.actor_migrate(value['node_id'], CalvinCB(self._migrated_cb, app=app, actor_id=actor_id, cb=cb),
                                       actor_id, req, False, move)

    def _migrated_cb(self, status, app, actor_id, cb, **kwargs):
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

    def __init__(self, deployable, node, cb=None):
        super(Deployer, self).__init__()
        self.app_info = deployable["app_info"]
        self.deploy_info = deployable["deploy_info"]
        self.actor_map = {}
        self.actor_connections = {}
        self.node = node
        self.app_manager = node.app_manager
        self.cb = cb
        self._verified_actors = {}
        self._instantiate_counter = 0
        self._requires_counter = 0
        self.name = self.app_info["name"]
        self.app_id = self.node.app_manager.new(self.name)
        self.ns = os.path.splitext(os.path.basename(self.name))[0]
        self.components = group_components(self.ns, self.app_info['actors'])


    def instantiate(self, actor_name, info, actor_def=None, cb=None):
        try:
            self._instantiate(actor_name, info, actor_def, cb)
        except Exception as e:
            # FIXME: what should happen here?
            _log.exception("Instantiate failed")
            raise e
        finally:
            if cb:
                cb()

    def _instantiate(self, actor_name, info, actor_def=None, cb=None):
        """
        Instantiate an actor.
          - 'actor_name' is <namespace>:<identifier>, e.g. app:src, or app:component:src
          - 'info' is information about the actor
             info['args'] is a dictionary of key-value arguments for this instance
             info['signature'] is the GlobalStore actor-signature to lookup the actor
        """

        def requirement_type(req):
            try:
                return req_operations[req['op']].req_type
            except:
                return "unknown"

        # TODO component ns needs to be stored in registry /component/<app-id>/ns[0]/ns[1]/.../actor_name: actor_id
        if 'port_properties' in self.app_info:
            port_properties = self.app_info['port_properties'].get(actor_name, None)
        else:
            port_properties = None
        info['args']['name'] = actor_name
        # TODO add requirements should be part of actor_manager new
        actor_id = self.node.am.new(actor_type=info['actor_type'], args=info['args'], signature=info['signature'],
                                    actor_def=actor_def, port_properties=port_properties)
        if not actor_id:
            raise Exception("Could not instantiate actor %s" % actor_name)
        deploy_req = get_req(actor_name, self.deploy_info)
        if deploy_req:
            # Placement requirements
            actor_reqs = [r for r in deploy_req if requirement_type(r)]
            # Placement requirements
            self.node.am.actors[actor_id].requirements_add(actor_reqs, extend=False)
            # Update requirements in registry
            self.node.storage.add_actor(self.node.am.actors[actor_id], self.node.id)

        # store actor requirements in registry
        actor = self.node.am.actors[actor_id]
        self._requires_counter += 1
        self.node.storage.add_actor_requirements(actor)

        self.actor_map[actor_name] = actor_id
        self.node.app_manager.add(self.app_id, actor_id)

    def deploy(self):
        """Verify actors, instantiate and link them together.
        """
        deploy_counter = 0

        def connect(src, dst, cb):
            # connect from dst to src
            dst_actor, port_name = dst.split('.')
            src_actor, peer_port_name = src.split('.')

            peer_node_id = self.node.id
            actor_id = self.actor_map[dst_actor]
            peer_actor_id = self.actor_map[src_actor]

            port_properties = {'direction': 'in'}
            peer_port_properties = {'direction': 'out'}

            self.node.pm.connect(actor_id=actor_id,
                                 port_name=port_name,
                                 port_properties=port_properties,
                                 peer_node_id=peer_node_id,
                                 peer_actor_id=peer_actor_id,
                                 peer_port_name=peer_port_name,
                                 peer_port_properties=peer_port_properties,
                                 callback=cb)

        def finalize():
            def wait_for_all_connections(status, *args, **kwargs):
                nonlocal connection_count
                nonlocal connection_status
                _log.debug(f"wait_for_all_connections {connection_count}")
                connection_count -= 1
                if not status:
                    # TODO handle connection errors
                    _log.error("Deployer failed a port connection status: %s port info: %s" %
                               (str(status), str(kwargs)))
                    connection_status = status
                if connection_count == 0:
                    _log.debug("wait_for_all_connections final")
                    if self._requires_counter >= len(self.app_info['actors']):
                        self.node.app_manager.finalize(self.app_id, migrate=bool(self.deploy_info),
                                                       cb=CalvinCB(self.cb, deployer=self))

            self._instantiate_counter += 1
            if self._instantiate_counter < len(self._verified_actors):
                return
            for component_name, actor_names in self.components.items():
                actor_ids = [self.actor_map[n] for n in actor_names]
                for actor_id in actor_ids:
                    self.node.am.actors[actor_id].component_add(actor_ids)

            for src, dst_list in self.app_info['connections'].items():
                if len(dst_list) > 1:
                    src_name, src_port = src.split('.')
                    _log.debug("GET PROPERTIES for %s, %s.%s" % (src, src_name, src_port))
                    current_properties = self.node.pm.get_port_properties(
                        actor_id=self.actor_map[src_name], port_dir='out', port_name=src_port)
                    kwargs = {'nbr_peers': len(dst_list)}
                    if 'routing' in current_properties and current_properties['routing'] != 'default':
                        kwargs['routing'] = current_properties['routing']
                    else:
                        kwargs['routing'] = 'fanout'
                    _log.debug("CURRENT PROPERTIES\n%s\n%s" % (current_properties, kwargs))
                    self.node.pm.set_port_properties(actor_id=self.actor_map[src_name], port_dir='out', port_name=src_port,
                                                     **kwargs)

            connection_count = sum(map(len, list(self.app_info['connections'].values())))
            connection_status = response.CalvinResponse(True)
            for src, dst_list in self.app_info['connections'].items():
                for dst in dst_list:
                    connect(src, dst, cb=wait_for_all_connections)

        def check_actor_requirements():
            nonlocal deploy_counter
            deploy_counter += 1
            if deploy_counter < len(self.app_info['actors']):
                return
            for actor_name, info in self._verified_actors.items():
                actor_info = info[0]
                actor_def = info[1]
                actor_reqs = actor_info["requires"]
                self.node.am.check_requirements(actor_reqs,
                                                callback=CalvinCB(self.instantiate,
                                                                  actor_name,
                                                                  actor_info,
                                                                  actor_def,
                                                                  cb=finalize))

        if not self.app_info['valid']:
            raise Exception("Deploy information is not valid")

        for actor_name, info in self.app_info['actors'].items():
            """
            Lookup and verify actor in actor store.
            - 'actor_name' is <namespace>:<identifier>, e.g. app:src, or app:component:src
            - 'info' is information about the actor
            """
            actor_type = info['actor_type']
            actor_def = self.node.actorstore.lookup_and_verify_actor(actor_type)
            info['requires'] = actor_def.requires if hasattr(actor_def, "requires") else []
            self._verified_actors[actor_name] = (info, actor_def)
            check_actor_requirements()
