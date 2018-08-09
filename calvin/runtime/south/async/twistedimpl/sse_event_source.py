from twisted.web import server, resource
from twisted.internet import reactor
import json


class SimpleSSE(resource.Resource):
    isLeaf = True
    connections = {}

    def responseCallback(self, err, connection):
        connection.finish
        keylist = [k for k,v in connections.iteritems() if v == connection]
        for key in keylist:
            connections.pop(key)

    def _validate_connection(self, postpath):
        if len(postpath) is not 2:
            return None
        if postpath[0] != "client_id" or postpath[1] == "":
            return None
        return postpath[1]

    def render_GET(self, request):
        client_id = self._validate_connection(request.postpath)
        if not client_id:
            request.setResponseCode(400)
            return "Bad Request\n"

        request.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write("")
        request.notifyFinish().addErrback(self.responseCallback, request)
        self.connections[client_id] = request
        return server.NOT_DONE_YET

    def _send(self, connection, data):
        fmt_msg = "data: {}\r\n".format(json.dumps(data))
        connection.write(fmt_msg + '\r\n')

    def send(self, client_id, data):
        if client_id in self.connections:
            self._send(connections[client_id], data)

    def broadcast(self, data):
        for connection in self.connections.values():
            self._send(connection, data)

class EventSource(object):
    """docstring for EventSource"""
    def __init__(self, port):
        super(EventSource, self).__init__()
        self._eventsource = SimpleSSE()
        self._tcp_port = reactor.listenTCP(port, server.Site(self._eventsource))

    def stop(self):
        print "FIXME: Implement STOP"

    def broadcast(self, data):
        self._eventsource.broadcast(data)

    def send(self, client_id, data):
        self._eventsource.send(client_id, data)
