# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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

import re
import time
import json
from random import randint
from calvin.csparser import cscompile as compiler
from calvin.csparser.dscodegen import calvin_dscodegen
from calvin.runtime.north.appmanager import Deployer
from calvin.runtime.north import metering
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.attribute_resolver import format_index_string
from calvin.runtime.south.plugins.async import server_connection, async
from calvin.runtime.north.plugins.port import DISCONNECT
from urlparse import urlparse
from calvin.requests import calvinresponse
from calvin.utilities.security import Security, security_enabled
from calvin.actorstore.store import DocumentationStore
from calvin.utilities import calvinuuid
from calvin.utilities.issuetracker import IssueTracker
_log = get_logger(__name__)

uuid_re = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Base
re_get_base_doc = re.compile(r"GET /\sHTTP/1")

control_api_doc = ""

control_api_doc += \
    """
    GET /actor_doc {path}
    Get documentation in 'raw' format for actor or module at {path}
    Path is formatted as '/{module}/{submodule}/ ... /{actor}'.
    If {path} is empty return top-level documentation.
    See DocumentStore help_raw() for details on data format.
    Response status code: OK
    Response: dictionary with documentation
"""
re_get_actor_doc = re.compile(r"GET /actor_doc(\S*)\sHTTP/1")

control_api_doc += \
    """
    POST /log
    Register for log events and set actor and event filter.
    Body:
    {
        'user_id': <user_id>     # Optional user id
        'actors': [<actor-id>],  # Actors to log, empty list for all
        'events': [<event_type>] # Event types to log: actor_firing, action_result,
                                                       actor_new, actor_destroy, actor_migrate,
                                                       application_new, application_destroy
    }
    Response status code: OK or BAD_REQUEST
    Response:
    {
        'user_id': <user_id>,
        'epoch_year': <the year the epoch starts at Jan 1 00:00, e.g. 1970>
    }
"""
re_post_log = re.compile(r"POST /log\sHTTP/1")

