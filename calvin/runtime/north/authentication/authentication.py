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
from calvin.utilities.security import decode_jwt, encode_jwt
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.authentication.authentication_decision_point import AuthenticationDecisionPoint
from calvin.runtime.north.authentication.authentication_retrieval_point import FileAuthenticationRetrievalPoint
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
import os

_log = get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf.get("security","security_conf")

class Authentication(object):
    """Authentication helper functions"""

    def __init__(self, node):
        _log.debug("Authentication::__init__")
        self.node = node
        try:
            if _sec_conf['authentication']['procedure'] == "local":
                _log.debug("Authentication::__init__   local authentication procedure configured")
                self.arp = FileAuthenticationRetrievalPoint(_sec_conf['authentication']['identity_provider_path'])
                self.adp = AuthenticationDecisionPoint(self.node, _sec_conf['authentication'])
                self.auth_server_id = self.node.id
            else:
                _log.debug("Authentication::__init__   external authentication procedure configured")
                self.auth_server_id = _sec_conf['authentication']['server_uuid']
        except Exception as e:
            _log.info("Missing or incomplete security config")
            self.auth_server_id = None

    def decode_request(self, data, callback):
        """Decode the JSON Web Token in the data."""
        _log.debug("decode_request, \n\tdata={}\n\tcallback={}".format(data, callback))
        return decode_jwt(data["jwt"],
                          data["cert_name"],
                          self.node,
                          callback=callback)

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
        # Create a JSON Web Token signed using the authentication server's private key.
        return encode_jwt(jwt_payload, self.node)


