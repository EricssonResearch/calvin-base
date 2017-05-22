from twisted.web import server, resource
from twisted.internet import reactor


class SimpleSSE(resource.Resource):
    isLeaf = True
    connections = []

    def responseCallback(self, err, request):
        request.finish
        print('Connection was either disconnected/error from: ' + str(request))
        self.connections.remove(request)

    def render_GET(self, request):
        request.setHeader('Content-Type',
                          'text/event-stream; charset=utf-8')
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write("")
        request.notifyFinish().addErrback(self.responseCallback, request)
        self.connections.append(request)
        return server.NOT_DONE_YET  # 1. Persist the connection

    def _send(self, request, msg):
        fmt_msg = "data: {}\r\n".format(msg)
        request.write(fmt_msg + '\r\n')

    def send(self, client_id, msg):
        if client_id < 0 or client_id >= len(connections):
            print "No such client"
            return
        self._send(connections[client_id], msg)

    def broadcast(self, msg):
        for request in self.connections:
            self._send(request=request, msg=msg)

class EventSource(object):
    """docstring for EventSource"""
    def __init__(self, port):
        super(EventSource, self).__init__()
        self._eventsource = SimpleSSE()
        self._tcp_port = reactor.listenTCP(port, server.Site(self._eventsource))

    def stop(self):
        print "FIXME: Implement STOP"

    def broadcast(self, msg="Hello, World!"):
        self._eventsource.broadcast(msg)

    def send(self, client_id, msg="Hello, World!"):
        self._eventsource.send(client_id, msg)
