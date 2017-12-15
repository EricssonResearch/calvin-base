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
from calvin.utilities import certificate
from calvin.utilities.certificate import Certificate
import os

_log = get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf.get("security","security_conf")

_search_attempt=0
_auth_server_attempt=0

class Authentication(object):
    """Authentication helper functions"""

    def __init__(self, node):
        _log.debug("Authentication::__init__")
        self.node = node
        self.auth_server_id = None
        try:
            if 'authentication' in _sec_conf and 'procedure' in _sec_conf['authentication']:
                if _sec_conf['authentication']['procedure'] == "local":
                    if 'identity_provider_path' in _sec_conf['authentication']:
                        _log.debug("Authentication::__init__   local authentication procedure configured")
                        self.arp = FileAuthenticationRetrievalPoint(_sec_conf['authentication']['identity_provider_path'])
                        self.adp = AuthenticationDecisionPoint(self.node, _sec_conf['authentication'])
                        self.auth_server_id = self.node.id
                    else:
                        _log.error("Missing identity_provider_path")
                        raise Exception("Missing identity_provider_path")

                elif (_sec_conf['authentication']['procedure'] == "external") and ('server_uuid' in _sec_conf['authentication']):
                    _log.debug("Authentication::__init__   external authentication procedure configured")
                    self.auth_server_id = _sec_conf['authentication']['server_uuid']
                else:
                    _log.debug("Authentication::__init__   external authentication procedure configured, but no node_id given."
                               " Will try to find one from storage.")
                    self.auth_server_id = None
            else:
                self.auth_server_id = None
        except Exception as e:
            _log.info("Missing or incomplete security config, e={}".format(e))
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

    def find_authentication_server(self):
        """If an authentication server has not been configured, let's try to find one"""
        _log.debug("find_authentication_server")
        #If an authentication server was configured, just return
        if self.auth_server_id:
            return
        elif _sec_conf and "authentication" in _sec_conf:
            try:
                if "procedure" in _sec_conf['authentication']:
                    if _sec_conf['authentication']['procedure'] == "external":
                        _log.debug("find_authentication_server: usage of external authentication server selected")
                        if not HAS_JWT:
                            _log.error("Install JWT to use external server as authentication method.")
                            return
                        else:
                            _log.debug("No authentication server configured, let's try to find one in storage")
                            self.node.storage.get_index(['external_authentication_server'],
                                        cb=CalvinCB(self._find_auth_server_cb, key='external_authentication_server'))
                    else:
                        _log.error("Local authentication configured but no auth_server_id set, something likely failed in the intialization phase")
                else:
                    _log.error("Please configure an authentication procedure")
                    raise("Please configure an authentication procedure")

            except Exception as e:
                _log.error("An authenticaiton server could not be found - %s" % str(e))
        else:
            _log.debug("No authentication enabled")


    def _find_auth_server_cb(self, key, value):
        import random
        import time
        global _search_attempt
        _log.debug("_find_auth_server_cb:"
                   "\n\tkey={}"
                   "\n\tvalue={}"
                   "\n\tattempt={}".format(key, value, _search_attempt))
        if value:
            self.auth_server_id = value[0]
            #Fetch authentication runtime certificate and verify that it is certified as an
            # authentication server
            index = ['certificate',self.auth_server_id]
            self.node.storage.get_index(index, cb=CalvinCB(self._check_auth_certificate_cb,
                                        key="/".join(index), auth_list_key=key, auth_list=value))
        elif _search_attempt<10:
            time_to_sleep = 1+_search_attempt*_search_attempt*_search_attempt
            _log.error("No authentication server found, try again after sleeping {} seconds".format(time_to_sleep))
            #Wait for a while and try again
            time.sleep(time_to_sleep)
            _search_attempt = _search_attempt+1
            self.node.storage.get_index(['external_authentication_server'],
                                        cb=CalvinCB(self._find_auth_server_cb, key='external_authentication_server'))
        else:
            raise Exception("No athentication server accepting external clients can be found")

    def _check_auth_certificate_cb(self, key, value, auth_list_key=None, auth_list=None):
        """Check certificate of authentcation server"""
        _log.debug("_check_auth_certificate_cb"
                   "\n\tkey={}"
                   "\n\tvalue={}".format(key, value))
        if value:
            certstr = value[0]
            try:
                certx509 = self.node.runtime_credentials.certificate.truststore_transport.verify_certificate_str(certstr)
            except Exception as err:
                _log.error("Failed to verify the authentication servers certificate from storage, err={}".format(err))
                raise
        if not "authserver" in certificate.cert_CN(certstr):
            _log.error("The runtime IS NOT certified by the CA as an authentication server, let's try another one.")
            auth_list_key.remove(key)
            auth_list.remove(value)
            self._find_auth_server_cb(key=auth_list_key, value=auth_list)
        else:
            _log.info("The runtime IS certified by the CA as an authentication server")
