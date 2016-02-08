class Connection(object):
    """Represents a connection between two node-port pairs"""

    def __init__(self, node_id, port_id, peer_node_id, peer_port_id):
        self.node_id = node_id
        self.port_id = port_id
        self.peer_node_id = peer_node_id
        self.peer_port_id = peer_port_id
