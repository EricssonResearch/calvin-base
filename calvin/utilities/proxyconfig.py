import json
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.csparser.port_property_syntax import list_port_property_capabilities

_log = get_logger(__name__)

def set_proxy_config_cb(key, value, link, callback):
    if not value:
        callback(status=response.CalvinResponse(response.INTERNAL_ERROR, {'peer_node_id': key}))
        return
    callback(status=response.CalvinResponse(response.OK))

def set_proxy_config(peer_id, capabilities, port_property_capability, link, storage, callback, attributes):
    """
    Store node
    """
    _log.info("Peer '%s' connected" % peer_id)
    try:
        for c in list_port_property_capabilities(which=port_property_capability):
            storage.add_index(['node', 'capabilities', c], peer_id, root_prefix_level=3)
        for c in capabilities:
            storage.add_index(['node', 'capabilities', c], peer_id, root_prefix_level=3)
    except:
        _log.error("Failed to set capabilities")

    public = None
    indexed_public = None

    if attributes is not None:
        attributes = json.loads(attributes)
        attributes = AttributeResolver(attributes)
        indexes = attributes.get_indexed_public()
        for index in indexes:
            storage.add_index(index, peer_id)
        public = attributes.get_public()
        indexed_public = attributes.get_indexed_public(as_list=False)

    storage.set(prefix="node-", key=peer_id,
                value={"proxy": storage.node.id,
                "uris": None,
                "control_uris": None,
                "authz_server": None, # Set correct value
                "attributes": {'public': public,
                'indexed_public': indexed_public}},
                cb=CalvinCB(set_proxy_config_cb, link=link, callback=callback))

def handle_sleep_request(peer_id, link, seconds_to_sleep, callback):
    """
    Handle sleep request
    """
    _log.info("Peer '%s' requested sleep for %s seconds" % (peer_id, seconds_to_sleep))
    callback(status=response.CalvinResponse(response.OK))
    link.set_peer_insleep()
