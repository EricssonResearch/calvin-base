# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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



import json

from calvin.common import calvinresponse
from calvin.common.calvinlogger import get_logger
from calvin.common.calvin_callback import CalvinCB
from calvin.common.issuetracker import IssueTracker
# from calvin.csparser import cscompile as compiler
# from calvin.csparser.dscodegen import calvin_dscodegen
from calvin.runtime.north.appmanager import Deployer
from calvin.runtime.north.plugins.port import DISCONNECT
from .routes import register, handler

_log = get_logger(__name__)


# USED BY: GUI, CSWEB, CSCONTROL
@handler(method="GET", path="/applications")

def handle_get_applications(self, handle, match, data, hdr):
    """
    GET /applications
    Get applications launched from this node
    Response status code: OK
    Response: List of application ids
    """
    self.send_response(handle, json.dumps(self.node.app_manager.list_applications()))

# USED BY: GUI, CSWEB, CSCONTROL
@handler(method="DELETE", path="/application/{application_id}")

def handle_del_application(self, handle, match, data, hdr):
    """
    DELETE /application/{application-id}
    Stop application (only applications launched from this node)
    Response status code: OK, NOT_FOUND, INTERNAL_ERROR
    Response: [<actor_id>, ...] when error list of actors in application not destroyed
    """
    try:
        self.node.app_manager.destroy(match.group(1), cb=CalvinCB(self.handle_del_application_cb,
                                                                    handle))
    except:
        _log.exception("Destroy application failed")
        self.send_response(handle, None, status=calvinresponse.INTERNAL_ERROR)

@register
def handle_del_application_cb(self, handle, status=None):
    if not status and status.data:
        data = json.dumps(status.data)
    else:
        data = None
    self.send_response(handle, data, status=status.status)

# USED BY: GUI, CSCONTROL
@handler(method="GET", path="/actors")

def handle_get_actors(self, handle, match, data, hdr):
    """
    GET /actors
    Get list of actors on this runtime
    Response status code: OK
    Response: list of actor ids
    """
    actors = self.node.am.list_actors()
    self.send_response(
        handle, json.dumps(actors))

@register
def _actor_report(self, handle, match, data, hdr):
    try:
        # Now we allow passing in arguments (must be dictionary or None)
        report = self.node.am.report(match.group(1), data)
        status = calvinresponse.OK
    except:
        _log.exception("Actor report failed")
        report = None
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, json.dumps([]) if report is None else json.dumps(report, default=repr), status=status)

# DEPRECATED: Perhaps used in Kappa?
@handler(method="GET", path="/actor/{actor_id}/report")

def handle_get_actor_report(self, handle, match, data, hdr):
    """
    GET /actor/{actor-id}/report
    Some actor store statistics on inputs and outputs, this reports these. Not always present.
    Response status code: OK or NOT_FOUND
    Response: Depends on actor
    """
    self._actor_report(handle, match, data, hdr)

# DEPRECATED: Perhaps used in Kappa?
@handler(method="POST", path="/actor/{actor_id}/report")

def handle_post_actor_report(self, handle, match, data, hdr):
    """
    POST /actor/{actor-id}/report
    Some actors accept external input using this function. Not always present.
    Response status code: OK or NOT_FOUND
    Response: Depends on actor
    """
    self._actor_report(handle, match, data, hdr)


@register
def handle_actor_migrate_proto_cb(self, handle, status, *args, **kwargs):
    self.send_response(handle, None, status=status.status)

@register
def handle_actor_migrate_lookup_peer_cb(self, key, value, handle, actor_id, peer_node_id):
    if calvinresponse.isnotfailresponse(value):
        self.node.proto.actor_migrate_direct(value['node_id'],
            CalvinCB(self.handle_actor_migrate_proto_cb, handle),
            actor_id,
            peer_node_id)
    else:
        self.send_response(handle, None, status=calvinresponse.NOT_FOUND)

# USED BY: GUI, CSWEB, CSCONTROL
@handler(method="POST", path="/actor/{actor_id}/migrate")

