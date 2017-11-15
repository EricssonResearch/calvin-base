import json
from calvin.requests import calvinresponse
from routes import handler, uuid_re
from calvin.runtime.north.proxyhandler import ProxyHandler

@handler(r"GET /proxy/(NODE_" + uuid_re + "|" + uuid_re + ")/capabilities\sHTTP/1")
def handle_get_proxy_capabilities(self, handle, connection, match, data, hdr):
    """
    GET /proxy/<uuid>/capabilities
    Get capabilities from proxy peer
    Response status code: Capabilities
    """
    try:
        data = self.node.proxy_handler.get_capabilities(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_proxy_capabilities")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection,
            json.dumps(data) if status == calvinresponse.OK else None, status=status)
