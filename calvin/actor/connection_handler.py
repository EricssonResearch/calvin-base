from calvin.utilities.calvin_callback import CalvinCB
import calvin.utilities.calvinresponse as response


class ConnectionHandler(object):
    def __init__(self, node):
        self.node = node

    def setup_connections(self, actor, prev_connections=None, connection_list=None, callback=None):
        if prev_connections:
            # Convert prev_connections to connection_list format
            connection_list = self._prev_connections_to_connection_list(prev_connections)

        if connection_list:
            # Migrated actor
            self.connect(actor, connection_list, callback=callback)

    def connections(self, actor):
        return actor.connections(self.node.id)

    def connect(self, actor, connection_list, callback=None):
        """
        Reconnecting the ports can be done using a connection_list
        of tuples (node_id i.e. our id, port_id, peer_node_id, peer_port_id)
        """
        peer_port_ids = [c[3] for c in connection_list]

        for node_id, port_id, peer_node_id, peer_port_id in connection_list:
            self.node.pm.connect(port_id=port_id,
                                 peer_node_id=peer_node_id,
                                 peer_port_id=peer_port_id,
                                 callback=CalvinCB(self._actor_connected,
                                                   peer_port_id=peer_port_id,
                                                   actor_id=actor.id,
                                                   peer_port_ids=peer_port_ids,
                                                   _callback=callback))

    def _actor_connected(self, status, peer_port_id, actor_id, peer_port_ids, _callback, **kwargs):
        """ Get called for each of the actor's ports when connecting, but callback should only be called once
            status: success or not
            _callback: original callback
            peer_port_ids: list of port ids kept in context between calls when *changed* by this function,
                           do not replace it
        """
        # Send negative response if not already done it
        if not status and peer_port_ids:
            if _callback:
                del peer_port_ids[:]
                _callback(status=response.CalvinResponse(False), actor_id=actor_id)
        if peer_port_id in peer_port_ids:
            # Remove this port from list
            peer_port_ids.remove(peer_port_id)
            # If all ports done send OK
            if not peer_port_ids:
                if _callback:
                    _callback(status=response.CalvinResponse(True), actor_id=actor_id)

    def _prev_connections_to_connection_list(self, prev_connections):
        """Convert prev_connection format to connection_list format"""
        cl = []
        for in_port_id, out_id in prev_connections['inports'].iteritems():
            cl.append((self.node.id, in_port_id, out_id[0], out_id[1]))
        for out_port_id, in_list in prev_connections['outports'].iteritems():
            for in_id in in_list:
                cl.append((self.node.id, out_port_id, in_id[0], in_id[1]))
        return cl
