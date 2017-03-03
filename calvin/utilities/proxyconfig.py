from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.csparser.port_property_syntax import list_port_property_capabilities

_log = get_logger(__name__)

def set_proxy_config_cb(key, value, callback):
    if not value:
        # the peer_id did not exist in storage
        callback(status=response.CalvinResponse(response.NOT_FOUND, {'peer_node_id': key}))
        return

    callback(status=response.CalvinResponse(response.OK))

def set_proxy_config(peer_id, name, capabilities, port_property_capability, storage, callback):
    """
    Store node
    """
    try:
        for c in list_port_property_capabilities(which=port_property_capability):
            storage.add_index(['node', 'capabilities', c], peer_id, root_prefix_level=3)
        for c in capabilities:
            storage.add_index(['node', 'capabilities', c], peer_id, root_prefix_level=3)
    except:
        _log.error("Failed to set capabilities")

    attributes = AttributeResolver({"indexed_public": {"node_name": {"name": name}}})
    indexes = attributes.get_indexed_public()
    try:
        for index in indexes:
            storage.add_index(index, peer_id)
    except:
        _log.error("Failed to add node index")

    storage.set(prefix="node-", key=peer_id,
                value={"proxy": storage.node.id,
                "uris": None,
                "control_uris": None,
                "authz_server": None, # Set correct value
                "attributes": {'public': attributes.get_public(),
                'indexed_public': attributes.get_indexed_public(as_list=False)}},
                cb=CalvinCB(set_proxy_config_cb, callback=callback))
