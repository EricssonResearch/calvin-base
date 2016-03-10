# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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
import glob
from datetime import datetime, timedelta
import requests
try:
    import OpenSSL.crypto
    HAS_OPENSSL = True
except:
    HAS_OPENSSL = False
try:
    import pyrad.packet
    from pyrad.client import Client
    from pyrad.dictionary import Dictionary
    HAS_PYRAD = True
except:
    HAS_PYRAD = False
try:
    import jwt
    HAS_JWT = True
except:
    HAS_JWT = False
from calvin.utilities.authorization.policy_decision_point import PolicyDecisionPoint
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
from calvin.utilities.utils import get_home

_conf = calvinconfig.get()
_log = get_logger(__name__)

# Default timeout
TIMEOUT=5


def security_modules_check():
    if _conf.get("security","security_conf"):
        # Want security
        if not HAS_OPENSSL:
            # Miss OpenSSL
            _log.error("Security: Install openssl to allow verification of signatures and certificates")
            return False
            _conf.get("security","security_conf")['authentication']
        if _conf.get("security","security_conf")['authentication']['procedure'] == "radius" and not HAS_PYRAD:
            _log.error("Security: Install pyrad to use radius server as authentication method.")
            return False
    return True

def security_needed_check():
    if _conf.get("security","security_conf"):
        # Want security
        return True
    else:
        return False

class Security(object):

    def __init__(self, node):
        _log.debug("Security: _init_")
        self.sec_conf = _conf.get("security","security_conf")
        if self.sec_conf is not None and not self.sec_conf.get('signature_trust_store', None):
            # Set default directory for trust store
            homefolder = get_home()
            truststore_dir = os.path.join(homefolder, ".calvin", "security", "trustStore")
            self.sec_conf['signature_trust_store'] = truststore_dir
        self.node = node
        self.subject = {}
        self.auth = {}

    def __str__(self):
        return "Subject: %s\nAuth: %s" % (self.subject, self.auth)

    def set_subject(self, subject):
        """Set subject attributes and mark them as unauthenticated"""
        _log.debug("Security: set_subject %s" % subject)
        if not isinstance(subject, dict):
            return False
        # Make sure that all subject values are lists.
        self.subject = {k: list(v) if isinstance(v, (list, tuple, set)) else [v]
                            for k, v in subject.iteritems()}
        # Set the corresponding values of self.auth to False to indicate that they are unauthenticated.
        self.auth = {k: [False]*len(v) for k, v in self.subject.iteritems()}

    def authenticate_subject(self):
        """Authenticate subject using the authentication procedure specified in config."""
        _log.debug("Security: authenticate_subject")
        if not security_needed_check():
            _log.debug("Security: authenticate_subject no security needed")
            return True

        if self.sec_conf['authentication']['procedure'] == "local_file":
            _log.debug("Security: local file authentication method chosen")
            return self.authenticate_using_local_database()
        if self.sec_conf['authentication']['procedure'] == "radius":
            if not HAS_PYRAD:
                _log.error("Security: Install pyrad to use radius server as authentication method.\n" +
                            "Note! NO AUTHENTICATION USED")
                return False
            _log.debug("Security: Radius authentication method chosen")
            return self.authenticate_using_radius_server()
        _log.debug("Security: No security config, so authentication disabled")
        return True

    def authenticate_using_radius_server(self):
        """
        Authenticate a subject using a RADIUS server.

        The corresponding value in self.auth is set to True
        if authentication is successful.
        """
        auth = []
        if self.subject['user']:
            srv=Client(server=self.sec_conf['authentication']['server_ip'], 
                        secret= bytes(self.sec_conf['authentication']['secret']),
                        dict=Dictionary("extras/pyrad_dicts/dictionary", "extras/pyrad_dicts/dictionary.acc"))
            req=srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                        User_Name=self.subject['user'][0],
                        NAS_Identifier="localhost")
            req["User-Password"]=req.PwCrypt(self.subject['password'][0])
            # FIXME is this over socket? then we should not block here
            reply=srv.SendPacket(req)
            _log.debug("Attributes returned by server:")
            for i in reply.keys():
                _log.debug("%s: %s" % (i, reply[i]))
            if reply.code==pyrad.packet.AccessAccept:
                _log.debug("Security: access accepted")
                auth.append(True)