control_api_doc += \
    """
    DELETE /log/{user-id}
    Unregister for trace data
    Response status code: OK or NOT_FOUND
"""
re_delete_log = re.compile(r"DELETE /log/(TRACE_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    GET /log/{user-id}
    Get streamed log events
    Response status code: OK or NOT_FOUND
    Content-Type: text/event-stream
    data:
    {
        'timestamp': <timestamp>,
        'node_id': <node_id>,
        'type': <event_type>, # event types: actor_fire, actor_new, actor_destroy, actor_migrate, application_new, application_destroy
        'actor_id',           # included in: actor_fire, actor_new, actor_destroy, actor_migrate
        'actor_name',         # included in: actor_new
        'actor_is_shadow'     # included in: actor_new
        'action_method',      # included in: actor_fire
        'consumed',           # included in: actor_fire
        'produced'            # included in: actor_fire
        'action_result'       # included in: actor_fire
        'actor_type',         # included in: actor_new
        'dest_node_id',       # included in: actor_migrate
        'application_name',   # included in: application_new
        'application_id'      # included in: application, application_destroy
    }
"""
re_get_log = re.compile(r"GET /log/(TRACE_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    GET /id
    Get id of this calvin node
    Response status code: OK
    Response: node-id
"""
re_get_node_id = re.compile(r"GET /id\sHTTP/1")

control_api_doc += \
    """
    GET /capabilities
    Get capabilities of this calvin node
    Response status code: OK
    Response: list of capabilities
"""
re_get_node_capabilities = re.compile(r"GET /capabilities\sHTTP/1")


control_api_doc += \
    """
    GET /nodes
    List nodes in network (excluding self) known to self
    Response status code: OK
    Response: List of node-ids
"""
re_get_nodes = re.compile(r"GET /nodes\sHTTP/1")

control_api_doc += \
    """
    GET /node/{node-id}
    Get information on node node-id
    Response status code: OK or NOT_FOUND
    Response:
    {
        "attributes": {...},
        "control_uri": "http(s)://<address>:<controlport>",
        "uri": "calvinip://<address>:<port>"
    }
"""
re_get_node = re.compile(r"GET /node/(NODE_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    POST /node/{node-id}/attributes/indexed_public
    Set indexed_public attributes on node with node-id
    Body:
    {
        "node_name": {"organization": <organization>, "organizationalUnit": <organizationalUnit>, "purpose": <purpose>, "group": <group>, "name": <name>},
        "owner": {"organization": <organization>, "organizationalUnit": <organizationalUnit>, "role": <role>, "personOrGroup": <personOrGroup>},
        "address": {"country": <country>, "stateOrProvince": <stateOrProvince>, "locality": <locality>, "street": <street>, "streetNumber": <streetNumber>, "building": <building>, "floor": <floor>, "room": <room>}
    }
    Response status code: OK, UNAUTHORIZED or INTERNAL_ERROR
"""
re_post_node_attribute_indexed_public = re.compile(r"POST /node/(NODE_" + uuid_re + "|" + uuid_re + ")/attributes/indexed_public\sHTTP/1")

control_api_doc += \
    """
    POST /peer_setup
    Add calvin nodes to network
    Body: {"peers: ["calvinip://<address>:<port>", ...] }
    Response status code: OK or SERVICE_UNAVAILABLE
    Response: {<peer control uri>: [<peer node id>, <per peer status>], ...}
"""
re_post_peer_setup = re.compile(r"POST /peer_setup\sHTTP/1")

control_api_doc += \
    """
    GET /applications
    Get applications launched from this node
    Response status code: OK
    Response: List of application ids
"""
re_get_applications = re.compile(r"GET /applications\sHTTP/1")

control_api_doc += \
    """
    GET /application/{application-id}
    Get information on application application-id
    Response status code: OK or NOT_FOUND
    Response:
    {
         "origin_node_id": <node id>,
         "actors": <list of actor ids>
         "name": <name or id of this application>
    }
"""
re_get_application = re.compile(r"GET /application/(APP_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    DELETE /application/{application-id}
    Stop application (only applications launched from this node)
    Response status code: OK, NOT_FOUND, INTERNAL_ERROR
    Response: [<actor_id>, ...] when error list of actors (replicas) in application not destroyed
"""
re_del_application = re.compile(r"DELETE /application/(APP_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    POST /actor
    Create a new actor
    Body:
    {
        "actor_type:" <type of actor>,
        "args" : { "name": <name of actor>, <actor argument>:<value>, ... }
        "deploy_args" : {"app_id": <application id>, "app_name": <application name>} (optional)
    }
    Response status code: OK or INTERNAL_ERROR
    Response: {"actor_id": <actor-id>}
"""
re_post_new_actor = re.compile(r"POST /actor\sHTTP/1")

control_api_doc += \
    """
    GET /actors
    Get list of actors on this runtime
    Response status code: OK
    Response: list of actor ids
"""
re_get_actors = re.compile(r"GET /actors\sHTTP/1")

control_api_doc += \
    """
    GET /actor/{actor-id}
    Get information on actor
    Response status code: OK or NOT_FOUND
    Response:
    {
        "inports": list inports
        "node_id": <node-id>,
        "type": <actor type>,
        "name": <actor name>,
        "outports": list of outports
    }
"""
re_get_actor = re.compile(r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    DELETE /actor/{actor-id}
    Delete actor
    Response status code: OK or NOT_FOUND
    Response: none
"""
re_del_actor = re.compile(r"DELETE /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    GET /actor/{actor-id}/report
    Some actor store statistics on inputs and outputs, this reports these. Not always present.
    Response status code: OK or NOT_FOUND
    Response: Depends on actor
"""
re_actor_report = re.compile(r"(?:GET|POST) /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/report\sHTTP/1")

control_api_doc += \
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
re_post_actor_migrate = re.compile(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/migrate\sHTTP/1")

control_api_doc += \
    """
    POST /actor/{actor-id}/disable
    DEPRECATED. Disables an actor
    Response status code: OK or NOT_FOUND
    Response: none
"""
re_post_actor_disable = re.compile(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/disable\sHTTP/1")

# control_api_doc += \
"""
    GET /actor/{actor-id}/port/{port-id}
    Get information on port {port-id} of actor {actor-id}
    Response status code: OK or NOT_FOUND
"""
re_get_port = re.compile(
    r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/port/(PORT_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    POST /actor/{actor-id}/replicate
    ONLY FOR TEST. Will replicate an actor directly
    Response status code: OK or NOT_FOUND
    Response: {'actor_id': <replicated actor instance id>}
"""
re_post_actor_replicate = re.compile(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/replicate\sHTTP/1")

# control_api_doc += \
"""
    GET /actor/{actor-id}/port/{port-id}/state
    Get port state {port-id} of actor {actor-id}
    Response status code: OK or NOT_FOUND
"""
re_get_port_state = re.compile(
    r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/port/(PORT_" + uuid_re + "|" + uuid_re + ")/state\sHTTP/1")

control_api_doc += \
    """
    POST /connect
    Connect actor ports
    Body:
    {
        "actor_id" : <actor-id>,
        "port_name": <port-name>,
        "port_dir": <in/out>,
        "peer_node_id": <node-id>,
        "peer_actor_id": <actor-id>,
        "peer_port_name": <port-name>,
        "peer_port_dir": <out/in>
    }
    Response status code: OK, BAD_REQUEST, INTERNAL_ERROR or NOT_FOUND
    Response: {"peer_port_id": <peer port id>}
"""
re_post_connect = re.compile(r"POST /connect\sHTTP/1")

control_api_doc += \
    """
    POST /set_port_property
    Sets a property of the port.
    Body:
    {
        "actor_id" : <actor-id>,
        "port_type": <in/out>,
        "port_name": <port-name>,
        "port_id": <port-id>, optionally instead of the above identifiers
        "port_property": <property-name as string>
        "value" : <property value>
    }
    Response status code: OK, BAD_REQUEST or NOT_FOUND
    Response: none
"""
re_set_port_property = re.compile(r"POST /set_port_property\sHTTP/1")

control_api_doc += \
    """
    POST /deploy
    Compile and deploy a calvin script to this calvin node
    Apply deployment requirements to actors of an application
    and initiate migration of actors accordingly
    Body:
    {
        "name": <application name>,
        "script": <calvin script>  # alternativly "app_info"
        "app_info": <compiled script as app_info>  # alternativly "script"
        "sec_sign": {<cert hash>: <security signature of script>, ...} # optional and only with "script"
        "sec_credentials": <security credentials of user> # optional
        "deploy_info":
           {"groups": {"<group 1 name>": ["<actor instance 1 name>", ...]},  # TODO not yet implemented
            "requirements": {
                "<actor instance 1 name>": [ {"op": "<matching rule name>",
                                              "kwargs": {<rule param key>: <rule param value>, ...},
                                              "type": "+" or "-" for set intersection or set removal, respectively
                                              }, ...
                                           ],
                ...
                            }
           }
    }
    Note that either a script or app_info must be supplied. Optionally security
    verification of application script can be made. Also optionally user credentials
    can be supplied, some runtimes are configured to require credentials. The
    credentials takes for example the following form:
        {"user": <username>,
         "password": <password>,
         "role": <role>,
         "group": <group>,
         ...
        }

    The matching rules are implemented as plug-ins, intended to be extended.
    The type "+" is "and"-ing rules together (actually the intersection of all
    possible nodes returned by the rules.) The type "-" is explicitly removing
    the nodes returned by this rule from the set of possible nodes. Note that
    only negative rules will result in no possible nodes, i.e. there is no
    implied "all but these."

    A special matching rule exist, to first form a union between matching
    rules, i.e. alternative matches. This is useful for e.g. alternative
    namings, ownerships or specifying either of two specific nodes.
        {"op": "union_group",
         "requirements": [list as above of matching rules but without type key]
         "type": "+"
        }
    Other matching rules available is current_node, all_nodes and
    node_attr_match which takes an index param which is attribute formatted,
    e.g.
        {"op": "node_attr_match",
         "kwargs": {"index": ["node_name", {"organization": "org.testexample", "name": "testNode1"}]}
         "type": "+"
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
re_post_deploy = re.compile(r"POST /deploy\sHTTP/1")

control_api_doc += \
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
re_post_application_migrate = re.compile(r"POST /application/(APP_" + uuid_re + "|" + uuid_re + ")/migrate\sHTTP/1")

control_api_doc += \
    """
    POST /disconnect
    Disconnect a port.
    If port fields are empty, all ports of the actor are disconnected
    Body:
    {
        "actor_id": <actor-id>,
        "port_name": <port-name>,
        "port_dir": <in/out>,
        "port_id": <port-id>
    }
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_post_disconnect = re.compile(r"POST /disconnect\sHTTP/1")

control_api_doc += \
    """
    DELETE /node{/now|/migrate}
    Stop (this) calvin node
     now: stop the runtime without handling actors on the runtime [default]
     migrate: migrate any actors before stopping the runtime
    Response status code: ACCEPTED
    Response: none
"""
re_delete_node = re.compile(r"DELETE /node(?:/(now|migrate))?\sHTTP/1")

control_api_doc += \
    """
    POST /meter
    Register for metering information
    Body:
    {
        "user_id": <user-id> optional user id
    }
    Response status code: OK or BAD_REQUEST
    Response:
    {
        "user_id": <user-id>,
        "timeout": <seconds data is kept>,
        "epoch_year": <the year the epoch starts at Jan 1 00:00, e.g. 1970>
    }
"""
re_post_meter = re.compile(r"POST /meter\sHTTP/1")

control_api_doc += \
    """
    DELETE /meter/{user-id}
    Unregister for metering information
    Response status code: OK or NOT_FOUND
"""
re_delete_meter = re.compile(r"DELETE /meter/(METERING_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    GET /meter/{user-id}/timed
    Get timed metering information
    Response status code: OK or NOT_FOUND
    Response:
    {
        <actor-id>:
            [
                [<seconds since epoch>, <name of action>],
                ...
            ],
            ...
    }
"""
re_get_timed_meter = re.compile(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/timed\sHTTP/1")

control_api_doc += \
    """
    GET /meter/{user-id}/aggregated
    Get aggregated metering information
    Response status code: OK or NOT_FOUND
    Response:
    {
        'activity':
        {
            <actor-id>:
            {
                <action-name>: <total fire count>,
                ...
            },
            ...
        },
        'time':
        {
            <actor-id>: [<start time of counter>, <last modification time>],
            ...
        }
    }
"""
re_get_aggregated_meter = re.compile(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/aggregated\sHTTP/1")

control_api_doc += \
    """
    GET /meter/{user-id}/metainfo
    Get metering meta information on actors
    Response status code: OK or NOT_FOUND
    Response:
    {
        <actor-id>:
        {
            <action-name>:
            {
                'inports': {
                    <port-name> : <number of tokens per firing>,
                    ...
                           },
                'outports': {
                    <port-name> : <number of tokens per firing>,
                    ...
                           }
            },
            ...
        }
    }
"""
re_get_metainfo_meter = re.compile(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/metainfo\sHTTP/1")

control_api_doc += \
    """
    POST /index/{key}
    Store value under index key
    Body:
    {
        "value": <string>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
"""
re_post_index = re.compile(r"POST /index/([0-9a-zA-Z\.\-/_]*)\sHTTP/1")

control_api_doc += \
    """
    DELETE /index/{key}
    Remove value from index key
    Body:
    {
        "value": <string>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
"""
re_delete_index = re.compile(r"DELETE /index/([0-9a-zA-Z\.\-/_]*)\sHTTP/1")

control_api_doc += \
    """
    GET /index/{key}
    Fetch values under index key
    Response status code: OK or NOT_FOUND
    Response: {"result": <list of strings>}
"""
re_get_index = re.compile(r"GET /index/([0-9a-zA-Z\.\-/_]*)\sHTTP/1")

control_api_doc += \
    """
    GET /storage/{prefix-key}
    Fetch value under prefix-key
    Response status code: OK or NOT_FOUND
    Response: {"result": <value>}
"""
re_get_storage = re.compile(r"GET /storage/([0-9a-zA-Z\.\-/_]*)\sHTTP/1")

control_api_doc += \
    """
    GET /dumpstorage
    Dump storage to temporary file in /tmp when available
    Response status code: OK
    Response: none
"""
re_dump_storage = re.compile(r"GET /dumpstorage\sHTTP/1")

control_api_doc += \
    """
    POST /storage/{prefix-key}
    Store value under prefix-key
    Body:
    {
        "value": <string>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
"""
re_post_storage = re.compile(r"POST /storage/([0-9a-zA-Z\.\-/_]*)\sHTTP/1")

control_api_doc += \
    """
    POST /certiticate_authority/certificate_signing_request
    Send CSR to CA, that creates a x509 certificate and returns it
    Response status code: OK or INTERNAL_ERROR
    Response:
    {"certificate":<value>}
"""
re_post_certificate_signing_request = re.compile(r"POST /certificate_authority/certificate_signing_request\sHTTP/1")

control_api_doc += \
    """
    GET /authentication/users_db
    Get user database on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
"""
re_get_authentication_users_db = re.compile(r"GET /authentication/users_db\sHTTP/1")

control_api_doc += \
    """
    PUT /authentication/users_db
    Update user database
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_edit_authentication_users_db = re.compile(r"PUT /authentication/users_db\sHTTP/1")

control_api_doc += \
    """
    GET /authentication/groups_db
    Get user database on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
"""
re_get_authentication_groups_db = re.compile(r"GET /authentication/groups_db\sHTTP/1")

control_api_doc += \
    """
    PUT /authentication/groups_db
    Update user database
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_edit_authentication_groups_db = re.compile(r"PUT /authentication/groups_db\sHTTP/1")

control_api_doc += \
    """
    POST /authorization/policies
    Create a new policy
    Body: policy in JSON format
    Response status code: OK or INTERNAL_ERROR
    Response: {"policy_id": <policy-id>}
"""
re_post_new_authorization_policy = re.compile(r"POST /authorization/policies\sHTTP/1")

control_api_doc += \
    """
    GET /authorization/policies
    Get all policies on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
"""
re_get_authorization_policies = re.compile(r"GET /authorization/policies\sHTTP/1")

control_api_doc += \
    """
    GET /authorization/policies/{policy-id}
    Get policy
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: {"policy": policy in JSON format}
"""
re_get_authorization_policy = re.compile(r"GET /authorization/policies/(POLICY_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    PUT /authorization/policies/{policy-id}
    Update policy
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_edit_authorization_policy = re.compile(r"PUT /authorization/policies/(POLICY_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    DELETE /authorization/policies/{policy-id}
    Delete policy
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_del_authorization_policy = re.compile(r"DELETE /authorization/policies/(POLICY_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

control_api_doc += \
    """
    OPTIONS /url
    Request for information about the communication options available on url
    Response status code: OK
    Response: Available communication options
"""
# re_options = re.compile(r"OPTIONS /[0-9a-z/-_.]*\sHTTP/1.1")
re_options = re.compile(r"OPTIONS /[^\s]*\sHTTP/1")

_calvincontrol = None


def get_calvincontrol():
    """ Returns the CalvinControl singleton
    """
    global _calvincontrol
    if _calvincontrol is None:
        _calvincontrol = CalvinControl()
    return _calvincontrol


class Logger(object):

    """ Log object
    """

    def __init__(self, actors, events):
        self.handle = None
        self.connection = None
        self.actors = actors
        self.events = events

    def set_connection(self, handle, connection):
        self.handle = handle
        self.connection = connection


class CalvinControl(object):

    """ A HTTP REST API for calvin nodes
    """

    LOG_ACTOR_FIRING = 0
    LOG_ACTION_RESULT = 1
    LOG_ACTOR_NEW = 2
    LOG_ACTOR_DESTROY = 3
    LOG_ACTOR_MIGRATE = 4
    LOG_APPLICATION_NEW = 5
    LOG_APPLICATION_DESTROY = 6
    LOG_LINK_CONNECTED = 7
    LOG_LINK_DISCONNECTED = 8
    LOG_ACTOR_REPLICATE = 9
    LOG_ACTOR_DEREPLICATE = 10
    LOG_LOG_MESSAGE = 11

    def __init__(self):
        self.node = None
        self.loggers = {}
        self.routes = None
        self.server = None
        self.connections = {}
        self.tunnel = None
        self.host = None
        self.tunnel_server = None
        self.tunnel_client = None
        self.metering = None
        self.security = None

        # Set routes for requests
        self.routes = [
            (re_get_base_doc, self.handle_get_base_doc),
            (re_get_actor_doc, self.handle_get_actor_doc),
            (re_post_log, self.handle_post_log),
            (re_delete_log, self.handle_delete_log),
            (re_get_log, self.handle_get_log),
            (re_get_node_id, self.handle_get_node_id),
            (re_get_node_capabilities, self.handle_get_node_capabilities),
            (re_get_nodes, self.handle_get_nodes),
            (re_get_node, self.handle_get_node),
            (re_post_node_attribute_indexed_public, self.handle_post_node_attribute_indexed_public),
            (re_post_peer_setup, self.handle_peer_setup),
            (re_get_applications, self.handle_get_applications),
            (re_get_application, self.handle_get_application),
            (re_del_application, self.handle_del_application),
            (re_post_new_actor, self.handle_new_actor),
            (re_get_actors, self.handle_get_actors),
            (re_get_actor, self.handle_get_actor),
            (re_del_actor, self.handle_del_actor),
            (re_actor_report, self.handle_actor_report),
            (re_post_actor_migrate, self.handle_actor_migrate),
            (re_post_actor_disable, self.handle_actor_disable),
            (re_post_actor_replicate, self.handle_actor_replicate),
            (re_get_port, self.handle_get_port),
            (re_get_port_state, self.handle_get_port_state),
            (re_post_connect, self.handle_connect),
            (re_set_port_property, self.handle_set_port_property),
            (re_post_deploy, self.handle_deploy),
            (re_post_application_migrate, self.handle_post_application_migrate),
            (re_delete_node, self.handle_quit),
            (re_post_disconnect, self.handle_disconnect),
            (re_post_meter, self.handle_post_meter),
            (re_delete_meter, self.handle_delete_meter),
            (re_get_timed_meter, self.handle_get_timed_meter),
            (re_get_aggregated_meter, self.handle_get_aggregated_meter),
            (re_get_metainfo_meter, self.handle_get_metainfo_meter),
            (re_post_index, self.handle_post_index),
            (re_delete_index, self.handle_delete_index),
            (re_get_index, self.handle_get_index),
            (re_get_storage, self.handle_get_storage),
            (re_dump_storage, self.handle_dump_storage),
            (re_post_storage, self.handle_post_storage),
            (re_post_certificate_signing_request,self.handle_post_certificate_signing_request),
            (re_get_authentication_users_db, self.handle_get_authentication_users_db),
            (re_edit_authentication_users_db, self.handle_edit_authentication_users_db),
            (re_get_authentication_groups_db, self.handle_get_authentication_groups_db),
            (re_edit_authentication_groups_db, self.handle_edit_authentication_groups_db),
            (re_post_new_authorization_policy, self.handle_new_authorization_policy),
            (re_get_authorization_policies, self.handle_get_authorization_policies),
            (re_get_authorization_policy, self.handle_get_authorization_policy),
            (re_edit_authorization_policy, self.handle_edit_authorization_policy),
            (re_del_authorization_policy, self.handle_del_authorization_policy),
            (re_options, self.handle_options)
        ]

    def authentication_decorator(func):
        def _exit_with_error(issue_tracker):
            """Helper method to generate a proper error"""
            _log.debug("CalvinControl::_exit_with_error  add 401 to issuetracker")
            issue_tracker.add_error("UNAUTHORIZED", info={'status':401})
            return

        def _handle_authentication_decision(authentication_decision, arguments=None, security=None, org_cb=None, issue_tracker=None):
            _log.debug("CalvinControl::_handle_authentication_decision, authentication_decision={}".format(authentication_decision))
            if not authentication_decision:
                _log.error("Authentication failed")
                # This error reason is detected in calvin control and gives proper REST response
                # Authentication failure currently results in no subject attrbutes, which might still give access to the resource
                # , an alternative approach is to always deny access for authentication failure. Not sure what is best.
                _exit_with_error(issue_tracker)
            try:
                security.check_security_policy(
                    CalvinCB(_handle_policy_decision,
                             arguments=arguments,
                             org_cb=org_cb,
                             issue_tracker=issue_tracker),
                    element_type="control_interface",
                    element_value=arguments['func'].func_name
                )
            except Exception as exc:
                _log.exception("Failed to check security policy, exc={}".format(exc))
                return _handle_policy_decision(access_decision=False, arguments=arguments, org_cb=org_cb, issue_tracker=issue_tracker) 

        def _handle_policy_decision(access_decision, arguments=None, org_cb=None, issue_tracker=None):
            _log.debug("CalvinControl::_handle_policy_decision:\n\tauthorization_decision={}\n\targuments={}\n\ttorg_cb={}".format(access_decision, arguments, org_cb))
            if not access_decision:
                _log.error("Access denied")
                # This error reason is detected in calvin control and gives proper REST response
                _exit_with_error(issue_tracker)
            if issue_tracker.error_count:
                four_oh_ones = [e for e in issue_tracker.errors(sort_key='reason')]
                errors = issue_tracker.errors(sort_key='reason')
                for e in errors:
                    if 'status' in e and e['status'] == 401:
                        _log.error("Security verification of script failed")
                        status = calvinresponse.UNAUTHORIZED
                        body = None
                        arguments['self'].send_response(arguments['handle'], arguments['connection'], body, status=status)
                        return
            return arguments['func'](arguments['self'], arguments['handle'], arguments['connection'], arguments['match'], arguments['data'], arguments['hdr'])

        def inner(self, handle, connection, match, data, hdr):
            from base64 import b64decode
            _log.debug("authentication_decorator::inner, arguments were:"
                       "\n\tfunc={}"
                       "\n\thandle={}"
                       "\n\tconnection={}"
                       "\n\tmatch={}"
                       "\n\tdata={}"
                       "\n\thdr={}".format(func, handle, connection, match, data, hdr))

            issue_tracker = IssueTracker()
            credentials = None
            arguments={'func':func, 'self':self, 'handle':handle, 'connection':connection, 'match':match, 'data':data, 'hdr':hdr}
            try:
                if 'authorization' in hdr:
                    cred = b64decode(hdr['authorization'].strip('Basic ')).split(':')
                    credentials ={'user':cred[0], 'password':cred[1]}
                if data and 'sec_credentials' in data:
                    deploy_credentials = data['sec_credentials']
            except TypeError as err:
                _log.error("inner: code not decode credentials in header")
                pass
            try:
                self.security.authenticate_subject(
                    credentials,
                    callback=CalvinCB(_handle_authentication_decision, arguments=arguments, security=self.security, org_cb=None, issue_tracker=issue_tracker)
                )
            except Exception as exc:
                _log.exception("Failed to authenticate the subject, exc={}".format(exc))
                _exit_with_error(issue_tracker)

        return inner

    def start(self, node, uri, tunnel=False, external_uri=None):
        """ If not tunnel, start listening on uri and handle http requests.
            If tunnel, setup a tunnel to uri and handle requests.
        """
        self.metering = metering.get_metering()
        self.node = node
        self.security = Security(self.node)
        schema, _ = uri.split(':', 1)
        if tunnel:
            # Connect to tunnel server
            self.tunnel_client = CalvinControlTunnelClient(uri, self)
        else:
            url = urlparse(uri)
            self.port = int(url.port)
            self.host = url.hostname
            if external_uri is not None:
                self.external_host = urlparse(external_uri).hostname
            else:
                self.external_host = self.host
            _log.info("Control API trying to listening on: %s:%s" % (self.host, self.port))

            self.server = server_connection.ServerProtocolFactory(self.handle_request, "http", node_name=node.node_name)
            self.server.start(self.host, self.port)

            # Create tunnel server
            self.tunnel_server = CalvinControlTunnelServer(self.node)

    def stop(self):
        """ Stop """
        self.server.stop()
        if self.tunnel_server is not None:
            self.tunnel_server.stop()
        if self.tunnel_client is not None:
            self.tunnel_client.stop()

    def close_log_tunnel(self, handle):
        """ Close log tunnel
        """
        for user_id, logger in self.loggers:
            if logger.handle == handle:
                del self.loggers[user_id]

    def handle_request(self, actor_ids=None):
        """ Handle incoming requests on socket
        """
        if self.server.pending_connections:
            addr, conn = self.server.accept()
            self.connections[addr] = conn

        for handle, connection in self.connections.items():
            if connection.data_available:
                command, headers, data = connection.data_get()
                self.route_request(handle, connection, command, headers, data)

    def route_request(self, handle, connection, command, headers, data):
        if self.node.quitting:
            # Answer internal error on all requests while quitting, assume client can handle that
            # TODO: Answer permantely moved (301) instead with header Location: <another-calvin-runtime>???
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)
            return
        try:
            issuetracker = IssueTracker()
            found = False
            for route in self.routes:
                match = route[0].match(command)
                if match:
                    credentials = None
                    if data:
                        data = json.loads(data)
                    _log.debug("Calvin control handles:%s\n%s\n---------------" % (command, data))
                    route[1](handle, connection, match, data, headers)
                    found = True
                    break

            if not found:
                _log.error("No route found for: %s\n%s" % (command, data))
                self.send_response(handle, connection, None, status=404)
        except Exception as e:
            _log.info("Failed to parse request", exc_info=e)
            self.send_response(handle, connection, None, status=calvinresponse.BAD_REQUEST)

    def send_response(self, handle, connection, data, status=200, content_type=None):
        """ Send response header text/html
        """
        content_type = content_type or "Content-Type: application/json"
        content_type += "\n"

        # No data return 204 no content
        if data is None and status in range(200, 207):
            status = 204

        header = "HTTP/1.0 " + \
            str(status) + " " + calvinresponse.RESPONSE_CODES[status] + \
            "\n" + ("" if data is None else content_type ) + \
            "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n" + \
            "Access-Control-Allow-Origin: *\r\n" + "\n"

        if connection is None:
            msg = {"cmd": "httpresp", "msgid": handle, "header": header, "data": data}
            self.tunnel_client.send(msg)
        else:
            if not connection.connection_lost:
                connection.send(header)
                if data:
                    connection.send(data)
                connection.close()
            del self.connections[handle]

    def send_streamheader(self, handle, connection):
        """ Send response header for text/event-stream
        """
        response = "HTTP/1.0 200 OK\n" + "Content-Type: text/event-stream\n" + \
            "Access-Control-Allow-Origin: *\r\n" + "\n"

        if connection is not None:
            if not connection.connection_lost:
                connection.send(response)
        elif self.tunnel_client is not None:
                msg = {"cmd": "logresp", "msgid": handle, "header": response, "data": None}
                self.tunnel_client.send(msg)

    def storage_cb(self, key, value, handle, connection):
        missing = value is None or value is False
        self.send_response(handle, connection, None if missing else json.dumps(value),
                           status=calvinresponse.NOT_FOUND if missing else calvinresponse.OK)

    @authentication_decorator
    def handle_get_base_doc(self, handle, connection, match, data, hdr):
        """ Query get all docs
        """

        lines = control_api_doc.split("\n")

        want_json = 'accept' in hdr and hdr['accept'] == "application/json"

        if not want_json:
            data = """
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
            <html>
            <title>Calvin control API</title>
            <body>
            <xmp style="display:none;">"""

            block = []
            for line in lines:
                if not line and block:
                    data += '- __' + block.pop(1).strip().replace('_', '\_') + '__' + "\n"
                    data += "```\n" + "\n".join(s for s in block) + "\n```\n"
                    block =  []
                elif line:
                    # same block
                    block.append(line)
            data += """
            </xmp>
            <script src="//strapdownjs.com/v/0.2/strapdown.js"></script>
            </body>
            </html>
            """
            self.send_response(handle, connection, data, status=200, content_type="Content-Type: text/HTML")
        else:
            data = []
            block = []
            for line in lines:
                if not line and block:
                    item = {'title': block.pop(1).strip().replace('_', '\_').strip()}
                    item['doc_rows'] = [ a.strip() for a in block ]
                    data.append(item)
                    block =  []
                elif line:
                    # same block
                    block.append(line)

            self.send_response(handle, connection, json.dumps(data), status=200)

    @authentication_decorator
    def handle_get_actor_doc(self, handle, connection, match, data, hdr):
        """ Query ActorStore for documentation
        """
        path = match.group(1)
        what = '.'.join(path.strip('/').split('/'))
        ds = DocumentationStore()
        what = None if not what else what
        data = ds.help_raw(what)
        self.send_response(handle, connection, data)

    @authentication_decorator
    def handle_post_log(self, handle, connection, match, data, hdr):
        """ Create log session
        """
        status = calvinresponse.OK
        actors = []
        events = []

        if data and 'user_id' in data:
            user_id = data['user_id']
        else:
            user_id = calvinuuid.uuid("TRACE")

        if user_id not in self.loggers:
            if 'actors' in data and data['actors']:
                actors = data['actors']
            if 'events' in data:
                events = []
                for event in data['events']:
                    if event == 'actor_firing':
                        events.append(self.LOG_ACTOR_FIRING)
                    elif event == 'action_result':
                        events.append(self.LOG_ACTION_RESULT)
                    elif event == 'actor_new':
                        events.append(self.LOG_ACTOR_NEW)
                    elif event == 'actor_destroy':
                        events.append(self.LOG_ACTOR_DESTROY)
                    elif event == 'actor_migrate':
                        events.append(self.LOG_ACTOR_MIGRATE)
                    elif event == 'actor_replicate':
                        events.append(self.LOG_ACTOR_REPLICATE)
                    elif event == 'actor_dereplicate':
                        events.append(self.LOG_ACTOR_DEREPLICATE)
                    elif event == 'application_new':
                        events.append(self.LOG_APPLICATION_NEW)
                    elif event == 'application_destroy':
                        events.append(self.LOG_APPLICATION_DESTROY)
                    elif event == 'link_connected':
                        events.append(self.LOG_LINK_CONNECTED)
                    elif event == 'link_disconnected':
                        events.append(self.LOG_LINK_DISCONNECTED)
                    elif event == 'log_message':
                        events.append(self.LOG_LOG_MESSAGE)
                    else:
                        status = calvinresponse.BAD_REQUEST
                        break
            if status == calvinresponse.OK:
                self.loggers[user_id] = Logger(actors=actors, events=events)
        else:
            status = calvinresponse.BAD_REQUEST

        self.send_response(handle, connection,
                           json.dumps({'user_id': user_id, 'epoch_year': time.gmtime(0).tm_year})
                           if status == calvinresponse.OK else None,
                           status=status)

    @authentication_decorator
    def handle_delete_log(self, handle, connection, match, data, hdr):
        """ Delete log session
        """
        if match.group(1) in self.loggers:
            del self.loggers[match.group(1)]
            status = calvinresponse.OK
        else:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    @authentication_decorator
    def handle_get_log(self, handle, connection, match, data, hdr):
        """ Get log stream
        """
        if match.group(1) in self.loggers:
            self.loggers[match.group(1)].set_connection(handle, connection)
            self.send_streamheader(handle, connection)
        else:
            self.send_response(handle, connection, None, calvinresponse.NOT_FOUND)

    #Can't be access controlled, as it is needed to find authorization server
#    @authentication_decorator
    def handle_get_node_id(self, handle, connection, match, data, hdr):
        """ Get node id from this node
        """
        self.send_response(handle, connection, json.dumps({'id': self.node.id}))

    def handle_get_node_capabilities(self, handle, connection, match, data, hdr):
        """ Get capabilities from this node
        """
        self.send_response(handle, connection, json.dumps(self.node._calvinsys.list_capabilities()))

    def handle_peer_setup(self, handle, connection, match, data, hdr):
        _log.analyze(self.node.id, "+", data)
        self.node.peersetup(data['peers'], cb=CalvinCB(self.handle_peer_setup_cb, handle, connection))

    def handle_peer_setup_cb(self, handle, connection, status=None, peer_node_ids=None):
        _log.analyze(self.node.id, "+", status.encode())
        if peer_node_ids:
            data = json.dumps({k: (v[0], v[1].status) for k, v in peer_node_ids.items()})
        else:
            data = None
        self.send_response(handle, connection, data, status=status.status)

    @authentication_decorator
    def handle_get_nodes(self, handle, connection, match, data, hdr):
        """ Get active nodes
        """
        self.send_response(handle, connection, json.dumps(self.node.network.list_links()))

    @authentication_decorator
    def handle_get_node(self, handle, connection, match, data, hdr):
        """ Get node information from id
        """
        self.node.storage.get_node(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    def handle_post_node_attribute_indexed_public_cb(self, key, value, handle, connection, attributes):
        try:
            indexed_public = []
            for attr in attributes.items():
                indexed_string = format_index_string(attr)
                indexed_public.append(indexed_string)
                self.node.storage.add_index(indexed_string, key)
            value['attributes']['indexed_public'] = indexed_public
            self.node.storage.set(prefix="node-", key=key, value=value,
                cb=CalvinCB(func=self.storage_cb, handle=handle, connection=connection))
        except Exception as e:
            _log.error("Failed to update node %s", e)
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

    @authentication_decorator
    def handle_post_node_attribute_indexed_public(self, handle, connection, match, data, hdr):
        """ Update node information
        """
        try:
            if match.group(1) == self.node.id:
                if self.node.runtime_credentials is None or self.node.runtime_credentials.domain is None:
                    self.node.storage.remove_node_index(self.node)
                    self.node.attributes.set_indexed_public(data)
                    self.node_name = self.node.attributes.get_node_name_as_str()
                    self.node.storage.add_node(self.node, CalvinCB(
                        func=self.storage_cb, handle=handle, connection=connection))
                else:
                    self.send_response(handle, connection, None, status=calvinresponse.UNAUTHORIZED)
            else:
                self.node.storage.get_node(match.group(1), CalvinCB(
                    func=self.handle_post_node_attribute_indexed_public_cb, handle=handle, connection=connection, attributes=data))
        except Exception as e:
            _log.error("Failed to update node %s", e)
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

    @authentication_decorator
    def handle_get_applications(self, handle, connection, match, data, hdr):
        """ Get applications
        """
        self.send_response(
            handle, connection, json.dumps(self.node.app_manager.list_applications()))

    @authentication_decorator
    def handle_get_application(self, handle, connection, match, data, hdr):
        """ Get application from id
        """
        self.node.storage.get_application(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    @authentication_decorator
    def handle_del_application(self, handle, connection, match, data, hdr):
        """ Delete application from id
        """
        try:
            self.node.app_manager.destroy(match.group(1), cb=CalvinCB(self.handle_del_application_cb,
                                                                        handle, connection))
        except:
            _log.exception("Destroy application failed")
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

    def handle_del_application_cb(self, handle, connection, status=None):
        if not status and status.data:
            data = json.dumps(status.data)
        else:
            data = None
        self.send_response(handle, connection, data, status=status.status)

    @authentication_decorator
    def handle_new_actor(self, handle, connection, match, data, hdr):
        """ Create actor
        """
        try:
            actor_id = self.node.new(actor_type=data['actor_type'], args=data[
                                     'args'], deploy_args=data['deploy_args'])
            status = calvinresponse.OK
        except:
            actor_id = None
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(
            handle, connection, None if actor_id is None else json.dumps({'actor_id': actor_id}), status=status)

    @authentication_decorator
    def handle_get_actors(self, handle, connection, match, data, hdr):
        """ Get actor list
        """
        actors = self.node.am.list_actors()
        self.send_response(
            handle, connection, json.dumps(actors))

    @authentication_decorator
    def handle_get_actor(self, handle, connection, match, data, hdr):
        """ Get actor from id
        """
        self.node.storage.get_actor(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    @authentication_decorator
    def handle_del_actor(self, handle, connection, match, data, hdr):
        """ Delete actor from id
        """
        try:
            self.node.am.destroy(match.group(1))
            status = calvinresponse.OK
        except:
            _log.exception("Destroy actor failed")
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    @authentication_decorator
    def handle_actor_report(self, handle, connection, match, data, hdr):
        """ Get report from actor
        """
        try:
            # Now we allow passing in arguments (must be dictionary or None)
            report = self.node.am.report(match.group(1), data)
            status = calvinresponse.OK
        except:
            _log.exception("Actor report failed")
            report = None
            status = calvinresponse.NOT_FOUND
        self.send_response(
            handle, connection, None if report is None else json.dumps(report), status=status)

    @authentication_decorator
    def handle_actor_migrate(self, handle, connection, match, data, hdr):
        """ Migrate actor
        """
        status = calvinresponse.OK
        if 'peer_node_id' in data:
            try:
                self.node.am.migrate(match.group(1), data['peer_node_id'],
                                 callback=CalvinCB(self.actor_migrate_cb, handle, connection))
            except:
                _log.exception("Migration failed")
                status = calvinresponse.INTERNAL_ERROR
        elif 'requirements' in data:
            try:
                self.node.am.update_requirements(match.group(1), data['requirements'],
                    extend=data['extend'] if 'extend' in data else False,
                    move=data['move'] if 'move' in data else False,
                    callback=CalvinCB(self.actor_migrate_cb, handle, connection))
            except:
                _log.exception("Migration failed")
                status = calvinresponse.INTERNAL_ERROR
        else:
            status=calvinresponse.BAD_REQUEST

        if status != calvinresponse.OK:
            self.send_response(handle, connection,
                               None, status=status)

    def actor_migrate_cb(self, handle, connection, status, *args, **kwargs):
        """ Migrate actor respons
        """
        self.send_response(handle, connection,
                           None, status=status.status)

    @authentication_decorator
    def handle_actor_disable(self, handle, connection, match, data, hdr):
        try:
            self.node.am.disable(match.group(1))
            status = calvinresponse.OK
        except:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status)

    @authentication_decorator
    def handle_actor_replicate(self, handle, connection, match, data, hdr):
        data = {} if data is None else data
        # TODO When feature ready, only requirement based scaling should be accessable (if not also that removed)
        # TODO Make replication requirements a part of deployment requirements
        # Dereplication
        if data.get('dereplicate', False):
            exhaust = data.get('exhaust', False)
            try:
                self.node.rm.dereplicate(
                    match.group(1), CalvinCB(self.handle_actor_replicate_cb, handle, connection), exhaust)
            except:
                _log.exception("Dereplication failed")
                self.send_response(handle, connection, None, calvinresponse.INTERNAL_ERROR)
            return
        try:
            # Supervise with potential autoscaling in requirements
            requirements = data.get('requirements', {})
            status_supervise = self.node.rm.supervise_actor(match.group(1), requirements)
            if status_supervise.status != calvinresponse.OK:
                _log.debug("Replication supervised failed %s" % (match.group(1),))
                self.send_response(handle, connection, None, status_supervise.status)
                return
            if not requirements:
                # Direct replication only
                node_id = data.get('peer_node_id', self.node.id)
                self.node.rm.replicate(
                    match.group(1), node_id, CalvinCB(self.handle_actor_replicate_cb, handle, connection))
                return
            self.send_response(handle, connection, json.dumps(status_supervise.data), calvinresponse.OK)
        except:
            _log.exception("Failed test replication")
            self.send_response(handle, connection, None, calvinresponse.NOT_FOUND)

    def handle_actor_replicate_cb(self, handle, connection, status):
        self.send_response(handle, connection, json.dumps(status.data), status=status.status)

#    @authentication_decorator
    def handle_get_port(self, handle, connection, match, data, hdr):
        """ Get port from id
        """
        self.node.storage.get_port(match.group(2), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    @authentication_decorator
    def handle_get_port_state(self, handle, connection, match, data, hdr):
        """ Get port from id
        """
        state = {}
        try:
            state = self.node.am.get_port_state(match.group(1), match.group(2))
            status = calvinresponse.OK
        except:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, json.dumps(state), status)

    @authentication_decorator
    def handle_connect(self, handle, connection, match, data, hdr):
        """ Connect port
        """
        self.node.connect(
            actor_id=data.get("actor_id"),
            port_name=data.get("port_name"),
            port_dir=data.get("port_dir"),
            port_properties=data.get("port_properties"),
            port_id=data.get("port_id"),
            peer_node_id=data.get("peer_node_id"),
            peer_actor_id=data.get("peer_actor_id"),
            peer_port_name=data.get("peer_port_name"),
            peer_port_dir=data.get("peer_port_dir"),
            peer_port_properties=data.get("peer_port_properties"),
            peer_port_id=data.get("peer_port_id"),
            cb=CalvinCB(self.handle_connect_cb, handle, connection))

    def handle_connect_cb(self, handle, connection, **kwargs):
        status = kwargs.get('status', None)
        peer_port_id = kwargs.get('peer_port_id', None)
        self.send_response(handle, connection, json.dumps({'peer_port_id': peer_port_id}) if status else None,
                           status=status.status)
        _log.debug("Handle connect finnished")

    @authentication_decorator
    def handle_set_port_property(self, handle, connection, match, data, hdr):
        try:
            if data.get("port_properties") is None:
                status = self.node.pm.set_port_property(
                    port_id=data.get("port_id"),
                    actor_id=data.get("actor_id"),
                    port_dir=data.get("port_type"),
                    port_name=data.get("port_name"),
                    port_property=data.get("port_property"),
                    value=data.get("value"))
            else:
                status = self.node.pm.set_port_properties(
                    port_id=data.get("port_id"),
                    actor_id=data.get("actor_id"),
                    port_dir=data.get("port_type"),
                    port_name=data.get("port_name"),
                    **data.get("port_properties"))
        except:
            _log.exception("Failed setting port property")
            status = calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND)
        self.send_response(handle, connection, None, status=status.status)

    @authentication_decorator
    def handle_deploy(self, handle, connection, match, data, hdr):
        try:
            _log.analyze(self.node.id, "+", data)
            if 'app_info' not in data:
                kwargs = {}
                credentials = ""
                # Supply security verification data when available
                content = None
                if "sec_credentials" in data:
                    credentials = data['sec_credentials']
                    content = {}
                    if not "sec_sign" in data:
                        data['sec_sign'] = {}
                    content = {
                            'file': data["script"],
                            'sign': {h: s.decode('hex_codec') for h, s in data['sec_sign'].iteritems()}}
                compiler.compile_script_check_security(
                    data["script"],
                    filename=data["name"],
                    security=self.security,
                    content=content,
                    node=self.node,
                    verify=(data["check"] if "check" in data else True),
                    cb=CalvinCB(self.handle_deploy_cont, handle=handle, connection=connection, data=data),
                    **kwargs
                )
            else:
                # Supplying app_info is for backward compatibility hence abort if node configured security
                # Main user is csruntime when deploying script at the same time and some tests used
                # via calvin.Tools.deployer (the Deployer below is the new in appmanager)
                # TODO rewrite these users to send the uncompiled script as cscontrol does.
                if security_enabled():
                    _log.error("Can't combine compiled script with runtime having security")
                    self.send_response(handle, connection, None, status=calvinresponse.UNAUTHORIZED)
                    return
                app_info = data['app_info']
                issuetracker = IssueTracker()
                self.handle_deploy_cont(app_info, issuetracker, handle, connection, data)
        except Exception as e:
            _log.exception("Deployer failed, e={}".format(e))
            self.send_response(handle, connection, json.dumps({'exception': str(e)}),
                               status=calvinresponse.INTERNAL_ERROR)

    def handle_deploy_cont(self, app_info, issuetracker, handle, connection, data, security=None):
        try:
            if issuetracker.error_count:
                four_oh_ones = [e for e in issuetracker.errors(sort_key='reason')]
                errors = issuetracker.errors(sort_key='reason')
                for e in errors:
                    if 'status' in e and e['status'] == 401:
                        _log.error("Security verification of script failed")
                        status = calvinresponse.UNAUTHORIZED
                        body = None
                    else:
                        _log.exception("Compilation failed")
                        body = json.dumps({'errors': issuetracker.errors(), 'warnings': issuetracker.warnings()})
                        status=calvinresponse.BAD_REQUEST
                    self.send_response(handle, connection, body, status=status)
                    return
            _log.analyze(
                self.node.id,
                "+ COMPILED",
                {'app_info': app_info, 'errors': issuetracker.errors(), 'warnings': issuetracker.warnings()}
            )
            # TODO When deployscript codegen is less experimental do it as part of the cscompiler
            # Now just run it here seperate if script is supplied and no seperate deploy_info
            deploy_info = data.get("deploy_info", None)
            if "script" in data and deploy_info is None:
                deploy_info, ds_issuestracker = calvin_dscodegen(data["script"], data["name"])
                if ds_issuestracker.error_count:
                    _log.warning("Deployscript contained errors:")
                    _log.warning(ds_issuestracker.formatted_issues())
                    deploy_info = None
                elif not deploy_info['requirements']:
                    deploy_info = None

            d = Deployer(
                    deployable=app_info,
                    deploy_info=deploy_info,
                    node=self.node,
                    name=data["name"] if "name" in data else None,
                    security=security,
                    verify=data["check"] if "check" in data else True,
                    cb=CalvinCB(self.handle_deploy_cb, handle, connection)
                )
            _log.analyze(self.node.id, "+ Deployer instantiated", {})
            d.deploy()
            _log.analyze(self.node.id, "+ DEPLOYING", {})
        except Exception as e:
            _log.exception("Deployer failed")
            self.send_response(
                handle,
                connection,
                json.dumps({'errors': issuetracker.errors(), 'warnings': issuetracker.warnings(), 'exception': str(e)}),
                status=calvinresponse.BAD_REQUEST if issuetracker.error_count else calvinresponse.INTERNAL_ERROR
            )

    def handle_deploy_cb(self, handle, connection, status, deployer, **kwargs):
        _log.analyze(self.node.id, "+ DEPLOYED", {'status': status.status})
        if status:
            print "DEPLOY STATUS", str(status)
            self.send_response(handle, connection,
                               json.dumps({'application_id': deployer.app_id,
                                           'actor_map': deployer.actor_map,
                                           'placement': kwargs.get('placement', None),
                                           'requirements_fulfilled': status.status == calvinresponse.OK}
                                          ) if deployer.app_id else None,
                               status=status.status)
        else:
            self.send_response(handle, connection, None, status=status.status)

    @authentication_decorator
    def handle_post_application_migrate(self, handle, connection, match, data, hdr):
        app_id = match.group(1)
        try:
            self.node.app_manager.migrate_with_requirements(app_id,
                                                   deploy_info=data["deploy_info"] if "deploy_info" in data else None,
                                                   move=data["move"] if "move" in data else False,
                                                   cb=CalvinCB(self.handle_post_application_migrate_cb, handle, connection))
        except:
            _log.exception("App migration failed")
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

    def handle_post_application_migrate_cb(self, handle, connection, status, **kwargs):
        _log.analyze(self.node.id, "+ MIGRATED", {'status': status.status})
        self.send_response(handle, connection, None, status=status.status)

    @authentication_decorator
    def handle_quit(self, handle, connection, match, data, hdr):
        if match.group(1) is None or match.group(1) == "now":
            async.DelayedCall(.2, self.node.stop)
            self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)
        elif match.group(1) == "migrate":
            async.DelayedCall(.2, self.node.stop_with_migration)
            self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)

    @authentication_decorator
    def handle_disconnect(self, handle, connection, match, data, hdr):
        actor_id = data.get('actor_id', None)
        port_name = data.get('port_name', None)
        port_dir = data.get('port_dir', None)
        port_id = data.get('port_id', None)
        # Convert type of disconnect as string to enum value
        # Allowed values TEMPORARY, TERMINATE, EXHAUST
        terminate = data.get('terminate', "TEMPORARY")
        try:
            terminate = DISCONNECT.__getattribute__(DISCONNECT, terminate)
        except:
            terminate = DISCONNECT.TEMPORARY

        _log.debug("disconnect(actor_id=%s, port_name=%s, port_dir=%s, port_id=%s)" %
                   (actor_id if actor_id else "", port_name if port_name else "",
                    port_dir if port_dir else "", port_id if port_id else ""))
        self.node.pm.disconnect(actor_id=actor_id, port_name=port_name,
                           port_dir=port_dir, port_id=port_id, terminate=terminate,
                           callback=CalvinCB(self.handle_disconnect_cb, handle, connection))

    def handle_disconnect_cb(self, handle, connection, **kwargs):
        status = kwargs.get('status', None)
        _log.analyze(self.node.id, "+ DISCONNECTED", {'status': status.status}, tb=True)
        self.send_response(handle, connection, None, status=status.status)

    @authentication_decorator
    def handle_post_meter(self, handle, connection, match, data, hdr):
        try:
            user_id = self.metering.register(data['user_id'] if data and 'user_id' in data else None)
            timeout = self.metering.timeout
            status = calvinresponse.OK
        except:
            _log.exception("handle_post_meter")
            status = calvinresponse.BAD_REQUEST
        self.send_response(handle, connection, json.dumps({ 'user_id': user_id,
                                                            'timeout': timeout,
                                                            'epoch_year': time.gmtime(0).tm_year})
                            if status == calvinresponse.OK else None, status=status)

    @authentication_decorator
    def handle_delete_meter(self, handle, connection, match, data, hdr):
        try:
            self.metering.unregister(match.group(1))
            status = calvinresponse.OK
        except:
            _log.exception("handle_delete_meter")
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    @authentication_decorator
    def handle_get_timed_meter(self, handle, connection, match, data, hdr):
        try:
            data = self.metering.get_timed_meter(match.group(1))
            status = calvinresponse.OK
        except:
            _log.exception("handle_get_timed_meter")
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection,
            json.dumps(data) if status == calvinresponse.OK else None, status=status)

    @authentication_decorator
    def handle_get_aggregated_meter(self, handle, connection, match, data, hdr):
        try:
            data = self.metering.get_aggregated_meter(match.group(1))
            status = calvinresponse.OK
        except:
            _log.exception("handle_get_aggregated_meter")
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection,
            json.dumps(data) if status == calvinresponse.OK else None, status=status)

    @authentication_decorator
    def handle_get_metainfo_meter(self, handle, connection, match, data, hdr):
        try:
            data = self.metering.get_actors_info(match.group(1))
            status = calvinresponse.OK
        except:
            _log.exception("handle_get_metainfo_meter")
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection,
            json.dumps(data) if status == calvinresponse.OK else None, status=status)

    @authentication_decorator
    def handle_post_index(self, handle, connection, match, data, hdr):
        """ Add to index
        """
        self.node.storage.add_index(
            match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

    @authentication_decorator
    def handle_delete_index(self, handle, connection, match, data, hdr):
        """ Remove from index
        """
        self.node.storage.remove_index(
            match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

    #Can't be access controlled, as it is needed to find authorization server
#    @authentication_decorator
    def handle_get_index(self, handle, connection, match, data, hdr):
        """ Get from index
        """
        self.node.storage.get_index(
            match.group(1), cb=CalvinCB(self.get_index_cb, handle, connection))

    def index_cb(self, handle, connection, *args, **kwargs):
        """ Index operation response
        """
        _log.debug("index cb (in control) %s, %s" % (args, kwargs))
        if 'value' in kwargs:
            value = kwargs['value']
        else:
            value = None
        self.send_response(handle, connection, None,
                           status=calvinresponse.INTERNAL_ERROR if value is None else calvinresponse.OK)

    def get_index_cb(self, handle, connection, key, value, *args, **kwargs):
        """ Index operation response
        """
        _log.debug("get index cb (in control) %s, %s" % (key, value))
        self.send_response(handle, connection, None if value is None else json.dumps({'result': value}),
                           status=calvinresponse.NOT_FOUND if value is None else calvinresponse.OK)

    @authentication_decorator
    def handle_post_storage(self, handle, connection, match, data, hdr):
        """ Store in storage
        """
        self.node.storage.set("", match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

    @authentication_decorator
    def handle_get_storage(self, handle, connection, match, data, hdr):
        """ Get from storage
        """
        self.node.storage.get("", match.group(1), cb=CalvinCB(self.get_index_cb, handle, connection))

    @authentication_decorator
    def handle_dump_storage(self, handle, connection, match, data, hdr):
        """ Get from storage
        """
        name = self.node.storage.dump()
        self.send_response(handle, connection, json.dumps(name), status=calvinresponse.OK)

    # No authentication decorator, this is called by the runtimes when deployed
    # without a certificate
    def handle_post_certificate_signing_request(self, handle, connection, match, data, hdr):
        """Post a CSR, if ok, CA creates and returns X509 certificate """
        try:
            cert = self.node.certificate_authority.sign_csr_request(data)
            status = calvinresponse.OK
        except:
            _log.exception("handle_post_certificate_signing_request")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, json.dumps({"certificate": cert}) if status == calvinresponse.OK else None,
                           status=status)

    @authentication_decorator
    def handle_get_authentication_users_db(self, handle, connection, match, data, hdr):
        """Get all authorization policies on this runtime"""
        try:
            users_db = self.node.authentication.arp.get_users_db()
            status = calvinresponse.OK
        except:
            _log.exception("handle_get_authentication_users_db")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, json.dumps({"users_db": users_db}) if status == calvinresponse.OK else None,
                           status=status)

    @authentication_decorator
    def handle_edit_authentication_users_db(self, handle, connection, match, data, hdr):
        """Edit users database"""
        # TODO: need some kind of authentication for policy management
        if 'users_db'in data:
            try:
    #            self.node.authentication.arp.update_users_db(data, match.group(1))
                self.node.authentication.arp.update_users_db(data['users_db'])
                status = calvinresponse.OK
            except IOError as err:
                _log.exception("handle_edit_authentication_users_db, err={}".format(err))
                status = calvinresponse.NOT_FOUND
            except Exception as err:
                _log.exception("handle_edit_authentication_users_db, err={}".format(err))
                status = calvinresponse.INTERNAL_ERROR
        else:
            _log.exception("handle_edit_authentication_users_db: no users_db in data\n\tdata={}".format(data))
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    @authentication_decorator
    def handle_get_authentication_groups_db(self, handle, connection, match, data, hdr):
        """Get all authorization policies on this runtime"""
        #TODO:to be implemented

    @authentication_decorator
    def handle_edit_authentication_groups_db(self, handle, connection, match, data, hdr):
        """Edit authorization policy identified by id"""
        #TODO:to be implemented

    @authentication_decorator
    def handle_new_authorization_policy(self, handle, connection, match, data, hdr):
        """Create authorization policy"""
        # TODO: need some kind of authentication for policy management
        try:
            policy_id = self.node.authorization.prp.create_policy(data)
            status = calvinresponse.OK
        except:
            policy_id = None
            _log.exception("handle_new_authorization_policy")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, None if policy_id is None else json.dumps({'policy_id': policy_id}),
                           status=status)

    @authentication_decorator
    def handle_get_authorization_policies(self, handle, connection, match, data, hdr):
        """Get all authorization policies on this runtime"""
        try:
            policies = self.node.authorization.prp.get_policies()
            status = calvinresponse.OK
        except:
            _log.exception("handle_get_authorization_policies")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, json.dumps({"policies": policies}) if status == calvinresponse.OK else None,
                           status=status)

    @authentication_decorator
    def handle_get_authorization_policy(self, handle, connection, match, data, hdr):
        """Get authorization policy identified by id"""
        try:
            data = self.node.authorization.prp.get_policy(match.group(1))
            status = calvinresponse.OK
        except IOError:
            _log.exception("handle_get_authorization_policy")
            status = calvinresponse.NOT_FOUND
        except:
            _log.exception("handle_get_authorization_policy")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, json.dumps({"policy": data}) if status == calvinresponse.OK else None,
                           status=status)

    @authentication_decorator
    def handle_edit_authorization_policy(self, handle, connection, match, data, hdr):
        """Edit authorization policy identified by id"""
        # TODO: need some kind of authentication for policy management
        try:
            self.node.authorization.prp.update_policy(data, match.group(1))
            status = calvinresponse.OK
        except IOError:
            _log.exception("handle_edit_authorization_policy")
            status = calvinresponse.NOT_FOUND
        except:
            _log.exception("handle_edit_authorization_policy")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, None, status=status)

    @authentication_decorator
    def handle_del_authorization_policy(self, handle, connection, match, data, hdr):
        """ Delete authorization policy identified by id"""
        # TODO: need some kind of authentication for policy management
        try:
            self.node.authorization.prp.delete_policy(match.group(1))
            status = calvinresponse.OK
        except OSError:
            _log.exception("handle_del_authorization_policy")
            status = calvinresponse.NOT_FOUND
        except:
            _log.exception("handle_del_authorization_policy")
            status = calvinresponse.INTERNAL_ERROR
        self.send_response(handle, connection, None, status=status)

    def log_actor_firing(self, actor_id, action_method, tokens_produced, tokens_consumed, production):
        """ Trace actor firing
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_FIRING in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_fire'
                    data['actor_id'] = actor_id
                    data['action_method'] = action_method
                    data['produced'] = tokens_produced
                    data['consumed'] = tokens_consumed
                    if self.LOG_ACTION_RESULT in logger.events:
                        data['action_result'] = production
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_actor_new(self, actor_id, actor_name, actor_type, is_shadow):
        """ Trace actor new
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_NEW in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_new'
                    data['actor_id'] = actor_id
                    data['actor_name'] = actor_name
                    data['actor_type'] = actor_type
                    data['is_shadow'] = is_shadow
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_actor_destroy(self, actor_id):
        """ Trace actor destroy
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_DESTROY in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_destroy'
                    data['actor_id'] = actor_id
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_actor_migrate(self, actor_id, dest_node_id):
        """ Trace actor migrate
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_MIGRATE in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_migrate'
                    data['actor_id'] = actor_id
                    data['dest_node_id'] = dest_node_id
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_actor_replicate(self, actor_id, replica_actor_id, replication_id, dest_node_id):
        """ Trace actor replication
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_REPLICATE in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_replicate'
                    data['actor_id'] = actor_id
                    data['dest_node_id'] = dest_node_id
                    data['replication_id'] = replication_id
                    data['replica_actor_id'] = replica_actor_id
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_actor_dereplicate(self, actor_id, replica_actor_id, replication_id):
        """ Trace actor dereplication
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_ACTOR_DEREPLICATE in logger.events:
                if not logger.actors or actor_id in logger.actors:
                    data = {}
                    data['timestamp'] = time.time()
                    data['node_id'] = self.node.id
                    data['type'] = 'actor_dereplicate'
                    data['actor_id'] = actor_id
                    data['replication_id'] = replication_id
                    data['replica_actor_id'] = replica_actor_id
                    if logger.connection is not None:
                        if not logger.connection.connection_lost:
                            logger.connection.send("data: %s\n\n" % json.dumps(data))
                        else:
                            disconnected.append(user_id)
                    elif self.tunnel_client is not None and logger.handle is not None:
                        msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                        self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_application_new(self, application_id, application_name):
        """ Trace application new
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_APPLICATION_NEW in logger.events:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'application_new'
                data['application_id'] = application_id
                data['application_name'] = application_name
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_application_destroy(self, application_id):
        """ Trace application destroy
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_APPLICATION_DESTROY in logger.events:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'application_destroy'
                data['application_id'] = application_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_link_connected(self, peer_id, uri):
        """ Trace node connect
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_LINK_CONNECTED in logger.events:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'link_connected'
                data['peer_id'] = peer_id
                data['uri'] = uri
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]


    def log_link_disconnected(self, peer_id):
        """ Trace node connect
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_LINK_DISCONNECTED in logger.events:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'link_disconnected'
                data['peer_id'] = peer_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    def log_log_message(self, message):
        """ Log message that is displayed at listener
        """
        disconnected = []
        for user_id, logger in self.loggers.iteritems():
            if not logger.events or self.LOG_LOG_MESSAGE in logger.events:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'log_message'
                data['msg'] = message
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
        for user_id in disconnected:
            del self.loggers[user_id]

    @authentication_decorator
    def handle_options(self, handle, connection, match, data, hdr):
        """ Handle HTTP OPTIONS requests
        """
        response = "HTTP/1.1 200 OK\n"

        """ Copy the content of Access-Control-Request-Headers to the response
        """
        if 'access-control-request-headers' in hdr:
            response += "Access-Control-Allow-Headers: " + \
                        hdr['access-control-request-headers'] + "\n"

        response += "Content-Length: 0\n" \
                    "Access-Control-Allow-Origin: *\n" \
                    "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n" \
                    "Content-Type: *\n" \
                    "\n\r\n"

        if connection is None:
            msg = {"cmd": "httpresp", "msgid": handle, "header": response, "data": None}
            self.tunnel_client.send(msg)
        else:
            connection.send(response)


class CalvinControlTunnelServer(object):

    """ A Calvin control tunnel server
    """

    def __init__(self, node):
        self.node = node
        self.tunnels = {}
        self.controltunnels = {}
        # Register for incoming control proxy requests
        self.node.proto.register_tunnel_handler("control", CalvinCB(self.tunnel_request_handles))

    def stop(self):
        for _, control in self.controltunnels.items():
            control.close()

    def tunnel_request_handles(self, tunnel):
        """ Incoming tunnel request for storage proxy server
            Start a socket server and update peer node with control uri
        """
        # Register tunnel
        self.tunnels[tunnel.peer_node_id] = tunnel
        self.controltunnels[tunnel.peer_node_id] = CalvinControlTunnel(tunnel)
        tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
        tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
        tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
        # We accept it by returning True
        return True

    def tunnel_down(self, tunnel):
        """ Callback that the tunnel is not accepted or is going down """
        self.controltunnels[tunnel.peer_node_id].close()
        del self.tunnels[tunnel.peer_node_id]
        del self.controltunnels[tunnel.peer_node_id]
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, tunnel):
        """ Callback that the tunnel is working """
        _log.analyze(self.node.id, "+ SERVER", {"tunnel_id": tunnel.id})
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a storage client request"""
        self.controltunnels[tunnel.peer_node_id].handle_response(payload)


class CalvinControlTunnel(object):

    """ A Calvin control socket to tunnel proxy
    """

    def __init__(self, tunnel):
        self.tunnel = tunnel
        self.connections = {}

        # Start a socket server on same interface as calvincontrol
        self.host = get_calvincontrol().host

        for x in range(0, 10):
            try:
                self.port = randint(5100, 5200)
                self.server = server_connection.ServerProtocolFactory(self.handle_request, "http")
                self.server.start(self.host, self.port)
                _log.info("Control proxy for %s listening on: %s:%s" % (tunnel.peer_node_id, self.host, self.port))
                break
            except:
                pass

        # Tell peer node that we a listening and on what uri
        msg = {"cmd": "started",
               "controluri": "http://" + get_calvincontrol().external_host + ":" + str(self.port)}
        self.tunnel.send(msg)

    def close(self):
        self.server.stop()

    def handle_request(self, actor_ids=None):
        """ Handle connections and tunnel requests
        """
        if self.server.pending_connections:
            addr, conn = self.server.accept()
            msg_id = calvinuuid.uuid("MSGID")
            self.connections[msg_id] = conn
            _log.debug("New connection msg_id: %s" % msg_id)

        for msg_id, connection in self.connections.items():
            if connection.data_available:
                command, headers, data = connection.data_get()
                _log.debug("CalvinControlTunnel handle_request msg_id: %s command: %s" % (msg_id, command))
                msg = {"cmd": "httpreq",
                       "msgid": msg_id,
                       "command": command,
                       "headers": headers,
                       "data": data}
                self.tunnel.send(msg)

    def handle_response(self, payload):
        """ Handle a tunnel response
        """
        if "msgid" in payload:
            msgid = payload["msgid"]
            if msgid in self.connections:
                if "cmd" in payload and "header" in payload and "data" in payload:
                    cmd = payload["cmd"]
                    if cmd == "httpresp":
                        self.send_response(msgid, payload["header"], payload["data"], True)
                        return
                    elif cmd == "logresp":
                        self.send_response(msgid, payload["header"], payload["data"], False)
                        return
                    elif cmd == "logevent":
                        result = self.send_response(msgid, payload["header"], payload["data"], False)
                        if not result:
                            msg = {"cmd": "logclose"}
                            self.tunnel.send(msg)
                        return
        _log.error("Unknown control proxy response %s" % payload)

    def send_response(self, msgid, header, data, closeConnection):
        """ Send response header text/html
        """
        connection = self.connections[msgid]
        if not connection.connection_lost:
            if header is not None:
                connection.send(str(header))
            if data is not None:
                connection.send(str(data))
            if closeConnection:
                connection.close()
                del self.connections[msgid]
            return True
        del self.connections[msgid]
        return False


class CalvinControlTunnelClient(object):

    """ A Calvin control tunnel client
    """

    def __init__(self, uri, calvincontrol):
        self.uri = uri
        self.calvincontrol = calvincontrol
        self.tunnel = None
        self.calvincontrol.node.network.join([uri], CalvinCB(self._start_link_cb))

    def stop(self):
        pass

    def _start_link_cb(self, status, uri, peer_node_id):
        if status == "NACK":
            return
        # Got link set up tunnel
        master_id = peer_node_id
        self.tunnel = self.calvincontrol.node.proto.tunnel_new(master_id, 'control', {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def tunnel_down(self):
        """ Callback that the tunnel is not accepted or is going down """
        if not self.tunnel:
            return True
        self.tunnel = None
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self):
        """ Callback that the tunnel is working """
        if not self.tunnel:
            return True
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, payload):
        """ Gets called when a control proxy replies"""
        if "cmd" in payload:
            if payload["cmd"] == "httpreq":
                try:
                    self.calvincontrol.route_request(
                        payload["msgid"], None, payload["command"], payload["headers"], payload["data"])
                except:
                    _log.exception("FIXME! Caught exception in calvincontrol when tunneling.")
                    self.calvincontrol.send_response(payload["msgid"], None, None, status=calvinresponse.INTERNAL_ERROR)
            elif payload["cmd"] == "started":
                self.calvincontrol.node.external_control_uri = payload["controluri"]
                self.calvincontrol.node.storage.add_node(self.calvincontrol.node)
                return
            elif payload["cmd"] == "logclose":
                self.calvincontrol.close_log_tunnel(payload["msg_id"])
                return
        _log.error("Tunnel client received unknown command %s" % payload['cmd'] if 'cmd' in payload else "")

    def send(self, msg):
        if self.tunnel:
            self.tunnel.send(msg)
        else:
            _log.error("No tunnel connected")
