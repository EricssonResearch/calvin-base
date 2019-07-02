
from calvin.common import calvinresponse
from calvin.common.calvin_callback import CalvinCB
from calvin.common import calvinlogger
from calvin.runtime.north.calvin_proto import TunnelHandler

_log = calvinlogger.get_logger(__name__)

class StorageProxyTunnelHandler(TunnelHandler):
    """docstring for StorageProxyTunnelHandler"""
    def __init__(self, proto, proxy_cmds):
        super(StorageProxyTunnelHandler, self).__init__(proto, 'storage', proxy_cmds)            

    # FIXME: Clean up this mess
    
    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a storage client request"""
        # Call this node's storage methods, which could be local or DHT,
        # prefix is empty since that is already in the key (due to these calls come from the storage plugin level).
        kwargs = {k: v for k, v in iter(payload.items()) if k in ('key', 'value', 'index')}
        if payload['cmd'].endswith("_INDEX"):
            kwargs['root_prefix_level'] = 0
            dummykey = {'key': None}
        else:
            kwargs['prefix'] = ''
            dummykey = {}
        command = self._proxy_cmds[payload['cmd']]
        # print "tunnel_recv_handler", command, "cb", kwargs
        command(cb=CalvinCB(self._proxy_send_reply, tunnel=tunnel, msgid=payload['msg_uuid'], **dummykey), **kwargs)


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
    

# FIXME: Get rid of node (-> proto) and self.storage (unnecessary)
class StorageProxyServer(object):
    """docstring for StorageProxyServer"""
    def __init__(self, node, storage):
        super(StorageProxyServer, self).__init__()
        self.storage = storage
        # We are not proxy client, so we can be proxy bridge/master
        proxy_cmds = {
            'GET': self.storage.get,
            'SET': self.storage.set,
            'DELETE': self.storage.delete,
            'ADD_INDEX': self.storage.add_index,
            'REMOVE_INDEX': self.storage.remove_index,
            'GET_INDEX': self.storage.get_index,
            'REPLY': self._proxy_reply,
        }
        self.tunnel_handler = StorageProxyTunnelHandler(node.proto, proxy_cmds)
    
    def _proxy_reply(self, cb, *args, **kwargs):
        # Should not get any replies to the server but log it just in case
        # _log.analyze(self.node.id, "+ SERVER", {args: args, 'kwargs': kwargs})
        raise Exception("Should not get any replies to the proxy server")
    

