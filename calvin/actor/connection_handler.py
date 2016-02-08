import calvin.utilities.calvinresponse as response
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class ConnectionHandler(object):
    def __init__(self, node):
        self.node = node

    def setup_connections(self, actor, prev_connections=None, connection_list=None, callback=None):
        _log.debug("Setting up connections for actor {}, prev_connections {}, connection_list {}".format(
            actor, prev_connections, connection_list))
        if prev_connections:
            # Convert prev_connections to connection_list format
            connection_list = self._prev_connections_to_connection_list(prev_connections)

        if connection_list:
            # Migrated actor
            self.connect(actor, connection_list, callback=callback)

    def setup_replica_connections(self, actor, state, prev_connections, callback=None):
        _log.debug("Setting up replica connections for actor {}, prev_connections {}".format(
            actor, prev_connections))
        connection_list = self._prev_connections_to_connection_list(prev_connections)

        port_id_translations = self._translate_port_ids(actor, prev_connections)
        connection_list = self._translate_connection_list(actor, connection_list, port_id_translations)
        state = self._translate_state(actor, state, port_id_translations)
        self.connect(actor, connection_list, callback=callback)

        for port in state['inports']:
            actor.inports[port]._set_state(state['inports'][port])

    def connections(self, actor):
        return actor.connections(self.node.id)

    def connect(self, actor, connection_list, callback=None):
        """
        Reconnecting the ports can be done using a connection_list
        of tuples (node_id i.e. our id, port_id, peer_node_id, peer_port_id)
        """
        _log.debug("Connecting actor {}, connection_list {}".format(actor, connection_list))
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
        for conn in prev_connections['inports']:
            cl.append((conn['node_id'], conn['port_id'], conn['peer_node_id'], conn['peer_port_id']))
        for conn in prev_connections['outports']:
            cl.append((conn['node_id'], conn['port_id'], conn['peer_node_id'], conn['peer_port_id']))
        return cl

    def _translate_port_ids(self, actor, prev_connections):
        port_id_translations = {}
        port_names = prev_connections['port_names']
        for (port_id, port_name) in port_names.iteritems():
            port_id_translations[port_id] = actor.inports[port_name].id if port_name in actor.inports else actor.outports[port_name].id

        return port_id_translations

    def _translate_connection_list(self, actor, connection_list, port_id_translations):
        """After replicating an actor, the list of previous connections
        contains port_ids for the original actor and must be updated.

        Args:
            connection_list: [(_, port_id, _, _), ...]
        Returns:
            [(_, updated_port_id, _, _), ...]
        """
        if not connection_list:
            return []

        translated_connection_list = []
        if port_id_translations:
            for node_id, port_id, peer_node_id, peer_port_id in connection_list:
                translated_connection_list.append((node_id, port_id_translations[port_id], peer_node_id, peer_port_id))

        return translated_connection_list

    def _translate_state(self, actor, state, port_id_translations):
        """Translates the port IDs in state inports to match IDs for the new
        replica.
        """
        inports = state['inports']
        new_inports = {}
        for port_name in inports:
            port = inports[port_name]
            if not port:
                continue

            fifo = port['fifo']

            new_readers = [port_id_translations[reader] for reader in fifo['readers']]

            new_tentative_read_pos = {}
            for port_id in fifo['tentative_read_pos']:
                val = fifo['tentative_read_pos'][port_id]
                new_tentative_read_pos[port_id_translations[port_id]] = val

            new_read_pos = {}
            for port_id in fifo['read_pos']:
                val = fifo['read_pos'][port_id]
                new_read_pos[port_id_translations[port_id]] = val

            new_inports[port_name] = {
                'name': port['name'],
                'fifo': {
                    'readers': new_readers,
                    'write_pos': fifo['write_pos'],
                    'N': fifo['N'],
                    'tentative_read_pos': new_tentative_read_pos,
                    'read_pos': new_read_pos,
                    'fifo': fifo['fifo']
                },
                'id': port_id_translations[port['id']]
            }

        state['inports'] = new_inports
        return state
