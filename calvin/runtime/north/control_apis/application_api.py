import json
from calvin.requests import calvinresponse
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.issuetracker import IssueTracker
from calvin.csparser import cscompile as compiler
from calvin.csparser.dscodegen import calvin_dscodegen
from calvin.runtime.north.appmanager import Deployer
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities.security import security_enabled
from routes import handler, register, uuid_re
from authentication import authentication_decorator

_log = get_logger(__name__)

@handler(r"GET /applications\sHTTP/1")
@authentication_decorator
def handle_get_applications(self, handle, connection, match, data, hdr):
    """
    GET /applications
    Get applications launched from this node
    Response status code: OK
    Response: List of application ids
    """
    self.send_response(handle, connection, json.dumps(self.node.app_manager.list_applications()))


@handler(r"DELETE /application/(APP_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")
@authentication_decorator
def handle_del_application(self, handle, connection, match, data, hdr):
    """
    DELETE /application/{application-id}
    Stop application (only applications launched from this node)
    Response status code: OK, NOT_FOUND, INTERNAL_ERROR
    Response: [<actor_id>, ...] when error list of actors (replicas) in application not destroyed
    """
    try:
        self.node.app_manager.destroy(match.group(1), cb=CalvinCB(self.handle_del_application_cb,
                                                                    handle, connection))
    except:
        _log.exception("Destroy application failed")
        self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

@register
def handle_del_application_cb(self, handle, connection, status=None):
    if not status and status.data:
        data = json.dumps(status.data)
    else:
        data = None
    self.send_response(handle, connection, data, status=status.status)


@handler(r"POST /actor\sHTTP/1")
@authentication_decorator
def handle_new_actor(self, handle, connection, match, data, hdr):
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
    try:
        actor_id = self.node.new(actor_type=data['actor_type'], args=data[
                                 'args'], deploy_args=data['deploy_args'])
        status = calvinresponse.OK
    except:
        actor_id = None
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(
        handle, connection, None if actor_id is None else json.dumps({'actor_id': actor_id}), status=status)


@handler(r"GET /actors\sHTTP/1")
@authentication_decorator
def handle_get_actors(self, handle, connection, match, data, hdr):
    """
    GET /actors
    Get list of actors on this runtime
    Response status code: OK
    Response: list of actor ids
    """
    actors = self.node.am.list_actors()
    self.send_response(
        handle, connection, json.dumps(actors))


@handler(r"DELETE /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")
@authentication_decorator
def handle_del_actor(self, handle, connection, match, data, hdr):
    """
    DELETE /actor/{actor-id}
    Delete actor
    Response status code: OK or NOT_FOUND
    Response: none
    """
    try:
        self.node.am.destroy(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("Destroy actor failed")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status=status)


# FIXME: The regex cannot possibly be correct?
@handler(r"(?:GET|POST) /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/report\sHTTP/1")
@authentication_decorator
def handle_actor_report(self, handle, connection, match, data, hdr):
    """
    GET /actor/{actor-id}/report
    Some actor store statistics on inputs and outputs, this reports these. Not always present.
    Response status code: OK or NOT_FOUND
    Response: Depends on actor
    """
    try:
        # Now we allow passing in arguments (must be dictionary or None)
        report = self.node.am.report(match.group(1), data)
        status = calvinresponse.OK
    except:
        _log.exception("Actor report failed")
        report = None
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None if report is None else json.dumps(report, default=repr), status=status)


@handler(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/migrate\sHTTP/1")
@authentication_decorator
def handle_actor_migrate(self, handle, connection, match, data, hdr):
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
        self.send_response(handle, connection, None, status=status)

@register
def actor_migrate_cb(self, handle, connection, status, *args, **kwargs):
    """ Migrate actor respons
    """
    self.send_response(handle, connection, None, status=status.status)


@handler(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/disable\sHTTP/1")
@authentication_decorator
def handle_actor_disable(self, handle, connection, match, data, hdr):
    """
    POST /actor/{actor-id}/disable
    DEPRECATED. Disables an actor
    Response status code: OK or NOT_FOUND
    Response: none
    """
    try:
        self.node.am.disable(match.group(1))
        status = calvinresponse.OK
    except:
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status)


@handler(r"POST /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/replicate\sHTTP/1")
@authentication_decorator
def handle_actor_replicate(self, handle, connection, match, data, hdr):
    """
    POST /actor/{actor-id}/replicate
    ONLY FOR TEST. Will replicate an actor directly
    Response status code: OK or NOT_FOUND
    Response: {'actor_id': <replicated actor instance id>}
    """
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

@register
def handle_actor_replicate_cb(self, handle, connection, status):
    self.send_response(handle, connection, json.dumps(status.data), status=status.status)


@handler(r"GET /actor/(ACTOR_" + uuid_re + "|" + uuid_re + ")/port/(PORT_" + uuid_re + "|" + uuid_re + ")/state\sHTTP/1")
@authentication_decorator
def handle_get_port_state(self, handle, connection, match, data, hdr):
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
    self.send_response(handle, connection, json.dumps(state), status)


@handler(r"POST /connect\sHTTP/1")
@authentication_decorator
def handle_connect(self, handle, connection, match, data, hdr):
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

@register
def handle_connect_cb(self, handle, connection, **kwargs):
    status = kwargs.get('status', None)
    peer_port_id = kwargs.get('peer_port_id', None)
    self.send_response(handle, connection, json.dumps({'peer_port_id': peer_port_id}) if status else None,
                       status=status.status)
    _log.debug("Handle connect finnished")


@handler(r"POST /set_port_property\sHTTP/1")
@authentication_decorator
def handle_set_port_property(self, handle, connection, match, data, hdr):
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


@handler(r"POST /deploy\sHTTP/1")
@authentication_decorator
def handle_deploy(self, handle, connection, match, data, hdr):
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

@register
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

@register
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


@handler(r"POST /application/(APP_" + uuid_re + "|" + uuid_re + ")/migrate\sHTTP/1")
@authentication_decorator
def handle_post_application_migrate(self, handle, connection, match, data, hdr):
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
                                               cb=CalvinCB(self.handle_post_application_migrate_cb, handle, connection))
    except:
        _log.exception("App migration failed")
        self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)

@register
def handle_post_application_migrate_cb(self, handle, connection, status, **kwargs):
    _log.analyze(self.node.id, "+ MIGRATED", {'status': status.status})
    self.send_response(handle, connection, None, status=status.status)

@handler(r"POST /disconnect\sHTTP/1")
@authentication_decorator
def handle_disconnect(self, handle, connection, match, data, hdr):
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

@register
def handle_disconnect_cb(self, handle, connection, **kwargs):
    status = kwargs.get('status', None)
    _log.analyze(self.node.id, "+ DISCONNECTED", {'status': status.status}, tb=True)
    self.send_response(handle, connection, None, status=status.status)