def handle_actor_migrate(self, handle, match, data, hdr):
    """
    POST /actor/{actor-id}/migrate
    Migrate actor to (other) node, either explicit node_id or by updated requirements
    Body: {"peer_node_id": <node-id>}
    Alternative body:
    Body:
    {
        "requirements": [ {"op": "<matching rule name>",
                          "kwargs": {<rule param key>: <rule param value>, ...},
                          "type": "+" or "-" for set intersection or set removal, respectively
                          }, ...
                        ],
        "extend": True or False  # defaults to False, i.e. replace current requirements
        "move": True or False  # defaults to False, i.e. when possible stay on the current node
    }

    For further details about requirements see application deploy.
    Response status code: OK, BAD_REQUEST, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    status = calvinresponse.OK
    actor_id = match.group(1)
    if 'peer_node_id' in data:
        if actor_id in self.node.am.list_actors():
            try:
                self.node.am.migrate(actor_id, data['peer_node_id'],
                                 callback=CalvinCB(self.actor_migrate_cb, handle))
            except:
                _log.exception("Migration failed")
                status = calvinresponse.INTERNAL_ERROR
        else:
            self.node.storage.get_actor(actor_id,
                CalvinCB(func=self.handle_actor_migrate_lookup_peer_cb, handle=handle,
                    actor_id=actor_id, peer_node_id=data['peer_node_id']))
    elif 'requirements' in data:
        try:
            self.node.am.update_requirements(match.group(1), data['requirements'],
                extend=data['extend'] if 'extend' in data else False,
                move=data['move'] if 'move' in data else False,
                callback=CalvinCB(self.actor_migrate_cb, handle))
        except:
            _log.exception("Migration failed")
            status = calvinresponse.INTERNAL_ERROR
    else:
        status=calvinresponse.BAD_REQUEST

    if status != calvinresponse.OK:
        self.send_response(handle, None, status=status)

@register
def actor_migrate_cb(self, handle, status, *args, **kwargs):
    """ Migrate actor respons
    """
    self.send_response(handle, None, status=status.status)


# USED BY: GUI, CSWEB
@handler(method="GET", path="/actor/{actor_id}/port/{port_id}/state")

def handle_get_port_state(self, handle, match, data, hdr):
    """
    GET /actor/{actor-id}/port/{port-id}/state
    Get port state {port-id} of actor {actor-id}
    Response status code: OK or NOT_FOUND
    """
    state = {}
    try:
        state = self.node.am.get_port_state(match.group(1), match.group(2))
        status = calvinresponse.OK
    except:
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, json.dumps(state), status)

# FIXME: Check integrity according to policy
# USED BY: GUI, CSWEB, CSCONTROL
@handler(method="POST", path="/deploy")

def handle_deploy(self, handle, match, data, hdr):
    """
    POST /deploy
    Compile and deploy a calvin script to this calvin node
    Apply deployment requirements to actors of an application
    and initiate migration of actors accordingly
    Body:
    {
        "app_info": ...
        "app_info_signature": <hex encoded signature based on app_info (JSON, compact, sorted)
        "deploy_info": ...
    }

    Response status code: OK, CREATED, BAD_REQUEST, UNAUTHORIZED or INTERNAL_ERROR
    Response: {"application_id": <application-id>,
               "actor_map": {<actor name with namespace>: <actor id>, ...}
               "placement": {<actor_id>: <node_id>, ...},
               "requirements_fulfilled": True/False}
    Failure response: {'errors': <compilation errors>,
                       'warnings': <compilation warnings>,
                       'exception': <exception string>}
    """

    def deploy_cb(status, placement=None, **kwargs):
        _log.analyze(self.node.id, "+ DEPLOYED", {'status': status.status})
        _log.info(f"DEPLOY: {json.dumps(kwargs, indent=2)}")
        if status and deployer.app_id:
            print("DEPLOY STATUS", str(status))
            response = {'application_id': deployer.app_id,
                        'actor_map': deployer.actor_map,
                        'placement': placement,
                        'requirements_fulfilled': status.status == calvinresponse.OK}
            self.send_response(handle,
                            json.dumps(response),
                            status=status.status)
        else:
            self.send_response(handle, None, status=status.status)
    try:
        # FIXME: Clean up deployer next
        deployer = Deployer(
                deployable=data,
                node=self.node,
                cb=deploy_cb
            )
        print(self.node.id, "Deployer instantiated")
        deployer.deploy()
    except Exception as e:
        _log.exception(f"Deployer failed: {e}")
        self.send_response(
            handle,
            json.dumps({'exception': str(e)}),
            status=calvinresponse.INTERNAL_ERROR
        )



# USED BY: GUI, CSWEB, CSCONTROL
@handler(method="POST", path="/application/{application_id}/migrate")

def handle_post_application_migrate(self, handle, match, data, hdr):
    """
    POST /application/{application-id}/migrate
    Update deployment requirements of application application-id
    and initiate migration of actors.
    Body:
    {
        "deploy_info":
           {"requirements": {
                "<actor instance 1 name>": [ {"op": "<matching rule name>",
                                              "kwargs": {<rule param key>: <rule param value>, ...},
                                              "type": "+" or "-" for set intersection or set removal, respectively
                                              }, ...
                                           ],
                ...
                            }
           }
    }
    For more details on deployment information see application deploy.
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    app_id = match.group(1)
    try:
        self.node.app_manager.migrate_with_requirements(app_id,
                                               deploy_info=data["deploy_info"] if "deploy_info" in data else None,
                                               move=data["move"] if "move" in data else False,
                                               cb=CalvinCB(self.handle_post_application_migrate_cb, handle))
    except:
        _log.exception("App migration failed")
        self.send_response(handle, None, status=calvinresponse.INTERNAL_ERROR)

@register
def handle_post_application_migrate_cb(self, handle, status, **kwargs):
    _log.analyze(self.node.id, "+ MIGRATED", {'status': status.status})
    self.send_response(handle, None, status=status.status)
