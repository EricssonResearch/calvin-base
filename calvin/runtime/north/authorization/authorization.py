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

import os
from datetime import datetime, timedelta
try:
    import jwt
    HAS_JWT = True
except:
    HAS_JWT = False
from calvin.utilities.security import decode_jwt, encode_jwt
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.authorization.policy_decision_point import PolicyDecisionPoint
from calvin.runtime.north.authorization.policy_retrieval_point import FilePolicyRetrievalPoint
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig

_log = get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf.get("security","security_conf")

class Authorization(object):
    """Authorization helper functions"""

    def __init__(self, node):
        self.node = node
        try:
            if _sec_conf['authorization']['procedure'] == "local":
                self.pdp = PolicyDecisionPoint(self.node, _sec_conf['authorization'] if _sec_conf else None)
                try:
                    self.prp = FilePolicyRetrievalPoint(_sec_conf['authorization']["policy_storage_path"])
                except:
                    self.prp = FilePolicyRetrievalPoint(os.path.join(os.path.expanduser("~"), 
                                                                     ".calvin", "security", "policies"))
                self.authz_server_id = self.node.id
            else:
                self.authz_server_id = _sec_conf['authorization']['server_uuid']
        except Exception:
            self.authz_server_id = None

    def decode_request(self, data):
        """Decode the JSON Web Token in the data."""
        return decode_jwt(data["jwt"], data["cert_name"], self.node.node_name, self.node.id)

    def encode_response(self, request, response, audience=None):
        """Encode the response to the request as a JSON Web Token."""
        jwt_payload = {
            "iss": self.node.id, 
            "aud": request["iss"] if audience is None else audience, 
            "iat": datetime.utcnow(), 
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "response": response
        }
        if "sub" in request:
            jwt_payload["sub"] = request["sub"]
        # Create a JSON Web Token signed using the authorization server's private key.
        return encode_jwt(jwt_payload, self.node.node_name)

    def register_node(self):
        """Register node attributes for authorization."""
        if _sec_conf and "authorization" in _sec_conf:
            # TODO: the node should contact the authz server regularly (once a day?), 
            #       otherwise it should be removed from the registered_nodes list on the authz server.
            try:
                if _sec_conf['authorization']['procedure'] == "external":
                    if not HAS_JWT:
                        _log.error("Security: Install JWT to use external server as authorization method.")
                        return
                    self.register_node_external()
                else:
                    self.pdp.register_node(self.node.id, self.node.attributes.get_indexed_public_with_keys())
            except Exception as e:
                _log.error("Node could not be registered for authorization - %s" % str(e))

    def register_node_external(self):
        """Register node attributes for external authorization"""
        # FIXME: should this include certificate exchange?
        payload = {
            "iss": self.node.id, 
            "aud": self.node.authorization.authz_server_id, 
            "iat": datetime.utcnow(), 
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "attributes": self.node.attributes.get_indexed_public_with_keys()
        }
        # Create a JSON Web Token signed using the node's Elliptic Curve private key.
        jwt_request = encode_jwt(payload, self.node.node_name)
        # Send registration request to authorization server.
        self.node.proto.authorization_register(self.node.authorization.authz_server_id, 
                                          CalvinCB(self._register_node_external_cb), 
                                          jwt_request)

    def _register_node_external_cb(self, status):
        if not status or status.status != 200:
            _log.error("Node could not be registered for authorization")
