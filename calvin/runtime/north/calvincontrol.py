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

import re
import time
import datetime
import json
from calvin.Tools import cscompiler as compiler
from calvin.Tools import deployer
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south.plugins.async import server_connection, async
from urlparse import urlparse
from calvin.utilities import calvinresponse
from calvin.actorstore.store import DocumentationStore

_log = get_logger(__name__)

uuid_re = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

control_api_doc = ""

control_api_doc += \
"""
    GET /actor_doc {path}
    Get documentation in 'raw' format for actor or module at {path}, where path
    is formatted as '/{module}/{submodule}/ ... /{actor}'.
    If {path} is empty return top-level documentation.
    See DocumentStore help_raw() for details on data format.
    Response status code: OK
    Response: dictionary with documentation
"""
re_get_actor_doc = re.compile(r"GET /actor_doc(\S*)\sHTTP/1")

# control_api_doc += \
"""
    GET /log
    Streaming log from calvin node (more documentation needed)
"""
re_get_log = re.compile(r"GET /log\sHTTP/1")

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
        "control_uri": "http://<address>:<controlport>",
        "uri": "calvinip://<address>:<port>"
    }
"""
re_get_node = re.compile(r"GET /node/(NODE_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

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
    Response status code: ACCEPTED
    Response: none
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
    Repsonse: Depends on actor
"""
re_get_actor_report = re.compile(r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/report\sHTTP/1")

control_api_doc += \
"""
    POST /actor/{actor-id}/migrate
    Migrate actor to (other) node
    Body: {"peer_node_id": <node-id>}
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
"""
re_post_actor_migrate = re.compile(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/migrate\sHTTP/1")

control_api_doc += \
"""
    POST /application/{application-id}/migrate
    Apply deployment requirements to actors of an application and initiate migration of actors accordingly
    Body:
    {
        "reqs":
           {"groups": {"<group 1 name>": ["<actor instance 1 name>", ...]},  # TODO not yet implemented
            "requirements": {
                "<actor instance 1 name>": [ {"op": "<mathing rule name>",
                                              "kwargs": {<rule param key>: <rule param value>, ...},
                                              "type": either "+" or "-" for set section operation or set removal, respectively
                                              }, ...
                                           ],
                ...
                            }
           }
    }
    The matching rules are implemented as plugg-ins, intended to be extended. The type "+" is anding rules togheter or
    rather taking the section between all rules return possible nodes. The type "-" is explicitly removing the matching
    rule's returned nodes from the set of possible nodes. Note that only negative rules will result in no possible nodes,
    i.e. no implied all but these.
    A special matching rule exist, to first form a union between matching rules, i.e. alternative matches. This is useful
    for e.g. alternative namings, ownerships or specifying either of two specific nodes.
        {"op": "union_group",
         "requirements": [list as above of matching rules but without type key]
         "type": "+"
        }
    Other matching rules available is current_node, all_nodes and node_attr_match which takes an index param which is
    attribute formatted, e.g.
        {"op": "node_attr_match",
         "kwargs": {"index": ["node_name", {"organization": "org.testexample", "name": "testNode1"}]}
         "type": "+"
        }
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: {"placement": {<actor_id>: <node_id>, ...}}
"""
re_post_application_requirements = re.compile(r"POST /application/((APP_)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/migrate\sHTTP/1")

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
re_get_port = re.compile(r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/port/(PORT_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")

# control_api_doc += \
"""
    GET /actor/{actor-id}/port/{port-id}/state
    Get port state {port-id} of actor {actor-id}
    Response status code: OK or NOT_FOUND
"""
re_get_port_state = re.compile(r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/port/(PORT_" + uuid_re + "|" + uuid_re + ")/state\sHTTP/1")

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
    Sets a property of the port. Currently only fanout on outports is supported.
    Body:
    {
        "actor_id" : <actor-id>,
        "port_type": <in/out>,
        "port_name": <port-name>,
        "port_property": <property-name>
        "value" : <property value>
    }
    Response status code: OK or NOT_FOUND
    Response: none
"""
re_set_port_property = re.compile(r"POST /set_port_property\sHTTP/1")

control_api_doc += \
"""
    POST /deploy
    Compile and deploy a calvin script to this calvin node
    Body:
    {
        "name": <application name>,
        "script": <calvin script>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: {"application_id": <application-id>,
               "actor_map": {<actor id>: <actor name with namespace>, ...}}
"""
re_post_deploy = re.compile(r"POST /deploy\sHTTP/1")

control_api_doc += \
"""
    POST /disconnect
    Disconnect a port. If port felds are empty, all ports of the actor are disconnected
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
    DELETE /node
    Stop (this) calvin node
    Response status code: ACCEPTED
    Response: none
"""
re_delete_node = re.compile(r"DELETE /node\sHTTP/1")

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
    OPTIONS /url
    Request for information about the communication options available on url
    Response status code: OK
    Response: Available communication options
"""
re_options = re.compile(r"OPTIONS /[0-9a-z/-]+\sHTTP/1.1")

_calvincontrol = None


def get_calvincontrol():
    """ Returns the CalvinControl singleton
    """
    global _calvincontrol
    if _calvincontrol is None:
        _calvincontrol = CalvinControl()
    return _calvincontrol


class CalvinControl(object):

    """ A HTTP REST API for calvin nodes
    """

    def __init__(self):
        self.node = None
        self.log_connection = None
        self.routes = None
        self.server = None
        self.connections = {}

    def start(self, node, uri):
        """ Start listening and handle request on uri
        """
        self.port = int(urlparse(uri).port)
        self.host = urlparse(uri).hostname
        _log.info("Listening on: %s:%s" % (self.host, self.port))

        self.node = node

        # Set routes for requests
        self.routes = [
            (re_get_actor_doc, self.handle_get_actor_doc),
            (re_get_log, self.handle_get_log),
            (re_get_node_id, self.handle_get_node_id),
            (re_get_nodes, self.handle_get_nodes),
            (re_get_node, self.handle_get_node),
            (re_post_peer_setup, self.handle_peer_setup),
            (re_get_applications, self.handle_get_applications),
            (re_get_application, self.handle_get_application),
            (re_del_application, self.handle_del_application),
            (re_post_new_actor, self.handle_new_actor),
            (re_get_actors, self.handle_get_actors),
            (re_get_actor, self.handle_get_actor),
            (re_del_actor, self.handle_del_actor),
            (re_get_actor_report, self.handle_get_actor_report),
            (re_post_actor_migrate, self.handle_actor_migrate),
            (re_post_application_requirements, self.handle_application_requirements),
            (re_post_actor_disable, self.handle_actor_disable),
            (re_get_port, self.handle_get_port),
            (re_get_port_state, self.handle_get_port_state),
            (re_post_connect, self.handle_connect),
            (re_set_port_property, self.handle_set_port_property),
            (re_post_deploy, self.handle_deploy),
            (re_delete_node, self.handle_quit),
            (re_post_disconnect, self.handle_disconnect),
            (re_post_index, self.handle_post_index),
            (re_delete_index, self.handle_delete_index),
            (re_get_index, self.handle_get_index),
            (re_get_storage, self.handle_get_storage),
            (re_post_storage, self.handle_post_storage),
            (re_options, self.handle_options)
        ]
        self.server = server_connection.ServerProtocolFactory(self.handle_request, "http")
        self.server.start(self.host, self.port)

    def stop(self):
        """ Stop
        """
        self.server.stop()

    def handle_request(self, actor_ids=None):
        """ Handle incoming requests
        """
        if self.server.pending_connections:
            addr, conn = self.server.accept()
            self.connections[addr] = conn

        for handle, connection in self.connections.items():
            if connection.data_available:
                command, headers, data = connection.data_get()
                found = False
                for route in self.routes:
                    match = route[0].match(command)
                    if match:
                        if data:
                            data = json.loads(data)
                        _log.debug("Calvin control handles:\n%s\n---------------" % data)
                        route[1](handle, connection, match, data, headers)
                        found = True
                        break

                if not found:
                    _log.error("No route found for: %s" % data)
                    self.send_response(
                        handle, connection, None, status=404)

    def send_response(self, handle, connection, data, status=200):
        """ Send response header text/html
        """
        if not connection.connection_lost:
            connection.send("HTTP/1.0 " + str(status) + " " + calvinresponse.RESPONSE_CODES[status] + "\n"
                            + ("" if data is None else "Content-Type: application/json\n")
                            + "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n"
                            + "Access-Control-Allow-Origin: *\r\n"
                            + "\n")
            if data:
                connection.send(data)
            connection.close()
        del self.connections[handle]

    def send_streamheader(self, connection):
        """ Send response header for text/event-stream
        """
        if not connection.connection_lost:
            connection.send("HTTP/1.0 200 OK\n"
                            + "Content-Type: text/event-stream\n"
                            + "Access-Control-Allow-Origin: *\r\n"
                            + "\n")

    def storage_cb(self, key, value, handle, connection):
        self.send_response(handle, connection, None if value is None else json.dumps(value),
                           status=calvinresponse.NOT_FOUND if None else calvinresponse.OK)

    def handle_get_actor_doc(self, handle, connection, match, data, hdr):
        """ Query ActorStore for documentation
        """
        path = match.group(1)
        what = '.'.join(path.strip('/').split('/'))
        ds = DocumentationStore()
        data = ds.help_raw(what)
        self.send_response(handle, connection, json.dumps(data))

    def handle_get_log(self, handle, connection, match, data, hdr):
        """ Get log stream
        """
        self.log_connection = connection
        self.send_streamheader(connection)

    def handle_get_node_id(self, handle, connection, match, data, hdr):
        """ Get node id from this node
        """
        self.send_response(
            handle, connection, json.dumps({'id': self.node.id}))

    def handle_peer_setup(self, handle, connection, match, data, hdr):
        _log.analyze(self.node.id, "+", data)
        self.node.peersetup(data['peers'], cb=CalvinCB(self.handle_peer_setup_cb, handle, connection))

    def handle_peer_setup_cb(self, handle, connection, status=None, peer_node_ids=None):
        _log.analyze(self.node.id, "+", status.encode())
        self.send_response(handle, connection,
            None if peer_node_ids is None else json.dumps({k: (v[0], v[1].status) for k, v in peer_node_ids.items()}),
            status=status.status)

    def handle_get_nodes(self, handle, connection, match, data, hdr):
        """ Get active nodes
        """
        self.send_response(
            handle, connection, json.dumps(self.node.network.list_links()))

    def handle_get_node(self, handle, connection, match, data, hdr):
        """ Get node information from id
        """
        self.node.storage.get_node(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    def handle_get_applications(self, handle, connection, match, data, hdr):
        """ Get applications
        """
        self.send_response(
            handle, connection, json.dumps(self.node.app_manager.list_applications()))

    def handle_get_application(self, handle, connection, match, data, hdr):
        """ Get application from id
        """
        self.node.storage.get_application(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    def handle_del_application(self, handle, connection, match, data, hdr):
        """ Delete application from id
        """
        # FIXME add callback, for now just say we got the request
        self.node.app_manager.destroy(match.group(1))
        self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)

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

    def handle_get_actors(self, handle, connection, match, data, hdr):
        """ Get actor list
        """
        actors = self.node.am.list_actors()
        self.send_response(
            handle, connection, json.dumps(actors))

    def handle_get_actor(self, handle, connection, match, data, hdr):
        """ Get actor from id
        """
        self.node.storage.get_actor(match.group(1), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    def handle_del_actor(self, handle, connection, match, data, hdr):
        """ Delete actor from id
        """
        try:
            self.node.am.destroy(match.group(1))
            status = calvinresponse.OK
        except:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    def handle_get_actor_report(self, handle, connection, match, data, hdr):
        """ Get report from actor
        """
        try:
            report = self.node.am.report(match.group(1))
            status = calvinresponse.OK
        except:
            report = None
            status = calvinresponse.NOT_FOUND
        self.send_response(
            handle, connection, None if report is None else json.dumps(report), status=status)

    def handle_actor_migrate(self, handle, connection, match, data, hdr):
        """ Migrate actor
        """
        self.node.am.migrate(match.group(1), data['peer_node_id'],
                             callback=CalvinCB(self.actor_migrate_cb, handle, connection))

    def actor_migrate_cb(self, handle, connection, status, *args, **kwargs):
        """ Migrate actor respons
        """
        self.send_response(handle, connection,
                           None, status=status.status)

    def handle_application_requirements(self, handle, connection, match, data, hdr):
        """ Apply application deployment requirements
            to actors of an application and initiate migration of actors accordingly
        """
        self.node.app_manager.deployment_add_requirements(match.group(1), data['reqs'],
                        cb=CalvinCB(func=self.handle_application_requirements_cb, handle=handle, connection=connection))

    def handle_application_requirements_cb(self, handle, connection, *args, **kwargs):
        self.send_response(handle, connection,
                           json.dumps({'placement': kwargs['placement'] if 'placement' in kwargs else {}}),
                                       status=kwargs['status'].status)

    def handle_actor_disable(self, handle, connection, match, data, hdr):
        try:
            self.node.am.disable(match.group(1))
            status = calvinresponse.OK
        except:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status)

    def handle_get_port(self, handle, connection, match, data, hdr):
        """ Get port from id
        """
        self.node.storage.get_port(match.group(2), CalvinCB(
            func=self.storage_cb, handle=handle, connection=connection))

    def handle_get_port_state(self, handle, connection, match, data, hdr):
        """ Get port from id
        """
        state = {}
        try:
            state = self.node.am.get_port_state(match.group(1), match.group(2))
            status = calvinresponse.OK
        except Exception as e:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, json.dumps(state), status)

    def handle_connect(self, handle, connection, match, data, hdr):
        """ Connect port
        """
        if "actor_id" not in data:
            data["actor_id"] = None
        if "port_name" not in data:
            data["port_name"] = None
        if "port_dir" not in data:
            data["port_dir"] = None
        if "port_id" not in data:
            data["port_id"] = None
        if "peer_node_id" not in data:
            data["peer_node_id"] = None
        if "peer_actor_id" not in data:
            data["peer_actor_id"] = None
        if "peer_port_name" not in data:
            data["peer_port_name"] = None
        if "peer_port_dir" not in data:
            data["peer_port_dir"] = None
        if "peer_port_id" not in data:
            data["peer_port_id"] = None

        self.node.connect(
            actor_id=data["actor_id"],
            port_name=data["port_name"],
            port_dir=data["port_dir"],
            port_id=data["port_id"],
            peer_node_id=data["peer_node_id"],
            peer_actor_id=data["peer_actor_id"],
            peer_port_name=data["peer_port_name"],
            peer_port_dir=data["peer_port_dir"],
            peer_port_id=data["peer_port_id"],
            cb=CalvinCB(self.handle_connect_cb, handle, connection))


    def handle_connect_cb(self, handle, connection, **kwargs):
        status = kwargs.get('status', None)
        peer_port_id = kwargs.get('peer_port_id', None)
        self.send_response(handle, connection, json.dumps({'peer_port_id': peer_port_id}) if status else None,
                           status=status.status)

    def handle_set_port_property(self, handle, connection, match, data, hdr):
        try:
            self.node.am.set_port_property(
                actor_id=data["actor_id"],
                port_type=data["port_type"],
                port_name=data["port_name"],
                port_property=data["port_property"],
                value=data["value"])
            status = calvinresponse.OK
        except:
            status = calvinresponse.NOT_FOUND
        self.send_response(handle, connection, None, status=status)

    def handle_deploy(self, handle, connection, match, data, hdr):
        try:
            _log.analyze(self.node.id, "+", {})
            app_info, errors, warnings = compiler.compile(
                data["script"], filename=data["name"], verify=data["check"] if "check" in data else True)
            _log.analyze(self.node.id, "+ COMPILED", {'app_info': app_info, 'errors': errors, 'warnings': warnings})
            app_info["name"] = data["name"]
            d = deployer.Deployer(
                runtime=None, deployable=app_info, node_info=None, node=self.node,
                verify=data["check"] if "check" in data else True)
            _log.analyze(self.node.id, "+ Deployer instanciated", {})
            app_id = d.deploy()
            _log.analyze(self.node.id, "+ DEPLOYED", {})
            status = calvinresponse.OK
        except:
            app_id = None
            status = calvinresponse.INTERNAL_ERROR

        self.send_response(
            handle, connection, json.dumps({'application_id': app_id, 'actor_map': d.actor_map}) if app_id else None,
            status=status)

    def handle_quit(self, handle, connection, match, data, hdr):
        async.DelayedCall(.2, self.node.stop)
        self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)

    def handle_disconnect(self, handle, connection, match, data, hdr):
        self.node.disconnect(
            data['actor_id'], data['port_name'], data['port_dir'], data['port_id'],
            cb=CalvinCB(self.handle_disconnect_cb, handle, connection))

    def handle_disconnect_cb(self, handle, connection, **kwargs):
        status = kwargs.get('status', None)
        self.send_response(handle, connection, None, status=status.status)

    def handle_post_index(self, handle, connection, match, data, hdr):
        """ Add to index
        """
        self.node.storage.add_index(
            match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

    def handle_delete_index(self, handle, connection, match, data, hdr):
        """ Remove from index
        """
        self.node.storage.remove_index(
            match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

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

    def handle_post_storage(self, handle, connection, match, data, hdr):
        """ Store in storage
        """
        self.node.storage.set("", match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

    def handle_get_storage(self, handle, connection, match, data, hdr):
        """ Get from storage
        """
        self.node.storage.get("", match.group(1), cb=CalvinCB(self.get_index_cb, handle, connection))

    def log_firing(self, actor_name, action_method, tokens_produced, tokens_consumed, production):
        """ Trace firing, sends data on log_sock
        """
        if self.log_connection is not None:
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            data = {}
            data['timestamp'] = st
            data['node_id'] = self.node.id
            data['type'] = 'fire'
            data['actor'] = actor_name
            data['action_method'] = action_method
            data['produced'] = tokens_produced
            data['consumed'] = tokens_consumed
            self.log_connection.send("data: %s\n\n" % json.dumps(data))

    def handle_options(self, handle, connection, match, data, hdr):
        """ Handle HTTP OPTIONS requests
        """
        response = "HTTP/1.1 200 OK\n"

        """ Copy the content of Access-Control-Request-Headers to the response
        """
        if 'access-control-request-headers' in hdr:
            response += "Access-Control-Allow-Headers: "+ \
                        hdr['access-control-request-headers']+"\n"

        response += "Content-Length: 0\n" \
                    "Access-Control-Allow-Origin: *\n" \
                    "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\n" \
                    "\n\r\n"

        connection.send(response)
