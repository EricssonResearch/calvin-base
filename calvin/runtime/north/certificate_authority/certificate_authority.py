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
from calvin.utilities.certificate_authority import CA
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
import os

_log = get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf.get("security","security_conf")

class CertificateAuthority(object):
    """Certificate Authority helper functions"""

    def __init__(self, node):
        _log.info("__init__, _sec_conf={}".format(_sec_conf))
        self.node = node
        domain = None
        try:
            if _conf.get("security","certificate_authority"):
                _log.debug("__init__  Runtime is a CA")
                domain = _conf.get("security","domain_name")
                security_dir = _conf.get("security","security_dir")
                self.ca = CA(domain, security_dir=security_dir)
                self.ca_server_id = self.node.id
            else:
                _log.debug("__init__ Runtime is not a CA")
                self.ca = None
        except Exception as e:
            _log.info("Missing or incomplete security config")
            self.ca = None

    def sign_csr_request(self, data):
        """Decrypt the CSR, verify challenge password and  the  in the data."""
        _log.debug("sign_csr_request, data={}".format(data))
        #Decrypt encrypted CSR with CAs private key
        csr = self.ca.decrypt_encrypted_csr(encrypted_enrollment_request=data['csr'])
        csr_path = self.ca.store_csr_with_enrollment_password(csr)
        cert_path = self.ca.sign_csr(csr_path)
        try:
            with open(cert_path,'r') as fd:
                cert_str = fd.read()
                return cert_str
        except:
            _log.error("Failed to open certitificate file")
            return "Failure"
