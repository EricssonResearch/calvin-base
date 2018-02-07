import json
from calvin.requests import calvinresponse
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south.plugins.async import async
from routes import handler, register
from authentication import authentication_decorator
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib

_log = get_logger(__name__)

#Can't be access controlled, as it is needed to find authorization server
#    @authentication_decorator
@handler(r"GET /id\sHTTP/1")
def handle_get_node_id(self, handle, connection, match, data, hdr):
    """
    GET /id
    Get id of this calvin node
    Response status code: OK
    Response: node-id
    """
    self.send_response(handle, connection, json.dumps({'id': self.node.id}))


@handler(r"GET /capabilities\sHTTP/1")
def handle_get_node_capabilities(self, handle, connection, match, data, hdr):
    """
    GET /capabilities
    Get capabilities of this calvin node
    Response status code: OK
    Response: list of capabilities
    """
    self.send_response(handle, connection, json.dumps(get_calvinsys().list_capabilities() + get_calvinlib().list_capabilities()))


@handler(r"POST /peer_setup\sHTTP/1")
def handle_peer_setup(self, handle, connection, match, data, hdr):
    """
    POST /peer_setup
    Add calvin nodes to network
    Body: {"peers: ["calvinip://<address>:<port>", ...] }
    Response status code: OK or SERVICE_UNAVAILABLE
    Response: {<peer control uri>: [<peer node id>, <per peer status>], ...}
    """
    _log.analyze(self.node.id, "+", data)
    self.node.peersetup(data['peers'], cb=CalvinCB(self.handle_peer_setup_cb, handle, connection))

@register
def handle_peer_setup_cb(self, handle, connection, status=None, peer_node_ids=None):
    _log.analyze(self.node.id, "+", status.encode())
    if peer_node_ids:
        data = json.dumps({k: (v[0], v[1].status) for k, v in peer_node_ids.items()})
    else:
        data = None
    self.send_response(handle, connection, data, status=status.status)


@handler(r"GET /nodes\sHTTP/1")
@authentication_decorator
def handle_get_nodes(self, handle, connection, match, data, hdr):
    """
    GET /nodes
    List nodes in network (excluding self) known to self
    Response status code: OK
    Response: List of node-ids
    """
    self.send_response(handle, connection, json.dumps(self.node.network.list_links()))


@handler(r"DELETE /node(?:/(now|migrate|clean))?\sHTTP/1")
@authentication_decorator
def handle_quit(self, handle, connection, match, data, hdr):
    """
    DELETE /node{/now|/migrate|/clean}
    Stop (this) calvin node
     now: stop the runtime without handling actors on the runtime
     migrate: migrate any actors before stopping the runtime
     clean: stop & destroy all actors before stopping [default]
    Response status code: ACCEPTED
    Response: none
    """

    if match.group(1) == "now":
        stop_method = self.node.stop
    elif match.group(1) == "migrate":
        stop_method = self.node.stop_with_migration
    else: # Clean up
        stop_method = self.node.stop_with_cleanup

    async.DelayedCall(.2, stop_method)
    self.send_response(handle, connection, None, status=calvinresponse.ACCEPTED)


@handler(r"OPTIONS /[^\s]*\sHTTP/1")
@authentication_decorator
def handle_options(self, handle, connection, match, data, hdr):
    """
    OPTIONS /url
    Request for information about the communication options available on url
    Response status code: OK
    Response: Available communication options
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