#                return True
            else:
                _log.debug("Security: access denied")
                auth.append(False)
#                return False
        self.auth['user']=auth
        return any(auth)

    def authenticate_using_local_database(self):
        """
        Authenticate a subject against information stored in config.

        The corresponding value in self.auth is set to True
        if authentication is successful.

        This is primarily intended for testing purposes,
        since passwords aren't stored securely.
        """
        if 'local_users' not in self.sec_conf['authentication']:
            _log.debug("local_users not found in security_conf: %s" % self.sec_conf['authentication'])
            return False
        # Verify users against stored passwords
        # TODO expand with other subject types
        d = self.sec_conf['authentication']['local_users']
        if not ('user' in self.subject and 'password' in self.subject):
            return False
        if len(self.subject['user']) != len(self.subject['password']):
            return False
        auth = []
        for user, password in zip(self.subject['user'], self.subject['password']):
            if user in d.keys():
                if d[user] == password:
                    _log.debug("Security: found user: %s",user)
                    auth.append(True)
                else:
                    _log.debug("Security: incorrect username or password")
                    auth.append(False)
            else:
                auth.append(False)
        self.auth['user'] = auth
        return any(auth)

    def get_authenticated_subject_attributes(self):
        """Return a dictionary with all authenticated subject attributes."""
        return {key: [self.subject[key][i] for i, auth in enumerate(values) if auth] 
                for key, values in self.auth.iteritems() if any(values)}

    def check_security_policy_actor(self, requires):
        """Check if access is permitted for the actor by the security policy"""
        _log.debug("Security: check_security_policy_actor")
        if self.sec_conf and self.sec_conf['access_control_enabled']:
            return self.get_authorization_decision(requires)
        # No security config, so access control is disabled
        return True

    def get_authorization_decision(self, requires=None):
        """Get authorization decision using the authorization procedure specified in config."""
        # The JSON code in the request is inspired by the XACML JSON Profile but has been simplified to be more compact.
        request = {}
        request["subject"] = self.get_authenticated_subject_attributes()
        request["resource"] = self.node.attributes.get_indexed_public_with_keys()
        if requires is not None:
            request["action"] = {"requires": requires}
        _log.debug("Security: authorization request: %s" % request)

        # Check if the authorization server is local (the runtime itself) or external.
        if self.sec_conf['authorization']['procedure'] == "external":
            if not HAS_JWT:
                _log.error("Security: Install JWT to use external server as authorization method.\n" +
                        "Note: NO AUTHORIZATION USED")
                return False
            _log.debug("Security: external authorization method chosen")
            decision = self.authorize_using_external_server(request)
        else: 
            _log.debug("Security: local file authorization method chosen")
            decision = self.authorize_using_local_policies(request)

        if decision == "permit":
            _log.debug("Security: access permitted to resources")
            return True
        elif decision == "deny":
            _log.debug("Security: access denied to resources")
            return False
        elif decision == "indeterminate":
            _log.debug("Security: access denied to resources. Error occured when evaluating policies.")
            return False
        else:
            _log.debug("Security: access denied to resources. No matching policies.")
            return False

    def authorize_using_external_server(self, request):
        """
        Authorize access using an external authorization server.

        The request is put in a JSON Web Token (JWT) that is signed
        and includes timestamps and information about sender and receiver.
        """
        ip_addr = self.sec_conf['authorization']['server_ip']
        port = self.sec_conf['authorization']['server_port']
        # FIXME: use name from certificate as issuer/audience (use certificate.obtain_cert_node_info(self.attributes.get_node_name_as_str())['id'])
        payload = {
            "iss": self.node.id,
            "aud": ip_addr, 
            "iat": datetime.utcnow(), 
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "request": request
        }
        # FIXME: how are the keys stored and retrieved?
        key_storage_path = os.path.join(os.path.expanduser("~/.calvin/security/keys/"), '')
        private_key = open(key_storage_path + 'private_key.pem', 'rb').read()
        pub_key_auth_server = open(key_storage_path + 'public_key_2.pem', 'rb').read()
        token = jwt.encode(payload, private_key, algorithm='RS256')
        # TODO: use async request to external server to not block here?
        try:
            response = requests.post("http://%s:%d/authorization/pdp" % (ip_addr, port), json={"jwt": token})
            if response.status_code != 200:
                print "Security: authorization server error - %s %s: %s" % (response.status_code, response.reason, response.json()["error"])
                return "indeterminate"
            else:
                json_data = response.json()
                # FIXME: use name from certificate as issuer/audience (use obtain_cert_node_info in certificate.py, see Github)
                decoded = jwt.decode(json_data['jwt'], pub_key_auth_server, algorithms=['RS256'], issuer=ip_addr, audience=self.node.id)
                return decoded['response']['decision']
        except Exception as e:
            _log.error("Security: error when sending request to authorization server: %s" % str(e))
            return "indeterminate"

    def authorize_using_local_policies(self, request):
        """Authorize access using a local Policy Decision Point (PDP)."""
        self.pdp = PolicyDecisionPoint(self.sec_conf['authorization'])
        response = self.pdp.authorize(request)
        return response['decision']

    @staticmethod
    def verify_signature_get_files(filename, skip_file=False):
        """Get files needed for signature verification of the specified file."""
        # Get the data
        sign_filenames = filename + ".sign.*"
        sign_content = {}
        file_content = ""
        # Filename is *.sign.<cert_hash>
        sign_files = {os.path.basename(f).split(".sign.")[1]: f for f in glob.glob(sign_filenames)}
        for cert_hash, sign_filename in sign_files.iteritems():
            try:
                with open(sign_filename, 'rt') as f:
                    sign_content[cert_hash] = f.read()
                    _log.debug("Security: found signature for %s" % cert_hash)
            except:
                pass
        if not skip_file:
            try:
                with open(filename, 'rt') as f:
                    file_content = f.read()
            except:
                return None
                _log.debug("Security: file can't be opened")
        return {'sign': sign_content, 'file': file_content}

    def verify_signature(self, file, flag):
        """Verify the signature of the specified file of type flag."""
        content = Security.verify_signature_get_files(file)
        if content:
            return self.verify_signature_content(content, flag)
        else:
            return False

    def verify_signature_content(self, content, flag):
        """Verify the signature of the content of type flag."""
        _log.debug("Security: verify %s signature of %s" % (flag, content))
        if not self.sec_conf:
            _log.debug("Security: no signature verification required: %s" % content['file'])
            return True

        if flag not in ["application", "actor"]:
            # TODO add component verification
            raise NotImplementedError

        self.auth[flag + "_signer"] = [True]  # Needed to include the signer attribute in authorization requests.

        if content is None or not content['sign']:
            _log.debug("Security: signature information missing")
            self.subject[flag + "_signer"] = ["__unsigned__"]
            return True  # True is returned to allow authorization request with the signer attribute '__unsigned__'.

        if not HAS_OPENSSL:
            _log.error("Security: install OpenSSL to allow verification of signatures and certificates")
            _log.error("Security: verification of %s signature failed" % flag)
            self.subject[flag + "_signer"] = ["__invalid__"]
            return False

        # If any of the signatures is verified correctly, True is returned.
        for cert_hash, signature in content['sign'].iteritems():
            try:
                # Check if the certificate is stored in the truststore (name is <cert_hash>.0)
                trusted_cert_path = os.path.join(self.sec_conf['signature_trust_store'], cert_hash + ".0")
                with open(trusted_cert_path, 'rt') as f:
                    trusted_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, f.read())
                    try:
                        # Verify signature
                        OpenSSL.crypto.verify(trusted_cert, signature, content['file'], 'sha256')
                        _log.debug("Security: signature correct")
                        self.subject[flag + "_signer"] = [trusted_cert.get_issuer().CN]  # The Common Name field for the issuer
                        return True
                    except Exception as e:
                        _log.debug("Security: OpenSSL verification error", exc_info=True)
                        continue
            except Exception as e:
                _log.debug("Security: error opening one of the needed certificates", exc_info=True)
                continue
        _log.error("Security: verification of %s signature failed" % flag)
        self.subject[flag + "_signer"] = ["__invalid__"]
        return False
