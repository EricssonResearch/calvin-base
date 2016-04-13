# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta
try:
    import jwt
    HAS_JWT = True
except:
    HAS_JWT = False
from calvin.utilities.security import encode_jwt
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_log = get_logger(__name__)
try:
    sec_conf = _conf.get("security","security_conf")
except Exception:
    sec_conf = None

def register_node(node):
    """Register node attributes for authorization."""
    try:
        if sec_conf['authorization']['procedure'] == "external":
            if not HAS_JWT:
                _log.error("Security: Install JWT to use external server as authorization method.")
                return False
            _log.debug("Register node for external authorization")
            register_node_external(node)
        else:
            _log.debug("Register node for local authorization")
            node.pdp.register_node(node.id, node.attributes.get_indexed_public_with_keys())
        return True
    except Exception as e:
        _log.error("Node could not be registered for authorization - %s" % str(e))
        return False

def register_node_external(node):
    """Register node attributes for external authorization"""
    # FIXME: should this include certificate exchange?
    authz_server_id = sec_conf['authorization']['server_uuid']
    payload = {
        "iss": node.id, 
        "aud": authz_server_id, 
        "iat": datetime.utcnow(), 
        "exp": datetime.utcnow() + timedelta(seconds=60),
        "attributes": node.attributes.get_indexed_public_with_keys()
    }
    # Create a JSON Web Token signed using the node's Elliptic Curve private key.
    jwt_request = encode_jwt(payload, node.node_name)
    # Send request to authorization server.
    # TODO: add callback
    node.proto.authorization_register(authz_server_id, None, jwt_request)