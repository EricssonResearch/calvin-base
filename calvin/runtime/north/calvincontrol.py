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
from calvin.utilities import calvinuuid
from calvin.utilities.issuetracker import IssueTracker
#
# Dynamically build selected set of APIs
#
from control_apis import routes
from control_apis import security_api
from control_apis import runtime_api
from control_apis import documentation_api
from control_apis import logging_api
from control_apis import metering_api
from control_apis import registry_api

_log = get_logger(__name__)

uuid_re = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

control_api_doc = ""

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
            # (re_get_base_doc, self.handle_get_base_doc),
            # (re_get_actor_doc, self.handle_get_actor_doc),
            # (re_post_log, self.handle_post_log),
            # (re_delete_log, self.handle_delete_log),
            # (re_get_log, self.handle_get_log),
            # (re_get_node_id, self.handle_get_node_id),
            # (re_get_node_capabilities, self.handle_get_node_capabilities),
            # (re_get_nodes, self.handle_get_nodes),
            # (re_get_node, self.handle_get_node),
            # (re_post_node_attribute_indexed_public, self.handle_post_node_attribute_indexed_public),
            # (re_post_peer_setup, self.handle_peer_setup),
            (re_get_applications, self.handle_get_applications),
            # (re_get_application, self.handle_get_application),
            (re_del_application, self.handle_del_application),
            (re_post_new_actor, self.handle_new_actor),
            (re_get_actors, self.handle_get_actors),
            # (re_get_actor, self.handle_get_actor),
            (re_del_actor, self.handle_del_actor),
            (re_actor_report, self.handle_actor_report),
            (re_post_actor_migrate, self.handle_actor_migrate),
            (re_post_actor_disable, self.handle_actor_disable),
            (re_post_actor_replicate, self.handle_actor_replicate),
            # (re_get_port, self.handle_get_port),
            (re_get_port_state, self.handle_get_port_state),
            (re_post_connect, self.handle_connect),
            (re_set_port_property, self.handle_set_port_property),
            (re_post_deploy, self.handle_deploy),
            (re_post_application_migrate, self.handle_post_application_migrate),
            # (re_delete_node, self.handle_quit),
            (re_post_disconnect, self.handle_disconnect),
            # (re_post_meter, self.handle_post_meter),
            # (re_delete_meter, self.handle_delete_meter),
            # (re_get_timed_meter, self.handle_get_timed_meter),
            # (re_get_aggregated_meter, self.handle_get_aggregated_meter),
            # (re_get_metainfo_meter, self.handle_get_metainfo_meter),
            # (re_post_index, self.handle_post_index),
            # (re_delete_index, self.handle_delete_index),
            # (re_get_index, self.handle_get_index),
            # (re_get_storage, self.handle_get_storage),
            # (re_dump_storage, self.handle_dump_storage),
            # (re_post_storage, self.handle_post_storage),
            # (re_post_certificate_signing_request,self.handle_post_certificate_signing_request),
            # (re_edit_certificate_enrollment_password, self.handle_edit_certificate_enrollment_password),
            # (re_get_certificate_enrollment_password, self.handle_get_certificate_enrollment_password),
            # (re_get_authentication_users_db, self.handle_get_authentication_users_db),
            # (re_edit_authentication_users_db, self.handle_edit_authentication_users_db),
            # (re_get_authentication_groups_db, self.handle_get_authentication_groups_db),
            # (re_edit_authentication_groups_db, self.handle_edit_authentication_groups_db),
            # (re_post_new_authorization_policy, self.handle_new_authorization_policy),
            # (re_get_authorization_policies, self.handle_get_authorization_policies),
            # (re_get_authorization_policy, self.handle_get_authorization_policy),
            # (re_edit_authorization_policy, self.handle_edit_authorization_policy),
            # (re_del_authorization_policy, self.handle_del_authorization_policy),
            # (re_options, self.handle_options)
        ]

        dynamic_routes = routes.install_handlers(self)
        self.routes.extend(dynamic_routes)

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

    def _handler_for_route(self, command):
        for re_route, handler in self.routes:
            match_object = re_route.match(command)
            if match_object:
                # FIXME: Return capture groups instead
                return handler, match_object
        return None, None

    def route_request(self, handle, connection, command, headers, data):
        if self.node.quitting:
            # Answer internal error on all requests while quitting, assume client can handle that
            # TODO: Answer permantely moved (301) instead with header Location: <another-calvin-runtime>???
            self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)
            return
        try:
            issuetracker = IssueTracker()
            handler, match = self._handler_for_route(command)
            if handler:
                credentials = None
                if data:
                    data = json.loads(data)
                _log.debug("Calvin control handles:%s\n%s\n---------------" % (command, data))
                handler(handle, connection, match, data, headers)
            else:
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


    @authentication_decorator
    def handle_get_applications(self, handle, connection, match, data, hdr):
        """ Get applications
        """
        self.send_response(
            handle, connection, json.dumps(self.node.app_manager.list_applications()))

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
        # FIXME: The long and winding construct should be replaced by the more concise:
        #        self.node.connect(**data, cb=CalvinCB(self.handle_connect_cb, handle, connection))
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


    #
    # Logging hooks
    #
    def log_actor_firing(self, actor_id, action_method, tokens_produced, tokens_consumed, production):
        pass

    def log_actor_new(self, actor_id, actor_name, actor_type, is_shadow):
        pass

    def log_actor_destroy(self, actor_id):
        pass

    def log_actor_migrate(self, actor_id, dest_node_id):
        pass

    def log_actor_replicate(self, actor_id, replica_actor_id, replication_id, dest_node_id):
        pass

    def log_actor_dereplicate(self, actor_id, replica_actor_id, replication_id):
        pass

    def log_application_new(self, application_id, application_name):
        pass

    def log_application_destroy(self, application_id):
        pass

    def log_link_connected(self, peer_id, uri):
        pass

    def log_link_disconnected(self, peer_id):
        pass

    def log_log_message(self, message):
        pass



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
