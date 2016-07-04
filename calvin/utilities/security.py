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
import json
from datetime import datetime, timedelta
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
from calvin.utilities import certificate
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
from calvin.utilities.utils import get_home
from calvin.utilities.calvin_callback import CalvinCB

_conf = calvinconfig.get()
_log = get_logger(__name__)

# Default timeout
TIMEOUT=5

try:
    _domain = _conf.get("security", "security_domain_name")
except:
    domain = None

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

def security_enabled():
    if _conf.get("security","security_conf"):
        # Want security
        return True
    else:
        return False

def encode_jwt(payload, node_name):
    """Encode JSON Web Token"""
    private_key = certificate.get_private_key(node_name)
    # Create a JSON Web Token signed using the node's Elliptic Curve private key.
    return jwt.encode(payload, private_key, algorithm='ES256')

def decode_jwt(token, sender_cert_name, node_name, node_id, actor_id=None):
    """Decode JSON Web Token"""
    # Get authorization server certificate from disk.
    try:
        sender_certificate = certificate.get_certificate(node_name, sender_cert_name)
    except Exception:
        raise Exception("Certificate not found.")
    sender_public_key = certificate.get_public_key(sender_certificate)
    sender_node_id = sender_certificate.get_subject().dnQualifier
    # The signature is verified using the Elliptic Curve public key of the sender.
    # Exception raised if signature verification fails or if issuer and/or audience are incorrect.
    decoded = jwt.decode(token, sender_public_key, algorithms=['ES256'],
                         issuer=sender_node_id, audience=node_id)
    if actor_id and decoded["sub"] != actor_id:
        raise  # Exception raised if subject (actor_id) is incorrect.
    return decoded


