from twisted.web import server, resource
from twisted.internet import reactor


class SimpleSSE(resource.Resource):
    isLeaf = True
    connections = []
    # lc = None

    def responseCallback(self, err, request):
        request.finish
        print('Connection was either disconnected/error from: ' + str(request))
        self.connections.remove(request)

    def add_headers(self, request):
        request.setHeader('Content-Type',
                          'text/event-stream; charset=utf-8')
        request.setHeader("Access-Control-Allow-Origin", "*")
        return request

    def push_sse_message(self, req, msg):
        event_line = "data: {}\r\n".format(msg)
        req.write(event_line + '\r\n')

    def send(self, index, msg):
        if index < 0 or index >= len(connections):
            print "No such client"
            return
        self.push_sse_message(connections[index], msg)

    def send_msg_to_all_requests(self, msg):
        for req in self.connections:
            self.push_sse_message(req=req, msg=msg)

    def render_GET(self, request):
        request = self.add_headers(request)  # 2. Format Headers
        request.write("")  # send an acknowledgement back to user
        request.notifyFinish().addErrback(self.responseCallback, request)  # add callback
        # acknowledge the client that you have received a connection
        self.connections.append(request)  # 3. Keep track of each request
        print "added", request
        return server.NOT_DONE_YET  # 1. Persist the connection

    def broadcast(self, msg):
        self.send_msg_to_all_requests(msg)

class EventSource(object):
    """docstring for EventSource"""
    def __init__(self, port):
        super(EventSource, self).__init__()
        self._sender = SimpleSSE()
        self._eventsource = reactor.listenTCP(port, server.Site(self._sender))

    def broadcast(self, msg="Hello, World!"):
        self._sender.broadcast(msg)

    def send(self, index, msg="Hello, World!"):
        self._sender.send(index, msg)
