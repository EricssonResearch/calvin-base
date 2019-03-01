from __future__ import print_function
from calvin.utilities import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

class StorageProxyServer(object):
    """docstring for StorageProxyServer"""
    def __init__(self, node, storage):
        super(StorageProxyServer, self).__init__()
        self.storage = storage
        self.node = node
        self.tunnel = {}
        # print self.node.id, "PROXY SERVER"
        # We are not proxy client, so we can be proxy bridge/master
        self._proxy_cmds = {
            'GET': self.storage.get,
            'SET': self.storage.set,
            'DELETE': self.storage.delete,
            'ADD_INDEX': self.storage.add_index,
            'REMOVE_INDEX': self.storage.remove_index,
            'GET_INDEX': self.storage.get_index,
            'REPLY': self._proxy_reply,
        }
        try:
            # print "TRY: register_tunnel_handler"
            self.node.proto.register_tunnel_handler('storage', CalvinCB(self.tunnel_request_handles))
        except:
            print("FAILED: register_tunnel_handler")
            
            # OK, then skip being a proxy server
            # FIXME: Set to None?
            pass

    def tunnel_request_handles(self, tunnel):
        """ Incoming tunnel request for storage proxy server"""
        # TODO check if we want a tunnel first
        # print self.node.id, "+ SERVER %s", {'tunnel_id': tunnel.id}
        self.tunnel[tunnel.peer_node_id] = tunnel
        tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
        tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
        tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
        # We accept it by returning True
        return True

    def tunnel_down(self, tunnel):
        """ Callback that the tunnel is not accepted or is going down """
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, tunnel):
        """ Callback that the tunnel is working """
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def _proxy_reply(self, cb, *args, **kwargs):
        # Should not get any replies to the server but log it just in case
        # _log.analyze(self.node.id, "+ SERVER", {args: args, 'kwargs': kwargs})
        raise Exception("Should not get any replies to the proxy server")

    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a storage client request"""
        # print "Storage proxy request %s" % payload
        if 'cmd' in payload and payload['cmd'] in self._proxy_cmds:
            # Call this node's storage methods, which could be local or DHT,
            # prefix is empty since that is already in the key (due to these calls come from the storage plugin level).
            kwargs = {k: v for k, v in payload.iteritems() if k in ('key', 'value', 'index')}
            if payload['cmd'].endswith("_INDEX"):
                kwargs['root_prefix_level'] = 0
                dummykey = {'key': None}
            else:
                kwargs['prefix'] = ''
                dummykey = {}
            command = self._proxy_cmds[payload['cmd']]
            # print "tunnel_recv_handler", command, "cb", kwargs
            command(cb=CalvinCB(self._proxy_send_reply, tunnel=tunnel, msgid=payload['msg_uuid'], **dummykey), **kwargs)
        else:
            _log.error("Unknown storage proxy request %s" % payload['cmd'] if 'cmd' in payload else "")

    def _proxy_send_reply(self, key, value, tunnel, msgid):
        # print self.node.id, "+ SERVER", {'msgid': msgid, 'key': key, 'value': value}
        # When a CalvinResponse send it on key 'response' instead of 'value'
        status = isinstance(value, calvinresponse.CalvinResponse)
        svalue = value.encode() if status else value
        response = 'response' if status else 'value'
        kwargs = {'cmd': 'REPLY', 'msg_uuid': msgid, response: svalue}
        if key is not None:
            kwargs['key'] = key
        tunnel.send(kwargs)
