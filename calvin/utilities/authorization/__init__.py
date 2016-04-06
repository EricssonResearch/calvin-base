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
from calvin.requests.request_handler import RequestHandler
from calvin.utilities import certificate
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_log = get_logger(__name__)
try:
    sec_conf = _conf.get("security","security_conf")
except Exception:
    sec_conf = None
request_handler = RequestHandler()

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
    ip_addr = sec_conf['authorization']['server_ip']
    port = sec_conf['authorization']['server_port']
    # Alternative: specify node_id/dnQualifier instead in sec_conf and create a tunnel for the 
    # runtime-to-runtime communication (see calvin_proto.py). Could also add node_id as "aud" (audience) in jwt payload.
    authorization_server_uri = "http://%s:%d" % (ip_addr, port) 
    payload = {
        "iss": node.id, 
        "iat": datetime.utcnow(), 
        "exp": datetime.utcnow() + timedelta(seconds=60),
        "attributes": node.attributes.get_indexed_public_with_keys()
    }
    cert_conffile = _conf.get("security", "certificate_conf")
    domain = _conf.get("security", "certificate_domain")
    cert_conf = certificate.Config(cert_conffile, domain)
    node_name = node.attributes.get_node_name_as_str()
    private_key = certificate.get_private_key(cert_conf, node_name)
    # Create a JSON Web Token signed using the node's Elliptic Curve private key.
    jwt_request = jwt.encode(payload, private_key, algorithm='ES256')
    # cert_name is this node's certificate filename (without file extension)
    cert_name = certificate.get_own_cert_name(cert_conf, node_name)
    # Send request to authorization server.
    request_handler.register_node_authorization(authorization_server_uri, jwt_request, cert_name)