class Security(object):

    def __init__(self, node):
        _log.debug("_init_, node={}".format(node))
        self.sec_conf = _conf.get("security","security_conf")
        self.node = node
        self.subject_attributes = {}
        try:
            self.truststore_for_signing = certificate.get_truststore_path(self.node.node_name, certificate.TRUSTSTORE_SIGN)
        except Exception as err:
            _log.error("Failed to determine trust store path" % err)
            raise Exception("Failed to load trust store path ")

    def __str__(self):
        return "Subject: %s:" % self.subject_attributes

    def set_subject_attributes(self, subject_attributes):
        """Set subject attributes."""
        _log.debug("Security: set_subject %s" % subject_attributes)
        if not isinstance(subject_attributes, dict):
            return False
        self.subject_attributes = subject_attributes

    def get_subject_attributes(self):
        """Return a dictionary with all authenticated subject attributes."""
        return self.subject_attributes.copy()

    def authenticate_subject(self, credentials, callback=None):
        """Authenticate subject using the authentication procedure specified in config."""
        _log.debug("Security: authenticate_subject")
        request = {}
        if not security_enabled() or not credentials:
            _log.debug("Security: no security needed or no credentials to authenticate (handle as guest)")
            return True
        # Only attempt authentication if credentials for the domain are supplied.
        # If not, subject_attributes is empty, which may still grant access according to
        # the policy
        if self.node.domain in credentials:
            request['subject'] = credentials[self.node.domain]
            if self.sec_conf['authentication']['procedure'] == "external":
                if not HAS_JWT:
                    _log.error("Security: Install JWT to use external server as authentication method.\n" +
                                   "Note: NO authentication USED")
                    return False
                _log.debug("Security: external authentication method chosen")
                self.authenticate_using_external_server(request, callback)
            elif self.sec_conf['authentication']['procedure'] == "local":
                _log.debug("local authentication method chosen")
                # Authenticate access using a local Authentication Decision Point (ADP).
                self.node.authentication.adp.authenticate(request, CalvinCB(self._handle_local_authentication_response,
                                                          callback=callback))
                return True
            elif self.sec_conf['authentication']['procedure'] == "radius":
                if not HAS_PYRAD:
                    _log.error("Security: Install pyrad to use radius server as authentication method.\n" +
                                "Note! NO AUTHENTICATION USED")
                    return False
                _log.debug("Security: Radius authentication method chosen")
                return self.authenticate_using_radius_server(request, callback)
        _log.debug("Security: No security config, so authentication disabled")
        return True

    def authenticate_using_radius_server(self, request, callback):
        """Authenticate a subject using a RADIUS server."""
        try:
            root_dir = os.path.abspath(os.path.join(_conf.install_location(), '..'))
            client = Client(server=self.sec_conf['authentication']['server_ip'],
                            secret=bytes(self.sec_conf['authentication']['secret']),
                            dict=Dictionary(os.path.join(root_dir, "extras", "pyrad_dicts", "dictionary"),
                                        os.path.join(root_dir, "extras", "pyrad_dicts", "dictionary.acc")))
            req = client.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                          User_Name=request['subject']['user'],
                                          NAS_Identifier=self.node.id)
            req["User-Password"] = req.PwCrypt(request['subject']['password'])
            # FIXME: should not block here (use a callback instead)
            reply = client.SendPacket(req)
            if reply.code == pyrad.packet.AccessAccept:
                _log.debug("Security: access accepted")
                # Save attributes returned by server.
                self._return_authentication_decision(True, json.loads(reply["Reply-Message"][0]),
                                                     callback)
                return
            _log.debug("Security: access denied")
            self._return_authentication_decision(False, [], callback)
        except Exception:
            self._return_authentication_decision(False, [], callback)


    def authenticate_using_external_server(self, request, callback):
        """
        Authenticate access using an external authentication server.

        The request is put in a JSON Web Token (JWT) that is signed and encrypted
        and includes timestamps and information about sender and receiver.
        """
        try:
            auth_server_id = self.sec_conf['authentication']['server_uuid']
            payload = {
                "iss": self.node.id,
                "aud": auth_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request
            }
            # TODO: encrypt the JWT
            # Create a JSON Web Token signed using the node's Elliptic Curve private key.
            jwt_request = encode_jwt(payload, self.node.node_name)
            # Send request to authentication server.
            self.node.proto.authentication_decision(auth_server_id,
                                                   CalvinCB(self._handle_authentication_response,
                                                            callback=callback, actor_id=actor_id),
                                                   jwt_request)
        except Exception as e:
            _log.error("Security: authentication error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _handle_authentication_response(self, reply, callback, actor_id=None):
        if reply.status != 200:
            _log.error("Security: authentication server error - %s" % reply)
            self._return_authentication_decision(False, [], callback)
            return
        try:
            # Decode JSON Web Token, which contains the authentication response.
            decoded = decode_jwt(reply.data["jwt"], reply.data["cert_name"],
                                 self.node.node_name, self.node.id, actor_id)
            authentication_response = decoded['response']
            self._return_authentication_decision(authentication_response['subject_attributes'],
                                                 callback,
                                                 authentication_response.get("obligations", []))
        except Exception as e:
            _log.error("Security: JWT decoding error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _handle_local_authentication_response(self, auth_response, callback):
        try:
            self._return_authentication_decision(auth_response['decision'],
                                                 auth_response['subject_attributes'],
                                                 callback,
                                                 auth_response.get("obligations", []))
        except Exception as e:
            _log.error("Security: local authentication error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _return_authentication_decision(self, decision, subject_attributes, callback, obligations=None):
        _log.debug("Authentication response received: decision:%s, attributes:%s, obligations %s" % (decision, subject_attributes, obligations))
        if decision:
            _log.debug("authentication successful")
            self.set_subject_attributes(subject_attributes)
            callback(authentication_decision=True)
        else:
            _log.debug("authentication failed")
            callback(authentication_decision=False)
#        if obligations:
#            callback(access_decision=(True, obligations))
#        else:
#            callback(access_decision=True)

    def check_security_policy(self, callback, element_type, actor_id=None, requires=None, signer=None, decision_from_migration=None):
        """Check if access is permitted by the security policy."""
        # Can't use id for application since it is not assigned when the policy is checked.
        _log.debug("Security: check_security_policy")
        if self.sec_conf:
            signer = {element_type + "_signer": signer}
            self.get_authorization_decision(callback, actor_id, requires, signer, decision_from_migration)
            return
        # No security config, so access control is disabled.
        return callback(access_decision=True)

    def get_authorization_decision(self, callback, actor_id=None, requires=None, signer=None, decision_from_migration=None):
        """Get authorization decision using the authorization procedure specified in config."""
        if decision_from_migration:
            try:
                _log.info("Security: Authorization decision from migration")
                # Decode JSON Web Token, which contains the authorization response.
                decoded = decode_jwt(decision_from_migration["jwt"], decision_from_migration["cert_name"],
                                     self.node.node_name, self.node.id, actor_id)
                authorization_response = decoded['response']
                self._return_authorization_decision(authorization_response['decision'],
                                                    authorization_response.get("obligations", []),
                                                    callback)
                return
            except Exception as e:
                _log.error("Security: JWT decoding error - %s" % str(e))
                self._return_authorization_decision("indeterminate", [], callback)
                return
        else:
            request = {}
            request["subject"] = self.get_subject_attributes()
            if signer is not None:
                request["subject"].update(signer)
            request["resource"] = {"node_id": self.node.id}
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
                self.authorize_using_external_server(request, callback, actor_id)
            else:
                _log.debug("Security: local authorization method chosen")
                # Authorize access using a local Policy Decision Point (PDP).
                self.node.authorization.pdp.authorize(request, CalvinCB(self._handle_local_authorization_response,
                                                          callback=callback))

    def _return_authorization_decision(self, decision, obligations, callback):
        _log.info("Authorization response received: %s, obligations %s" % (decision, obligations))
        if decision == "permit":
            _log.debug("Security: access permitted to resources")
            if obligations:
                callback(access_decision=(True, obligations))
            else:
                callback(access_decision=True)
        elif decision == "deny":
            _log.debug("Security: access denied to resources")
            callback(access_decision=False)
        elif decision == "indeterminate":
            _log.debug("Security: access denied to resources. Error occured when evaluating policies.")
            callback(access_decision=False)
        else:
            _log.debug("Security: access denied to resources. No matching policies.")
            callback(access_decision=False)

    def authorize_using_external_server(self, request, callback, actor_id=None):
        """
        Authorize access using an external authorization server.

        The request is put in a JSON Web Token (JWT) that is signed
        and includes timestamps and information about sender and receiver.
        """
        try:
            authz_server_id = self.sec_conf['authorization']['server_uuid']
            payload = {
                "iss": self.node.id,
                "aud": authz_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request
            }
            if actor_id:
                payload["sub"] = actor_id
            # Create a JSON Web Token signed using the node's Elliptic Curve private key.
            jwt_request = encode_jwt(payload, self.node.node_name)
            # Send request to authorization server.
            self.node.proto.authorization_decision(authz_server_id,
                                                   CalvinCB(self._handle_authorization_response,
                                                            callback=callback, actor_id=actor_id),
                                                   jwt_request)
        except Exception as e:
            _log.error("Security: authorization error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def _handle_authorization_response(self, reply, callback, actor_id=None):
        if reply.status != 200:
            _log.error("Security: authorization server error - %s" % reply)
            self._return_authorization_decision("indeterminate", [], callback)
            return
        try:
            # Decode JSON Web Token, which contains the authorization response.
            decoded = decode_jwt(reply.data["jwt"], reply.data["cert_name"],
                                 self.node.node_name, self.node.id, actor_id)
            authorization_response = decoded['response']
            self._return_authorization_decision(authorization_response['decision'],
                                                authorization_response.get("obligations", []),
                                                callback)
        except Exception as e:
            _log.error("Security: JWT decoding error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def _handle_local_authorization_response(self, authz_response, callback):
        try:
            self._return_authorization_decision(authz_response['decision'],
                                                authz_response.get("obligations", []), callback)
        except Exception as e:
            _log.error("Security: local authorization error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def authorization_runtime_search(self, actor_id, actorstore_signature, callback):
        """Search for runtime where the authorization decision for the actor is 'permit'."""
        # extra_requirement is used to prevent InfiniteElement from being returned.
        extra_requirement = [{"op": "actor_reqs_match",
                              "kwargs": {"requires": ["calvinsys.native.python-json"]},
                              "type": "+"},
                             {"op": "current_node",
                              "kwargs": {},
                              "type": "-"}]
        self.node.am.update_requirements(actor_id, extra_requirement, True, authorization_check=True,
                                         callback=CalvinCB(self._authorization_runtime_search_cont,
                                                           actor_id=actor_id,
                                                           actorstore_signature=actorstore_signature,
                                                           callback=callback))

    def _authorization_runtime_search_cont(self, actor_id, actorstore_signature, possible_placements, callback):
        if not possible_placements:
            callback(None)
            return
        request = {}
        request["subject"] = self.get_subject_attributes()
        request["subject"]["actorstore_signature"] = actorstore_signature
        self.node.storage.get_node(possible_placements[0],
                                   cb=CalvinCB(self._send_authorization_runtime_search,
                                               actor_id=actor_id, request=request,
                                               possible_placements=possible_placements,
                                               authz_server_blacklist=[],
                                               callback=callback))

    def _send_authorization_runtime_search(self, key, value, actor_id, request, possible_placements,
                                           authz_server_blacklist, callback, counter=0):
        authz_server_id = value["authz_server"]
        if authz_server_id is None or authz_server_id in authz_server_blacklist:
            counter += 1
            if counter < len(possible_placements):
                # Try with next runtime instead.
                self.node.storage.get_node(possible_placements[counter],
                                           cb=CalvinCB(self._send_authorization_runtime_search,
                                                       actor_id=actor_id, request=request,
                                                       possible_placements=possible_placements,
                                                       authz_server_blacklist=authz_server_blacklist,
                                                       callback=callback, counter=counter))
            else:
                callback(None)
            return
        try:
            payload = {
                "iss": self.node.id,
                "sub": actor_id,
                "aud": authz_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request,
                "whitelist": possible_placements
            }
            jwt_request = encode_jwt(payload, self.node.node_name)
            # Add authz_server to blacklist to prevent sending more requests to the same server if search fails.
            authz_server_blacklist.append(authz_server_id)
            # Send request to authorization server.
            self.node.proto.authorization_search(authz_server_id,
                                                 CalvinCB(self._handle_authorization_runtime_search_response,
                                                          actor_id=actor_id, request=request,
                                                          possible_placements=possible_placements,
                                                          authz_server_blacklist=authz_server_blacklist,
                                                          callback=callback, counter=counter), jwt_request)
        except Exception as e:
            _log.error("Security: authorization server error - %s" % str(e))
            callback(None)

    def _handle_authorization_runtime_search_response(self, reply, actor_id, request, possible_placements,
                                                      authz_server_blacklist, callback, counter):
        if reply.status != 200 or reply.data["node_id"] is None:
            counter += 1
            if counter < len(possible_placements):
                # Continue searching
                self.node.storage.get_node(possible_placements[counter],
                                           cb=CalvinCB(self._send_authorization_runtime_search,
                                                       actor_id=actor_id, request=request,
                                                       possible_placements=possible_placements,
                                                       authz_server_blacklist=authz_server_blacklist,
                                                       callback=callback, counter=counter))
                return
        callback(reply)

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
                _log.debug("Security: file can't be opened")
                return None
        return {'sign': sign_content, 'file': file_content}

    def verify_signature(self, file, flag):
        """
        Verify the signature of the specified file of type flag.

        A tuple (verified True/False, signer) is returned.
        """
        _log.debug("verify_signature: file={}, flag={}".format(file, flag))
        content = Security.verify_signature_get_files(file)
        if content:
            return self.verify_signature_content(content, flag)
        else:
            return (False, None)

    def verify_signature_content(self, content, flag):
        """
        Verify the signature of the content of type flag.

        A tuple (verified True/False, signer) is returned.
        """
        _log.debug("verify_signature_content: flag={} , content={}".format(flag, content))
        if not self.sec_conf:
            _log.debug("Security: no signature verification required: %s" % content['file'])
            return (True, None)

        if flag not in ["application", "actor"]:
            # TODO add component verification
            raise NotImplementedError

        signer = None

        if content is None or not content['sign']:
            _log.debug("Security: signature information missing, content={}".format(content))
            signer = ["__unsigned__"]
            return (True, signer)  # True is returned to allow authorization request with the signer attribute '__unsigned__'.

        if not HAS_OPENSSL:
            _log.error("Security: install OpenSSL to allow verification of signatures and certificates")
            _log.error("Security: verification of %s signature failed" % flag)
            return (False, None)

        # If any of the signatures is verified correctly, True is returned.
        for cert_hash, signature in content['sign'].iteritems():
            try:
                # Check if the certificate is stored in the truststore (name is <cert_hash>.0)
                #TODO: remove signature_trust_store dependency
                trusted_cert_path = os.path.join(self.truststore_for_signing, cert_hash + ".0")
                with open(trusted_cert_path, 'rt') as f:
                    trusted_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, f.read())
                    try:
                        signer = [trusted_cert.get_issuer().CN]  # The Common Name field for the issuer
                        # Verify signature
                        OpenSSL.crypto.verify(trusted_cert, signature, content['file'], 'sha256')
                        _log.debug("Security: signature correct")
                        return (True, signer)
                    except Exception as e:
                        _log.debug("Security: OpenSSL verification error", exc_info=True)
                        continue
            except Exception as e:
                _log.debug("Security: error opening one of the needed certificates", exc_info=True)
                continue
        _log.error("Security: verification of %s signature failed" % flag)
        return (False, signer)
