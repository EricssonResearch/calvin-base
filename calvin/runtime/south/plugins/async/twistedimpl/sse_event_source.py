from twisted.web import server, resource
from twisted.internet import reactor
import json


class SimpleSSE(resource.Resource):
    isLeaf = True
    # FIXME: Rename connnections
    client_ids = {}

    def responseCallback(self, err, request):
        request.finish
        print('Connection was either disconnected/error from: ' + str(request))
        keylist = [k for k,v in client_ids.iteritems() if v == request]
        for key in keylist:
            client_ids.pop(key)

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

        request.setHeader('Content-Type',
                          'text/event-stream; charset=utf-8')
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write("")
        request.notifyFinish().addErrback(self.responseCallback, request)
        self.client_ids[client_id] = request
        return server.NOT_DONE_YET

    def _send(self, request, data):
        fmt_msg = "data: {}\r\n".format(json.dumps(data))
        request.write(fmt_msg + '\r\n')

    def send(self, client_id, data):
        if client_id not in self.client_ids:
            print "No such client"
            return
        self._send(client_ids[client_id], data)

    def broadcast(self, data):
        for request in self.client_ids.values():
            self._send(request, data)

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
